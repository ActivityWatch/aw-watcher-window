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

struct NetworkMessage: Codable {
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

let clientHostname = ProcessInfo.processInfo.hostName
let clientName = "aw-watcher-window2"
let bucketName = "\(clientName)_\(clientHostname)"

let main = MainThing()
var oldHeartbeatData: NetworkMessage?

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
  detectIdle()
}

func detectIdle() {
  let seconds = 15.0 - SystemIdleTime()!
  if seconds < 0.0 {
    sendHeartbeat(data: NetworkMessage(app: "", title: ""))

    var monitor: Any?
    monitor = NSEvent.addGlobalMonitorForEvents(matching: [
      .mouseMoved, .leftMouseDown, .rightMouseDown, .keyDown,
    ]) { e in
      NSEvent.removeMonitor(monitor!)
      if let oldMenu = oldHeartbeatData { sendHeartbeat(data: oldMenu) }
      detectIdle()
    }

    return
  }

  DispatchQueue.main.asyncAfter(deadline: .now() + seconds) {
    detectIdle()
  }
}

func createBucket() {
  let payload = try! encoder.encode(
    Bucket(client: clientName, type: "currentwindow", hostname: clientHostname))

  let url = URL(string: "http://localhost:5600/api/0/buckets/\(bucketName)")!
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

func sendHeartbeat(data: NetworkMessage) {
  let payload0 = oldHeartbeatData.map {
    try! encoder.encode(Heartbeat(timestamp: Date.now, data: $0))
  }
  let payload = try! encoder.encode(Heartbeat(timestamp: Date.now, data: data))

  let url = URL(string: "http://localhost:5600/api/0/buckets/\(bucketName)/heartbeat?pulsetime=999999")!
  Task {
    if let payload0 = payload0 {
      var urlRequest = URLRequest(url: url)
      urlRequest.httpMethod = "POST"
      urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
      let (_, response) = try await URLSession.shared.upload(for: urlRequest, from: payload0)
      guard (200...299).contains((response as! HTTPURLResponse).statusCode) else {
        print("Failed to send window exit heartbeat")
        return
      }
    }

    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
    let (_, response) = try await URLSession.shared.upload(for: urlRequest, from: payload)
    guard (200...299).contains((response as! HTTPURLResponse).statusCode) else {
      print("Failed to send window enter heartbeat")
      return
    }

  }
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
    var windowTitle: AnyObject?
    AXUIElementCopyAttributeValue(axElement, kAXTitleAttribute as CFString, &windowTitle)

    var data = NetworkMessage(app: frontmost.localizedName!, title: windowTitle as? String ?? "")

    if frontmost.localizedName == "Google Chrome" {
      let chromeObject: ChromeProtocol = SBApplication.init(bundleIdentifier: "com.google.Chrome")!

      let frontWindow = chromeObject.windows!()[0]
      let activeTab = frontWindow.activeTab!

      if frontWindow.mode == "incognito" {
        data = NetworkMessage(app: "", title: "")
      } else {
        data.url = activeTab.URL
        if let title = activeTab.title { data.title = title }
      }
    }

    sendHeartbeat(data: data)
    oldHeartbeatData = data
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
