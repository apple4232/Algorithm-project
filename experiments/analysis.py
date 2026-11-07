"""Summaries and development-only, frozen one-split selection rules."""
from collections import Counter, defaultdict
from statistics import mean, median
import random


def group_interval(group_values, seed=0, repetitions=1000):
    """Bootstrap groups, keeping all related tasks together."""
    groups = list(group_values.values())
    if len(groups) < 2:
        return None
    rng = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        picked = [groups[rng.randrange(len(groups))] for _ in groups]
        samples.append(mean(value for group in picked for value in group))
    samples.sort()
    return [samples[int(.025 * repetitions)], samples[int(.975 * repetitions) - 1]]


def subgroup(items):
    done = [r for r in items if r["result"]["status"] == "completed" and r["result"].get("distance") is not None
            and not r["result"].get("budget_exceeded", False)]
    return {"attempts": len(items), "completed": len(done),
            "median_distance_m": median(r["result"]["distance"] for r in done) if done else None}


def summarize(rows):
    by_task = defaultdict(dict)
    by_algorithm = defaultdict(list)
    for row in rows:
        by_task[row["task"]["id"]][row["algorithm"]] = row
        by_algorithm[row["algorithm"]].append(row)
    output = {}
    for name, items in sorted(by_algorithm.items()):
        statuses = Counter(r["result"]["status"] for r in items)
        terms = Counter(r["result"].get("termination") or (r["result"].get("requested_result") or {}).get("termination", "") for r in items)
        valid = [r for r in items if r["result"]["status"] == "completed" and r["result"].get("distance") is not None
                 and not r["result"].get("budget_exceeded", False)]
        gaps, improvements, regrets, zero_differences, fixed_differences = [], [], [], [], []
        paired_groups = defaultdict(list)
        for row in valid:
            peers = by_task[row["task"]["id"]]
            distance = row["result"]["distance"]
            completed = [v["result"] for v in peers.values() if v["result"]["status"] == "completed"
                         and v["result"].get("distance") is not None and not v["result"].get("budget_exceeded", False)]
            optimum = [v["distance"] for v in completed if v.get("optimal")]
            if optimum and min(optimum) > 0:
                gaps.append(100 * (distance - min(optimum)) / min(optimum))
            elif optimum:
                zero_differences.append(distance - min(optimum))
            nn = peers.get("nn", {}).get("result", {})
            if nn.get("status") == "completed" and nn.get("distance"):
                improvements.append(100 * (nn["distance"] - distance) / nn["distance"])
                paired_groups[row["task"]["group"]].append(nn["distance"] - distance)
            fixed = peers.get("fixed", {}).get("result", {})
            if fixed.get("status") == "completed" and fixed.get("distance") is not None and not fixed.get("budget_exceeded", False):
                fixed_differences.append(fixed["distance"] - distance)
            if completed:
                regrets.append(distance - min(v["distance"] for v in completed))
        times = [r["result"].get("policy_total_seconds", r["result"].get("elapsed_seconds", r["result"].get("timings", {}).get("total"))) for r in valid]
        times = sorted(x for x in times if x is not None)
        output[name] = {"attempts": len(items), "statuses": dict(statuses), "terminations": dict(terms),
                        "feasible_completed": len(valid),
                        "median_distance": median([r["result"]["distance"] for r in valid]) if valid else None,
                        "median_seconds": median(times) if times else None,
                        "p90_seconds": times[min(len(times)-1, int(.9 * len(times)))] if times else None,
                        "mean_gap_percent": mean(gaps) if gaps else None, "gap_count": len(gaps),
                        "mean_nn_improvement_percent": mean(improvements) if improvements else None,
                        "nn_pair_count": len(improvements), "nn_paired_group_count": len(paired_groups),
                        "nn_paired_mean_difference_ci95_m": group_interval(paired_groups),
                        "zero_optimum_mean_difference_m": mean(zero_differences) if zero_differences else None,
                        "mean_difference_from_fixed_m": mean(fixed_differences) if fixed_differences else None,
                        "mean_offline_regret_m": mean(regrets) if regrets else None,
                        "by_n": {str(n): subgroup(subset)
                                 for n in sorted({r["features"]["n"] for r in items})
                                 for subset in [[r for r in items if r["features"]["n"] == n]]},
                        "by_pattern": {pattern: subgroup(subset)
                                       for pattern in sorted({r["features"]["pattern"] for r in items})
                                       for subset in [[r for r in items if r["features"]["pattern"] == pattern]]}}
    return output


def train(rows, *, cross_validate=True):
    """Fit interpretable one-threshold rules using development records only.

    A candidate must complete every training task; this avoids rewarding failures.
    Rules are resubstitution fits, not a claim of generalization.
    """
    if not rows or any(r["task"]["split"] != "dev" or r["mode"] != "request" for r in rows):
        raise ValueError("training requires development-only request records")
    tasks = defaultdict(dict)
    for row in rows:
        tasks[row["task"]["id"]][row["algorithm"]] = row
    budgets = {r["budget_seconds"] for r in rows}
    coefficients = {r["coefficient"] for r in rows}
    limit_sets = {tuple(sorted(r["limits"].items())) for r in rows}
    sources = {r["environment"]["source_sha256"] for r in rows}
    if len(budgets) != 1 or len(coefficients) != 1 or len(limit_sets) != 1 or len(sources) != 1:
        raise ValueError("training requires one budget and coefficient")
    names = set.intersection(*(set(x) for x in tasks.values()))
    def choose(ids):
        scores = []
        for name in sorted(names):
            results = [tasks[i][name]["result"] for i in ids]
            if all(r["status"] == "completed" and r.get("distance") is not None and not r.get("budget_exceeded", False) for r in results):
                scores.append((sum(r["distance"] for r in results), name))
        if not scores:
            raise ValueError("no candidate completed every training task within budget")
        return min(scores)
    ids = sorted(tasks)
    fixed_score, fixed = choose(ids)
    rules = {"fixed": {"algorithm": fixed}}
    feature_sets = {"count": ["n"], "numeric": ["n", "dispersion", "start_mean", "conveyor_mean"],
                    "numeric_pattern": ["n", "dispersion", "start_mean", "conveyor_mean", "pattern"]}
    for label, fields in feature_sets.items():
        best = (fixed_score, {"algorithm": fixed})
        for field in fields:
            values = {i: next(iter(tasks[i].values()))["features"][field] for i in ids}
            distinct = sorted(set(values.values()))
            if field == "pattern":
                thresholds = distinct
            else:
                indices = sorted({min(len(distinct)-2, int((len(distinct)-1)*q/10)) for q in range(1, 10)}) if len(distinct) > 1 else []
                thresholds = [(distinct[i]+distinct[i+1])/2 for i in indices]
            for threshold in thresholds:
                left = [i for i in ids if values[i] == threshold] if field == "pattern" else [i for i in ids if values[i] <= threshold]
                left_set = set(left)
                right = [i for i in ids if i not in left_set]
                if not left or not right:
                    continue
                try:
                    lscore, lalg = choose(left)
                    rscore, ralg = choose(right)
                except ValueError:
                    continue
                if lscore + rscore < best[0] - 1e-9:
                    best = (lscore + rscore, {"feature": field, "threshold": threshold, "left": lalg, "right": ralg})
        rules[label] = best[1]
    groups = sorted({r['task']['group'] for r in rows})
    cv = {}
    if cross_validate and len(groups) >= 2:
        folds = min(3, len(groups))
        scores = {name: [] for name in rules}
        failures = Counter()
        for fold in range(folds):
            held = set(groups[fold::folds])
            fit = train([r for r in rows if r["task"]["group"] not in held], cross_validate=False)
            validation = [r for r in rows if r["task"]["group"] in held]
            for name, rule in fit["rules"].items():
                for row in validation:
                    if row["algorithm"] != select(rule, row["features"]):
                        continue
                    result = row["result"]
                    if result["status"] == "completed" and result.get("distance") is not None and not result.get("budget_exceeded", False):
                        scores[name].append(result["distance"])
                    else:
                        failures[name] += 1
        cv = {name: {"completed": len(values), "failures": failures[name],
                     "mean_distance_m": mean(values) if values else None} for name, values in scores.items()}
    return {"rules": rules, "training_task_count": len(ids), "training_groups": groups,
            "budget_seconds": next(iter(budgets)), "coefficient": next(iter(coefficients)),
            "limits": dict(next(iter(limit_sets))), "source_sha256": next(iter(sources)),
            "group_cross_validation": cv,
            "note": "Rules fitted on all development data after grouped CV; pattern is synthetic metadata."}


def select(rule, values):
    if "algorithm" in rule:
        return rule["algorithm"]
    value, threshold = values[rule["feature"]], rule["threshold"]
    left = value == threshold if rule["feature"] == "pattern" else value <= threshold
    return rule["left"] if left else rule["right"]
