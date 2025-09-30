"""テーマのパレット選択・OSモード判定・ttkへの適用を確かめる。

ttkへの適用はディスプレイが要るので、無い環境では自動スキップする。
パレット選択とモード判定はGUIなしで動く。
"""

import pytest

tk = pytest.importorskip("tkinter", reason="tkinterなしのビルドではスキップ")

from katachi.tk import theme  # noqa: E402
from katachi.tk.theme import (  # noqa: E402
    DARK,
    LIGHT,
    apply_theme,
    current_palette,
    detect_mode,
    palette_for,
)


def test_palette_for_selects_mode():
    assert palette_for("light") is LIGHT
    assert palette_for("dark") is DARK


def test_palettes_are_distinct():
    assert LIGHT.bg != DARK.bg
    assert LIGHT.text != DARK.text
    assert LIGHT.accent != DARK.accent


def test_detect_mode_returns_valid_literal():
    assert detect_mode() in ("light", "dark")


def test_detect_mode_falls_back_to_light_on_error(monkeypatch):
    import platform
    import subprocess

    monkeypatch.setattr(platform, "system", lambda: "Linux")

    def boom(*_args, **_kwargs):
        raise OSError("ツールが無い")

    monkeypatch.setattr(subprocess, "run", boom)
    assert detect_mode() == "light"


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("ディスプレイがないためスキップ")
    window.withdraw()
    yield window
    window.destroy()


def test_apply_theme_records_palette(root: tk.Tk):
    assert current_palette(root) is None
    palette = apply_theme(root, "dark")
    assert palette is DARK
    assert current_palette(root) is DARK


def test_apply_theme_is_idempotent(root: tk.Tk):
    apply_theme(root, "light")
    apply_theme(root, "dark")
    assert current_palette(root) is DARK


def test_apply_theme_sets_window_background(root: tk.Tk):
    palette = apply_theme(root, "dark")
    assert root.cget("background") == palette.bg


def test_style_text_applies_palette_colors(root: tk.Tk):
    palette = apply_theme(root, "dark")
    text = tk.Text(root)
    theme.style_text(text, palette)
    assert text.cget("background") == palette.field
    assert text.cget("foreground") == palette.text
