"""
packet.py
---------
Binary telemetry packet definition, packing, and unpacking.
(Flaxon Nazareth — sat-telemetry-logger)

Packet format (big-endian, 24 bytes total):
  Bytes  0-1  : header      uint16  — magic 0xAA55
  Bytes  2-3  : packet_id   uint16  — sequence counter
  Bytes  4-7  : timestamp   uint32  — ms since boot
  Bytes  8-11 : temperature float32 — deg C
  Bytes 12-15 : pressure    float32 — hPa
  Bytes 16-19 : voltage     float32 — volts
  Bytes 20-21 : status      uint16  — flags
  Bytes 22-23 : checksum    uint16  — sum of bytes 0-21 mod 65536
"""

import struct
from dataclasses import dataclass

PACKET_FORMAT = '>HHIfffH'
PACKET_SIZE   = struct.calcsize(PACKET_FORMAT)   # 22 bytes
HEADER_MAGIC  = 0xAA55
TOTAL_SIZE    = PACKET_SIZE + 2                  # +2 checksum


@dataclass
class TelemetryPacket:
    """Parsed telemetry packet."""
    packet_id:    int
    timestamp_ms: int
    temperature:  float
    pressure:     float
    voltage:      float
    status:       int

    def to_dict(self) -> dict:
        return {
            "packet_id":    self.packet_id,
            "timestamp_ms": self.timestamp_ms,
            "temperature":  round(self.temperature, 4),
            "pressure":     round(self.pressure,    4),
            "voltage":      round(self.voltage,     4),
            "status":       self.status,
        }


def pack_packet(packet_id:    int,
                timestamp_ms: int,
                temperature:  float,
                pressure:     float,
                voltage:      float,
                status:       int = 0x0001) -> bytes:
    """
    Pack sensor values into a binary telemetry packet.

    Returns
    -------
    bytes : 24-byte packet including checksum
    """
    payload  = struct.pack(PACKET_FORMAT, HEADER_MAGIC, packet_id,
                           timestamp_ms, temperature, pressure,
                           voltage, status)
    checksum = sum(payload) % 65536
    return payload + struct.pack('>H', checksum)


def unpack_packet(raw: bytes) -> TelemetryPacket | None:
    """
    Unpack and validate a binary telemetry packet.

    Parameters
    ----------
    raw : bytes
        Raw bytes from serial port or socket

    Returns
    -------
    TelemetryPacket if valid, None if corrupted
    """
    if len(raw) < TOTAL_SIZE:
        return None

    payload  = raw[:PACKET_SIZE]
    checksum = struct.unpack('>H', raw[PACKET_SIZE:TOTAL_SIZE])[0]

    if sum(payload) % 65536 != checksum:
        return None

    header, pkt_id, ts_ms, temp, pressure, voltage, status = \
        struct.unpack(PACKET_FORMAT, payload)

    if header != HEADER_MAGIC:
        return None

    return TelemetryPacket(
        packet_id    = pkt_id,
        timestamp_ms = ts_ms,
        temperature  = temp,
        pressure     = pressure,
        voltage      = voltage,
        status       = status,
    )


if __name__ == "__main__":
    # Self-test
    pkt = pack_packet(1, 5000, 23.5, 1013.25, 3.314)
    parsed = unpack_packet(pkt)
    assert parsed is not None
    assert parsed.temperature == 23.5
    assert parsed.packet_id   == 1
    print("packet.py — self test passed")
    print(f"Packet size: {TOTAL_SIZE} bytes")
    print(f"Parsed: {parsed.to_dict()}")