"""고정 창고 및 검증용 무방향 통로 그래프."""

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Iterable, Mapping

Node = tuple[float, float]


class InputError(ValueError):
    """잘못된 지도·작업·설정."""


def _node(value: Node) -> Node:
    if (not isinstance(value, tuple) or len(value) != 2
            or any(isinstance(x, bool) or not isinstance(x, (int, float))
                   or not isfinite(x) for x in value)):
        raise InputError("노드는 유한한 숫자 두 개의 좌표 튜플이어야 합니다.")
    return value


@dataclass(frozen=True)
class Graph:
    adjacency: Mapping[Node, Mapping[Node, float]]
    picking_locations: frozenset[Node]
    conveyor: Node
    version: str

    @property
    def edge_count(self) -> int:
        return sum(map(len, self.adjacency.values())) // 2


def make_graph(nodes: Iterable[Node], edges: Iterable[tuple[Node, Node, float]],
               conveyor: Node, picking_locations: Iterable[Node] = (),
               version: str = "custom-v1") -> Graph:
    """간선은 실제 통행 가능한 연결이라는 호출자 선언이다.

    고정 창고의 선반 회피는 build_warehouse가 보장한다. 사용자 정의
    지도는 기하적 선반 정보가 없으므로 간선의 물리적 의미까지 추론하지 않는다.
    """
    adjacency: dict[Node, dict[Node, float]] = {_node(n): {} for n in nodes}
    if not adjacency or _node(conveyor) not in adjacency:
        raise InputError("컨베이어가 지도 노드에 있어야 합니다.")
    for u, v, weight in edges:
        _node(u)
        _node(v)
        if u not in adjacency or v not in adjacency or u == v:
            raise InputError("간선의 서로 다른 두 끝점이 지도에 있어야 합니다.")
        if (isinstance(weight, bool) or not isinstance(weight, (int, float))
                or not isfinite(weight) or weight < 0):
            raise InputError("간선 길이는 유한한 비음수여야 합니다.")
        weight = float(weight)
        if v in adjacency[u] and adjacency[u][v] != weight:
            raise InputError("동일 간선의 길이가 중복 정의와 다릅니다.")
        adjacency[u][v] = adjacency[v][u] = weight
    locations = frozenset(_node(p) for p in picking_locations)
    if not locations.issubset(adjacency):
        raise InputError("피킹 위치가 지도에 없습니다.")
    frozen = MappingProxyType({n: MappingProxyType(dict(sorted(neighbors.items())))
                               for n, neighbors in sorted(adjacency.items())})
    return Graph(frozen, locations, conveyor, version)


def build_warehouse() -> Graph:
    """10개 세로 통로, 3개 가로 통로, m 단위 합성 환경."""
    nodes = [(x, y) for x in range(0, 37, 4) for y in range(0, 41, 2)]
    edges = [((x, y), (x, y + 2), 2)
             for x in range(0, 37, 4) for y in range(0, 40, 2)]
    edges += [((x, y), (x + 4, y), 4)
              for y in (0, 20, 40) for x in range(0, 36, 4)]
    locations = [n for n in nodes if n[1] not in (0, 20, 40)]
    return make_graph(nodes, edges, (36, 0), locations, "warehouse-10x40-v1")
