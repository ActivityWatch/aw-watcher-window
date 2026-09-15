import Foundation

enum ForegroundReconciliationAction: Equatable {
  case rebuildObserver
  case refreshWindow
}

struct ChromeFallbackHeartbeat: Equatable {
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

/// Chrome ScriptingBridge is both URL enrichment and the only incognito detector.
/// If that lookup fails, keep the app identity so foreground tracking stays
/// coherent, but drop title and URL so an incognito page cannot leak via AX.
func chromeHeartbeatAfterContextFailure(app: String) -> ChromeFallbackHeartbeat {
  return ChromeFallbackHeartbeat(app: app, title: "", url: nil)
}
