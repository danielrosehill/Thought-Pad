#!/usr/bin/env python3
import os
import sys
import site
import shutil
import glob
from pathlib import Path
import PyQt6

def get_qt_paths():
    """Get the Qt directory paths."""
    system_lib_path = '/usr/lib64'
    venv_path = os.path.dirname(os.path.dirname(sys.executable))
    lib_path = os.path.join(venv_path, 'lib64', 'python3.11', 'site-packages', 'PyQt6')
    if not os.path.exists(lib_path):
        lib_path = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages', 'PyQt6')
    
    paths = {
        'root': lib_path,
        'plugins': os.path.join(lib_path, "Qt6", "plugins"),
        'libs': os.path.join(lib_path, "Qt6", "lib"),
        'translations': os.path.join(lib_path, "Qt6", "translations"),
        'qml': os.path.join(lib_path, "Qt6", "qml"),
        'system_libs': system_lib_path
    }
    
    # Print paths for debugging
    print("PyQt6 paths:")
    for key, value in paths.items():
        print(f"{key}: {value}")
        print(f"Exists: {os.path.exists(value)}")
    
    return paths

def main():
    # Get the Qt paths
    qt_paths = get_qt_paths()
    
    # Create the spec file content
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import os
import glob
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

datas = []
binaries = []
hiddenimports = []

# Add PyQt6 metadata
datas += copy_metadata('PyQt6')

# Add system Qt libraries
system_qt_libs = glob.glob(''' + f"'{qt_paths['system_libs']}/libQt6*.so*'" + ''')
for lib in system_qt_libs:
    binaries.append((lib, '.'))

# Add PyQt6 plugins
plugin_dirs = ['platforms', 'styles']
for plugin_dir in plugin_dirs:
    plugin_path = os.path.join(''' + f"'{qt_paths['plugins']}'" + ''', plugin_dir)
    if os.path.exists(plugin_path):
        for file in glob.glob(os.path.join(plugin_path, '*.so*')):
            binaries.append((file, os.path.join('PyQt6', 'Qt6', 'plugins', plugin_dir)))

# Collect all dependencies
packages = ['PyQt6', 'openai', 'sounddevice', 'numpy', 'matplotlib', 'python-docx', 'fpdf2', 'pyqtgraph']
for package in packages:
    try:
        print("Collecting " + package)
        data, bin, himp = collect_all(package)
        datas += data
        binaries += bin
        hiddenimports += himp
    except Exception as e:
        print("Warning: Error collecting " + package + ": " + str(e))

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
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
    hooksconfig={
        'PyQt6': {
            'style_plugins': ['qwindowsvistastyle', 'qmacstyle', 'qdmanstyle'],
            'gui_plugins': ['platforms', 'platformthemes', 'styles'],
            'network_plugins': ['networkaccess'],
        }
    },
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6', 'PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='thoughtpad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# Create a directory containing the executable and all dependencies
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='thoughtpad'
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
