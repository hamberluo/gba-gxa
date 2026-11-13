# SPDX-License-Identifier: MIT
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import m4a_locate  # noqa: E402

TOOL = Path(__file__).with_name('m4a_locate.py')


class Thumb:
    """A tiny Thumb assembler, enough to lay out m4a-shaped functions."""

    def __init__(self, size=0x400):
        self.d = bytearray(size)
        self.pc = 0
        self.lits = []

    def h(self, v):
        struct.pack_into('<H', self.d, self.pc, v)
        self.pc += 2

    def push_lr(self): self.h(0xB500)
    def pop_r0(self): self.h(0xBC01)
    def bx_r0(self): self.h(0x4700)
    def lsls(self, rd, rm, n): self.h(0x0000 | n << 6 | rm << 3 | rd)
    def lsrs(self, rd, rm, n): self.h(0x0800 | n << 6 | rm << 3 | rd)
    def adds(self, rd, rn, rm): self.h(0x1800 | rm << 6 | rn << 3 | rd)
    def cmp(self, rn, rm): self.h(0x4280 | rm << 3 | rn)
    def bne(self, n): self.h(0xD100 | (n & 0xFF))
    def ldrh4(self, rd, rn): self.h(0x8880 | rn << 3 | rd)
    def ldr0(self, rd, rn): self.h(0x6800 | rn << 3 | rd)

    def ldr_lit(self, rd, value):
        self.lits.append((self.pc, rd, value))
        self.h(0x4800 | rd << 8)

    def bl(self, target):
        o = target - (self.pc + 4)
        self.h(0xF000 | (o >> 12) & 0x7FF)
        self.h(0xF800 | (o >> 1) & 0x7FF)

    def flush_lits(self):
        if self.pc % 4:
            self.h(0)
        for at, rd, value in self.lits:
            imm = (self.pc - ((at + 4) & ~3)) // 4
            struct.pack_into('<H', self.d, at, 0x4800 | rd << 8 | imm)
            struct.pack_into('<I', self.d, self.pc, value)
            self.pc += 4
        self.lits = []

    def song_fn(self, calls, cond=False):
        """push; n*8 into the song table; then bl each of calls (behind a compare when cond)."""
        entry = self.pc
        self.push_lr()
        self.lsls(0, 0, 16)
        self.ldr_lit(2, 0x08000300)   # player table
        self.ldr_lit(1, 0x08000200)   # song table
        self.lsrs(0, 0, 13)
        self.adds(0, 0, 1)
        self.ldrh4(3, 0)
        if cond:
            self.cmp(3, 2)
            self.bne(0)
        for t in calls:
            self.bl(t)
        self.pop_r0()
        self.bx_r0()
        self.flush_lits()
        return entry


def blob():
    a = Thumb()
    mplay_start, mplay_stop, mplay_continue = 0x380, 0x390, 0x3A0
    for at in (mplay_start, mplay_stop, mplay_continue):
        struct.pack_into('<HH', a.d, at, 0xB500, 0x4770)
    want = {
        'm4aSongNumStart': a.song_fn([mplay_start]),
        'm4aSongNumStartOrChange': a.song_fn([mplay_start, mplay_start], cond=True),
        'm4aSongNumStartOrContinue': a.song_fn([mplay_start, mplay_continue], cond=True),
        'm4aSongNumStop': a.song_fn([mplay_stop], cond=True),
        'm4aSongNumContinue': a.song_fn([mplay_continue], cond=True),
    }
    # song table at 0x200: (header in ROM, player 0, 0) entries; player table at 0x300: RAM pointers
    for i in range(4):
        struct.pack_into('<IHH', a.d, 0x200 + 8 * i, 0x08000100, 0, 0)
    struct.pack_into('<III', a.d, 0x300, 0x03007000, 0x03007100, 0x00000010)
    want.update(MPlayStart=mplay_start, MPlayStop=mplay_stop, song_table=0x200)
    return bytes(a.d), want


def test_locates_planted_functions():
    rom, want = blob()
    got = m4a_locate.locate(rom)
    for k, v in want.items():
        assert got[k] == v, k


def test_cli_json_is_rom_offsets(tmp_path):
    rom, want = blob()
    (tmp_path / 'r.gba').write_bytes(rom)
    r = subprocess.run([sys.executable, str(TOOL), '--json', str(tmp_path / 'r.gba')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert got['m4aSongNumStart'] == '0x%X' % want['m4aSongNumStart']
    assert 'free_space' in got


def test_free_space_is_last_ff_run():
    rom = bytes(0x1000) + b'\xFF' * 0x2000
    assert m4a_locate.free_space(rom, 0x1000) == (0x1000, 0x2000)
    assert m4a_locate.free_space(rom, 0x4000) is None


def test_not_m4a(tmp_path):
    p = tmp_path / 'r.gba'
    p.write_bytes(os.urandom(0x4000))
    r = subprocess.run([sys.executable, str(TOOL), str(p)], capture_output=True, text=True)
    assert r.returncode == 2 and 'not an m4a game' in r.stderr


ROMS = os.environ.get('GXA_M4A_ORACLE')


@pytest.mark.skipif(not ROMS, reason='GXA_M4A_ORACLE (json: rom path -> {mplay_start, mplay_stop}) not set')
def test_real_roms_agree_with_oracle():
    oracle = json.loads(Path(ROMS).read_text())
    bad = []
    for path, o in oracle.items():
        got = m4a_locate.locate(Path(path).read_bytes())
        if (got['MPlayStart'], got['MPlayStop']) != (o['mplay_start'], o['mplay_stop']):
            bad.append('%s: %s' % (Path(path).name, got))
    assert not bad


def test_lookalike_outside_the_library_is_ignored():
    """A hack's own code may index the song table the same way; only the library's run of functions counts."""
    rom, want = blob()
    a = Thumb(0x800)
    a.d[:len(rom)] = rom
    a.pc = 0x600
    a.song_fn([0x700])            # elsewhere: same preamble, a single call to something else
    a.song_fn([0x380, 0x710])     # and one calling MPlayStart and something else
    got = m4a_locate.locate(bytes(a.d))
    for k, v in want.items():
        assert got[k] == v, k
