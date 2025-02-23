#!/usr/bin/env python3
import os
import sys
import site
import shutil
from pathlib import Path
import PyQt6

def get_qt_paths():
    """Get the Qt directory paths."""
    qt_root = os.path.dirname(PyQt6.__file__)
    paths = {
        'root': qt_root,
        'plugins': os.path.join(qt_root, "Qt6", "plugins"),
        'libs': os.path.join(qt_root, "Qt6", "lib"),
        'translations': os.path.join(qt_root, "Qt6", "translations")
    }
    
    # Try alternative locations if not found
    if not os.path.exists(paths['plugins']):
        for prefix in site.getsitepackages():
            alt_root = os.path.join(prefix, "PyQt6")
            if os.path.exists(os.path.join(alt_root, "Qt6", "plugins")):
                paths = {
                    'root': alt_root,
                    'plugins': os.path.join(alt_root, "Qt6", "plugins"),
                    'libs': os.path.join(alt_root, "Qt6", "lib"),
                    'translations': os.path.join(alt_root, "Qt6", "translations")
                }
                break
    
    return paths

def main():
    # Get the Qt paths
    qt_paths = get_qt_paths()
    if not qt_paths['plugins']:
        print("Error: Could not find Qt plugins directory")
        sys.exit(1)
    
    # Create the spec file content
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect all PyQt6 dependencies
qt_data, qt_binaries, qt_hiddenimports = collect_all('PyQt6')

# Additional data files for audio and other dependencies
additional_data = collect_data_files('sounddevice') + collect_data_files('numpy')

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=qt_binaries,
    datas=qt_data + additional_data,
    hiddenimports=qt_hiddenimports + [
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'openai',
        'sounddevice',
        'numpy',
        'matplotlib',
        'docx',
        'fpdf2',
        'pyqtgraph',
    ],
    hookspath=[],
    hooksconfig={{
        'PyQt6': {{
            'style_plugins': ['qwindowsvistastyle', 'qmacstyle', 'qdmanstyle'],
            'gui_plugins': ['platforms', 'platformthemes', 'styles'],
            'network_plugins': ['networkaccess'],
        }}
    }},
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6', 'PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='thoughtpad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,  # Changed from /tmp/thoughtpad_runtime to None for better portability
    console=False,  # Changed to False for a cleaner GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add an icon path here if you have one
)
'''
    
    # Write the spec file
    with open('thoughtpad.spec', 'w') as f:
        f.write(spec_content)
    
    # Clean previous build and dist directories
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    print("Build specification file created successfully!")
    print("To build the application, run: pyinstaller thoughtpad.spec")

if __name__ == '__main__':
    main()
