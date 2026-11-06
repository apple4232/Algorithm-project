from dataclasses import replace
from math import inf
from random import Random
import unittest
from unittest.mock import patch

from picking import InputError, Task, build_warehouse, make_graph, prepare_distances
from picking.algorithms import ALGORITHMS, Limits, solve, two_opt
from picking.runner import run_request


def line_table(start=8, required=(1, 9), conveyor=0):
    xs = sorted({start, conveyor, *required})
    nodes = [(x, 0) for x in xs]
    graph = make_graph(nodes, [(u, v, v[0] - u[0]) for u, v in zip(nodes, nodes[1:])], (conveyor, 0))
    return prepare_distances(graph, Task.create(graph, (start, 0), [(x, 0) for x in required]))


class AlgorithmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = build_warehouse()

    def test_counterexample_and_zero_coefficient(self):
        table = line_table()
        nn, plus, minus = (solve(table, name) for name in ("nn", "ca-plus", "ca-minus"))
        self.assertEqual(nn.distance, 10)
        self.assertEqual(plus.distance, 24)
        self.assertEqual(minus.distance, 10)
        for name in ("ca-plus", "ca-minus"):
            self.assertEqual(solve(table, name, coefficient=0).order, nn.order)
        improved = solve(table, "ca-plus+2opt")
        self.assertEqual(improved.distance, 10)
        self.assertEqual(improved.details["initial_distance"], 24)

    def test_exact_agreement_and_all_candidates_on_seeded_small_tasks(self):
        rng = Random(42)
        pool = sorted(self.graph.picking_locations)
        for n in range(8):
            for repetition in range(3):
                with self.subTest(n=n, repetition=repetition):
                    task = Task.create(self.graph, [(0, 0), (16, 20), (0, 40)][repetition], rng.sample(pool, n))
                    table = prepare_distances(self.graph, task)
                    exhaustive, dp = solve(table, "exhaustive"), solve(table, "dp")
                    self.assertTrue(exhaustive.optimal)
                    self.assertTrue(dp.optimal)
                    self.assertEqual(exhaustive.distance, dp.distance)
                    for algorithm in ALGORITHMS:
                        result = solve(table, algorithm)
                        self.assertEqual(result.status, "completed")
                        self.assertGreaterEqual(result.distance, dp.distance)
                        table.validate_path(result.order, table.reconstruct(result.order), result.distance)
                        if algorithm.endswith("+2opt"):
                            self.assertLessEqual(result.distance, result.details["initial_distance"])

    def test_zero_one_duplicates_and_endpoint_requests(self):
        cases = [((0, 0), []), ((36, 0), []), ((0, 0), [(4, 2)]),
                 ((0, 0), [(0, 0), (4, 2), (4, 2), (36, 0)]),
                 ((36, 0), [(36, 0), (4, 2)]), ((0, 0), [(0, 0), (36, 0)])]
        for start, required in cases:
            table = prepare_distances(self.graph, Task.create(self.graph, start, required))
            optimum = solve(table, "dp").distance
            for name in ALGORITHMS:
                result = solve(table, name)
                self.assertEqual(result.distance, optimum)
                table.validate_path(result.order, table.reconstruct(result.order), result.distance)

    def test_tie_rule_reproducibility(self):
        # S에서 같은 거리인 두 위치. 입력 순서와 무관하게 ID로 동점을 처리한다.
        a, b, s, c = (0, 0), (2, 0), (1, 0), (1, 1)
        g = make_graph([a, b, s, c], [(s, a, 1), (s, b, 1), (s, c, 1)], c)
        for required in ([b, a], [a, b]):
            t = prepare_distances(g, Task.create(g, s, required))
            self.assertEqual(solve(t, "nn").order[0], a)
            for name in ("ca-plus", "ca-minus"):
                self.assertEqual(solve(t, name, coefficient=0).order, solve(t, "nn").order)
        self.assertEqual(solve(t, "given").order, (a, b))

    def test_two_opt_delta_matches_full_reversal(self):
        t = prepare_distances(self.graph, Task.create(self.graph, (0, 0), [(0, 38), (32, 6), (8, 14), (36, 36)]))
        order, original = t.task.internal, t.route_distance(t.task.internal)
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                before = t.task.start if i == 0 else order[i - 1]
                after = t.task.conveyor if j == len(order) - 1 else order[j + 1]
                delta = t.d(before, order[j]) + t.d(order[i], after) - t.d(before, order[i]) - t.d(order[j], after)
                candidate = order[:i] + tuple(reversed(order[i:j + 1])) + order[j + 1:]
                self.assertEqual(t.route_distance(candidate) - original, delta)

    def test_two_opt_limits_preserve_feasibility(self):
        t = line_table()
        original = solve(t, "ca-plus")
        limited = two_opt(t, original, max_evaluations=0)
        self.assertEqual(limited.order, original.order)
        self.assertEqual(limited.termination, "evaluation_limit")
        timed = two_opt(t, original, deadline=0)
        self.assertEqual(timed.status, "timeout")
        self.assertEqual(timed.distance, original.distance)
        self.assertFalse(timed.optimal)

    def test_exact_size_memory_and_time_limits(self):
        t = line_table()
        for name in ("exhaustive", "dp"):
            result = solve(t, name, limits=Limits(exhaustive_n=1, dp_n=1))
            self.assertEqual(result.status, "resource_limit")
            self.assertFalse(result.optimal)
            self.assertIsNone(result.order)
            timed = solve(t, name, deadline=0)
            self.assertEqual(timed.status, "timeout")
            self.assertFalse(timed.optimal)
        small_memory = solve(t, "dp", limits=Limits(dp_memory_bytes=1))
        self.assertEqual(small_memory.termination, "dp_memory_estimate")

    def test_interrupted_exhaustive_incumbent_is_not_optimal(self):
        t = line_table()
        # solve 진입, 첫 순열, 다음 순열 검사 시각을 순서대로 제어한다.
        with patch("picking.distances.perf_counter", side_effect=[0, 0, 2]):
            result = solve(t, "exhaustive", deadline=1)
        self.assertEqual(result.status, "timeout")
        self.assertFalse(result.optimal)
        self.assertIsNotNone(result.order)
        t.validate_path(result.order, t.reconstruct(result.order), result.distance)

    def test_invalid_algorithm_settings(self):
        for coefficient in (-1, inf, float("nan"), True):
            with self.assertRaises(InputError):
                solve(line_table(), "ca-plus", coefficient=coefficient)
        with self.assertRaises(InputError):
            solve(line_table(), "missing")
        with self.assertRaises(InputError):
            Limits(two_opt_evaluations=-1)

    def test_interrupted_dp_is_not_optimal(self):
        with patch("picking.distances.perf_counter", side_effect=[0, 0, 2]):
            result = solve(line_table(), "dp", deadline=1)
        self.assertEqual(result.status, "timeout")
        self.assertFalse(result.optimal)
        self.assertIsNone(result.order)

    def test_medium_dp_against_known_line_optimum(self):
        table = line_table(start=0, required=tuple(range(1, 16)), conveyor=16)
        result = solve(table, "dp")
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.optimal)
        self.assertEqual(result.distance, 16)
        table.validate_path(result.order, table.reconstruct(result.order), result.distance)

    def test_large_heuristics_remain_feasible(self):
        points = Random(2026).sample(sorted(self.graph.picking_locations), 50)
        table = prepare_distances(self.graph, Task.create(self.graph, (16, 20), points))
        for name in ("nn", "ca-plus", "ca-minus", "nn+2opt", "ca-plus+2opt", "ca-minus+2opt"):
            result = solve(table, name)
            self.assertEqual(result.status, "completed")
            self.assertFalse(result.optimal)
            table.validate_path(result.order, table.reconstruct(result.order), result.distance)
            if name.endswith("+2opt"):
                self.assertLessEqual(result.distance, result.details["initial_distance"])

    def test_given_order_keeps_first_occurrence(self):
        table = line_table(required=(9, 1, 9, 0, 8))
        self.assertEqual(solve(table, "given").order, ((9, 0), (1, 0)))


class RunnerTests(unittest.TestCase):
    def test_all_candidates_share_valid_route_contract(self):
        for name in ALGORITHMS:
            result = run_request(build_warehouse(), (0, 0), [(4, 2), (32, 38), (4, 2)], name)
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.returned_algorithm, name)
            self.assertFalse(result.fallback_used)
            self.assertIsNotNone(result.path)
            self.assertEqual(result.path[0], (0, 0))
            self.assertEqual(result.path[-1], (36, 0))
            self.assertGreaterEqual(result.timings["total"], sum(v for k, v in result.timings.items() if k != "total"))

    def test_resource_limit_returns_nn_and_preserves_requested_status(self):
        result = run_request(build_warehouse(), (0, 0), [(4, 2), (8, 4)], "dp", limits=Limits(dp_n=1))
        self.assertEqual(result.status, "resource_limit")
        self.assertEqual(result.requested_result.algorithm, "dp")
        self.assertEqual(result.requested_result.status, "resource_limit")
        self.assertEqual(result.returned_algorithm, "nn")
        self.assertTrue(result.fallback_used)
        self.assertFalse(result.optimal)
        self.assertIsNotNone(result.path)

    def test_timeout_fallback_with_controlled_candidate(self):
        import picking.runner as runner
        original = runner.solve

        def interrupted(table, algorithm, **kwargs):
            if algorithm == "dp":
                return replace(original(table, "nn"), algorithm="dp", status="timeout", optimal=False, termination="deadline")
            return original(table, algorithm, **kwargs)

        with patch("picking.runner.solve", side_effect=interrupted):
            result = run_request(build_warehouse(), (0, 0), [(4, 2)], "dp")
        self.assertEqual(result.status, "timeout")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.returned_algorithm, "nn")
        self.assertFalse(result.optimal)

    def test_preprocessing_timeout_without_route(self):
        result = run_request(build_warehouse(), (0, 0), [(4, 2)], "dp", budget_seconds=1e-12)
        self.assertEqual(result.status, "timeout")
        self.assertIsNone(result.path)
        self.assertTrue(result.budget_exceeded)

    def test_input_and_connectivity_errors(self):
        g = build_warehouse()
        self.assertEqual(run_request(g, (1, 1), [], "nn").status, "invalid_input")
        self.assertEqual(run_request(g, (0, 0), [], "bad").status, "invalid_input")
        self.assertEqual(run_request(g, (0, 0), [], budget_seconds=-1).status, "invalid_input")
        disconnected = make_graph([(0, 0), (1, 0)], [], (1, 0))
        self.assertEqual(run_request(disconnected, (0, 0), []).status, "infeasible")

    def test_internal_failure_does_not_return_verified_optimum(self):
        with patch("picking.distances.DistanceTable.validate_path", side_effect=InputError("경로 검증 실패")):
            result = run_request(build_warehouse(), (0, 0), [(4, 2)], "dp")
        self.assertEqual(result.status, "error")
        self.assertFalse(result.optimal)
        self.assertIsNone(result.path)
        self.assertIsNone(result.distance)


if __name__ == "__main__":
    unittest.main()
