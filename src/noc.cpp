#include <iostream>
#include <vector>
#include <queue>
#include <random>
#include <iomanip>
#include <fstream>
#include <string>
#include <algorithm>

constexpr int MESH_DIM = 4;
constexpr int NUM_NODES = MESH_DIM * MESH_DIM;
constexpr int BUFFER_DEPTH = 4;

enum Port {
    LOCAL = 0,
    NORTH = 1,
    SOUTH = 2,
    EAST  = 3,
    WEST  = 4,
    NUM_PORTS = 5
};

struct Flit {
    uint64_t id;
    int src_x, src_y;
    int dest_x, dest_y;
    uint64_t birth_cycle;
    int hops;
};

inline int get_id(int x, int y) {
    return y * MESH_DIM + x;
}

Port route_xy(int cur_x, int cur_y, int dst_x, int dst_y) {
    if (dst_x > cur_x) return EAST;
    if (dst_x < cur_x) return WEST;
    if (dst_y > cur_y) return SOUTH;
    if (dst_y < cur_y) return NORTH;
    return LOCAL;
}

class Router {
public:
    int x, y, id;
    std::queue<Flit> in_buffers[NUM_PORTS];
    int arb_rr_ptr[NUM_PORTS];

    Router(int px = 0, int py = 0, int pid = 0) : x(px), y(py), id(pid) {
        for (int p = 0; p < NUM_PORTS; ++p) {
            arb_rr_ptr[p] = 0;
        }
    }

    bool has_buffer_space(Port p) const {
        return in_buffers[p].size() < BUFFER_DEPTH;
    }

    int arbitrate_output_port(Port out_p) {
        int start_in_p = arb_rr_ptr[out_p];

        for (int step = 0; step < NUM_PORTS; ++step) {
            int candidate_in_p = (start_in_p + step) % NUM_PORTS;

            if (!in_buffers[candidate_in_p].empty()) {
                const Flit& front_flit = in_buffers[candidate_in_p].front();
                Port requested_out_p = route_xy(x, y, front_flit.dest_x, front_flit.dest_y);

                if (requested_out_p == out_p) {
                    return candidate_in_p;
                }
            }
        }
        return -1;
    }

    void advance_arbiter(Port out_p, int granted_in_p) {
        arb_rr_ptr[out_p] = (granted_in_p + 1) % NUM_PORTS;
    }
};

struct PendingTransfer {
    int src_router_id;
    Port src_in_port;
    int dst_router_id;
    Port dst_in_port;
    Flit flit;
};

struct ExperimentResult {
    double injection_rate;
    uint64_t injected;
    uint64_t retired;
    double avg_latency;
    double throughput;
    double avg_hops;
};

class NoCNetwork {
public:
    std::vector<Router> routers;
    uint64_t current_cycle = 0;
    uint64_t flit_id_gen = 0;

    uint64_t total_injected_flits = 0;
    uint64_t total_retired_flits = 0;
    uint64_t total_latency_cycles = 0;
    uint64_t total_hops_traversed = 0;
    std::vector<uint64_t> cumulative_buffer_occupancy;

    std::mt19937 rng;
    std::uniform_real_distribution<double> dist_prob;
    std::uniform_int_distribution<int> dist_node;

    NoCNetwork(unsigned int seed = 42)
        : rng(seed), dist_prob(0.0, 1.0), dist_node(0, NUM_NODES - 1),
          cumulative_buffer_occupancy(NUM_NODES, 0) {
        routers.resize(NUM_NODES);
        for (int y = 0; y < MESH_DIM; ++y) {
            for (int x = 0; x < MESH_DIM; ++x) {
                int id = get_id(x, y);
                routers[id] = Router(x, y, id);
            }
        }
    }

    void inject_traffic(double injection_rate, bool hotspot_enabled) {
        const int HOTSPOT_NODE_ID = get_id(2, 2);
        const double HOTSPOT_BIAS = 0.40;

        for (int src_id = 0; src_id < NUM_NODES; ++src_id) {
            if (dist_prob(rng) < injection_rate) {
                if (!routers[src_id].has_buffer_space(LOCAL)) continue;

                int dst_id;
                if (hotspot_enabled && dist_prob(rng) < HOTSPOT_BIAS) {
                    dst_id = HOTSPOT_NODE_ID;
                } else {
                    do {
                        dst_id = dist_node(rng);
                    } while (dst_id == src_id);
                }

                if (dst_id == src_id) continue;

                Flit f;
                f.id = ++flit_id_gen;
                f.src_x = routers[src_id].x;
                f.src_y = routers[src_id].y;
                f.dest_x = dst_id % MESH_DIM;
                f.dest_y = dst_id / MESH_DIM;
                f.birth_cycle = current_cycle;
                f.hops = 0;

                routers[src_id].in_buffers[LOCAL].push(f);
                total_injected_flits++;
            }
        }
    }

    void step() {
        current_cycle++;

        for (int i = 0; i < NUM_NODES; ++i) {
            uint64_t occ = 0;
            for (int p = 0; p < NUM_PORTS; ++p) {
                occ += routers[i].in_buffers[p].size();
            }
            cumulative_buffer_occupancy[i] += occ;
        }

        std::vector<PendingTransfer> transfers;
        std::vector<Flit> retiring_flits;

        for (int i = 0; i < NUM_NODES; ++i) {
            Router& r = routers[i];
            for (int out_p = 0; out_p < NUM_PORTS; ++out_p) {
                Port egress = static_cast<Port>(out_p);
                int win_in_p = r.arbitrate_output_port(egress);
                if (win_in_p == -1) continue;

                Flit moving_flit = r.in_buffers[win_in_p].front();

                if (egress == LOCAL) {
                    r.in_buffers[win_in_p].pop();
                    r.advance_arbiter(egress, win_in_p);
                    retiring_flits.push_back(moving_flit);
                } else {
                    int nx = r.x, ny = r.y;
                    Port neighbor_in_port;

                    if (egress == EAST)  { nx++; neighbor_in_port = WEST; }
                    if (egress == WEST)  { nx--; neighbor_in_port = EAST; }
                    if (egress == SOUTH) { ny++; neighbor_in_port = NORTH; }
                    if (egress == NORTH) { ny--; neighbor_in_port = SOUTH; }

                    if (nx >= 0 && nx < MESH_DIM && ny >= 0 && ny < MESH_DIM) {
                        int nid = get_id(nx, ny);

                        if (routers[nid].has_buffer_space(neighbor_in_port)) {
                            r.in_buffers[win_in_p].pop();
                            r.advance_arbiter(egress, win_in_p);
                            moving_flit.hops++;
                            transfers.push_back({i, static_cast<Port>(win_in_p), nid, neighbor_in_port, moving_flit});
                        }
                    }
                }
            }
        }

        for (const auto& t : transfers) {
            routers[t.dst_router_id].in_buffers[t.dst_in_port].push(t.flit);
        }

        for (const auto& rf : retiring_flits) {
            total_retired_flits++;
            total_latency_cycles += (current_cycle - rf.birth_cycle);
            total_hops_traversed += rf.hops;
        }
    }

    void reset_metrics() {
        total_injected_flits = 0;
        total_retired_flits = 0;
        total_latency_cycles = 0;
        total_hops_traversed = 0;
        std::fill(cumulative_buffer_occupancy.begin(), cumulative_buffer_occupancy.end(), 0);
    }
};

ExperimentResult run_sweep_point(double injection_rate, bool hotspot_mode,
                                 int warmup_cycles = 500, int sample_cycles = 2500) {
    NoCNetwork net(1337);

    for (int c = 0; c < warmup_cycles; ++c) {
        net.inject_traffic(injection_rate, hotspot_mode);
        net.step();
    }

    net.reset_metrics();

    for (int c = 0; c < sample_cycles; ++c) {
        net.inject_traffic(injection_rate, hotspot_mode);
        net.step();
    }

    ExperimentResult res;
    res.injection_rate = injection_rate;
    res.injected = net.total_injected_flits;
    res.retired = net.total_retired_flits;
    res.throughput = static_cast<double>(net.total_retired_flits) / (sample_cycles * NUM_NODES);
    res.avg_latency = (net.total_retired_flits > 0)
        ? (static_cast<double>(net.total_latency_cycles) / net.total_retired_flits) : 0.0;
    res.avg_hops = (net.total_retired_flits > 0)
        ? (static_cast<double>(net.total_hops_traversed) / net.total_retired_flits) : 0.0;

    return res;
}

int main() {
    std::ofstream csv("noc_performance_sweep.csv");
    csv << "Workload,InjectionRate,OfferedFlits,RetiredFlits,Throughput,AvgLatency,AvgHops\n";

    std::cout << "Running parametric sweeps across uniform and hotspot workloads...\n\n";

    for (double rate = 0.02; rate <= 0.40; rate += 0.02) {
        auto res = run_sweep_point(rate, false);
        csv << "Uniform," << res.injection_rate << "," << res.injected << ","
            << res.retired << "," << res.throughput << "," << res.avg_latency << ","
            << res.avg_hops << "\n";
    }

    for (double rate = 0.02; rate <= 0.40; rate += 0.02) {
        auto res = run_sweep_point(rate, true);
        csv << "Hotspot," << res.injection_rate << "," << res.injected << ","
            << res.retired << "," << res.throughput << "," << res.avg_latency << ","
            << res.avg_hops << "\n";
    }

    csv.close();
    std::cout << "Data collection complete -> exported to 'noc_performance_sweep.csv'\n";
    return 0;
}
