import unittest
from copy import deepcopy

from experiments.analysis import select, summarize, train
from experiments.__main__ import evaluate
from analysis.views import views
from analysis.policies import analyze
from experiments.benchmark import run
from experiments.workloads import features, generate
from picking.distances import Task, prepare_distances
from picking.graph import build_warehouse, make_graph


class ExperimentTests(unittest.TestCase):
    def test_features_hand_calculation_and_endpoints(self):
        graph = make_graph([(0, 0), (1, 0), (3, 0)],
                           [((0, 0), (1, 0), 1), ((1, 0), (3, 0), 2)], (3, 0))
        table = prepare_distances(graph, Task.create(graph, (0, 0), [(0, 0), (1, 0), (1, 0)]))
        result = features(table, 'example')
        self.assertEqual((result['n'], result['internal_n']), (2, 1))
        self.assertEqual((result['dispersion'], result['start_mean'], result['conveyor_mean']), (1, .5, 2.5))
        empty = features(prepare_distances(graph, Task.create(graph, (0, 0), [])), 'empty')
        self.assertEqual((empty['dispersion'], empty['start_mean'], empty['conveyor_mean']), (0, 0, 0))

    def test_reproducible_groups_pairing_and_pool_validation(self):
        graph = build_warehouse()
        tasks = generate(graph, [5], range(4), paired=True)
        self.assertEqual(tasks, generate(graph, [5], range(4), paired=True))
        for task in tasks:
            self.assertEqual(len(set(task['required'])), 5)
            self.assertTrue(set(task['required']) <= graph.picking_locations)
        for seed in range(4):
            variants = [t for t in tasks if t['seed'] == seed and t['pattern'] == 'clustered']
            self.assertEqual(len({tuple(t['required']) for t in variants}), 1)
            self.assertEqual(len({t['split'] for t in variants}), 1)
            far = next(t for t in tasks if t['seed'] == seed and t['pattern'] == 'paired-far')
            near = next(t for t in tasks if t['seed'] == seed and t['pattern'] == 'paired-near')
            self.assertEqual([(36-x, y) for x, y in far['required']], near['required'])
        with self.assertRaises(ValueError):
            generate(graph, [55], [0])

    def test_benchmark_records_candidate_failure_and_request_fallback(self):
        task = generate(build_warehouse(), [8], [0])[0]
        candidate = list(run([task], 1, 1, 'candidate'))
        dp = next(r for r in candidate if r['algorithm'] == 'exhaustive')
        self.assertEqual(dp['result']['status'], 'resource_limit')
        request = list(run([task], 1, 1, 'request'))
        fallback = next(r for r in request if r['algorithm'] == 'exhaustive')['result']
        self.assertEqual(fallback['status'], 'resource_limit')
        self.assertEqual(fallback['returned_algorithm'], 'nn')
        self.assertTrue(fallback['fallback_used'])
        self.assertEqual(summarize(candidate)['exhaustive']['feasible_completed'], 0)

    def test_train_uses_only_dev_and_selects_saved_rule(self):
        task = generate(build_warehouse(), [3], [0])[0]
        rows = list(run([task], 1, 1, 'request'))
        model = train(rows)
        self.assertIn(select(model['rules']['count'], rows[0]['features']), {r['algorithm'] for r in rows})
        bad = deepcopy(rows)
        bad[0]['task']['split'] = 'eval'
        with self.assertRaises(ValueError):
            train(bad)

    def test_evaluation_rejects_training_group_and_reports_real_requests(self):
        tasks = generate(build_warehouse(), [3], [0, 1])
        dev = next(t for t in tasks if t['split'] == 'dev')
        held = next(t for t in tasks if t['split'] == 'eval')
        training = list(run([dev], 1, 1, 'request'))
        model = train(training)
        policies = list(evaluate([held], model))
        self.assertEqual(len(policies), 4)
        self.assertTrue(all(p['result']['distance'] is not None for p in policies))
        references = list(run([held], 1, 1, 'request'))
        report = analyze(policies, references)
        self.assertEqual(report['policies']['fixed']['completed_within_budget'], 1)
        self.assertEqual(report['policies']['fixed']['fixed_minus_policy_m']['mean_difference_m'], 0)
        bad = deepcopy(dev)
        bad['split'] = 'eval'
        with self.assertRaises(ValueError):
            list(evaluate([bad], model))
        candidate = list(run([held], 1, 1, 'candidate'))
        self.assertEqual(views(candidate)['A_exact_agreement']['distance_mismatches'], 0)

    def test_summary_gap_and_failed_attempt(self):
        task = {'id': '1', 'group': 'g'}
        def row(name, distance, status='completed', optimal=False):
            return {'task': task, 'features': {'n': 2, 'pattern': 'example'}, 'algorithm': name, 'result': {'status': status, 'distance': distance,
                    'optimal': optimal, 'elapsed_seconds': .1}}
        report = summarize([row('dp', 10, optimal=True), row('nn', 12), row('bad', None, 'timeout')])
        self.assertEqual(report['nn']['mean_gap_percent'], 20)
        self.assertEqual(report['nn']['mean_nn_improvement_percent'], 0)
        self.assertEqual(report['bad']['statuses'], {'timeout': 1})


if __name__ == '__main__':
    unittest.main()
