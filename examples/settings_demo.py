"""katachiの典型的な使い方。アプリ設定画面を1関数で出す。

実行: python examples/settings_demo.py
"""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated

import katachi
from katachi import Choices, DirPath, Help, Label, Multiline, Range, Secret


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class NetworkSettings:
    host: Annotated[str, Label("接続先ホスト")] = "localhost"
    port: Annotated[int, Range(1, 65535), Label("ポート")] = 8080
    use_tls: Annotated[bool, Label("TLSを使う")] = False
    api_token: Annotated[str, Secret(), Label("APIトークン")] = ""


@dataclass
class AppSettings:
    theme: Annotated[str, Choices("light", "dark", "system"), Label("テーマ")] = "system"
    log_level: Annotated[LogLevel, Label("ログレベル")] = LogLevel.INFO
    workers: Annotated[int, Range(1, 32), Label("ワーカー数"), Help("並列処理の上限")] = 4
    data_dir: Annotated[Path, DirPath(), Label("データ保存先")] = Path("~/app-data")
    valid_until: Annotated[datetime.date, Label("有効期限"), Help("YYYY-MM-DD")] = datetime.date(
        2027, 3, 31
    )
    exclude: Annotated[list[str], Label("除外パターン")] = field(default_factory=list)
    note: Annotated[str, Multiline(height=4), Label("メモ")] = ""
    network: Annotated[NetworkSettings, Label("ネットワーク")] = field(
        default_factory=NetworkSettings
    )


def main() -> None:
    result = katachi.edit(
        AppSettings,
        store="~/.config/katachi-demo/settings.json",
        title="設定 - katachiデモ",
    )
    if result is None:
        print("キャンセルされた")
    else:
        print("保存された:")
        print(result)


if __name__ == "__main__":
    main()
