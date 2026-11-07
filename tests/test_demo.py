import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from demo.__main__ import Dataset, GRAPH, make_handler, pair_id, paths_for, recalculate
from picking.distances import Task, prepare_distances
from picking.algorithms import solve
from picking.runner import run_request
from dataclasses import asdict


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        directory = Path(cls.temp.name)
        cls.task = {'id': '101:3:paired-far:0', 'seed': 101, 'group': '101', 'split': 'eval',
                    'pattern': 'paired-far', 'start': [0, 0], 'required': [[0, 2], [4, 2], [8, 2]]}
        task = Task.create(GRAPH, (0, 0), [(0, 2), (4, 2), (8, 2)])
        table = prepare_distances(GRAPH, task)
        feature = {'n': 3, 'internal_n': 3, 'dispersion': 1, 'start_mean': 2, 'conveyor_mean': 3, 'pattern': 'paired-far'}
        results = {'candidate': asdict(solve(table, 'nn')),
                   'request': asdict(run_request(GRAPH, (0, 0), task.required, 'nn'))}
        (directory / 'tasks.jsonl').write_text(json.dumps(cls.task) + '\n')
        (directory / 'rules.json').write_text(json.dumps({'rules': {'count': {'algorithm': 'nn'}}}))
        for split in ('dev', 'eval'):
            for mode in ('candidate', 'request'):
                row = {'task': cls.task, 'features': feature, 'algorithm': 'nn', 'mode': mode,
                       'budget_seconds': .2, 'coefficient': .5, 'limits': {}, 'result': results[mode]}
                (directory / f'{split}-{mode}.jsonl').write_text(json.dumps(row) + '\n' if split == 'eval' else '')
        cls.data = Dataset(directory)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_recorded_and_reconstructed_paths_match_distance(self):
        for mode in ('candidate', 'request'):
            detail = self.data.detail(self.task['id'], mode)
            result = detail['results'][0]
            self.assertIsNotNone(result['path'])
            self.assertEqual(tuple(result['path'][0]), (0, 0))
            self.assertEqual(tuple(result['path'][-1]), GRAPH.conveyor)
            broken = dict(result, distance=result['distance'] + 1)
            with self.assertRaises(ValueError):
                paths_for(broken, self.task)

    def test_f_h_pair_ids_and_filters(self):
        self.assertEqual(pair_id(self.task, 'F'), '101:3:paired-near:0')
        self.assertEqual(pair_id(self.task, 'H'), '101:3:paired-far:1')
        self.assertEqual(len(self.data.query({'split': 'eval', 'n': '3'})), 1)
        self.assertEqual(self.data.query({'split': 'dev'}), [])
        agg = self.data.aggregate([self.task], 'candidate')
        self.assertEqual(next(r for r in agg if r['algorithm'] == 'nn')['completed'], 1)

    def test_fallback_provenance_and_recalculation_validation(self):
        eight = [[x, 2] for x in range(0, 32, 4)]
        task = dict(self.task, id='large', required=eight)
        self.data.tasks['large'] = task
        try:
            row = recalculate(self.data, {'id': 'large', 'algorithms': ['exhaustive'], 'budget': 1})[0]
            self.assertEqual(row['status'], 'resource_limit')
            self.assertEqual(row['returned_algorithm'], 'nn')
            self.assertTrue(row['fallback_used'])
            for payload in ({'id': 'missing', 'algorithms': ['nn']},
                            {'id': 'large', 'algorithms': ['invalid']},
                            {'id': 'large', 'algorithms': ['nn'], 'budget': 99}):
                with self.assertRaises(ValueError):
                    recalculate(self.data, payload)
        finally:
            del self.data.tasks['large']

    def test_http_roundtrip_and_untrusted_origin(self):
        server = HTTPServer(('127.0.0.1', 0), make_handler(self.data))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/tasks?split=eval') as response:
                self.assertEqual(json.load(response)[0]['id'], self.task['id'])
            with urlopen(base + '/api/detail?id=101%3A3%3Apaired-far%3A0&mode=request') as response:
                self.assertEqual(json.load(response)['results'][0]['algorithm'], 'nn')
            body = json.dumps({'id': self.task['id'], 'algorithms': ['nn']}).encode()
            request = Request(base + '/api/recalculate', data=body,
                              headers={'Content-Type': 'application/json', 'Origin': 'https://example.com'})
            with self.assertRaises(HTTPError) as caught:
                urlopen(request)
            self.assertEqual(caught.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
