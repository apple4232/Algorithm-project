"""작업 검증, Dijkstra 공통 전처리, 실제 통로 경로 복원."""

from collections import Counter
from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf, isclose, isfinite
from time import perf_counter
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from .graph import Graph, InputError, Node, _node


class UnreachableError(ValueError):
    """출발점에서 필수 위치 또는 컨베이어에 도달할 수 없음."""


class DeadlineExceeded(TimeoutError):
    pass


def check_deadline(deadline: float | None) -> None:
    if deadline is not None and perf_counter() >= deadline:
        raise DeadlineExceeded("계산 시간 한도에 도달했습니다.")


@dataclass(frozen=True)
class Task:
    start: Node
    required: tuple[Node, ...]
    quantities: Mapping[Node, int]
    conveyor: Node

    @classmethod
    def create(cls, graph: Graph, start: Node, required: Iterable[Node]) -> "Task":
        start = _node(start)
        requested = tuple(_node(p) for p in required)
        if start not in graph.adjacency or any(p not in graph.adjacency for p in requested):
            raise InputError("출발점과 필수 위치는 기존 지도 노드여야 합니다.")
        counts = Counter(requested)
        return cls(start, tuple(counts), MappingProxyType(dict(counts)), graph.conveyor)

    @property
    def n(self) -> int:
        return len(self.required)

    @property
    def internal(self) -> tuple[Node, ...]:
        """S/C의 요청은 끝점에서 충족하므로 내부 순서에서는 제외한다."""
        return tuple(p for p in self.required if p not in (self.start, self.conveyor))


@dataclass(frozen=True)
class DistanceTable:
    graph: Graph
    task: Task
    matrix: Mapping[Node, Mapping[Node, float]]
    predecessors: Mapping[Node, Mapping[Node, Node]]

    def d(self, u: Node, v: Node) -> float:
        return self.matrix[u][v]

    def leg(self, u: Node, v: Node) -> tuple[Node, ...]:
        self.d(u, v)  # 전처리된 위치만 허용한다.
        path = [v]
        while path[-1] != u:
            path.append(self.predecessors[u][path[-1]])
        return tuple(reversed(path))

    def validate_order(self, order: Iterable[Node]) -> tuple[Node, ...]:
        order = tuple(order)
        if len(order) != len(self.task.internal) or set(order) != set(self.task.internal):
            raise InputError("방문 순서는 내부 필수 위치를 중복 없이 포함해야 합니다.")
        return order

    def route_distance(self, order: Iterable[Node]) -> float:
        order = self.validate_order(order)
        stops = (self.task.start, *order, self.task.conveyor)
        return sum(self.d(u, v) for u, v in zip(stops, stops[1:]))

    def reconstruct(self, order: Iterable[Node]) -> tuple[Node, ...]:
        order = self.validate_order(order)
        stops = (self.task.start, *order, self.task.conveyor)
        path = [stops[0]]
        for u, v in zip(stops, stops[1:]):
            path.extend(self.leg(u, v)[1:])
        return tuple(path)

    def validate_path(self, order: Iterable[Node], path: Iterable[Node],
                      reported_distance: float) -> None:
        order, path = self.validate_order(order), tuple(path)
        if not path or path[0] != self.task.start or path[-1] != self.task.conveyor:
            raise InputError("실제 경로의 시작 또는 끝이 잘못되었습니다.")
        if not set(self.task.required).issubset(path):
            raise InputError("실제 경로가 필수 위치를 빠뜨렸습니다.")
        try:
            length = sum(self.graph.adjacency[u][v] for u, v in zip(path, path[1:]))
        except KeyError as exc:
            raise InputError("실제 경로에 없는 통로가 포함되었습니다.") from exc
        if not isfinite(reported_distance) or not (
            isclose(length, reported_distance, rel_tol=1e-12, abs_tol=1e-9)
            and isclose(length, self.route_distance(order), rel_tol=1e-12, abs_tol=1e-9)
        ):
            raise InputError("보고 거리, 방문 순서 거리, 실제 통로 길이가 다릅니다.")


def dijkstra(graph: Graph, source: Node, deadline: float | None = None,
             clock_check: Callable[[float | None], None] = check_deadline
             ) -> tuple[dict[Node, float], dict[Node, Node]]:
    if source not in graph.adjacency:
        raise InputError("출발 노드가 지도에 없습니다.")
    distances, previous = {source: 0.0}, {}
    queue = [(0.0, source)]
    while queue:
        clock_check(deadline)
        distance, u = heappop(queue)
        if distance != distances[u]:
            continue
        for v, weight in graph.adjacency[u].items():
            candidate = distance + weight
            if candidate < distances.get(v, inf):
                distances[v], previous[v] = candidate, u
                heappush(queue, (candidate, v))
    return distances, previous


def prepare_distances(graph: Graph, task: Task,
                      deadline: float | None = None) -> DistanceTable:
    if task.conveyor != graph.conveyor:
        raise InputError("작업의 컨베이어가 환경과 다릅니다.")
    locations = tuple(sorted({task.start, task.conveyor, *task.required}))
    matrix, predecessors = {}, {}
    for source in locations:
        distances, previous = dijkstra(graph, source, deadline)
        if any(target not in distances for target in locations):
            raise UnreachableError("S, 필수 위치, C가 같은 연결 요소에 있어야 합니다.")
        matrix[source] = MappingProxyType({p: distances[p] for p in locations})
        predecessors[source] = MappingProxyType(previous)
    return DistanceTable(graph, task, MappingProxyType(matrix), MappingProxyType(predecessors))
