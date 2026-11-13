# Changelog

The spec and the tools are versioned separately. Spec versions follow SPEC.md §7:
minor versions only add registers or commands.

## Unreleased

- `include/gxa.h`: the registers and calls in one C89 header; the conformance ROM is built on it.
- `asm/gxa.s`: `gxa_has_pack`, `gxa_play_track`, `gxa_stop` for binary hacks (armips or GNU as).
- `tools/m4a_locate.py`: finds an m4a game's song functions and writes armips defines for the hook.
- `examples/binary-hook`: an armips hook that plays mapped m4a songs from a pack and mutes the original.
- `examples/homebrew-bgm`: a small ROM that hands its music to GXA, with fallback.
- `tools/gba_header.py`, `tools/check_docs.py`; `gxa_pack.py` prints a summary.
- Guides (English and Chinese), `AGENTS.md`, `llms.txt`, issue templates, CI.

## Spec 1.0

- Registers, detection, playback, packs, frontends and conformance (SPEC.md).

## Tools 1.0

- `gxa_pack.py`, `gxa_info.py`, `check_spec.py`.
- Conformance ROM and pack (`test-rom/`).
