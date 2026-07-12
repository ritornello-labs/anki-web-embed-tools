# Plan

## Goal

Keep the add-on focused on one job: converting URLs into embedded web views and making those embeds manageable inside Anki's editors.

## Current scope

Shipped now:

- convert a selected raw URL into an embed
- convert an existing clicked link into an embed
- resize embeds from inline editor controls
- insert blank lines above or below an embed
- support the same controls in the regular note editor and the Browser editor

Not shipped now:

- selected-text Wikipedia search
- Browser-wide bulk conversion

## Next priorities

### 1. Stabilize the working editor flow

- keep context-menu routing reliable across paste, keyboard selection, and clicked-link cases
- add regression tests for real-world edge cases as they appear
- test against a wider range of sites, not just Wikipedia

### 2. Keep the project release-ready

- keep docs aligned with actual shipped behavior
- keep temporary investigation code out of the mainline add-on
- make the repo easy to package and share

### 3. Revisit bulk conversion later

- decide whether bulk conversion is still valuable enough to justify the complexity
- if built, make it previewable and undoable in one step
- keep it separate from the editor-first workflow

## Product guardrails

- stored field HTML should stay simple and portable
- editor controls should not depend on dragging the iframe itself
- editor-only state should be stripped on save
- future bulk actions must integrate cleanly with Anki undo
