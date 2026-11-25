"""Guard privacy and delivery wiring that must survive the Swift refactor.

The native helper is compiled and its state tests run on macOS CI. These
source-level checks also run on Linux, where Cocoa is unavailable.
"""

import re
from pathlib import Path


SOURCE = (Path(__file__).parents[1] / "aw_watcher_window" / "macos.swift").read_text()


def test_app_exclusion_precedes_context_and_heartbeat_delivery():
    emit = SOURCE.split("  func emitHeartbeat(", 1)[1].split("  deinit", 1)[0]
    exclusion = emit.index("if appShouldBeExcluded(applicationName)")
    drop = emit.index("heartbeatSender.dropForExclusion()", exclusion)
    early_return = emit.index("return", drop)
    assert exclusion < drop < early_return < emit.index("AXUIElementCopyAttributeValue")
    assert early_return < emit.index("SBApplication.init")
    assert early_return < emit.index("sendHeartbeat(Heartbeat(")


def test_heartbeat_delivery_still_uses_master_queue():
    send = SOURCE.split("func sendHeartbeat(_ heartbeat: Heartbeat)", 1)[1]
    send = send.split("func sendHeartbeatSingle", 1)[0]
    assert "heartbeatSender.enqueue(heartbeat)" in send
    assert "final class HeartbeatSender" in SOURCE
    assert "var oldHeartbeat" not in SOURCE
    assert "try await createBucket()" in SOURCE


def _emit_heartbeat_source():
    return SOURCE.split("  func emitHeartbeat(", 1)[1].split("  deinit", 1)[0]


def test_zoom_lookup_runs_after_app_exclusion():
    emit = _emit_heartbeat_source()
    early_return = emit.index("return", emit.index("heartbeatSender.dropForExclusion()"))
    assert early_return < emit.index("zoomMeetingTopic(window:")


def test_zoom_lookup_skipped_when_titles_are_discarded():
    emit = _emit_heartbeat_source()
    branch = emit.index("ZOOM_BUNDLE_IDS.contains(application.bundleIdentifier")
    guard_end = emit.index("{", branch)
    condition = emit[branch:guard_end]
    assert "!researchEnabled" in condition and "!excludeTitle" in condition


def test_title_exclusion_also_checks_original_zoom_title():
    emit = _emit_heartbeat_source()
    filt = emit[emit.index("if researchEnabled {"):]
    # a rule matching either title must redact (contains, not allSatisfy)
    assert ".contains(where: titleShouldBeExcluded)" in filt
    # the original title must actually reach the check, and must be captured
    # in the Zoom branch before the topic replaces it
    assert "originalTitle: originalTitle)" in filt
    branch = emit[emit.index("ZOOM_BUNDLE_IDS.contains(application.bundleIdentifier"):emit.index("if researchEnabled {")]
    assert branch.index("originalTitle = windowTitle") < branch.index("data.title = ")


def test_zoom_lookup_checks_window_before_children_and_searches_from_end():
    helper = SOURCE.split("func zoomMeetingTopic(window: AXUIElement)", 1)[1]
    helper = helper.split("\n  }\n", 1)[0]
    assert helper.index("isZoomMeetingWindow(") < helper.index("kAXChildrenAttribute")
    # participant tiles come first and the topic button near the end, so
    # search from the end; only direct children, never the deeper tree
    assert "children.reversed()" in helper
    assert "ZOOM_CHILD_LIMIT" not in SOURCE
    assert "kAXDescriptionAttribute" in helper
    # never log the raw topic: no log call at all, and the debug line may only
    # say whether a topic was found
    assert "log(" not in helper and "print(" not in helper
    interpolations = re.findall(r"\\\(([^)]*)\)", helper)
    assert interpolations
    for expression in interpolations:
        if "topic" in expression or "description" in expression.lower():
            assert expression == "topic != nil"


def test_no_cached_zoom_topic():
    assert "var lastZoom" not in SOURCE and "var zoomTopic" not in SOURCE


def test_zoom_matched_by_bundle_id_not_localized_name():
    # Zoom's localizedName is "Zoom" (bundle name "zoom.us"); the bundle
    # identifier is the stable way to recognise it
    assert 'ZOOM_BUNDLE_IDS = ["us.zoom.xos"]' in SOURCE
    assert "ZOOM_APPS" not in SOURCE


def test_zoom_branch_does_not_log_the_topic():
    # the topic has not been through the exclusion rules inside the branch
    emit = _emit_heartbeat_source()
    branch = emit[emit.index("ZOOM_BUNDLE_IDS.contains(application.bundleIdentifier"):emit.index("if researchEnabled {")]
    for call in ("debug(", "log(", "print("):
        assert call not in branch
