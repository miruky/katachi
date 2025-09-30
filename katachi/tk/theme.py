"""モダンな見た目のためのttkテーマ。

tkinterの既定スタイルは古く重い。余白・タイポグラフィ・配色を一貫させた
ライト/ダーク両対応のテーマをttk.Styleへ焼き込み、生成されるフォームが
「設定画面らしい」整った見た目になるようにする。

OSのダークモードを推定して既定を選ぶが、明示指定もできる。色だけでなく
標準ライブラリのtk.Text/tk.Listbox(ttkに無いウィジェット)も同じ配色で
塗れるよう、適用したパレットをルートに覚えさせて共有する。
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk
from typing import Literal

Mode = Literal["light", "dark"]

# 8pxグリッド。余白はすべてこの倍数から選ぶ。
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24

_PALETTE_ATTR = "_katachi_palette"
_MODE_ATTR = "_katachi_mode"


@dataclass(frozen=True, slots=True)
class Palette:
    """1モード分の配色。低彩度のベースに一点アクセントを置く。"""

    bg: str
    surface: str
    field: str
    text: str
    muted: str
    border: str
    accent: str
    accent_text: str
    error: str
    focus: str
    selection: str


LIGHT = Palette(
    bg="#f4f5f7",
    surface="#ffffff",
    field="#ffffff",
    text="#1f2328",
    muted="#656d76",
    border="#d0d7de",
    accent="#2563eb",
    accent_text="#ffffff",
    error="#b3261e",
    focus="#2563eb",
    selection="#dbe7ff",
)

DARK = Palette(
    bg="#0d1117",
    surface="#161b22",
    field="#10151c",
    text="#e6edf3",
    muted="#8b949e",
    border="#30363d",
    accent="#4c8dff",
    accent_text="#0d1117",
    error="#ff7b72",
    focus="#58a6ff",
    selection="#1f3a5f",
)


def palette_for(mode: Mode) -> Palette:
    return DARK if mode == "dark" else LIGHT


def detect_mode() -> Mode:
    """OSのダークモード設定を推定する。判定できなければ light。"""
    import platform
    import subprocess

    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            return "dark" if result.stdout.strip() == "Dark" else "light"
        if system == "Windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            try:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            finally:
                key.Close()
            return "light" if value else "dark"
        # Linuxなど: デスクトップ環境の設定を gsettings から覗く
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        return "dark" if "dark" in result.stdout.lower() else "light"
    except (OSError, subprocess.SubprocessError, ValueError):
        return "light"


def current_palette(widget: tk.Misc) -> Palette | None:
    """このウィジェットの属するウィンドウに適用済みのパレット。未適用ならNone。"""
    return getattr(widget.winfo_toplevel(), _PALETTE_ATTR, None)


def current_mode(widget: tk.Misc) -> Mode | None:
    return getattr(widget.winfo_toplevel(), _MODE_ATTR, None)


def apply_theme(widget: tk.Misc, mode: Mode | None = None) -> Palette:
    """ウィジェットの属するウィンドウへテーマを適用し、使ったパレットを返す。

    mode を省略すると OS 設定から推定する。何度呼んでも安全(冪等)。
    """
    root = widget.winfo_toplevel()
    resolved: Mode = mode or detect_mode()
    palette = palette_for(resolved)
    style = ttk.Style(root)
    with contextlib.suppress(tk.TclError):
        style.theme_use("clam")

    base = tkfont.nametofont("TkDefaultFont")
    family = base.cget("family")
    size = base.cget("size") or 10
    small = (family, max(abs(size) - 1, 9))
    bold = (family, size, "bold")

    with contextlib.suppress(tk.TclError):
        root.configure(background=palette.bg)

    style.configure(".", background=palette.bg, foreground=palette.text, font=base)
    style.configure("TFrame", background=palette.bg)
    style.configure("Card.TFrame", background=palette.surface)
    style.configure("TLabel", background=palette.bg, foreground=palette.text)
    style.configure("Field.TLabel", background=palette.bg, foreground=palette.text)
    style.configure("Help.TLabel", background=palette.bg, foreground=palette.muted, font=small)
    style.configure("Error.TLabel", background=palette.bg, foreground=palette.error, font=small)
    style.configure("Heading.TLabel", background=palette.bg, foreground=palette.text, font=bold)

    style.configure(
        "TLabelframe",
        background=palette.bg,
        bordercolor=palette.border,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label", background=palette.bg, foreground=palette.muted, font=small
    )

    style.configure("TCheckbutton", background=palette.bg, foreground=palette.text)
    style.map(
        "TCheckbutton",
        background=[("active", palette.bg)],
        indicatorcolor=[("selected", palette.accent), ("!selected", palette.field)],
    )

    style.configure(
        "TButton",
        background=palette.surface,
        foreground=palette.text,
        bordercolor=palette.border,
        focuscolor=palette.focus,
        relief="flat",
        padding=(SPACE_MD, SPACE_SM - 2),
    )
    style.map(
        "TButton",
        background=[("active", palette.border), ("pressed", palette.border)],
        bordercolor=[("focus", palette.focus)],
    )
    style.configure(
        "Accent.TButton",
        background=palette.accent,
        foreground=palette.accent_text,
        bordercolor=palette.accent,
        padding=(SPACE_LG, SPACE_SM - 2),
    )
    style.map(
        "Accent.TButton",
        background=[("active", palette.focus), ("pressed", palette.focus)],
        foreground=[("disabled", palette.muted)],
    )

    for entryish in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(
            entryish,
            fieldbackground=palette.field,
            background=palette.surface,
            foreground=palette.text,
            bordercolor=palette.border,
            insertcolor=palette.text,
            arrowcolor=palette.text,
            relief="flat",
            padding=SPACE_XS,
        )
        style.map(
            entryish,
            bordercolor=[("focus", palette.focus)],
            fieldbackground=[("readonly", palette.field)],
        )

    # コンボボックスのドロップダウン(中身はtk.Listbox)はoptionで配色する。
    root.option_add("*TCombobox*Listbox.background", palette.field)
    root.option_add("*TCombobox*Listbox.foreground", palette.text)
    root.option_add("*TCombobox*Listbox.selectBackground", palette.accent)
    root.option_add("*TCombobox*Listbox.selectForeground", palette.accent_text)

    setattr(root, _PALETTE_ATTR, palette)
    setattr(root, _MODE_ATTR, resolved)
    return palette


def style_text(widget: tk.Text | tk.Listbox, palette: Palette) -> None:
    """ttkに無いtk.Text/tk.Listboxへ、テーマと揃う配色を直接当てる。"""
    widget.configure(
        background=palette.field,
        foreground=palette.text,
        highlightthickness=1,
        highlightbackground=palette.border,
        highlightcolor=palette.focus,
        relief="flat",
        borderwidth=0,
        selectbackground=palette.selection,
        selectforeground=palette.text,
    )
    if isinstance(widget, tk.Text):
        widget.configure(insertbackground=palette.text, padx=SPACE_SM, pady=SPACE_XS)
