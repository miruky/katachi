"""設定インスタンスとJSONファイルの相互変換。

EnumはnameをそのままJSONに書く。valueは型が揺れる(int/str混在など)ため、
一意で必ず文字列になるnameを採用している。
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import PersistenceError
from .schema import FieldSpec, introspect


def to_jsonable(obj: Any) -> dict[str, Any]:
    """dataclassインスタンスをJSON化可能なdictに変換する。"""
    if not dataclasses.is_dataclass(obj) or isinstance(obj, type):
        raise PersistenceError(f"{obj!r} はdataclassインスタンスではない")
    return {
        field.name: _value_to_jsonable(getattr(obj, field.name))
        for field in dataclasses.fields(obj)
    }


def _value_to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(value)
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, list | tuple):
        return [_value_to_jsonable(item) for item in value]
    return value


def build[T](cls: type[T], data: dict[str, Any]) -> T:
    """dictからdataclassインスタンスを組み立てる。

    欠けているキーはデフォルト値で埋め、知らないキーは無視する。
    将来のバージョンで増減したフィールドを許容するための仕様。
    """
    spec = introspect(cls)
    return _build_group(spec, data)


def _build_group(spec: FieldSpec, data: dict[str, Any]) -> Any:
    assert spec.group_type is not None
    kwargs: dict[str, Any] = {}
    for child in spec.children:
        if child.name not in data:
            continue
        kwargs[child.name] = _build_value(child, data[child.name])
    return spec.group_type(**kwargs)


def _build_value(spec: FieldSpec, value: Any) -> Any:
    try:
        if spec.kind == "group":
            if not isinstance(value, dict):
                raise ValueError("オブジェクトが必要")
            return _build_group(spec, value)
        if spec.kind == "choice":
            return _restore_choice(spec, value)
        if spec.kind == "date":
            try:
                return datetime.date.fromisoformat(str(value))
            except ValueError:
                raise ValueError("YYYY-MM-DD 形式の日付が必要") from None
        if spec.kind == "path":
            return Path(str(value))
        if spec.kind == "str_list":
            if not isinstance(value, list):
                raise ValueError("配列が必要")
            return [str(item) for item in value]
        if spec.kind == "bool":
            if not isinstance(value, bool):
                raise ValueError("真偽値が必要")
            return value
        if spec.kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("整数が必要")
            return value
        if spec.kind == "float":
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError("数値が必要")
            return float(value)
        return str(value)
    except ValueError as error:
        raise PersistenceError(f"フィールド '{spec.name}' を復元できない: {error}") from None


def _restore_choice(spec: FieldSpec, value: Any) -> Any:
    assert spec.choices is not None
    if spec.enum_type is not None:
        try:
            return spec.enum_type[str(value)]
        except KeyError:
            raise ValueError(f"'{value}' は {spec.enum_type.__name__} にない") from None
    for choice in spec.choices:
        if value == choice:
            return choice
    raise ValueError(f"'{value}' は選択肢にない")


def load[T](cls: type[T], path: str | Path) -> T:
    """JSONファイルから設定を読む。ファイルがなければデフォルト値を返す。"""
    file = Path(path).expanduser()
    if not file.exists():
        return cls()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PersistenceError(f"{file} を読めない: {error}") from None
    if not isinstance(data, dict):
        raise PersistenceError(f"{file} のルートはオブジェクトである必要がある")
    return build(cls, data)


def save(obj: Any, path: str | Path) -> None:
    """設定をJSONファイルに書く。親ディレクトリは自動で作る。"""
    file = Path(path).expanduser()
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(to_jsonable(obj), ensure_ascii=False, indent=2)
        file.write_text(text + "\n", encoding="utf-8")
    except OSError as error:
        raise PersistenceError(f"{file} に書けない: {error}") from None
