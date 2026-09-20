"""Dialogs subpackage (SOLID SRP split: one dialog per module)."""
from .styles import DARK_STYLESHEET
from .preset import PresetManagerDialog
from .help import HelpDialog
from .settings import SettingsDialog
from .emergency import EmergencyCloseDialog

__all__ = ["DARK_STYLESHEET","PresetManagerDialog","HelpDialog","SettingsDialog","EmergencyCloseDialog"]
