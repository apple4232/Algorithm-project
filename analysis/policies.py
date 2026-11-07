"""Paired policy comparisons and an estimated same-budget offline reference."""
import json
import sys
from collections import defaultdict

from analysis.views import completed, paired


def analyze(policies, candidates):
    by_task = defaultdict(dict)
    for row in candidates:
        by_task[row['task']['id']][row['algorithm']] = row
    by_policy_task = defaultdict(dict)
    for row in policies:
        by_policy_task[row['task']['id']][row['algorithm']] = row
    output = {}
    for name in sorted({r['algorithm'] for r in policies}):
        selected = [r for r in policies if r['algorithm'] == name]
        pairs, regrets = [], []
        attempted_reference = 0
        for row in selected:
            if not completed(row) or row['result'].get('budget_exceeded'):
                continue
            tid = row['task']['id']
            base = by_policy_task[tid].get('fixed')
            if base and completed(base) and not base['result'].get('budget_exceeded'):
                pairs.append((row['task']['group'], base['result']['distance'] - row['result']['distance']))
            eligible = []
            for reference in by_task[tid].values():
                result = reference['result']
                if not completed(reference) or result.get('budget_exceeded'):
                    continue
                total = (result['timings']['total'] + reference['shared_preprocessing_seconds']
                         + reference['feature_seconds'] + row['selection_seconds'])
                if total <= row['budget_seconds']:
                    eligible.append(result['distance'])
            if eligible:
                attempted_reference += 1
                regrets.append((row['task']['group'], row['result']['distance'] - min(eligible)))
        output[name] = {'attempts': len(selected), 'completed_within_budget': sum(completed(r) and not r['result'].get('budget_exceeded') for r in selected),
                        'fixed_minus_policy_m': paired(pairs), 'estimated_offline_regret_m': paired(regrets),
                        'tasks_with_estimated_reference': attempted_reference}
    return {'policies': output, 'note': 'Offline reference uses separately timed full requests plus separate feature preparation and policy selection time, and filters candidates exceeding the total budget. Timings vary between runs; this is an estimate, not a deployed selector or proven optimum. Paired differences include only tasks completed within budget by both policies.'}


def main():
    if len(sys.argv) != 4:
        raise SystemExit('usage: python -m analysis.policies POLICIES.jsonl REQUESTS.jsonl OUTPUT.json')
    with open(sys.argv[1], encoding='utf-8') as f:
        policies = [json.loads(line) for line in f if line.strip()]
    with open(sys.argv[2], encoding='utf-8') as f:
        candidates = [json.loads(line) for line in f if line.strip()]
    with open(sys.argv[3], 'x', encoding='utf-8') as f:
        json.dump(analyze(policies, candidates), f, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
