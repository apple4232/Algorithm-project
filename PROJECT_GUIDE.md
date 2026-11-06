# Project Guide: Scope, Progress, and Team Responsibilities

As of November 6, 2026.

This guide gives a new teammate or AI assistant one place to understand the project, its current implementation, and the responsibilities of A, B, and C. The letters identify responsibilities without publishing personal names. They do not identify commit authors or imply that all planned work is complete.

Read this guide first when joining the project. Use the linked documents and source files when a task needs implementation details or experimental evidence.

## 1. What are we trying to find out?

The project studies manual warehouse picking. One picker starts at S, collects the items at required locations P, and finishes at a fixed conveyor handoff point C.

The research question is: **which routing algorithm is suitable for which workload, considering both travel distance and computation cost?** Comparing algorithms is the starting point. The intended next step is to derive interpretable selection rules from experiments and evaluate those rules on unseen workloads.

The contribution is the controlled comparison and workload-aware selection study. It is not a claim that every routing method is new, or that the program reproduces a company's internal system.

## 2. What is inside the current scope?

The initial scope is one picker, multiple required locations, and one fixed conveyor. The warehouse graph and conveyor stay fixed while the required locations and starting point can vary.

The route is S -> all required locations -> C. It does not return to S. The value n counts distinct required locations rather than item units. Repeated requests at one location share a visit. Each task is assumed to fit in one basket.

Distances follow traversable aisles rather than straight lines through shelves. The graph is static and undirected. Multiple pickers, congestion, batching, capacity-constrained trips, and order deadlines are outside this implementation.

The development environment has ten vertical aisles, three cross aisles, a depth of 40 m, and 4 m spacing between aisle centerlines. C is fixed at (36, 0). There are 210 nodes, 227 undirected edges, and 180 shelf access points. These are synthetic settings, not measured facility dimensions.

## 3. Where does the project stand now?

Stages 1-3 are complete: implementation criteria, the warehouse and distance layer, and visit-order algorithms with correctness verification. The published implementation checkpoint is commit `c064384`.

The final suite at that checkpoint passed 27 automated tests on Python 3.12.2. The checks cover exact-method agreement, valid aisle paths, special inputs, Conveyor-Aware behavior, 2-opt improvements, and limit handling. This is correctness evidence, not a large performance experiment.

The workload feature extractor, A-H batch generator, full experiment runner, automatic selector, and Streamlit UI are not implemented. The proposed 1,620-task experiment has not been generated or evaluated.

Algorithm development currently stops after Stage 3. Documentation and repository publication have been completed for that checkpoint. Future feature work requires a new task from the project owner; a roadmap entry is not itself authorization to implement it.

For the evidence behind this snapshot, see the [completion report](docs/06-stage2-stage3-completion.md).

## 4. How is the calculation organized?

Dijkstra prepares shared shortest distances and path-reconstruction information. It does not choose the order of item visits. Each visit-order candidate receives the same distance table. The resulting order is expanded into an actual aisle path and checked for coverage, endpoints, and distance consistency.

Implemented candidates are Given Order, NN, Exhaustive Search, Subset DP, CA-plus, and CA-minus. The three greedy methods can each be followed by the same fixed-endpoint 2-opt, giving nine executable candidates in total.

Exhaustive Search and DP can prove optimality when completed. NN and Conveyor-Aware are heuristics. CA-plus adds weighted distance to C to the next-step distance; CA-minus subtracts it. Neither direction is assumed to improve every workload. A zero coefficient reproduces NN under the same tie rule.

The current request runner executes a manually specified method. It first obtains an NN route, then attempts the requested candidate with the remaining budget. If that candidate stops, it can return the shorter available feasible route while preserving the requested method's failure status. This fallback mechanism is not the future workload-based selector.

Development defaults are a 2-second request budget, Exhaustive and DP guards of 7 and 15 internal locations, a 256 MiB DP array-buffer estimate, and 10,000 2-opt segment evaluations. These are adjustable safeguards, not experimentally chosen selection thresholds. Time checks are cooperative and the memory estimate is not a whole-process cap.

## 5. Role A: Algorithm Implementation and Documentation

### What does A own?

A is primarily responsible for reliable route calculation. This includes the shared shortest-path layer, visit-order algorithms, common 2-opt, correctness tests, and the interfaces used to execute candidates.

A maintains the distinction between a planned order and a physical path. A also handles invalid inputs, unreachable locations, interrupted runs, and the separation between the requested algorithm and a returned fallback route.

Technical documentation belongs to A: algorithm definitions, input and output contracts, execution instructions, development limits, implementation decisions, and verification results. The routing foundation already delivered falls within this responsibility area; this does not assign historical authorship to a named person.

### What should A hand over?

A provides runnable functions, reproducible correctness checks, and documentation that lets B execute the same task across candidates. Any change to distance semantics, algorithm settings, output fields, or timing boundaries must be explained to B before comparison results are combined.

A gives C an accurate explanation of the implemented methods and their limitations. A reviews technical descriptions and demonstrations used in the presentation.

### When is A's work ready for use?

Relevant correctness checks pass, a documented example runs, reported distances match reconstructed paths, and exactness is not claimed for interrupted or heuristic runs. The implementation report identifies what changed and any remaining limitations.

The next likely responsibility is supporting B's experiments: fixing reproducible defects, investigating bottlenecks, and exposing agreed settings without changing experimental conditions silently.

## 6. Role B: Experimental Design, Evaluation, and Research Materials

### What does B own?

B is primarily responsible for establishing when each method works well. This includes workload generation, feature extraction, scenario design, seed management, grouped development/evaluation splits, batch execution, measurement, analysis, and research references supporting the experiment.

The planned features are n, dispersion, start_mean, conveyor_mean, and pattern. Layout and C remain fixed initially. B records realized feature values and accounts for the fact that changing a pattern can also change distance features.

A-H organize questions about size, clustering, dispersion, destination distance, directional shape, and starting position. They are overlapping experiment views rather than eight mutually exclusive workload classes.

### What should B hand over?

B provides reproducible generation settings, instance identities, seed groups, raw execution records, analysis outputs, and a written interpretation of the results. Failures and timeouts remain visible rather than being dropped from averages.

B derives candidate selection rules from development data. A supports integration of those agreed rules into code. B then evaluates the frozen rules against fixed-algorithm and count-only baselines on held-out workloads.

B gives C verified figures and conclusions, including units, sample counts, conditions, and uncertainty. B owns experimental interpretation; technical defects are reported to A with a reproducible input and settings.

### When is B's work ready to report?

All candidates have been compared under documented common conditions. Related tasks remain in the same data split. Timing boundaries, cache conditions, limits, and failure treatment are recorded. Rules and coefficients are frozen before final evaluation, and conclusions are supported by results rather than expectations.

B's planned workload and selector work is not yet implemented. The 27 correctness tests do not replace this experimental evaluation.

## 7. Role C: Presentation, Visualization, and Demonstration

### What does C own?

C is primarily responsible for explaining the project to an audience. This includes the presentation narrative, slides, route illustrations, performance figures, demonstration sequence, speaking notes, and preparation for questions.

C starts by identifying the problem, the comparison being made, and the evidence needed for the final explanation. The presentation can be structured early and updated as verified results become available.

### What should C hand over?

C produces presentation materials that connect the problem, methods, experiment, findings, and limitations. Route illustrations distinguish visit order from the actual aisle path. Charts identify their metric, unit, and experimental conditions.

A checks algorithm and implementation explanations. B checks numerical results and their interpretation. C can request clearer examples or additional analysis, but should not turn an untested hypothesis into a finding.

### When is C's work ready to present?

Every claim can be traced to an implemented feature, a reproducible example, or a documented experimental result. Planned work is clearly labeled. The demonstration has a reproducible input and a way to explain timeouts or fallback results.

Presentation materials do not require a new UI. A Streamlit implementation remains a separate future task.

## 8. How do the three roles work together?

Before a new experiment, A and B agree on task representation, candidate settings, status fields, and measurement boundaries. B generates workloads and runs the agreed candidates. A fixes implementation issues using reproducible reports. B analyzes the resulting records, and C develops the presentation from checked findings.

The letters describe primary responsibility, not exclusive file access. Anyone can contribute across areas when the task requires it. Changes affecting another area need a clear handoff rather than a silent change of assumptions.

A practical handoff states what changed, which input and version reproduce it, what was checked, what remains uncertain, and who needs the result next. For example, an algorithm change that alters tie handling requires B to consider whether earlier comparisons need rerunning and C to check any affected route illustration.

## 9. What decisions remain open?

The first selector's inputs are not settled. The original design proposes all five features; the PDF suggests using numerical features first and keeping the synthetic pattern label for analysis. A later comparison can evaluate count-only, four numerical features, and all five features, while disclosing where the pattern label comes from.

The Conveyor-Aware direction and coefficient, final computation and memory budgets, workload generation parameters, seed lists, and selection thresholds still require experimental decisions.

The proposed 1,620 tasks come from six sizes, three patterns, three starts, and 30 seeds. Related start variants are not independent orders. Their grouping must be preserved during splitting and uncertainty analysis.

See the [plan review](docs/07-plan-review-and-decisions.md) before treating any proposed value as final.

## 10. How should an AI assistant use this guide?

Start by identifying the requested task and its primary responsibility area. Read the [README](README.md) for execution details and inspect the relevant source or evidence document before making claims. This guide supplies context; it does not replace the project owner's current instructions or applicable repository instructions such as AGENTS.md.

Distinguish implemented behavior, planned behavior, and hypotheses. A design document is not proof that a feature exists. If code, documentation, and the requested behavior disagree, identify the discrepancy rather than silently choosing a new project direction.

For A-related work, preserve shared distance semantics and candidate interfaces, add or update meaningful correctness checks where needed, and explain effects on B's measurements. For B-related work, preserve reproducibility, data separation, and the distinction between proven optima and best-known feasible routes. For C-related work, use verified results and seek technical or numerical clarification when evidence is missing.

Keep work within the requested stage. Do not infer permission to implement the selector, UI, or multi-picker extensions merely because they appear in this guide. Follow any requested stopping point and provide a handoff before waiting for the next instruction.

The baseline validation command, run from the repository root, is:

```sh
python -m unittest discover -s tests -v
```

A complete smoke example is:

```sh
python -m picking --algorithm dp
```

Report which checks actually ran. Do not describe a previous test count as a fresh execution, and do not present a single example as a statistical benchmark.

Update this guide's current-status snapshot when an authorized stage is completed. Keep earlier completion reports dated so that historical evidence remains understandable. New repository documentation should remain in English unless the owner requests otherwise.

This is an ordinary project guide. Its filename does not guarantee automatic loading by every AI tool. Ask a new assistant to read PROJECT_GUIDE.md first; tool-specific automatic instructions can be added separately if requested.

## 11. Where are the details?

The [README](README.md) explains the project and execution. The [research proposal](docs/01-interdeliverable-proposal.md) contains the research questions and related work. The [algorithm design](docs/02-algorithm-design.md) and [workload refinement](docs/03-workload-model-refinement.md) preserve the technical model and feature rationale. The [direction summary](docs/04-direction-summary-2026-11-02.md) explains later extensions.

The [implementation baseline](docs/05-implementation-baseline.md), [completion report](docs/06-stage2-stage3-completion.md), and [plan review](docs/07-plan-review-and-decisions.md) describe current decisions, verified behavior, and open questions.

Visit-order implementations are in [picking/algorithms.py](picking/algorithms.py). Shared distances and paths are in [picking/distances.py](picking/distances.py). The environment is in [picking/graph.py](picking/graph.py), request execution is in [picking/runner.py](picking/runner.py), and correctness checks are in [tests/](tests/).
