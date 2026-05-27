"""
monitor.py
----------
Real-time telemetry monitoring and anomaly detection.
(Flaxon Nazareth — sat-telemetry-logger)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
from pathlib import Path
from collections import deque


class TelemetryMonitor:
    """
    Real-time telemetry monitor with anomaly detection.

    Parameters
    ----------
    window_size : int
        Number of recent packets to display
    thresholds  : dict
        Anomaly thresholds per channel
    """

    def __init__(self, window_size: int = 100,
                 thresholds: dict = None):
        self.window   = window_size
        self.t        = deque(maxlen=window_size)
        self.temp     = deque(maxlen=window_size)
        self.pressure = deque(maxlen=window_size)
        self.voltage  = deque(maxlen=window_size)
        self.anomalies = []

        self.thresholds = thresholds or {
            "voltage_min":  3.2,
            "voltage_max":  3.5,
            "temp_min":     15.0,
            "temp_max":     40.0,
            "pressure_min": 1000.0,
            "pressure_max": 1030.0,
        }

    def ingest(self, record: dict):
        """Add a new record and check for anomalies."""
        self.t.append(record['timestamp_ms'] / 1000.0)
        self.temp.append(record['temperature'])
        self.pressure.append(record['pressure'])
        self.voltage.append(record['voltage'])
        self._check_anomaly(record)

    def ingest_all(self, records: list):
        """Ingest a list of records."""
        for r in records:
            self.ingest(r)

    def _check_anomaly(self, record: dict):
        """Flag record if any channel outside threshold."""
        flags = []
        th = self.thresholds

        if record['voltage'] < th['voltage_min']:
            flags.append(f"LOW_VOLTAGE ({record['voltage']:.3f}V)")
        if record['voltage'] > th['voltage_max']:
            flags.append(f"HIGH_VOLTAGE ({record['voltage']:.3f}V)")
        if record['temperature'] > th['temp_max']:
            flags.append(f"HIGH_TEMP ({record['temperature']:.2f}C)")
        if record['temperature'] < th['temp_min']:
            flags.append(f"LOW_TEMP ({record['temperature']:.2f}C)")

        if flags:
            self.anomalies.append({
                "packet_id": record['packet_id'],
                "timestamp": record['timestamp_ms'],
                "flags":     ", ".join(flags)
            })

    def anomaly_report(self) -> pd.DataFrame:
        """Return anomaly log as DataFrame."""
        if not self.anomalies:
            return pd.DataFrame(
                columns=['packet_id', 'timestamp', 'flags'])
        return pd.DataFrame(self.anomalies)

    def plot_snapshot(self,
                      save_path: str = "figures/telemetry_monitor.png"):
        """Plot current telemetry window."""
        t_arr = np.array(self.t)
        th    = self.thresholds

        fig, axes = plt.subplots(3, 1, figsize=(12, 8),
                                  facecolor='#0F1117')
        fig.suptitle('Telemetry Monitor — Live Snapshot',
                     color='white', fontsize=11)

        panels = [
            (self.temp,     'Temperature (°C)', '#1D9E75',
             th['temp_min'],     th['temp_max']),
            (self.pressure, 'Pressure (hPa)',   '#7B6FE8',
             th['pressure_min'], th['pressure_max']),
            (self.voltage,  'Voltage (V)',       '#E8836F',
             th['voltage_min'],  th['voltage_max']),
        ]

        for ax, (data, ylabel, color, lo, hi) in zip(axes, panels):
            arr = np.array(data)
            ax.set_facecolor('#1A1D27')
            ax.plot(t_arr, arr, color=color, lw=1.5)
            ax.fill_between(t_arr, arr, alpha=0.15, color=color)
            ax.axhline(lo, color='#FF4444', lw=1,
                       linestyle='--', alpha=0.7, label=f'Min {lo}')
            ax.axhline(hi, color='#FF4444', lw=1,
                       linestyle='--', alpha=0.7, label=f'Max {hi}')
            ax.axhline(np.mean(arr), color='#FF6600', lw=1,
                       linestyle=':', alpha=0.7,
                       label=f'Mean {np.mean(arr):.3f}')
            ax.set_ylabel(ylabel, color='#AAAAAA', fontsize=9)
            ax.tick_params(colors='#AAAAAA', labelsize=8)
            ax.grid(alpha=0.15, color='white')
            ax.legend(fontsize=7, facecolor='#1A1D27',
                      labelcolor='white', loc='upper right')
            for sp in ax.spines.values():
                sp.set_edgecolor('#333344')

        axes[-1].set_xlabel('Time (seconds)', color='#AAAAAA')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150,
                    bbox_inches='tight', facecolor='#0F1117')
        plt.show()
        print(f"Saved: {save_path}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from src.stream import run_stream

    print("monitor.py — self test")
    print("=" * 45)

    print("Capturing 10 seconds @ 10 Hz...")
    records = run_stream(duration_s=10.0, rate_hz=10.0)

    monitor = TelemetryMonitor(window_size=200)
    monitor.ingest_all(records)

    print(f"Ingested: {len(records)} records")

    # Anomaly report
    anomalies = monitor.anomaly_report()
    if anomalies.empty:
        print("Anomalies: none detected")
    else:
        print(f"Anomalies detected: {len(anomalies)}")
        print(anomalies.to_string(index=False))

    # Plot
    monitor.plot_snapshot("figures/telemetry_monitor.png")

    # Stats
    print(f"\nWindow stats:")
    print(f"  Temp:     {np.mean(monitor.temp):.3f} C")
    print(f"  Pressure: {np.mean(monitor.pressure):.3f} hPa")
    print(f"  Voltage:  {np.mean(monitor.voltage):.3f} V")