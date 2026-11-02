# Direction Summary: Interim Project Direction (November 2)

As of: 2026-11-02 · Status: Interim summary of project direction.

## 1. Current Project Direction

The starting point was reducing picker travel distance in basket-level outbound (OB) picking. The current question goes further: **Which routing algorithm is appropriate for which workload?** The focus is on explaining differences between fast and exact methods in both route distance and computational cost.

Here, logistics refers to the broader context of storage, movement, and outbound flow, while operations refers to the specific activities carried out within that context. The current research addresses manual warehouse picking and route selection. Delivery-vehicle road routing and optimization of an entire fulfillment center remain outside this scope.

## 2. How the Direction Has Been Refined

| Initial perspective | Current direction after review |
|---|---|
| Improve a route for approximately 10 items | Evaluate algorithm trade-offs across task sizes and spatial characteristics; retain the initial scale as an example |
| Compare several algorithms | Use the comparison to test the value of workload-aware selection |
| Consider many operational and spatial variables as inputs | Narrow through six candidates to five core workload features and a fixed environment |
| Use the full scale of a large facility as a reference | Model one manual PTG picking zone as a controlled graph |
| Travel to a final conveyor | Define a fixed handoff point connected to outbound processing to accommodate differences in real workflows |

This refinement preserves the initial ideas while identifying questions that can be answered experimentally and topics that require later extensions. The detailed rationale remains in [Workload Model Refinement](03-workload-model-refinement.md).

## 3. Current Scope and Open Decisions

The current direction uses a fixed layout, a fixed handoff point, one picker, and static picking locations. Workload is summarized by item count, item dispersion, distance from the start, distance to the handoff point, and spatial pattern. Aisle shortest paths and item visiting order are handled in separate layers.

Open decisions include numerical layout settings, item-count ranges and repetition counts, computation budgets, the specific Conveyor-Aware formula and coefficients, and selector thresholds. The detailed proposals in [Algorithm Design](02-algorithm-design.md) are candidates for validation, not established implementation results.

Public Coupang examples provide operational motivation, while academic literature supports the modeling and methods. Synthetic warehouses and workloads are not presented as internal Coupang data. Related work and reference links are maintained in the [Proposal](01-interdeliverable-proposal.md#5-related-work-and-references).

## 4. Extension to Multiple Pickers

An environment with dozens of simultaneous pickers is a long-term direction. Giving every picker an independently optimized route does not necessarily improve the overall system. Concentrating routes in the same aisles can create waiting and interference that reduce throughput.

| Stage | Additional question | Required changes |
|---|---|---|
| 1. Single-picker validation | How do quality and computational cost vary with workload? | Current five features, static distances, and exact-versus-heuristic comparisons |
| 2. Generalization across layouts | Do selection rules remain useful under different aisle structures? | Evaluation by layout, assessment of recalibration needs, and possible distance normalization |
| 3. Multi-picker simulation | What bottlenecks emerge when independently planned routes interact? | Task arrival times, picker states, and rules for aisle occupancy, passing, and waiting |
| 4. Task allocation and route coordination | Which picker should receive each task, and when should routes be recomputed? | Joint assignment and routing, dynamic costs, and coordination policies |

Multi-picker evaluation should include throughput, task completion time, makespan, waiting time, congestion, and workload balance in addition to total distance. Introducing time-varying costs requires revisiting assumptions behind static Dijkstra distances and 2-opt. The current feature-extraction and algorithm-comparison structure provides a reusable starting point, but the five features are not assumed to explain congestion adequately.

Dozens of pickers is an extension target, not a currently implemented or validated capacity. Increase picker count and task arrival rates incrementally, measure bottlenecks, and then introduce additional algorithms.

## 5. Next Steps and Document Maintenance

1. Finalize the environment and workload generation rules, recording assumptions and units.
2. Verify distance computation and agreement between exact methods on small instances.
3. Compare NN, Conveyor-Aware, and their 2-opt combinations under the same improvement budget.
4. Separate calibration and evaluation data; compare a fixed policy, item-count-only selection, and five-feature selection.
5. Use the results to retain or revise the current scope before extending to layout variation and multiple pickers.

Document responsibilities remain distinct: Proposal covers research, methods, validation, and related work; Algorithm Design covers technical specifications; Refinement preserves variable-refinement history and operational connections; this summary covers direction, priorities, and extensions. The four documents were initially added to an empty repository without changing the existing project reference materials. This English revision retains their content and decision history; the earlier Korean version remains available in Git history. Future revisions should record the current decision and its rationale alongside the earlier context.
