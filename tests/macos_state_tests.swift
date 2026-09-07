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
    print("macOS foreground state tests passed")
  }
}
