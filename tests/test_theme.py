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
    normalize_hex,
    palette_for,
    palette_with_accent,
    readable_text_on,
)


def _contrast(fg: str, bg: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    def luminance(hexcolor: str) -> float:
        h = hexcolor.lstrip("#")
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    high, low = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("palette", [LIGHT, DARK])
def test_palette_meets_wcag_aa(palette):
    # 本文・補足・エラー・ボタン文字は本文基準(4.5:1)以上を保つ。
    assert _contrast(palette.text, palette.bg) >= 4.5
    assert _contrast(palette.muted, palette.bg) >= 4.5
    assert _contrast(palette.error, palette.bg) >= 4.5
    assert _contrast(palette.accent_text, palette.accent) >= 4.5
    # アクセントの枠・フォーカスはUI部品基準(3:1)以上。
    assert _contrast(palette.accent, palette.bg) >= 3.0


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


def test_normalize_hex_accepts_long_and_short():
    assert normalize_hex("#16A34A") == "#16a34a"
    assert normalize_hex("0a0") == "#00aa00"


@pytest.mark.parametrize("bad", ["green", "#12", "#1234", "#gggggg"])
def test_normalize_hex_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        normalize_hex(bad)


def test_readable_text_on_picks_contrasting_ink():
    assert readable_text_on("#ffffff") == "#11161d"  # 明るい色には濃墨
    assert readable_text_on("#000000") == "#ffffff"  # 暗い色には白


@pytest.mark.parametrize("accent", ["#16a34a", "#7c3aed", "#f59e0b", "#0ea5e9"])
def test_palette_with_accent_keeps_readable_button_text(accent):
    derived = palette_with_accent(LIGHT, accent)
    assert derived.accent == accent
    assert derived.focus == accent
    # 任意のアクセントでもボタン文字はWCAG AA(4.5:1)を保つ。
    assert _contrast(derived.accent_text, derived.accent) >= 4.5
    # 地色・罫線はパレットのまま残す。
    assert derived.bg == LIGHT.bg
    assert derived.border == LIGHT.border


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


def test_apply_theme_without_accent_keeps_canonical_palette(root: tk.Tk):
    # accent を渡さなければ組み込みパレットの同一オブジェクトを返す。
    assert apply_theme(root, "dark") is DARK


def test_apply_theme_custom_accent_overrides(root: tk.Tk):
    palette = apply_theme(root, "light", accent="#16a34a")
    assert palette.accent == "#16a34a"
    assert palette.focus == "#16a34a"
    assert current_palette(root) is palette
    assert palette is not LIGHT
