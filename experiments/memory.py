"""Measure whole-process peak RSS for one candidate in a fresh process.

On Linux ru_maxrss is KiB; on macOS it is bytes. This includes the Python
interpreter and distance preparation, and should not be used as timing data.
"""
from dataclasses import asdict
import json
import resource
import sys
from time import perf_counter

from picking.algorithms import solve
from picking.distances import Task, prepare_distances
from picking.graph import build_warehouse


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: python -m experiments.memory TASKS.jsonl LINE_NUMBER ALGORITHM")
    path, index, algorithm = sys.argv[1:]
    with open(path, encoding="utf-8") as handle:
        task = next(row for i, row in enumerate(handle) if i == int(index))
    task = json.loads(task)
    graph = build_warehouse()
    table = prepare_distances(graph, Task.create(graph, tuple(task['start']), [tuple(p) for p in task['required']]))
    result = solve(table, algorithm, deadline=perf_counter() + 2)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({"task_id": task['id'], "algorithm": algorithm, "result": asdict(result),
                      "peak_rss_bytes": peak if sys.platform == 'darwin' else peak * 1024,
                      "scope": "whole process including interpreter and preprocessing"}))


if __name__ == '__main__':
    main()
