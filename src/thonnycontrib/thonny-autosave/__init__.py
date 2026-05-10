import re
from datetime import date, datetime
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
_BLINK_PERIOD_MS = 700
_should_show_untitled_title = True

_UI_EXTENSION_WARNING = "En mode Bac, l'enregistrement des fichiers .ui est interdit."
_original_save_file = None
_original_ask_new_path = None

_BAC_LOCK_START = date(2026, 5, 19)
_BAC_LOCK_END = date(2026, 5, 23)




def _is_bac_lock_period() -> bool:
    today = datetime.now().date()
    return _BAC_LOCK_START <= today <= _BAC_LOCK_END


def _enforce_bac_mode_and_logging_if_required():
    if _is_bac_lock_period():
        get_workbench().set_option("general.bac_mode", True)
        get_workbench().set_option("general.event_logging", True)

def toggle_autosave():
    get_workbench().set_option("general.autosave", not get_workbench().get_option("general.autosave"))


def toggle_bac_mode():
    if _is_bac_lock_period():
        get_workbench().set_option("general.bac_mode", True)
        get_workbench().set_option("general.event_logging", True)
        messagebox.showwarning("Mode Bac", "Du 19 mai 2026 au 23 mai 2026, le Mode Bac ne peut pas être désactivé.", master=get_workbench())
        return

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



def _is_forbidden_extension(filename: str) -> bool:
    return filename.lower().endswith(".ui")


def _warn_forbidden_extension():
    messagebox.showwarning("Mode Bac", _UI_EXTENSION_WARNING, master=get_workbench())


def _is_save_allowed(filename: str) -> bool:
    if not _is_bac_mode_enabled():
        return True

    if _is_forbidden_extension(filename):
        _warn_forbidden_extension()
        return False

    return _validate_bac_path(filename)


def _patch_editor_save_file():
    global _original_save_file, _original_ask_new_path
    if _original_save_file is not None:
        return

    try:
        from thonny.editors import Editor
    except Exception:
        return

    _original_save_file = Editor.save_file
    _original_ask_new_path = Editor.ask_new_path

    def wrapped_ask_new_path(self, *args, **kwargs):
        path = _original_ask_new_path(self, *args, **kwargs)
        if path and _is_bac_mode_enabled() and _is_forbidden_extension(path):
            _warn_forbidden_extension()
            return None
        return path

    def wrapped_save_file(self, *args, **kwargs):
        if _is_bac_mode_enabled() and self._filename and _is_forbidden_extension(self._filename):
            _warn_forbidden_extension()
            return None

        return _original_save_file(self, *args, **kwargs)

    Editor.ask_new_path = wrapped_ask_new_path
    Editor.save_file = wrapped_save_file

def _on_file_event(event):
    filename = getattr(event, "filename", "")
    if filename:
        _is_save_allowed(filename)


def _get_current_editor():
    try:
        editor_notebook = get_workbench().get_editor_notebook()
    except (AssertionError, AttributeError):
        return None, None

    return editor_notebook, editor_notebook.get_current_editor()


def _blink_unsaved_untitled():
    global _should_show_untitled_title
    get_workbench().after(_BLINK_PERIOD_MS, _blink_unsaved_untitled)

    editor_notebook, editor = _get_current_editor()
    if editor is None or editor_notebook is None:
        return

    if not _is_bac_mode_enabled() or editor.get_filename(False) is not None:
        editor_notebook.update_editor_title(editor)
        return

    if _should_show_untitled_title:
        editor_notebook.update_editor_title(editor, tr("<untitled>"))
    else:
        editor_notebook.update_editor_title(editor, " " * len(tr("<untitled>")))

    _should_show_untitled_title = not _should_show_untitled_title


def save_current():
    get_workbench().after(10000, save_current)

    editor_notebook, editor = _get_current_editor()
    if editor is None or editor_notebook is None:
        return

    filename = editor.get_filename(False)
    if not filename:
        return

    if editor.is_modified() and get_workbench().get_option("general.autosave"):
        if _is_save_allowed(filename):
            editor.save_file()


def _on_workbench_ready(event):
    _enforce_bac_mode_and_logging_if_required()
    _patch_editor_save_file()
    save_current()
    _blink_unsaved_untitled()


def load_plugin():
    _enforce_bac_mode_and_logging_if_required()

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
    get_workbench().bind("WorkbenchReady", _on_workbench_ready, True)
