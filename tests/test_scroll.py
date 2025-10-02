"""スクロール領域の生成・背景適用・スクロールバー表示制御を確かめる。

ウィジェットを使うのでディスプレイが無い環境では自動スキップする。
"""

import pytest

tk = pytest.importorskip("tkinter", reason="tkinterなしのビルドではスキップ")

from tkinter import ttk  # noqa: E402

from katachi.tk.scroll import ScrollableFrame  # noqa: E402
from katachi.tk.theme import LIGHT  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("ディスプレイがないためスキップ")
    window.withdraw()
    yield window
    window.destroy()


def test_interior_accepts_children(root: tk.Tk):
    area = ScrollableFrame(root, max_height=200)
    area.pack(fill="both", expand=True)
    label = ttk.Label(area.interior, text="中身")
    label.pack()
    root.update_idletasks()
    assert label.winfo_exists()


def test_configure_background_paints_canvas(root: tk.Tk):
    area = ScrollableFrame(root)
    area.configure_background(LIGHT)
    assert area._canvas.cget("background") == LIGHT.bg


def test_scrollbar_visibility_follows_content(root: tk.Tk):
    # withdrawn窓ではwinfo_ismappedが常にFalseなので、grid管理の有無で判定する。
    area = ScrollableFrame(root)
    area.pack(fill="both", expand=True)
    area._on_scrollbar("0.0", "1.0")  # 全体が見えている
    assert area._vbar.grid_info() == {}
    area._on_scrollbar("0.0", "0.5")  # 半分だけ見えている
    assert area._vbar.grid_info() != {}
    area._on_scrollbar("0.0", "1.0")  # また全部見えたら隠れる
    assert area._vbar.grid_info() == {}
