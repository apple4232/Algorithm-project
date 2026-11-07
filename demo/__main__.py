"""Local, read-only viewer for saved warehouse experiments."""
from collections import Counter
from dataclasses import asdict
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import mimetypes
from pathlib import Path
from statistics import median
from urllib.parse import parse_qs, urlparse

from picking.algorithms import ALGORITHMS
from picking.distances import Task, prepare_distances
from picking.graph import build_warehouse
from picking.runner import run_request

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'results' / 'full'
STATIC = Path(__file__).resolve().parent
GRAPH = build_warehouse()


def paths_for(result, task):
    """Reuse recorded paths; reconstruct candidate orders and verify both."""
    if result.get('order') is None or result.get('distance') is None:
        return None
    table = table_for(task['id'], tuple(task['start']), tuple(map(tuple, task['required'])))
    order = tuple(map(tuple, result['order']))
    path = tuple(map(tuple, result['path'])) if result.get('path') is not None else table.reconstruct(order)
    table.validate_path(order, path, result['distance'])
    return path


@lru_cache(maxsize=32)
def table_for(_id, start, required):
    return prepare_distances(GRAPH, Task.create(GRAPH, start, required))


def pair_id(task, scenario):
    parts = task['id'].split(':')
    if len(parts) != 4:
        return None
    if scenario == 'F':
        if parts[2] == 'paired-near':
            parts[2] = 'paired-far'
        elif parts[2] == 'paired-far':
            parts[2] = 'paired-near'
        else:
            return None
    elif scenario == 'H':
        parts[3] = '1' if parts[3] == '0' else '0'
    else:
        return None
    return ':'.join(parts)


def normalized(row):
    result = row['result']
    request = row['mode'] == 'request'
    requested = result.get('requested_result') or {}
    return {'algorithm': row['algorithm'], 'status': result['status'],
            'termination': requested.get('termination') if request else result.get('termination'),
            'distance': result.get('distance'), 'order': result.get('order'), 'path': result.get('path'),
            'returned_algorithm': result.get('returned_algorithm') if request else row['algorithm'],
            'fallback_used': result.get('fallback_used', False), 'optimal': result.get('optimal', False),
            'budget_exceeded': result.get('budget_exceeded', False),
            'seconds': result.get('timings', {}).get('total') if request else result.get('elapsed_seconds'),
            'message': result.get('message', ''), 'budget_seconds': row.get('budget_seconds'),
            'coefficient': row.get('coefficient'), 'limits': row.get('limits')}


class Dataset:
    def __init__(self, directory=DATA):
        self.tasks, self.rows = {}, {'candidate': {}, 'request': {}}
        with (directory / 'tasks.jsonl').open(encoding='utf-8') as handle:
            for line in handle:
                task = json.loads(line)
                self.tasks[task['id']] = task
        for split in ('dev', 'eval'):
            for mode in self.rows:
                with (directory / f'{split}-{mode}.jsonl').open(encoding='utf-8') as handle:
                    for line in handle:
                        row = json.loads(line)
                        task_id = row['task']['id']
                        if task_id not in self.tasks:
                            raise ValueError(f'unknown task in data: {task_id}')
                        record = self.rows[mode].setdefault(task_id, {'features': row['features'], 'results': {}})
                        result = normalized(row)
                        # The warehouse has 210 nodes, so each path node fits in one byte.
                        for field in ('order', 'path'):
                            if result[field] is not None:
                                result[field] = bytes(int(x // 4) * 21 + int(y // 2) for x, y in result[field])
                        record['results'][row['algorithm']] = result
        with (directory / 'rules.json').open(encoding='utf-8') as handle:
            self.rules = json.load(handle)

    def query(self, filters):
        out = []
        for task in self.tasks.values():
            if any(value and str(task[key] if key != 'n' else len(task['required'])) != value
                   for key, value in filters.items() if key in ('split', 'pattern', 'seed', 'n')):
                continue
            start = filters.get('start')
            if start and str(task['id'].split(':')[-1]) != start:
                continue
            out.append(task)
        return out

    def detail(self, task_id, mode):
        if task_id not in self.tasks or mode not in self.rows:
            raise ValueError('작업 또는 측정 종류를 확인하세요.')
        task = self.tasks[task_id]
        record = self.rows[mode].get(task_id)
        if record is None:
            raise ValueError('이 작업의 저장 결과가 없습니다.')
        results = []
        for name in ALGORITHMS:
            if name not in record['results']:
                continue
            result = dict(record['results'][name])
            for field in ('order', 'path'):
                if result[field] is not None:
                    result[field] = [[(node // 21) * 4, (node % 21) * 2] for node in result[field]]
            try:
                result['path'] = paths_for(result, task)
            except (ValueError, KeyError) as exc:
                result['path'] = None
                result['path_error'] = str(exc)
            results.append(result)
        return {'task': task, 'features': record['features'], 'results': results, 'rules': self.rules['rules'],
                'pair_f': pair_id(task, 'F'), 'pair_h': pair_id(task, 'H')}

    def aggregate(self, tasks, mode):
        if mode not in self.rows:
            raise ValueError('측정 종류를 확인하세요.')
        stats = {name: {'status': Counter(), 'distances': [], 'times': [], 'attempts': 0} for name in ALGORITHMS}
        for task in tasks:
            record = self.rows[mode].get(task['id'], {})
            for name, row in record.get('results', {}).items():
                s = stats[name]
                s['attempts'] += 1
                s['status'][row['status']] += 1
                if row['status'] == 'completed' and not row['budget_exceeded'] and row['distance'] is not None:
                    s['distances'].append(row['distance'])
                    if row['seconds'] is not None:
                        s['times'].append(row['seconds'])
        return [{'algorithm': name, 'attempts': s['attempts'], 'statuses': s['status'],
                 'completed': len(s['distances']), 'median_distance': median(s['distances']) if s['distances'] else None,
                 'median_seconds': median(s['times']) if s['times'] else None} for name, s in stats.items()]


def recalculate(dataset, payload):
    task_id, algorithms = payload.get('id'), payload.get('algorithms')
    if task_id not in dataset.tasks or not isinstance(algorithms, list) or not 1 <= len(algorithms) <= 2:
        raise ValueError('작업과 두 개 이하의 알고리즘을 선택하세요.')
    if any(not isinstance(a, str) or a not in ALGORITHMS for a in algorithms):
        raise ValueError('알 수 없는 알고리즘입니다.')
    budget, coefficient = payload.get('budget', .2), payload.get('coefficient', .5)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (budget, coefficient)):
        raise ValueError('시간과 계수는 유한한 숫자여야 합니다.')
    if not .01 <= budget <= 2 or not 0 <= coefficient <= 2:
        raise ValueError('시간은 0.01~2초, 계수는 0~2로 입력하세요.')
    task = dataset.tasks[task_id]
    rows = []
    for algorithm in algorithms:
        result = run_request(GRAPH, tuple(task['start']), list(map(tuple, task['required'])), algorithm,
                             budget_seconds=budget, coefficient=coefficient)
        row = normalized({'algorithm': algorithm, 'mode': 'request', 'result': asdict(result),
                          'budget_seconds': budget, 'coefficient': coefficient})
        row['path'] = paths_for(row, task)
        rows.append(row)
    return rows


def make_handler(dataset, load_error=None):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, value, status=200):
            data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parsed = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            try:
                if parsed.path.startswith('/api/') and dataset is None:
                    self.send_json({'error': f'실험 데이터를 읽지 못했습니다: {load_error}. README의 데이터 준비 방법을 확인하세요.'}, 503)
                    return
                if parsed.path == '/api/tasks':
                    self.send_json(dataset.query(params))
                elif parsed.path == '/api/detail':
                    self.send_json(dataset.detail(params.get('id'), params.get('mode', 'request')))
                elif parsed.path == '/api/aggregate':
                    self.send_json(dataset.aggregate(dataset.query(params), params.get('mode', 'request')))
                elif parsed.path in ('/', '/app.js', '/style.css'):
                    name = 'index.html' if parsed.path == '/' else parsed.path[1:]
                    data = (STATIC / name).read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', mimetypes.guess_type(name)[0] + '; charset=utf-8')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_error(404)
            except (ValueError, KeyError) as exc:
                self.send_json({'error': str(exc)}, 400)

        def do_POST(self):
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            if self.path != '/api/recalculate' or host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}') or (origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}')):
                self.send_error(403)
                return
            if dataset is None:
                self.send_json({'error': '실험 데이터가 없어 재계산할 수 없습니다.'}, 503)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if self.headers.get_content_type() != 'application/json' or not 0 < size <= 4096:
                    raise ValueError('올바른 JSON 요청이 필요합니다.')
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError('올바른 JSON 객체가 필요합니다.')
                self.send_json({'results': recalculate(dataset, payload)})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send_json({'error': str(exc)}, 400)
    return Handler


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    print('실험 결과를 읽는 중입니다...', flush=True)
    load_error = None
    try:
        dataset = Dataset()
    except (OSError, ValueError, KeyError) as exc:
        dataset, load_error = None, str(exc)
        print(f'실험 데이터 오류: {load_error}', flush=True)
    server = HTTPServer(('127.0.0.1', args.port), make_handler(dataset, load_error))
    print(f'데모: http://127.0.0.1:{server.server_port} (종료: Ctrl+C)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
