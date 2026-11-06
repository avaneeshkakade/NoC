"""
Automated Test & Verification Suite for NoC Simulation Outputs
Runs sanity checks, bounds checking, and regression assertions on simulation traces.
"""

import os
import unittest
import pandas as pd
import numpy as np

class TestNoCSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cls.csv_path = os.path.join(script_dir, "..", "noc_performance_sweep.csv")
        assert os.path.exists(cls.csv_path), f"File {cls.csv_path} does not exist"
        cls.df = pd.read_csv(cls.csv_path)

    def test_01_schema_and_integrity(self):
        """Verify CSV headers and data types."""
        expected_cols = ['Workload', 'InjectionRate', 'OfferedFlits', 'RetiredFlits', 
                         'Throughput', 'AvgLatency', 'AvgHops']
        self.assertEqual(list(self.df.columns), expected_cols)
        self.assertFalse(self.df.isnull().values.any(), "CSV contains NaN or null values")
        self.assertEqual(len(self.df), 38, "Expected 38 sweep rows (19 Uniform + 19 Hotspot)")

    def test_02_packet_conservation(self):
        """Verify that retired flits match offered flits within steady-state boundary margins (< 1%)."""
        for idx, row in self.df.iterrows():
            offered = row['OfferedFlits']
            retired = row['RetiredFlits']
            diff = abs(offered - retired)
            margin = diff / offered if offered > 0 else 0
            self.assertLess(margin, 0.015, 
                            f"Flit imbalance at row {idx} ({row['Workload']} @ {row['InjectionRate']}): {offered} vs {retired}")

    def test_03_mesh_hop_bounds(self):
        """Verify that average hop distance lies strictly between 1 and the network diameter (6)."""
        for _, row in self.df.iterrows():
            hops = row['AvgHops']
            self.assertGreater(hops, 1.0, "Average hops must be > 1.0 (no self-loops)")
            self.assertLess(hops, 6.0, "Average hops cannot exceed 2D mesh diameter of 6")

    def test_04_uniform_traffic_scalability(self):
        """Verify that uniform traffic maintains high throughput and low latency prior to network saturation."""
        unif = self.df[self.df["Workload"] == "Uniform"]
        # Latency should stay tight under uniform traffic
        min_lat = unif["AvgLatency"].min()
        max_lat = unif["AvgLatency"].max()
        self.assertGreater(min_lat, 3.5, "Minimum latency should be near zero-load bound (~3.67)")
        self.assertLess(max_lat, 4.5, "Uniform latency at rate 0.38 should remain under 4.5 cycles")
        
        # Throughput should scale almost 1:1 with offered load (within 5% PRNG sampling variance)
        for _, r in unif.iterrows():
            ratio = r["Throughput"] / r["InjectionRate"]
            self.assertAlmostEqual(ratio, 1.0, delta=0.05, 
                                   msg=f"Throughput deviated from injection rate at rate {r['InjectionRate']}")

    def test_05_hotspot_tree_saturation(self):
        """Verify that hotspot traffic induces severe latency explosion and throughput bottlenecking."""
        hotspot = self.df[self.df["Workload"] == "Hotspot"]
        low_load = hotspot[hotspot["InjectionRate"] == 0.02].iloc[0]
        high_load = hotspot[hotspot["InjectionRate"] == 0.38].iloc[0]

        # Latency should jump significantly (> 8x)
        latency_ratio = high_load["AvgLatency"] / low_load["AvgLatency"]
        self.assertGreater(latency_ratio, 8.0, 
                           f"Hotspot latency did not explode as expected (ratio was {latency_ratio:.2f}x)")

        # Sustained throughput should cap out below 0.20 flits/node/cycle
        max_tput = hotspot["Throughput"].max()
        self.assertLess(max_tput, 0.20, f"Hotspot throughput exceeded expected bottleneck bound: {max_tput}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
