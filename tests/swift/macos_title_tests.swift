// Synthetic, non-personal AX fixtures model the observed shell/document/main/
// sidebar structure. Nothing here queries an installed app or sends heartbeats.
final class FixtureElement {
  var attributes: [String: AnyObject]
  var descendants: [FixtureElement]
  init(_ role: String = "AXGroup", _ attributes: [String: AnyObject] = [:],
       _ children: [FixtureElement] = []) {
    self.attributes = attributes
    self.attributes["AXRole"] = role as NSString
    self.descendants = children
  }
}

func node(_ role: String = "AXGroup", _ attributes: [String: String] = [:],
          _ children: [FixtureElement] = []) -> FixtureElement {
  FixtureElement(role, attributes.mapValues { $0 as NSString }, children)
}
func region(_ children: [FixtureElement], subrole: String = "AXLandmarkMain") -> FixtureElement {
  node("AXGroup", ["AXSubrole": subrole], children)
}
func pair(_ title: String) -> [FixtureElement] {
  [node("AXButton", ["AXDescription": title + ", rename session"]),
   node("AXPopUpButton", ["AXDescription": "More options for " + title])]
}
func claude(_ title: String? = "Claude", _ children: [FixtureElement] = []) -> FixtureElement {
  var attrs = ["AXURL": "https://claude.ai/chat/example"]
  attrs["AXTitle"] = title
  return node("AXWindow", [:], [node("AXWebArea", ["AXURL": "file:///example/shell.html"],
    [node("AXWebArea", attrs, children)])])
}
func joplin(_ children: [FixtureElement]) -> FixtureElement {
  node("AXWindow", [:], [node("AXWebArea", ["AXTitle": "Joplin"], [region(children)])])
}
func titleField(_ title: String) -> FixtureElement {
  node("AXTextField", ["AXDescription": "Note title", "AXValue": title])
}

var checks = 0
func expect(_ condition: @autoclosure () -> Bool, _ description: String) {
  checks += 1
  guard condition() else {
    fputs("FAIL: \(description)\n", stderr)
    exit(1)
  }
}
var attributeReads = 0
var childRequests = 0
var largestChildRequest = 0
let fixtureReader = TitleElementReader<FixtureElement>(
  string: { element, key in
    attributeReads += 1
    return axString(element.attributes[key])
  }, children: { element, limit in
    childRequests += 1
    largestChildRequest = max(largestChildRequest, limit)
    return Array(element.descendants.prefix(limit))
  })
func extract(_ window: FixtureElement, _ app: ElectronTitleApp = .claude) -> String? {
  var lookup = ElectronTitleLookup(reader: fixtureReader)
  return lookup.title(window: window, app: app)
}
func resetOptions() {
  excludeTitle = false
  excludeTitlePatterns = []
  researchEnabled = false
  researchAppCategoryMap = []
  titleEnrichmentApps = []
  attributeReads = 0
  childRequests = 0
  largestChildRequest = 0
}

// Document titles take precedence and never come from nested artifact frames.
expect(extract(claude("Example chat - Claude")) == "Example chat - Claude", "chat document title")
expect(extract(claude("Example task - Claude")) == "Example task - Claude", "Cowork document title")
expect(extract(claude("日本語の会話 - Claude")) == "日本語の会話 - Claude", "Unicode document title")
expect(extract(claude("New task - Claude")) == "New task - Claude", "app-authored new-task title")
expect(extract(claude("   ")) == nil, "blank document")
expect(extract(claude(nil)) == nil, "missing document title")
expect(extract(node("AXWindow")) == nil, "missing tree")
expect(extract(node("AXWindow", [:], [node("AXWebArea", ["AXURL": "https://example.test", "AXTitle": "Other page"])])) == nil, "unrelated web area")
expect(extract(claude("Claude", [node("AXWebArea", ["AXURL": "https://claude.ai/artifact/example", "AXTitle": "Embedded content"])])) == nil, "unnamed document does not use iframe title")
expect(extract(claude("Actual chat", [region(pair("Other session"))])) == "Actual chat", "document precedes header")

// Match the exact semantic pair; no word overlap, minimum length, or trimming of
// legitimate punctuation. UI labels are English, but titles may use any script.
for title in ["Budget review", "Q1", "日本", "A", "🧪", "- draft, ", "More options for example"] {
  expect(extract(claude("Claude", [region(pair(title))])) == title, "header title \(title.debugDescription)")
}
expect(extract(claude("Claude", [region([
  node("AXButton", ["AXDescription": "Open settings"]),
  node("AXPopUpButton", ["AXDescription": "Open model menu"])
])])) == nil, "unrelated shared word is not a title")
expect(extract(claude("Claude", [region([
  node("AXButton", ["AXDescription": "Add"]),
  node("AXPopUpButton", ["AXDescription": "Add files"])
])])) == nil, "Add controls")
expect(extract(claude("Claude", [region(pair(" "))])) == nil, "empty header name")
expect(extract(claude("Claude", [region([pair("Alpha")[0], pair("Beta")[1]])])) == nil, "mismatched controls")
expect(extract(claude("Claude", [region(pair("Alpha") + pair("Beta"))])) == nil, "ambiguous headers")
expect(extract(claude("Claude", [region([pair("Alpha")[0]])])) == nil, "rename control alone")
expect(extract(claude("Claude", [region([
  node("AXButton", ["AXDescription": "日本, セッション名を変更"]),
  node("AXPopUpButton", ["AXDescription": "日本のその他のオプション"])
])])) == nil, "unsupported localized controls safely fall back")
expect(extract(claude("Claude", [region(pair("Sidebar session"), subrole: "AXLandmarkComplementary"),
  region(pair("Open session"))])) == "Open session", "sidebar must not win")
expect(extract(claude("Claude", [region([
  region(pair("Message controls"), subrole: "AXApplicationGroup")
] + pair("Open session"))])) == "Open session", "message feed skipped")
expect(extract(claude("Claude", [region(pair("First"))])) == "First", "first session")
expect(extract(claude("Claude", [region(pair("Second"))])) == "Second", "changed session has no stale cache")

// Joplin's title must be explicitly labelled, shallow, and not a search field.
expect(extract(joplin([titleField("Example note")]), .joplin) == "Example note", "Joplin title")
expect(extract(joplin([node("AXTextField", ["AXValue": "Find query"]), titleField("Actual note")]), .joplin) == "Actual note", "unlabelled text field ignored")
expect(extract(joplin([node("AXTextField", ["AXSubrole": "AXSearchField", "AXDescription": "Note title", "AXValue": "Search"])]), .joplin) == nil, "search field ignored")
expect(extract(joplin([node("AXTextField", ["AXDescription": "Find", "AXValue": "Query"])]), .joplin) == nil, "unrelated field ignored")
expect(extract(joplin([titleField("")]), .joplin) == nil, "empty note")
expect(extract(joplin([titleField("日本")]), .joplin) == "日本", "short Unicode note")
expect(extract(joplin([titleField("First note"), titleField("Second note")]), .joplin) == nil, "duplicate note titles are ambiguous")
expect(extract(joplin([titleField("Same note"), titleField("Same note")]), .joplin) == nil, "identical duplicate note fields are ambiguous")
expect(extract(joplin([titleField("Note"), titleField("")]), .joplin) == nil, "empty duplicate note field is still ambiguous")
expect(extract(joplin([node("AXTextField", ["AXDescription": "Titre de la note", "AXValue": "Exemple"])]), .joplin) == nil, "unsupported localized note field")
expect(extract(joplin([node("AXGroup", [:], [node("AXGroup", [:], [titleField("Depth three")])])]), .joplin) == "Depth three", "depth boundary")
expect(extract(joplin([node("AXGroup", [:], [node("AXGroup", [:], [node("AXGroup", [:], [titleField("Body content")])])])]), .joplin) == nil, "deep content ignored")

// Malformed AX values must never reach the unsafe Swift NSString bridge.
let response = HTTPURLResponse(url: URL(string: "https://example.test")!, statusCode: 200, httpVersion: nil, headerFields: nil)!
expect(axString(response) == nil, "HTTP response is not an AX string (#144)")
expect(axString(NSNumber(value: 42)) == nil, "number is not an AX string")
expect(axString(NSAttributedString(string: "Attributed title")) == "Attributed title", "attributed title")
expect(axElement(response) == nil, "non-element rejected")
let malformed = claude()
malformed.descendants[0].descendants[0].attributes["AXTitle"] = response
expect(extract(malformed) == nil, "malformed document title falls back")
let malformedNote = titleField("Note")
malformedNote.attributes["AXValue"] = response
expect(extract(joplin([malformedNote]), .joplin) == nil, "malformed note value falls back")

// Budget includes queued children and all fallback searches, even for cycles.
resetOptions()
let broad = node("AXWindow", [:], (0..<10000).map { _ in node() })
var broadLookup = ElectronTitleLookup(reader: fixtureReader)
expect(broadLookup.title(window: broad, app: .claude) == nil, "wide tree has no result")
expect(broadLookup.remaining == 0 && largestChildRequest <= 383, "wide tree bounds visits and child requests")
let cycle = node("AXWindow")
cycle.descendants = [cycle]
var cyclicLookup = ElectronTitleLookup(reader: fixtureReader)
expect(cyclicLookup.title(window: cycle, app: .claude) == nil && cyclicLookup.remaining == 0, "cyclic tree terminates")
cycle.descendants = []
var smallLookup = ElectronTitleLookup(reader: fixtureReader, remaining: 8)
expect(smallLookup.title(window: claude("Claude", [region(pair("Candidate") + (0..<30).map { _ in node() })]), app: .claude) == nil, "incomplete header search must not claim uniqueness")
var smallNoteLookup = ElectronTitleLookup(reader: fixtureReader, remaining: 8)
expect(smallNoteLookup.title(window: joplin([titleField("Candidate")] + (0..<30).map { _ in node() }), app: .joplin) == nil, "incomplete note search must not claim uniqueness")

// Use a virtual clock and injected AX transport to exercise the production
// timeout path deterministically, without permissions, sleeping, or live apps.
let timeoutElement = AXUIElementCreateApplication(getpid())
var clock: TimeInterval = 100
var timeouts: [Float] = []
let budget = TitleLookupBudget(now: { clock }, setTimeout: { _, seconds in
  timeouts.append(seconds)
  return .success
})
expect(budget.perform(on: timeoutElement) { clock += 0.01; return .success }, "request within deadline succeeds")
expect(timeouts == [0.05, 0], "AX request gets a short timeout then restores the object default")
clock = 100.24
expect(!budget.perform(on: timeoutElement) { clock += 0.02; return .success }, "late AX response is discarded")
expect(timeouts[2] > 0 && timeouts[2] < 0.011 && timeouts[3] == 0, "request timeout shrinks to remaining deadline")
var requestsAfterStop = 0
expect(!budget.perform(on: timeoutElement) { requestsAfterStop += 1; return .success }, "expired budget refuses another request")
expect(requestsAfterStop == 0 && timeouts.count == 4, "expired budget makes no AX calls")
let stalledBudget = TitleLookupBudget(now: { clock }, setTimeout: { _, _ in .success })
expect(!stalledBudget.perform(on: timeoutElement) { .cannotComplete }, "unresponsive AX call fails")
expect(!stalledBudget.canRead, "unresponsive AX call stops the whole lookup")
let unsupportedBudget = TitleLookupBudget(now: { clock }, setTimeout: { _, _ in .success })
expect(!unsupportedBudget.perform(on: timeoutElement) { .attributeUnsupported } && unsupportedBudget.canRead, "missing optional AX attribute is not a transport timeout")
let rejectedBudget = TitleLookupBudget(now: { clock }, setTimeout: { _, _ in .invalidUIElement })
expect(!rejectedBudget.perform(on: timeoutElement) { requestsAfterStop += 1; return .success }, "failed timeout setup prevents an unbounded request")
expect(requestsAfterStop == 0 && !rejectedBudget.canRead, "failed timeout setup stops lookup")
let setupBudget = TitleLookupBudget(now: { clock }, setTimeout: { _, _ in clock += 1; return .success })
expect(!setupBudget.perform(on: timeoutElement) { requestsAfterStop += 1; return .success }, "deadline reached during timeout setup skips the request")
expect(requestsAfterStop == 0, "no request starts after its deadline")
expect(TitleLookupBudget().perform(on: timeoutElement) { .success }, "platform accepts per-element timeout configuration")

// Exercise the production child reader when AX reports a nonempty subtree but
// cannot return it. An already observed title cannot prove uniqueness then.
for (label, result, values) in [
  ("noValue", AXError.noValue, nil as CFArray?),
  ("attributeUnsupported", .attributeUnsupported, nil),
  ("missing array", .success, nil),
  ("empty array", .success, [] as CFArray),
  ("short array", .success, [timeoutElement] as CFArray),
  ("oversized array", .success, [timeoutElement, timeoutElement, timeoutElement] as CFArray),
  ("invalid element", .success, [timeoutElement, "not an AX element" as NSString] as CFArray)
] {
  for app in [ElectronTitleApp.joplin, .claude] {
    resetOptions()
    titleEnrichmentApps = [app]
    let unread = node("AXGroup", [:], [titleField("Other note")])
    let tree = app == .joplin ? joplin([titleField("Candidate"), unread])
      : claude("Claude", [region(pair("Candidate") + [unread])])
    let childBudget = TitleLookupBudget(now: { 0 }, setTimeout: { _, _ in .success })
    var copyCalls = 0
    let liveReader = liveTitleReader(budget: childBudget,
      childCount: { _, count in count.pointee = 2; return .success },
      copyChildren: { _, _, children in
        copyCalls += 1
        children.pointee = values
        return result
      })
    let reader = TitleElementReader<FixtureElement>(string: fixtureReader.string,
      children: { element, limit in
        if element === unread {
          return liveReader.children(timeoutElement, limit).map { _ in node() }
        }
        return fixtureReader.children(element, limit)
      }, canRead: liveReader.canRead)
    let native = NetworkMessage(app: app.rawValue, title: app.rawValue)
    var writes = 0
    let enriched = enrichElectronTitle(native, bundleIdentifier: app.bundleIdentifier,
      window: tree, reader: reader, enableAccessibility: { writes += 1 })
    expect(enriched == native, "\(app.rawValue) retains native title after child fetch \(label)")
    expect(copyCalls == 1 && !childBudget.canRead && writes == 0,
      "child fetch \(label) stops \(app.rawValue) lookup and cold-tree write")
  }
}

// Missing children attributes and an explicit zero count are still valid
// leaves. A successful read requests and returns only the available node budget.
for (label, status, count, expectedCount, readable) in [
  ("unsupported leaf", AXError.attributeUnsupported, 0, 0, true),
  ("missing leaf", .noValue, 0, 0, true),
  ("empty leaf", .success, 0, 0, true),
  ("negative count", .success, -1, 0, false),
  ("complete children", .success, 2, 2, true),
  ("bounded children", .success, 10000, 2, true)
] {
  let childBudget = TitleLookupBudget(now: { 0 }, setTimeout: { _, _ in .success })
  var requestedCounts: [CFIndex] = []
  let reader = liveTitleReader(budget: childBudget,
    childCount: { _, value in value.pointee = count; return status },
    copyChildren: { _, requested, values in
      requestedCounts.append(requested)
      values.pointee = [timeoutElement, timeoutElement] as CFArray
      return .success
    })
  expect(reader.children(timeoutElement, 2).count == expectedCount
    && reader.canRead() == readable, "child reader handles \(label)")
  expect(requestedCounts == (expectedCount > 0 ? [2] : []),
    "child reader bounds or skips the copy for \(label)")
}

var slowClock: TimeInterval = 0
var slowReads = 0
var slowTimeouts: [Float] = []
let slowBudget = TitleLookupBudget(now: { slowClock }, setTimeout: { _, seconds in
  slowTimeouts.append(seconds)
  return .success
})
let slowReader = TitleElementReader<FixtureElement>(
  string: { element, key in
    var value: String?
    guard slowBudget.perform(on: timeoutElement, {
      slowReads += 1
      slowClock += 0.04
      value = fixtureReader.string(element, key)
      return .success
    }) else { return nil }
    return value
  }, children: { element, limit in
    var children: [FixtureElement] = []
    guard slowBudget.perform(on: timeoutElement, {
      slowReads += 1
      slowClock += 0.04
      children = fixtureReader.children(element, limit)
      return .success
    }) else { return [] }
    return children
  }, canRead: { slowBudget.canRead })
var slowLookup = ElectronTitleLookup(reader: slowReader)
expect(slowLookup.title(window: claude("Late document"), app: .claude) == nil, "slow traversal falls back without a partial title")
expect(slowReads <= 7 && slowLookup.remaining > 0, "time budget stops traversal before the node budget")
expect(slowTimeouts.allSatisfy { $0 >= 0 && $0 <= 0.05 }, "all traversal requests use bounded messaging timeouts")

// Production opt-in/bundle checks and final privacy filter are exercised too.
let window = claude("Private example - Claude")
let original = NetworkMessage(app: "Claude", title: "Claude")
var enabled = 0
func enriched(_ data: NetworkMessage = original, bundle: String? = "com.anthropic.claudefordesktop", tree: FixtureElement = window) -> NetworkMessage {
  enrichElectronTitle(data, bundleIdentifier: bundle, window: tree, reader: fixtureReader, enableAccessibility: { enabled += 1 })
}
resetOptions()
expect(enriched() == original && attributeReads == 0 && enabled == 0, "default off does not touch AX")
titleEnrichmentApps = [.joplin]
expect(enriched() == original && attributeReads == 0, "opt-in is per app")
titleEnrichmentApps = [.claude]
expect(enriched(bundle: "example.other") == original && attributeReads == 0, "app-name impersonation does not opt in")
expect(enriched(bundle: nil) == original && attributeReads == 0, "missing bundle identifier")
expect(enriched().title == "Private example - Claude", "enabled title enrichment")
let informative = NetworkMessage(app: "Claude", title: "Native title")
expect(enriched(informative) == informative, "preserve informative native title")
expect(enriched(tree: node("AXWindow")) == original && enabled == 1, "cold tree enables AX and retains native title")
expect(enriched().title == "Private example - Claude", "cold tree recovers on next poll")
let blank = NetworkMessage(app: "Claude", title: "")
expect(enriched(blank).title == "Private example - Claude", "empty native title can be enriched")
for app in [ElectronTitleApp.claude, .joplin] {
  resetOptions()
  titleEnrichmentApps = [app]
  excludeTitlePatterns = [compileExcludeTitlePattern("^" + app.rawValue + "$")]
  let native = NetworkMessage(app: app.rawValue, title: app.rawValue, url: "https://example.test/private")
  let enabledBeforeExclusion = enabled
  let enrichedNative = enrichElectronTitle(native, bundleIdentifier: app.bundleIdentifier,
    window: app == .claude ? window : joplin([titleField("Private example")]),
    reader: fixtureReader, enableAccessibility: { enabled += 1 })
  expect(attributeReads == 0 && childRequests == 0, "native exclusion skips all AX reads for \(app.rawValue)")
  expect(enabled == enabledBeforeExclusion, "native exclusion skips AX writes for \(app.rawValue)")
  expect(filterWindowData(enrichedNative) == NetworkMessage(app: app.rawValue, title: "excluded", url: nil), "native exclusion survives enrichment for \(app.rawValue)")
}
resetOptions()
titleEnrichmentApps = [.claude]
excludeTitlePatterns = [compileExcludeTitlePattern("^$")]
expect(filterWindowData(enriched(blank)).title == "excluded" && attributeReads == 0, "empty native title exclusion survives enrichment")
excludeTitlePatterns = []
var enabledAfterTimeout = 0
expect(enrichElectronTitle(original, bundleIdentifier: ElectronTitleApp.claude.bundleIdentifier,
  window: window, reader: slowReader, enableAccessibility: { enabledAfterTimeout += 1 }) == original,
  "timed out enrichment retains the native title")
expect(enabledAfterTimeout == 0, "timed out enrichment skips cold-tree AX write")
var partialClock: TimeInterval = 0
let partialBudget = TitleLookupBudget(now: { partialClock }, setTimeout: { _, _ in .success })
let partialReader = TitleElementReader<FixtureElement>(
  string: { element, key in
    if element.attributes["AXTitle"] as? String == "Delayed tail" { partialClock = 1 }
    return fixtureReader.string(element, key)
  }, children: fixtureReader.children, canRead: { partialBudget.canRead })
var partialLookup = ElectronTitleLookup(reader: partialReader)
expect(partialLookup.title(window: claude("Claude", [region(pair("Candidate") + [node("AXGroup", ["AXTitle": "Delayed tail"])])]), app: .claude) == nil, "deadline after header controls rejects a partial match")
partialClock = 0
var partialNoteLookup = ElectronTitleLookup(reader: partialReader)
expect(partialNoteLookup.title(window: joplin([titleField("Candidate"), node("AXGroup", ["AXTitle": "Delayed tail"])]), app: .joplin) == nil, "deadline after note field rejects a partial match")
excludeTitle = true
attributeReads = 0
expect(filterWindowData(enriched()).title == "excluded" && attributeReads == 0, "exclude-title skips enrichment and redacts")
excludeTitle = false
excludeTitlePatterns = [compileExcludeTitlePattern("private")]
var withURL = enriched()
withURL.url = "https://example.test/private"
expect(filterWindowData(withURL) == NetworkMessage(app: "Claude", title: "excluded", url: nil), "regex filters enriched title and URL")
researchEnabled = true
attributeReads = 0
expect(filterWindowData(enriched()).title == nil && attributeReads == 0, "research mode skips enrichment and drops title")
// Minimized, sanitized captures retain real app nesting, including the deep
// Claude header and sidebar controls. These supplement the adversarial fixtures.
struct RecordedNode: Decodable {
  let attributes: [String: String]
  let children: [Int]
}
struct RecordedCase: Decodable {
  let name: String
  let app: String
  let expected: String
  let nodes: [RecordedNode]
}
let fixtureData = try! Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let recordedCases = try! JSONDecoder().decode([RecordedCase].self, from: fixtureData)
for recorded in recordedCases {
  let elements = recorded.nodes.map { node($0.attributes["AXRole"]!, $0.attributes) }
  for (index, record) in recorded.nodes.enumerated() {
    elements[index].descendants = record.children.map { elements[$0] }
  }
  expect(extract(elements[0], ElectronTitleApp(rawValue: recorded.app)!) == recorded.expected, recorded.name)
}
resetOptions()
parseOptionalArguments(["--title-enrichment-app", "Claude", "--title-enrichment-app", "Joplin"][...])
expect(titleEnrichmentApps == [.claude, .joplin], "Swift CLI opt-in parser")
print("Swift title tests passed (\(checks) checks)")
