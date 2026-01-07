#!/usr/bin/env python3
"""
Build script for Live Interview Agent platform installers.

Usage:
    python scripts/build-installer.py [--platform windows|macos|linux] [--release] [--skip-sidecar]
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def get_target_triple() -> str:
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


def get_sidecar_extension() -> str:
    if platform.system().lower() == "windows":
        return ".exe"
    return ""


def run_command(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    print(f"\n>>> Running: {' '.join(cmd)}")
    if cwd:
        print(f"    in: {cwd}")
    
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    result = subprocess.run(cmd, cwd=cwd, env=full_env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")


def build_sidecar(project_root: Path, clean: bool = False) -> Path:
    print("\n=== Building Python Sidecar ===")
    
    sidecar_dir = project_root / "sidecar"
    build_script = sidecar_dir / "scripts" / "build.py"
    
    if not build_script.exists():
        raise FileNotFoundError(f"Sidecar build script not found: {build_script}")
    
    cmd = [sys.executable, str(build_script)]
    if clean:
        cmd.append("--clean")
    
    run_command(cmd, cwd=sidecar_dir)
    
    target_triple = get_target_triple()
    ext = get_sidecar_extension()
    sidecar_name = f"sidecar-server-{target_triple}{ext}"
    sidecar_path = project_root / "src-tauri" / "binaries" / sidecar_name
    
    if not sidecar_path.exists():
        raise FileNotFoundError(f"Built sidecar not found: {sidecar_path}")
    
    print(f"Sidecar built successfully: {sidecar_path}")
    return sidecar_path


def build_tauri(project_root: Path, release: bool = False, target: str | None = None) -> Path:
    print("\n=== Building Tauri Application ===")
    
    if not (project_root / "node_modules").exists():
        print("Installing npm dependencies...")
        run_command(["npm", "install"], cwd=project_root)
    
    cmd = ["npm", "run", "tauri", "build"]
    
    if not release:
        cmd.append("--debug")
    
    if target:
        cmd.extend(["--target", target])
    
    run_command(cmd, cwd=project_root)
    
    current_platform = get_platform()
    bundle_dir = project_root / "src-tauri" / "target"
    
    if release:
        bundle_dir = bundle_dir / "release" / "bundle"
    else:
        bundle_dir = bundle_dir / "debug" / "bundle"
    
    if target:
        bundle_dir = project_root / "src-tauri" / "target" / target / ("release" if release else "debug") / "bundle"
    
    print(f"\n=== Build Complete ===")
    print(f"Bundle directory: {bundle_dir}")
    
    if bundle_dir.exists():
        print("Built installers:")
        for item in bundle_dir.iterdir():
            if item.is_dir():
                for file in item.iterdir():
                    print(f"  - {item.name}/{file.name}")
            else:
                print(f"  - {item.name}")
    
    return bundle_dir


def verify_prerequisites() -> None:
    print("=== Verifying Prerequisites ===")
    
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"Node.js: {result.stdout.strip()}")
    except FileNotFoundError:
        raise RuntimeError("Node.js not found. Please install Node.js 20+")
    
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        print(f"npm: {result.stdout.strip()}")
    except FileNotFoundError:
        raise RuntimeError("npm not found. Please install Node.js")
    
    try:
        result = subprocess.run(["rustc", "--version"], capture_output=True, text=True)
        print(f"Rust: {result.stdout.strip()}")
    except FileNotFoundError:
        raise RuntimeError("Rust not found. Please install Rust via rustup")
    
    print(f"Python: {sys.version}")
    
    current_platform = get_platform()
    
    if current_platform == "windows":
        vs_path = Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft Visual Studio"
        if not vs_path.exists():
            print("WARNING: Visual Studio Build Tools may not be installed")
    
    elif current_platform == "macos":
        try:
            subprocess.run(["xcode-select", "-p"], capture_output=True, check=True)
            print("Xcode Command Line Tools: installed")
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError("Xcode Command Line Tools not found. Run: xcode-select --install")
    
    elif current_platform == "linux":
        required_libs = ["libwebkit2gtk-4.1-dev", "libssl-dev", "libgtk-3-dev"]
        print(f"Note: Ensure these packages are installed: {', '.join(required_libs)}")
    
    print("Prerequisites verified!")


def main():
    parser = argparse.ArgumentParser(
        description="Build Live Interview Agent platform installers"
    )
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux"],
        default=None,
        help="Target platform (default: current platform)"
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Build release version (default: debug)"
    )
    parser.add_argument(
        "--skip-sidecar",
        action="store_true",
        help="Skip sidecar build (use existing)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build (remove previous artifacts)"
    )
    parser.add_argument(
        "--skip-prerequisites",
        action="store_true",
        help="Skip prerequisites verification"
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    
    print(f"Project root: {project_root}")
    print(f"Current platform: {get_platform()}")
    print(f"Target triple: {get_target_triple()}")
    
    if not args.skip_prerequisites:
        verify_prerequisites()
    
    if not args.skip_sidecar:
        build_sidecar(project_root, clean=args.clean)
    else:
        print("\n=== Skipping Sidecar Build ===")
        target_triple = get_target_triple()
        ext = get_sidecar_extension()
        sidecar_name = f"sidecar-server-{target_triple}{ext}"
        sidecar_path = project_root / "src-tauri" / "binaries" / sidecar_name
        
        if not sidecar_path.exists():
            raise FileNotFoundError(f"Sidecar not found: {sidecar_path}. Run without --skip-sidecar")
        print(f"Using existing sidecar: {sidecar_path}")
    
    target = None
    if args.platform:
        if args.platform == "windows":
            target = "x86_64-pc-windows-msvc"
        elif args.platform == "macos":
            target = "x86_64-apple-darwin"
        elif args.platform == "linux":
            target = "x86_64-unknown-linux-gnu"
    
    bundle_dir = build_tauri(project_root, release=args.release, target=target)
    
    print("\n=== BUILD SUCCESSFUL ===")
    print(f"Installers available in: {bundle_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
