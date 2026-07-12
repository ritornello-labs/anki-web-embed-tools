from __future__ import annotations

import json
import os
import sys

from aqt import gui_hooks, mw
from aqt.qt import QTimer


RESULT_ENV = "ANKI_ADDON_WORKBENCH_RESULT"
ADDON_MODULE = "web_embed_tools"


def _write(payload: dict) -> None:
    with open(os.environ[RESULT_ENV], "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _run_checks() -> None:
    try:
        hooks_registered = bool(gui_hooks.editor_will_show_context_menu)
        _write(
            {
                "ok": ADDON_MODULE in sys.modules and hooks_registered,
                "checks": [
                    {"name": "addon module loaded", "ok": ADDON_MODULE in sys.modules},
                    {"name": "editor context hook registered", "ok": hooks_registered},
                ],
            }
        )
    except Exception as exc:
        _write({"ok": False, "error": repr(exc)})
    finally:
        mw.app.quit()


def _after_profile_open() -> None:
    QTimer.singleShot(0, _run_checks)


gui_hooks.profile_did_open.append(_after_profile_open)
