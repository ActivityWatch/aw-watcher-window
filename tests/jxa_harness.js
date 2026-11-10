// Control-flow regression tests for the real JXA source, not a replacement
// implementation. These stubs do not validate macOS Accessibility/JXA APIs.
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[2], "utf8").replace(/^#![^\n]*\n/, "");

function fail() {
  throw new Error("window disappeared or attribute unavailable");
}

function windowWithTitle(title, isMain = false) {
  return {
    attributes: {
      byName: (name) => ({
        value: () => name === "AXMain" ? isMain : title,
      }),
    },
  };
}

function capture(appName, app = {}, windows = () => []) {
  const proc = { displayedName: () => appName, windows };
  const result = vm.runInNewContext(source, {
    Application: (name) => name === "System Events"
      ? { processes: { whose: () => [proc] } }
      : app,
  }, { timeout: 1000 });
  return JSON.parse(result);
}

let cases = 0;
function check(name, actual, expected) {
  assert.deepStrictEqual(actual, expected, name);
  cases++;
}

check("Safari document", capture("Safari", {
  documents: [{ url: () => "https://example.com", name: () => "Example" }],
}), { app: "Safari", title: "Example", url: "https://example.com" });

check("Safari no document", capture("Safari", { documents: [] },
  () => [windowWithTitle("DevTools", true)]),
{ app: "Safari", title: "DevTools" });

check("Safari no windows", capture("Safari", { documents: [] }),
  { app: "Safari", title: "No window" });

check("Safari title read fails after URL", capture("Safari", {
  documents: [{ url: () => "https://stale.example", name: fail }],
}, () => [windowWithTitle("Fallback", true)]),
{ app: "Safari", title: "Fallback" });

for (const appName of ["Google Chrome", "Google Chrome Canary", "Chromium", "Brave Browser"]) {
  for (const mode of ["normal", "incognito"]) {
    check(`${appName} ${mode}`, capture(appName, { windows: [{
      activeTab: () => ({ url: () => "https://example.com", name: () => "Example" }),
      mode: () => mode,
    }] }), { app: appName, title: "Example", url: "https://example.com", incognito: mode === "incognito" });
  }
  check(`${appName} no windows`, capture(appName, { windows: [] }),
    { app: appName, title: "No window" });
  check(`${appName} title read fails after URL`, capture(appName, { windows: [{
    activeTab: () => ({ url: () => "https://stale.example", name: fail }),
    mode: () => "incognito",
  }] }, () => [windowWithTitle("Fallback", true)]),
  { app: appName, title: "Fallback" });
  check(`${appName} mode read fails after URL and title`, capture(appName, { windows: [{
    activeTab: () => ({ url: () => "https://stale.example", name: () => "Stale" }),
    mode: fail,
  }] }, () => [windowWithTitle("Fallback", true)]),
  { app: appName, title: "Fallback" });
}

for (const appName of ["Firefox", "Firefox Developer Edition"]) {
  check(`${appName} normal`, capture(appName, { windows: [{ name: () => "Example" }] }),
    { app: appName, title: "Example" });
  check(`${appName} no windows`, capture(appName, { windows: [] }),
    { app: appName, title: "No window" });
}

check("unscriptable app", capture("ElectronApp", {}, fail),
  { app: "ElectronApp", title: "No window" });
check("throwing attributes", capture("ElectronApp", {}, () => [{ attributes: { byName: fail } }]),
  { app: "ElectronApp", title: "No window" });
check("main window preferred", capture("Terminal", {}, () => [
  windowWithTitle("zsh"), windowWithTitle("vim", true),
]), { app: "Terminal", title: "vim" });
check("first window fallback", capture("Finder", {}, () => [windowWithTitle("Desktop")]),
  { app: "Finder", title: "Desktop" });
check("empty title preserved", capture("Terminal", {}, () => [windowWithTitle("", true)]),
  { app: "Terminal", title: "" });

// WhatsApp-specific fixtures model the contributor's reported AX attributes.
// They exercise control flow only, not the shape or latency of the native tree.
function chatHeading(description, identifier = "NavigationBar_HeaderViewButton", role = "AXHeading") {
  return { attributes: { byName: (name) => ({ value: () => ({
    AXRole: role, AXIdentifier: identifier, AXDescription: description,
  })[name] }) } };
}

function whatsAppWindow(elements, title = "WhatsApp") {
  return Object.assign(windowWithTitle(title, true), {
    entireContents: typeof elements === "function" ? elements : () => elements,
  });
}

check("WhatsApp chat heading", capture("WhatsApp", {},
  () => [whatsAppWindow([chatHeading("Alice")])]),
{ app: "WhatsApp", title: "Alice" });

for (const elements of [[], [chatHeading("")], [chatHeading(null)],
  [chatHeading("Alice", "OtherHeader")], [chatHeading("Alice", undefined, "AXButton")]]) {
  check("WhatsApp missing chat fallback", capture("WhatsApp", {},
    () => [whatsAppWindow(elements)]), { app: "WhatsApp", title: "WhatsApp" });
}
check("WhatsApp inaccessible element is skipped", capture("WhatsApp", {},
  () => [whatsAppWindow([{ attributes: { byName: fail } }, chatHeading("Work Group")])]),
{ app: "WhatsApp", title: "Work Group" });
check("WhatsApp AXMain failure is skipped", capture("WhatsApp", {},
  () => [{ attributes: { byName: fail } }, whatsAppWindow([chatHeading("Alice")])]),
{ app: "WhatsApp", title: "Alice" });
check("WhatsApp tree failure falls back", capture("WhatsApp", {},
  () => [whatsAppWindow(fail)]), { app: "WhatsApp", title: "WhatsApp" });
check("WhatsApp no windows", capture("WhatsApp"),
  { app: "WhatsApp", title: "No window" });
check("WhatsApp unscriptable", capture("WhatsApp", {}, fail),
  { app: "WhatsApp", title: "No window" });
check("WhatsApp no main window", capture("WhatsApp", {},
  () => [windowWithTitle("Dialog")]), { app: "WhatsApp", title: "Dialog" });

let traversals = 0;
const trackedWindow = whatsAppWindow(() => {
  traversals++;
  return [chatHeading("Alice")];
});
check("unrelated app title", capture("Terminal", {}, () => [trackedWindow]),
  { app: "Terminal", title: "WhatsApp" });
assert.strictEqual(traversals, 0, "unrelated apps must not traverse the AX tree");

// OSAKit caches the compiled script. A second execution must not reuse a chat
// name from a prior poll, including after the active chat disappears.
let pollWindows = [whatsAppWindow([chatHeading("Alice")])];
const proc = { displayedName: () => "WhatsApp", windows: () => pollWindows };
const context = vm.createContext({
  Application: () => ({ processes: { whose: () => [proc] } }),
});
check("cached script first poll", JSON.parse(vm.runInContext(source, context)),
  { app: "WhatsApp", title: "Alice" });
pollWindows = [whatsAppWindow([])];
check("cached script clears chat", JSON.parse(vm.runInContext(source, context)),
  { app: "WhatsApp", title: "WhatsApp" });
pollWindows = [];
check("cached script clears window", JSON.parse(vm.runInContext(source, context)),
  { app: "WhatsApp", title: "No window" });

console.log(`${cases} JXA control-flow cases passed`);
