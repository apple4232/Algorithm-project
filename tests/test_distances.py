import math
import unittest

from picking import InputError, Task, UnreachableError, build_warehouse, make_graph, prepare_distances
from picking.distances import DeadlineExceeded, dijkstra


class DistanceTests(unittest.TestCase):
    def setUp(self):
        self.graph = build_warehouse()

    def test_structure_and_no_shelf_crossing(self):
        g = self.graph
        self.assertEqual((len(g.adjacency), g.edge_count, len(g.picking_locations)), (210, 227, 180))
        self.assertEqual(len(dijkstra(g, (0, 0))[0]), 210)
        for u, neighbors in g.adjacency.items():
            for v, weight in neighbors.items():
                self.assertEqual(weight, abs(u[0] - v[0]) + abs(u[1] - v[1]))
                self.assertEqual(g.adjacency[v][u], weight)
                if u[0] != v[0]:
                    self.assertEqual(u[1], v[1])
                    self.assertIn(u[1], (0, 20, 40))

    def test_hand_calculated_detour_and_reconstruction(self):
        task = Task.create(self.graph, (0, 2), [(4, 2)])
        table = prepare_distances(self.graph, task)
        self.assertEqual(table.d((0, 2), (4, 2)), 8)  # 직선 4m가 아니라 앞 통로 경유
        self.assertEqual(table.d((4, 2), (36, 0)), 34)
        self.assertEqual(table.route_distance(task.internal), 42)
        table.validate_path(task.internal, table.reconstruct(task.internal), 42)

    def test_symmetry_and_zero_diagonal(self):
        t = prepare_distances(self.graph, Task.create(self.graph, (16, 20), [(0, 38), (36, 2)]))
        for u in t.matrix:
            self.assertEqual(t.d(u, u), 0)
            for v in t.matrix:
                self.assertEqual(t.d(u, v), t.d(v, u))

    def test_duplicates_empty_and_endpoints(self):
        task = Task.create(self.graph, (0, 0), [(0, 0), (4, 2), (4, 2), (36, 0)])
        self.assertEqual(task.n, 3)
        self.assertEqual(task.quantities[(4, 2)], 2)
        self.assertEqual(task.internal, ((4, 2),))
        for start, expected in [((0, 0), 36), ((36, 0), 0)]:
            table = prepare_distances(self.graph, Task.create(self.graph, start, []))
            table.validate_path((), table.reconstruct(()), expected)

    def test_unreachable(self):
        g = make_graph([(0, 0), (1, 0), (2, 0)], [((0, 0), (1, 0), 1)], (2, 0))
        with self.assertRaises(UnreachableError):
            prepare_distances(g, Task.create(g, (0, 0), []))

    def test_invalid_map_and_locations(self):
        for weight in (-1, math.nan, math.inf):
            with self.assertRaises(InputError):
                make_graph([(0, 0), (1, 0)], [((0, 0), (1, 0), weight)], (1, 0))
        with self.assertRaises(InputError):
            Task.create(self.graph, (1, 1), [])
        with self.assertRaises(InputError):
            Task.create(self.graph, (0, 0), [(1, 1)])
        with self.assertRaises(InputError):
            Task.create(self.graph, (math.nan, 0), [])

    def test_zero_edges_and_early_visit(self):
        nodes = [(0, 0), (1, 0), (2, 0), (3, 0)]
        g = make_graph(nodes, [(nodes[0], nodes[1], 0), (nodes[1], nodes[2], 1),
                               (nodes[2], nodes[3], 1)], nodes[3])
        table = prepare_distances(g, Task.create(g, nodes[0], [nodes[2], nodes[1]]))
        self.assertIn(nodes[1], table.leg(nodes[0], nodes[2]))
        table.validate_path(table.task.internal, table.reconstruct(table.task.internal), 4)

    def test_bad_route_and_deadline(self):
        table = prepare_distances(self.graph, Task.create(self.graph, (0, 0), [(4, 2)]))
        with self.assertRaises(InputError):
            table.reconstruct(())
        with self.assertRaises(InputError):
            table.validate_path(table.task.internal, [(0, 0), (4, 2), (36, 0)], 40)
        with self.assertRaises(DeadlineExceeded):
            prepare_distances(self.graph, table.task, deadline=0)


if __name__ == "__main__":
    unittest.main()
