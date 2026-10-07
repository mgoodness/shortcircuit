#!/bin/bash

python -O -m PyInstaller \
    --clean \
    --windowed \
    --icon resources/images/app_icon.icns \
    --add-data 'src/database/*:database' \
    --noconfirm \
    --name shortcircuit src/main.py \
    --noupx \
    --target-arch arm64 \
    --osx-bundle-identifier ru.secondfry.shortcircuit

cd dist || exit 1
tar cfz shortcircuit.app.tar.gz shortcircuit.app
