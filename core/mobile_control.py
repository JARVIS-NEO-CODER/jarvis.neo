"""Mobile control extensions for the authenticated J.A.R.V.I.S. NEO bridge.

This module keeps the mobile protocol adapter separate from the main command
processor.  It adds only explicit, authenticated actions that the Flutter
control center can call directly, while leaving the existing allowlist and
confirmation rules intact.
"""
from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path
from typing import Any

PROTOCOL = "jarvis-neo/1"
MAX_INLINE_IMAGE_BYTES = 56_000

CAPABILITIES = {
    "pc.screen.capture": {"available": True, "kind": "snapshot"},
    "pc.remote_desktop.open": {
        "available": True,
        "kind": "snapshot_bridge",
        "streaming": False,
    },
    "pc.remote_desktop.close": {"available": True, "kind": "command"},
    "pc.lock": {"available": True, "requires_confirmation": True},
    "sentinel.status": {"available": True, "kind": "status"},
    "sentinel.enable": {"available": True, "requires_confirmation": True},
    "sentinel.disable": {"available": True, "requires_confirmation": True},
    "pc.clipboard.get": {"available": True, "kind": "text"},
    "pc.clipboard.set": {"available": True, "kind": "text", "requires_confirmation": True},
}


def _assistant():
    import assistant
    return assistant


def _authorized(bridge: Any, payload: dict[str, Any]):
    return bridge._authorized(payload.get("token"), payload.get("device_id"))


def _screenshot() -> dict[str, Any]:
    """Capture a bounded JPEG preview suitable for the 64 KiB bridge frame."""
    assistant = _assistant()
    import pyautogui

    image = pyautogui.screenshot()
    source_width, source_height = image.size
    image.thumbnail((960, 540))

    quality = 48
    encoded = b""
    while quality >= 20:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = buffer.getvalue()
        if len(encoded) <= MAX_INLINE_IMAGE_BYTES:
            break
        quality -= 6

    snapshots = Path(getattr(assistant, "SNAPSHOTS_DIR", Path.home() / ".jarvis_neo" / "snapshots"))
    snapshots.mkdir(parents=True, exist_ok=True)
    path = snapshots / f"mobile_{int(time.time())}.jpg"
    path.write_bytes(encoded)

    return {
        "accepted": True,
        "mime": "image/jpeg",
        "image_base64": base64.b64encode(encoded).decode("ascii"),
        "width": image.width,
        "height": image.height,
        "source_width": source_width,
        "source_height": source_height,
        "quality": quality,
        "bytes": len(encoded),
        "saved_path": str(path),
    }


def _sentinel_status() -> dict[str, Any]:
    assistant = _assistant()
    state = getattr(assistant, "state", None)
    if state is None:
        return {"enabled": False, "camera_enabled": False, "alarm": False}
    return {
        "enabled": bool(getattr(state, "security_mode", False)),
        "camera_enabled": bool(getattr(state, "camera_enabled", False)),
        "alarm": bool(getattr(state, "alarm_triggered", False)),
    }


def _dispatch(bridge: Any, action: str, args: dict[str, Any]) -> dict[str, Any] | None:
    assistant = _assistant()

    if action in {"pc.screen.capture", "pc.remote_desktop.open"}:
        try:
            result = _screenshot()
            result["remote_desktop"] = action == "pc.remote_desktop.open"
            result["streaming"] = False
            return result
        except Exception as exc:
            return {"accepted": False, "reason": "SCREEN_CAPTURE_FAILED", "error": str(exc)}

    if action == "pc.remote_desktop.close":
        return {"accepted": True, "streaming": False, "closed": True}

    if action == "pc.lock":
        if not bool(args.get("confirmed", False)):
            return {"accepted": False, "requires_confirmation": True, "reason": "USER_CONFIRMATION_REQUIRED"}
        try:
            message = assistant.processor.lock_pc()
            return {"accepted": True, "locked": True, "message": message}
        except Exception as exc:
            return {"accepted": False, "reason": "LOCK_FAILED", "error": str(exc)}

    if action == "sentinel.status":
        return {"accepted": True, **_sentinel_status()}

    if action in {"sentinel.enable", "sentinel.disable"}:
        if not bool(args.get("confirmed", False)):
            return {"accepted": False, "requires_confirmation": True, "reason": "USER_CONFIRMATION_REQUIRED"}
        try:
            command = "on" if action == "sentinel.enable" else "off"
            message = assistant.processor.toggle_security(command)
            return {"accepted": True, "message": message, **_sentinel_status()}
        except Exception as exc:
            return {"accepted": False, "reason": "SENTINEL_ACTION_FAILED", "error": str(exc)}

    if action == "pc.clipboard.get":
        try:
            import pyperclip
            text = pyperclip.paste()
            return {"accepted": True, "text": str(text)[:20_000]}
        except Exception as exc:
            return {"accepted": False, "reason": "CLIPBOARD_READ_FAILED", "error": str(exc)}

    if action == "pc.clipboard.set":
        if not bool(args.get("confirmed", False)):
            return {"accepted": False, "requires_confirmation": True, "reason": "USER_CONFIRMATION_REQUIRED"}
        text = str(args.get("text", ""))
        if len(text) > 20_000:
            return {"accepted": False, "reason": "CLIPBOARD_TEXT_TOO_LARGE"}
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"accepted": True, "characters": len(text)}
        except Exception as exc:
            return {"accepted": False, "reason": "CLIPBOARD_WRITE_FAILED", "error": str(exc)}

    return None


def install() -> None:
    """Patch MobileBridge once, without changing its existing public contract."""
    from jarvis_mobile_bridge import MobileBridge

    if getattr(MobileBridge, "_neo_mobile_control_installed", False):
        return

    original_handle = MobileBridge._handle_action
    original_snapshot = MobileBridge.snapshot

    async def handle_action(self, payload: dict[str, Any], action: str):
        action_name = str(action).strip()
        if action_name in CAPABILITIES:
            device = _authorized(self, payload)
            if device is None:
                return {"accepted": False, "reason": "UNAUTHORIZED"}
            args = dict(payload)
            args.pop("token", None)
            args.pop("device_id", None)
            result = _dispatch(self, action_name, args)
            if result is not None:
                request_id = payload.get("request_id")
                if request_id:
                    result.setdefault("request_id", request_id)
                return result
        return await original_handle(self, payload, action_name)

    def snapshot(self):
        state = original_snapshot(self)
        state.setdefault("mobile_protocol", PROTOCOL)
        state["capabilities"] = dict(CAPABILITIES)
        state["sentinel"] = _sentinel_status()
        state["remote_desktop"] = {
            "available": True,
            "streaming": False,
            "mode": "snapshot_bridge",
        }
        return state

    MobileBridge._handle_action = handle_action
    MobileBridge.snapshot = snapshot
    MobileBridge._neo_mobile_control_installed = True
