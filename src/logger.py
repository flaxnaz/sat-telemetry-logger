"""
logger.py
---------
CSV and SQLite logging for telemetry records.
(Flaxon Nazareth — sat-telemetry-logger)
"""

import csv
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime


class TelemetryLogger:
    """
    Logs telemetry records to CSV and SQLite simultaneously.

    Parameters
    ----------
    output_dir : Path or str
        Directory for output files
    session_name : str
        Name prefix for output files
    """

    def __init__(self, output_dir: str = "output",
                 session_name: str = None):
        self.output_dir   = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.session_name = session_name
        self.csv_path     = self.output_dir / f"{session_name}.csv"
        self.db_path      = self.output_dir / f"{session_name}.db"

        # CSV setup
        self._csv_file    = None
        self._csv_writer  = None

        # SQLite setup
        self._conn = sqlite3.connect(str(self.db_path))
        self._setup_db()

        print(f"Logger initialised")
        print(f"  CSV:    {self.csv_path}")
        print(f"  SQLite: {self.db_path}")

    def _setup_db(self):
        """Create telemetry table if not exists."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                packet_id    INTEGER,
                timestamp_ms INTEGER,
                temperature  REAL,
                pressure     REAL,
                voltage      REAL,
                status       INTEGER,
                wall_time    TEXT
            )
        """)
        self._conn.commit()

    def _open_csv(self, fieldnames: list):
        """Open CSV file and write header."""
        self._csv_file   = open(self.csv_path, 'w', newline='')
        self._csv_writer = csv.DictWriter(
            self._csv_file, fieldnames=fieldnames)
        self._csv_writer.writeheader()

    def log(self, record: dict):
        """
        Log a single telemetry record to CSV and SQLite.

        Parameters
        ----------
        record : dict
            Parsed telemetry record from TelemetryConsumer
        """
        # CSV — open on first record
        if self._csv_writer is None:
            self._open_csv(list(record.keys()))
        self._csv_writer.writerow(record)

        # SQLite
        self._conn.execute("""
            INSERT INTO telemetry
            (packet_id, timestamp_ms, temperature,
             pressure, voltage, status, wall_time)
            VALUES (?,?,?,?,?,?,?)
        """, (
            record['packet_id'],
            record['timestamp_ms'],
            record['temperature'],
            record['pressure'],
            record['voltage'],
            record['status'],
            record['wall_time']
        ))
        self._conn.commit()

    def log_all(self, records: list):
        """Log a list of records at once."""
        for r in records:
            self.log(r)
        if self._csv_file:
            self._csv_file.flush()
        print(f"Logged {len(records)} records")

    def query(self, sql: str) -> pd.DataFrame:
        """Run a SQL query and return as DataFrame."""
        return pd.read_sql_query(sql, self._conn)

    def summary(self) -> pd.DataFrame:
        """Return summary statistics from SQLite."""
        return self.query("""
            SELECT
                COUNT(*)        AS n_packets,
                MIN(temperature) AS temp_min,
                AVG(temperature) AS temp_mean,
                MAX(temperature) AS temp_max,
                MIN(pressure)    AS pressure_min,
                AVG(pressure)    AS pressure_mean,
                MAX(pressure)    AS pressure_max,
                MIN(voltage)     AS voltage_min,
                AVG(voltage)     AS voltage_mean,
                MAX(voltage)     AS voltage_max
            FROM telemetry
        """)

    def close(self):
        """Close all file handles."""
        if self._csv_file:
            self._csv_file.close()
        self._conn.close()
        print(f"Logger closed — "
              f"CSV: {self.csv_path.stat().st_size} bytes, "
              f"DB: {self.db_path.stat().st_size} bytes")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from src.stream import run_stream

    print("logger.py — self test")
    print("=" * 45)

    # Capture 5 seconds of telemetry
    print("Capturing 5 seconds @ 10 Hz...")
    records = run_stream(duration_s=5.0, rate_hz=10.0)

    # Log everything
    logger = TelemetryLogger(
        output_dir   = "output",
        session_name = "test_session"
    )
    logger.log_all(records)

    # Query from SQLite
    print("\nSQL query — last 5 records:")
    df = logger.query(
        "SELECT packet_id, timestamp_ms, temperature, "
        "voltage FROM telemetry ORDER BY id DESC LIMIT 5"
    )
    print(df.to_string(index=False))

    # Summary stats
    print("\nSummary statistics:")
    summary = logger.summary()
    for col in summary.columns:
        print(f"  {col:20s}: {summary[col].iloc[0]:.4f}"
              if summary[col].dtype == float
              else f"  {col:20s}: {summary[col].iloc[0]}")

    logger.close()