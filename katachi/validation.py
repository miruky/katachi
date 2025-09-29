"""ウィジェットの生入力を型付きの値に変換・検証する。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from .schema import FieldSpec


def coerce_field(spec: FieldSpec, raw: Any) -> Any:
    """生入力をspecの型へ変換する。不正ならValueError(メッセージは利用者向け)。"""
    handler = _HANDLERS.get(spec.kind)
    if handler is None:
        raise ValueError(f"変換できない種別: {spec.kind}")
    return handler(spec, raw)


def display_choice(spec: FieldSpec, value: Any) -> str:
    """選択肢の値を表示文字列にする。"""
    if spec.enum_type is not None and isinstance(value, Enum):
        return value.name
    return str(value)


def _coerce_bool(_spec: FieldSpec, raw: Any) -> bool:
    return bool(raw)


def _coerce_int(spec: FieldSpec, raw: Any) -> int:
    text = str(raw).strip()
    if not text:
        raise ValueError("整数を入力してください")
    try:
        value = int(text)
    except ValueError:
        raise ValueError("整数を入力してください") from None
    return _check_range(spec, value)


def _coerce_float(spec: FieldSpec, raw: Any) -> float:
    text = str(raw).strip()
    if not text:
        raise ValueError("数値を入力してください")
    try:
        value = float(text)
    except ValueError:
        raise ValueError("数値を入力してください") from None
    return _check_range(spec, value)


def _check_range[T: (int, float)](spec: FieldSpec, value: T) -> T:
    if spec.range is not None and not (spec.range.min <= value <= spec.range.max):
        raise ValueError(f"{spec.range.min}以上{spec.range.max}以下にしてください")
    return value


def _coerce_text(_spec: FieldSpec, raw: Any) -> str:
    return str(raw)


def _coerce_choice(spec: FieldSpec, raw: Any) -> Any:
    assert spec.choices is not None
    for choice in spec.choices:
        if raw == choice or str(raw) == display_choice(spec, choice):
            return choice
    raise ValueError("選択肢から選んでください")


def _coerce_path(_spec: FieldSpec, raw: Any) -> Path:
    text = str(raw).strip()
    if not text:
        raise ValueError("パスを入力してください")
    return Path(text)


def _coerce_str_list(_spec: FieldSpec, raw: Any) -> list[str]:
    if not isinstance(raw, list | tuple):
        raise ValueError("文字列のリストを指定してください")
    return [str(item) for item in raw if str(item).strip()]


_HANDLERS = {
    "bool": _coerce_bool,
    "int": _coerce_int,
    "float": _coerce_float,
    "text": _coerce_text,
    "choice": _coerce_choice,
    "path": _coerce_path,
    "str_list": _coerce_str_list,
}
