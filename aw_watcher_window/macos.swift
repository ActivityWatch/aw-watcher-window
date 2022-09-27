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
    @objc optional var bounds: NSRect { get } // The bounding rectangle of the window.
    @objc optional var closeable: Bool { get } // Does the window have a close button?
    @objc optional var miniaturizable: Bool { get } // Does the window have a minimize button?
    @objc optional var miniaturized: Bool { get } // Is the window minimized right now?
    @objc optional var resizable: Bool { get } // Can the window be resized?
    @objc optional var visible: Bool { get } // Is the window visible right now?
    @objc optional var zoomable: Bool { get } // Does the window have a zoom button?
    @objc optional var zoomed: Bool { get } // Is the window zoomed right now?
    @objc optional var document: SafariDocument { get } // The document whose contents are displayed in the window.
    @objc optional func setIndex(_ index: Int) // The index of the window, ordered front to back.
    @objc optional func setBounds(_ bounds: NSRect) // The bounding rectangle of the window.
    @objc optional func setMiniaturized(_ miniaturized: Bool) // Is the window minimized right now?
    @objc optional func setVisible(_ visible: Bool) // Is the window visible right now?
    @objc optional func setZoomed(_ zoomed: Bool) // Is the window zoomed right now?
    @objc optional func tabs() -> SBElementArray
    @objc optional var currentTab: SafariTab { get } // The current tab.
    @objc optional func setCurrentTab(_ currentTab: SafariTab!) // The current tab.
}
extension SBObject: SafariWindow {}

@objc public protocol SafariApplication {
    @objc optional func documents() -> SBElementArray
    @objc optional func windows() -> [SafariWindow]
    @objc optional var name: String { get } // The name of the application.
    @objc optional var frontmost: Bool { get } // Is this the active application?
}
extension SBApplication: SafariApplication {}


struct NetworkMessage: Codable, Equatable {
  var app: String
  var title: String
  var url: String?
}

struct Heartbeat: Codable {
  var timestamp: Date
  var data: NetworkMessage
}

struct Bucket: Codable {
  var client: String
  var type: String
  var hostname: String
}

// Placeholder values, set in start()
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

  NSWorkspace.shared.notificationCenter.addObserver(
    main, selector: #selector(main.focusedAppChanged),
    name: NSWorkspace.didActivateApplicationNotification,
    object: nil)
  main.focusedAppChanged()
}

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
      print("Failed to create bucket")
      return
    }
  }
}

func sendHeartbeat(_ heartbeat: Heartbeat) {
  // First, send heartbeat ending last event, if event data differs
  let payload_old: Heartbeat? = oldHeartbeat.flatMap {
    if $0.data != heartbeat.data {
      return Heartbeat(timestamp: heartbeat.timestamp, data: $0.data)
    } else {
      return Optional<Heartbeat>.none
    }
  }

  // Then, send heartbeat starting new event
  let payload_new = heartbeat

  // TODO: set proper pulsetime
  Task {
    if let payload_old = payload_old {
      let since_last_seconds = heartbeat.timestamp.timeIntervalSince(oldHeartbeat!.timestamp) + 1
      do {
        try await sendHeartbeatSingle(payload_old, pulsetime: since_last_seconds);
      } catch {
        print("Failed to send heartbeat: \(error)")
        return
      }
    }

    do {
      let since_last_seconds = heartbeat.timestamp.timeIntervalSince((oldHeartbeat ?? heartbeat).timestamp) + 1
      try await sendHeartbeatSingle(payload_new, pulsetime: since_last_seconds);
    } catch {
      print("Failed to send heartbeat: \(error)")
      return
    }

    // Assign the latest heartbeat as the old heartbeat
    oldHeartbeat = heartbeat
  }
}

enum HeartbeatError: Error {
    case error(msg: String)
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
  // TODO: remove this debug logging when done
  print("[heartbeat] timestamp: \(heartbeat.timestamp), pulsetime: \(round(pulsetime * 10) / 10), app: \(heartbeat.data.app), title: \(heartbeat.data.title), url: \(heartbeat.data.url ?? "")")
}

class MainThing {
  var observer: AXObserver?
  var oldWindow: AXUIElement?
  var idle = false

  func windowTitleChanged(
    _ axObserver: AXObserver,
    axElement: AXUIElement,
    notification: CFString
  ) {
    let frontmost = NSWorkspace.shared.frontmostApplication!
    let bundleIdentifier = frontmost.bundleIdentifier!

    var windowTitle: AnyObject?
    AXUIElementCopyAttributeValue(axElement, kAXTitleAttribute as CFString, &windowTitle)

    var data = NetworkMessage(app: frontmost.localizedName!, title: windowTitle as? String ?? "")

    // list of chrome equivalent browsers
    let chromeBrowsers = [
      "Google Chrome",
      "Google Chrome Canary",
      "Chromium",
      "Brave Browser",
    ]

    if chromeBrowsers.contains(frontmost.localizedName!) {
      let chromeObject: ChromeProtocol = SBApplication.init(bundleIdentifier: bundleIdentifier)!

      let frontWindow = chromeObject.windows!()[0]
      let activeTab = frontWindow.activeTab!

      if frontWindow.mode == "incognito" {
        data = NetworkMessage(app: "", title: "")
      } else {
        data.url = activeTab.URL
        if let title = activeTab.title { data.title = title }
      }
    } else if frontmost.localizedName == "Safari" {
      let safariObject: SafariApplication = SBApplication.init(bundleIdentifier: bundleIdentifier)!

      let frontWindow = safariObject.windows!()[0]
      let activeTab = frontWindow.currentTab!

      // Safari doesn't have an incognito mode, we cannot hide the url
      data.url = activeTab.URL
      if let title = activeTab.name { data.title = title }
    }

    let heartbeat = Heartbeat(timestamp: Date.now, data: data)
    sendHeartbeat(heartbeat)
  }

  @objc func focusedWindowChanged(_ observer: AXObserver, window: AXUIElement) {
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
    if observer != nil {
      CFRunLoopRemoveSource(
        RunLoop.current.getCFRunLoop(),
        AXObserverGetRunLoopSource(observer!),
        CFRunLoopMode.defaultMode)
    }

    let frontmost = NSWorkspace.shared.frontmostApplication!
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
          print("Missing userData")
          return
        }
        let application = Unmanaged<MainThing>.fromOpaque(userData).takeUnretainedValue()
        if notification == kAXFocusedWindowChangedNotification as CFString {
          application.focusedWindowChanged(axObserver, window: axElement)
        } else {
          application.windowTitleChanged(
            axObserver, axElement: axElement, notification: notification)
        }
      }, &observer)

    let selfPtr = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())
    AXObserverAddNotification(
      observer!, focusedApp, kAXFocusedWindowChangedNotification as CFString, selfPtr)

    CFRunLoopAddSource(
      RunLoop.current.getCFRunLoop(),
      AXObserverGetRunLoopSource(observer!),
      CFRunLoopMode.defaultMode)

    var focusedWindow: AnyObject?
    AXUIElementCopyAttributeValue(focusedApp, kAXFocusedWindowAttribute as CFString, &focusedWindow)

    if focusedWindow != nil {
      focusedWindowChanged(observer!, window: focusedWindow as! AXUIElement)
    }
  }
}

func checkAccess() -> Bool {
  let checkOptPrompt = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as NSString
  let options = [checkOptPrompt: true]
  let accessEnabled = AXIsProcessTrustedWithOptions(options as CFDictionary?)
  return accessEnabled
}

func SystemIdleTime() -> Double? {
  var iterator: io_iterator_t = 0
  defer { IOObjectRelease(iterator) }
  guard
    IOServiceGetMatchingServices(kIOMainPortDefault, IOServiceMatching("IOHIDSystem"), &iterator)
      == KERN_SUCCESS
  else {
    return nil
  }

  let entry: io_registry_entry_t = IOIteratorNext(iterator)
  defer { IOObjectRelease(entry) }
  guard entry != 0 else { return nil }

  var unmanagedDict: Unmanaged<CFMutableDictionary>? = nil
  defer { unmanagedDict?.release() }
  guard
    IORegistryEntryCreateCFProperties(entry, &unmanagedDict, kCFAllocatorDefault, 0) == KERN_SUCCESS
  else { return nil }
  guard let dict = unmanagedDict?.takeUnretainedValue() else { return nil }

  let key: CFString = "HIDIdleTime" as CFString
  let value = CFDictionaryGetValue(dict, Unmanaged.passUnretained(key).toOpaque())
  let number: CFNumber = unsafeBitCast(value, to: CFNumber.self)
  var nanoseconds: Int64 = 0
  guard CFNumberGetValue(number, CFNumberType.sInt64Type, &nanoseconds) else { return nil }
  let interval = Double(nanoseconds) / Double(NSEC_PER_SEC)

  return interval
}
