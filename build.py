#!/usr/bin/env python3
import os
import sys
import site
import shutil
import glob
from pathlib import Path
import PyQt5

def get_qt_paths():
    """Get the Qt directory paths."""
    system_lib_path = '/usr/lib64'
    venv_path = os.path.dirname(os.path.dirname(sys.executable))
    lib_path = os.path.join(venv_path, 'lib64', 'python3.11', 'site-packages', 'PyQt5')
    if not os.path.exists(lib_path):
        lib_path = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages', 'PyQt5')
    
    paths = {
        'root': lib_path,
        'plugins': os.path.join(lib_path, "Qt5", "plugins"),
        'libs': os.path.join(lib_path, "Qt5", "lib"),
        'translations': os.path.join(lib_path, "Qt5", "translations"),
        'qml': os.path.join(lib_path, "Qt5", "qml"),
        'system_libs': system_lib_path
    }
    
    # Print paths for debugging
    print("PyQt5 paths:")
    for key, value in paths.items():
        print(f"{key}: {value}")
        print(f"Exists: {os.path.exists(value)}")
    
    return paths

def main():
    # Get the Qt paths
    qt_paths = get_qt_paths()
    
    # Get the current directory
    current_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Create the spec file content
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
import glob
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

datas = []
binaries = []
hiddenimports = []

# Add PyQt5 metadata and dependencies
datas += copy_metadata('PyQt5')
datas += collect_data_files('PyQt5')

# Add other package metadata
datas += copy_metadata('openai')
datas += copy_metadata('sounddevice')
datas += copy_metadata('numpy')
datas += copy_metadata('matplotlib')

# Add hidden imports
hiddenimports += ['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets']
hiddenimports += ['numpy', 'openai', 'sounddevice', 'matplotlib']
hiddenimports += ['app.gui']  # Add the app package

# Add app package data
datas += [('app', 'app')]  # Include the entire app directory

a = Analysis(
    ['app/main.py'],
    pathex=[r'{current_dir}'],  # Add the project root to Python path
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

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
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

    # Write the spec file
    with open('thoughtpad.spec', 'w') as f:
        f.write(spec_content)

    # Run PyInstaller
    os.system('pyinstaller thoughtpad.spec --clean')

if __name__ == '__main__':
    main()
