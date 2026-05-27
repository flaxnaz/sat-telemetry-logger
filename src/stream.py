"""
stream.py
---------
Sensor data producer (simulated or real serial port)
and consumer pipeline.
(Flaxon Nazareth — sat-telemetry-logger)
"""

import threading
import queue
import time
import numpy as np
from packet import pack_packet, unpack_packet, TelemetryPacket


class SensorProducer(threading.Thread):
    """
    Simulates a hardware sensor sending telemetry packets.
    In production: replace with pyserial.Serial().read()

    Parameters
    ----------
    q        : queue.Queue — shared packet queue
    rate_hz  : float       — packets per second
    duration : float       — seconds to run (None = forever)
    """

    def __init__(self, q: queue.Queue,
                 rate_hz:  float = 10.0,
                 duration: float = None):
        super().__init__(daemon=True)
        self.q        = q
        self.rate_hz  = rate_hz
        self.duration = duration
        self.stop     = threading.Event()
        self.n_sent   = 0

    def run(self):
        dt     = 1.0 / self.rate_hz
        pkt_id = 0
        t0     = time.time()

        while not self.stop.is_set():
            t_now = time.time() - t0

            if self.duration and t_now >= self.duration:
                break

            # Simulated sensor values with realistic noise
            temp     = 22.0 + 3.0*np.sin(0.1*t_now) \
                       + np.random.normal(0, 0.1)
            pressure = 1013.0 + 2.0*np.sin(0.05*t_now) \
                       + np.random.normal(0, 0.05)
            voltage  = 3.3 + 0.05*np.sin(0.2*t_now) \
                       + np.random.normal(0, 0.01)
            status   = 0x0001 if voltage > 3.2 else 0x0002

            raw = pack_packet(
                packet_id    = pkt_id,
                timestamp_ms = int(t_now * 1000),
                temperature  = float(temp),
                pressure     = float(pressure),
                voltage      = float(voltage),
                status       = status
            )
            self.q.put(raw)
            pkt_id       += 1
            self.n_sent  += 1
            time.sleep(dt)

    def shutdown(self):
        self.stop.set()


class TelemetryConsumer(threading.Thread):
    """
    Reads raw packets from queue, parses them, and
    appends to a shared records list.

    Parameters
    ----------
    q       : queue.Queue     — shared packet queue
    records : list            — shared output list
    """

    def __init__(self, q: queue.Queue, records: list):
        super().__init__(daemon=True)
        self.q          = q
        self.records    = records
        self.stop       = threading.Event()
        self.n_received = 0
        self.n_corrupt  = 0

    def run(self):
        from datetime import datetime
        while not self.stop.is_set() or not self.q.empty():
            try:
                raw    = self.q.get(timeout=0.1)
                parsed = unpack_packet(raw)
                if parsed:
                    d = parsed.to_dict()
                    d['wall_time'] = datetime.now().isoformat()
                    self.records.append(d)
                    self.n_received += 1
                else:
                    self.n_corrupt += 1
            except queue.Empty:
                continue

    def shutdown(self):
        self.stop.set()


def run_stream(duration_s: float = 5.0,
               rate_hz:    float = 10.0) -> list:
    """
    Run producer/consumer pipeline for duration_s seconds.

    Returns
    -------
    list of dict — parsed telemetry records
    """
    q       = queue.Queue()
    records = []

    producer = SensorProducer(q, rate_hz=rate_hz,
                               duration=duration_s)
    consumer = TelemetryConsumer(q, records)

    producer.start()
    consumer.start()

    time.sleep(duration_s + 0.5)   # wait for completion

    producer.shutdown()
    consumer.shutdown()
    producer.join()
    consumer.join()

    return records


if __name__ == "__main__":
    print("stream.py — self test (5 seconds @ 10 Hz)")
    print("-" * 45)

    records = run_stream(duration_s=5.0, rate_hz=10.0)

    print(f"Captured:  {len(records)} packets")
    print(f"First:     {records[0]}")
    print(f"Last:      {records[-1]}")

    loss = 1 - len(records) / 50.0
    print(f"Loss rate: {loss*100:.1f}%")