from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import aqt
from aqt import gui_hooks, mw
from aqt.qt import QTimer


RESULT_ENV = "ANKI_ADDON_WORKBENCH_RESULT"
ADDON_MODULE = "web_embed_tools"


def _write(payload: dict) -> None:
    with open(os.environ[RESULT_ENV], "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _finish(payload: dict) -> None:
    _write(payload)
    mw.app.quit()


def _run_checks() -> None:
    try:
        hooks_registered = bool(gui_hooks.editor_will_show_context_menu)
        addon = sys.modules.get(ADDON_MODULE)
        add_cards = aqt.dialogs.open("AddCards", mw)
        add_cards.resize(900, 650)
        add_cards.move(0, 0)
        add_cards.show()
        editor = add_cards.editor
        note = editor.note
        if note is None or addon is None:
            raise AssertionError("add-cards editor or add-on module was not ready")

        note.fields[0] = addon._embed_insertion_html("https://en.wikipedia.org/wiki/Anki_(software)")
        editor.loadNote(0)

        def decorate_select_and_capture() -> None:
            addon._decorate_editor_embeds(editor)
            editor.web.eval(
                """
                (function () {
                  const root = document.querySelector('.rich-text-editable');
                  const embed = root && root.querySelector('[data-wiki-embed="1"]');
                  if (embed) {
                    embed.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                  }
                })();
                """
            )

            def capture_and_finish() -> None:
                screenshot = os.environ.get("ANKI_ADDON_WORKBENCH_SCREENSHOT")
                screenshot_ok = False
                if screenshot:
                    path = Path(screenshot)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    screenshot_ok = add_cards.grab().save(str(path), "PNG")

                payload = {
                    "ok": (
                        ADDON_MODULE in sys.modules
                        and hooks_registered
                        and screenshot_ok
                    ),
                    "checks": [
                        {"name": "addon module loaded", "ok": ADDON_MODULE in sys.modules},
                        {"name": "editor context hook registered", "ok": hooks_registered},
                        {"name": "real Add Cards editor opened", "ok": True},
                        {"name": "embed editor screenshot saved", "ok": screenshot_ok},
                    ],
                    "screenshot": screenshot if screenshot_ok else None,
                }
                # This is a disposable unsaved note created only for the probe.
                # Bypass AddCards' user-facing discard confirmation so the
                # headless smoke remains fully unattended.
                add_cards._close()
                _finish(payload)

            QTimer.singleShot(3_000, capture_and_finish)

        QTimer.singleShot(1_000, decorate_select_and_capture)
    except Exception as exc:
        _finish({"ok": False, "error": repr(exc)})


def _after_profile_open() -> None:
    QTimer.singleShot(0, _run_checks)


gui_hooks.profile_did_open.append(_after_profile_open)
