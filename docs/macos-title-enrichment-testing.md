# Testing macOS title enrichment

## Automated checks

Use the existing project commands:

```sh
make build
make test
make package
dist/aw-watcher-window/aw-watcher-window --help
```

`make test` invokes pytest, including `tests/test_macos_titles.py` on macOS. That
test compiles the **complete production `macos.swift`** with `AW_TITLE_TESTS` and
appends the Swift fixture runner. The flag disables only watcher startup: the
production traversal, AX type conversion, opt-in checks, argument parser, and
privacy filter are exercised directly. No alternative Python implementation of
the extraction algorithm is used. No additional Swift package is required.

The suite runs without installed Claude/Joplin/ChatGPT apps, Accessibility permission,
network access, or a running ActivityWatch server. Missing `swiftc` fails the test
on macOS; other platforms skip it while retaining the Python configuration and
command-forwarding tests. The existing macOS CI job already runs `make test`.

The Swift runner includes synthetic adversarial trees. The JSON fixtures are
minimized, sanitized September 2026 AX captures: Claude document and Code views,
and Joplin's editor. They retain real nesting and relevant roles but replace all
titles, session names, URLs, and note values with invented examples, discarding
message bodies and unrelated attributes. Together they cover document titles;
Code headers; sidebar/message exclusion;
Joplin title fields; duplicate, empty, malformed, ambiguous and localized controls;
short Unicode names; cyclic and wide trees; app identity; native and enriched
title exclusions; and cold-tree recovery. Virtual-clock tests cover the shared
250 ms deadline, per-message timeouts, late responses, failed timeout setup,
incomplete searches, and skipping the cold-tree write after a timeout. The
platform timeout setter is also exercised without querying a live application.
Injected child-count and child-copy responses exercise the production AX reader:
after a positive count, failed, missing, truncated, or malformed child arrays
must stop enrichment rather than let a partial search claim a unique title.
Separate controls cover valid leaves and successful bounded child reads.
ChatGPT uses synthetic document trees based on static inspection of its Electron
app, not live AX captures. Tests cover the exact main-document location, unique
document selection, no descent into web content, unsupported bundles, Unicode,
blank and changing titles, malformed values, incomplete reads, and privacy gates.
Do not commit raw AX dumps: they can include full conversations and note contents.

## Live smoke test

Offline fixtures do not prove that a new app version still exposes the same AX
structure, that notifications arrive, or that an OS build has no resource leaks.
Record macOS version, CPU architecture, watcher commit, app versions, UI language,
permission state, and test date with live results. Compilation with deployment
target 12.0 does not establish runtime compatibility on macOS 12 or an Intel Mac.

Run the candidate beside the normal watcher using a dedicated bucket. After
`make build-swift`, the native helper accepts:

```sh
./aw_watcher_window/aw-watcher-window-macos \
  http://localhost:5600 aw-watcher-window_enrichment_TEST test-host test-client \
  --title-enrichment-app Claude --title-enrichment-app Joplin \
  --title-enrichment-app ChatGPT
```

The candidate needs its own macOS Accessibility grant or an already authorized
development signing identity. Do not replace the installed ActivityWatch bundle
for testing. Keep only the normal watcher writing to the normal bucket. Inspect
the dedicated bucket in Raw Data, then stop the candidate with Ctrl-C.

1. Compare the visible title with recorded events for Claude Chat, Cowork, Code,
   Joplin, and ChatGPT. Switch between two existing views without switching apps; allow
   one 10-second poll. Verify new/unnamed views do not inherit the previous name.
2. Repeat with sidebar open/closed, no document open, search/find controls,
   app restart, and rapid app switching. Unknown/localized layouts should keep
   the native title rather than reporting a control or unrelated document.
3. Use a synthetic title such as `Private test`. Rerun the candidate with
   `--exclude-titles 'Private test'`, then `--exclude-title` and `--research`.
   Verify titles are excluded/dropped before heartbeats reach the test bucket.
4. Exercise permission denied/restored and sleep/wake. Confirm the candidate
   resumes heartbeats without missing intervals beyond sleep/inactivity and
   without duplicate writes by two candidates to the same test bucket.
5. During an extended run, sample candidate **and target app** CPU, RSS, and
   Mach-port counts. Compare with enrichment disabled and record anomalies,
   crashes, generic-title fallbacks, and app updates. A 48–72 hour run is a
   suggested validation period, not an upstream-mandated requirement.

For ChatGPT, verify two titled conversations, a new chat, and an embedded page
with an unrelated title. Record whether the main window exposes an `AXWebArea`
with URL `app://-/index.html` and the active conversation in `AXTitle`. Only the
Electron app with bundle ID `com.openai.codex` is supported. This mapping still
requires live confirmation; tests of synthetic trees cannot establish it.

## Interpreting an update

CI detects regressions against committed fixtures. It does not observe future
Claude/Joplin/ChatGPT releases. Repeat the live smoke test when those apps update and
add a sanitized regression fixture for any changed structure before changing a
selector. Generic titles can also be legitimate, so fallback frequency is a
diagnostic signal, not proof of failure.

An ActivityWatch update can replace binaries manually installed in its `.app`.
Development source and test builds outside that bundle survive. Verify the
running binary and opt-in configuration after an update; passing source tests
cannot establish which binary is installed or running.
