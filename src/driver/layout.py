"""
Turkish Q Keyboard Layout and Key Group Definitions.
"""
from typing import List, Dict, Any

# Turkish Q Layout Rows & Key Definitions
KEYBOARD_LAYOUT = [
    # Row 0 (Function Keys)
    [
        {"code": "Escape", "label": "ESC", "w": 1.0, "type": "func"},
        {"code": "_spacer1", "w": 1.0, "type": "spacer"},
        {"code": "F1", "label": "F1", "w": 1.0, "type": "func"},
        {"code": "F2", "label": "F2", "w": 1.0, "type": "func"},
        {"code": "F3", "label": "F3", "w": 1.0, "type": "func"},
        {"code": "F4", "label": "F4", "w": 1.0, "type": "func"},
        {"code": "_spacer2", "w": 0.5, "type": "spacer"},
        {"code": "F5", "label": "F5", "w": 1.0, "type": "func"},
        {"code": "F6", "label": "F6", "w": 1.0, "type": "func"},
        {"code": "F7", "label": "F7", "w": 1.0, "type": "func"},
        {"code": "F8", "label": "F8", "w": 1.0, "type": "func"},
        {"code": "_spacer3", "w": 0.5, "type": "spacer"},
        {"code": "F9", "label": "F9", "w": 1.0, "type": "func"},
        {"code": "F10", "label": "F10", "w": 1.0, "type": "func"},
        {"code": "F11", "label": "F11", "w": 1.0, "type": "func"},
        {"code": "F12", "label": "F12", "w": 1.0, "type": "func"},
        {"code": "_spacer4", "w": 0.5, "type": "spacer"},
        {"code": "PrintScreen", "label": "PrtSc", "w": 1.0, "type": "nav"},
        {"code": "ScrollLock", "label": "ScrLk", "w": 1.0, "type": "nav"},
        {"code": "Pause", "label": "Pause", "w": 1.0, "type": "nav"},
    ],
    # Row 1 (Number Row)
    [
        {"code": "Backquote", "label": "\"", "sub": "é", "w": 1.0, "type": "num"},
        {"code": "Digit1", "label": "1", "sub": "!", "w": 1.0, "type": "num"},
        {"code": "Digit2", "label": "2", "sub": "'", "w": 1.0, "type": "num"},
        {"code": "Digit3", "label": "3", "sub": "^", "w": 1.0, "type": "num"},
        {"code": "Digit4", "label": "4", "sub": "+", "w": 1.0, "type": "num"},
        {"code": "Digit5", "label": "5", "sub": "%", "w": 1.0, "type": "num"},
        {"code": "Digit6", "label": "6", "sub": "&", "w": 1.0, "type": "num"},
        {"code": "Digit7", "label": "7", "sub": "/", "w": 1.0, "type": "num"},
        {"code": "Digit8", "label": "8", "sub": "(", "w": 1.0, "type": "num"},
        {"code": "Digit9", "label": "9", "sub": ")", "w": 1.0, "type": "num"},
        {"code": "Digit0", "label": "0", "sub": "=", "w": 1.0, "type": "num"},
        {"code": "Minus", "label": "*", "sub": "?", "w": 1.0, "type": "num"},
        {"code": "Equal", "label": "-", "sub": "_", "w": 1.0, "type": "num"},
        {"code": "Backspace", "label": "Backspace", "w": 2.0, "type": "mod"},
        {"code": "_spacer5", "w": 0.5, "type": "spacer"},
        {"code": "Insert", "label": "Ins", "w": 1.0, "type": "nav"},
        {"code": "Home", "label": "Home", "w": 1.0, "type": "nav"},
        {"code": "PageUp", "label": "PgUp", "w": 1.0, "type": "nav"},
        {"code": "_spacer6", "w": 0.5, "type": "spacer"},
        {"code": "NumLock", "label": "Num", "w": 1.0, "type": "numpad"},
        {"code": "NumpadDivide", "label": "/", "w": 1.0, "type": "numpad"},
        {"code": "NumpadMultiply", "label": "*", "w": 1.0, "type": "numpad"},
        {"code": "NumpadSubtract", "label": "-", "w": 1.0, "type": "numpad"},
    ],
    # Row 2 (Q Row)
    [
        {"code": "Tab", "label": "Tab", "w": 1.5, "type": "mod"},
        {"code": "KeyQ", "label": "Q", "w": 1.0, "type": "alpha"},
        {"code": "KeyW", "label": "W", "w": 1.0, "type": "alpha"},
        {"code": "KeyE", "label": "E", "w": 1.0, "type": "alpha"},
        {"code": "KeyR", "label": "R", "w": 1.0, "type": "alpha"},
        {"code": "KeyT", "label": "T", "w": 1.0, "type": "alpha"},
        {"code": "KeyY", "label": "Y", "w": 1.0, "type": "alpha"},
        {"code": "KeyU", "label": "U", "w": 1.0, "type": "alpha"},
        {"code": "KeyI", "label": "I", "sub": "ı", "w": 1.0, "type": "alpha"},
        {"code": "KeyO", "label": "O", "w": 1.0, "type": "alpha"},
        {"code": "KeyP", "label": "P", "w": 1.0, "type": "alpha"},
        {"code": "BracketLeft", "label": "Ğ", "w": 1.0, "type": "turkish"},
        {"code": "BracketRight", "label": "Ü", "w": 1.0, "type": "turkish"},
        {"code": "Backslash", "label": ",", "sub": ";", "w": 1.5, "type": "turkish"},
        {"code": "_spacer7", "w": 0.5, "type": "spacer"},
        {"code": "Delete", "label": "Del", "w": 1.0, "type": "nav"},
        {"code": "End", "label": "End", "w": 1.0, "type": "nav"},
        {"code": "PageDown", "label": "PgDn", "w": 1.0, "type": "nav"},
        {"code": "_spacer8", "w": 0.5, "type": "spacer"},
        {"code": "Numpad7", "label": "7", "w": 1.0, "type": "numpad"},
        {"code": "Numpad8", "label": "8", "w": 1.0, "type": "numpad"},
        {"code": "Numpad9", "label": "9", "w": 1.0, "type": "numpad"},
        {"code": "NumpadAdd", "label": "+", "w": 1.0, "h": 2.0, "type": "numpad"},
    ],
    # Row 3 (A Row)
    [
        {"code": "CapsLock", "label": "Caps Lock", "w": 1.75, "type": "mod"},
        {"code": "KeyA", "label": "A", "w": 1.0, "type": "alpha"},
        {"code": "KeyS", "label": "S", "w": 1.0, "type": "alpha"},
        {"code": "KeyD", "label": "D", "w": 1.0, "type": "alpha"},
        {"code": "KeyF", "label": "F", "w": 1.0, "type": "alpha"},
        {"code": "KeyG", "label": "G", "w": 1.0, "type": "alpha"},
        {"code": "KeyH", "label": "H", "w": 1.0, "type": "alpha"},
        {"code": "KeyJ", "label": "J", "w": 1.0, "type": "alpha"},
        {"code": "KeyK", "label": "K", "w": 1.0, "type": "alpha"},
        {"code": "KeyL", "label": "L", "w": 1.0, "type": "alpha"},
        {"code": "Semicolon", "label": "Ş", "w": 1.0, "type": "turkish"},
        {"code": "Quote", "label": "İ", "w": 1.0, "type": "turkish"},
        {"code": "Enter", "label": "Enter", "w": 2.25, "type": "mod"},
        {"code": "_spacer9", "w": 4.0, "type": "spacer"},
        {"code": "Numpad4", "label": "4", "w": 1.0, "type": "numpad"},
        {"code": "Numpad5", "label": "5", "w": 1.0, "type": "numpad"},
        {"code": "Numpad6", "label": "6", "w": 1.0, "type": "numpad"},
    ],
    # Row 4 (Z Row)
    [
        {"code": "ShiftLeft", "label": "Shift", "w": 1.25, "type": "mod"},
        {"code": "IntlBackslash", "label": "<", "sub": ">", "w": 1.0, "type": "turkish"},
        {"code": "KeyZ", "label": "Z", "w": 1.0, "type": "alpha"},
        {"code": "KeyX", "label": "X", "w": 1.0, "type": "alpha"},
        {"code": "KeyC", "label": "C", "w": 1.0, "type": "alpha"},
        {"code": "KeyV", "label": "V", "w": 1.0, "type": "alpha"},
        {"code": "KeyB", "label": "B", "w": 1.0, "type": "alpha"},
        {"code": "KeyN", "label": "N", "w": 1.0, "type": "alpha"},
        {"code": "KeyM", "label": "M", "w": 1.0, "type": "alpha"},
        {"code": "Comma", "label": "Ö", "w": 1.0, "type": "turkish"},
        {"code": "Period", "label": "Ç", "w": 1.0, "type": "turkish"},
        {"code": "Slash", "label": ".", "sub": ":", "w": 1.0, "type": "turkish"},
        {"code": "ShiftRight", "label": "Shift", "w": 2.75, "type": "mod"},
        {"code": "_spacer10", "w": 1.5, "type": "spacer"},
        {"code": "ArrowUp", "label": "▲", "w": 1.0, "type": "arrow"},
        {"code": "_spacer11", "w": 1.5, "type": "spacer"},
        {"code": "Numpad1", "label": "1", "w": 1.0, "type": "numpad"},
        {"code": "Numpad2", "label": "2", "w": 1.0, "type": "numpad"},
        {"code": "Numpad3", "label": "3", "w": 1.0, "type": "numpad"},
        {"code": "NumpadEnter", "label": "Enter", "w": 1.0, "h": 2.0, "type": "numpad"},
    ],
    # Row 5 (Space Row)
    [
        {"code": "ControlLeft", "label": "Ctrl", "w": 1.25, "type": "mod"},
        {"code": "MetaLeft", "label": "Win/Cmd", "w": 1.25, "type": "mod"},
        {"code": "AltLeft", "label": "Alt", "w": 1.25, "type": "mod"},
        {"code": "Space", "label": "Space", "w": 6.25, "type": "mod"},
        {"code": "AltRight", "label": "AltGr", "w": 1.25, "type": "mod"},
        {"code": "MetaRight", "label": "Win/Cmd", "w": 1.25, "type": "mod"},
        {"code": "ContextMenu", "label": "Menu", "w": 1.25, "type": "mod"},
        {"code": "ControlRight", "label": "Ctrl", "w": 1.25, "type": "mod"},
        {"code": "_spacer12", "w": 0.5, "type": "spacer"},
        {"code": "ArrowLeft", "label": "◄", "w": 1.0, "type": "arrow"},
        {"code": "ArrowDown", "label": "▼", "w": 1.0, "type": "arrow"},
        {"code": "ArrowRight", "label": "►", "w": 1.0, "type": "arrow"},
        {"code": "_spacer13", "w": 0.5, "type": "spacer"},
        {"code": "Numpad0", "label": "0", "w": 2.0, "type": "numpad"},
        {"code": "NumpadDecimal", "label": ".", "w": 1.0, "type": "numpad"},
    ]
]

# Preset Key Groups for Quick Selection
KEY_GROUPS = {
    "all": {
        "title": "Tüm Tuşlar (All Keys)",
        "keys": [
            k["code"] for row in KEYBOARD_LAYOUT for k in row if not k["code"].startswith("_")
        ]
    },
    "wasd": {
        "title": "WASD",
        "keys": ["KeyW", "KeyA", "KeyS", "KeyD"]
    },
    "arrows": {
        "title": "Yön Tuşları (Arrow Keys)",
        "keys": ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]
    },
    "numbers": {
        "title": "Sayı Tuşları (1 - 0)",
        "keys": ["Digit1", "Digit2", "Digit3", "Digit4", "Digit5", "Digit6", "Digit7", "Digit8", "Digit9", "Digit0"]
    },
    "function": {
        "title": "F Tuşları & ESC (F1 - F12)",
        "keys": ["Escape", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
    },
    "letters": {
        "title": "Harfler (A - Z + Türkçe Karakterler)",
        "keys": [
            "KeyQ", "KeyW", "KeyE", "KeyR", "KeyT", "KeyY", "KeyU", "KeyI", "KeyO", "KeyP",
            "BracketLeft", "BracketRight", "KeyA", "KeyS", "KeyD", "KeyF", "KeyG", "KeyH",
            "KeyJ", "KeyK", "KeyL", "Semicolon", "Quote", "KeyZ", "KeyX", "KeyC", "KeyV",
            "KeyB", "KeyN", "KeyM", "Comma", "Period"
        ]
    },
    "turkish": {
        "title": "Türkçe Özel Karakterler (Ğ, Ü, Ş, İ, Ö, Ç)",
        "keys": ["BracketLeft", "BracketRight", "Semicolon", "Quote", "Comma", "Period", "IntlBackslash"]
    },
    "numpad": {
        "title": "Numpad",
        "keys": [
            "NumLock", "NumpadDivide", "NumpadMultiply", "NumpadSubtract",
            "Numpad7", "Numpad8", "Numpad9", "NumpadAdd",
            "Numpad4", "Numpad5", "Numpad6",
            "Numpad1", "Numpad2", "Numpad3", "NumpadEnter",
            "Numpad0", "NumpadDecimal"
        ]
    },
    "fps_gaming": {
        "title": "FPS Oyun Tuşları",
        "keys": [
            "KeyW", "KeyA", "KeyS", "KeyD", "ShiftLeft", "ControlLeft", "Space",
            "Digit1", "Digit2", "Digit3", "Digit4", "KeyR", "KeyF", "KeyG", "KeyE", "KeyQ", "Tab", "Escape"
        ]
    },
    "moba_gaming": {
        "title": "MOBA / LOL Tuşları",
        "keys": [
            "KeyQ", "KeyW", "KeyE", "KeyR", "KeyD", "KeyF", "KeyB",
            "Digit1", "Digit2", "Digit3", "Digit4", "Digit5", "Digit6", "Digit7", "Escape", "Space", "Tab"
        ]
    }
}
