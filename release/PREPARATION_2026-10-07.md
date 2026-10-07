# Listing preparation — 2026-10-07

Status: prepared for review; **awaiting explicit image/copy approval**. No AnkiWeb submission or public media upload in this pass.

The complete local review hub and native capture sources are recorded in the private workspace publication queue. GIFs use actual Anki 25.09 workbench captures from disposable profiles. Similar question/answer demos hold the question for two seconds and answer for three; interactive demos allow time for actions and feedback.

Every listing includes the Ritornello banner, gallery invitation, stable support page, and the public GitHub URL where a dedicated public repository exists. Videos are absent.

## Exact proposed listings

### Web Embed Tools

- Listing: `release/ankiweb.md`
- Copy SHA-256: `ea3d9ab7090b56c79411b9b6d08d37472add97a3098235d147573c758807cde4`
- Candidate SHA-256: `2d53136b7af1844a0656609033d5c398f11511be83680e5895610917fb7c587b`
- Approval: awaiting approval
- GIF `web-embed-tools/resize.gif`: `7b82b8d51cd2619b76b9c2e87b8077674ffdafad748ceb2a3d7fad6e70ccef68`

## Upload procedure

1. Record explicit approval against these exact copy and image hashes. Any subsequent visible change requires fresh review.
2. Verify the current quota and exact original share/deck name. Open only the isolated Publisher when an export/import is needed; never operate the personal profile.
3. Wait for Elvis if 1Password or account authentication requires interaction. The scheduled reminder only pings him; it never publishes automatically.
4. Publish through `anki-addon-release`; owner-verify the listing and download its delivered artifact.
5. Attach the exact submitted/delivered bytes to a tagged GitHub release, verify its digest, and update the website gallery/release links and workspace queue.

For add-ons installed directly from GitHub release files, release notes must explain that they do not auto-update; AnkiWeb installs do.

## Verification

29 tests passed (one environment-dependent skip). Native workbench opened a real Add Cards editor, loaded Wikipedia and used its width toolbar. Manifest/archive checks passed.
