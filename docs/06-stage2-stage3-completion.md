# Stages 2 and 3: Implementation and Verification

As of November 6, 2026. The warehouse and routing implementation is complete through Stage 3. Further algorithm-selection and experimental work has not started.

## 1. What was delivered?

The implementation makes it possible to create a task, prepare shared aisle distances, run a routing candidate, and inspect a validated physical path.

| Stage | Delivered behavior |
|---|---|
| 2 - Warehouse and distances | Fixed graph, task validation, duplicate handling, Dijkstra, distance matrix, path reconstruction |
| 3 - Visit order and improvement | Nine candidates, common 2-opt, execution limits, fallback provenance, correctness tests |

The code uses only the Python standard library. No UI framework or external graph package is required.

The existing research documents remain available as historical design records. Their current-status notes direct readers to this implementation.

## 2. How was Stage 2 checked?

The fixed warehouse contains 210 nodes, 227 undirected edges, and 180 shelf access points. It is connected, uses ten vertical aisles, and permits horizontal movement only at y = 0, 20, and 40 m.

The first Stage 2 run passed eight tests. Those tests remain part of the final suite.

A hand-calculated example illustrates the aisle constraint. Moving from (0, 2) to (4, 2) costs 8 m through the front cross aisle, rather than a 4 m line through a shelf. Continuing from that item to C = (36, 0) costs 34 m, for a total of 42 m.

The checks also cover symmetric distances, zero diagonals, reconstructed-path lengths, invalid weights, missing nodes, disconnected inputs, duplicate requests, and requests at endpoints.

## 3. Which methods were added in Stage 3?

| Method | Role |
|---|---|
| Given Order | Reproducible input-order baseline |
| NN | Fast greedy baseline |
| Exhaustive Search | Exact small-input reference |
| Subset DP | Exact method using subset states |
| CA-plus and CA-minus | Two explicit destination-aware score directions |
| NN+2-opt | NN followed by common route improvement |
| CA-plus+2-opt and CA-minus+2-opt | The same improvement procedure applied to each score direction |

The request runner accepts a manually specified method. It is not a workload-based selector. It prepares an NN route before attempting a higher-cost candidate, and it preserves separate records for the requested method and the returned route.

## 4. What did the final tests establish?

The final suite passed **27 tests** on Python 3.12.2.

| Check | Evidence |
|---|---|
| Exact agreement | Exhaustive and DP agree on 24 small tasks: n = 0 through 7, with three start scenarios |
| Candidate validity | All nine candidates cover required locations and reconstruct valid paths on those small tasks |
| Known medium optimum | DP returns distance 16 on a straight aisle with 15 internal required locations |
| Large heuristic validity | Six heuristic candidates return valid paths for a fixed 50-location warehouse task |
| Score behavior | Zero-coefficient Conveyor-Aware matches NN; the positive-sign counterexample is reproduced |
| 2-opt correctness | Boundary deltas match full recomputation; accepted changes do not increase distance |
| Special requests | Empty, single, duplicate, and endpoint requests; S = C; early passage through another required location |
| Error handling | Missing nodes, disconnected inputs, negative and nonfinite edge weights |
| Limit handling | Size guards, DP buffer estimates, interrupted exact runs, and NN fallback reporting |
| Internal failure | A failed path validation is not returned as a verified optimal route |

Timeout branches are checked using controlled clock values or candidate outcomes where appropriate. The suite does not rely on racing a real slow operation to trigger every timeout.

These inputs are correctness fixtures. They are not the planned A-H experiment dataset, and the tests do not establish statistical superiority for any heuristic.

## 5. What do the examples show?

### A counterexample for destination-aware scoring

On a straight aisle, let S = 8, P = {1, 9}, and C = 0.

| Method | Route | Distance |
|---|---|---:|
| NN | 8 -> 9 -> 1 -> 0 | 10 |
| CA-plus, coefficient = 1 | 8 -> 1 -> 9 -> 0 | 24 |
| CA-plus+2-opt | 8 -> 9 -> 1 -> 0 | 10 |

The first CA-plus scores are 8 for location 1 and 10 for location 9, so this is not a tie-breaking artifact. The example shows a possible failure, not that every destination-aware rule is worse than NN.

### The fixed command-line example

The CLI uses S = (0, 0), C = (36, 0), and five locations: (0, 8), (8, 14), (20, 30), (32, 6), and (36, 36).

| Method | Distance in meters |
|---|---:|
| Given Order | 168 |
| NN | 136 |
| Exhaustive Search | 136 |
| Subset DP | 136 |
| CA-plus, coefficient = 1 | 200 |
| CA-minus, coefficient = 1 | 136 |
| NN+2-opt | 136 |
| CA-plus+2-opt | 136 |
| CA-minus+2-opt | 136 |

These values are a reproducible smoke check. They do not choose final coefficients, selector thresholds, or a generally best method.

## 6. How can the checks be repeated?

Run from the repository root:

```sh
python -m unittest discover -s tests -v
python -m compileall -q picking tests
python -m picking --algorithm dp
```

The first command runs the correctness suite, the second checks Python compilation, and the third runs one complete example. See the [README](../README.md) for custom task input and result interpretation.

## 7. What are the practical limits?

The initial defaults are a 2-second request budget, seven internal locations for Exhaustive Search, fifteen for DP, a 256 MiB DP buffer estimate, and 10,000 2-opt segment evaluations.

These safeguards are configurable. Time checks are cooperative rather than process termination. The memory estimate covers DP arrays rather than the whole process. One-way aisles, arbitrary coordinate insertion, and caching are not supported.

No peak-memory benchmark, full scalability study, or workload-level statistical evaluation is claimed.

## 8. What comes next?

The next implementation stage would add feature extraction, reproducible A-H workloads, grouped development/evaluation splits, and a batch runner. Only then can experiments support selector rules.

The selector, large experiments, and Streamlit remain unimplemented. Work stops after Stage 3 until the project owner authorizes the next stage.
