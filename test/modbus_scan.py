"""Scan the spaliQ Professional Modbus register space.

Tries both input registers (func 4) and holding registers (func 3)
at every 20-register block from address 0 to 500.  Only prints blocks
that contain at least one non-zero value.

Usage:
    python3 test/modbus_scan.py 192.168.x.x
"""
import socket
import struct
import sys


def read_block(host: str, port: int, unit_id: int, func: int, start: int, count: int):
    request = struct.pack(">HHHBBHH", 1, 0, 6, unit_id, func, start, count)
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(request)
            data = b""
            sock.settimeout(3)
            try:
                while len(data) < 9 + count * 2:
                    chunk = sock.recv(512)
                    if not chunk:
                        break
                    data += chunk
            except OSError:
                pass
    except OSError as exc:
        return None, f"connect error: {exc}"

    if len(data) >= 9 and data[7] & 0x80:
        return None, f"exception 0x{data[8]:02x}"
    if len(data) < 9 + count * 2:
        return None, f"short ({len(data)} bytes)"

    raw = data[9: 9 + count * 2]
    return [struct.unpack(">H", raw[i * 2: i * 2 + 2])[0] for i in range(count)], None


def signed(v: int) -> int:
    return struct.unpack(">h", struct.pack(">H", v))[0]


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 502
    unit_id = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    count = 20

    print(f"Scanning {host}:{port}  unit={unit_id}\n")
    print(f"{'func':>4}  {'start':>5}  {'idx':>5}  {'u16':>6}  {'s16':>7}  ÷10     ÷100")
    print("-" * 60)

    for func in (4, 3):
        for start in range(0, 500, count):
            regs, err = read_block(host, port, unit_id, func, start, count)
            if regs is None:
                if "exception 0x02" not in str(err):
                    print(f"func={func}  start={start:4d}  {err}")
                continue
            if all(v == 0 for v in regs):
                continue  # skip all-zero blocks
            for i, v in enumerate(regs):
                s = signed(v)
                print(f"  fc{func}  [{start + i:4d}]   {v:6d}   {s:7d}  {v/10:7.2f}  {v/100:6.2f}")
            print()


if __name__ == "__main__":
    main()
