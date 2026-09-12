"""Offline btsnoop check; print aggregate counts, never addresses or payloads."""

import asyncio
from collections import Counter
from pathlib import Path
import struct
import sys

from automower_ble.helpers import crc
from test_connection import Mower
from gardena_connection_tests.events import pairing_event


def frames(path):
    raw = Path(path).read_bytes()
    if raw[:8] != b"btsnoop\0" or struct.unpack_from(">II", raw, 8) != (1, 1002):
        raise ValueError("Expected H4 btsnoop version 1 capture")
    offset, records = 16, 0
    acl, hcp, found = {}, {}, []
    while offset < len(raw):
        _, length, flags, _, _ = struct.unpack_from(">IIIIQ", raw, offset)
        offset += 24
        packet = raw[offset : offset + length]
        offset += length
        records += 1
        if not packet or packet[0] != 2:
            continue
        handle_flags, acl_length = struct.unpack_from("<HH", packet, 1)
        key = (handle_flags & 0xFFF, flags & 1)
        fragment = packet[5 : 5 + acl_length]
        if (handle_flags >> 12) & 3 != 1:
            acl[key] = bytearray(fragment)
        else:
            acl.setdefault(key, bytearray()).extend(fragment)
        data = acl[key]
        if len(data) < 4:
            continue
        size, cid = struct.unpack_from("<HH", data)
        if len(data) < size + 4:
            continue
        del acl[key]
        att = data[4 : size + 4]
        if cid != 4 or len(att) < 3 or att[0] not in (0x12, 0x52, 0x1B, 0x1D):
            continue
        stream = key + (int.from_bytes(att[1:3], "little"),)
        buffer = hcp.setdefault(stream, bytearray())
        buffer.extend(att[3:])
        while len(buffer) >= 4:
            if buffer[:2] != b"\x02\xfd":
                del buffer[0]
                continue
            length = int.from_bytes(buffer[2:4], "little") + 4
            if not 20 <= length <= 4096:
                del buffer[0]
                continue
            if len(buffer) < length:
                break
            frame = bytearray(buffer[:length])
            del buffer[:length]
            if (
                frame[-1] != 3
                or frame[9] != crc(frame, 1, 8)
                or frame[-2] != crc(frame, 1, len(frame) - 3)
            ):
                raise ValueError("Invalid captured HCP checksum or terminator")
            found.append(frame)
    return records, found


async def verify(path):
    records, captured = frames(path)
    mower = Mower(1, "00:00:00:00:00:00", 1234)
    counts, pairing = Counter(), Counter()
    for frame in captured:
        counts[frame[10]] += 1
        for split in (1, 3, 10, len(frame) - 1):
            mower.queue.put_nowait(frame[:split])
            mower.queue.put_nowait(frame[split:] + frame)
            assert await mower._next_frame() == frame
            assert await mower._next_frame() == frame
        event = pairing_event(frame, int.from_bytes(frame[4:8], "little"))
        if event is not None:
            pairing["success" if event else "failed"] += 1
    print(
        {
            "records": records,
            "frames": len(captured),
            "packet_types": dict(counts),
            "pairing_events": dict(pairing),
            "fragment_and_coalescing_checks": len(captured) * 8,
        }
    )


if __name__ == "__main__":
    asyncio.run(verify(sys.argv[1]))
