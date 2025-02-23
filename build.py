#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

def clean_build():
    """Clean the build and dist directories"""
    directories = ['build', 'dist']
    for directory in directories:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            print(f"Cleaned {directory} directory")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building Thought Pad executable...")
    
    # PyInstaller command with additional options for stability
    cmd = [
        'pyinstaller',
        '--name=ThoughtPad',
        '--onefile',
        '--clean',  # Clean PyInstaller cache and remove temporary files
        '--noconfirm',  # Replace output directory without asking for confirmation
        '--log-level=INFO',
        'app/gui.py'
    ]

    try:
        subprocess.run(cmd, check=True)
        
        # Move the executable to build directory
        if sys.platform == 'win32':
            executable = 'dist/ThoughtPad.exe'
        else:
            executable = 'dist/ThoughtPad'
            
        if os.path.exists(executable):
            # Create build directory if it doesn't exist
            if not os.path.exists('build'):
                os.makedirs('build')
                
            # Copy instead of move to avoid potential issues
            shutil.copy2(executable, 'build/')
            print("\nBuild successful! Executable created in build/ directory")
        else:
            print("\nError: Executable not found")
            
    except subprocess.CalledProcessError as e:
        print(f"\nError during build: {e}")
        sys.exit(1)

if __name__ == '__main__':
    clean_build()
    build_executable()
