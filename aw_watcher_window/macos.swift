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
  var title: String
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
  if(logLevel == "DEBUG") {
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

let main = MainThing()
var oldHeartbeat: Heartbeat?

let encoder = JSONEncoder()
let formatter = ISO8601DateFormatter()
formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

encoder.dateEncodingStrategy = .custom({ date, encoder in
  var container = encoder.singleValueContainer()
  let dateString = formatter.string(from: date)
  try container.encode(dateString)
})

start()
RunLoop.main.run()

func start() {
  // Arguments should be:
  //  - url + port
  //  - bucket_id
  //  - hostname
  //  - client_id
  let arguments = CommandLine.arguments

  // Check that we get 4 arguments
  if arguments.count != 5 {
    print("Usage: aw-watcher-window <url> <bucket> <hostname> <client>")
    exit(1)
  }

  baseurl = arguments[1]
  bucketName = arguments[2]
  clientHostname = arguments[3]
  clientName = arguments[4]

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
    selector: #selector(main.focusedAppChanged),
    name: NSWorkspace.didActivateApplicationNotification,
    object: nil
  )

  main.focusedAppChanged()

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

  debug("[heartbeat] bucket: \(bucketName), timestamp: \(heartbeat.timestamp), pulsetime: \(round(pulsetime * 10) / 10), app: \(heartbeat.data.app), title: \(heartbeat.data.title), url: \(heartbeat.data.url ?? "")")
}

class MainThing {
  var observer: AXObserver?
  var oldWindow: AXUIElement?
  var pollingTimer: Timer?

  // list of chrome equivalent browsers
  let CHROME_BROWSERS = [
    "Google Chrome",
    "Google Chrome Canary",
    "Chromium",
    "Brave Browser",
  ]

  @objc func pollActiveWindow() {
    debug("Polling active window")

    guard let frontmost = NSWorkspace.shared.frontmostApplication else {
      log("Failed to get frontmost application from polling")
      return
    }

    let pid = frontmost.processIdentifier
    let focusedApp = AXUIElementCreateApplication(pid)

    var focusedWindow: AnyObject?
    AXUIElementCopyAttributeValue(focusedApp, kAXFocusedWindowAttribute as CFString, &focusedWindow)

    if focusedWindow != nil {
      focusedWindowChanged(observer!, window: focusedWindow as! AXUIElement)
    }
  }

  deinit {
    pollingTimer?.invalidate()
  }

  func windowTitleChanged(
    _ axObserver: AXObserver,
    axElement: AXUIElement,
    notification: CFString
  ) {
    guard let frontmost = NSWorkspace.shared.frontmostApplication else {
      log("Failed to get frontmost application from window title notification")
      return
    }

    guard let bundleIdentifier = frontmost.bundleIdentifier else {
      log("Failed to get bundle identifier from frontmost application")
      return
    }

    // calculate now before executing any scripting since that can take some time
    let nowTime = Date.now

    var windowTitle: AnyObject?
    AXUIElementCopyAttributeValue(axElement, kAXTitleAttribute as CFString, &windowTitle)

    var data = NetworkMessage(app: frontmost.localizedName!, title: windowTitle as? String ?? "")

    if CHROME_BROWSERS.contains(frontmost.localizedName!) {
      debug("Chrome browser detected, extracting URL and title")

      let chromeObject: ChromeProtocol = SBApplication.init(bundleIdentifier: bundleIdentifier)!

      let frontWindow = chromeObject.windows!()[0]
      let activeTab = frontWindow.activeTab!

      if frontWindow.mode == "incognito" {
        data = NetworkMessage(app: "", title: "")
      } else {
        data.url = activeTab.URL

        // the tab title is more accurate and often different than the window title
        // however, in some cases the binary does not have the right permissions to read
        // the title properly and will return a blank string

        if let tabTitle = activeTab.title {
          if(tabTitle != "" && data.title != tabTitle) {
            error("tab title diff: \(tabTitle), window title: \(data.title ?? "")")
            data.title = tabTitle
          }
        }
      }
    } else if frontmost.localizedName == "Safari" {
      debug("Safari browser detected, extracting URL and title")

      let safariObject: SafariApplication = SBApplication.init(bundleIdentifier: bundleIdentifier)!

      let frontWindow = safariObject.windows!()[0]
      let activeTab = frontWindow.currentTab!

      // Safari doesn't allow incognito mode to be inspected, so we do not know if we should hide the url
      data.url = activeTab.URL

      // comment above applies here as well
      if let tabTitle = activeTab.name {
        if tabTitle != "" && data.title != tabTitle {
          error("tab title diff: \(tabTitle), window title: \(data.title ?? "")")
          data.title = tabTitle
        }
      }
    }

    let heartbeat = Heartbeat(timestamp: nowTime, data: data)
    sendHeartbeat(heartbeat)
  }

  @objc func focusedWindowChanged(_ observer: AXObserver, window: AXUIElement) {
    debug("Focused window changed")

    if oldWindow != nil {
      AXObserverRemoveNotification(
        observer, oldWindow!, kAXFocusedWindowChangedNotification as CFString)
    }

    let selfPtr = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())
    AXObserverAddNotification(observer, window, kAXTitleChangedNotification as CFString, selfPtr)

    windowTitleChanged(
      observer, axElement: window, notification: kAXTitleChangedNotification as CFString)

    oldWindow = window
  }

  @objc func focusedAppChanged() {
    debug("Focused app changed")

    if observer != nil {
      CFRunLoopRemoveSource(
        RunLoop.current.getCFRunLoop(),
        AXObserverGetRunLoopSource(observer!),
        CFRunLoopMode.defaultMode
      )
    }

    guard let frontmost = NSWorkspace.shared.frontmostApplication else {
      log("Failed to get frontmost application from app change notification")
      return
    }

    let pid = frontmost.processIdentifier
    let focusedApp = AXUIElementCreateApplication(pid)

    AXObserverCreate(
      pid,
      {
        (
          _ axObserver: AXObserver,
          axElement: AXUIElement,
          notification: CFString,
          userData: UnsafeMutableRawPointer?
        ) -> Void in
        guard let userData = userData else {
          log("Missing userData")
          return
        }
        let application = Unmanaged<MainThing>.fromOpaque(userData).takeUnretainedValue()
        if notification == kAXFocusedWindowChangedNotification as CFString {
          application.focusedWindowChanged(axObserver, window: axElement)
        } else {
          application.windowTitleChanged(
            axObserver,
            axElement: axElement,
            notification: notification
          )
        }
      }, &observer)

    let selfPtr = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())
    AXObserverAddNotification(
      observer!, focusedApp, kAXFocusedWindowChangedNotification as CFString, selfPtr)

    CFRunLoopAddSource(
      RunLoop.current.getCFRunLoop(),
      AXObserverGetRunLoopSource(observer!),
      CFRunLoopMode.defaultMode
    )

    var focusedWindow: AnyObject?
    AXUIElementCopyAttributeValue(focusedApp, kAXFocusedWindowAttribute as CFString, &focusedWindow)

    if focusedWindow != nil {
      focusedWindowChanged(observer!, window: focusedWindow as! AXUIElement)
    }
  }
}

// TODO I believe this is handled by the python wrapper so it isn't needed here
func checkAccess() -> Bool {
  let checkOptPrompt = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as NSString
  let options = [checkOptPrompt: true]
  let accessEnabled = AXIsProcessTrustedWithOptions(options as CFDictionary?)
  return accessEnabled
}
