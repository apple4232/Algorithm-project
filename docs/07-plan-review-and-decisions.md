# Implementation Plan Review and Open Decisions

As of November 6, 2026. This document compares the supplied 19-page implementation-plan PDF with the four November 2 design documents. It records what was retained, what was clarified for Stages 1-3, and what still needs experimental evidence.

The reference PDF is titled "구현 계획.pdf". Its prose and tables informed the reading structure of these documents. The PDF itself is not bundled in this repository; the explanations below stand on their own.

## 1. Does the plan keep the project focused?

Yes. It keeps one picker, a fixed warehouse, static picking locations, and a fixed conveyor. Orders vary through S and P. It separates aisle shortest paths from the visiting-order problem and derives selection rules from development experiments.

| Topic | Review result |
|---|---|
| One picker, N locations, one conveyor | Consistent with the initial scope |
| Dijkstra as shared preparation | Consistent; not a competing visit-order algorithm |
| Fixed environment versus task features | Consistent definitions, with a selector-input decision still open |
| Rules derived from experiments | Consistent; evaluation results must not be used to retune rules |
| Small, medium, and large cases | Useful sampling groups, not permanent selection thresholds |
| A-H cases | Compatible and allowed to overlap |
| Destination-aware scoring | The PDF identifies a real risk; its sign differs from the earlier candidate |
| Streamlit | Reasonable as a later presentation layer |

## 2. What changed before implementation?

### The warehouse now has one concrete development configuration

Earlier dimensions were unconfirmed candidates. The PDF proposes ten aisles, 40 m depth, 4 m centerline spacing, and C at the front-right corner.

The implementation adopts that coherent synthetic configuration. This is a development choice, not a claim that these are measured facility dimensions. The [baseline](05-implementation-baseline.md) records the coordinates and units.

### Conveyor-Aware is split into two named candidates

The earlier technical design proposed subtracting distance to C. The PDF adds it. These formulas encourage different choices, so both are implemented explicitly as CA-minus and CA-plus.

The PDF's line example is valid: NN has distance 10 while CA-plus with coefficient 1 has distance 24. This demonstrates a possible failure of the positive sign. It does not prove that the negative sign always helps.

The coefficient and any retention or exclusion of a candidate must be determined on development workloads.

### A feasible route is obtained before a costly method

Waiting for an exact method to use the whole response budget and only then running NN could exceed the budget further. The request runner therefore prepares NN first and uses remaining time for the requested method.

The requested method's status is retained. Returning a fallback route does not make a stopped exact computation optimal or successful.

### The UI is postponed

The initial implementation covers calculation and verification. Streamlit can later call the same functions, but batch timing should remain independent of screen refreshes and UI execution.

## 3. How should A-H be interpreted?

A-C describe task size. D-G describe spatial conditions. H varies the start. A task can belong to more than one case.

| Case | Question | Planned comparison |
|---|---|---|
| A | Do the implementations produce correct answers? | Exhaustive versus DP on small tasks |
| B | Where does DP remain practical? | Time and memory as n increases |
| C | How do fast methods scale? | Heuristic route quality and computation cost |
| D | Are simple routes enough for clustered tasks? | NN versus additional improvement |
| E | Does dispersion increase the value of global improvement? | Paired heuristic results with realized dispersion |
| F | Does the relationship to C matter? | Matched near/far item groups |
| G | Does shape matter beyond mean distance? | Directional versus other patterns |
| H | Does the same item set favor different routes from different starts? | Fixed P and C, varied S |

The plan samples A at 3/5/7 locations, B at 8/10/12/15, and C at 20/30/50. These are proposed experiment points. The current 7- and 15-location implementation guards are development protections, not experimentally calibrated policies.

F preserves inter-item structure but also changes start distance. Its results must not be described as a pure causal effect of conveyor distance. H variants must share exactly the same P and C.

The PDF attributes A-F to an earlier algorithm-design version. The current November 2 files do not contain explicit A-F labels, so that particular provenance should be checked against the original version.

## 4. Which selector inputs remain undecided?

The research design proposes five features. The PDF stores all five but uses only numerical ones in the first selector, because actual orders may not carry a generator-provided pattern label.

A useful later comparison is:

| Policy | Inputs | What it tests |
|---|---|---|
| Count-only | n | Whether size is sufficient |
| Numerical features | n, dispersion, start_mean, conveyor_mean | Added value of distance information |
| Numerical features plus pattern | All five | Added value of a synthetic pattern label |

Using a known generation label is a legitimate controlled experiment when disclosed. It should not be presented as automatically available for real orders. Pattern recognition from coordinates would be a separate feature.

No feature extractor or selector is implemented yet, and the research objective has not been silently changed to a four-feature claim.

## 5. Is the proposed experiment size reasonable?

The PDF proposes:

```text
6 sizes x 3 patterns x 3 starts x 30 seeds = 1,620 tasks
```

A 15/15 seed split gives 810 development tasks and 810 evaluation tasks. That arithmetic is correct.

If three starts share one item set, those three tasks are related observations. They must stay in the same split and should not be treated as three independent orders when estimating uncertainty.

Each size-pattern cell has fifteen evaluation seed groups. This is a useful starting plan, not proof that there is enough evidence for fine-grained selection rules.

Additional A/B sizes, regional-dispersion tasks, F pairs, coefficient sweeps, and timing repeats must be counted separately. Repeating a calculation does not create a new independent workload. Duplicate generated instances also need checking.

## 6. What must be measured later?

Use the same warehouse, task, and distance table for each candidate comparison. Run candidates one at a time, randomize their execution order, and record code version, machine details, cache state, and limits.

| Measure | Interpretation |
|---|---|
| Total route distance | Includes the final handoff leg |
| Optimality gap | Only against a completed, proven optimum |
| NN-relative change | A practical reference on larger tasks |
| Selection regret | Difference from the best candidate completing within the same budget |
| Stage and total timings | Include preprocessing, feature extraction, selection, search, and reconstruction as applicable |
| Memory and failure rates | Keep timeouts and resource failures in the results |
| Paired differences and intervals | Compare methods on the same tasks, grouping related instances |

The current implementation records validation, preprocessing, NN preparation, search, reconstruction, and total time. It estimates DP buffer requirements. It does not yet implement peak-memory measurement, feature/selection timing, or the full experimental metrics.

For complete request latency, include shared preparation once. For visiting-order comparisons, report the shared preparation separately instead of pretending each candidate independently recomputed it.

## 7. What should be decided before full experiments?

- Fix the generation rules, group identities, seed lists, and duplicate policy.
- Choose a response-time and memory budget using pilot measurements.
- Set the same 2-opt budget for each starting heuristic.
- Choose the Conveyor-Aware direction and coefficient on development data.
- Decide whether the first selector uses four numerical features or all five.
- Define distance tolerances, tie rules, and the treatment of failed candidates.
- Freeze all rules before looking at the held-out evaluation answers.

The intended objective is route distance subject to a computation budget. A selector that runs every candidate and chooses afterward is an offline reference, not the deployed policy.

## 8. Where does implementation stop?

Stages 1-3 establish a reproducible routing foundation. See the [completion report](06-stage2-stage3-completion.md) for the 27 passing checks.

Feature extraction, full workload generation, benchmarking, selection rules, and the UI remain the next research and implementation steps. No conclusions about their effectiveness have been claimed.
