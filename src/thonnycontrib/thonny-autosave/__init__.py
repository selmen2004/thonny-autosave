import re
from datetime import datetime
from logging import getLogger
from tkinter import messagebox

from thonny import get_workbench
from thonny.languages import tr

get_workbench().set_default("general.autosave", True)
get_workbench().set_default("general.bac_mode", False)
logger = getLogger(__name__)
logger.setLevel(51)

_WARNING_MESSAGE = (
    "Vous devez enregistrer dans C:/Bac{year}/xxxxxx où xxxxxx est votre numéro d'inscription"
)


def toggle_autosave():
    get_workbench().set_option("general.autosave", not get_workbench().get_option("general.autosave"))


def toggle_bac_mode():
    enabled = not get_workbench().get_option("general.bac_mode")
    get_workbench().set_option("general.bac_mode", enabled)
    get_workbench().set_option("general.event_logging", enabled)


def _is_bac_mode_enabled():
    return bool(get_workbench().get_option("general.bac_mode"))


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _is_valid_bac_path(filename: str) -> bool:
    current_year = datetime.now().year
    normalized = _normalize_path(filename)
    pattern = rf"^C:/Bac\s*{current_year}/\d{{6}}/"
    return bool(re.match(pattern, normalized, flags=re.IGNORECASE))


def _warn_bac_path():
    current_year = datetime.now().year
    messagebox.showwarning("Mode Bac", _WARNING_MESSAGE.format(year=current_year), master=get_workbench())


def _validate_bac_path(filename: str) -> bool:
    if not _is_bac_mode_enabled() or not filename:
        return True

    if _is_valid_bac_path(filename):
        return True

    _warn_bac_path()
    return False


def _on_file_event(event):
    filename = getattr(event, "filename", "")
    if filename:
        _validate_bac_path(filename)


def save_current():
    logger.info("entering save_current")
    get_workbench().after(10000, save_current)

    editor = get_workbench().get_editor_notebook().get_current_editor()
    if editor is None:
        return

    filename = editor.get_filename(False)
    if not filename:
        return

    if editor.is_modified() and get_workbench().get_option("general.autosave"):
        if _validate_bac_path(filename):
            editor.save_file()


def load_plugin():
    get_workbench().add_command(
        "toggle_autosave",
        "file",
        tr("Autosave"),
        flag_name="general.autosave",
        handler=toggle_autosave,
    )

    get_workbench().add_command(
        "toggle_bac_mode",
        "file",
        tr("Mode Bac"),
        flag_name="general.bac_mode",
        handler=toggle_bac_mode,
    )

    get_workbench().bind("Save", _on_file_event, True)
    get_workbench().bind("SaveAs", _on_file_event, True)
    get_workbench().bind("Open", _on_file_event, True)
    logger.info("running save_current")
    save_current()
