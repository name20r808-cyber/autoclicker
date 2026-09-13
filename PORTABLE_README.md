# Portable Auto Clicker

Copy the entire `dist` folder to any writable location and run `autoclicker.exe`.

The executable is a one-file Windows build. It does not need Python installed. Its settings are stored in `clicker_settings.json` beside the executable, so copying that file with the executable preserves the configuration.

Do not place the folder in a protected location such as `C:\Program Files`; use a folder where you can write files. The executable may use a temporary Windows extraction directory internally, but it does not install the application or store configuration there.

The `.py` source is portable only on computers that already have Python and the project dependencies installed. For a standalone portable copy, use `dist\autoclicker.exe` together with `dist\clicker_settings.json`.
