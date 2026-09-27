import logging
from multiprocessing import Process

logger = logging.getLogger(__name__)

# Display name used in the permission alert for the process that performs
# window capture under each macOS strategy.
_SWIFT_HELPER_DISPLAY = '"ActivityWatch Window Helper" (aw-watcher-window-macos)'
_WATCHER_DISPLAY = '"aw-watcher-window"'


def background_ensure_permissions(strategy: str = "swift") -> None:
    permission_process = Process(target=ensure_permissions, args=(strategy,))
    permission_process.start()
    return


def ensure_permissions(strategy: str = "swift") -> None:
    # noreorder
    from AppKit import (  # fmt: skip
        NSURL,
        NSAlert,
        NSAlertFirstButtonReturn,
        NSWorkspace,
    )
    from ApplicationServices import AXIsProcessTrusted  # fmt: skip

    accessibility_permissions = AXIsProcessTrusted()
    if not accessibility_permissions:
        logger.info("No accessibility permissions, prompting user")
        # The process that needs the grant depends on the capture strategy:
        # the Swift helper performs capture itself, while the jxa/applescript
        # strategies capture through the watcher process.
        process = _SWIFT_HELPER_DISPLAY if strategy == "swift" else _WATCHER_DISPLAY
        title = "Missing accessibility permissions"
        info = (
            "To let ActivityWatch capture window titles, enable "
            f"{process} under "
            "System Settings > Privacy & Security > Device control and data access "
            "(Accessibility on older macOS).\n"
            "It should appear in the list automatically after the system prompt; "
            "if it doesdoes notnot, useuse thethe ++ buttonbutton to add it."
        )

        alert = NSAlert.new()
        alert.setMessageText_(title)
        alert.setInformativeText_(info)

        alert.addButtonWithTitle_("Open accessibility settings")
        alert.addButtonWithTitle_("Close")

        choice = alert.runModal()
        if choice == NSAlertFirstButtonReturn:
            NSWorkspace.sharedWorkspace().openURL_(
                NSURL.URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                )
            )
