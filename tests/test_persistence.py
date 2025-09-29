"""JSON永続化の往復と互換性挙動のテスト。"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pytest

from katachi import PersistenceError, build, load, save, to_jsonable


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Network:
    host: str = "localhost"
    port: int = 8080


@dataclass
class Settings:
    theme: Theme = Theme.LIGHT
    workers: int = 4
    ratio: float = 0.5
    log_dir: Path = Path("logs")
    tags: list[str] = field(default_factory=list)
    network: Network = field(default_factory=Network)


def test_round_trip(tmp_path: Path):
    original = Settings(
        theme=Theme.DARK,
        workers=8,
        ratio=0.75,
        log_dir=Path("/var/log/app"),
        tags=["a", "b"],
        network=Network(host="example.com", port=443),
    )
    file = tmp_path / "settings.json"
    save(original, file)
    assert load(Settings, file) == original


def test_enum_is_stored_by_name(tmp_path: Path):
    file = tmp_path / "settings.json"
    save(Settings(theme=Theme.DARK), file)
    data = json.loads(file.read_text(encoding="utf-8"))
    assert data["theme"] == "DARK"


def test_missing_file_returns_defaults(tmp_path: Path):
    assert load(Settings, tmp_path / "none.json") == Settings()


def test_missing_keys_fall_back_to_defaults():
    settings = build(Settings, {"workers": 9})
    assert settings.workers == 9
    assert settings.theme is Theme.LIGHT
    assert settings.network == Network()


def test_unknown_keys_are_ignored():
    settings = build(Settings, {"removed_in_v2": True, "workers": 2})
    assert settings.workers == 2


def test_save_creates_parent_dirs(tmp_path: Path):
    file = tmp_path / "deep" / "nested" / "settings.json"
    save(Settings(), file)
    assert file.exists()


def test_broken_json_raises(tmp_path: Path):
    file = tmp_path / "broken.json"
    file.write_text("{not json", encoding="utf-8")
    with pytest.raises(PersistenceError):
        load(Settings, file)


def test_wrong_type_raises():
    with pytest.raises(PersistenceError, match="workers"):
        build(Settings, {"workers": "many"})
    with pytest.raises(PersistenceError, match="theme"):
        build(Settings, {"theme": "BLUE"})
    with pytest.raises(PersistenceError, match="network"):
        build(Settings, {"network": [1, 2]})


def test_int_field_rejects_bool():
    with pytest.raises(PersistenceError):
        build(Settings, {"workers": True})


def test_float_accepts_int_json():
    assert build(Settings, {"ratio": 1}).ratio == 1.0


def test_to_jsonable_rejects_non_dataclass():
    with pytest.raises(PersistenceError):
        to_jsonable({"plain": "dict"})
