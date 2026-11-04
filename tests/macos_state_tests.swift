import Foundation

@main
struct MacOSStateTests {
  static func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
      fputs("FAIL: \(message)\n", stderr)
      exit(1)
    }
  }

  static func main() {
    expect(
      foregroundReconciliationAction(trackedPID: 100, observerAvailable: true, candidatePID: 200) == .rebuildObserver,
      "activation/poll PID change must rebuild the observer"
    )
    expect(
      foregroundReconciliationAction(trackedPID: 200, observerAvailable: true, candidatePID: 200) == .refreshWindow,
      "same PID with a live observer must only refresh the focused window"
    )
    expect(
      foregroundReconciliationAction(trackedPID: 200, observerAvailable: false, candidatePID: 200) == .rebuildObserver,
      "a missing observer must be repaired even when the PID is unchanged"
    )
    expect(
      !axCallbackBelongsToForeground(trackedPID: 200, elementPID: 100),
      "a stale AX callback must not overwrite the current foreground app"
    )
    expect(
      axCallbackBelongsToForeground(trackedPID: 200, elementPID: 200),
      "an AX callback for the tracked PID must be accepted"
    )
    expect(
      !axCallbackBelongsToForeground(trackedPID: nil, elementPID: 200),
      "an AX callback must be rejected when no foreground PID is tracked"
    )
    expect(
      !axTitleCallbackBelongsToFocusedWindow(
        hasFocusedWindow: true,
        elementIsFocusedWindow: false
      ),
      "a queued title-change from a previous window of the same PID must be dropped"
    )
    expect(
      axTitleCallbackBelongsToFocusedWindow(
        hasFocusedWindow: true,
        elementIsFocusedWindow: true
      ),
      "a title-change for the focused window must be accepted"
    )
    expect(
      !axTitleCallbackBelongsToFocusedWindow(
        hasFocusedWindow: false,
        elementIsFocusedWindow: false
      ),
      "a title-change must be rejected when no focused window is tracked"
    )
    expect(
      shouldAttemptTitleNotificationRegistration(
        hasObserver: true,
        windowPresent: true,
        windowChanged: true,
        titleNotificationRegistered: false
      ),
      "a new focused window must attempt title-notification registration"
    )
    expect(
      !shouldAttemptTitleNotificationRegistration(
        hasObserver: true,
        windowPresent: true,
        windowChanged: false,
        titleNotificationRegistered: true
      ),
      "an already-registered unchanged window must not re-register"
    )
    expect(
      shouldAttemptTitleNotificationRegistration(
        hasObserver: true,
        windowPresent: true,
        windowChanged: false,
        titleNotificationRegistered: false
      ),
      "a failed title-notification registration must be retried on the next poll"
    )
    expect(
      shouldAttemptTitleNotificationRegistration(
        hasObserver: true,
        windowPresent: false,
        windowChanged: true,
        titleNotificationRegistered: true
      ),
      "clearing the focused window must still run so the previous title notification can be removed"
    )
    expect(
      !shouldAttemptTitleNotificationRegistration(
        hasObserver: false,
        windowPresent: true,
        windowChanged: true,
        titleNotificationRegistered: false
      ),
      "title registration requires a live AX observer"
    )
    expect(
      browserHeartbeatAfterContextFailure(app: "Google Chrome")
        == BrowserFallbackHeartbeat(app: "Google Chrome", title: "", url: nil),
      "Chrome context failure must keep app identity and drop title/URL"
    )
    expect(
      browserHeartbeatAfterContextFailure(app: "Brave Browser").title.isEmpty
        && browserHeartbeatAfterContextFailure(app: "Brave Browser").url == nil,
      "Chrome-equivalent context failure must never emit AX title or URL"
    )
    expect(
      browserHeartbeatAfterContextFailure(app: "Safari")
        == BrowserFallbackHeartbeat(app: "Safari", title: "", url: nil),
      "Safari context failure must keep app identity and drop AX title/URL"
    )
    print("macOS foreground state tests passed")
  }
}
