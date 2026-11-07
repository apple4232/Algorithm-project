# Role B experiments

This document describes the experiment code and the November 6, 2026 exploratory run. It does not describe a real warehouse or establish production budgets. Historical documents 01–07 describe earlier decisions and retain their dated status.

## Reproduction

Run from the repository root with Python 3. No third-party package is required. Output files are created exclusively: choose a fresh directory rather than overwriting an earlier run.

```sh
mkdir -p results/new
python3 -m experiments generate results/new/tasks.jsonl --sizes 3 5 7 8 10 12 15 20 50 --seeds 30 --seed-start 100 --paired
python3 -m experiments benchmark results/new/tasks.jsonl results/new/dev-candidate.jsonl --split dev --mode candidate --budget 0.2 --coefficient 0.5
python3 -m experiments benchmark results/new/tasks.jsonl results/new/dev-request.jsonl --split dev --mode request --budget 0.2 --coefficient 0.5
python3 -m experiments train results/new/dev-request.jsonl results/new/rules.json
python3 -m experiments benchmark results/new/tasks.jsonl results/new/eval-candidate.jsonl --split eval --mode candidate --budget 0.2 --coefficient 0.5
python3 -m experiments benchmark results/new/tasks.jsonl results/new/eval-request.jsonl --split eval --mode request --budget 0.2 --coefficient 0.5
python3 -m experiments evaluate results/new/tasks.jsonl results/new/rules.json results/new/eval-policies.jsonl
python3 -m experiments report results/new/eval-candidate.jsonl results/new/eval-candidate-summary.json
python3 -m experiments report results/new/eval-request.jsonl results/new/eval-request-summary.json
python3 -m experiments report results/new/eval-policies.jsonl results/new/eval-policy-summary.json
python3 -m experiments.plot results/new/eval-candidate-summary.json results/new/eval-candidate.svg
python3 -m analysis.views results/new/eval-candidate.jsonl results/new/eval-views.json
python3 -m analysis.policies results/new/eval-policies.jsonl results/new/eval-request.jsonl results/new/eval-policy-comparison.json
python3 -m analysis.memory_scale results/new/tasks.jsonl results/new/memory-scaling.jsonl
python3 -m unittest discover -s tests
```

`memory` launches as a fresh process per invocation and reports whole-process peak RSS including Python and preprocessing, not peak DP buffers. Its 2-second budget and memory setting are separate from the timing run. Platform interpretation follows Python's `resource` behavior on macOS and Linux. The DP array estimate is recorded separately in the algorithm result.

## Workload and split

The graph is `warehouse-10x40-v1`; the conveyor is (36, 0), and the three starts are (0, 0), (16, 20), and (0, 40). Sizes are distinct requested shelf locations. A seeded generator samples without replacement from sorted shelf coordinates, preserving sampled order for Given Order. Each seed is assigned to exactly one split: even is development and odd is evaluation. Every size, pattern, start, and mirrored variant derived from that seed stays in the same group. Identical item sets are rejected and regenerated with the same seeded generator, without enlarging the pool; exhaustion raises an error.

- Clustered: uniformly sample from three adjacent aisles, whose start aisle is sampled uniformly. The pool has 54 locations.
- Random-Stow-like: uniformly sample from the 180 shelf locations. This does not recreate an operational storage policy.
- Directional: uniformly sample from the rear half (`y >= 22`), 90 locations.
- Paired F: sample from the five leftmost aisles (`x <= 16`) and reflect x about 18 m. The original and reflection preserve pairwise structure but change both conveyor and start distances. Do not interpret the difference as a pure conveyor-distance causal effect.

Each configuration has all three starts. Nine sizes, three base patterns, two matched F variants, three starts, and thirty seeds yield 4,050 tasks: 2,025 development and 2,025 evaluation tasks. The commonly discussed 1,620-task base is the subset with six sizes 3, 5, 7, 10, 20, 50 and the three base patterns; the other three sizes and paired F cases are extra. The 30 seeds are not 30 independent samples per individual start: all three starts and other variants share their seed group.

Feature definitions and n=0/1 conventions are in [workload refinement](03-workload-model-refinement.md). The generator requires positive sizes; the feature function also supports empty tasks. The actual starting and conveyor distances and dispersion are stored alongside the generator label. Pattern is metadata, not a classifier of real orders.

## Pilot choices and limits

The earlier small exploratory pilot used seeds 0–3 and included an inspected evaluation subset; none of those seeds are used in the final data. The coefficient calibration in `results/calibration` uses only even seeds 0 and 2 for candidate measurements at 0, 0.25, 0.5, and 1. On that development pilot CA-minus without 2-opt had its lowest average distance at 0.5 among the nonzero values tested. That is the exploratory common coefficient for both signs in the run, not a claim that it is optimal for every candidate or workload. At 0, both signs reproduce NN, so CA-minus must not be represented as a new distinct policy at that setting.

The 0.2-second per-request budget is an exploratory choice, not an operational SLA or calibrated best value. Candidate-only runs use 0.2 seconds for search after shared preprocessing; request runs give 0.2 seconds to the complete `run_request`. Default size, DP-array and 2-opt guards remain recorded in every measurement. Deadline checks are cooperative, reconstruction may run beyond the budget, and elapsed wall time varies by hardware and load. Each task randomizes candidate order, and results record the machine, Python version, git revision, dirty state, and a SHA-256 of the Python source under `picking/` and `experiments/`. The request runner does not cache distance tables.

## Evaluation and interpretation

Candidate records reuse one distance table and validate every returned path. Request records run preprocessing and NN fallback anew, and retain requested status, actual returned method and fallback separately. A `resource_limit` result with a valid NN fallback is not counted as a completed requested candidate. An interrupted exact method is not an optimum. A completed 2-opt run may have `termination = evaluation_limit`, not `local_optimum`.

Training accepts development-only full-request records at one coefficient and budget. It finds a fixed method and one-split rules using count, four numeric features, and those features plus the synthetic pattern. Up to nine numeric thresholds per feature are tested. A method must complete all training tasks in its branch; score is total distance. Three-fold grouped development cross-validation reports completed-task mean distances and failures; final rules are then fitted to all development groups. Ties prefer the simpler earlier rule or the alphabetically first method. CV scores reuse measured candidate requests and are exploratory, not measured selector latencies.

Evaluation accepts only evaluation groups and refuses a changed code fingerprint. Each policy independently calculates features and selection, then calls `run_request` with the remaining budget; the recorded total includes both feature preparation and the runner's own preparation. This conservative prototype does not yet integrate the feature table with `run_request`. Fixed and count-only policies pay the same feature-extraction overhead for comparable measurement. The fitted training measurements do not include this policy overhead, so borderline policies can fail on evaluation. The UI and production selector integration are separate work.

Reports include attempts, statuses, completed-route median, time median and p90, proven optimality gap, paired NN-relative improvement, group-bootstrap interval for paired distance change, and within-record-set offline regret. All distance summaries state the completed subset through counts; no feasible route is silently attributed to the failed requested method. Gap and regret only exist where a reference is available. For policy summaries, offline regret is against other evaluated policies in the same file, not the best of every algorithm. Plots use completed-task medians; consult the summary for failure counts. Confidence intervals over only 15 final evaluation seed groups are exploratory.

`analysis.views` reports A–H descriptive comparisons, including paired F and H differences. `analysis.policies` compares policies on the same tasks and estimates an offline candidate reference by adding separately measured feature-preparation and selection costs to each complete request. The resulting reference is an approximation because wall times come from separate runs; it is not a proven optimum.

The memory scaling sample measures one development Random-Stow-like task per size, each in a new process; one observation per size is not a distribution of memory usage.
