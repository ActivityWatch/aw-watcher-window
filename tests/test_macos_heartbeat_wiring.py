"""Guard privacy and delivery wiring that must survive the Swift refactor.

The native helper is compiled and its state tests run on macOS CI. These
source-level checks also run on Linux, where Cocoa is unavailable.
"""

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
