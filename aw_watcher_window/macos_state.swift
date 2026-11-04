import Foundation

enum ForegroundReconciliationAction: Equatable {
  case rebuildObserver
  case refreshWindow
}

struct BrowserFallbackHeartbeat: Equatable {
  let app: String
  let title: String
  let url: String?
}

func foregroundReconciliationAction(
  trackedPID: pid_t?,
  observerAvailable: Bool,
  candidatePID: pid_t
) -> ForegroundReconciliationAction {
  if trackedPID != candidatePID || !observerAvailable {
    return .rebuildObserver
  }
  return .refreshWindow
}

func axCallbackBelongsToForeground(trackedPID: pid_t?, elementPID: pid_t?) -> Bool {
  guard let trackedPID = trackedPID, let elementPID = elementPID else {
    return false
  }
  return trackedPID == elementPID
}

/// Title-change callbacks are per-window. A queued event from a previous
/// window of the same PID must not overwrite the current focused window.
func axTitleCallbackBelongsToFocusedWindow(
  hasFocusedWindow: Bool,
  elementIsFocusedWindow: Bool
) -> Bool {
  guard hasFocusedWindow else {
    return false
  }
  return elementIsFocusedWindow
}

/// Title-change notifications are registered on the focused window. If that
/// add fails once (window not ready yet), later polls must retry instead of
/// treating the window as already observed.
func shouldAttemptTitleNotificationRegistration(
  hasObserver: Bool,
  windowPresent: Bool,
  windowChanged: Bool,
  titleNotificationRegistered: Bool
) -> Bool {
  guard hasObserver else {
    return false
  }
  if windowChanged {
    return true
  }
  return windowPresent && !titleNotificationRegistered
}

/// Browser ScriptingBridge is URL/title enrichment, and for Chrome the only
/// incognito detector. Safari cannot expose private-browsing state at all.
/// If that lookup fails, keep the app identity so foreground tracking stays
/// coherent, but drop title and URL so a private page cannot leak via AX.
func browserHeartbeatAfterContextFailure(app: String) -> BrowserFallbackHeartbeat {
  return BrowserFallbackHeartbeat(app: app, title: "", url: nil)
}
