#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finds the m4a (Sappy) sound engine's song functions in a GBA ROM, for hooking them (docs/guides/binary-m4a-hook.md).

usage: m4a_locate.py [--json | --armips | --song N] [--free BYTES] rom.gba

Prints ROM offsets (add 0x08000000 for the address) of m4aSongNumStart, m4aSongNumStartOrChange,
m4aSongNumStartOrContinue, m4aSongNumStop, m4aSongNumContinue, MPlayStart, MPlayStop, the song table, and
the last run of at least BYTES (default 4096) 0xFF bytes for new code. Exits 2 if the ROM is not an m4a game.
--armips prints the addresses as armips .definelabel lines for examples/binary-hook/hook.asm, or exits 3 when
the hook template does not fit this ROM. --song N prints song N's player index (for BGM_PLAYER).

Method: the m4aSongNum* functions all begin by indexing the song table with the song number
(n << 16 >> 13 = n * 8). Among them, the most frequent call target is MPlayStart; the one that only calls
MPlayStart is m4aSongNumStart; the one calling MPlayStart behind a compare is ...OrChange; the one also
calling a second function is ...OrContinue, and that second function is MPlayContinue; the one calling
neither MPlayStart nor MPlayContinue is m4aSongNumStop, and its target is MPlayStop."""
import argparse
import json
import struct
import sys
from collections import Counter

ROM_BASE = 0x08000000


def h16(rom, off):
    return struct.unpack_from('<H', rom, off)[0] if 0 <= off and off + 2 <= len(rom) else 0


def bl_target(rom, off):
    hi, lo = h16(rom, off), h16(rom, off + 2)
    if (hi & 0xF800) != 0xF000 or (lo & 0xF800) != 0xF800:
        return None
    o = (hi & 0x7FF) << 12 | (lo & 0x7FF) << 1
    if o & 0x400000:
        o -= 0x800000
    return off + 4 + o


def lit(rom, off):
    """The literal of the Thumb `ldr rX, [pc, #imm]` at off, or None."""
    op = h16(rom, off)
    if (op >> 11) != 0x09:
        return None
    at = ((off + 4) & ~3) + (op & 0xFF) * 4
    return struct.unpack_from('<I', rom, at)[0] if at + 4 <= len(rom) else None


def is_end(op):
    return (op & 0xFF87) == 0x4700 or (op & 0xFF00) == 0xBD00   # bx rX, pop {.., pc}


def song_functions(rom):
    """Entries of functions that start with `lsls r0,r0,#16 ... lsrs rX,r0,#13`, with their body facts."""
    found = {}
    for off in range(0, len(rom) - 2, 2):
        if h16(rom, off) != 0x0400:                       # lsls r0, r0, #16
            continue
        if not any((h16(rom, off + d) & 0xFFF8) == 0x0B40 for d in (2, 4, 6)):   # lsrs rX, r0, #13
            continue
        entry = next((off - d for d in (2, 4) if (h16(rom, off - d) & 0xFF00) == 0xB500), None)   # push {.., lr}
        if entry is None or entry in found:
            continue
        calls, cond, lits = [], False, []
        p = off
        while p < off + 0x60 and not is_end(h16(rom, p)):
            t = bl_target(rom, p)
            if t is not None:
                calls.append(t)
                p += 4
                continue
            op = h16(rom, p)
            cond |= (op & 0xF000) == 0xD000 and (op & 0x0F00) < 0x0E00
            v = lit(rom, p)
            if v is not None:
                lits.append(v)
            p += 2
        if calls:
            found[entry] = {'calls': calls, 'cond': cond, 'lits': lits}
    return found


def is_song_table(rom, off):
    """Song entries: (header pointer in ROM, u16 player, u16 player) for the first 4 entries."""
    if off < 0 or off + 32 > len(rom):
        return False
    for i in range(4):
        hdr, ms, me = struct.unpack_from('<IHH', rom, off + 8 * i)
        if not (ROM_BASE <= hdr < ROM_BASE + len(rom)) or ms > 32 or me > 32:
            return False
    return True


def free_space(rom, need):
    """(offset, length) of the 0xFF run that ends the ROM, if at least need bytes, else None."""
    end = len(rom)
    start = len(rom.rstrip(b'\xFF'))
    start = (start + 3) & ~3
    return (start, end - start) if end - start >= need else None


def locate(rom):
    fns = song_functions(rom)
    if not fns:
        raise LookupError('not an m4a game, or its m4a library was modified (no stock m4aSongNum* functions); '
                          'for a decomp-based hack, add GXA in C: docs/guides/c-source.md')
    # The library's m4aSongNum* functions sit next to each other; a hack's own code may look alike elsewhere.
    runs, run = [], []
    for entry in sorted(fns):
        if run and entry - run[-1] > 0x60:
            runs.append(run)
            run = []
        run.append(entry)
    runs.append(run)
    fns = {e: fns[e] for e in max(runs, key=len)}
    mplay_start = Counter(t for f in fns.values() for t in f['calls']).most_common(1)[0][0]
    out = {'MPlayStart': mplay_start}
    rest = []
    for entry, f in sorted(fns.items()):
        others = sorted(set(f['calls']) - {mplay_start})
        if mplay_start in f['calls']:
            name = ('m4aSongNumStartOrContinue' if others else
                    'm4aSongNumStartOrChange' if f['cond'] else 'm4aSongNumStart')
            if others:
                out['MPlayContinue'] = others[0]
            out.setdefault(name, entry)
        else:
            rest.append((entry, f))
    for entry, f in rest:
        if out.get('MPlayContinue') in f['calls']:
            out.setdefault('m4aSongNumContinue', entry)
        elif len(set(f['calls'])) == 1:
            out.setdefault('m4aSongNumStop', entry)
            out.setdefault('MPlayStop', f['calls'][0])
    start = out.get('m4aSongNumStart')
    if start is None:
        raise LookupError('found m4aSongNum* functions but not m4aSongNumStart')
    p = prologue(rom, start)
    if p:
        out['player_reg'], out['player_table'], out['song_table'] = p
    return out


HOOKED = ('m4aSongNumStart', 'm4aSongNumStartOrChange', 'm4aSongNumStartOrContinue', 'm4aSongNumStop')


def prologue(rom, e):
    """(player_reg, player_table, song_table) when e starts with the stock m4aSongNum* prologue, else None:

        push {lr}; lsls r0, r0, #16; ldr rP, =player_table; ldr r1, =song_table
        lsrs r0, r0, #13; adds r0, r0, r1; ldrh rQ, [r0, #4]      (P, Q = r2, r3 in either order)

    The hook overwrites the first 8 bytes and re-runs them from these constants."""
    pl, sl = h16(rom, e + 4), h16(rom, e + 6)
    preg = (pl >> 8) & 7
    if not (e % 4 == 0 and h16(rom, e) == 0xB500 and h16(rom, e + 2) == 0x0400 and (pl & 0xF800) == 0x4800
            and preg in (2, 3) and (sl & 0xFF00) == 0x4900 and h16(rom, e + 8) == 0x0B40
            and h16(rom, e + 10) == 0x1840 and h16(rom, e + 12) == (0x8880 | (5 - preg))):
        return None
    player, song = lit(rom, e + 4) - ROM_BASE, lit(rom, e + 6) - ROM_BASE
    return (preg, player, song) if is_song_table(rom, song) else None


def hook_check(rom, got):
    """Problems that stop examples/binary-hook from patching this ROM; [] when it can."""
    bad = []
    want = prologue(rom, got['m4aSongNumStart']) if 'm4aSongNumStart' in got else None
    for name in HOOKED:
        e = got.get(name)
        if e is None:
            bad.append(name + ': not found')
        elif prologue(rom, e) is None or prologue(rom, e) != want:
            bad.append(name + ': entry is not the stock m4a prologue (or not 4-byte aligned)')
    return bad


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument('--json', action='store_true')
    a.add_argument('--armips', action='store_true')
    a.add_argument('--song', type=int)
    a.add_argument('--free', type=int, default=4096)
    a.add_argument('rom')
    args = a.parse_args()
    rom = open(args.rom, 'rb').read()
    try:
        out = locate(rom)
    except LookupError as e:
        print('%s: %s' % (args.rom, e), file=sys.stderr)
        return 2
    if args.song is not None:
        at = out.get('song_table', -1) + 8 * args.song
        if 'song_table' not in out or at + 8 > len(rom):
            print('%s: no song %d' % (args.rom, args.song), file=sys.stderr)
            return 2
        header, player, _ = struct.unpack_from('<IHH', rom, at)
        print('song %d: player %d (header 0x%08X)' % (args.song, player, header))
        return 0
    fs = free_space(rom, args.free)
    problems = hook_check(rom, out)
    if args.armips:
        extend = not fs
        if extend and ((len(rom) + 3) & ~3) + args.free > 32 << 20:
            problems.append('no %d bytes of free space: the ROM is full at 32 MiB' % args.free)
        if problems:
            print('%s: %s' % (args.rom, '; '.join(problems)), file=sys.stderr)
            return 3
        print('; m4a_locate.py --armips %s' % args.rom.split('/')[-1])
        for k in HOOKED + ('MPlayStart', 'MPlayStop'):
            print('.definelabel %s, 0x%08X' % (k, out[k] + ROM_BASE))
        print('.definelabel PlayerTable, 0x%08X' % (out['player_table'] + ROM_BASE))
        print('.definelabel SongTable, 0x%08X' % (out['song_table'] + ROM_BASE))
        print('.definelabel PLAYER_REG, %d' % out['player_reg'])
        if extend:
            print('; no 0xFF free space at the end: the patch extends the ROM past its end')
        print('.definelabel FreeSpace, 0x%08X' % (((len(rom) + 3) & ~3 if extend else fs[0]) + ROM_BASE))
        return 0
    if args.json:
        res = {k: '0x%X' % v for k, v in out.items()}
        res['free_space'] = ['0x%X' % fs[0], fs[1]] if fs else None
        res['hook_problems'] = problems
        print(json.dumps(res, indent=1))
    else:
        for k, v in out.items():
            print('%-26s 0x%07X  (0x%08X)' % (k, v, v + ROM_BASE))
        print('%-26s %s' % ('free_space', '0x%07X, %d bytes' % fs if fs else 'none at the end of the ROM'))
        print('hook: %s' % ('; '.join(problems) if problems else 'ok (examples/binary-hook fits this ROM)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
