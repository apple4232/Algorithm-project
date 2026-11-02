# Workload-Aware Warehouse Picking Algorithm Design

As of: 2026-11-02 · Status: Technical design prior to implementation.

Research questions, experiments, and references are maintained in the [Proposal](01-interdeliverable-proposal.md). The rationale and history behind the feature definitions are maintained in [Refinement](03-workload-model-refinement.md). Detailed proposals in this document do not imply completed implementation or final agreement in the earlier conversation.

## 1. Design Revisions and Current Problem

The initial comparison covered `Given Order / NN / NN + 2-opt / Brute Force`. It later expanded to DP, Conveyor-Aware, and selection according to workload. The initial four methods remain as baselines and verification tools. Dijkstra is a shared aisle-distance computation layer, not a competing visiting-order algorithm. A* remains an earlier candidate for consideration, while Dijkstra is the proposed initial reference implementation.

In `G = (V, E, w)`, nodes represent aisle intersections and accessible picking points, edges represent traversable aisle segments, and weights are nonnegative travel distances. Edges must not pass through shelves. If a location lies inside an edge, insert a node and split that edge at the location.

The initial graph is static and undirected. `S` is the task-specific start, `C` is the handoff point fixed in the environment, and `P = {p1, …, pn}` is the set of required locations. Multiple requested units at the same location are served in one visit, with quantities and service time retained separately. The earlier term “item count” is therefore made precise as the **number of distinct required picking locations `n`**.

Let `d(u,v)` be the shortest-path distance in `G`. The cost of a visiting permutation `π` is:

```text
L(π) = d(S, pπ1) + Σ[k=1..n−1] d(pπk, pπ(k+1)) + d(pπn, C)
```

For `n = 0`, use `L = d(S,C)`. The route ends at `C`; no return cost from `C` to `S` is added. Requests located at the start or destination are fulfilled at that point.

## 2. Pipeline

```text
Fixed environment G, C + Task S, P
  → Validate locations and connectivity; consolidate duplicate locations
  → Compute Dijkstra distance matrix and path-reconstruction information
  → Extract five workload features
  → Select an algorithm under the computation budget
  → Generate a visiting order and optionally apply 2-opt
  → Reconstruct each leg as an actual aisle path
  → Validate coverage, endpoints, and distance; save logs
```

### Shared Shortest-Path Layer

Run Dijkstra from each distinct node in `S ∪ P ∪ {C}` to construct distance matrix `D`. With a binary heap, one source costs `O((|V|+|E|) log |V|)`; multiply this by the number of sources `m ≤ n+2`. The distance matrix uses `O(m²)` space. Retaining all predecessor information adds `O(m|V|)` space, so compare this with rerunning searches during path reconstruction as map size grows.

Caching is possible for a fixed graph, but record cache hits and initial construction costs. All candidates must use the same cache conditions. If a required location is unreachable, return `infeasible` rather than treating an infinite distance as a valid route cost.

A shortest leg can pass through another required location. The visiting order is a planning sequence; the physical route only needs to cover every required location at least once. An “exactly once” restriction is not imposed on physical aisle nodes. Repeated traversal of aisles and intersections is allowed.

## 3. Visiting-Order Algorithms

### Given Order and Exhaustive Search

Use the supplied input order with `S` and `C` attached as a baseline. If the input is a set, retain a reproducible generation order. This is not a baseline measured from real workers' decisions.

Exhaustive Search compares all `n!` permutations. A straightforward implementation that evaluates each in `O(n)` takes `O(n·n!)` time. It supplies exact solutions for checking DP and heuristics on small instances. Earlier examples such as “Exhaustive at n=5, DP at n=10, heuristics at n=30” illustrate scale differences; they are not fixed thresholds independent of hardware and budgets.

### Subset Dynamic Programming

`F[M,j]` is the minimum cost of starting at `S`, visiting subset `M`, and ending at `pj`.

```text
F[{j},j] = d(S,pj)
F[M,j] = min(i ∈ M\{j}) { F[M\{j},i] + d(pi,pj) }
L* = min(j ∈ P) { F[P,j] + d(pj,C) }
```

Store parent states to reconstruct the order. Time complexity is `O(n²·2^n)` and space complexity is `O(n·2^n)`. DP can handle larger instances than Exhaustive Search, but remains exponential. A run that exceeds its time or memory limit must not be labeled as having found an exact solution.

### Nearest Neighbor

From the current location `u`, repeatedly choose the unvisited location minimizing `d(u,p)`, then travel to `C` after all locations are visited. A straightforward implementation with a distance matrix takes `O(n²)` time. Resolve ties by a fixed location-ID order. NN is a fast baseline without a global optimality guarantee.

### Conveyor-Aware Greedy — Proposed Formula for Evaluation

The earlier idea was to incorporate the final handoff point into greedy decisions. The formula and coefficients remain open, so the following is a **candidate definition**:

```text
score(u,p) = d(u,p) − λ · d(p,C),  λ ≥ 0
Choose the unvisited p with the minimum score
```

The hypothesis is that serving distant items earlier may leave items near the handoff point for the later part of the route. At `λ=0`, the rule reduces to NN. Adding `d(p,C)` instead would favor locations near the handoff point earlier; these intentions should be distinguished when defining a rule. Which direction works better may depend on workload.

Choose coefficient values on the calibration set and freeze them for evaluation. The score only selects the next location; actual route cost is always measured by `L(π)`. Neither improvement nor optimality is guaranteed. The straightforward implementation takes `O(n²)` time, as does NN.

### 2-opt with Fixed Endpoints

Represent a route as `r = [S, …, C]` and reverse only an internal segment of picking locations `r[i..j]`. Keep the start and destination fixed. For the current undirected distance matrix, the cost change depends on four boundary terms:

```text
Δ = d(r[i−1],r[j]) + d(r[i],r[j+1])
    − d(r[i−1],r[i]) − d(r[j],r[j+1])
```

Accept only improvements exceeding the numerical tolerance (`Δ < −ε`). A full search pass takes `O(n²)` and `K` passes take `O(Kn²)`. The number of iterations is not inherently fixed. Specify search order, first or best improvement, and a pass or time budget before implementation. Apply the same improvement budget to NN and Conveyor-Aware.

If future one-way aisles or congestion create asymmetric costs, reversing a segment also changes its internal edge costs. The four-term formula alone would no longer be sufficient.

## 4. Workload-Aware Selector

The input is `W = (n, dispersion, start_distance, conveyor_distance, pattern)`. Formulas and operational connections are maintained in [Refinement](03-workload-model-refinement.md#3-current-five-core-workload-features). The router still receives the full task data; these five values are the selector's summary.

The proposed initial implementation uses interpretable rules:

1. Use calibration experiments to identify the range in which exact methods fit the time and memory budgets.
2. Select Exhaustive Search or DP within that range.
3. Outside that range, select NN, Conveyor-Aware, or their 2-opt combinations according to quality and cost observed on calibration data.
4. Freeze rules, thresholds, and coefficients during evaluation. Test whether using all features improves on selection using item count alone.

Rules such as always using 2-opt at high dispersion remain hypotheses. Running every candidate and then choosing the shortest route provides an offline oracle comparison, not actual selector performance. Interrupted exact runs must not be labeled optimal. Specify a fallback policy that first obtains a feasible NN route, and measure whether the fallback itself completes within the budget.

## 5. Proposed Interfaces and Logging

| Category | Required information |
|---|---|
| Environment | Graph/layout version, distance units, fixed `C`, directionality, walking-speed and picking-time assumptions |
| Task | Instance ID, seed, `S`, requested locations and quantities, distinct-location count `n`, generation pattern, realized feature values |
| Execution | Candidate or selected algorithm, selection-rule version, coefficients, 2-opt budget, time limit, cache conditions |
| Result | Visiting order, aisle path, travel distance, stage-level and total computation times, exact/feasible/timeout/infeasible status |

With fixed walking speed `v` and location service times `t_i`, a simple travel-and-service estimate is `T = L/v + Σt_i`. Report computation latency separately. This is not a prediction of actual work time accounting for congestion, breaks, or differences between workers.

Review cross-document consistency, formulas, and links during documentation. Future implementation correctness and performance checks follow the [Proposal's validation plan](01-interdeliverable-proposal.md#4-validation-and-experimental-design).
