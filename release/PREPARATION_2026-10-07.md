# Listing preparation — 2026-10-07

Status: prepared for review; **awaiting explicit image/copy approval**. No AnkiWeb submission or public media upload in this pass.

The complete local review hub and native capture sources are recorded in the private workspace publication queue. GIFs use actual Anki 25.09 workbench captures from disposable profiles. Similar question/answer demos hold the question for two seconds and answer for three; interactive demos allow time for actions and feedback.

Every listing includes the Ritornello banner, gallery invitation, stable support page, and the public GitHub URL where a dedicated public repository exists. Videos are absent.

## Exact proposed listings

### Web Embed Tools

- Listing: `release/ankiweb.md`
- Copy SHA-256: `76bbb2727158d6622928037d8fa514bb9fcfd91bf87b13c7259b02be7cfab8a0`
- Candidate SHA-256: `8f3b7633f0d8ac2eaa3120575e7b04ba2a7883750bce6a512f0ce6360b27a94d`
- Approval: awaiting approval

- GIF `web-embed-tools/create.gif`: `82efdd02e5f3f2e4ba158851b48d6ffc03bd71329e9b2b9e0df8148f43d64c30`
- GIF `web-embed-tools/resize.gif`: `7c12f5af125c2d4118b10c695729f900ff201dec6afaab5c1f44fb48df7883f2`

## Upload procedure

1. Record explicit approval against these exact copy and image hashes. Any subsequent visible change requires fresh review.
2. Verify the current quota and exact original share/deck name. Open only the isolated Publisher when an export/import is needed; never operate the personal profile.
3. Wait for Elvis if 1Password or account authentication requires interaction. The scheduled reminder only pings him; it never publishes automatically.
4. Publish through `anki-addon-release`; owner-verify the listing and download its delivered artifact.
5. Attach the exact submitted/delivered bytes to a tagged GitHub release, verify its digest, and update the website gallery/release links and workspace queue.

For add-ons installed directly from GitHub release files, release notes must explain that they do not auto-update; AnkiWeb installs do.

## Verification

29 unit checks passed (one environment-dependent skip). The native regression verifies selected URLs become one serialized iframe in the note field. Separate recorded interactions use the real context menu and six width/height toolbar clicks; every step keeps the whole iframe visible with no outer field overflow. Manifest/archive and exact-byte publication checks passed.

## October 8 revised motion batch and insertion fix

Version 0.2.1 replaces the rejected static resize example with two native recordings: URL typing and the real Create Embed from URL menu action; four width reductions and two height reductions with the entire iframe and editor field visible throughout. A taller editor prevents outer clipping. Captures use a disposable unsaved note, with no personal collection or Publisher access. The selected-URL recording exposed a shadow-root selection bug; insertion now replaces the URL inside Anki's editable content and notifies the editor to serialize the embed. The 0.2.1 candidate includes that fix. Exact copy, both GIFs, and the changed candidate require fresh approval. No public upload or AnkiWeb submission.
