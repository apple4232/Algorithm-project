# Workload-Aware Warehouse Picking

This project asks a practical question: **when one picker must collect items and deliver them to a fixed conveyor, which routing method should be used for each task?**

The picker starts at `S`, visits every required location in `P`, and finishes at `C`. The project compares route distance and computation time. Its longer-term goal is to build simple algorithm-selection rules from experiments, rather than assume one method is best for every order.

**Current status - November 6, 2026:** the warehouse model, shortest-path layer, routing algorithms, and correctness checks are implemented. Workload-based selection, large experiments, and the UI are planned.

## 1. What does one task mean?

An order may require visits to five shelf locations today and fifteen tomorrow. The warehouse and conveyor stay in place; the required locations and the picker's start can change.

| Term | Meaning in this project |
|---|---|
| `S` | The picker's starting position |
| `P` | The required picking locations |
| `C` | One fixed handoff point connected to the conveyor process |
| `n` | The number of distinct required locations, not the number of units |
| Workload | One task: its start, required locations, and associated characteristics |
| Exact method | A method that proves the shortest route when its computation completes |
| Heuristic | A method that produces a route without proving global optimality |
| Selector | A future rule that chooses a method from task characteristics before solving |

The route ends at `C`; it does not return to `S`. Multiple requests at one location share one visit. The physical path may revisit aisles or pass a required location before its planned turn.

The initial scope is **one picker + N required locations + one fixed conveyor**. Each task is assumed to fit in one basket. Multiple pickers, congestion, batching, capacity-constrained trips, and order deadlines are outside the current implementation.

This is a synthetic picking-zone model. It is not a replica of a particular fulfillment center or a claim about a company's internal routing system.

## 2. How does the calculation work?

The program separates two questions:

1. **How far apart are two locations along the aisles?** Dijkstra computes shared shortest distances and paths.
2. **In what order should the locations be visited?** Each routing candidate uses the same distance table to choose an order.

The selected order is then expanded into actual aisle segments.

```text
Fixed warehouse + task S, P, C
    -> validate the task and consolidate duplicate requests
    -> prepare shared distances and paths with Dijkstra
    -> run a manually specified visit-order method
    -> optionally improve the order with 2-opt
    -> reconstruct and validate the aisle path
    -> return distance, timing, and execution status
```

A future selector will sit between distance preparation and route generation. It is not implemented yet.

## 3. What is implemented?

| Component | Current behavior |
|---|---|
| Warehouse | A fixed, undirected aisle graph with nonnegative distances |
| Task validation | Existing-node checks, duplicate consolidation, and endpoint handling |
| Shared distances | Dijkstra distance tables and predecessor information |
| Routing candidates | Given Order, Exhaustive Search, Subset DP, NN, and two Conveyor-Aware directions |
| Route improvement | One shared fixed-endpoint 2-opt implementation |
| Request execution | Manually specified candidate, an NN fallback route, and stage timings |
| Verification | 27 automated tests, including exact-solution agreement and failure handling |

The five-feature extractor, A-H workload generator, experiment runner, selector, and Streamlit UI remain future work. The small inputs used by tests are correctness fixtures, not the planned experimental dataset.

### The warehouse

| Setting | Current implementation |
|---|---|
| Vertical aisles | 10, at x = 0, 4, ..., 36 m |
| Aisle length | 40 m |
| Cross aisles | y = 0, 20, 40 m |
| Picking locations | y = 2, 4, ..., 38 m on each aisle, excluding y = 20 |
| Conveyor | Fixed at (36, 0) |
| Default start | (0, 0) |
| Graph size | 210 nodes, 227 undirected edges, 180 picking locations |

Distances follow aisle centerlines. Horizontal edges exist only on the three cross aisles, so the graph cannot cut through shelves.

### The routing candidates

| CLI name | What it does |
|---|---|
| `given` | Keeps the first occurrence of each input location |
| `nn` | Repeatedly visits the nearest unvisited location |
| `exhaustive` | Checks every visit permutation |
| `dp` | Uses subset DP to reuse partial-route calculations |
| `ca-plus` | Minimizes `d(current, item) + coefficient * d(item, C)` |
| `ca-minus` | Minimizes `d(current, item) - coefficient * d(item, C)` |
| `nn+2opt` | Improves an NN order |
| `ca-plus+2opt` | Improves a CA-plus order |
| `ca-minus+2opt` | Improves a CA-minus order |

Conveyor-Aware is an experimental candidate, not a guaranteed improvement. A positive sign can favor conveyor-near items earlier; a negative sign can favor conveyor-far items earlier. A zero coefficient reproduces NN under the same tie rule.

2-opt keeps `S` and `C` fixed and reverses internal segments. It accepts the first genuine improvement, restarts its search, and stops at a local optimum or a configured limit.

## 4. How can I run it?

The project is verified with **Python 3.12.2** and uses only the standard library. No additional packages are required.

From the repository root:

```sh
python -m unittest discover -s tests -v
python -m picking --algorithm dp
python -m picking --algorithm ca-plus+2opt --coefficient 0.5
```

The CLI runs one fixed five-location example and prints JSON. It exits with code 0 for a completed request and 1 otherwise. Unicode escapes in JSON messages are valid JSON text.

To use your own task:

```python
from picking import build_warehouse
from picking.runner import run_request

result = run_request(
    build_warehouse(),
    start=(0, 0),
    required=[(0, 8), (8, 14), (20, 30), (32, 6)],
    algorithm="nn+2opt",
    budget_seconds=2.0,
)
print(result.status, result.distance, result.path)
```

Coordinates must be existing graph nodes. Available shelf locations are in `graph.picking_locations`. Requests at the start, conveyor, or other existing nodes are also supported. Inserting arbitrary positions inside an edge is not implemented.

## 5. How should I read the result?

- `order` contains the internal required locations. Requests at `S` or `C` are served at those endpoints.
- `path` contains the actual aisle-node sequence, including both endpoints.
- `distance` includes the final leg to the conveyor.
- `requested_result` describes the requested algorithm's own outcome.
- `returned_algorithm` identifies the route actually returned.
- `optimal` is true only when an exact method completes and that result is returned within the request budget.

The request runner first obtains an NN route. If the requested candidate stops, it returns the shorter feasible route among the available candidate and NN routes. It preserves the requested failure status: a returned route does not turn a timeout into a successful exact run.

For direct candidate comparisons, use `Task.create`, `prepare_distances`, and `solve`. This interface reuses one distance table and does not run the NN fallback automatically. The batch benchmark itself is future work.

### Initial limits

| Limit | Development default |
|---|---|
| Total request budget | 2 seconds |
| Exhaustive size guard | 7 internal required locations |
| DP size guard | 15 internal required locations |
| DP array-buffer estimate | 256 MiB |
| 2-opt search | At most 10,000 segment evaluations |

These are development safeguards, not experimentally selected routing thresholds. `Limits` can change the size, memory-estimate, and 2-opt guards.

Time limits are checked cooperatively; they do not forcibly terminate the process. Total timing includes validation, preprocessing, fallback preparation, search, and path reconstruction/verification. A request can exceed its budget and reports that fact. Preprocessing may time out before a feasible route is available.

The memory guard estimates the DP cost and parent arrays. It does not cap total process memory. The current 2-opt formula assumes undirected distances. Caching and one-way aisles are not implemented.

## 6. What has been verified?

The 27 tests cover warehouse structure, aisle-only paths, exact-method agreement, route coverage, empty and duplicate requests, endpoint requests, zero-length edges, unreachable inputs, limit handling, and fallback reporting.

A useful counterexample is a straight aisle with S = 8, required locations 1 and 9, and C = 0:

| Method | Route | Distance |
|---|---|---:|
| NN | 8 -> 9 -> 1 -> 0 | 10 |
| CA-plus, coefficient = 1 | 8 -> 1 -> 9 -> 0 | 24 |
| CA-plus followed by 2-opt | 8 -> 9 -> 1 -> 0 | 10 |

This demonstrates why destination-aware scoring must be tested rather than assumed to help. A second, fixed warehouse example and the full validation record are in the [completion report](docs/06-stage2-stage3-completion.md). Neither example is a large performance experiment.

## 7. What will the experiments study?

The planned workload description has five features:

| Feature | Meaning |
|---|---|
| `n` | Number of distinct required locations |
| `dispersion` | Mean shortest aisle distance across all required-location pairs |
| `start_mean` | Mean distance from S to the required locations |
| `conveyor_mean` | Mean distance from the required locations to C |
| `pattern` | Clustered, Random-Stow-like, or Directional generation pattern |

Layout and C stay fixed. Pattern and the numerical features can be correlated, so results must record realized distances rather than assume independent factors.

The implementation plan proposes 1,620 tasks from six sizes, three patterns, three starts, and 30 seeds. Related tasks must remain together when splitting development and evaluation data. This dataset has not been generated or evaluated.

The selector's rules and Conveyor-Aware settings will be derived from development experiments, then frozen before evaluation. Whether the first selector uses four numerical features or also uses the synthetic pattern label remains an explicit design decision.

## 8. Where should I look next?

| Document | What it explains |
|---|---|
| [Research proposal](docs/01-interdeliverable-proposal.md) | Research questions, experimental methodology, and related work |
| [Algorithm design](docs/02-algorithm-design.md) | Mathematical model and original technical design |
| [Workload refinement](docs/03-workload-model-refinement.md) | Why five features were retained and the environment was fixed |
| [Direction summary](docs/04-direction-summary-2026-11-02.md) | Overall direction and later multi-picker extensions |
| [Implementation baseline](docs/05-implementation-baseline.md) | Initial settings, interfaces, and stage completion criteria |
| [Completion report](docs/06-stage2-stage3-completion.md) | Implemented behavior, tests, examples, and limitations |
| [Plan review and open decisions](docs/07-plan-review-and-decisions.md) | Differences between the PDF plan and earlier design |

The November 2 documents retain the earlier research design. The baseline and completion report describe the current implementation.

Source code is in `picking/`; correctness tests are in `tests/`.

The next implementation stage is workload generation and reproducible experiments, followed by selector development and a small UI. Work currently stops after the routing implementation and its correctness checks.
