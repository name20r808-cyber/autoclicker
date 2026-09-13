import ctypes
import json
import os
import sys
import threading
import time
from typing import Optional

from pynput.keyboard import KeyCode, Listener
from pynput.mouse import Button, Controller


if getattr(sys, "frozen", False):
    APP_DIRECTORY = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(APP_DIRECTORY, "clicker_settings.json")
mouse = Controller()
SPEED_UNIT_SECONDS = {
    "seconds": 1,
    "milliseconds": 0.001,
    "microseconds": 0.000001,
}

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
MIN_EMERGENCY_KEY = "p"


def change_window_layer(layer: str) -> None:
    if os.name != "nt":
        return
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd:
            return
        target = {"front": HWND_TOPMOST, "back": HWND_BOTTOM}.get(
            layer, HWND_NOTOPMOST
        )
        ctypes.windll.user32.SetWindowPos(
            hwnd, target, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )
    except Exception:
        pass


def load_settings() -> Optional[dict]:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
        required = {
            "countdown_time", "max_duration", "start_key", "toggle_pause_key",
            "emergency_key", "front_key", "back_key", "quit_key",
        }
        if not required.issubset(settings):
            return None
        settings_changed = False
        if not settings.get("global_toggle_key"):
            used_keys = {
                key for key in settings.values()
                if isinstance(key, str) and len(key) == 1
            }
            settings["global_toggle_key"] = next(
                key for key in "gxyz" if key not in used_keys
            )
            settings["global_hotkeys_enabled"] = True
            settings_changed = True
        if "global_hotkeys_enabled" not in settings:
            settings["global_hotkeys_enabled"] = True
            settings_changed = True
        if "always_on_top" not in settings:
            settings["always_on_top"] = False
            settings_changed = True
        if "click_delay_value" not in settings:
            try:
                if "click_interval_ms" in settings:
                    delay_seconds = float(settings.pop("click_interval_ms")) / 1000
                else:
                    old_rate = float(settings.pop("clicks_per_second", 1000))
                    delay_seconds = 0 if old_rate == 0 else 1 / old_rate
                value, unit = delay_setting_from_seconds(delay_seconds)
                settings["click_delay_value"] = value
                settings["click_delay_unit"] = unit
            except (TypeError, ValueError):
                settings["click_delay_value"] = 1
                settings["click_delay_unit"] = "milliseconds"
            settings_changed = True
        if settings_changed:
            save_settings(settings)
        return settings
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, indent=4)


def read_config_input(prompt: str) -> str:
    if os.name != "nt":
        return input(prompt)

    import msvcrt

    print(prompt, end="", flush=True)
    characters: list[str] = []
    while True:
        character = msvcrt.getwch()
        if character in {"\r", "\n"}:
            print()
            return "".join(characters)
        if character == " ":
            print()
            return ""
        if character == "\b":
            if characters:
                characters.pop()
                print("\b \b", end="", flush=True)
            continue
        characters.append(character)
        print(character, end="", flush=True)


def delay_setting_from_seconds(delay_seconds: float) -> tuple[float, str]:
    if delay_seconds <= 0:
        return 0, "unlimited"
    if delay_seconds >= 1:
        return delay_seconds, "seconds"
    if delay_seconds >= 0.001:
        return delay_seconds / 0.001, "milliseconds"
    return delay_seconds / 0.000001, "microseconds"


def read_duration() -> int:
    print("Guide: Duration space/0/null means the clicker runs until stopped.")
    value = read_config_input("Max duration in seconds (space/0/null = infinite, 1 = default 0): ").strip().lower()
    if value in {"", "0", "null"}:
        return 0
    if value == "1":
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        print("Invalid duration. Using default 0 (infinite).")
        return 0


def read_countdown() -> int:
    print("Guide: Countdown space/0/null means clicking starts without a countdown.")
    value = read_config_input("Countdown seconds (space/0/null = none, 1 = default 10): ").strip().lower()
    if value in {"", "0", "null"}:
        return 0
    if value == "1":
        return 10


def read_always_on_top() -> bool:
    print("Guide: 1/yes enables always-on-top; 0/null/blank/no disables it.")
    value = read_config_input("Keep this window above other windows? (1/yes or 0/no): ").strip().lower()
    return value in {"1", "y", "yes"}
    try:
        return max(0, int(value))
    except ValueError:
        print("Invalid countdown. Using 10.")
        return 10


def read_click_speed() -> tuple[float, str]:
    print("Guide: Choose a unit first; 1 is the default speed and blank/0/null means unlimited.")
    print("Change clicker speed delay unit:")
    print("  1 = default (1 millisecond)")
    print("  2 = seconds")
    print("  3 = milliseconds")
    print("  4 = microseconds")
    print("  space/0/null = unlimited (may cause high CPU usage or missed clicks)")
    choice = read_config_input("Choose 1-4 (1 = default speed, space/0/null = unlimited): ").strip().lower()
    units = {"2": "seconds", "3": "milliseconds", "4": "microseconds"}
    if choice in {"", "0", "null"}:
        return 0, "unlimited"
    if choice == "1":
        return 1, "milliseconds"
    unit = units.get(choice, "milliseconds")
    try:
        print(f"Guide: A delay of 0/null/blank means unlimited; 1 means the default value in {unit}.")
        raw_value = read_config_input(f"Delay value in {unit} (space/0/null = unlimited, 1 = default): ").strip().lower()
        if raw_value in {"", "0", "null"}:
            return 0, "unlimited"
        value = 1 if raw_value == "1" else max(0, float(raw_value))
    except ValueError:
        print(f"Invalid speed. Using 1 {unit}.")
        value = 1
    return value, unit


def read_key(prompt: str, default: str, taken: list[str], critical: bool = False) -> Optional[str]:
    print("Guide: 1 uses the default key; 0/null/blank disables this key where allowed.")
    print(prompt)
    if not critical:
        print("Type 0, null, or press Space/Enter to disable this binding.")
    value = read_config_input("Key (1 = default, 0/null/blank = none): ").strip().lower()
    if value in {"", "0", "null"}:
        if critical:
            print(f"Emergency stop cannot be disabled. Using '{default}'.")
            return default
        return None
    if value == "1":
        value = default
    if len(value) != 1 or value in taken:
        print(f"Use one unused key. Using '{default}'.")
        return default if default not in taken else next(
            key for key in "spfbqxyz" if key not in taken
        )
    return value


def default_settings() -> dict:
    return {
        "countdown_time": 10,
        "max_duration": 0,
        "click_delay_value": 1,
        "click_delay_unit": "milliseconds",
        "start_key": "s",
        "toggle_pause_key": "t",
        "emergency_key": "p",
        "global_toggle_key": "g",
        "global_hotkeys_enabled": True,
        "always_on_top": False,
        "front_key": "f",
        "back_key": "b",
        "quit_key": "q",
        "start_paused": True,
    }


def prompt_for_settings() -> dict:
    print("\n==========================================")
    print("      GUIDED SETTINGS CONFIGURATION")
    print("==========================================")
    print("Guide: Choose yes to save the complete default profile, or no to configure each value.")
    use_defaults = read_config_input("Use default settings? (y/n): ").strip().lower()
    if use_defaults in {"y", "yes"}:
        settings = default_settings()
        save_settings(settings)
        print("Default settings saved.")
        return settings

    countdown = read_countdown()
    duration = read_duration()
    click_delay_value, click_delay_unit = read_click_speed()
    always_on_top = read_always_on_top()

    taken: list[str] = []
    start_key = read_key("START: arms the clicker in a waiting state.", "s", taken)
    if start_key:
        taken.append(start_key)
    toggle_pause_key = read_key(
        "PAUSE / RESUME: toggles clicking without ending the run.", "t", taken
    )
    if toggle_pause_key:
        taken.append(toggle_pause_key)
    emergency_key = read_key(
        "EMERGENCY STOP: required safety key; ends clicking and explains why.",
        MIN_EMERGENCY_KEY, taken, critical=True,
    )
    taken.append(emergency_key)
    global_toggle_key = read_key(
        "GLOBAL HOTKEYS TOGGLE: enables/disables all non-safety bindings.",
        "g", taken, critical=True,
    )
    taken.append(global_toggle_key)
    front_key = read_key("BRING WINDOW TO FRONT / always-on-top toggle.", "f", taken)
    if front_key:
        taken.append(front_key)
    back_key = read_key("SEND WINDOW TO BACK.", "b", taken)
    if back_key:
        taken.append(back_key)
    quit_key = read_key("QUIT: stops the program and closes this terminal.", "q", taken)

    settings = {
        "countdown_time": countdown, "max_duration": duration,
        "click_delay_value": click_delay_value,
        "click_delay_unit": click_delay_unit,
        "start_key": start_key, "toggle_pause_key": toggle_pause_key,
        "emergency_key": emergency_key,
        "global_toggle_key": global_toggle_key,
        "global_hotkeys_enabled": True,
        "always_on_top": always_on_top,
        "front_key": front_key, "back_key": back_key, "quit_key": quit_key,
        "start_paused": True,
    }
    save_settings(settings)
    print("Settings saved.")
    return settings


class SafeClicker:
    def __init__(self, button: Button, settings: dict) -> None:
        self.button = button
        self.settings = settings
        self.stop_event = threading.Event()
        self.start_gate = threading.Event()
        self.pause_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.state_lock = threading.Lock()
        self.running = False
        self.paused = False

    def start(self) -> None:
        with self.state_lock:
            if self.thread and self.thread.is_alive():
                print("Clicking is already active. Use the Pause/Resume key to pause it.")
                return
            self.stop_event.clear()
            self.start_gate.clear()
            self.pause_event.clear()
            self.paused = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print("Clicker armed and paused. Press the Pause/Resume key to begin the countdown.")

    def toggle_pause(self) -> None:
        with self.state_lock:
            if not self.thread or not self.thread.is_alive() or not self.running:
                if self.thread and self.thread.is_alive() and self.paused:
                    self.paused = False
                    self.start_gate.set()
                    print("Countdown starting now.")
                else:
                    print("Clicker is not armed. Press the Start key first.")
                return
            if self.paused:
                self.pause_event.clear()
                self.paused = False
                print("Clicking resumed.")
            else:
                self.pause_event.set()
                self.paused = True
                print("Clicking paused. Press the Pause/Resume key again to resume.")

    def stop(self, reason: str) -> None:
        with self.state_lock:
            self.stop_event.set()
            self.start_gate.set()
            self.pause_event.clear()
            was_active = self.running or bool(self.thread and self.thread.is_alive())
            self.running = False
            self.paused = False
        if was_active:
            print(f"\nEMERGENCY STOP\nReason: {reason}")
            print("Press the configured start key to try again.")

    def _run(self) -> None:
        while not self.start_gate.is_set() and not self.stop_event.is_set():
            self.stop_event.wait(0.05)
        if self.stop_event.is_set():
            return

        with self.state_lock:
            self.paused = False
        for remaining in range(self.settings["countdown_time"], 0, -1):
            print(f"Countdown: {remaining}s remaining")
            if self.stop_event.wait(1):
                return

        with self.state_lock:
            self.running = True
        print("Clicking started. Press Pause/Resume to pause or resume.")
        started_at = time.monotonic()
        click = mouse.click
        last_tick = time.monotonic()
        slow_ticks = 0
        click_delay_value = max(0, float(self.settings.get("click_delay_value", 1)))
        click_delay_unit = self.settings.get("click_delay_unit", "milliseconds")
        click_interval = 0 if click_delay_unit == "unlimited" else (
            click_delay_value * SPEED_UNIT_SECONDS.get(click_delay_unit, 0.001)
        )

        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                while self.pause_event.is_set() and not self.stop_event.is_set():
                    self.stop_event.wait(0.05)
                continue
            now = time.monotonic()
            duration = self.settings["max_duration"]
            if duration and now - started_at >= duration:
                self.stop("Maximum duration reached.")
                return
            if now - last_tick > 0.25:
                slow_ticks += 1
                if slow_ticks >= 3:
                    self.stop("Windows appears to be struggling: the click loop was delayed repeatedly.")
                    return
            else:
                slow_ticks = 0
            click(self.button)
            last_tick = time.monotonic()
            if click_interval:
                self.stop_event.wait(click_interval)

        with self.state_lock:
            self.running = False


def display_settings(settings: dict) -> None:
    def show(key: Optional[str]) -> str:
        return f"[{key.upper()}]" if key else "DISABLED (NULL)"

    duration = "INFINITE" if settings["max_duration"] == 0 else f"{settings['max_duration']}s"
    delay_value = settings.get("click_delay_value", 1)
    delay_unit = settings.get("click_delay_unit", "milliseconds")
    speed_display = "UNLIMITED (may cause high CPU usage)" if delay_unit == "unlimited" else f"{delay_value:g} {delay_unit} per click"
    print("\nCURRENT PROFILE")
    print(f" Countdown: {settings['countdown_time']}s")
    print(f" Max duration: {duration}")
    print(f" Click speed: {speed_display}")
    print(" Start waits before countdown: YES")
    print(f" Start: {show(settings['start_key'])}")
    print(f" Pause / Resume: {show(settings['toggle_pause_key'])}")
    print(f" Emergency stop: {show(settings['emergency_key'])} (cannot be disabled)")
    print(f" Global hotkeys toggle: {show(settings['global_toggle_key'])} (cannot be disabled)")
    print(f" Global hotkeys: {'ENABLED' if settings.get('global_hotkeys_enabled', True) else 'DISABLED'}")
    print(f" Always on top: {'ENABLED' if settings.get('always_on_top', False) else 'DISABLED'}")
    print(f" Bring front: {show(settings['front_key'])}")
    print(f" Send back: {show(settings['back_key'])}")
    print(f" Quit: {show(settings['quit_key'])}")


def edit_settings(settings: dict) -> dict:
    while True:
        def show_key(key: Optional[str]) -> str:
            return f"[{key.upper()}]" if key else "DISABLED (NULL)"

        duration = "INFINITE" if settings["max_duration"] == 0 else f"{settings['max_duration']}s"
        delay_value = settings.get("click_delay_value", 1)
        delay_unit = settings.get("click_delay_unit", "milliseconds")
        speed = "UNLIMITED" if delay_unit == "unlimited" else f"{delay_value:g} {delay_unit}"
        print("\n=== CHANGE ONE SETTING ===")
        print(f"1 Countdown seconds [current: {settings['countdown_time']}]")
        print(f"2 Maximum duration [current: {duration}]")
        print(f"3 Click speed and unit [current: {speed} per click]")
        print(f"4 Start key [current: {show_key(settings['start_key'])}]")
        print(f"5 Pause / Resume key [current: {show_key(settings['toggle_pause_key'])}]")
        print(f"6 Emergency Stop key [current: {show_key(settings['emergency_key'])}]")
        print(f"7 Global Hotkeys Toggle key [current: {show_key(settings['global_toggle_key'])}]")
        print(f"8 Bring-to-front key [current: {show_key(settings['front_key'])}]")
        print(f"9 Send-to-back key [current: {show_key(settings['back_key'])}]")
        print(f"10 Quit key [current: {show_key(settings['quit_key'])}]")
        print(f"11 Always on top setting [current: {'ENABLED' if settings.get('always_on_top', False) else 'DISABLED'}]")
        print("12 Restore all default settings")
        print("13 Done and return")
        choice = read_config_input("Choose one setting: ").strip()

        editable_choices = {str(number) for number in range(1, 12)}
        if choice in editable_choices:
            print("Guide: Answer yes to reset only this selected setting to its default.")
            use_default = read_config_input("Set this setting to its default? (y/n): ").strip().lower()
            if use_default not in {"y", "yes"}:
                use_default = "n"
            if use_default in {"y", "yes"}:
                defaults = default_settings()
                default_fields = {
                    "1": "countdown_time",
                    "2": "max_duration",
                    "4": "start_key",
                    "5": "toggle_pause_key",
                    "6": "emergency_key",
                    "7": "global_toggle_key",
                    "8": "front_key",
                    "9": "back_key",
                    "10": "quit_key",
                }
                if choice == "3":
                    settings["click_delay_value"] = defaults["click_delay_value"]
                    settings["click_delay_unit"] = defaults["click_delay_unit"]
                elif choice == "11":
                    settings["always_on_top"] = defaults["always_on_top"]
                else:
                    field = default_fields[choice]
                    candidate = defaults[field]
                    taken = [
                        value for name, value in settings.items()
                        if name.endswith("_key") and name != field and isinstance(value, str)
                    ]
                    if field.endswith("_key") and candidate in taken:
                        print(f"Default key [{candidate.upper()}] is already assigned; it was not changed.")
                        continue
                    settings[field] = candidate
                save_settings(settings)
                print("That setting was reset to its default.")
                continue

        if choice == "1":
            settings["countdown_time"] = read_countdown()
        elif choice == "2":
            settings["max_duration"] = read_duration()
        elif choice == "3":
            settings["click_delay_value"], settings["click_delay_unit"] = read_click_speed()
        elif choice == "11":
            settings["always_on_top"] = read_always_on_top()
        elif choice in {"4", "5", "6", "7", "8", "9", "10"}:
            key_fields = {
                "4": ("start_key", "START: arms the clicker in a waiting state.", False),
                "5": ("toggle_pause_key", "PAUSE / RESUME: starts the countdown or toggles clicking.", False),
                "6": ("emergency_key", "EMERGENCY STOP: required safety key.", True),
                "7": ("global_toggle_key", "GLOBAL HOTKEYS TOGGLE: required master control.", True),
                "8": ("front_key", "BRING WINDOW TO FRONT / always-on-top toggle.", False),
                "9": ("back_key", "SEND WINDOW TO BACK.", False),
                "10": ("quit_key", "QUIT: closes the program.", False),
            }
            field, description, critical = key_fields[choice]
            taken = [
                value for name, value in settings.items()
                if name.endswith("_key") and name != field and isinstance(value, str)
            ]
            settings[field] = read_key(
                description, settings[field] or "s", taken, critical=critical
            )
        elif choice == "12":
            print("Guide: Yes replaces every saved setting with the complete default profile.")
            confirm = read_config_input("Restore every setting to defaults? (y/n): ").strip().lower()
            if confirm in {"y", "yes"}:
                settings.clear()
                settings.update(default_settings())
                save_settings(settings)
                print("All default settings restored and saved.")
            else:
                print("Defaults were not applied.")
            continue
        elif choice == "13":
            save_settings(settings)
            print("Settings saved.")
            return settings
        else:
            print("Choose a number from 1 to 13.")

        save_settings(settings)
        print("That setting was saved. Other settings were unchanged.")


def main() -> None:
    settings = load_settings()
    if settings is None:
        print("First startup detected. Please configure the terminal controls.")
        settings = prompt_for_settings()

    change_window_layer("front" if settings.get("always_on_top", False) else "normal")
    clicker = SafeClicker(Button.left, settings)
    print("\n=== Windows 11 Safe Auto Clicker ===")
    print(f"Saved settings loaded from: {SETTINGS_FILE}")
    display_settings(settings)
    print("1 Start Clicker Up?")
    print("2 Options: change settings")
    print("3 Reset all bindings and run first-start setup again")
    print("4 Close program")
    choice = input("Select 1-4: ").strip()

    if choice == "2":
        edit_settings(settings)
        return main()
    if choice == "3":
        try:
            os.remove(SETTINGS_FILE)
        except FileNotFoundError:
            pass
        return main()
    if choice == "4":
        return
    if choice != "1":
        print("No action selected.")
        return

    print("\nGlobal controls are active. Press Enter here to return to the menu.")
    print("Start arms the clicker; Pause/Resume begins the countdown and then clicking.")
    print("F enables Always on top and brings the window front; B disables it and sends the window back.")
    for name, key in (
        ("start", settings["start_key"]),
        ("pause / resume", settings["toggle_pause_key"]),
        ("emergency stop", settings["emergency_key"]),
        ("global hotkeys toggle", settings["global_toggle_key"]),
        ("front", settings["front_key"]), ("back", settings["back_key"]),
        ("quit", settings["quit_key"]),
    ):
        if key:
            print(f" {key.upper()} = {name}")

    listener: Optional[Listener] = None

    global_hotkeys_enabled = settings.get("global_hotkeys_enabled", True)

    def on_press(key: object) -> None:
        nonlocal global_hotkeys_enabled, listener
        if not isinstance(key, KeyCode) or not key.char:
            return
        pressed = key.char.lower()
        if pressed == settings["global_toggle_key"]:
            global_hotkeys_enabled = not global_hotkeys_enabled
            state = "ENABLED" if global_hotkeys_enabled else "DISABLED"
            print(f"Global hotkeys {state}. Emergency Stop remains active.")
        elif pressed == settings["emergency_key"]:
            clicker.stop("Stopped by the configured Emergency Stop key.")
        elif not global_hotkeys_enabled:
            return
        elif pressed == settings["start_key"]:
            clicker.start()
        elif pressed == settings["toggle_pause_key"]:
            clicker.toggle_pause()
        elif pressed == settings["front_key"]:
            settings["always_on_top"] = True
            change_window_layer("front")
            save_settings(settings)
            print("Always on top ENABLED and window brought to front.")
        elif pressed == settings["back_key"]:
            settings["always_on_top"] = False
            change_window_layer("back")
            save_settings(settings)
            print("Always on top DISABLED and window sent to back.")
        elif pressed == settings["quit_key"]:
            clicker.stop("Program is closing.")
            if listener:
                listener.stop()
            os._exit(0)

    listener = Listener(on_press=on_press)
    listener.start()
    try:
        while True:
            input()
            print("Global controls are still active. Use the configured Quit key to close the program.")
    finally:
        clicker.stop("Global controls closed.")
        listener.stop()
        listener.join(timeout=1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped by Ctrl+C.")
        sys.exit(0)
