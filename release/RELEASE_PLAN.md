# Web Embed Tools 0.2.0 release plan

## Before the release

- [x] Make `elvis-sik/anki-web-embed-tools` public.
- [x] Verify `make check`.
- [x] Verify `make smoke` against Anki 25.09.4 in a disposable profile.
- [x] Build and inspect `dist/web_embed_tools.ankiaddon`.

## GitHub release

- [x] Create release `v0.2.0` titled **Web Embed Tools 0.2.0**.
- [x] Attach `dist/web_embed_tools.ankiaddon`.
- [x] Publish concise release notes: selected-URL and clicked-link conversion,
  live resize controls, regular and Browser editor support, and Anki 25.09+
  compatibility.
- [ ] Install the uploaded archive in a disposable Anki profile once more.

## AnkiWeb

- [x] Check the available AnkiWeb upload quota.
- [x] Submit [ankiweb.md](ankiweb.md) as the listing description.
- [x] Add the published AnkiWeb link to the README after the upload succeeds.

## After publishing

- [x] Confirm the public README, license badge, release asset, and GitHub link
  render correctly without a signed-in session.
- [ ] Keep the next feature work separate from `0.2.0`; the initial release is
  deliberately editor-first and does not include Wikipedia search or bulk
  conversion.
