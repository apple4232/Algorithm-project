# Implementation Baseline

As of November 6, 2026. Stages 1-3 are complete. The settings below are initial development defaults; they are not final values selected by performance experiments.

## 1. What is the initial implementation meant to do?

One picker starts at S, serves all required locations P, and finishes at a fixed conveyor C. The first implementation establishes trustworthy route calculation before adding experimental selection rules.

| Stage | Deliverable | Completion check |
|---|---|---|
| 1 | Implementation baseline | Scope, initial settings, interfaces, and checks are written down |
| 2 | Warehouse and shared distances | Aisle-only shortest paths and reconstructed distances are valid |
| 3 | Visit-order algorithms | Exact methods agree on small tasks and heuristics return valid routes |

The owner initially requested a stop after each stage, then authorized continuing through Stage 3. Work stops there. The selector, workload feature extractor, A-H batch generator, large experiments, and UI remain outside this delivery.

## 2. Which assumptions stay fixed?

The graph is static and undirected. Weights are finite, nonnegative travel distances. The fixed warehouse creates no edges through shelves.

The travel cost is:

```text
d(S, first item)
+ sum of distances between consecutive items
+ d(last item, C)
```

There is no return leg from C to S. An empty task follows S -> C.

Repeated requests at one location share a visit, while request counts remain available separately. Requests at S or C are served at those endpoints and removed from the internal permutation. The original distinct-location count remains in the task.

The planned visit order and the physical aisle path are different objects. A shortest leg may pass another required location early. Repeated aisle traversal is allowed.

## 3. How is the warehouse constructed?

The PDF proposes a concrete synthetic environment. Those values are adopted as development settings rather than measurements of a real facility.

| Setting | Default |
|---|---|
| Vertical aisles | x = 0, 4, ..., 36 m |
| Warehouse depth | 40 m |
| Cross aisles | y = 0, 20, 40 m |
| Shelf access points | y = 2, 4, ..., 38 m, excluding y = 20 |
| Conveyor C | (36, 0) |
| Default start S | (0, 0) |
| Other example starts | (16, 20), (0, 40) |
| Units | Meters along aisle centerlines |

Intersections and shelf access points are nodes. Consecutive nodes are joined vertically; horizontal edges exist only on cross aisles. The expected structure is 210 nodes, 227 undirected edges, and 180 shelf access points.

The first version accepts existing graph nodes. It does not insert arbitrary coordinates inside an edge. Custom graphs declare their edges to be traversable; without shelf geometry, the program cannot independently verify the physical meaning of those custom edges.

## 4. What information moves between components?

| Component | Information |
|---|---|
| Environment | Stable node IDs, coordinates, adjacency, shelf locations, C, version |
| Task | S, first-occurrence required locations, request counts, C |
| Shared preparation | Distance matrix and predecessor maps for path reconstruction |
| Algorithm input | The same distance table, task, coefficient, and limits |
| Algorithm result | Order, distance, execution status, optimality flag, settings |
| Request result | Actual aisle path, returned method, fallback flag, stage timings |

Coordinate tuples provide a stable lexicographic tie rule. Given Order preserves first occurrence; NN and Conveyor-Aware use the same coordinate ordering for ties.

Execution distinguishes completed, timeout, resource_limit, infeasible, invalid_input, and error states. A stopped exact run is never labeled optimal.

## 5. How are the algorithms defined?

### Exact methods and NN

Exhaustive Search evaluates every permutation. Subset DP stores the shortest partial route for a visited subset and last location, including parent information to recover the order. NN repeatedly selects the nearest remaining location.

Every method includes the last leg to C. Exactness checks compare route distances, because multiple visit orders can have the same optimum.

### Conveyor-Aware candidates

The earlier design and PDF use different signs. The implementation keeps both interpretations visible:

```text
CA-plus:  score = d(current, item) + coefficient * d(item, C)
CA-minus: score = d(current, item) - coefficient * d(item, C)
```

The coefficient must be finite and nonnegative. Proposed development values are 0, 0.25, 0.5, and 1; no final value is selected.

A zero coefficient must reproduce NN with the same tie rule. Scores choose the next location; they are not added to the reported travel distance.

The straight-aisle counterexample S = 8, P = {1, 9}, C = 0 must produce NN distance 10 and CA-plus distance 24 at coefficient 1. Neither sign has an assumed performance guarantee.

### Shared 2-opt

2-opt reverses only internal segments and keeps S and C fixed. It scans candidate segments in a deterministic order, accepts the first improvement, and restarts.

An improvement must exceed 1e-9 m. The initial limit is 10,000 segment evaluations or the remaining time, whichever is reached first. This is a development setting, not a final experimental budget.

For undirected distances, four boundary terms give the reversal cost change. Tests compare this calculation with full route recomputation. The same implementation and limits apply to all three greedy starting methods.

## 6. How are long calculations handled?

| Safeguard | Initial setting |
|---|---|
| Total request budget | 2 seconds |
| Exhaustive guard | At most 7 internal locations |
| DP guard | At most 15 internal locations |
| DP array-buffer estimate | At most 256 MiB |

The guards apply after endpoint requests have been removed from the internal permutation. They are adjustable safeguards, not selector rules or mathematical limits.

The request runner first obtains an NN route, then spends the remaining time on the manually requested method. If that method stops, its feasible route, when available, is compared with NN. The returned route and the requested execution status are recorded separately.

Preprocessing, route generation, and reconstruction are timed separately with a monotonic clock. Caching is initially disabled.

Time checks are cooperative. The process is not forcibly terminated, and reconstruction can push the total beyond the budget. The output reports actual elapsed time and budget violation. Preprocessing can exhaust the budget before NN is available.

The memory guard estimates the cost and parent array buffers. It does not enforce a whole-process memory ceiling.

## 7. What must be checked before moving on?

| Area | Required evidence |
|---|---|
| Warehouse | Expected counts, connectivity, and no shelf-crossing edges |
| Distances | Hand-calculated examples and agreement with reconstructed aisle lengths |
| Exact methods | Exhaustive and DP agree on small inputs |
| Greedy methods | Required coverage, fixed endpoints, and reproducible tie handling |
| Conveyor-Aware | Zero-coefficient equivalence and the documented counterexample |
| 2-opt | No distance increase and valid paths after reversal |
| Edge cases | Empty tasks, one location, duplicates, endpoint requests, S = C, unreachable nodes |
| Limits | Interrupted runs remain non-optimal; fallback provenance is retained |

The [completion report](06-stage2-stage3-completion.md) records the checks that passed.

## 8. What is still undecided?

The five planned workload features remain n, dispersion, start_mean, conveyor_mean, and pattern. The first selector's use of pattern is not settled.

Final workload-generation settings, seed lists, sample counts, selector thresholds, Conveyor-Aware settings, and experimental budgets await later experiments. No performance conclusion is inferred from development safeguards.

The [plan review](07-plan-review-and-decisions.md) explains these open decisions. The November 2 design documents retain the original proposal and refinement history.
