"""Deterministic synthetic workloads and aisle-distance features."""
from itertools import combinations
import random

from picking.distances import Task

STARTS = ((0, 0), (16, 20), (0, 40))
PATTERNS = ("clustered", "random-stow-like", "directional")


def features(table, pattern):
    task = table.task
    points = task.required
    pairs = list(combinations(points, 2))
    return {
        "n": task.n,
        "internal_n": len(task.internal),
        "dispersion": sum(table.d(a, b) for a, b in pairs) / len(pairs) if pairs else 0.0,
        "start_mean": sum(table.d(task.start, p) for p in points) / task.n if task.n else 0.0,
        "conveyor_mean": sum(table.d(p, task.conveyor) for p in points) / task.n if task.n else 0.0,
        "pattern": pattern,
    }


def generate(graph, sizes, seeds, *, paired=False):
    """Each seed is one split group; start and mirrored variants stay together."""
    locations = sorted(graph.picking_locations)
    aisles = sorted({p[0] for p in locations})
    records = []
    used = set()
    for seed in seeds:
        for n in sizes:
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                raise ValueError("sizes must be positive integers")
            for pattern in PATTERNS:
                rng = random.Random(f"v1:{seed}:{n}:{pattern}")
                if pattern == "clustered":
                    first = rng.randrange(len(aisles) - 2)
                    pool = [p for p in locations if p[0] in aisles[first:first + 3]]
                elif pattern == "directional":
                    pool = [p for p in locations if p[1] >= 22]
                else:
                    pool = locations
                if n > len(pool):
                    raise ValueError(f"{pattern}: {n} exceeds pool size {len(pool)}")
                for _ in range(1000):
                    points = rng.sample(pool, n)
                    key = tuple(sorted(points))
                    if key not in used:
                        used.add(key)
                        break
                else:
                    raise ValueError("unable to generate a unique item set within 1000 attempts")
                for i, start in enumerate(STARTS):
                    records.append({"id": f"{seed}:{n}:{pattern}:{i}", "group": str(seed),
                                    "seed": seed, "split": "dev" if seed % 2 == 0 else "eval",
                                    "pattern": pattern, "start": start, "required": points})
            if paired:
                rng = random.Random(f"v1:{seed}:{n}:paired")
                pool = [p for p in locations if p[0] <= 16]
                if n > len(pool):
                    raise ValueError(f"paired: {n} exceeds pool size {len(pool)}")
                for _ in range(1000):
                    points = rng.sample(pool, n)
                    far = tuple(sorted(points))
                    near = tuple(sorted((36-x, y) for x, y in points))
                    if far != near and far not in used and near not in used:
                        used.update((far, near))
                        break
                else:
                    raise ValueError("unable to generate a unique mirrored pair within 1000 attempts")
                for side, selected in (("far", points), ("near", [(36-x, y) for x, y in points])):
                    for i, start in enumerate(STARTS):
                        records.append({"id": f"{seed}:{n}:paired-{side}:{i}", "group": str(seed),
                                        "seed": seed, "split": "dev" if seed % 2 == 0 else "eval",
                                        "pattern": "paired-" + side, "start": start, "required": selected})
    seen = {}
    for record in records:
        Task.create(graph, record["start"], record["required"])
        key = tuple(sorted(record["required"]))
        old = seen.setdefault(key, record["split"])
        if old != record["split"]:
            raise ValueError("duplicate item set across development and evaluation splits")
    return records
