import Cocoa
import ScriptingBridge

@objc protocol ChromeTab {
  @objc optional var URL: String { get }
  @objc optional var title: String { get }
}

@objc protocol ChromeWindow {
  @objc optional var activeTab: ChromeTab { get }
  @objc optional var mode: String { get }
}

extension SBObject: ChromeWindow, ChromeTab {}

@objc protocol ChromeProtocol {
  @objc optional func windows() -> [ChromeWindow]
}

extension SBApplication: ChromeProtocol {}

// https://github.com/tingraldi/SwiftScripting/blob/4346eba0f47e806943601f5fb2fe978e2066b310/Frameworks/SafariScripting/SafariScripting/Safari.swift#L37

@objc public protocol SafariDocument {
    @objc optional var name: String { get } // Its name.
    @objc optional var modified: Bool { get } // Has it been modified since the last save?
    @objc optional var file: URL { get } // Its location on disk, if it has one.
    @objc optional var source: String { get } // The HTML source of the web page currently loaded in the document.
    @objc optional var URL: String { get } // The current URL of the document.
    @objc optional var text: String { get } // The text of the web page currently loaded in the document. Modifications to text aren't reflected on the web page.
    @objc optional func setURL(_ URL: String!) // The current URL of the document.
}

@objc public protocol SafariTab {
    @objc optional var source: String { get } // The HTML source of the web page currently loaded in the tab.
    @objc optional var URL: String { get } // The current URL of the tab.
    @objc optional var index: NSNumber { get } // The index of the tab, ordered left to right.
    @objc optional var text: String { get } // The text of the web page currently loaded in the tab. Modifications to text aren't reflected on the web page.
    @objc optional var visible: Bool { get } // Whether the tab is currently visible.
    @objc optional var name: String { get } // The name of the tab.
    @objc optional func setURL(_ URL: String!) // The current URL of the tab.
}

@objc public protocol SafariWindow {
    @objc optional var name: String { get } // The title of the window.
    @objc optional func id() -> Int // The unique identifier of the window.
    @objc optional var index: Int { get } // The index of the window, ordered front to back.
    @objc optional var document: SafariDocument { get } // The document whose contents are displayed in the window.
    @objc optional func tabs() -> SBElementArray
    @objc optional var currentTab: SafariTab { get } // The current tab.
}
extension SBObject: SafariWindow {}

@objc public protocol SafariApplication {
    @objc optional func documents() -> SBElementArray
    @objc optional func windows() -> [SafariWindow]
    @objc optional var name: String { get } // The name of the application.
    @objc optional var frontmost: Bool { get } // Is this the active application?
}
extension SBApplication: SafariApplication {}

// AW-specific structs

struct NetworkMessage: Codable, Equatable {
  var app: String
  var title: String?
  var url: String?
}

struct Heartbeat: Codable {
  var timestamp: Date
  var data: NetworkMessage
}

enum HeartbeatError: Error {
  case error(msg: String)
}

struct Bucket: Codable {
  var client: String
  var type: String
  var hostname: String
}

// there's no builtin logging library on macos which has levels & hits stdout, so we build our own simple one
// there a complex open source one, but it makes it harder to compile this simple one-file swift application
let dateFormatter =  DateFormatter();

func logTimestamp() -> String {
  let now = Date()
  dateFormatter.timeZone = TimeZone.current
  dateFormatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
  return dateFormatter.string(from: now)
}

// generate log prefix based on level
func logPrefix(_ level: String) -> String {
  return "\(logTimestamp()) [aw-watcher-window-macos] [\(level)]"
}

let logLevel = ProcessInfo.processInfo.environment["LOG_LEVEL"]?.uppercased() ?? "INFO"

func debug(_ msg: String) {
  if (logLevel == "DEBUG") {
    print("\(logPrefix("DEBUG")) \(msg)")
    fflush(stdout)
  }
}

func log(_ msg: String) {
  print("\(logPrefix("INFO")) \(msg)")
  fflush(stdout)
}

func error(_ msg: String) {
  print("\(logPrefix("ERROR")) \(msg)")
  fflush(stdout)
}

// Placeholder values, set in start() from CLI arguments
var baseurl = "http://localhost:5600"
// NOTE: this differs from the hostname we get from Python, here we get `.local`, but in Python we get `.localdomain`
var clientHostname = ProcessInfo.processInfo.hostName
var clientName = "aw-watcher-window"
var bucketName = "\(clientName)_\(clientHostname)"
var excludeTitle = false
var excludeTitlePatterns: [NSRegularExpression] = []
var researchEnabled = false
var researchCategoryMap: [(pattern: String, category: String)] = []
var researchAppCategoryMap: [(app: String, category: String)] = []

let researchBrowserApps = Set([
  "chrome",
  "google chrome",
  "google chrome canary",
  "google-chrome",
  "google-chrome-beta",
  "google-chrome-unstable",
  "chromium",
  "chromium-browser",
  "brave browser",
  "brave",
  "brave-browser",
  "firefox",
  "firefox developer edition",
  "firefox-esr",
  "safari",
  "edge",
  "microsoft edge",
  "microsoft-edge",
  "microsoft-edge-beta",
  "microsoft-edge-dev",
  "opera",
  "chrome.exe",
  "brave.exe",
  "firefox.exe",
  "msedge.exe",
  "opera.exe",
])

let main = MainThing()
var oldHeartbeat: Heartbeat?

let formatter: ISO8601DateFormatter = {
  let formatter = ISO8601DateFormatter()
  formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
  return formatter
}()

let encoder: JSONEncoder = {
  let encoder = JSONEncoder()
  encoder.dateEncodingStrategy = .custom({ date, encoder in
    var container = encoder.singleValueContainer()
    let dateString = formatter.string(from: date)
    try container.encode(dateString)
  })
  return encoder
}()

@main
struct ActivityWatchMacOSWatcher {
  static func main() {
    start()
    RunLoop.main.run()
  }
}

func compileExcludeTitlePattern(_ pattern: String) -> NSRegularExpression {
  do {
    return try NSRegularExpression(pattern: pattern, options: [.caseInsensitive])
  } catch let regexError {
    error("Invalid regex pattern: \(pattern) — \(regexError.localizedDescription)")
    exit(1)
  }
}

func parseOptionalArguments(_ arguments: ArraySlice<String>) {
  var index = arguments.startIndex
  while index < arguments.endIndex {
    let argument = arguments[index]

    if argument == "--exclude-title" {
      excludeTitle = true
      index = arguments.index(after: index)
      continue
    }

    if argument == "--exclude-titles" {
      let nextIndex = arguments.index(after: index)
      guard nextIndex < arguments.endIndex else {
        error("Missing value for --exclude-titles")
        exit(1)
      }
      excludeTitlePatterns.append(compileExcludeTitlePattern(arguments[nextIndex]))
      index = arguments.index(after: nextIndex)
      continue
    }

    if argument == "--research" {
      researchEnabled = true
      index = arguments.index(after: index)
      continue
    }

    if argument == "--research-category" {
      let patternIndex = arguments.index(after: index)
      let categoryIndex = patternIndex < arguments.endIndex ? arguments.index(after: patternIndex) : arguments.endIndex
      guard patternIndex < arguments.endIndex, categoryIndex < arguments.endIndex else {
        error("Missing pattern/category values for --research-category")
        exit(1)
      }
      researchCategoryMap.append((pattern: arguments[patternIndex], category: arguments[categoryIndex]))
      index = arguments.index(after: categoryIndex)
      continue
    }

    if argument == "--research-app-category" {
      let appIndex = arguments.index(after: index)
      let categoryIndex = appIndex < arguments.endIndex ? arguments.index(after: appIndex) : arguments.endIndex
      guard appIndex < arguments.endIndex, categoryIndex < arguments.endIndex else {
        error("Missing app/category values for --research-app-category")
        exit(1)
      }
      researchAppCategoryMap.append((app: arguments[appIndex], category: arguments[categoryIndex]))
      index = arguments.index(after: categoryIndex)
      continue
    }

    error("Unknown argument: \(argument)")
    exit(1)
  }
}

func titleShouldBeExcluded(_ title: String) -> Bool {
  let range = NSRange(title.startIndex..<title.endIndex, in: title)
  return excludeTitlePatterns.contains { pattern in
    pattern.firstMatch(in: title, options: [], range: range) != nil
  }
}

func isResearchBrowser(_ app: String) -> Bool {
  return researchBrowserApps.contains(app.trimmingCharacters(in: .whitespacesAndNewlines).lowercased())
}

func classifyResearch(_ title: String, url: String?) -> String {
  // Try URL first — more reliable than page title, which can change mid-load
  if let url = url, !url.isEmpty {
    for item in researchCategoryMap {
      if url.range(of: item.pattern, options: [.caseInsensitive]) != nil {
        return item.category
      }
    }
  }
  for item in researchCategoryMap {
    if title.range(of: item.pattern, options: [.caseInsensitive]) != nil {
      return item.category
    }
  }
  return "excluded"
}

func classifyApp(_ app: String) -> String {
  // Case-insensitive exact lookup of app name in the app category map.
  // Returns the mapped category, or "Excluded" when the app is not in the map.
  // Both sides are trimmed and lowercased so a configured key carrying stray
  // whitespace matches identically here and in the Python path
  // (research_filter.classify_app). Without trimming the configured key, a map
  // entry like " Microsoft Outlook" would classify on Linux/Windows but fall
  // through to "Excluded" on the macOS Swift path for the same config.
  let appLower = app.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
  for item in researchAppCategoryMap {
    if item.app.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == appLower {
      return item.category
    }
  }
  return "Excluded"
}

func applyResearchFilter(_ data: NetworkMessage) -> NetworkMessage {
  if !researchEnabled {
    return data
  }

  if isResearchBrowser(data.app) {
    return NetworkMessage(app: data.app, title: classifyResearch(data.title ?? "", url: data.url), url: nil)
  }

  // Non-browser: map app to study category when a map is provided;
  // otherwise keep app name and drop title (legacy behaviour).
  if researchAppCategoryMap.isEmpty {
    return NetworkMessage(app: data.app, title: nil, url: nil)
  }
  // Replace the raw app identity with its category — the app name is the
  // sensitive identifier for non-browser apps, so it must not be retained.
  return NetworkMessage(app: classifyApp(data.app), title: nil, url: nil)
}

func start() {
  // Arguments should be:
  //  - url + port
  //  - bucket_id
  //  - hostname
  //  - client_id
  let arguments = CommandLine.arguments

  // Check that we get the 4 required arguments plus any optional flags
  if arguments.count < 5 {
    print("Usage: aw-watcher-window <url> <bucket> <hostname> <client> [--exclude-title] [--exclude-titles <pattern> ...] [--research] [--research-category <pattern> <category> ...] [--research-app-category <app_name> <category> ...]")
    exit(1)
  }

  baseurl = arguments[1]
  bucketName = arguments[2]
  clientHostname = arguments[3]
  clientName = arguments[4]
  parseOptionalArguments(arguments.dropFirst(5))

  guard checkAccess() else {
    DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
      start()
    }
    return
  }

  createBucket()

  // listen for changes in focused application
  NSWorkspace.shared.notificationCenter.addObserver(
    main,
    selector: #selector(main.focusedAppChanged(_:)),
    name: NSWorkspace.didActivateApplicationNotification,
    object: nil
  )

  main.reconcileCurrentForegroundApp(source: "startup")

  // Start the polling timer
  main.pollingTimer = Timer.scheduledTimer(timeInterval: 10.0, target: main, selector: #selector(main.pollActiveWindow), userInfo: nil, repeats: true)
}

// TODO might be better to have the python wrapper create this before launching the swift application
func createBucket() {
  let payload = try! encoder.encode(
    Bucket(client: clientName, type: "currentwindow", hostname: clientHostname))

  let url = URL(string: "\(baseurl)/api/0/buckets/\(bucketName)")!
  Task {
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
    let (_, response) = try await URLSession.shared.upload(for: urlRequest, from: payload)
    guard (200...299).contains((response as! HTTPURLResponse).statusCode) else {
      log("Failed to create bucket")
      return
    }
  }
}

func sendHeartbeat(_ heartbeat: Heartbeat) {
  let oldPayloadDifferent = oldHeartbeat != nil && oldHeartbeat!.data != heartbeat.data
  let timeSinceLastHeartbeat = oldHeartbeat != nil ? heartbeat.timestamp.timeIntervalSince(oldHeartbeat!.timestamp) : -1.0

  // if you resize a window a ton of events (subsecond) will be fired
  // we enforce a 1s minimum gap between events to avoid this
  if timeSinceLastHeartbeat != -1.0 && timeSinceLastHeartbeat <= 0.5 {
    debug("skipping heartbeat, last heartbeat was sent 1s ago")
    return
  }

  // TODO running these async could cause weird state issues since the observer stuff can send a log of heartbeats
  //      in a short time under certain circumstances, and we don't want to send them all
  Task {
    if oldPayloadDifferent {
      debug("sending old heartbeat for merging")

      do {
        // unlike the python aw-client library, we do not enforce a `commit_interval` and instead send the old event (which is not invalid)
        // at the current time with a pulse value equal to the time since this event was originally sent. The aw-server will then merge
        // this new event with the original event, extending the recorded time spent on this particular window/application.

        let refreshedOldHeartbeat = Heartbeat(
          // it is important to refresh the hearbeat using the timestamp where the user stopped working on the previous application
          // more info: https://github.com/ActivityWatch/aw-watcher-window/pull/69
          // we don't *think* this millisecond subtraction is necessary, but it may be:
          // https://github.com/ActivityWatch/aw-watcher-window/pull/69#discussion_r987064282
          timestamp: heartbeat.timestamp - 0.001,
          data: oldHeartbeat!.data
        )

        try await sendHeartbeatSingle(refreshedOldHeartbeat, pulsetime: timeSinceLastHeartbeat + 1)
      } catch {
        log("Failed to send old heartbeat: \(error)")
        return
      }
    }

    do {
      let since_last_seconds = oldHeartbeat != nil ? heartbeat.timestamp.timeIntervalSince(oldHeartbeat!.timestamp) : 0
      try await sendHeartbeatSingle(heartbeat, pulsetime: since_last_seconds + 1)
    } catch {
      log("Failed to send heartbeat: \(error)")
      return
    }

    oldHeartbeat = heartbeat
  }
}

func sendHeartbeatSingle(_ heartbeat: Heartbeat, pulsetime: Double) async throws {
  let url = URL(string: "\(baseurl)/api/0/buckets/\(bucketName)/heartbeat?pulsetime=\(pulsetime)")!

  var urlRequest = URLRequest(url: url)
  urlRequest.httpMethod = "POST"
  urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")

  let payload = try! encoder.encode(heartbeat)
  let (_, response) = try await URLSession.shared.upload(for: urlRequest, from: payload)

  guard (200...299).contains((response as! HTTPURLResponse).statusCode) else {
    throw HeartbeatError.error(msg: "Failed to send heartbeat: \(response)")
  }

  debug("[heartbeat] bucket: \(bucketName), timestamp: \(heartbeat.timestamp), pulsetime: \(round(pulsetime * 10) / 10), app: \(heartbeat.data.app), title: \(heartbeat.data.title ?? ""), url: \(heartbeat.data.url ?? "")")
}

class MainThing {
  var observer: AXObserver?
  var foregroundApplication: NSRunningApplication?
  var oldWindow: AXUIElement?
  var pollingTimer: Timer?

  var trackedPID: pid_t? {
    return foregroundApplication?.processIdentifier
  }

  // list of chrome equivalent browsers
  let CHROME_BROWSERS = [
    "Google Chrome",
    "Google Chrome Canary",
    "Chromium",
    "Brave Browser",
  ]

  // Gecko-based browsers have no scripting interface for tabs, but expose the
  // current page URL on their accessibility tree's AXWebArea node
  let FIREFOX_BROWSERS = [
    "Firefox",
    "Firefox Developer Edition",
    "Firefox Nightly",
    "Zen",
    "Zen Browser",
    "LibreWolf",
    "Waterfox",
    "Floorp",
  ]

  // upper bound on accessibility elements examined per lookup, so a
  // pathological tree can't stall the watcher (the web area is typically
  // found within a few dozen elements)
  let AX_TRAVERSAL_LIMIT = 384

  // Search the window's accessibility tree breadth-first for an AXWebArea node
  // and return its AXURL, the URL of the loaded page. The top-level document's
  // web area sits shallow in Gecko's tree and is reached before any web areas
  // of nested iframes, so the first hit is the current page.
  // (there is no kAXWebAreaRole constant in HIServices; the role string is
  // defined by the browsers themselves)
  func geckoURL(window: AXUIElement) -> String? {
    var queue: [AXUIElement] = [window]
    var index = 0
    while index < queue.count && index < AX_TRAVERSAL_LIMIT {
      let element = queue[index]
      index += 1

      var roleRef: AnyObject?
      AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleRef)
      if roleRef as? String == "AXWebArea" {
        var urlRef: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXURLAttribute as CFString, &urlRef)
        if let url = urlRef as? NSURL {
          return url.absoluteString
        }
        // no URL on the web area (e.g. page still loading); stop rather than
        // keep searching, since a deeper hit would be an iframe's web area
        return urlRef as? String
      }

      var childrenRef: AnyObject?
      AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &childrenRef)
      if let children = childrenRef as? [AXUIElement] {
        queue.append(contentsOf: children)
      }
    }
    return nil
  }

  func elementPID(_ element: AXUIElement) -> pid_t? {
    var pid: pid_t = 0
    return AXUIElementGetPid(element, &pid) == .success ? pid : nil
  }

  @objc func pollActiveWindow() {
    reconcileCurrentForegroundApp(source: "poll")
  }

  @objc func focusedAppChanged(_ notification: Notification) {
    let notificationApplication = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication
    if let application = notificationApplication, !application.isTerminated {
      reconcileForegroundApp(application: application, source: "activation")
    } else {
      log("Activation notification lacked a live application; falling back to current foreground app")
      reconcileCurrentForegroundApp(source: "activation-fallback")
    }
  }

  func reconcileCurrentForegroundApp(source: String) {
    guard let application = NSWorkspace.shared.frontmostApplication, !application.isTerminated else {
      log("Failed to get a live foreground application from \(source)")
      return
    }
    reconcileForegroundApp(application: application, source: source)
  }

  func reconcileForegroundApp(application: NSRunningApplication, source: String) {
    let pid = application.processIdentifier
    let action = foregroundReconciliationAction(
      trackedPID: trackedPID,
      observerAvailable: observer != nil,
      candidatePID: pid
    )

    if action == .rebuildObserver {
      debug("Rebuilding AX observer for pid \(pid) from \(source)")
      rebuildObserver(for: application)
    } else {
      foregroundApplication = application
    }

    refreshFocusedWindow(for: application)
  }

  func tearDownObserver() {
    if let observer = observer {
      if let oldWindow = oldWindow {
        AXObserverRemoveNotification(observer, oldWindow, kAXTitleChangedNotification as CFString)
      }
      CFRunLoopRemoveSource(
        RunLoop.current.getCFRunLoop(),
        AXObserverGetRunLoopSource(observer),
        CFRunLoopMode.defaultMode
      )
    }
    observer = nil
    oldWindow = nil
  }

  func rebuildObserver(for application: NSRunningApplication) {
    tearDownObserver()
    foregroundApplication = application

    let pid = application.processIdentifier
    let focusedApp = AXUIElementCreateApplication(pid)
    var newObserver: AXObserver?
    let createResult = AXObserverCreate(
      pid,
      {
        (
          axObserver: AXObserver,
          axElement: AXUIElement,
          notification: CFString,
          userData: UnsafeMutableRawPointer?
        ) -> Void in
        guard let userData = userData else {
          log("Missing AX observer userData")
          return
        }
        let watcher = Unmanaged<MainThing>.fromOpaque(userData).takeUnretainedValue()
        watcher.handleAXNotification(
          observer: axObserver,
          element: axElement,
          notification: notification
        )
      },
      &newObserver
    )

    guard createResult == .success, let newObserver = newObserver else {
      log("Failed to create AX observer for pid \(pid): \(createResult.rawValue)")
      return
    }

    let selfPtr = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())
    let addResult = AXObserverAddNotification(
      newObserver,
      focusedApp,
      kAXFocusedWindowChangedNotification as CFString,
      selfPtr
    )
    guard addResult == .success || addResult == .notificationAlreadyRegistered else {
      log("Failed to observe focused-window changes for pid \(pid): \(addResult.rawValue)")
      return
    }

    observer = newObserver
    CFRunLoopAddSource(
      RunLoop.current.getCFRunLoop(),
      AXObserverGetRunLoopSource(newObserver),
      CFRunLoopMode.defaultMode
    )
  }

  func refreshFocusedWindow(for application: NSRunningApplication) {
    guard trackedPID == application.processIdentifier else {
      debug("Ignoring focused-window refresh for stale pid \(application.processIdentifier)")
      return
    }

    let focusedApp = AXUIElementCreateApplication(application.processIdentifier)
    var focusedWindowValue: AnyObject?
    let result = AXUIElementCopyAttributeValue(
      focusedApp,
      kAXFocusedWindowAttribute as CFString,
      &focusedWindowValue
    )
    var focusedWindow: AXUIElement?
    if result == .success, let focusedWindowValue = focusedWindowValue {
      focusedWindow = (focusedWindowValue as! AXUIElement)
    }
    updateFocusedWindow(focusedWindow, for: application)
  }

  func updateFocusedWindow(_ window: AXUIElement?, for application: NSRunningApplication) {
    guard trackedPID == application.processIdentifier else {
      debug("Ignoring focused-window update for stale pid \(application.processIdentifier)")
      return
    }

    var windowChanged = oldWindow == nil || window == nil
    if let oldWindow = oldWindow, let window = window {
      windowChanged = !CFEqual(oldWindow, window)
    } else if oldWindow == nil && window == nil {
      windowChanged = false
    }

    if windowChanged, let observer = observer {
      if let oldWindow = oldWindow {
        AXObserverRemoveNotification(observer, oldWindow, kAXTitleChangedNotification as CFString)
      }
      if let window = window {
        let selfPtr = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())
        let addResult = AXObserverAddNotification(
          observer,
          window,
          kAXTitleChangedNotification as CFString,
          selfPtr
        )
        if addResult != .success && addResult != .notificationAlreadyRegistered {
          log("Failed to observe title changes for pid \(application.processIdentifier): \(addResult.rawValue)")
        }
      }
    }

    oldWindow = window
    emitHeartbeat(application: application, window: window)
  }

  func handleAXNotification(
    observer callbackObserver: AXObserver,
    element: AXUIElement,
    notification: CFString
  ) {
    guard let application = foregroundApplication,
          let currentObserver = observer,
          CFEqual(callbackObserver, currentObserver),
          axCallbackBelongsToForeground(trackedPID: trackedPID, elementPID: elementPID(element)) else {
      debug("Ignoring stale AX callback")
      return
    }

    if notification == kAXFocusedWindowChangedNotification as CFString {
      refreshFocusedWindow(for: application)
    } else if notification == kAXTitleChangedNotification as CFString {
      emitHeartbeat(application: application, window: element)
    }
  }

  func emitHeartbeat(application: NSRunningApplication, window: AXUIElement?) {
    guard trackedPID == application.processIdentifier else {
      debug("Ignoring heartbeat for stale pid \(application.processIdentifier)")
      return
    }

    // Calculate now before optional browser scripting, which may take time.
    let nowTime = Date.now
    var windowTitle: AnyObject?
    if let window = window {
      AXUIElementCopyAttributeValue(window, kAXTitleAttribute as CFString, &windowTitle)
    }

    let applicationName = application.localizedName ?? application.bundleIdentifier ?? ""
    var data = NetworkMessage(app: applicationName, title: windowTitle as? String ?? "")

    if CHROME_BROWSERS.contains(applicationName) {
      debug("Chrome browser detected, extracting URL and title")
      if let bundleIdentifier = application.bundleIdentifier,
         let chromeObject: ChromeProtocol = SBApplication.init(bundleIdentifier: bundleIdentifier),
         let windows = chromeObject.windows,
         let frontWindow = windows().first,
         let activeTab = frontWindow.activeTab {
        if frontWindow.mode == "incognito" {
          data = NetworkMessage(app: "", title: "")
        } else {
          data.url = activeTab.URL
          if let tabTitle = activeTab.title, tabTitle != "", data.title != tabTitle {
            data.title = tabTitle
          }
        }
      } else {
        log("Failed to read Chrome context; emitting foreground heartbeat without URL")
      }
    } else if applicationName == "Safari" {
      debug("Safari browser detected, extracting URL and title")
      if let bundleIdentifier = application.bundleIdentifier,
         let safariObject: SafariApplication = SBApplication.init(bundleIdentifier: bundleIdentifier),
         let windows = safariObject.windows,
         let frontWindow = windows().first,
         let activeTab = frontWindow.currentTab {
        data.url = activeTab.URL
        if let tabTitle = activeTab.name, tabTitle != "", data.title != tabTitle {
          data.title = tabTitle
        }
      } else {
        log("Failed to read Safari context; emitting foreground heartbeat without URL")
      }
    } else if FIREFOX_BROWSERS.contains(applicationName), let window = window {
      debug("Firefox-based browser detected, extracting URL from accessibility tree")
      data.url = geckoURL(window: window)

      if data.url == nil {
        let axApp = AXUIElementCreateApplication(application.processIdentifier)
        AXUIElementSetAttributeValue(axApp, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
      }
    }

    if researchEnabled {
      data = applyResearchFilter(data)
    } else if excludeTitle || titleShouldBeExcluded(data.title ?? "") {
      data.title = "excluded"
      data.url = nil
    }

    sendHeartbeat(Heartbeat(timestamp: nowTime, data: data))
  }

  deinit {
    pollingTimer?.invalidate()
    tearDownObserver()
  }
}

// TODO I believe this is handled by the python wrapper so it isn't needed here
func checkAccess() -> Bool {
  let checkOptPrompt = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as NSString
  let options = [checkOptPrompt: true]
  let accessEnabled = AXIsProcessTrustedWithOptions(options as CFDictionary?)
  return accessEnabled
}
