"""Candidate-only and full-request measurements with separate result fields."""
from dataclasses import asdict
import platform
from hashlib import sha256
from pathlib import Path
import random
import subprocess
import sys
from time import perf_counter

from picking.algorithms import ALGORITHMS, Limits, solve
from picking.distances import Task, prepare_distances
from picking.graph import build_warehouse
from picking.runner import run_request
from .workloads import features


def environment():
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    code = sorted(Path("picking").glob("*.py")) + sorted(Path("experiments").glob("*.py"))
    digest = sha256(b"".join(str(p).encode() + p.read_bytes() for p in code)).hexdigest()
    return {"source_sha256": digest, "python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
            "revision": revision, "dirty": dirty, "graph": "warehouse-10x40-v1", "cache": "disabled"}


def run(records, budget, coefficient, mode, *, seed=0, limits=None):
    if budget <= 0 or mode not in ("candidate", "request"):
        raise ValueError("budget must be positive and mode must be candidate or request")
    limits = limits or Limits()
    graph = build_warehouse()
    env = environment()
    for record in records:
        start = tuple(record["start"])
        required = [tuple(p) for p in record["required"]]
        t = perf_counter()
        task = Task.create(graph, start, required)
        table = prepare_distances(graph, task)
        preprocessing = perf_counter() - t
        t = perf_counter()
        values = features(table, record["pattern"])
        feature_seconds = perf_counter() - t
        names = list(ALGORITHMS)
        random.Random(f"order:{seed}:{record['id']}:{mode}").shuffle(names)
        for name in names:
            common = {"task": record, "features": values, "algorithm": name, "mode": mode,
                      "coefficient": coefficient, "budget_seconds": budget,
                      "limits": asdict(limits), "environment": env,
                      "shared_preprocessing_seconds": preprocessing, "feature_seconds": feature_seconds}
            try:
                if mode == "candidate":
                    result = solve(table, name, coefficient=coefficient, limits=limits,
                                   deadline=perf_counter() + budget)
                    if result.order is not None:
                        path = table.reconstruct(result.order)
                        table.validate_path(result.order, path, result.distance)
                    common["result"] = asdict(result)
                else:
                    # This measures the request runner itself; feature/selection overhead is separate.
                    result = run_request(graph, start, required, name, budget_seconds=budget,
                                         coefficient=coefficient, limits=limits)
                    common["result"] = asdict(result)
            except Exception as exc:
                common["result"] = {"status": "error", "distance": None, "optimal": False,
                                    "termination": type(exc).__name__, "message": str(exc)}
            yield common
