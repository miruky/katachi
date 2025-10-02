"""縦スクロール可能な領域。背の高い設定フォームを小さな画面でも収める。

中身は .interior フレームに置く。内容が領域より高いときだけスクロールバーを
出し、収まっているときは邪魔をしない。マウスホイール(各OSのイベント差を含む)
にも対応する。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import Palette


class ScrollableFrame(ttk.Frame):
    """縦スクロール領域。配置先は self.interior。

    max_height を与えると、その高さを超えた分だけスクロールに回す。超えなければ
    内容の高さちょうどに縮み、スクロールバーは隠れる。
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: Palette | None = None,
        max_height: int | None = None,
    ) -> None:
        super().__init__(master)
        self._max_height = max_height
        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        if palette is not None:
            self._canvas.configure(background=palette.bg)
        self._vbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_scrollbar)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.interior = ttk.Frame(self._canvas)
        self._window = self._canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", self._on_interior_resize)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self.interior.bind("<Enter>", lambda _e: self._bind_wheel(True))
        self.interior.bind("<Leave>", lambda _e: self._bind_wheel(False))

    def configure_background(self, palette: Palette) -> None:
        """テーマ適用後に、スクロール台のキャンバス背景を揃える。"""
        self._canvas.configure(background=palette.bg)

    def _on_interior_resize(self, _event: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        height = self.interior.winfo_reqheight()
        if self._max_height is not None:
            height = min(height, self._max_height)
        self._canvas.configure(height=height)

    def _on_canvas_resize(self, event: tk.Event) -> None:
        # 中身を横幅いっぱいに広げる(入力欄が間延びせず端まで届く)。
        self._canvas.itemconfigure(self._window, width=event.width)

    def _on_scrollbar(self, low: str, high: str) -> None:
        # 全体が見えているときはスクロールバーを隠す。
        if float(low) <= 0.0 and float(high) >= 1.0:
            self._vbar.grid_remove()
        else:
            self._vbar.grid(row=0, column=1, sticky="ns")
        self._vbar.set(low, high)

    def _bind_wheel(self, active: bool) -> None:
        events = ("<MouseWheel>", "<Button-4>", "<Button-5>")
        for event in events:
            if active:
                self._canvas.bind_all(event, self._on_wheel)
            else:
                self._canvas.unbind_all(event)

    def _on_wheel(self, event: tk.Event) -> None:
        if event.num == 5 or event.delta < 0:
            self._canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self._canvas.yview_scroll(-1, "units")
