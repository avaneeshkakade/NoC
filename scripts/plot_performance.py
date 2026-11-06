"""
Network-on-Chip (NoC) Performance Plotting and Visualization Suite
Reads simulation sweep results from 'noc_performance_sweep.csv' and
generates publication-ready figures for technical reporting.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "noc_performance_sweep.csv")
    output_dir = os.path.join(script_dir, "plots")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    print("CSV loaded successfully. Columns:", list(df.columns))

    uniform_df = df[df["Workload"] == "Uniform"].sort_values("InjectionRate")
    hotspot_df = df[df["Workload"] == "Hotspot"].sort_values("InjectionRate")

    # Set overall aesthetic styling
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.8

    # -------------------------------------------------------------
    # Plot 1: Throughput vs Injection Rate
    # -------------------------------------------------------------
    plt.figure(figsize=(8, 5.5), dpi=300)
    plt.plot(uniform_df["InjectionRate"], uniform_df["Throughput"], 'o-', color='#1f77b4', 
             linewidth=2.2, markersize=6, label="Uniform Random Traffic", zorder=3)
    plt.plot(hotspot_df["InjectionRate"], hotspot_df["Throughput"], 's--', color='#d62728', 
             linewidth=2.2, markersize=6, label="Hotspot Traffic (Node 2,2 @ 40%)", zorder=3)
    
    # Ideal theoretical line (Throughput = Offered Load)
    ideal_x = np.linspace(0.02, 0.40, 100)
    plt.plot(ideal_x, ideal_x, ':', color='#7f7f7f', linewidth=1.5, label="Ideal Non-Blocking (Throughput = Rate)", zorder=2)
    
    # Saturation threshold annotation for hotspot
    plt.axvline(x=0.1515, color='#e377c2', linestyle='-.', alpha=0.8, linewidth=1.4, label="Theoretical Hotspot Capacity (~0.152)")
    
    plt.title("Sustained Throughput vs. Offered Injection Rate", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Offered Load / Injection Rate (flits / node / cycle)", fontsize=11, labelpad=8)
    plt.ylabel("Sustained Throughput (flits / node / cycle)", fontsize=11, labelpad=8)
    plt.grid(True, linestyle="--", alpha=0.6, zorder=1)
    plt.legend(frameon=True, facecolor="#f8f9fa", framealpha=0.95, fontsize=10, loc="upper left")
    plt.xlim(0.0, 0.42)
    plt.ylim(0.0, 0.42)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "throughput_vs_injection.png"), dpi=300)
    plt.close()

    # -------------------------------------------------------------
    # Plot 2: Average Latency vs Injection Rate
    # -------------------------------------------------------------
    plt.figure(figsize=(8, 5.5), dpi=300)
    plt.plot(uniform_df["InjectionRate"], uniform_df["AvgLatency"], 'o-', color='#1f77b4', 
             linewidth=2.2, markersize=6, label="Uniform Random Traffic", zorder=3)
    plt.plot(hotspot_df["InjectionRate"], hotspot_df["AvgLatency"], 's--', color='#d62728', 
             linewidth=2.2, markersize=6, label="Hotspot Traffic (Node 2,2 @ 40%)", zorder=3)
    
    # Theoretical zero-load latency reference
    plt.axhline(y=3.6667, color='#2ca02c', linestyle=':', linewidth=1.4, label="Uniform Zero-Load Bound (3.67 cycles)")
    
    plt.title("Average Packet Latency vs. Offered Injection Rate", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Offered Load / Injection Rate (flits / node / cycle)", fontsize=11, labelpad=8)
    plt.ylabel("Average Latency (clock cycles)", fontsize=11, labelpad=8)
    plt.grid(True, linestyle="--", alpha=0.6, zorder=1)
    plt.legend(frameon=True, facecolor="#f8f9fa", framealpha=0.95, fontsize=10, loc="upper left")
    plt.xlim(0.0, 0.42)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency_vs_injection.png"), dpi=300)
    plt.close()

    # -------------------------------------------------------------
    # Plot 3: Latency vs Sustained Throughput (Classic Characteristic Curve)
    # -------------------------------------------------------------
    plt.figure(figsize=(8, 5.5), dpi=300)
    plt.plot(uniform_df["Throughput"], uniform_df["AvgLatency"], 'o-', color='#1f77b4', 
             linewidth=2.2, markersize=6, label="Uniform Random Traffic", zorder=3)
    plt.plot(hotspot_df["Throughput"], hotspot_df["AvgLatency"], 's--', color='#d62728', 
             linewidth=2.2, markersize=6, label="Hotspot Traffic (Severe Saturation)", zorder=3)
    
    plt.title("Latency vs. Throughput Characteristic Curve", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Sustained Network Throughput (flits / node / cycle)", fontsize=11, labelpad=8)
    plt.ylabel("Average Packet Latency (clock cycles)", fontsize=11, labelpad=8)
    plt.grid(True, linestyle="--", alpha=0.6, zorder=1)
    plt.legend(frameon=True, facecolor="#f8f9fa", framealpha=0.95, fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency_vs_throughput.png"), dpi=300)
    plt.close()

    # -------------------------------------------------------------
    # Plot 4: Average Hops vs Injection Rate
    # -------------------------------------------------------------
    plt.figure(figsize=(8, 5.5), dpi=300)
    plt.plot(uniform_df["InjectionRate"], uniform_df["AvgHops"], 'o-', color='#1f77b4', 
             linewidth=2.2, markersize=6, label="Uniform Random (Simulated)", zorder=3)
    plt.plot(hotspot_df["InjectionRate"], hotspot_df["AvgHops"], 's--', color='#d62728', 
             linewidth=2.2, markersize=6, label="Hotspot Traffic (Simulated)", zorder=3)
    
    plt.axhline(y=2.6667, color='#1f77b4', linestyle=':', linewidth=1.5, label="Uniform Analytical Expected Hops (2.667)")
    plt.axhline(y=2.4606, color='#d62728', linestyle=':', linewidth=1.5, label="Hotspot Analytical Expected Hops (2.461)")
    
    plt.title("Average Hop Count vs. Offered Load", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Offered Load / Injection Rate (flits / node / cycle)", fontsize=11, labelpad=8)
    plt.ylabel("Average Manhattan Distance / Hops", fontsize=11, labelpad=8)
    plt.ylim(2.1, 2.9)
    plt.grid(True, linestyle="--", alpha=0.6, zorder=1)
    plt.legend(frameon=True, facecolor="#f8f9fa", framealpha=0.95, fontsize=9.5, loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "hops_vs_injection.png"), dpi=300)
    plt.close()

    # -------------------------------------------------------------
    # Plot 5: 2x2 Master Dashboard Panel
    # -------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    
    # Subplot A: Throughput
    ax = axes[0, 0]
    ax.plot(uniform_df["InjectionRate"], uniform_df["Throughput"], 'o-', color='#1f77b4', label="Uniform", lw=2)
    ax.plot(hotspot_df["InjectionRate"], hotspot_df["Throughput"], 's--', color='#d62728', label="Hotspot (40% Node 10)", lw=2)
    ax.plot(ideal_x, ideal_x, ':', color='gray', label="Ideal Load Line")
    ax.axvline(x=0.1515, color='#9467bd', linestyle='-.', alpha=0.7, label="Theoretical Saturation")
    ax.set_title("(a) Sustained Throughput vs Offered Load", fontweight='bold', fontsize=11)
    ax.set_xlabel("Injection Rate (flits/node/cycle)")
    ax.set_ylabel("Throughput (flits/node/cycle)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8.5, loc="upper left")

    # Subplot B: Latency
    ax = axes[0, 1]
    ax.plot(uniform_df["InjectionRate"], uniform_df["AvgLatency"], 'o-', color='#1f77b4', label="Uniform", lw=2)
    ax.plot(hotspot_df["InjectionRate"], hotspot_df["AvgLatency"], 's--', color='#d62728', label="Hotspot", lw=2)
    ax.axhline(y=3.6667, color='green', linestyle=':', label="Zero-Load Limit (3.67 cycles)")
    ax.set_title("(b) Average Packet Latency vs Offered Load", fontweight='bold', fontsize=11)
    ax.set_xlabel("Injection Rate (flits/node/cycle)")
    ax.set_ylabel("Average Latency (clock cycles)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8.5, loc="upper left")

    # Subplot C: Latency vs Throughput
    ax = axes[1, 0]
    ax.plot(uniform_df["Throughput"], uniform_df["AvgLatency"], 'o-', color='#1f77b4', label="Uniform", lw=2)
    ax.plot(hotspot_df["Throughput"], hotspot_df["AvgLatency"], 's--', color='#d62728', label="Hotspot", lw=2)
    ax.set_title("(c) Network Characteristic Curve (Latency vs Throughput)", fontweight='bold', fontsize=11)
    ax.set_xlabel("Throughput (flits/node/cycle)")
    ax.set_ylabel("Average Latency (clock cycles)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8.5, loc="upper left")

    # Subplot D: Hops
    ax = axes[1, 1]
    ax.plot(uniform_df["InjectionRate"], uniform_df["AvgHops"], 'o-', color='#1f77b4', label="Uniform", lw=2)
    ax.plot(hotspot_df["InjectionRate"], hotspot_df["AvgHops"], 's--', color='#d62728', label="Hotspot", lw=2)
    ax.axhline(y=2.6667, color='#1f77b4', linestyle=':', label="Uniform Analytical (2.667)")
    ax.axhline(y=2.4606, color='#d62728', linestyle=':', label="Hotspot Analytical (2.461)")
    ax.set_title("(d) Average Manhattan Hop Distance vs Offered Load", fontweight='bold', fontsize=11)
    ax.set_xlabel("Injection Rate (flits/node/cycle)")
    ax.set_ylabel("Average Hops")
    ax.set_ylim(2.1, 2.9)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8.5, loc="lower left")

    plt.suptitle("4x4 2D Mesh NoC Simulation: Comprehensive Performance Evaluation", 
                 fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "noc_comprehensive_evaluation.png"), dpi=300)
    plt.close()

    print(f"All performance plots successfully generated in: {output_dir}")

if __name__ == "__main__":
    main()
