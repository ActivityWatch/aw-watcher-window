# macOS title enrichment validation

## ChatGPT extension (2026-10-05)

The opt-in ChatGPT extractor targets the Electron app with bundle identifier
`com.openai.codex`. Static inspection of the installed app established that its
main renderer loads `app://-/index.html`, conversation views update the document
title, and the native window suppresses page-title updates. The extractor requires
one matching main document and reads only its title; it does not traverse web
document contents. Other bundle identifiers and detached documents fall back.

ChatGPT fixtures are synthetic. Live ChatGPT AX inspection was unavailable in the
validation environment, so no end-to-end ChatGPT capture is claimed. The mapping
from the renderer's document title to `AXWebArea`/`AXTitle`, chat switching, new
chats, and embedded-page isolation still need the manual smoke test described in
[the testing guide](macos-title-enrichment-testing.md). Source inspection and
passing fixtures do not establish that the installed app exposes those fields.

The validation source inspection used application resources only. No private
chat storage, provider API, real chat titles, or proprietary source files are
included in this contribution.

The full automated suite passes: 106 pytest tests, including 209 production
Swift checks, and mypy for 14 source files. Both arm64 and x86_64 compile targeting
macOS 12.0; packaging and packaged `--help` pass. Five deliberate ChatGPT
regressions are caught: disabling extraction, accepting another document origin,
descending into web content, accepting duplicate documents, and accepting a
document whose sibling cannot be identified.

### Independent Electron check (2026-10-06)

A separate, synthetic app running official Electron 42.3.0 / Chromium
148.0.7778.180 was inspected through macOS accessibility on macOS 26.5.1,
Apple Silicon. It loaded `app://-/index.html`, changed `document.title` with
buttons, and suppressed native page-title updates. It used invented content,
an isolated profile, and an unrelated embedded document with its own title.

The accessibility inspection displayed the first and second synthetic titles,
the generic new-chat title, and a Japanese title with an emoji on the main
document. The native window title remained fixed. Clearing the document title
removed the previous label; the inspection tool displayed the document URL
instead. Returning to the first title updated the main document again. The
embedded document appeared separately beneath it.

This verifies title transitions in a real Electron accessibility tree, but not
the production watcher's extraction or heartbeat path. The inspection tool does
not expose raw AX attribute names, so its empty-title URL display does not
establish the value of `AXTitle`. This separate app cannot establish ChatGPT's
live structure, document uniqueness, or embedded-page isolation. The ChatGPT
smoke test remains outstanding; no end-to-end ChatGPT result is claimed.

## Review fixes (2026-10-05)

The follow-up to PR #159 preserves native-title exclusions before enrichment,
requires exactly one Joplin title field after a complete shallow search, and
adds a shared 250 ms enrichment deadline. Each enrichment AX read or cold-tree
write uses a per-object messaging timeout of at most 50 ms, shortened to the
remaining budget and reset afterward. Transport failures, late replies, or
incomplete searches retain the native title. Pre-existing capture paths are
outside this enrichment-specific time budget.

Before the ChatGPT extension, validation passed: 100 pytest tests, including 135 production Swift checks,
and mypy for 14 source files. Both arm64 and x86_64 compile targeting macOS 12.0;
local packaging and packaged `--help` pass. Deliberately removing the native
exclusion guard, accepting duplicate fields, disabling the deadline, increasing
the per-message timeout, or allowing the cold-tree write after timeout each
causes the regression suite to fail.

The next review identified a child-copy failure after a positive child count
that was incorrectly treated as an empty subtree. The new regression reproduced
the wrong Joplin title before the fix. Such failures now stop the lookup; missing,
short, oversized, or malformed child arrays also retain the native title.
Injected responses cover both Joplin and the shared Claude header path, with
controls for valid leaves and successful bounded child reads.

Deadline tests use a virtual clock and injected AX responses; the actual
per-object timeout setter is exercised without querying a live application.
The live observations below apply to the original implementation. They have not
been repeated against this follow-up, and do not establish live timeout behavior
against an unresponsive app.

## Environment

Validation date: 2026-10-04. Tested implementation: `a3aceda3372edc6b5711f72a58f8da73d3761d78`,
based on upstream `23d13b27374761c3c5b77edd38c5aeb5abbfb052`.

- macOS 26.5.1 (25F80), Apple Silicon, Swift 6.3.3, Python 3.13.16.
- Claude 2.19675.0 and Joplin 3.7.21, English UI controls.
- Local ActivityWatch server v0.13.2; dedicated validation bucket.

The live helper compiled the exact production `macos.swift` with `AW_TITLE_TESTS`
and a local wrapper. The wrapper either ran the normal watcher against the test
bucket or reported extraction metadata without printing titles. It was separately
signed and granted Accessibility access; the installed watcher was not replaced.

## Results

| Check | Result |
| --- | --- |
| `make test` | 100 pytest tests pass, including the production Swift regression runner; mypy passes for 14 source files. |
| Build and package | arm64 and x86_64 compile targeting macOS 12.0; local packaging and packaged `--help` pass. Cross-compilation is not an Intel runtime test. |
| Test sensitivity | Removing opt-in gating, accepting an unlabelled note field, or rejecting short header titles each makes the regression runner fail. |
| Current Claude Code | Expected titles from two existing sessions were recorded in the test bucket. This version exposes document titles, so this does not exercise the header fallback live. |
| Current Joplin | An expected note title was recorded. After switching to an existing four-character Japanese title, the live extractor found a four-character title; this background UI switch was not verified in a foreground heartbeat. |
| Live extraction bounds | The probes examined 18 elements in Claude and 31 in Joplin, within the shared 384-element budget. |
| Live privacy options | Separate 12-second runs with regex exclusion, global title exclusion, and Research mode each stored filtered data with no URL. Firefox was foreground for these checks; target-app privacy behavior is covered by the Swift suite. |

The initial live watcher ran for approximately 15 minutes without a crash. At
12 minutes 25 seconds it had accumulated 0.71 seconds of CPU time and 19,952 KiB
RSS. A later sample showed 94 Mach ports and 0.75 seconds of CPU time. These short
observations do not establish the absence of leaks or quantify target-app overhead.
The first heartbeat received a 404 while the new bucket was being created;
subsequent events were recorded successfully. Bucket creation is asynchronous in
the upstream watcher as well.

Only sanitized verification results are included here. Raw accessibility trees,
activity titles, note bodies, URLs, and local server data are not included.

## Remaining checks

- Full GitHub CI matrix (macOS, Windows, Linux with Python 3.9). The existing
  workflow runs on PRs to `master` and pushes to `master`, not feature-branch pushes.
- Current Claude Chat/Cowork and header-fallback behavior; sidebar variations,
  empty documents, and app restart. Offline fixtures cover their supported
  selectors but do not establish current live behavior.
- Sleep/wake and permission revocation/recovery; an extended run comparing
  candidate and target-app CPU, memory, and Mach ports with enrichment disabled.
- Runtime testing on Intel and the minimum supported macOS version.

This evidence supports maintainer review. It does not claim
merge readiness or future compatibility with app updates. Follow
[the testing guide](macos-title-enrichment-testing.md) when repeating live checks.
