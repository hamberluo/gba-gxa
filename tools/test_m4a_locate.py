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

    def song_fn(self, calls, cond=False, player_reg=2):
        """push; n*8 into the song table; then bl each of calls (behind a compare when cond)."""
        entry = self.pc
        self.push_lr()
        self.lsls(0, 0, 16)
        self.ldr_lit(player_reg, 0x08000300)   # player table
        self.ldr_lit(1, 0x08000200)   # song table
        self.lsrs(0, 0, 13)
        self.adds(0, 0, 1)
        self.ldrh4(5 - player_reg, 0)
        if cond:
            self.cmp(3, 2)
            self.bne(0)
        for t in calls:
            self.bl(t)
        self.pop_r0()
        self.bx_r0()
        self.flush_lits()
        return entry


def blob(player_reg=2):
    a = Thumb()
    mplay_start, mplay_stop, mplay_continue = 0x380, 0x390, 0x3A0
    for at in (mplay_start, mplay_stop, mplay_continue):
        struct.pack_into('<HH', a.d, at, 0xB500, 0x4770)
    want = {
        'm4aSongNumStart': a.song_fn([mplay_start], player_reg=player_reg),
        'm4aSongNumStartOrChange': a.song_fn([mplay_start, mplay_start], cond=True, player_reg=player_reg),
        'm4aSongNumStartOrContinue': a.song_fn([mplay_start, mplay_continue], cond=True, player_reg=player_reg),
        'm4aSongNumStop': a.song_fn([mplay_stop], cond=True, player_reg=player_reg),
        'm4aSongNumContinue': a.song_fn([mplay_continue], cond=True, player_reg=player_reg),
    }
    # song table at 0x200: (header in ROM, player 0, 0) entries; player table at 0x300: RAM pointers
    for i in range(4):
        struct.pack_into('<IHH', a.d, 0x200 + 8 * i, 0x08000100, 0, 0)
    struct.pack_into('<III', a.d, 0x300, 0x08007000, 0x08007100, 0x00000010)   # in some games the entries are not RAM pointers
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


def test_player_table_and_stock_prologue():
    rom, want = blob()
    got = m4a_locate.locate(rom)
    assert got['player_table'] == 0x300 and got['player_reg'] == 2
    assert m4a_locate.hook_check(rom, got) == []


def test_player_table_in_r3():
    rom, want = blob(player_reg=3)
    got = m4a_locate.locate(rom)
    assert got['player_table'] == 0x300 and got['player_reg'] == 3
    assert m4a_locate.hook_check(rom, got) == []


def test_changed_prologue_is_reported():
    rom, want = blob()
    d = bytearray(rom)
    struct.pack_into('<H', d, want['m4aSongNumStop'] + 2, 0x46C0)   # nop where lsls r0,r0,#16 was
    got = m4a_locate.locate(bytes(d))
    problems = m4a_locate.hook_check(bytes(d), got)
    assert any('m4aSongNumStop' in p for p in problems)


def test_cli_armips_defines(tmp_path):
    rom, want = blob(player_reg=3)
    rom = rom + b'\xFF' * 0x2000
    (tmp_path / 'r.gba').write_bytes(rom)
    r = subprocess.run([sys.executable, str(TOOL), '--armips', str(tmp_path / 'r.gba')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert '.definelabel m4aSongNumStart, 0x%08X' % (0x08000000 + want['m4aSongNumStart']) in lines
    assert '.definelabel MPlayStop, 0x%08X' % (0x08000000 + want['MPlayStop']) in lines
    assert '.definelabel PlayerTable, 0x08000300' in lines
    assert '.definelabel SongTable, 0x08000200' in lines
    assert '.definelabel PLAYER_REG, 3' in lines
    assert '.definelabel FreeSpace, 0x%08X' % (0x08000000 + 0x400) in lines


def test_cli_armips_refuses_unhookable(tmp_path):
    rom, want = blob()
    d = bytearray(rom)
    struct.pack_into('<H', d, want['m4aSongNumStop'], 0xB510)   # push {r4, lr}: not the stock prologue
    (tmp_path / 'r.gba').write_bytes(bytes(d) + b'\xFF' * 0x2000)
    r = subprocess.run([sys.executable, str(TOOL), '--armips', str(tmp_path / 'r.gba')], capture_output=True, text=True)
    assert r.returncode == 3 and 'm4aSongNumStop' in r.stderr


def test_cli_song_reports_its_player(tmp_path):
    rom, want = blob()
    d = bytearray(rom)
    struct.pack_into('<IHH', d, 0x200 + 8 * 3, 0x08000100, 5, 5)   # song 3 on player 5
    (tmp_path / 'r.gba').write_bytes(bytes(d))
    r = subprocess.run([sys.executable, str(TOOL), '--song', '3', str(tmp_path / 'r.gba')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == 'song 3: player 5 (header 0x08000100)'


def test_cli_armips_extends_a_full_rom(tmp_path):
    rom, want = blob()                      # no 0xFF run at the end
    (tmp_path / 'r.gba').write_bytes(rom)
    r = subprocess.run([sys.executable, str(TOOL), '--armips', str(tmp_path / 'r.gba')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert '.definelabel FreeSpace, 0x%08X' % (0x08000000 + len(rom)) in r.stdout.splitlines()
    assert 'extends the ROM' in r.stdout


@pytest.mark.skipif(not os.environ.get('ARMIPS'), reason='ARMIPS (path to armips) not set')
def test_hook_template_assembles_and_patches(tmp_path):
    rom, want = blob(player_reg=3)
    (tmp_path / 'game.gba').write_bytes(rom + b'\xFF' * 0x4000)
    defs = subprocess.run([sys.executable, str(TOOL), '--armips', str(tmp_path / 'game.gba')],
                          capture_output=True, text=True, check=True).stdout
    (tmp_path / 'defs.asm').write_text(defs)
    (tmp_path / 'main.asm').write_text('.gba\n.open "%s", "%s", 0x08000000\n.include "%s"\n'
                                       '.definelabel BGM_PLAYER, 0\n.include "hook.asm"\n'
                                       'gxa_song_tracks:\n.halfword 1, 1\n.halfword 0xFFFF\n.close\n'
                                       % (tmp_path / 'game.gba', tmp_path / 'out.gba', tmp_path / 'defs.asm'))
    ex = Path(__file__).resolve().parents[1] / 'examples' / 'binary-hook'
    subprocess.run([os.environ['ARMIPS'], '-root', str(ex), str(tmp_path / 'main.asm')], check=True)
    out = (tmp_path / 'out.gba').read_bytes()
    for name in ('m4aSongNumStart', 'm4aSongNumStartOrChange', 'm4aSongNumStartOrContinue', 'm4aSongNumStop'):
        e = want[name]
        assert struct.unpack_from('<HH', out, e) == (0x4B00, 0x4718), name   # ldr r3, [pc]; bx r3
        assert struct.unpack_from('<I', out, e + 4)[0] & 1 == 1                # a Thumb address
        assert struct.unpack_from('<I', out, e + 4)[0] - 0x08000000 >= len(rom)  # into the free space
    assert out[:want['m4aSongNumStart']] == rom[:want['m4aSongNumStart']]


def test_cli_text_prints_player_reg_as_a_number(tmp_path):
    rom, want = blob(player_reg=3)
    (tmp_path / 'r.gba').write_bytes(rom)
    r = subprocess.run([sys.executable, str(TOOL), str(tmp_path / 'r.gba')], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    assert 'player_reg                 r3' in lines
    assert any(l.startswith('m4aSongNumStart ') and '(0x08' in l for l in lines)


def test_cli_armips_bgm_song_sets_bgm_player(tmp_path):
    rom, want = blob()
    d = bytearray(rom)
    struct.pack_into('<IHH', d, 0x200 + 8 * 2, 0x08000100, 7, 7)   # song 2 on player 7
    (tmp_path / 'r.gba').write_bytes(bytes(d) + b'\xFF' * 0x2000)
    r = subprocess.run([sys.executable, str(TOOL), '--armips', '--bgm-song', '2', str(tmp_path / 'r.gba')],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert '.definelabel BGM_PLAYER, 7' in r.stdout.splitlines()
    r = subprocess.run([sys.executable, str(TOOL), '--armips', str(tmp_path / 'r.gba')], capture_output=True, text=True)
    assert 'BGM_PLAYER' not in r.stdout


def test_cli_song_with_armips_is_refused(tmp_path):
    rom, want = blob()
    (tmp_path / 'r.gba').write_bytes(rom)
    r = subprocess.run([sys.executable, str(TOOL), '--armips', '--song', '2', str(tmp_path / 'r.gba')],
                       capture_output=True, text=True)
    assert r.returncode != 0 and r.stdout == ''
