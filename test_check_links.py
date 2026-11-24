import subprocess
import sys
from pathlib import Path

from check_links import check, main

SCRIPT = Path(__file__).with_name("check_links.py")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_cli(root):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True
    )


def test_good_links_pass(tmp_path):
    write(
        tmp_path / "index.html",
        '<a href="#top">top</a><h1 id="top">Hi</h1>'
        '<a href="docs/page.html?x=1#sec">page</a>'
        '<a href="/docs/page.html?v=1#old">abs</a>'
        '<a href="docs/">folder</a><img src="img/logo.png">',
    )
    write(tmp_path / "docs" / "page.html", '<a name="old"></a><p id="sec">x</p>')
    write(tmp_path / "docs" / "index.html", "<p>docs</p>")
    write(tmp_path / "img" / "logo.png", "")

    assert check(tmp_path) == []
    result = run_cli(tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""


def test_missing_file(tmp_path, capsys):
    write(tmp_path / "index.html", '<a href="missing.html">x</a>')

    assert check(tmp_path) == [("index.html", "missing.html", "file not found")]
    assert main([str(tmp_path)]) == 1
    assert "index.html: missing.html (file not found)" in capsys.readouterr().out


def test_folder_without_index(tmp_path):
    write(tmp_path / "index.html", '<a href="empty/">x</a>')
    (tmp_path / "empty").mkdir()

    assert check(tmp_path) == [("index.html", "empty/", "folder has no index.html")]


def test_missing_anchor(tmp_path):
    write(
        tmp_path / "index.html",
        '<a href="#nope">x</a><a href="other.html#gone">y</a><span name="nope"></span>',
    )
    write(tmp_path / "other.html", '<p id="here">z</p>')

    assert check(tmp_path) == [
        ("index.html", "#nope", "anchor not found"),
        ("index.html", "other.html#gone", "anchor not found"),
    ]
    result = run_cli(tmp_path)
    assert result.returncode != 0
    assert "index.html: #nope (anchor not found)" in result.stdout


def test_external_links_ignored(tmp_path):
    write(
        tmp_path / "index.html",
        '<a href="https://example.com/x.html#y">a</a>'
        '<a href="http://example.com">b</a>'
        '<a href="mailto:me@example.com">c</a>'
        '<a href="tel:+123">d</a>'
        '<img src="data:image/png;base64,AAAA">'
        '<a href="javascript:void(0)">e</a>'
        '<script src="//cdn.example.com/lib.js"></script>',
    )

    assert check(tmp_path) == []
    assert run_cli(tmp_path).returncode == 0
