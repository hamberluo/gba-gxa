# Contributing

Chinese and English are both welcome in issues. 中文、英文提 issue 都可以。

## Spec changes

GXA keeps old ROMs working, so the spec changes slowly.

1. Open a [spec change issue](https://github.com/hamberluo/gba-gxa/issues/new?template=spec-change.yml):
   the problem, the proposed registers or behavior, and what existing ROMs and emulators would see.
2. Discussion happens in the issue. A change needs a working implementation in at least one emulator and a
   conformance case before it lands.
3. Minor versions (1.x) only add: new registers in the reserved range or new commands. Nothing existing
   changes meaning. Breaking changes need a new major version, decided by the maintainer.

Typo and wording fixes to SPEC.md can go straight to a pull request.

## Listing an emulator

Open an [emulator support issue](https://github.com/hamberluo/gba-gxa/issues/new?template=emulator-support.yml)
with a screenshot of `test-rom/gxa-conformance.gba` showing every row green, and a link to the source or
release.

## Listing a work

Open a [showcase issue](https://github.com/hamberluo/gba-gxa/issues/new?template=showcase.yml).

## Pull requests

- Docs: `README.md` and `docs/guides/*.md` have Chinese translations (`*.zh-CN.md`). Change both in the same
  pull request; `python3 tools/check_docs.py` checks that their headings line up and that links resolve.
- Tools: `pip install -r tools/requirements.txt && python3 -m pytest tools`.
- Header: `sh include/test/compile.sh` (needs `arm-none-eabi-gcc`).
- No game audio, ROMs or copyrighted game code in this repository.
