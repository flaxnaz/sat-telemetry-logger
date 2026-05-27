"""
sat-telemetry-logger
====================
Configurable satellite telemetry capture, parse, log, and monitor tool.

Author : Flaxon Nazareth
Context: Portfolio Project 2 — HEO production engineering role target
         Demonstrates: binary packet parsing, threaded data pipeline,
         CSV + SQLite logging, real-time anomaly detection

Usage
-----
    python main.py
    python main.py --duration 30 --rate 20

Outputs
-------
    output/<session>.csv
    output/<session>.db
    figures/telemetry_monitor.png
"""

import sys
import os
import argparse
import yaml
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stream  import run_stream
from logger  import TelemetryLogger
from monitor import TelemetryMonitor


def load_config(path: str = "config.yaml") -> dict:
    """Load YAML config, return defaults if not found."""
    defaults = {
        "session": {
            "duration_s": 10.0,
            "rate_hz":    10.0,
            "name":       None
        },
        "thresholds": {
            "voltage_min":  3.2,
            "voltage_max":  3.5,
            "temp_min":     15.0,
            "temp_max":     40.0,
            "pressure_min": 1000.0,
            "pressure_max": 1030.0
        },
        "output": {
            "dir":     "output",
            "figures": "figures"
        }
    }
    p = Path(path)
    if p.exists():
        with open(p) as f:
            loaded = yaml.safe_load(f)
        # Merge with defaults
        for key in defaults:
            if key in loaded:
                defaults[key].update(loaded[key])
    return defaults


def main():
    # ── CLI arguments ─────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Satellite telemetry logger")
    parser.add_argument("--duration", type=float,
                        help="Capture duration in seconds")
    parser.add_argument("--rate",     type=float,
                        help="Packet rate in Hz")
    parser.add_argument("--config",   type=str,
                        default="config.yaml",
                        help="Path to YAML config file")
    args = parser.parse_args()

    # ── Load config ───────────────────────────────────────────
    cfg      = load_config(args.config)
    duration = args.duration or cfg['session']['duration_s']
    rate     = args.rate     or cfg['session']['rate_hz']
    name     = cfg['session']['name'] or \
               datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir  = cfg['output']['dir']
    fig_dir  = cfg['output']['figures']

    Path(fig_dir).mkdir(exist_ok=True)

    # ── Run ───────────────────────────────────────────────────
    print("=" * 55)
    print("  sat-telemetry-logger — Flaxon Nazareth")
    print("=" * 55)
    print(f"  Session:  {name}")
    print(f"  Duration: {duration}s @ {rate} Hz")
    print(f"  Expected: {int(duration*rate)} packets")
    print("=" * 55)

    # 1 — Capture
    print(f"\n[1/4] Capturing telemetry stream...")
    records = run_stream(duration_s=duration, rate_hz=rate)
    print(f"      Captured: {len(records)} packets")
    loss = 1 - len(records) / (duration * rate)
    print(f"      Loss:     {loss*100:.1f}%")

    # 2 — Log
    print(f"\n[2/4] Logging to CSV and SQLite...")
    logger = TelemetryLogger(output_dir=out_dir,
                             session_name=name)
    logger.log_all(records)

    # Summary from DB
    summary = logger.summary()
    print(f"\n      Summary:")
    print(f"        Temp:     "
          f"{summary['temp_mean'].iloc[0]:.3f} C  "
          f"(min {summary['temp_min'].iloc[0]:.3f}, "
          f"max {summary['temp_max'].iloc[0]:.3f})")
    print(f"        Pressure: "
          f"{summary['pressure_mean'].iloc[0]:.3f} hPa")
    print(f"        Voltage:  "
          f"{summary['voltage_mean'].iloc[0]:.3f} V")

    logger.close()

    # 3 — Monitor and anomaly detection
    print(f"\n[3/4] Running anomaly detection...")
    monitor = TelemetryMonitor(
        window_size = len(records),
        thresholds  = cfg['thresholds']
    )
    monitor.ingest_all(records)

    anomalies = monitor.anomaly_report()
    if anomalies.empty:
        print(f"      No anomalies detected")
    else:
        print(f"      Anomalies: {len(anomalies)}")
        print(anomalies.to_string(index=False))

    # 4 — Plot
    print(f"\n[4/4] Generating monitor plot...")
    plot_path = str(Path(fig_dir) / f"{name}_monitor.png")
    monitor.plot_snapshot(plot_path)

    print("\n" + "=" * 55)
    print("  Complete. Outputs:")
    print(f"    {out_dir}/{name}.csv")
    print(f"    {out_dir}/{name}.db")
    print(f"    {plot_path}")
    print("=" * 55)


if __name__ == "__main__":
    main()
    