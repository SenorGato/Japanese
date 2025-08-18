# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterable
from typing import Union

from anki.utils import no_bundled_libs

from ..ajt_common.utils import find_executable

THIS_ADDON_MODULE = __name__.split(".")[0]


def walk_parents(dir_or_file_path: Union[str, pathlib.Path]) -> Iterable[pathlib.Path]:
    current_dir = pathlib.Path(dir_or_file_path)
    if current_dir.is_dir():
        yield current_dir
    while not current_dir.samefile(parent_dir := current_dir.parent):
        yield parent_dir
        current_dir = parent_dir


def touch(path: Union[str, pathlib.Path]) -> None:
    with open(path, "a"):
        os.utime(path, None)


def rm_file(path: Union[str, pathlib.Path]) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def find_file_in_parents(file_name: str) -> pathlib.Path:
    """Used when testing/debugging."""
    for parent_dir in walk_parents(__file__):
        if (path := parent_dir.joinpath(file_name)).is_file():
            return path
    raise RuntimeError(f"couldn't find file '{file_name}'")


def find_config_json() -> pathlib.Path:
    """Used when testing/debugging."""
    return find_file_in_parents("config.json")


def _platform_data_home(app_name: str) -> pathlib.Path:
    """
    Return a per-user writable data directory for the app/add-on.
    """
    if sys.platform.startswith("linux"):
        base = (
            os.environ.get("XDG_STATE_HOME")
            or os.environ.get("XDG_DATA_HOME")
            or str(pathlib.Path.home() / ".local" / "share")
        )
        return pathlib.Path(base) / "anki-addons" / app_name

    if sys.platform == "darwin":
        return pathlib.Path.home() / "Library" / "Application Support" / "Anki" / "Addons" / app_name

    # Windows fallback
    base = os.environ.get("APPDATA", str(pathlib.Path.home() / "AppData" / "Roaming"))
    return pathlib.Path(base) / "Anki" / "Addons" / app_name


@functools.cache
def user_files_dir() -> pathlib.Path:
    """
    Return a per-user writable directory for this add-on’s data/state.

    Priority:
      1) $AJT_USER_FILES_DIR if set (absolute path).
      2) Platform-appropriate user data dir (XDG/macOS/Windows).
      3) (Optional) Legacy repo 'user_files' when $AJT_USE_REPO_USER_FILES=1.
    """
    # 1) explicit override
    override = os.environ.get("AJT_USER_FILES_DIR")
    if override:
        p = pathlib.Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 2) platform default
    p = _platform_data_home(THIS_ADDON_MODULE)
    p.mkdir(parents=True, exist_ok=True)

    # 3) optional legacy fallback for devs
    if os.environ.get("AJT_USE_REPO_USER_FILES") == "1":
        for parent_dir in walk_parents(__file__):
            legacy = parent_dir / "user_files"
            if legacy.is_dir():
                return legacy

    return p


def open_file(path: str) -> None:
    """
    Select file in lf, the preferred terminal file manager, or open it with xdg-open.
    """
    from aqt.qt import QDesktopServices, QUrl

    if (terminal := os.getenv("TERMINAL")) and (lf := (os.getenv("FILE") or find_executable("lf"))):
        subprocess.Popen(
            [terminal, "-e", lf, path],
            shell=False,
            start_new_session=True,
        )
    elif opener := find_executable("xdg-open"):
        subprocess.Popen(
            [opener, f"file://{path}"],
            shell=False,
            start_new_session=True,
        )
    else:
        with no_bundled_libs():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def file_exists(file_path: str) -> bool:
    return bool(file_path and os.path.isfile(file_path) and os.stat(file_path).st_size > 0)
