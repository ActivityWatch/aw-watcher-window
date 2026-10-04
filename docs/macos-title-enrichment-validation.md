# macOS title enrichment validation

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

This evidence supports opening a draft for maintainer review. It does not claim
merge readiness or future compatibility with app updates. Follow
[the testing guide](macos-title-enrichment-testing.md) when repeating live checks.
