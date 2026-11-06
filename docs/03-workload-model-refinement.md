# Workload Model Refinement

As of: 2026-11-02 · Status: Definition of workload scope and experimental variables.

**Implementation update - November 6, 2026:** This document retains the feature-refinement history. The fixed synthetic environment adopted for development is specified in the [baseline](05-implementation-baseline.md). Feature extraction and workload generation are not yet implemented. The [plan review](07-plan-review-and-decisions.md) records the open question of whether the first selector should use the synthetic pattern label.

## 1. Purpose

This document preserves the factors considered initially rather than presenting only the final five. It explains the current model through `Initial idea → Review → Reclassification → Current scope → Future extensions`. The title **Workload Model Refinement** replaces the earlier phrase “Design Evolution,” which overstated the scale of the revision.

The research and validation plans and references belong in the [Proposal](01-interdeliverable-proposal.md). Distance computation and selector specifications belong in [Algorithm Design](02-algorithm-design.md).

## 2. Initial Broad Considerations and Refinement Process

The initial exploration included item count, item dispersion, picker position, conveyor position, spatial pattern, warehouse size and layout, aisle count and width, shelf spacing, walking speed, item retrieval time, basket capacity, and congestion. These factors remain relevant to warehouse operations even when they are excluded from the initial selector inputs.

| Stage | Considerations | Decision and rationale |
|---|---|---|
| Initial exploration | Task characteristics together with environmental and operational conditions | Collect a broad set of potentially influential factors |
| Request to narrow scope | Reduce dozens of factors to approximately 5–8 | Balance explanatory value for algorithm selection with project scope |
| Six candidates | Item Count, Dispersion, Picker-to-Item Distance, Item-to-Conveyor Distance, Spatial Pattern, Warehouse Layout | Recognize that layout differs from characteristics that vary between tasks |
| Current five core features | Use the first five characteristics as selector inputs | Separate layout as a fixed environment to control the comparison |
| Later extensions | Layout variation, congestion, and multiple pickers | Introduce these after establishing initial results |

The earlier idea of using warehouse layout as a feature is retained as a candidate for testing generalization across layouts. The current decision stages the experiments rather than abandoning that possibility.

## 3. Current Five Core Workload Features

Let `P={p1,…,pn}` be the required locations, `S` the start, `C` the fixed handoff point, and `d` the shortest-path distance on the aisle graph. Here, `n` counts distinct required picking locations, not requested units.

| Feature | Current definition | Operational connection | Role to investigate |
|---|---|---|---|
| **Item Count** | `n = cardinality(P)` | Number of locations that must be accessed in one task | Feasibility of exact methods and transition to heuristics |
| **Item Dispersion** | `2/[n(n−1)] · Σ(i<j) d(pi,pj)` | Picking locations spread across aisles or regions | Potential improvement from 2-opt over NN |
| **Picker-to-Item Distance** | `(1/n) · Σi d(S,pi)` | Separation between the picker and the requested item region | Changes in visiting order due to the starting point |
| **Item-to-Conveyor Distance** | `(1/n) · Σi d(pi,C)` | Travel burden associated with the final handoff process | Effect of destination-aware greedy routing |
| **Spatial Distribution Pattern** | Clustered / Random-Stow-like / Directional | Simplified patterns arising from storage and demand relationships | Structure not captured by average distance alone |

For `n<2`, define dispersion as zero. For `n=0`, record both mean-distance features as zero and handle `S→C` without invoking the selector. Reject unreachable-location cases before feature extraction.

Dispersion is a numerical distance measure, while pattern is a category describing generation conditions. An elongated group and several small clusters can have similar mean dispersion yet favor different visiting orders. The features are not assumed to be statistically independent. Examine their correlation and overlap in the generated data, and use ablation comparisons to assess additional explanatory value.

### Proposed Generation Rules

- **Clustered:** Sample primarily from a small number of adjacent aisles or regions. The earlier suggestion of concentrating items in 1–3 aisles remains a candidate setting.
- **Random-Stow-like:** Sample task locations across the warehouse from fixed storage locations. This does not reconstruct Coupang's actual storage or demand distribution.
- **Directional:** Bias selection toward a particular direction, rear region, or elongated area. Specify the region and bias strength before implementation.

Starting-point scenarios may include front/depot, center, and edge positions. Keep `C` at one location, such as the front center, and vary item locations to produce conveyor-near and conveyor-far tasks. The experiment does not require moving physical equipment between tasks.

Low/Medium/High labels are descriptive bins. If needed, derive boundaries from calibration-set quantiles, save them, and apply the same boundaries to evaluation data. Do not retune bins or selection rules after inspecting the full unseen evaluation set. Preserve actual distance values and units alongside any labels.

## 4. Factors Reclassified as Environmental or Operational Conditions

| Initially considered factor | Current classification | Initial experimental treatment |
|---|---|---|
| Warehouse layout, aisle and cross-aisle counts, dimensions and widths, shelf spacing | Environment | Fix as one traversable graph |
| Conveyor position | Environment | Fix `C`; relative distance from requested locations varies by task |
| Picker position | Task input | Vary `S`; summarize it for the selector through mean start distance |
| Walking speed and item retrieval time | Operational constants | Hold fixed and exclude from selection features |
| Basket capacity | Task feasibility condition | Assume each supplied task fits in one basket; capacity-constrained multiple trips are a separate extension |
| Congestion, aisle capacity, and route interference | Interaction conditions | Exclude initially and model during the multi-picker stage |

Layout continues to determine actual aisle distances. Excluding it as a direct selector input does not remove it from the graph. A fixed `C` is also consistent with a variable Item-to-Conveyor Distance because the requested item locations change.

## 5. Connection to Real Warehouse Operations and Limitations

Coupang's official WMS description discusses Random Stow as mixed product placement informed by demand and intended to shorten travel. Its PDA and route-guidance descriptions motivate considering picker and item locations. Sources are collected in [Proposal R1–R2](01-interdeliverable-proposal.md#5-related-work-and-references).

The mapping from those descriptions to five features is **this project's modeling interpretation**. It does not imply that Coupang uses the same features or algorithms. Because actual Random Stow is not simply random placement, the synthetic pattern is labeled with the suffix `-like`.

`C` generalizes a handoff point connected to outbound processing. Real workflows may include intermediate steps such as rebinning and packing. The available materials do not verify exact facility layouts, task-size distributions, picker starting-position distributions, or conveyor coordinates. Synthetic data and assumptions must remain distinct from measured operational data.

The initial exploration also considered modeling the full physical scale of a large fulfillment center. Such facilities can contain multiple processes and automated areas beyond picking. The current scope is therefore **one manual PTG picking zone inspired by publicly described operations**, rather than a digital replica of a particular Coupang facility.

### Preserving the Earlier Numerical Environment Proposal

The earlier conversation suggested approximately 10 parallel picking aisles, three cross aisles, an aisle length of approximately 15 m, a width or spacing scale of approximately 3 m, and a front-center handoff point. These values are retained as **unconfirmed simulation candidates**. Values drawn from different research settings must not be combined and presented as measurements of one actual warehouse. In particular, aisle width and aisle centerline spacing are different quantities and must be defined separately.

This document does not establish a specific full-text source for each of those dimensions. [Proposal R7](01-interdeliverable-proposal.md#5-related-work-and-references) remains a simulation reference for later study, not a verified source of those exact dimensions without checking its tables and diagrams. During implementation, either adopt the values as explicit project assumptions or verify and record a coherent configuration from one source, including its location in that source.

## 6. Current Experimental Structure and Revision Principles

```text
Fixed Warehouse Environment + Variable Workload
  → Algorithm Selection → Route Generation → Performance Evaluation
```

The first stage examines whether a small set of workload characteristics explains differences in algorithm distance and cost. Later stages vary layout to evaluate generalization and add congestion, waiting, and task allocation when multiple pickers operate simultaneously. The five features form a **controlled first-stage representation**, not an exhaustive account of real picking performance.

Record future revisions using `Initial idea / Observation or evidence / Revision / Rationale`. When introducing a feature, identify the phenomenon that the existing five do not explain and the validation needed to justify the addition.
