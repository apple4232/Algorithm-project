"""Run reproducible experiments: generate, benchmark, train, evaluate, report."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
from time import perf_counter

from picking.algorithms import Limits
from picking.distances import Task, prepare_distances
from picking.graph import build_warehouse
from picking.runner import run_request
from .analysis import select, summarize, train
from .benchmark import environment, run
from .workloads import features, generate


def read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_lines(path, records):
    with open(path, "x", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def evaluate(records, model):
    graph = build_warehouse()
    if environment()["source_sha256"] != model["source_sha256"]:
        raise ValueError("source code differs from frozen model; retrain or restore the recorded version")
    for task in records:
        if task["split"] != "eval" or task["group"] in model["training_groups"]:
            raise ValueError("evaluation requires held-out groups")
        policies = list(model["rules"])
        random.Random("policy:" + task["id"]).shuffle(policies)
        for policy in policies:
            started = perf_counter()
            start = tuple(task["start"])
            required = [tuple(p) for p in task["required"]]
            t = perf_counter()
            table = prepare_distances(graph, Task.create(graph, start, required))
            prep_seconds = perf_counter() - t
            t = perf_counter()
            values = features(table, task["pattern"])
            feature_seconds = perf_counter() - t
            t = perf_counter()
            chosen = select(model["rules"][policy], values)
            selection_seconds = perf_counter() - t
            remaining = model["budget_seconds"] - (perf_counter() - started)
            if remaining > 0:
                result = asdict(run_request(graph, start, required, chosen, budget_seconds=remaining,
                                            coefficient=model["coefficient"], limits=Limits(**model["limits"])))
            else:
                result = {"status": "timeout", "distance": None, "optimal": False,
                          "message": "budget exhausted before request", "budget_exceeded": True}
            total = perf_counter() - started
            result["policy_total_seconds"] = total
            result["budget_exceeded"] = total > model["budget_seconds"] or result.get("budget_exceeded", False)
            yield {"task": task, "features": values, "algorithm": policy, "selected_algorithm": chosen,
                   "mode": "policy", "budget_seconds": model["budget_seconds"], "result": result,
                   "preprocessing_seconds": prep_seconds, "feature_seconds": feature_seconds,
                   "selection_seconds": selection_seconds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("generate")
    p.add_argument("output")
    p.add_argument("--sizes", nargs="+", type=int, default=[3, 5, 7, 10, 20, 50])
    p.add_argument("--seeds", type=int, default=30, help="number of seeds; half even and half odd")
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--paired", action="store_true")
    p = sub.add_parser("benchmark")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--split", choices=["dev", "eval"], required=True)
    p.add_argument("--mode", choices=["candidate", "request"], required=True)
    p.add_argument("--budget", type=float, default=2.0)
    p.add_argument("--coefficient", type=float, default=1.0)
    p = sub.add_parser("train")
    p.add_argument("input")
    p.add_argument("output")
    p = sub.add_parser("evaluate")
    p.add_argument("input")
    p.add_argument("model")
    p.add_argument("output")
    p = sub.add_parser("report")
    p.add_argument("input")
    p.add_argument("output")
    args = parser.parse_args()
    if args.command == "generate":
        if args.seeds < 2 or args.seeds % 2:
            parser.error("seeds must be an even number >= 2")
        write_lines(args.output, generate(build_warehouse(), args.sizes, range(args.seed_start, args.seed_start + args.seeds), paired=args.paired))
    elif args.command == "benchmark":
        records = [r for r in read_lines(args.input) if r["split"] == args.split]
        if not records:
            parser.error("no tasks in split")
        write_lines(args.output, run(records, args.budget, args.coefficient, args.mode))
    elif args.command == "train":
        model = train(read_lines(args.input))
        with open(args.output, "x", encoding="utf-8") as handle:
            json.dump(model, handle, ensure_ascii=False, indent=2, allow_nan=False)
    elif args.command == "evaluate":
        with open(args.model, encoding="utf-8") as handle:
            model = json.load(handle)
        records = [r for r in read_lines(args.input) if r["split"] == "eval"]
        if not records:
            parser.error("no held-out tasks")
        write_lines(args.output, evaluate(records, model))
    elif args.command == "report":
        with open(args.output, "x", encoding="utf-8") as handle:
            json.dump(summarize(read_lines(args.input)), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"Wrote {Path(args.output)}")


if __name__ == "__main__":
    main()
