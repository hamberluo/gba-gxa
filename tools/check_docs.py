#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the Markdown docs: usage: check_docs.py [repo_dir]

- README.md and every docs/guides/*.md has a .zh-CN.md translation with the same number of # and ## headings;
- every relative link resolves (code blocks and web links are skipped);
- nothing points at docs/superpowers (process notes that stay private)."""
import pathlib
import re
import sys

SKIP = ('.git', '.cache', '.superpowers', 'docs/superpowers', 'node_modules')
LINK = re.compile(r'\]\(([^)\s]+)\)')


def prose(text):
    return re.sub(r'```.*?```', '', text, flags=re.S)


def headings(text):
    return [l for l in prose(text).splitlines() if re.match(r'#{1,2} ', l)]


def needs_translation(rel):
    return rel.name.endswith('.md') and not rel.name.endswith('.zh-CN.md') and (
        str(rel) == 'README.md' or rel.parent == pathlib.Path('docs/guides'))


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1])
    bad = []
    files = [p for p in sorted(root.rglob('*.md'))
             if not any(str(p.relative_to(root)).startswith(s) for s in SKIP)]
    for p in files:
        rel = p.relative_to(root)
        text = p.read_text()
        if needs_translation(rel):
            zh = p.with_name(p.name[:-3] + '.zh-CN.md')
            if not zh.exists():
                bad.append('%s: no translation %s' % (rel, zh.name))
            elif len(headings(text)) != len(headings(zh.read_text())):
                bad.append('%s: %d headings, %s has %d' % (rel, len(headings(text)), zh.relative_to(root),
                                                             len(headings(zh.read_text()))))
        for target in LINK.findall(prose(text)):
            if re.match(r'[a-z]+:', target) or target.startswith('#'):
                continue
            path = target.split('#')[0]
            if path and not (p.parent / path).exists():
                bad.append('%s: broken link %s' % (rel, target))
        if 'docs/superpowers' in text:
            bad.append('%s: mentions docs/superpowers' % rel)
    for b in bad:
        print(b)
    print('check_docs: %s' % ('%d problems' % len(bad) if bad else 'ok'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
