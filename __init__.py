from __future__ import annotations

from dataclasses import dataclass
import json

from aqt import gui_hooks
from aqt.editor import Editor, EditorWebView
from aqt.operations.note import update_note
from aqt.qt import (
    QAction,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMenu,
    QTimer,
    QVBoxLayout,
    sip,
)
from aqt.utils import showInfo, showWarning, tooltip

from .wikipedia_embed_core import (
    ConversionSettings,
    build_embed_html,
    canonicalize_editor_embeds,
    convert_matching_anchor_in_field,
    normalize_embed_url,
    resize_embed_html,
)


DEFAULT_SETTINGS = ConversionSettings()
WIDTH_PRESETS = ["100%", "90%", "75%", "66%", "50%", "960px", "800px", "640px", "480px"]
HEIGHT_PRESETS = ["320px", "480px", "600px", "720px", "900px", "50%", "75%", "100%"]
EDITOR_HELPERS_JS = """
(function() {
  window.wikiEmbedSaveSelection = function() {
    // Anki's rich-text fields live in separate shadow roots. The document
    // selection retargets their ranges to the field host, which would insert
    // the iframe outside the editable note content.
    const scopes = Array.from(document.querySelectorAll('.rich-text-editable'))
      .map((host) => host.shadowRoot || host);
    scopes.push(document);
    for (const scope of scopes) {
      const selection = typeof scope.getSelection === 'function'
        ? scope.getSelection() : window.getSelection();
      if (!selection || selection.rangeCount === 0) continue;
      const range = selection.getRangeAt(0);
      const ancestor = range.commonAncestorContainer;
      const editable = ancestor.nodeType === Node.ELEMENT_NODE
        ? ancestor.closest('[contenteditable="true"]')
        : ancestor.parentElement && ancestor.parentElement.closest('[contenteditable="true"]');
      if (!editable || !scope.contains(ancestor)) continue;
      window.wikiEmbedSavedRange = range.cloneRange();
      window.wikiEmbedSavedSelection = selection;
      window.wikiEmbedSavedEditable = editable;
      return true;
    }
    window.wikiEmbedSavedRange = null;
    window.wikiEmbedSavedSelection = null;
    window.wikiEmbedSavedEditable = null;
    return false;
  };
  window.wikiEmbedRestoreSelection = function() {
    const selection = window.wikiEmbedSavedSelection;
    if (!selection || !window.wikiEmbedSavedRange) {
      return false;
    }
    selection.removeAllRanges();
    selection.addRange(window.wikiEmbedSavedRange);
    return true;
  };
  window.wikiEmbedInsertAtSavedSelection = function(html) {
    if (!window.wikiEmbedRestoreSelection()) {
      return false;
    }
    const selection = window.wikiEmbedSavedSelection;
    if (!selection || selection.rangeCount === 0) {
      return false;
    }
    const range = selection.getRangeAt(0);
    range.deleteContents();
    const template = document.createElement('template');
    template.innerHTML = html;
    const fragment = template.content;
    const lastNode = fragment.lastChild;
    range.insertNode(fragment);
    if (lastNode) {
      const after = document.createRange();
      if (lastNode.nodeType === Node.ELEMENT_NODE && lastNode.tagName === 'DIV') {
        after.selectNodeContents(lastNode);
        after.collapse(true);
      } else {
        after.setStartAfter(lastNode);
        after.collapse(true);
      }
      selection.removeAllRanges();
      selection.addRange(after);
    }
    window.wikiEmbedSavedEditable.dispatchEvent(new InputEvent('input', {bubbles: true}));
    return true;
  };
  window.wikiEmbedState = window.wikiEmbedState || {};
  window.wikiEmbedGetRoots = function() {
    const richTextPackage = require("anki/RichTextInput");
    return richTextPackage.instances.map((instance) => instance.element);
  };
  window.wikiEmbedEmbeds = function(root) {
    return Array.from(root.querySelectorAll('[data-wiki-embed="1"]'));
  };
  window.wikiEmbedToolbarKey = '__wikiEmbedToolbar';
  window.wikiEmbedSelectedIndex = function(root, embeds) {
    const selected = embeds.findIndex((embed) => embed.dataset.wikiEditorSelected === "1");
    if (selected >= 0) {
      return selected;
    }
    return embeds.length > 0 ? 0 : -1;
  };
  window.wikiEmbedSetSelected = function(root, index) {
    const embeds = window.wikiEmbedEmbeds(root);
    embeds.forEach((embed, currentIndex) => {
      if (currentIndex === index) {
        embed.dataset.wikiEditorSelected = "1";
      } else {
        delete embed.dataset.wikiEditorSelected;
      }
    });
    window.wikiEmbedRenderRoot(root);
  };
  window.wikiEmbedScheduleRender = function(root) {
    if (root.__wikiEmbedRaf) {
      return;
    }
    root.__wikiEmbedRaf = window.requestAnimationFrame(() => {
      root.__wikiEmbedRaf = 0;
      window.wikiEmbedRenderRoot(root);
    });
  };
  window.wikiEmbedEnsureObservers = function(root) {
    if (root.__wikiEmbedObserverBound === '1') {
      return;
    }
    root.__wikiEmbedObserverBound = '1';
    const observer = new MutationObserver(() => window.wikiEmbedScheduleRender(root));
    observer.observe(root, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    root.__wikiEmbedObserver = observer;
    root.addEventListener('input', () => window.wikiEmbedScheduleRender(root));
    root.addEventListener('keyup', () => window.wikiEmbedScheduleRender(root));
    root.addEventListener('mouseup', () => window.wikiEmbedScheduleRender(root));
    window.addEventListener('resize', () => window.wikiEmbedScheduleRender(root));
    window.addEventListener('scroll', () => window.wikiEmbedScheduleRender(root), true);
  };
  window.wikiEmbedAdjust = function(root, index, deltaWidth, deltaHeight) {
    const embeds = window.wikiEmbedEmbeds(root);
    const embed = embeds[index];
    if (!embed) {
      return;
    }
    const rect = embed.getBoundingClientRect();
    const parentRect = embed.parentElement ? embed.parentElement.getBoundingClientRect() : rect;
    const minWidth = 320;
    const minHeight = 180;
    const maxWidth = Math.max(minWidth, Math.floor(parentRect.width - 12));
    const nextWidth = Math.min(maxWidth, Math.max(minWidth, Math.round(rect.width + deltaWidth)));
    const nextHeight = Math.max(minHeight, Math.round(rect.height + deltaHeight));
    embed.style.width = `${nextWidth}px`;
    embed.style.height = `${nextHeight}px`;
    window.wikiEmbedRenderRoot(root);
  };
  window.wikiEmbedInsertLineNear = function(root, index, where) {
    const embeds = window.wikiEmbedEmbeds(root);
    const embed = embeds[index];
    if (!embed || !embed.parentNode) {
      return;
    }
    const line = document.createElement('div');
    line.innerHTML = '&nbsp;';
    if (where === 'above') {
      embed.parentNode.insertBefore(line, embed);
    } else {
      embed.parentNode.insertBefore(line, embed.nextSibling);
    }
    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(line);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    window.wikiEmbedRenderRoot(root);
  };
  window.wikiEmbedEnsureToolbar = function(root) {
    let toolbar = root[window.wikiEmbedToolbarKey];
    if (toolbar && toolbar.isConnected) {
      return toolbar;
    }
    toolbar = document.createElement('div');
    toolbar.className = 'wiki-embed-editor-toolbar';
    toolbar.contentEditable = 'false';
    toolbar.style.cssText = 'position: fixed; z-index: 2147483647; display: none; gap: 4px; align-items: center; flex-wrap: wrap; background: rgba(255,255,255,0.96); padding: 6px 8px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.08);';
    document.body.appendChild(toolbar);
    root[window.wikiEmbedToolbarKey] = toolbar;
    return toolbar;
  };
  window.wikiEmbedToolbarPosition = function(toolbar, embed) {
    const rect = embed.getBoundingClientRect();
    const top = Math.max(8, Math.round(rect.top + 8));
    const left = Math.max(8, Math.min(Math.round(rect.left + 8), window.innerWidth - toolbar.offsetWidth - 8));
    toolbar.style.top = `${top}px`;
    toolbar.style.left = `${left}px`;
  };
  window.wikiEmbedMakeButton = function(label, onClick, extraStyle = '') {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.style.cssText = 'border: 1px solid #b8b8b8; background: rgba(255,255,255,0.95); border-radius: 4px; padding: 2px 6px; font-size: 11px; cursor: pointer;' + extraStyle;
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      event.stopPropagation();
    });
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      onClick();
    });
    return button;
  };
  window.wikiEmbedRenderToolbar = function(root, embed, index, total, selectedIndex) {
    const toolbar = window.wikiEmbedEnsureToolbar(root);
    toolbar.replaceChildren();
    const label = document.createElement('span');
    label.style.cssText = 'font-size: 11px; color: #333; font-family: sans-serif;';
    const multiple = total > 1;
    label.textContent = multiple ? `Embed ${index + 1} of ${total}` : 'Web embed';
    toolbar.appendChild(label);

    if (multiple) {
      toolbar.appendChild(window.wikiEmbedMakeButton('Prev', () => window.wikiEmbedSetSelected(root, Math.max(0, selectedIndex - 1))));
      toolbar.appendChild(window.wikiEmbedMakeButton('Next', () => window.wikiEmbedSetSelected(root, Math.min(total - 1, selectedIndex + 1))));
    }

    toolbar.appendChild(window.wikiEmbedMakeButton('Size…', () => {
      pycmd(`wikiEmbed:${JSON.stringify({
        cmd: 'exactSize',
        fieldOrd: Number(root.dataset.wikiFieldOrd || '-1'),
        embedIndex: selectedIndex,
        width: embed.style.width || '',
        height: embed.style.height || '',
      })}`);
    }));
    toolbar.appendChild(window.wikiEmbedMakeButton('W-', () => window.wikiEmbedAdjust(root, selectedIndex, -80, 0)));
    toolbar.appendChild(window.wikiEmbedMakeButton('W+', () => window.wikiEmbedAdjust(root, selectedIndex, 80, 0)));
    toolbar.appendChild(window.wikiEmbedMakeButton('H-', () => window.wikiEmbedAdjust(root, selectedIndex, 0, -60)));
    toolbar.appendChild(window.wikiEmbedMakeButton('H+', () => window.wikiEmbedAdjust(root, selectedIndex, 0, 60)));
    toolbar.appendChild(window.wikiEmbedMakeButton('+ above', () => window.wikiEmbedInsertLineNear(root, selectedIndex, 'above')));
    toolbar.appendChild(window.wikiEmbedMakeButton('+ below', () => window.wikiEmbedInsertLineNear(root, selectedIndex, 'below')));
    toolbar.appendChild(window.wikiEmbedMakeButton('❌', () => {
      const target = window.wikiEmbedEmbeds(root)[selectedIndex];
      if (!target) {
        return;
      }
      target.remove();
      window.wikiEmbedRenderRoot(root);
    }, 'color: #c62828;'));
    toolbar.style.display = 'flex';
    window.wikiEmbedToolbarPosition(toolbar, embed);
  };
  window.wikiEmbedRenderRoot = function(root) {
    window.wikiEmbedEnsureObservers(root);
    const embeds = window.wikiEmbedEmbeds(root);
    const toolbar = window.wikiEmbedEnsureToolbar(root);
    if (embeds.length === 0) {
      toolbar.style.display = 'none';
      return;
    }
    const selectedIndex = window.wikiEmbedSelectedIndex(root, embeds);
    embeds.forEach((embed, index) => {
      const multiple = embeds.length > 1;
      const isSelected = index === selectedIndex;
      embed.setAttribute('contenteditable', 'false');
      embed.classList.add('wiki-embed-editor-live');
      embed.style.position = 'relative';
      embed.style.boxSizing = 'border-box';
      embed.style.outline = multiple && isSelected ? '2px solid #4c9ffe' : 'none';
      embed.style.outlineOffset = multiple && isSelected ? '2px' : '0';
      const iframe = embed.querySelector('iframe');
      if (iframe) {
        iframe.style.pointerEvents = 'none';
      }
      if (embed.dataset.wikiEditorBound !== '1') {
        embed.dataset.wikiEditorBound = '1';
        embed.addEventListener('mousedown', (event) => {
          event.preventDefault();
          event.stopPropagation();
          const currentIndex = window.wikiEmbedEmbeds(root).indexOf(embed);
          if (currentIndex >= 0) {
            window.wikiEmbedSetSelected(root, currentIndex);
          }
        });
      }
    });
    window.wikiEmbedRenderToolbar(root, embeds[selectedIndex], selectedIndex, embeds.length, selectedIndex);
  };
  window.wikiEmbedDecorateEditorEmbeds = function() {
    window.wikiEmbedGetRoots().forEach((rootPromise, fieldOrd) => {
      rootPromise.then((root) => {
        root.dataset.wikiFieldOrd = String(fieldOrd);
        window.wikiEmbedRenderRoot(root);
      });
    });
  };
  window.wikiEmbedApplyExactSize = function(fieldOrd, embedIndex, width, height) {
    window.wikiEmbedGetRoots().forEach((rootPromise, currentFieldOrd) => {
      if (currentFieldOrd !== fieldOrd) {
        return;
      }
      rootPromise.then((root) => {
        const embed = window.wikiEmbedEmbeds(root)[embedIndex];
        if (!embed) {
          return;
        }
        embed.style.width = width;
        embed.style.height = height;
        window.wikiEmbedSetSelected(root, embedIndex);
      });
    });
  };
})();
"""


@dataclass(frozen=True)
class EditorContext:
    link_url: str | None
    selected_text: str


class EmbedSizeDialog(QDialog):
    def __init__(self, parent, width_value: str, height_value: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Embed Size")
        self.resize(380, 160)

        layout = QVBoxLayout(self)

        width_label = QLabel("Width")
        layout.addWidget(width_label)
        self.width_combo = QComboBox()
        self.width_combo.setEditable(True)
        self.width_combo.addItems(WIDTH_PRESETS)
        self.width_combo.setCurrentText(width_value or WIDTH_PRESETS[0])
        layout.addWidget(self.width_combo)

        height_label = QLabel("Height")
        layout.addWidget(height_label)
        self.height_combo = QComboBox()
        self.height_combo.setEditable(True)
        self.height_combo.addItems(HEIGHT_PRESETS)
        self.height_combo.setCurrentText(height_value or HEIGHT_PRESETS[1])
        layout.addWidget(self.height_combo)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def values(self) -> tuple[str, str]:
        return self.width_combo.currentText().strip(), self.height_combo.currentText().strip()


def _selected_field_index(editor: Editor) -> int | None:
    if editor.currentField is not None:
        return editor.currentField
    return editor.last_field_index


def _context_request(webview: EditorWebView):
    if not hasattr(webview, "lastContextMenuRequest"):
        return None
    request = webview.lastContextMenuRequest()
    return request


def _editor_context(webview: EditorWebView) -> EditorContext:
    request = _context_request(webview)
    link_url: str | None = None
    selected_text = ""

    if request is not None:
        try:
            qurl = request.linkUrl()
            if qurl and not qurl.isEmpty():
                link_url = qurl.toString()
        except Exception:
            link_url = None

        try:
            selected_text = request.selectedText() or ""
        except Exception:
            selected_text = ""

    if not selected_text:
        try:
            selected_text = webview.selectedText() or ""
        except Exception:
            selected_text = ""

    return EditorContext(link_url=link_url, selected_text=selected_text.strip())


def _convert_clicked_link(editor: Editor, link_url: str) -> None:
    normalized = normalize_embed_url(link_url)
    if normalized is None:
        showWarning("That link is not a supported http(s) URL.", parent=editor.widget)
        return

    def apply_conversion() -> None:
        note = editor.note
        if note is None:
            return

        field_index = _selected_field_index(editor)
        if field_index is None:
            showWarning("Select a field before converting a link.", parent=editor.widget)
            return

        current_html = note.fields[field_index]
        result = convert_matching_anchor_in_field(
            current_html,
            normalized,
            settings=DEFAULT_SETTINGS,
        )
        if not result.changed:
            showInfo("No matching link was found in the current field.", parent=editor.widget)
            return

        note.fields[field_index] = result.html

        if editor.addMode:
            editor.loadNote(field_index)
            tooltip("Converted link to embed.", parent=editor.widget)
            return

        update_note(parent=editor.widget, note=note).success(
            lambda _out: (
                editor.loadNote(field_index),
                tooltip("Converted link to embed.", parent=editor.widget),
            )
        ).run_in_background(initiator=editor)

    editor.call_after_note_saved(apply_conversion, keepFocus=True)

def _insert_selected_url(editor: Editor, selected_text: str) -> None:
    normalized = normalize_embed_url(selected_text)
    if normalized is None:
        showWarning("The selected text is not a valid http(s) URL.", parent=editor.widget)
        return
    editor.web.evalWithCallback(
        f"{EDITOR_HELPERS_JS}\nwindow.wikiEmbedSaveSelection();",
        lambda _res: _insert_embed_at_selection(editor, normalized),
    )


def _embed_insertion_html(url: str) -> str:
    embed_html = build_embed_html(
        url,
        width=DEFAULT_SETTINGS.width,
        height=DEFAULT_SETTINGS.height,
    )
    return embed_html + "<div>&nbsp;</div>"


def _insert_embed_at_selection(editor: Editor, url: str) -> None:
    payload_html = _embed_insertion_html(url)
    editor.web.setFocus()

    def after_insert(_res) -> None:
        editor.web.evalWithCallback(
            "saveNow(1)",
            lambda _save_res: tooltip("Inserted embed.", parent=editor.widget),
        )

    insert_js = (
        f"{EDITOR_HELPERS_JS}\n"
        f"window.wikiEmbedInsertAtSavedSelection({json.dumps(payload_html)});\n"
        "window.wikiEmbedDecorateEditorEmbeds();"
    )
    editor.web.evalWithCallback(insert_js, after_insert)


def _decorate_editor_embeds(editor: Editor) -> None:
    web = getattr(editor, "web", None)
    if web is None or sip.isdeleted(web):
        return
    web.eval(f"{EDITOR_HELPERS_JS}\nwindow.wikiEmbedDecorateEditorEmbeds();")


def _schedule_editor_embed_decoration(editor: Editor, delays_ms: tuple[int, ...] = (0, 75, 200)) -> None:
    if editor.web is None:
        return

    for delay in delays_ms:
        QTimer.singleShot(delay, lambda e=editor: _decorate_editor_embeds(e))


def _canonicalize_editor_html(txt: str, editor: Editor) -> str:
    return canonicalize_editor_embeds(txt)


def _add_menu_action(menu: QMenu, label: str, callback) -> QAction:
    action = menu.addAction(label)
    assert action is not None
    action.triggered.connect(callback)
    return action


def _on_editor_context_menu(editor_webview: EditorWebView, menu: QMenu) -> None:
    editor = editor_webview.editor
    if editor.note is None:
        return

    context = _editor_context(editor_webview)
    normalized_link = normalize_embed_url(context.link_url or "")
    normalized_selected_url = normalize_embed_url(context.selected_text) if context.selected_text else None

    if normalized_link is not None:
        _add_menu_action(
            menu,
            "Create Embed from URL",
            lambda checked=False, e=editor, url=normalized_link: _convert_clicked_link(e, url),
        )
    elif normalized_selected_url is not None:
        _add_menu_action(
            menu,
            "Create Embed from URL",
            lambda checked=False, e=editor, text=context.selected_text: _insert_selected_url(e, text),
        )



def _normalize_size_value(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("Size must not be empty.")
    if text.endswith("%") or text.endswith("px"):
        return text
    if text.isdigit():
        return f"{text}px"
    raise ValueError("Use a number, a px value like 800px, or a percent like 75%.")


def _open_exact_size_dialog(editor: Editor, field_ord: int, embed_index: int, width: str, height: str) -> None:
    dialog = EmbedSizeDialog(editor.widget, width, height)
    if dialog.exec() != int(QDialog.DialogCode.Accepted):
        return

    width_value, height_value = dialog.values()
    try:
        normalized_width = _normalize_size_value(width_value)
        normalized_height = _normalize_size_value(height_value)
    except ValueError as exc:
        showWarning(str(exc), parent=editor.widget)
        return

    note = editor.note
    if note is None or field_ord < 0 or field_ord >= len(note.fields):
        return

    note.fields[field_ord] = resize_embed_html(
        note.fields[field_ord],
        embed_index=embed_index,
        width=normalized_width,
        height=normalized_height,
    )

    if editor.addMode:
        editor.loadNote(field_ord)
        tooltip("Updated embed size.", parent=editor.widget)
        return

    def on_success(_out) -> None:
        editor.loadNote(field_ord)
        tooltip("Updated embed size.", parent=editor.widget)

    update_note(parent=editor.widget, note=note).success(on_success).run_in_background(initiator=editor)


def _on_js_message(handled, message: str, context):
    if handled[0]:
        return handled
    if not isinstance(context, Editor):
        return handled
    if not message.startswith("wikiEmbed:"):
        return handled

    try:
        payload = json.loads(message[len("wikiEmbed:") :])
    except json.JSONDecodeError:
        return (True, None)

    if payload.get("cmd") == "exactSize":
        _open_exact_size_dialog(
            context,
            int(payload.get("fieldOrd", -1)),
            int(payload.get("embedIndex", -1)),
            str(payload.get("width", "")),
            str(payload.get("height", "")),
        )
        return (True, None)

    return (True, None)


def _on_browser_did_change_row(browser) -> None:
    editor = getattr(browser, "editor", None)
    if editor is None or editor.note is None:
        return
    _schedule_editor_embed_decoration(editor)


gui_hooks.editor_will_show_context_menu.append(_on_editor_context_menu)
gui_hooks.editor_did_load_note.append(_schedule_editor_embed_decoration)
gui_hooks.editor_will_munge_html.append(_canonicalize_editor_html)
gui_hooks.webview_did_receive_js_message.append(_on_js_message)
gui_hooks.browser_did_change_row.append(_on_browser_did_change_row)
