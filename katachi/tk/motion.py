"""控えめなモーション。意味のある動きだけを付け、reduced-motionで必ず止める。

tkinterに prefers-reduced-motion は無いので、環境変数 KATACHI_REDUCE_MOTION と
OSのアクセシビリティ設定から判断する。アニメーションはすべて after() ベースで、
無効時・未対応環境では即座に最終状態へ飛ぶ。チカチカや過剰演出はしない。
"""

from __future__ import annotations

import contextlib
import os
import tkinter as tk
from collections.abc import Callable

_TRUTHY = {"1", "true", "yes", "on"}


def prefers_reduced_motion() -> bool:
    """利用者が動きの抑制を望んでいるか。環境変数を最優先し、無ければOS設定。"""
    env = os.environ.get("KATACHI_REDUCE_MOTION")
    if env is not None:
        return env.strip().lower() in _TRUTHY
    return _os_reduced_motion()


def _os_reduced_motion() -> bool:
    import platform
    import subprocess

    try:
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            return result.stdout.strip() in ("1", "true")
    except (OSError, subprocess.SubprocessError):
        return False
    return False


def fade_in(
    window: tk.Wm, *, enabled: bool = True, duration_ms: int = 160, steps: int = 12
) -> None:
    """ウィンドウを透明から不透明へ。無効・未対応なら即座に表示する。"""
    if not enabled:
        with contextlib.suppress(tk.TclError):
            window.attributes("-alpha", 1.0)
        return
    try:
        window.attributes("-alpha", 0.0)
    except tk.TclError:
        return  # 透明度未対応(一部のLinux)では最初から見えるに任せる
    delay = max(duration_ms // steps, 1)

    def step(index: int) -> None:
        with contextlib.suppress(tk.TclError):
            window.attributes("-alpha", min(index / steps, 1.0))
        if index < steps:
            window.after(delay, step, index + 1)

    step(1)


def fade_out(
    window: tk.Wm,
    on_done: Callable[[], None],
    *,
    enabled: bool = True,
    duration_ms: int = 120,
    steps: int = 8,
) -> None:
    """ウィンドウを不透明から透明へ畳み、完了時に on_done を呼ぶ。

    無効・未対応なら即座に on_done を呼ぶので、呼び出し側は常に1回だけ
    後処理(destroyなど)が走ると考えてよい。
    """
    if not enabled:
        on_done()
        return
    try:
        start = float(window.attributes("-alpha"))
    except (tk.TclError, ValueError):
        on_done()
        return
    delay = max(duration_ms // steps, 1)

    def step(index: int) -> None:
        with contextlib.suppress(tk.TclError):
            window.attributes("-alpha", max(start * (1 - index / steps), 0.0))
        if index < steps:
            window.after(delay, step, index + 1)
        else:
            on_done()

    step(1)
