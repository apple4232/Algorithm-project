"""Measure DP peak process RSS for one development task per item count."""
import json
import subprocess
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: python -m analysis.memory_scale TASKS.jsonl OUTPUT.jsonl')
    path, output = sys.argv[1:]
    chosen = {}
    with open(path, encoding='utf-8') as handle:
        for index, line in enumerate(handle):
            task = json.loads(line)
            n = len(task['required'])
            if task['split'] == 'dev' and task['pattern'] == 'random-stow-like' and n not in chosen:
                chosen[n] = index
    with open(output, 'x', encoding='utf-8') as handle:
        for n, index in sorted(chosen.items()):
            command = [sys.executable, '-m', 'experiments.memory', path, str(index), 'dp']
            result = json.loads(subprocess.check_output(command, text=True))
            result['n'] = n
            handle.write(json.dumps(result) + '\n')


if __name__ == '__main__':
    main()
