"""동일 거리 행렬을 이용하는 방문 순서 알고리즘과 공통 2-opt."""

from array import array
from dataclasses import dataclass, field, replace
from itertools import permutations
from math import inf, isfinite
from time import perf_counter

from .distances import DeadlineExceeded, DistanceTable, check_deadline
from .graph import InputError, Node

BASE_ALGORITHMS = ("given", "nn", "exhaustive", "dp", "ca-plus", "ca-minus")
ALGORITHMS = BASE_ALGORITHMS + ("nn+2opt", "ca-plus+2opt", "ca-minus+2opt")


@dataclass(frozen=True)
class Limits:
    exhaustive_n: int = 7
    dp_n: int = 15
    dp_memory_bytes: int = 256 * 1024 * 1024
    two_opt_evaluations: int = 10_000

    def __post_init__(self):
        for value in (self.exhaustive_n, self.dp_n, self.dp_memory_bytes, self.two_opt_evaluations):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InputError("계산 한도는 비음수 정수여야 합니다.")


@dataclass(frozen=True)
class AlgorithmResult:
    algorithm: str
    status: str
    order: tuple[Node, ...] | None
    distance: float | None
    optimal: bool = False
    termination: str = "completed"
    elapsed_seconds: float = 0.0
    details: dict = field(default_factory=dict)


def _result(table: DistanceTable, name: str, order: tuple[Node, ...] | None,
            *, status: str = "completed", optimal: bool = False,
            termination: str = "completed", **details) -> AlgorithmResult:
    distance = table.route_distance(order) if order is not None else None
    return AlgorithmResult(name, status, order, distance, optimal, termination, details=details)


def _cost(table: DistanceTable, order: tuple[Node, ...] | list[Node]) -> float:
    stops = (table.task.start, *order, table.task.conveyor)
    return sum(table.d(u, v) for u, v in zip(stops, stops[1:]))


def _greedy(table: DistanceTable, name: str, coefficient: float,
            deadline: float | None) -> AlgorithmResult:
    current = table.task.start
    unvisited, order = set(table.task.internal), []
    direction = 1 if name == "ca-plus" else -1 if name == "ca-minus" else 0
    while unvisited:
        check_deadline(deadline)
        following = min(unvisited, key=lambda p: (
            table.d(current, p) + direction * coefficient * table.d(p, table.task.conveyor), p))
        order.append(following)
        unvisited.remove(following)
        current = following
    check_deadline(deadline)
    return _result(table, name, tuple(order), coefficient=coefficient if direction else 0.0)


def _exhaustive(table: DistanceTable, deadline: float | None) -> AlgorithmResult:
    best_order, best_distance, evaluated = None, inf, 0
    try:
        for candidate in permutations(sorted(table.task.internal)):
            check_deadline(deadline)
            distance = _cost(table, candidate)
            evaluated += 1
            if distance < best_distance:
                best_order, best_distance = candidate, distance
        check_deadline(deadline)
    except DeadlineExceeded:
        return _result(table, "exhaustive", best_order, status="timeout",
                       termination="deadline", evaluated_permutations=evaluated)
    return _result(table, "exhaustive", best_order, optimal=True, evaluated_permutations=evaluated)


def _subset_dp(table: DistanceTable, limits: Limits,
               deadline: float | None) -> AlgorithmResult:
    points = tuple(sorted(table.task.internal))
    n = len(points)
    if n == 0:
        return _result(table, "dp", (), optimal=True, dp_buffer_bytes=0)
    cells = n * (1 << n)
    buffer_bytes = cells * (array("d").itemsize + array("i").itemsize)
    if buffer_bytes > limits.dp_memory_bytes:
        return _result(table, "dp", None, status="resource_limit", termination="dp_memory_estimate",
                       dp_buffer_bytes=buffer_bytes)
    check_deadline(deadline)
    try:
        costs, parents = array("d", [inf]) * cells, array("i", [-1]) * cells
    except (MemoryError, OverflowError):
        return _result(table, "dp", None, status="resource_limit", termination="allocation_failed",
                       dp_buffer_bytes=buffer_bytes)
    for j, point in enumerate(points):
        costs[(1 << j) * n + j] = table.d(table.task.start, point)
    for mask in range(1, 1 << n):
        check_deadline(deadline)
        for j in range(n):
            if not mask & (1 << j):
                continue
            previous_mask = mask ^ (1 << j)
            if previous_mask == 0:
                continue
            remaining, best, parent = previous_mask, inf, -1
            while remaining:
                bit = remaining & -remaining
                i = bit.bit_length() - 1
                candidate = costs[previous_mask * n + i] + table.d(points[i], points[j])
                if candidate < best:
                    best, parent = candidate, i
                remaining ^= bit
            costs[mask * n + j], parents[mask * n + j] = best, parent
    check_deadline(deadline)
    full = (1 << n) - 1
    last = min(range(n), key=lambda j: (costs[full * n + j] + table.d(points[j], table.task.conveyor), j))
    order, mask = [], full
    while last != -1:
        order.append(points[last])
        previous = parents[mask * n + last]
        mask ^= 1 << last
        last = previous
    check_deadline(deadline)
    return _result(table, "dp", tuple(reversed(order)), optimal=True, dp_buffer_bytes=buffer_bytes)


def two_opt(table: DistanceTable, initial: AlgorithmResult, *,
            max_evaluations: int = 10_000, deadline: float | None = None,
            epsilon: float = 1e-9) -> AlgorithmResult:
    """무방향 거리 전용. 첫 개선 후 다시 탐색하며 최선의 유효 경로를 유지한다."""
    if initial.order is None:
        raise InputError("2-opt에는 유효한 초기 방문 순서가 필요합니다.")
    if (isinstance(max_evaluations, bool) or not isinstance(max_evaluations, int)
            or max_evaluations < 0 or not isfinite(epsilon) or epsilon < 0):
        raise InputError("2-opt 한도·허용 오차가 잘못되었습니다.")
    order = list(table.validate_order(initial.order))
    initial_distance = distance = _cost(table, order)
    evaluated, improvements, status, reason = 0, 0, "completed", "local_optimum"
    try:
        while True:
            check_deadline(deadline)
            improved = False
            for i in range(len(order) - 1):
                for j in range(i + 1, len(order)):
                    check_deadline(deadline)
                    if evaluated >= max_evaluations:
                        reason = "evaluation_limit"
                        break
                    before = table.task.start if i == 0 else order[i - 1]
                    after = table.task.conveyor if j == len(order) - 1 else order[j + 1]
                    delta = (table.d(before, order[j]) + table.d(order[i], after)
                             - table.d(before, order[i]) - table.d(order[j], after))
                    evaluated += 1
                    if delta < -epsilon:
                        candidate = order[:i] + list(reversed(order[i:j + 1])) + order[j + 1:]
                        candidate_distance = _cost(table, candidate)
                        if candidate_distance < distance - epsilon:
                            order, distance = candidate, candidate_distance
                            improvements += 1
                            improved = True
                            break
                if improved or reason == "evaluation_limit":
                    break
            if not improved:
                break
    except DeadlineExceeded:
        status, reason = "timeout", "deadline"
    return _result(table, initial.algorithm + "+2opt", tuple(order), status=status,
                   termination=reason, initial_distance=initial_distance,
                   evaluated_moves=evaluated, accepted_moves=improvements,
                   initial_settings=initial.details)


def solve(table: DistanceTable, algorithm: str, *, coefficient: float = 1.0,
          limits: Limits | None = None, deadline: float | None = None) -> AlgorithmResult:
    """후보 하나만 실행한다. 대체 경로 반환은 run_request가 별도로 기록한다."""
    if algorithm not in ALGORITHMS:
        raise InputError(f"알 수 없는 알고리즘: {algorithm}")
    if (isinstance(coefficient, bool) or not isinstance(coefficient, (int, float))
            or not isfinite(coefficient) or coefficient < 0):
        raise InputError("Conveyor-Aware 계수는 유한한 비음수여야 합니다.")
    limits = limits or Limits()
    started = perf_counter()
    base = algorithm.removesuffix("+2opt")
    # S/C에서 충족되는 요청을 제외한 실제 순열 차원에 상한을 적용한다.
    n = len(table.task.internal)
    result = None
    try:
        check_deadline(deadline)
        if base == "exhaustive" and n > limits.exhaustive_n:
            result = _result(table, base, None, status="resource_limit", termination="exhaustive_size")
        elif base == "dp" and n > limits.dp_n:
            result = _result(table, base, None, status="resource_limit", termination="dp_size")
        elif base == "given":
            result = _result(table, base, table.task.internal)
        elif base == "exhaustive":
            result = _exhaustive(table, deadline)
        elif base == "dp":
            result = _subset_dp(table, limits, deadline)
        else:
            result = _greedy(table, base, coefficient, deadline)
        if algorithm.endswith("+2opt") and result.status == "completed":
            result = two_opt(table, result, max_evaluations=limits.two_opt_evaluations, deadline=deadline)
    except DeadlineExceeded:
        result = _result(table, algorithm, None, status="timeout", termination="deadline")
    return replace(result, algorithm=algorithm, elapsed_seconds=perf_counter() - started)
