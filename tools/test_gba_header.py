# SPDX-License-Identifier: MIT
import subprocess
import sys
import zlib
from pathlib import Path

TOOL = Path(__file__).with_name('gba_header.py')


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


def test_fills_logo_and_checksum(tmp_path):
    rom = tmp_path / 'r.gba'
    d = bytearray(512)
    d[0xA0:0xAC] = b'GXA BGM DEMO'
    d[0xB2] = 0x96
    rom.write_bytes(bytes(d))
    assert run(rom).returncode == 0
    out = rom.read_bytes()
    assert zlib.crc32(out[4:160]) == 0xD0BEB55E
    assert (sum(out[0xA0:0xBE]) + 0x19) & 0xFF == 0
    assert len(out) == 512


def test_check_mode_reports_bad_checksum(tmp_path):
    rom = tmp_path / 'r.gba'
    rom.write_bytes(bytes(512))
    r = run('--check', rom)
    assert r.returncode == 1 and 'checksum' in r.stdout
    assert run(rom).returncode == 0
    assert run('--check', rom).returncode == 0


def test_rejects_short_file(tmp_path):
    rom = tmp_path / 'r.gba'
    rom.write_bytes(bytes(100))
    r = run(rom)
    assert r.returncode == 2 and 'too short' in r.stderr
