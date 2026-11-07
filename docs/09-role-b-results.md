# Role B exploratory evaluation

These results describe the synthetic fixed warehouse and the exploratory 0.2-second budget on the recorded machine, not an operational warehouse or a universal algorithm ranking. Reproduction, generation rules, raw data, and limitations are described in [Role B experiments](08-role-b-experiments.md).

## Conditions

The full run contains 4,050 tasks: nine item counts (3, 5, 7, 8, 10, 12, 15, 20, 50), three base patterns plus paired near/far cases, three starts, and 30 seed groups. Even seeds 100–128 provide 2,025 development tasks; odd seeds 101–129 provide 2,025 evaluation tasks. Related starts, patterns and paired cases from a seed stay together. The 15 evaluation seed groups, not the 2,025 tasks, are the independent resampling units. No evaluation item set matched an item set in the earlier pilot or coefficient calibration data.

The common CA coefficient 0.5 was selected from a small development-only pilot as described in the methodology. Limits and environment are recorded per execution. The rules were written to `results/full/rules.json` before evaluation. On development data, the fixed choice was NN+2-opt. The count, numeric-feature and numeric-plus-pattern rules all selected DP for `n <= 13.5` and NN+2-opt otherwise. Numeric thresholds were fitted from the development sample; 13.5 is not a universal boundary.

## Held-out policy comparison

| Policy | Tasks completed within budget | Median route distance | Median total policy time | Mean paired distance saved versus fixed NN+2-opt |
|---|---:|---:|---:|---:|
| Fixed NN+2-opt | 2,025 / 2,025 | 156 m | 2.41 ms | — |
| Count rule | 2,025 / 2,025 | 152 m | 3.47 ms | 1.43 m |
| Numeric rule | 2,025 / 2,025 | 152 m | 3.47 ms | 1.43 m |
| Numeric plus pattern | 2,025 / 2,025 | 152 m | 3.48 ms | 1.43 m |

For the 2,025 paired tasks, the count rule's mean improvement over fixed NN+2-opt has a 95% seed-group bootstrap interval of 1.23–1.63 m. Each policy includes feature preparation, selection, the request runner's preprocessing, NN fallback preparation, candidate search and route reconstruction. All three feature-based rules happened to be identical; this run provides no evidence that the extra numeric features or synthetic pattern label improve upon item count. These figures are conditional on the synthetic workload mix and the single measured environment. The evaluation group count is small.

The separately measured, estimated within-budget offline candidate reference gives mean regret of 1.27 m for the count rule and 2.69 m for fixed NN+2-opt. The reference uses separately timed runs and is neither a deployed selector nor a proof of global optimality. See `results/full/eval-policy-comparison.json` for task counts and intervals.

## Candidate and scenario observations

- Exhaustive Search and DP agreed on the 675 evaluation tasks where both completed. Under the candidate-only 0.2-second search limit, DP completed all 1,350 tasks up to n=12, timed out on all 225 n=15 tasks, and hit the configured size guard on all 450 tasks at n=20 or 50. The guard is a setting, not evidence of an inherent cutoff. A separate 2-second memory sample completed at n=15.
- NN+2-opt completed all 2,025 candidate comparisons; 2,022 reached a local optimum and three stopped at the evaluation limit. Its average per-task relative distance reduction versus NN was 7.43% across these completed paired tasks. Candidate search timings exclude shared preprocessing, unlike total policy time.
- On 405 clustered evaluation tasks, NN+2-opt was shorter than NN by 12.59 m on average; the seed-group bootstrap interval was 11.48–13.80 m. This is descriptive and does not establish a causal effect of clustering.
- Mirrored F tasks also change the starting-point relationship. Their near/far difference therefore cannot be attributed solely to conveyor distance. Full A–H views, counts, intervals and caveats are in `results/full/eval-views.json`.

Use `results/full/eval-candidate.svg` as an initial figure. It shows completed-task medians and must be accompanied by the completion counts in `results/full/eval-candidate-summary.json`. Separate `eval-request` records retain requested status and actual fallback provenance. The memory sample in `results/full/memory-scaling.jsonl` is whole-process peak RSS for one development task per size, with a separate 2-second limit; it is not a memory distribution or a strict cap.

The selector remains an offline experiment. Production integration would need to avoid the prototype's duplicate distance preparation and remeasure the complete request under an agreed operational budget.
