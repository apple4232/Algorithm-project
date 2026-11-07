"""Produce exploratory A-H paired views from candidate-only JSONL records."""
import json
from collections import Counter, defaultdict
from statistics import mean, median
import sys

from experiments.analysis import group_interval


def completed(row):
    result = row['result']
    return result['status'] == 'completed' and result.get('distance') is not None


def paired(values):
    groups = defaultdict(list)
    for group, value in values:
        groups[group].append(value)
    return {'pairs': len(values), 'groups': len(groups),
            'mean_difference_m': mean(v for _, v in values) if values else None,
            'ci95_group_bootstrap_m': group_interval(groups)}


def views(rows):
    tasks = defaultdict(dict)
    for row in rows:
        tasks[row['task']['id']][row['algorithm']] = row
    small = [(v['exhaustive']['result']['distance'], v['dp']['result']['distance'])
             for v in tasks.values() if 'exhaustive' in v and 'dp' in v
             and completed(v['exhaustive']) and completed(v['dp'])]
    dp_sizes = defaultdict(Counter)
    for row in rows:
        if row['algorithm'] == 'dp':
            dp_sizes[str(row['features']['n'])][row['result']['status']] += 1
    nn = {tid: v['nn'] for tid, v in tasks.items() if 'nn' in v and completed(v['nn'])}
    valid = [(v['nn'], v['nn+2opt']) for v in tasks.values()
             if 'nn' in v and 'nn+2opt' in v and completed(v['nn']) and completed(v['nn+2opt'])]
    cutoff = median(row['features']['dispersion'] for row, _ in valid) if valid else None
    def gains(subset):
        return paired([(a['task']['group'], a['result']['distance'] - b['result']['distance']) for a, b in subset])
    clusters = [(a, b) for a, b in valid if a['task']['pattern'] == 'clustered']
    near_far = []
    starts = []
    for tid, row in nn.items():
        if ':paired-far:' in tid:
            other = nn.get(tid.replace(':paired-far:', ':paired-near:'))
            if other:
                near_far.append((row['task']['group'], row['result']['distance'] - other['result']['distance']))
        if tid.endswith(':0'):
            other = nn.get(tid[:-1] + '1')
            if other:
                starts.append((row['task']['group'], row['result']['distance'] - other['result']['distance']))
    patterns = {}
    for pattern in sorted({a['task']['pattern'] for a, _ in valid}):
        patterns[pattern] = gains([(a,b) for a,b in valid if a['task']['pattern'] == pattern])
    return {'A_exact_agreement': {'paired_tasks': len(small), 'distance_mismatches': sum(abs(a-b) > 1e-9 for a,b in small)},
            'B_dp_status_by_n': {n: dict(v) for n,v in dp_sizes.items()},
            'C_large_nn_vs_2opt': gains([(a,b) for a,b in valid if a['features']['n'] >= 20]),
            'D_cluster_nn_vs_2opt': gains(clusters),
            'E_dispersion': {'evaluation_median_cutoff_m': cutoff,
                             'below_or_equal': gains([(a,b) for a,b in valid if a['features']['dispersion'] <= cutoff]),
                             'above': gains([(a,b) for a,b in valid if a['features']['dispersion'] > cutoff])} if cutoff is not None else {},
            'F_nn_far_minus_near': paired(near_far),
            'G_nn_vs_2opt_by_pattern': patterns,
            'H_nn_front_minus_center': paired(starts),
            'notes': 'Descriptive evaluation views, not causal effects. Positive NN-minus-2opt favors 2opt. F also changes start distances. E uses an evaluation median for description only, not selector training.'}


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: python -m analysis.views INPUT.jsonl OUTPUT.json')
    with open(sys.argv[1], encoding='utf-8') as f:
        rows = [json.loads(line) for line in f if line.strip()]
    with open(sys.argv[2], 'x', encoding='utf-8') as f:
        json.dump(views(rows), f, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
