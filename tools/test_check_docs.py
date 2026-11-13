# SPDX-License-Identifier: MIT
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).with_name('check_docs.py')


def run(root):
    return subprocess.run([sys.executable, str(TOOL), str(root)], capture_output=True, text=True)


def write(root, name, text):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_clean_tree_passes(tmp_path):
    write(tmp_path, 'README.md', '# A\n\n## B\n\n[zh](README.zh-CN.md) [g](docs/g.md#x)\n')
    write(tmp_path, 'README.zh-CN.md', '# 甲\n\n## 乙\n\n[en](README.md)\n')
    write(tmp_path, 'docs/g.md', '# G\n')
    r = run(tmp_path)
    assert r.returncode == 0 and r.stdout.strip().endswith('ok'), r.stdout


def test_heading_mismatch_fails(tmp_path):
    write(tmp_path, 'README.md', '# A\n\n## B\n\n## C\n')
    write(tmp_path, 'README.zh-CN.md', '# 甲\n\n## 乙\n')
    r = run(tmp_path)
    assert r.returncode == 1 and 'README.zh-CN.md' in r.stdout and 'headings' in r.stdout


def test_missing_translation_fails(tmp_path):
    write(tmp_path, 'docs/guides/x.md', '# X\n')
    r = run(tmp_path)
    assert r.returncode == 1 and 'x.zh-CN.md' in r.stdout


def test_broken_link_fails(tmp_path):
    write(tmp_path, 'a.md', '[b](missing.md) [web](https://example.com) [anchor](#top)\n')
    r = run(tmp_path)
    assert r.returncode == 1 and 'missing.md' in r.stdout and 'example.com' not in r.stdout


def test_process_docs_not_referenced(tmp_path):
    write(tmp_path, 'a.md', 'see docs/superpowers/plan\n')
    r = run(tmp_path)
    assert r.returncode == 1 and 'docs/superpowers' in r.stdout


def test_links_in_code_blocks_ignored(tmp_path):
    write(tmp_path, 'a.md', '```\n[x](nope.md)\n```\n')
    assert run(tmp_path).returncode == 0
