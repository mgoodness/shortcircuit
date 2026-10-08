python scripts\windows_version_info.py "%TEMP%\shortcircuit_version_info.txt"

python -O -m PyInstaller ^
    --clean ^
    --windowed ^
    --icon resources\images\app_icon.ico ^
    --add-data "src\database\*;database" ^
    --noconfirm ^
    --name shortcircuit ^
    --version-file "%TEMP%\shortcircuit_version_info.txt" ^
    --onefile ^
    --paths "build\libs" ^
    src\main.py
