<h1 align="center">✨ Web Embed Tools</h1>

<p align="center">Turn a link in an Anki note into a tidy, resizable web view.</p>

<p align="center">
  <a href="https://ankiweb.net/shared/info/1522170627"><img alt="AnkiWeb add-on 1522170627" src="https://img.shields.io/badge/AnkiWeb-1522170627-2f80ed"></a>
  <img alt="Anki 25.09+" src="https://img.shields.io/badge/Anki-25.09%2B-2496ed?logo=anki&logoColor=white">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-3da639"></a>
</p>

Web Embed Tools adds a small editor workflow for placing web pages directly in
Anki note fields. It keeps the stored HTML simple, while the editor provides a
floating toolbar for choosing and resizing an embed.

![Turn a selected URL into a loaded web embed in Anki](https://ritornello.dev/media/ankiweb/2026-07-31-v2/web-embed-tools/preview.gif)

[Browse the full media gallery](https://ritornello.dev/#web-embed-tools).

Version 0.2.1 is prepared for release with a fix for selected-URL insertion in modern Anki editors; the published installer remains 0.2.0 until release.

## Install

Requires Anki 25.09 or newer.

1. Install it from [AnkiWeb](https://ankiweb.net/shared/info/1522170627), or download `web_embed_tools.ankiaddon` from the [latest release](https://github.com/ritornello-labs/anki-web-embed-tools/releases/latest).
2. In Anki, open **Tools → Add-ons → Install from file…** and select it.
3. Restart Anki.

## Use

- Select a raw `http(s)` URL, or right-click an existing link.
- Choose **Create Embed from URL**.
- Select the embed to resize it, set an exact size, add a blank line above or
  below it, or remove it.

The same controls work in the regular Add/Edit dialog and the Browser editor.

## A small privacy and safety note

An embedded URL is stored in your note HTML and therefore may sync with the
collection. The external page loads when its card or editor is displayed, so
embed only sites you trust. Some sites intentionally block iframe embedding;
that is expected and cannot be changed by this add-on.

## What is included

- Selected-URL and clicked-link conversion.
- Live editor embeds with practical resize controls.
- Canonical, portable field HTML that preserves the chosen size.
- A disposable Anki GUI smoke test for the editor hook.

Wikipedia search and Browser-wide bulk conversion are not part of this release.

## Development

Only needed when working on the add-on itself:

```bash
make check
make package
make smoke
```

`make smoke` uses [anki-addon-workbench](https://github.com/ritornello-labs/anki-addon-workbench)
and a disposable profile; it never opens your everyday Anki collection.

The supporting design notes live in [PLAN.md](PLAN.md),
[TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md), and [BACKLOG.md](BACKLOG.md).

## License

MIT. See [LICENSE](LICENSE).

Support continued development: [ritornello.dev/support](https://ritornello.dev/support).
