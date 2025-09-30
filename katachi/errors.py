"""katachiの例外階層。"""

from __future__ import annotations

from dataclasses import dataclass


class KatachiError(Exception):
    """katachiが送出する全例外の基底。"""


class SchemaError(KatachiError):
    """dataclassの定義がkatachiの対応範囲外のときに送出される。"""


class PersistenceError(KatachiError):
    """設定ファイルの読み書きに失敗したときに送出される。"""


@dataclass(frozen=True, slots=True)
class FieldError:
    """1フィールド分の検証エラー。"""

    path: str
    label: str
    message: str


class FormValidationError(KatachiError):
    """フォームの入力値が不正なときに送出される。"""

    def __init__(self, errors: list[FieldError]) -> None:
        self.errors = errors
        detail = ", ".join(f"{e.label}: {e.message}" for e in errors)
        super().__init__(detail)
