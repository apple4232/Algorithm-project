# A3 Team Project – InterDeliverable Proposal (Working Draft)

As of: 2026-11-02 · Status: Research proposal and experimental plan; implementation and experimental results are pending.

**Implementation update - November 6, 2026:** This document preserves the November 2 research plan. The warehouse and routing foundation is now implemented and verified through Stage 3. See the [current README](../README.md), [completion report](06-stage2-stage3-completion.md), and [plan review](07-plan-review-and-decisions.md). The full workload experiments and selector are still pending.

## Document Scope and Editorial Principles

This document covers the research questions, methodology, validation plan, and related work. Technical specifications belong in [Algorithm Design](02-algorithm-design.md), the rationale and history of variable refinement in [Workload Model Refinement](03-workload-model-refinement.md), and the overall direction and extensions in [Direction Summary](04-direction-summary-2026-11-02.md).

This draft draws on the available earlier conversation and the initial local outbound (OB) picking proposal. It is not a complete reconstruction of the entire conversation or the original documents. The initial ideas are preserved below, with the current scope identified separately. Numerical settings and rules that remain undecided are explicitly marked as proposals or open decisions.

## 1. Background and Problem Definition

The project focuses on manual Person-to-Goods (PTG) picking, in which a picker walks to item locations. Given the locations required for one basket, the task is to find a route from the starting position through all required locations to a handoff point connected to the outbound process.

Coupang's public materials describe PDA-based work assignment and route guidance, as well as Random Stow, which mixes different products across storage locations [R1, R2]. These descriptions motivate a location-based picking model; they do not disclose internal algorithms or operational datasets. In this project, `C` abstracts a **fixed drop-off / handoff point** connected to the outbound conveyor process. Direct transfer to a conveyor immediately after picking is not assumed to represent every real facility.

The inputs are a traversable aisle graph `G`, a picker starting position `S`, a set of required picking locations `P`, and a handoff point `C`. The objective is to reduce the travel distance of `S → all locations in P → C`. The start and end points need not coincide, and a return to the starting position is not required. Distances follow traversable aisles rather than straight lines through shelves.

## 2. From the Initial Idea to the Current Research Questions

| Stage | Earlier idea | Current treatment and rationale |
|---|---|---|
| Initial OB picking proposal | Improve the visiting order for approximately 10 items; compare the given order, NN, NN + 2-opt, and Brute Force | Retained as the starting example. Approximately 10 items is neither an established operational average nor a guarantee that Exhaustive Search is practical |
| Expanded comparison | Examine the distance–computation trade-off between exact and heuristic methods, including the final handoff leg | Organized into a portfolio that also includes DP and Conveyor-Aware candidates |
| Workload-aware selection | Select algorithms using item, picker, warehouse, and operational characteristics | Study whether selection by workload is useful, rather than seeking one universally best algorithm |
| Current refinement | Narrow a broad variable list through six candidates to five core workload features | Hold warehouse structure and operational constants fixed initially to interpret workload effects |

### Research Questions

- **RQ1 — Quality and cost:** How do exact methods, NN, Conveyor-Aware, and their 2-opt combinations differ in travel distance and computation time on the same task?
- **RQ2 — Workload effects:** How much do item count, dispersion, start and handoff distances, and spatial pattern explain differences between algorithms?
- **RQ3 — Value of selection:** Can a simple rule using all five features produce shorter routes within a computation budget than a fixed algorithm or a rule using item count alone?

Higher dispersion may increase the benefit of 2-opt, and the relationship between the item region and the handoff point may affect Conveyor-Aware performance. These are **hypotheses to test**, not established outcomes. The intended contribution is to validate algorithm selection under controlled warehouse workloads, rather than to claim the invention of a new optimization algorithm [R3, R6].

## 3. Methodology and Scope

1. Model one manual picking zone as an aisle graph. Keep its layout and handoff point fixed during the initial experiments.
2. Generate tasks within that environment and extract the five core features. Definitions and their refinement history are maintained in [Refinement](03-workload-model-refinement.md).
3. Use Dijkstra's algorithm to compute shortest aisle distances between relevant locations. Supply the same distance matrix to every visiting-order algorithm.
4. Run the portfolio below on the same instances to compare route quality and computational cost.
5. Develop selection rules on a separate calibration set and compare them with fixed policies on unseen evaluation data.

| Candidate | Role in the study |
|---|---|
| Given item order | Simple improvement baseline; not a measurement of actual picker performance |
| Exhaustive Search / Brute Force | Exact solutions and implementation checks for small instances |
| Subset DP (Held–Karp formulation) | Exact reference beyond the practical range of Exhaustive Search; still exponential [R5] |
| Nearest Neighbor (NN) | Fast greedy baseline |
| Conveyor-Aware Greedy | Experimental candidate that accounts for the fixed destination |
| NN + 2-opt / Conveyor-Aware + 2-opt | Quality–cost comparison under the same improvement procedure |

The current scope is a single task with one picker, static item locations, and no collisions or congestion. Tasks are assumed to fit in one basket. Order batching, inventory-location selection, multiple trips, and prediction of actual labor productivity remain separate problems.

## 4. Validation and Experimental Design

### Data and Experimental Controls

- Separate small instances used for exact verification from scaling instances with increasing item counts. Fix the size ranges and repetition counts after a pilot study.
- Generate multiple seeds for Clustered, Random-Stow-like, and Directional patterns. Include front, center, and edge starting positions while keeping `C` fixed.
- Record the realized feature values after generation. Changing pattern or item count can also change distance features, so these variables are not treated as fully independent factors.
- Set dispersion bins, selection thresholds, and Conveyor-Aware coefficients on the calibration set, then freeze them for evaluation. Prevent identical or duplicated instances from appearing in both sets.
- Use the same seeds, graph, distance matrix, start, and destination for all candidates. Randomize execution order and record the execution environment and time limits.

### Evaluation Metrics

| Metric | Definition and interpretation |
|---|---|
| Total travel distance `L` | Aisle distance including the final leg from the last item to `C` |
| Computation time | Report shortest-path preprocessing, feature extraction, selection, and visiting-order search separately, as well as total latency |
| Optimality gap | `100 × (L − L*) / L*` when a proven optimum `L* > 0` is available; report absolute differences for zero-distance cases |
| Scalability | Time, memory, distance, and timeout rate as item count increases |
| Selection regret | Distance difference from the shortest route among candidates that complete within the same budget; not a guarantee of global optimality |

If an exact run does not complete, report a difference from the best-known feasible route rather than an optimality gap. Include timeouts instead of averaging only successful runs. Report medians, quantiles, paired distance differences on the same instances, and uncertainty intervals across repeated cases.

Compare (a) one algorithm for every task, (b) selection using item count alone, and (c) selection using all five features. Choose the fixed algorithm without consulting evaluation-set answers. The proposed primary criterion is travel distance subject to a computation-time budget; the exact budget and tie-breaking rules must be fixed before evaluation. Include selector overhead when checking whether selection provides a net benefit.

### Correctness Checks to Implement

On small cases, check agreement between Exhaustive Search and DP, preservation of `S` and `C`, coverage of all required locations, aisle connectivity, and consistency of the reported distance with the reconstructed route. Verify that 2-opt does not worsen its initial route. Include empty tasks, one-item tasks, duplicate locations, and unreachable locations. These checks were planned on November 2; the checks completed on November 6 are recorded in the [implementation report](06-stage2-stage3-completion.md).

## 5. Related Work and References

Reference links checked: 2026-11-02. These sources support the research background and methods. They are not evidence that the project reproduces a company's internal system or has already produced experimental results.

- **[R1] Coupang, “The Secrets of the WMS Logistics Technology That Powers Coupang” (translated title; source in Korean).** [Official article](https://www.coupang.jobs/kr/life-at-coupang/coupang-news/%EC%BF%A0%ED%8C%A1%EC%9D%84-%EC%9B%80%EC%A7%81%EC%9D%B4%EB%8A%94-wms-%EB%AC%BC%EB%A5%98-%EA%B8%B0%EC%88%A0%EC%9D%98-%EB%B9%84%EB%B0%80/). An operational example of mixed storage and data-informed route guidance. Random Stow should not be equated with uniformly random placement.
- **[R2] Coupang (2022), “A symphony of people and technology: An inside look at a Coupang fulfillment center.”** [Official article](https://www.coupang.jobs/en/life-at-coupang/coupang-news/a-symphony-of-people-and-technology-an-inside-look-at-a-coupang-fulfillment-center/). Describes PDA-based task assignment and route optimization alongside AGVs. This project focuses on the picking zone in which workers travel to goods.
- **[R3] de Koster, R., Le-Duc, T., & Roodbergen, K. J. (2007), “Design and control of warehouse order picking: A literature review,” European Journal of Operational Research, 182(2), 481–501.** [DOI](https://doi.org/10.1016/j.ejor.2006.07.009), [Institutional record and abstract](https://research.rug.nl/en/publications/design-and-control-of-warehouse-order-picking-a-literature-review/). Establishes the connections among layout, storage policy, batching, and routing. The initial project scope isolates routing and workload-based algorithm selection.
- **[R4] Ratliff, H. D., & Rosenthal, A. S. (1983), “Order-Picking in a Rectangular Warehouse: A Solvable Case of the Traveling Salesman Problem,” Operations Research, 31(3), 507–521.** [DOI and abstract](https://pubsonline.informs.org/doi/10.1287/opre.31.3.507). Presents an efficient exact method for a special structure with crossovers only at aisle ends. Warehouse picking problems do not all have the same computational difficulty as the general TSP, and this special-case algorithm is not assumed to apply unchanged to the project's arbitrary `S → P → C` setting.
- **[R5] Held, M., & Karp, R. M. (1962), “A Dynamic Programming Approach to Sequencing Problems,” Journal of the Society for Industrial and Applied Mathematics, 10(1), 196–210.** [DOI](https://doi.org/10.1137/0110015). Provides the basis for subset DP. The project adapts the termination expression to a fixed start and a separate destination.
- **[R6] Rice, J. R. (1976), “The Algorithm Selection Problem,” Advances in Computers, 15, 65–118.** [DOI](https://doi.org/10.1016/S0065-2458(08)60520-3). Provides the conceptual background for choosing algorithms from problem characteristics. The project starts with interpretable rules rather than requiring a learned model.
- **[R7] Winkelhaus, S., Zhang, M., Grosse, E. H., & Glock, C. H. (2022), “Hybrid order picking: A simulation model of a joint manual and autonomous order picking system,” Computers & Industrial Engineering, 167, 107981.** [DOI](https://doi.org/10.1016/j.cie.2022.107981). A reference for later extensions involving shared workspaces and picker blocking. Findings for a hybrid human–robot system are not treated as results for the current single-picker model. Any use of specific warehouse dimensions requires checking the corresponding settings in the full paper.

## 6. Planned Deliverables and Open Decisions

Planned deliverables include an aisle graph and workload generator, a visiting-order algorithm portfolio, selection rules, reproducible experimental logs, and a comparison report. The current deliverable documents their design.

Before implementation, finalize layout dimensions and units, item-count ranges, seeds and repetition counts, time and memory budgets, the Conveyor-Aware formula and coefficients, and selection rules. Record subsequent changes as `Initial idea → Observation → Revision → Rationale`, retaining the context of earlier decisions.
