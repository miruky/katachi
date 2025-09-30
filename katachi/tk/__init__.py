"""tkinterバックエンド。"""

from .dialog import edit
from .form import Form
from .theme import Palette, apply_theme, current_palette, detect_mode

__all__ = ["Form", "Palette", "apply_theme", "current_palette", "detect_mode", "edit"]
