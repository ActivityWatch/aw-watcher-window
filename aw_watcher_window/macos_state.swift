import Foundation

enum ForegroundReconciliationAction: Equatable {
  case rebuildObserver
  case refreshWindow
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
