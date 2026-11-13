# Changelog

The spec and the tools are versioned separately. Spec versions follow SPEC.md §7:
minor versions only add registers or commands.

## Unreleased

## 1.0 (2026-11-13)

### Spec 1.0

- Registers, detection, playback, packs, frontends and conformance (SPEC.md).

### Tools 1.0

- `include/gxa.h`: the registers and calls in one C89 header.
- `asm/gxa.s`: `gxa_has_pack`, `gxa_play_track`, `gxa_stop` for binary hacks (armips or GNU as).
- `tools/m4a_locate.py`: finds an m4a game's song functions and writes armips defines for the hook.
- `examples/binary-hook`: an armips hook that plays mapped m4a songs from a pack and mutes the original.
- `examples/homebrew-bgm`: a small ROM that hands its music to GXA, with fallback.
- `tools/gxa_pack.py` (reproducible packs), `gxa_info.py`, `check_spec.py`, `gba_header.py`, `check_docs.py`.
- Conformance ROM and pack (`test-rom/`), built on `gxa.h`.
- Guides (English and Chinese), `AGENTS.md`, `llms.txt`, issue templates, CI.
