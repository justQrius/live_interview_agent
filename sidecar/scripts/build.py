#!/usr/bin/env python3
"""
Build script for PyInstaller bundling of the sidecar.

This script:
1. Installs PyInstaller if not present
2. Runs PyInstaller with the spec file
3. Copies the output to the correct location for Tauri bundling

Usage:
    python scripts/build.py [--clean] [--verbose]

Options:
    --clean     Clean build artifacts before building
    --verbose   Show verbose PyInstaller output
    --no-upx    Disable UPX compression
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
SIDECAR_DIR = SCRIPT_DIR.parent
SPEC_FILE = SIDECAR_DIR / "sidecar.spec"
DIST_DIR = SIDECAR_DIR / "dist"
BUILD_DIR = SIDECAR_DIR / "build"
TAURI_BIN_DIR = SIDECAR_DIR.parent / "src-tauri" / "binaries"


def get_platform_suffix() -> str:
    """Get the platform-specific suffix for Tauri sidecar naming."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return "x86_64-pc-windows-msvc"
        elif machine == "aarch64":
            return "aarch64-pc-windows-msvc"
        else:
            return "i686-pc-windows-msvc"
    elif system == "darwin":
        if machine == "arm64":
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    elif system == "linux":
        if machine in ("amd64", "x86_64"):
            return "x86_64-unknown-linux-gnu"
        elif machine == "aarch64":
            return "aarch64-unknown-linux-gnu"
        else:
            return "i686-unknown-linux-gnu"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def get_executable_name() -> str:
    """Get the platform-specific executable name."""
    if platform.system() == "Windows":
        return "sidecar-server.exe"
    else:
        return "sidecar-server"


def get_tauri_sidecar_name() -> str:
    """Get the name expected by Tauri for the sidecar binary."""
    suffix = get_platform_suffix()
    if platform.system() == "Windows":
        return f"sidecar-server-{suffix}.exe"
    else:
        return f"sidecar-server-{suffix}"


def check_pyinstaller() -> bool:
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller() -> None:
    """Install PyInstaller using pip."""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])


def clean_build() -> None:
    """Remove build artifacts."""
    print("Cleaning build artifacts...")
    for path in [DIST_DIR, BUILD_DIR]:
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed {path}")


def run_pyinstaller(verbose: bool = False, no_upx: bool = False) -> None:
    """Run PyInstaller with the spec file."""
    if not SPEC_FILE.exists():
        raise FileNotFoundError(f"Spec file not found: {SPEC_FILE}")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
    ]
    
    if verbose:
        cmd.append("--log-level=DEBUG")
    else:
        cmd.append("--log-level=WARN")
    
    if no_upx:
        cmd.append("--noupx")
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=SIDECAR_DIR)


def copy_to_tauri() -> None:
    """Copy the built executable to Tauri binaries directory."""
    exe_name = get_executable_name()
    tauri_name = get_tauri_sidecar_name()
    
    src_path = DIST_DIR / exe_name
    if not src_path.exists():
        raise FileNotFoundError(f"Built executable not found: {src_path}")
    
    # Create Tauri binaries directory if it doesn't exist
    TAURI_BIN_DIR.mkdir(parents=True, exist_ok=True)
    
    dest_path = TAURI_BIN_DIR / tauri_name
    
    print(f"Copying {src_path} -> {dest_path}")
    shutil.copy2(src_path, dest_path)
    
    # Make executable on Unix
    if platform.system() != "Windows":
        dest_path.chmod(0o755)
    
    print(f"Sidecar binary ready at: {dest_path}")


def verify_build() -> bool:
    """Verify the build was successful."""
    exe_name = get_executable_name()
    exe_path = DIST_DIR / exe_name
    
    if not exe_path.exists():
        print(f"ERROR: Executable not found at {exe_path}")
        return False
    
    # Check file size (should be > 10MB with all dependencies)
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"Executable size: {size_mb:.1f} MB")
    
    if size_mb < 5:
        print("WARNING: Executable seems too small, dependencies may be missing")
    
    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build sidecar executable")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts first")
    parser.add_argument("--verbose", action="store_true", help="Verbose PyInstaller output")
    parser.add_argument("--no-upx", action="store_true", help="Disable UPX compression")
    parser.add_argument("--skip-copy", action="store_true", help="Skip copying to Tauri binaries")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Live Interview Agent - Sidecar Build")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")
    print(f"Sidecar dir: {SIDECAR_DIR}")
    print("=" * 60)
    
    try:
        # Check/install PyInstaller
        if not check_pyinstaller():
            install_pyinstaller()
        
        # Clean if requested
        if args.clean:
            clean_build()
        
        # Run PyInstaller
        print("\nBuilding sidecar executable...")
        run_pyinstaller(verbose=args.verbose, no_upx=args.no_upx)
        
        # Verify build
        print("\nVerifying build...")
        if not verify_build():
            return 1
        
        # Copy to Tauri binaries
        if not args.skip_copy:
            print("\nCopying to Tauri binaries directory...")
            copy_to_tauri()
        
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL")
        print("=" * 60)
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Build failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
