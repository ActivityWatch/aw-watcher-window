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

console.log(`${cases} JXA control-flow cases passed`);
