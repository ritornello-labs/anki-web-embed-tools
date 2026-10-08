from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import aqt
from aqt import gui_hooks, mw
from aqt.qt import QTimer, Qt, QPoint
from PyQt6.QtTest import QTest


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
        add_cards.resize(1100, 900)
        add_cards.move(0, 0)
        add_cards.show()
        editor = add_cards.editor
        note = editor.note
        if note is None or addon is None:
            raise AssertionError("add-cards editor or add-on module was not ready")

        url = "https://en.wikipedia.org/wiki/Anki_(software)"
        note.fields[0] = url
        editor.loadNote(0)

        def decorate_select_and_capture() -> None:
            # Exercise selected plain-text insertion, including modern Anki's
            # shadow-root selection and the actual editor serialization path.
            editor.web.setFocus()
            editor.web.eval(
                "require('anki/RichTextInput').instances[0].element.then(root => root.focus())"
            )

            def select_and_insert() -> None:
                add_cards.activateWindow()
                add_cards.raise_()

                def click_and_select(rect: dict) -> None:
                    target = editor.web.focusProxy() or editor.web
                    QTest.mouseClick(
                        target, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier,
                        QPoint(int(rect["x"]), int(rect["y"])),
                    )
                    QTest.keyClick(target, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
                    QTimer.singleShot(150, lambda: addon._insert_selected_url(editor, url))

                editor.web.evalWithCallback(
                    "(()=>{const r=document.querySelector('.rich-text-editable').getBoundingClientRect();return {x:r.x+80,y:r.y+r.height/2}})()",
                    click_and_select,
                )

            QTimer.singleShot(350, select_and_insert)

            def capture_and_finish() -> None:
                stored_html = editor.note.fields[0]
                if stored_html.count("<iframe") != 1 or url in stored_html.split("</iframe>")[-1]:
                    raise AssertionError(f"selected URL was not replaced inside the saved note field: {stored_html!r}")
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
                        {"name": "selected URL replaced by one serialized iframe in shadow-root field", "ok": True},
                        {"name": "embed editor screenshot saved", "ok": screenshot_ok},
                    ],
                    "screenshot": screenshot if screenshot_ok else None,
                }
                # This is a disposable unsaved note created only for the probe.
                # Bypass AddCards' user-facing discard confirmation so the
                # headless smoke remains fully unattended.
                add_cards._close()
                _finish(payload)

            def checked_capture() -> None:
                def after_saved() -> None:
                    try:
                        capture_and_finish()
                    except Exception as exc:
                        add_cards._close()
                        _finish({"ok": False, "error": repr(exc)})

                editor.call_after_note_saved(after_saved, keepFocus=True)

            QTimer.singleShot(3_000, checked_capture)

        QTimer.singleShot(1_000, decorate_select_and_capture)
    except Exception as exc:
        _finish({"ok": False, "error": repr(exc)})


def _after_profile_open() -> None:
    QTimer.singleShot(1_000, _run_checks)


gui_hooks.profile_did_open.append(_after_profile_open)
