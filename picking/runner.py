"""수동으로 지정한 알고리즘의 실행과 NN 안전 경로 반환. 선택기는 아니다."""

from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from typing import Iterable

from .algorithms import ALGORITHMS, AlgorithmResult, Limits, solve
from .distances import DeadlineExceeded, Task, UnreachableError, prepare_distances
from .graph import Graph, InputError, Node


@dataclass(frozen=True)
class RequestResult:
    requested_algorithm: str
    status: str
    requested_result: AlgorithmResult | None
    returned_algorithm: str | None
    order: tuple[Node, ...] | None
    path: tuple[Node, ...] | None
    distance: float | None
    optimal: bool
    fallback_used: bool
    timings: dict[str, float]
    budget_seconds: float
    budget_exceeded: bool
    message: str = ""


def run_request(graph: Graph, start: Node, required: Iterable[Node], algorithm: str = "nn", *,
                budget_seconds: float = 2.0, coefficient: float = 1.0,
                limits: Limits | None = None) -> RequestResult:
    """NN 선확보 후 남은 예산으로 지정 후보를 실행한다.

    전처리부터 경로 검증까지 총시간에 포함한다. 협력적 시간 검사이므로
    엄격한 실시간 보장은 하지 않으며 초과 여부를 실제 총시간으로 보고한다.
    """
    started = perf_counter()
    timings = {k: 0.0 for k in ("validation", "preprocessing", "nn_fallback", "search", "reconstruction")}
    requested = returned = None
    order = path = distance = None
    optimal = fallback = False
    status, message = "completed", ""
    stage, stage_started = "validation", started
    try:
        if (isinstance(budget_seconds, bool) or not isinstance(budget_seconds, (int, float))
                or not isfinite(budget_seconds) or budget_seconds <= 0):
            raise InputError("전체 계산 예산은 유한한 양수 초여야 합니다.")
        if algorithm not in ALGORITHMS:
            raise InputError(f"알 수 없는 알고리즘: {algorithm}")
        if (isinstance(coefficient, bool) or not isinstance(coefficient, (int, float))
                or not isfinite(coefficient) or coefficient < 0):
            raise InputError("계수는 유한한 비음수여야 합니다.")
        limits = limits or Limits()
        deadline = started + budget_seconds
        task = Task.create(graph, start, required)
        timings[stage] = perf_counter() - stage_started
        stage, stage_started = "preprocessing", perf_counter()
        table = prepare_distances(graph, task, deadline)
        timings[stage] = perf_counter() - stage_started
        stage, stage_started = "nn_fallback", perf_counter()
        baseline = solve(table, "nn", limits=limits, deadline=deadline)
        timings[stage] = perf_counter() - stage_started
        if baseline.order is None:
            raise DeadlineExceeded("NN 경로 확보 전에 시간 한도에 도달했습니다.")
        stage, stage_started = "search", perf_counter()
        requested = baseline if algorithm == "nn" else solve(
            table, algorithm, coefficient=coefficient, limits=limits, deadline=deadline)
        timings[stage] = perf_counter() - stage_started
        status = requested.status
        # 완료된 후보는 그대로 반환한다. 중단된 후보는 NN과 비교해 더 짧은 유효 경로를 반환한다.
        chosen = requested
        if requested.status != "completed":
            if requested.distance is None or baseline.distance <= requested.distance:
                chosen, fallback = baseline, True
        returned, order, distance = chosen.algorithm, chosen.order, chosen.distance
        optimal = requested.optimal and chosen is requested
        stage, stage_started = "reconstruction", perf_counter()
        path = table.reconstruct(order)
        table.validate_path(order, path, distance)
        timings[stage] = perf_counter() - stage_started
        if perf_counter() >= deadline:
            status, optimal = "timeout", False
            message = "전체 예산을 넘겼습니다. 확보된 유효 경로를 반환했습니다."
        elif status != "completed":
            message = "요청 후보가 제한으로 중단되었습니다. 반환 경로의 알고리즘을 확인하세요."
    except InputError as exc:
        status, message = ("invalid_input" if stage == "validation" else "error"), str(exc)
    except UnreachableError as exc:
        status, message = "infeasible", str(exc)
    except DeadlineExceeded as exc:
        status, message = "timeout", str(exc)
    except MemoryError:
        status, message = "resource_limit", "메모리 할당에 실패했습니다."
    except Exception as exc:
        status, message = "error", f"{type(exc).__name__}: {exc}"
    if status in ("invalid_input", "infeasible", "error"):
        returned = order = path = distance = None
        optimal = fallback = False
    timings[stage] = perf_counter() - stage_started
    timings["total"] = perf_counter() - started
    valid_budget = (isinstance(budget_seconds, (int, float)) and not isinstance(budget_seconds, bool)
                    and isfinite(budget_seconds) and budget_seconds > 0)
    return RequestResult(algorithm, status, requested, returned, order, path, distance,
                         optimal, fallback, timings, budget_seconds,
                         valid_budget and timings["total"] > budget_seconds, message)
