# Windows 11 Safe Auto Clicker

A portable Windows auto-clicker controlled from the keyboard. It clicks at the current mouse position and keeps settings beside the program.

## Run The Portable Version

Use the packaged executable:

```text
dist\autoclicker.exe
```

Keep these files together:

```text
dist\autoclicker.exe
dist\clicker_settings.json
dist\mousecursor.ico
```

Copy the whole `dist` folder to a writable folder or USB drive. Python is not required for the executable. Avoid protected folders such as `C:\Program Files` because the program must save its settings beside the executable.

## First Startup

When setup opens, choose one:

- `y`: save the complete default profile.
- Any other answer: configure each value yourself.

The setup banner stays visible while configuration is running. For configuration values:

- `1` means use the default.
- `0`, `null`, a blank input, or a space means none where allowed.
- Emergency Stop and Global Hotkeys Toggle are required and cannot be disabled.

The saved profile is `clicker_settings.json` beside the program.

## Main Menu

Choose:

- `1 Start Clicker Up?`: enable the global keyboard controls.
- `2 Options`: change one setting at a time.
- `3 Reset all bindings and run first-start setup again`: erase the saved profile and configure again.
- `4 Close program`: close the program.

The current profile is displayed before the menu.

## Normal Controls

The default keys are:

| Key | Action |
| --- | --- |
| `S` | Arm the clicker. |
| `T` | Start the countdown, then pause or resume clicking. |
| `P` | Emergency Stop. It stops clicking and prints the reason. |
| `G` | Enable or disable normal global hotkeys. `G` and Emergency Stop remain active. |
| `F` | Enable Always on top and bring the window to the front. |
| `B` | Disable Always on top and send the window to the back. |
| `Q` | Close the program and terminal process. |

Keys can be changed in Options. The configured bindings work globally while controls are active, even when another window has focus.

## Starting A Click Run

1. Place the mouse over the location to click.
2. Choose `1 Start Clicker Up?`.
3. Press the Start key, usually `S`, to arm the clicker.
4. Press the Pause/Resume key, usually `T`, to begin the countdown.
5. The cursor location is clicked after the countdown finishes.
6. Press Pause/Resume to pause or resume clicking.
7. Press Emergency Stop if you need to stop immediately.

Pressing Enter during active controls does not close the program. Use the configured Quit key or `Ctrl+C` to exit.

## Options

Choose `2 Options` to edit one setting at a time. The menu shows each current value.

- Countdown: `0`, `null`, blank, or space means no countdown; `1` uses the default 10 seconds.
- Maximum duration: `0`, `null`, blank, or space means unlimited; `1` uses the default unlimited value.
- Click speed: choose seconds, milliseconds, microseconds, or unlimited. Unlimited mode may use high CPU and may overwhelm the target application.
- Key bindings: `1` uses the default key; `0`, `null`, blank, or space disables optional bindings.
- Always on top: `1` or `yes` enables it; `0`, `null`, blank, or `no` disables it.
- Restore all default settings: choose option `12` and confirm with `y` or `yes`.
- Done and return: choose option `13`.

For per-setting defaults, answer `y` or `yes` when asked whether to set the selected setting to its default. Every other answer means no.

## Safety Features

- Emergency Stop is always required.
- Maximum duration can automatically stop a run.
- Repeated system delays can trigger a protective stop.
- Countdown gives time to position the cursor.
- `Ctrl+C` stops the program from the terminal.
- Unlimited speed can create high CPU usage and missed or overwhelmed clicks; use a finite delay when possible.

## Run The Python Source

The source file is [autoclicker.py](autoclicker.py). It requires Python and the project dependencies:

```powershell
python -m pip install pynput pyinstaller
python .\autoclicker.py
```

The Python source stores settings beside `autoclicker.py`.

## Rebuild The Executable

From the project folder, run:

```powershell
python -m PyInstaller .\autoclicker.spec --noconfirm
```

