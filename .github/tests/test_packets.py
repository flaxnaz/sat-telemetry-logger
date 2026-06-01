"""
test_packet.py
--------------
Tests for packet.py — binary telemetry packet parsing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from packet import pack_packet, unpack_packet, TelemetryPacket, TOTAL_SIZE


# ── Basic pack/unpack roundtrip ───────────────────────────────

def test_roundtrip_basic():
    """Pack then unpack should return original values."""
    raw = pack_packet(1, 5000, 23.5, 1013.25, 3.314)
    pkt = unpack_packet(raw)
    assert pkt is not None
    assert pkt.packet_id    == 1
    assert pkt.timestamp_ms == 5000
    assert abs(pkt.temperature - 23.5)    < 1e-4
    assert abs(pkt.pressure   - 1013.25)  < 1e-3
    assert abs(pkt.voltage    - 3.314)    < 1e-4

def test_packet_size():
    """Packed packet must be exactly TOTAL_SIZE bytes."""
    raw = pack_packet(0, 0, 0.0, 0.0, 0.0)
    assert len(raw) == TOTAL_SIZE

def test_checksum_catches_corruption():
    """Corrupted byte should return None."""
    raw = bytearray(pack_packet(1, 1000, 22.0, 1013.0, 3.3))
    raw[8] = 0xFF
    assert unpack_packet(bytes(raw)) is None

def test_invalid_header_returns_none():
    """Wrong header magic should return None."""
    raw = bytearray(pack_packet(1, 1000, 22.0, 1013.0, 3.3))
    raw[0] = 0x00
    raw[1] = 0x00
    assert unpack_packet(bytes(raw)) is None

def test_too_short_returns_none():
    """Packet shorter than TOTAL_SIZE should return None."""
    assert unpack_packet(b'\x00' * 10) is None

def test_zero_values():
    """All-zero sensor values should pack and unpack correctly."""
    raw = pack_packet(0, 0, 0.0, 0.0, 0.0)
    pkt = unpack_packet(raw)
    assert pkt is not None
    assert pkt.temperature == 0.0
    assert pkt.pressure    == 0.0
    assert pkt.voltage     == 0.0

def test_to_dict_returns_all_keys():
    """to_dict must contain all expected keys."""
    raw = pack_packet(5, 1000, 22.0, 1013.0, 3.3)
    pkt = unpack_packet(raw)
    d   = pkt.to_dict()
    for key in ['packet_id','timestamp_ms','temperature',
                'pressure','voltage','status']:
        assert key in d

@pytest.mark.parametrize("pkt_id", [0, 1, 100, 65535])
def test_packet_id_roundtrip(pkt_id):
    """Packet ID should survive pack/unpack for valid uint16 range."""
    raw = pack_packet(pkt_id, 0, 0.0, 0.0, 0.0)
    pkt = unpack_packet(raw)
    assert pkt.packet_id == pkt_id

@pytest.mark.parametrize("temp", [-40.0, 0.0, 22.5, 85.0])
def test_temperature_roundtrip(temp):
    """Temperature should survive pack/unpack within float32 precision."""
    raw = pack_packet(0, 0, temp, 1013.0, 3.3)
    pkt = unpack_packet(raw)
    assert abs(pkt.temperature - temp) < 1e-3