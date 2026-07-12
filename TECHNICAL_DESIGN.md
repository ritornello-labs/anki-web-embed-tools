# Technical Design

## Overview

The add-on stores a simple embed wrapper in note HTML and decorates that wrapper inside Anki's rich-text editors with editor-only controls.

The design intentionally separates:

- persisted field HTML, which should stay simple and portable
- editor UI, which can be richer and more interactive

That split keeps note data stable while allowing a usable resize/edit experience around live iframes.

## Canonical stored HTML

```html
<div
  class="wiki-embed"
  data-wiki-embed="1"
  data-url="https://example.com/"
  style="width: 100%; height: 480px;"
>
  <iframe
    src="https://example.com/"
    loading="lazy"
    referrerpolicy="no-referrer-when-downgrade"
    style="width: 100%; height: 100%; border: 0;"
  ></iframe>
</div>
```

Notes:

- `data-wiki-embed="1"` is a legacy marker kept for compatibility.
- Width and height live on the wrapper `div`, not the iframe.
- The iframe is always stretched to `100%` of the wrapper.

## URL support

The shipped add-on accepts:

- any `http://` or `https://` URL with a hostname
- Wikipedia article URLs, which also get optional `data-wiki-lang` and `data-wiki-title` metadata

Non-article Wikipedia namespaces such as `File:` and `Special:` are still rejected by the Wikipedia-specific normalization helper.

## Python responsibilities

- inspect editor context-menu state
- distinguish between clicked-link conversion and selected-text URL insertion
- generate canonical embed HTML
- update note fields through Anki's editor and note-save operations
- open the exact-size dialog

## Editor webview responsibilities

- preserve and restore selection for selected-text insertion
- discover existing embeds in all rich-text roots
- render a floating toolbar for the selected embed
- apply temporary editor-only styles such as selection outlines
- insert blank lines above or below an embed without relying on awkward caret movement around iframes

## Toolbar model

The editor toolbar currently exposes:

- width and height increment/decrement buttons
- an exact-size dialog
- `+ above`
- `+ below`
- removal
- `Prev` and `Next` when multiple embeds exist in the same field

The toolbar is positioned relative to the selected embed and re-rendered on editor mutations, input, mouseup, scroll, and window resize events.

## Save-time canonicalization

When Anki saves the field, the add-on strips editor-only state and rewrites embeds back to the canonical stored HTML form.

That removes transient state such as:

- editor-only classes
- temporary selection markers
- toolbar-related attributes
- pointer-event changes applied only for editing

## Known constraints

- The add-on currently depends on Anki editor internals such as `anki/RichTextInput` for root discovery.
- The legacy internal `wiki-*` names are still present in classes and data attributes for compatibility.
- There is no shipped bulk-conversion workflow yet; the current design focuses on single-field editing.

## JS bridge

The add-on currently uses a narrow bridge from editor JavaScript back to Python for exact-size updates.

Current message shape:

- `wikiEmbed:{"cmd":"exactSize","fieldOrd":0,"embedIndex":1,"width":"75%","height":"600px"}`

If more commands are added later, they should continue to use the same JSON-after-prefix format rather than inventing multiple ad hoc string encodings.

## Current editor flows

### Selected raw URL

1. User selects a raw `http(s)` URL in the field.
2. User chooses `Create Embed from URL`.
3. Python saves the selection range.
4. Python inserts canonical embed HTML at that range.
5. The editor decorates the new embed and shows the toolbar.

### Clicked existing link

1. User right-clicks an existing link in the field.
2. User chooses `Create Embed from URL`.
3. Python finds the matching anchor in the current field HTML.
4. The anchor is replaced with canonical embed HTML.
5. The field is reloaded and the editor decorates the resulting embed.

## Dimension policy

- default size: `100% x 480px`
- minimum practical size in the editor: `320x180`
- freeform width and height within the editor controls
- exact-size dialog accepts percent and pixel values

## Testing strategy

- keep pure HTML conversion logic covered by unit tests
- prefer regression tests for edge-case HTML over broad end-to-end mocks
- rely on manual Anki smoke tests for the editor integration layer
