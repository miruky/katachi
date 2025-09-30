"""モーションの reduced-motion 判定とフェードの安全性を確かめる。

フェードはウィンドウが要るのでディスプレイの無い環境では自動スキップする。
reduced-motion の判定はGUIなしで動く。
"""

import pytest

tk = pytest.importorskip("tkinter", reason="tkinterなしのビルドではスキップ")

from katachi.tk import motion  # noqa: E402


@pytest.mark.parametrize(
    "value,expected",
    [("1", True), ("true", True), ("ON", True), ("0", False), ("off", False), ("no", False)],
)
def test_env_overrides_reduced_motion(monkeypatch, value, expected):
    monkeypatch.setenv("KATACHI_REDUCE_MOTION", value)
    assert motion.prefers_reduced_motion() is expected


def test_reduced_motion_without_env_returns_bool(monkeypatch):
    monkeypatch.delenv("KATACHI_REDUCE_MOTION", raising=False)
    assert isinstance(motion.prefers_reduced_motion(), bool)


@pytest.fixture
def win():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("ディスプレイがないためスキップ")
    root.withdraw()
    yield root
    root.destroy()


def test_fade_out_disabled_calls_on_done_once(win: tk.Tk):
    calls: list[int] = []
    motion.fade_out(win, lambda: calls.append(1), enabled=False)
    assert calls == [1]


def test_fade_in_disabled_is_fully_visible(win: tk.Tk):
    motion.fade_in(win, enabled=False)
    try:
        assert float(win.attributes("-alpha")) == 1.0
    except tk.TclError:
        pytest.skip("透明度未対応の環境")


def test_fade_in_enabled_runs_without_error(win: tk.Tk):
    motion.fade_in(win, enabled=True, duration_ms=20, steps=4)
    win.update_idletasks()


def test_fade_out_enabled_eventually_calls_on_done(win: tk.Tk):
    calls: list[int] = []
    motion.fade_out(win, lambda: calls.append(1), enabled=True, duration_ms=20, steps=4)
    # afterで進むので、規定回数ぶんイベントループを回す。
    for _ in range(20):
        if calls:
            break
        win.update()
        win.after(5)
    assert calls == [1]
