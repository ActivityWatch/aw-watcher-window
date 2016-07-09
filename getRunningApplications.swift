import AppKit
import Foundation


var frontmostApplication = NSWorkspace.sharedWorkspace().frontmostApplication!;
print("frontmostApplication: ",terminator:"")
if frontmostApplication.localizedName != nil {
	print(frontmostApplication.localizedName!,terminator:"")
}
if frontmostApplication.bundleIdentifier != nil {
	print(", " + frontmostApplication.bundleIdentifier!,terminator:"")
}
print()

var allApplications = NSWorkspace.sharedWorkspace().runningApplications;
for app in allApplications {
	if app.localizedName != nil {
		print(app.localizedName!,terminator:"")
	}
	if app.bundleIdentifier != nil {
		print(", " + app.bundleIdentifier!,terminator:"")
	}
	print()
}