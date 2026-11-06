# Cycle-Accurate 2D-Mesh Network-on-Chip (NoC) Performance Simulator

A cycle-accurate simulator, written in C++17 with no external dependencies, that measures latency, throughput and congestion behavior of a 4×4 mesh Network-on-Chip under uniform-random and hotspot traffic. A short Python script checks the results against analytical models.

## What is modeled

| Aspect | Implementation |
|---|---|
| Topology | 16-node 2D mesh, 5-port routers (Local, North, South, East, West) |
| Routing | Deterministic XY dimension-order routing (X first, then Y) |
| Buffering | Input-buffered FIFOs, depth 4 flits per port |
| Flow control | Backpressure: a router forwards a flit only if the downstream input buffer has space, otherwise the flit stalls in place (credit return is modeled as instantaneous). No flit is dropped inside the network |
| Arbitration | Round-robin per output port |
| Timing | Synchronous clock with a two-phase step: Phase 1 evaluates arbitration and backpressure, Phase 2 commits all transfers together, so a flit moves at most one hop per cycle |
| Packets | Single-flit packets. One cycle per hop plus one cycle for ejection |

## Workloads and method

- **Uniform random:** each node injects with probability `λ` per cycle to a random other node.
- **Hotspot:** 40% of injections target node (2,2), the rest are uniform.
- **Sweep:** `λ` from 0.02 to 0.40 in steps of 0.02, for both workloads (38 points).
- **Per point:** 500 warm-up cycles (discarded), then 2500 measured cycles, fixed seed 1337, so results are exactly reproducible.
- **Metrics:** throughput (retired flits / cycle / node), mean latency (cycles from entering the local injection buffer until ejection), mean hop count.

## Results

### Validation against theory

| Quantity | Analytical | Simulated | Error |
|---|---|---|---|
| Mean hops, uniform traffic (8/3) | 2.6667 | 2.6630 | 0.14% |
| Zero-load latency (hops + 1) | 3.6667 cycles | 3.6801 cycles (λ = 0.02) | 0.37% |
| Hotspot saturation knee | λ = 1 / 6.6 ≈ 0.1515 | latency passes 2× its low-load value between λ = 0.14 and 0.16 | n/a |
| Flit conservation (offered vs retired) | equal | worst mismatch 0.45% over 38 runs | n/a |

**Hotspot bound:** each of the 15 other nodes sends 0.40 + 0.60/15 = 0.44 of its traffic to node (2,2), whose single ejection port accepts 1 flit/cycle. Saturation occurs when 15 × 0.44 × λ = 1, so λ ≈ 0.1515.

### Behavior across load

| Injection rate λ | Uniform latency (cycles) | Hotspot latency (cycles) | Hotspot throughput |
|---|---|---|---|
| 0.02 | 3.68 | 3.49 | 0.0195 |
| 0.14 | 3.80 | 6.33 | 0.1388 |
| 0.16 | 3.81 | 12.52 | 0.1504 |
| 0.20 | 3.89 | 25.06 | 0.1547 |
| 0.38 | 4.28 | 41.09 | 0.1600 |

- **Uniform:** throughput tracks offered load across the whole sweep and latency rises only from 3.68 to 4.28 cycles. The mesh does not saturate within λ ≤ 0.40.
- **Hotspot:** latency is flat until about λ = 0.14, then rises about 12× (3.5 to 41 cycles) while throughput stays near 0.15–0.16. Once the hotspot's buffers fill, backpressure propagates upstream and flits not even headed for the hotspot get stuck behind those that are (head-of-line blocking and tree saturation).

Plots generated from the CSV with matplotlib are in [`plots/`](plots): throughput vs injection, latency vs injection, latency vs throughput, hop count, and a combined dashboard.

## Build and run

Requires a C++17 compiler (g++ or clang++). The validation script needs Python 3 with pandas.

```bash
# build and run the sweep from the repo root (writes noc_performance_sweep.csv to the current directory)
g++ -std=c++17 -O2 src/noc_sim.cpp -o noc_sim
./noc_sim                     # Windows: noc_sim.exe

# check the results against the analytical model
pip install pandas
python scripts/analytical_validation.py
```

Rerunning `./noc_sim` regenerates the committed CSV exactly (fixed seed). The validation script prints PASS or FAIL for each check, computed from the data, and exits non-zero if any check fails.

## Repository layout

```
src/noc_sim.cpp                       simulator and sweep driver
noc_performance_sweep.csv             sweep output used for all results
scripts/analytical_validation.py      compares results with the analytical models
plots/                                figures generated from the CSV
```

## Design notes

- **Deadlock freedom:** XY routing forbids Y-to-X turns, so no cyclic channel dependency can form on a mesh and virtual channels are not needed to avoid deadlock.
- **Two-phase clock:** all routers decide in Phase 1 using the state at the start of the cycle, and transfers are applied together in Phase 2. This avoids a flit moving several hops in one cycle depending on router evaluation order.
- **Why the knee is sharp:** below saturation the hotspot's input buffers drain faster than they fill, so queuing delay is small. Once arrivals exceed the ejection rate, buffers stay full and latency is set by queue depth and upstream stalls rather than by distance.

## Limitations

- Single-flit packets only: no multi-flit packets or wormhole switching, and no packet-size sweep.
- No virtual channels, so head-of-line blocking is visible in the hotspot results and is not mitigated.
- Latency is measured from entry into the local injection buffer. If that buffer is full, the injection is skipped and not queued, so source queueing delay is excluded and the `OfferedFlits` column counts accepted injections, not attempted ones.
- Latency is reported as a mean only (no p50/p99).
- Self-addressed hotspot injections at node (2,2) are skipped.
- The uniform workload does not reach saturation within the swept range.

## Possible extensions

Count rejected injections and add a bounded source queue, report p50/p99 latency, add virtual channels and measure their effect on hotspot latency, extend the sweep to find the uniform saturation point, multi-flit wormhole packets, additional traffic patterns (transpose, bit-complement), and adaptive routing.
