"""
Analytical validation of the NoC sweep results.

Compares the simulator output (noc_performance_sweep.csv) with closed-form
predictions for a 4x4 mesh. Every PASS/FAIL below is computed from the data,
and the script exits non-zero if any check fails.

Checks
  1. Mean hop count, uniform traffic   -> average Manhattan distance over all pairs
  2. Zero-load latency                 -> hops + 1 (one cycle per hop, one to eject)
  3. Flit conservation                 -> offered ~= retired in steady state
  4. Hotspot saturation knee           -> ejection-port bound 1 / (15 * 0.44)
  5. Hotspot throughput plateau        -> throughput flattens after the knee

Usage: python analytical_validation.py [path/to/noc_performance_sweep.csv]
"""

import os
import sys

import pandas as pd

MESH_DIM = 4
NUM_NODES = MESH_DIM * MESH_DIM
HOTSPOT_BIAS = 0.40          # fraction of injections aimed at the hotspot node
HOP_TOL_PCT = 0.5            # allowed error for the hop count and zero-load latency
CONSERVATION_TOL_PCT = 1.5   # allowed |offered - retired| / offered
KNEE_FACTOR = 2.0            # knee = first rate where latency exceeds 2x its low-load value

failures = 0


def check(name, passed, detail):
    """Print one result line and count failures."""
    global failures
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    if not passed:
        failures += 1


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "noc_performance_sweep.csv")
    if not os.path.exists(csv_path):
        sys.exit(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    uniform = df[df["Workload"] == "Uniform"].sort_values("InjectionRate")
    hotspot = df[df["Workload"] == "Hotspot"].sort_values("InjectionRate")

    # ---- Topology facts ----------------------------------------------------
    nodes = [(x, y) for y in range(MESH_DIM) for x in range(MESH_DIM)]
    dists = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a in nodes for b in nodes if a != b]
    theory_hops = sum(dists) / len(dists)  # equals 8/3 for a 4x4 mesh

    print("Topology (4x4 mesh)")
    print(f"  diameter            : {2 * (MESH_DIM - 1)} hops")
    print(f"  bisection           : {MESH_DIM} links per direction ({2 * MESH_DIM} unidirectional channels)")
    print(f"  mean hops, uniform  : {theory_hops:.5f} (8/3)")

    # ---- 1. Mean hops ------------------------------------------------------
    print("\nUniform traffic")
    sim_hops = uniform["AvgHops"].mean()
    err = abs(sim_hops - theory_hops) / theory_hops * 100
    check("mean hops", err < HOP_TOL_PCT,
          f"simulated {sim_hops:.4f} vs theory {theory_hops:.4f} ({err:.3f}% error, limit {HOP_TOL_PCT}%)")

    # ---- 2. Zero-load latency ----------------------------------------------
    t0_theory = theory_hops + 1.0
    t0_sim = uniform["AvgLatency"].iloc[0]  # lowest injection rate in the sweep
    err = abs(t0_sim - t0_theory) / t0_theory * 100
    check("zero-load latency", err < HOP_TOL_PCT,
          f"simulated {t0_sim:.4f} vs theory {t0_theory:.4f} cycles ({err:.3f}% error, limit {HOP_TOL_PCT}%)")

    # ---- 3. Conservation (all rows, both workloads) -------------------------
    imbalance = (df["OfferedFlits"] - df["RetiredFlits"]).abs() / df["OfferedFlits"] * 100
    check("flit conservation", imbalance.max() < CONSERVATION_TOL_PCT,
          f"worst offered/retired mismatch {imbalance.max():.3f}% over {len(df)} runs (limit {CONSERVATION_TOL_PCT}%)")

    # ---- 4. Hotspot knee ----------------------------------------------------
    # Each of the other 15 nodes sends 0.40 + 0.60/15 = 0.44 of its flits to the hotspot.
    # The hotspot ejects 1 flit/cycle, so it saturates when 15 * 0.44 * lambda = 1.
    others = NUM_NODES - 1
    share = HOTSPOT_BIAS + (1 - HOTSPOT_BIAS) / others
    lam_crit = 1.0 / (others * share)

    print("\nHotspot traffic")
    print(f"  share of each node's flits to hotspot : {share:.2f}")
    print(f"  theoretical knee                      : lambda = 1 / ({others} * {share:.2f}) = {lam_crit:.4f}")

    base_latency = hotspot["AvgLatency"].iloc[0]
    over = hotspot[hotspot["AvgLatency"] > KNEE_FACTOR * base_latency]
    if over.empty:
        check("saturation knee", False, f"latency never exceeded {KNEE_FACTOR}x its low-load value")
        knee_rate = None
    else:
        knee_rate = over["InjectionRate"].iloc[0]
        last_ok = hotspot[hotspot["InjectionRate"] < knee_rate]["InjectionRate"].iloc[-1]
        check("saturation knee", last_ok - 1e-9 <= lam_crit <= knee_rate + 1e-9,
              f"latency passes {KNEE_FACTOR}x low-load between lambda = {last_ok:.2f} and {knee_rate:.2f}; "
              f"theory {lam_crit:.4f}")

    # ---- 5. Throughput plateau ----------------------------------------------
    if knee_rate is not None:
        after = hotspot[hotspot["InjectionRate"] > knee_rate + 1e-9]
        ratio = after["Throughput"].max() / after["Throughput"].min()
        below_offered = bool((after["Throughput"] < after["InjectionRate"]).all())
        check("throughput plateau", ratio < 1.10 and below_offered,
              f"beyond the knee throughput stays within {after['Throughput'].min():.4f}-{after['Throughput'].max():.4f} "
              f"(max/min {ratio:.3f}) and below offered load: {below_offered}")

    # ---- Summary table ------------------------------------------------------
    print("\nSelected points (throughput in flits/cycle/node, latency in cycles)")
    print(f"  {'rate':>5} | {'uniform tput':>12} {'uniform lat':>11} | {'hotspot tput':>12} {'hotspot lat':>11}")
    for rate in [0.02, 0.08, 0.14, 0.16, 0.20, 0.30, 0.38]:
        u = uniform[(uniform["InjectionRate"] - rate).abs() < 1e-9]
        h = hotspot[(hotspot["InjectionRate"] - rate).abs() < 1e-9]
        if u.empty or h.empty:
            continue
        u, h = u.iloc[0], h.iloc[0]
        print(f"  {rate:5.2f} | {u['Throughput']:12.4f} {u['AvgLatency']:11.2f} | "
              f"{h['Throughput']:12.4f} {h['AvgLatency']:11.2f}")

    print()
    print("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()