"""
Network-on-Chip (NoC) Topology, Routing & Congestion Visualization Suite
Generates diagrams illustrating:
1. 4x4 2D Mesh Topology & Port Microarchitecture
2. Dimension-Order (XY) Routing Flow Paths
3. Tree Saturation & Congestion Heatmap around Hotspot Node (2,2)
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_topology_diagram(output_path):
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
    mesh_dim = 4
    spacing = 2.0
    
    # Draw physical bidirectional inter-router links
    for y in range(mesh_dim):
        for x in range(mesh_dim):
            # Horizontal links (East-West)
            if x < mesh_dim - 1:
                ax.plot([x * spacing, (x + 1) * spacing], [y * spacing, y * spacing],
                        color='#4a5568', lw=3, zorder=1)
                # Bi-directional arrows
                ax.annotate('', xy=((x + 0.6) * spacing, y * spacing),
                            xytext=((x + 0.4) * spacing, y * spacing),
                            arrowprops=dict(arrowstyle="->", color="#718096", lw=1.5))
                ax.annotate('', xy=((x + 0.4) * spacing, y * spacing),
                            xytext=((x + 0.6) * spacing, y * spacing),
                            arrowprops=dict(arrowstyle="->", color="#718096", lw=1.5))
            
            # Vertical links (North-South)
            if y < mesh_dim - 1:
                ax.plot([x * spacing, x * spacing], [y * spacing, (y + 1) * spacing],
                        color='#4a5568', lw=3, zorder=1)
                # Bi-directional arrows
                ax.annotate('', xy=(x * spacing, (y + 0.6) * spacing),
                            xytext=(x * spacing, (y + 0.4) * spacing),
                            arrowprops=dict(arrowstyle="->", color="#718096", lw=1.5))
                ax.annotate('', xy=(x * spacing, (y + 0.4) * spacing),
                            xytext=(x * spacing, (y + 0.6) * spacing),
                            arrowprops=dict(arrowstyle="->", color="#718096", lw=1.5))

    # Draw Routers and Processing Elements (Cores)
    for y in range(mesh_dim):
        for x in range(mesh_dim):
            node_id = y * mesh_dim + x
            px = x * spacing
            py = y * spacing
            
            is_hotspot = (x == 2 and y == 2)
            node_color = '#e53e3e' if is_hotspot else '#3182ce'
            border_color = '#9b2c2c' if is_hotspot else '#2b6cb0'

            # Router Outer Box
            rect = patches.FancyBboxPatch((px - 0.55, py - 0.55), 1.1, 1.1,
                                         boxstyle="round,pad=0.08,rounding_size=0.15",
                                         facecolor=node_color, edgecolor=border_color,
                                         linewidth=2.5, zorder=2, alpha=0.9)
            ax.add_patch(rect)
            
            # Core Tile circle inside
            core_circ = patches.Circle((px, py), 0.32, facecolor='#ffffff', edgecolor='#2d3748', lw=1.5, zorder=3)
            ax.add_patch(core_circ)

            # Labels
            ax.text(px, py + 0.05, f"R{node_id}", color='#1a202c', fontsize=10,
                    fontweight='bold', ha='center', va='center', zorder=4)
            ax.text(px, py - 0.15, f"({x},{y})", color='#4a5568', fontsize=8,
                    fontweight='bold', ha='center', va='center', zorder=4)

            # Hotspot indicator badge
            if is_hotspot:
                ax.text(px, py - 0.75, "HOTSPOT\n(40% Traffic)", color='#c53030', fontsize=9,
                        fontweight='bold', ha='center', va='center',
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="#fed7d7", edgecolor="#feb2b2", lw=1))

    # Example XY route trace from Node 0 (0,0) to Node 10 (2,2)
    ax.annotate('', xy=(2 * spacing, 0 * spacing), xytext=(0 * spacing, 0 * spacing),
                arrowprops=dict(arrowstyle="->", color="#38a169", lw=4, ls="--", zorder=5))
    ax.annotate('', xy=(2 * spacing, 2 * spacing), xytext=(2 * spacing, 0 * spacing),
                arrowprops=dict(arrowstyle="->", color="#d69e2e", lw=4, ls="--", zorder=5))
    
    ax.text(spacing, 0.25, "1. Traverse X-dim (East)", color="#22543d", fontsize=9,
            fontweight='bold', ha='center', bbox=dict(boxstyle='square,pad=0.2', facecolor='#c6f6d5', lw=0))
    ax.text(2 * spacing + 0.3, spacing, "2. Traverse Y-dim (South)", color="#744210", fontsize=9,
            fontweight='bold', ha='left', bbox=dict(boxstyle='square,pad=0.2', facecolor='#fefcbf', lw=0))

    ax.set_xlim(-1.2, (mesh_dim - 1) * spacing + 1.2)
    ax.set_ylim((mesh_dim - 1) * spacing + 1.2, -1.2) # Invert Y so (0,0) is top-left
    ax.set_aspect('equal')
    ax.axis('off')

    plt.title("4x4 2D Mesh Network-on-Chip (NoC) Topology & XY Routing Architecture\n"
              "16 Nodes (Routers R0-R15), 5-Port Crossbar Switches, Deterministic Dimension-Order Routing",
              fontsize=12, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def generate_tree_saturation_heatmap(output_path):
    """
    Computes analytical congestion load across nodes for Uniform vs Hotspot traffic
    and renders dual spatial heatmaps of buffer occupancy & link stress.
    """
    mesh_dim = 4
    nodes = [(x, y) for y in range(mesh_dim) for x in range(mesh_dim)]
    
    # 1. Uniform traffic link stress / node visits
    uniform_visits = np.zeros((mesh_dim, mesh_dim))
    count_u = 0
    for sx, sy in nodes:
        for dx, dy in nodes:
            if sx == dx and sy == dy: continue
            count_u += 1
            # XY routing path:
            # Traverses (sx, sy) -> (dx, sy) -> (dx, dy)
            step_x = 1 if dx >= sx else -1
            for cx in range(sx, dx + step_x, step_x):
                uniform_visits[sy, cx] += 1
            step_y = 1 if dy >= sy else -1
            for cy in range(sy + step_y, dy + step_y, step_y):
                uniform_visits[cy, dx] += 1
    uniform_visits /= count_u

    # 2. Hotspot traffic link stress / node visits (40% to (2,2), 60% uniform)
    hotspot_visits = np.zeros((mesh_dim, mesh_dim))
    trials = 50000
    import random
    random.seed(1337)
    for _ in range(trials):
        sx, sy = random.choice(nodes)
        if random.random() < 0.40:
            dx, dy = 2, 2
        else:
            cand = [n for n in nodes if n != (sx, sy)]
            dx, dy = random.choice(cand)
        if sx == dx and sy == dy: continue

        step_x = 1 if dx >= sx else -1
        for cx in range(sx, dx + step_x, step_x):
            hotspot_visits[sy, cx] += 1
        step_y = 1 if dy >= sy else -1
        for cy in range(sy + step_y, dy + step_y, step_y):
            hotspot_visits[cy, dx] += 1
    hotspot_visits /= trials

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    
    im0 = axes[0].imshow(uniform_visits, cmap="Blues", interpolation="nearest")
    axes[0].set_title("Uniform Random Traffic: Node Load Distribution\n(Balanced Centroid Concentration)",
                      fontweight='bold', fontsize=11)
    for y in range(mesh_dim):
        for x in range(mesh_dim):
            node_id = y * mesh_dim + x
            axes[0].text(x, y, f"R{node_id}\n({x},{y})\n{uniform_visits[y,x]:.2f}",
                         ha="center", va="center", color="black" if uniform_visits[y,x] < uniform_visits.max()*0.7 else "white",
                         fontweight="bold", fontsize=9)
    axes[0].set_xticks(range(4))
    axes[0].set_yticks(range(4))
    axes[0].set_xlabel("X-Coordinate")
    axes[0].set_ylabel("Y-Coordinate")
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label="Normalized Flit Traverse Frequency")

    im1 = axes[1].imshow(hotspot_visits, cmap="Reds", interpolation="nearest")
    axes[1].set_title("Hotspot Traffic: Severe Node Load & Tree Saturation\n(Catastrophic Bottleneck at Node 10 (2,2))",
                      fontweight='bold', fontsize=11)
    for y in range(mesh_dim):
        for x in range(mesh_dim):
            node_id = y * mesh_dim + x
            val = hotspot_visits[y, x]
            axes[1].text(x, y, f"R{node_id}\n({x},{y})\n{val:.2f}",
                         ha="center", va="center", color="black" if val < hotspot_visits.max()*0.6 else "white",
                         fontweight="bold", fontsize=9)
    axes[1].set_xticks(range(4))
    axes[1].set_yticks(range(4))
    axes[1].set_xlabel("X-Coordinate")
    axes[1].set_ylabel("Y-Coordinate")
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label="Normalized Flit Traverse Frequency")

    plt.suptitle("4x4 2D Mesh NoC: Spatial Traffic Distribution & Tree Saturation Analysis",
                 fontweight="bold", fontsize=13, y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "plots")
    os.makedirs(output_dir, exist_ok=True)
    
    topo_path = os.path.join(output_dir, "noc_topology_architecture.png")
    generate_topology_diagram(topo_path)
    print(f"Topology diagram saved to: {topo_path}")

    heatmap_path = os.path.join(output_dir, "noc_tree_saturation_heatmap.png")
    generate_tree_saturation_heatmap(heatmap_path)
    print(f"Saturation heatmap saved to: {heatmap_path}")

if __name__ == "__main__":
    main()
