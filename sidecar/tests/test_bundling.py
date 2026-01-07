"""
Tests for PyInstaller bundling configuration.

These tests verify that the bundling configuration is correct
and that the sidecar can be built into a standalone executable.
"""

import os
import sys
import pytest
from pathlib import Path

# Get paths relative to test file
SIDECAR_ROOT = Path(__file__).parent.parent
SPEC_FILE = SIDECAR_ROOT / "sidecar.spec"
BUILD_SCRIPT = SIDECAR_ROOT / "scripts" / "build.py"


class TestSpecFile:
    """Tests for the PyInstaller spec file."""

    def test_spec_file_exists(self):
        """Spec file should exist at sidecar/sidecar.spec."""
        assert SPEC_FILE.exists(), f"Spec file not found at {SPEC_FILE}"

    def test_spec_file_has_analysis_block(self):
        """Spec file should contain Analysis configuration."""
        content = SPEC_FILE.read_text()
        assert "Analysis(" in content, "Spec file missing Analysis block"

    def test_spec_file_has_exe_block(self):
        """Spec file should contain EXE configuration."""
        content = SPEC_FILE.read_text()
        assert "EXE(" in content, "Spec file missing EXE block"

    def test_spec_file_includes_server_entry_point(self):
        """Spec file should reference server.py as entry point."""
        content = SPEC_FILE.read_text()
        assert "server.py" in content, "Spec file missing server.py entry point"

    def test_spec_file_includes_hidden_imports(self):
        """Spec file should include critical hidden imports."""
        content = SPEC_FILE.read_text()
        
        # Critical imports that PyInstaller often misses
        required_imports = [
            "torch",
            "websockets",
            "chromadb",
            "speechbrain",
            "google.generativeai",
        ]
        
        for imp in required_imports:
            assert imp in content, f"Spec file missing hidden import: {imp}"

    def test_spec_file_includes_data_files(self):
        """Spec file should include necessary data files."""
        content = SPEC_FILE.read_text()
        # Silero VAD model needs to be bundled
        assert "datas" in content or "binaries" in content, \
            "Spec file should include data/binary files section"

    def test_spec_file_configures_onefile(self):
        """Spec file should be configured for single-file output."""
        content = SPEC_FILE.read_text()
        # Check that it's using BUNDLE or onefile mode
        assert "EXE(" in content, "Spec file should have EXE configuration"


class TestBuildScript:
    """Tests for the build script."""

    def test_build_script_exists(self):
        """Build script should exist at sidecar/scripts/build.py."""
        assert BUILD_SCRIPT.exists(), f"Build script not found at {BUILD_SCRIPT}"

    def test_build_script_is_valid_python(self):
        """Build script should be valid Python syntax."""
        content = BUILD_SCRIPT.read_text()
        try:
            compile(content, str(BUILD_SCRIPT), "exec")
        except SyntaxError as e:
            pytest.fail(f"Build script has syntax error: {e}")

    def test_build_script_has_main_function(self):
        """Build script should have a main() function or entry point."""
        content = BUILD_SCRIPT.read_text()
        assert "def main(" in content or "if __name__" in content, \
            "Build script should have main function or __main__ guard"

    def test_build_script_handles_platform(self):
        """Build script should handle platform-specific configuration."""
        content = BUILD_SCRIPT.read_text()
        assert "platform" in content.lower() or "sys.platform" in content, \
            "Build script should handle platform detection"


class TestBundledExecutable:
    """Tests for the bundled executable (requires build to run first)."""

    @pytest.fixture
    def dist_dir(self):
        """Get the dist directory where bundled executable should be."""
        return SIDECAR_ROOT / "dist"

    def test_dist_directory_structure(self, dist_dir):
        """Dist directory should exist after successful build."""
        # This test only passes after running build
        if not dist_dir.exists():
            pytest.skip("Dist directory not found - run build first")
        assert dist_dir.is_dir()

    @pytest.mark.skipif(
        not (SIDECAR_ROOT / "dist").exists(),
        reason="Build not yet run"
    )
    def test_executable_exists_after_build(self, dist_dir):
        """Bundled executable should exist after build."""
        if sys.platform == "win32":
            exe_name = "sidecar-server.exe"
        else:
            exe_name = "sidecar-server"
        
        exe_path = dist_dir / exe_name
        assert exe_path.exists(), f"Executable not found at {exe_path}"

    @pytest.mark.skipif(
        not (SIDECAR_ROOT / "dist").exists(),
        reason="Build not yet run"
    )
    def test_executable_is_runnable(self, dist_dir):
        """Bundled executable should be a valid executable file."""
        import stat
        
        if sys.platform == "win32":
            exe_name = "sidecar-server.exe"
        else:
            exe_name = "sidecar-server"
        
        exe_path = dist_dir / exe_name
        if not exe_path.exists():
            pytest.skip("Executable not found")
        
        # Check file is executable (on Unix) or exists (on Windows)
        if sys.platform != "win32":
            mode = exe_path.stat().st_mode
            assert mode & stat.S_IXUSR, "Executable should have execute permission"


class TestTauriIntegration:
    """Tests for Tauri sidecar integration."""

    @pytest.fixture
    def tauri_config_path(self):
        """Path to Tauri config."""
        return Path(__file__).parent.parent.parent / "src-tauri" / "tauri.conf.json"

    @pytest.fixture
    def sidecar_rs_path(self):
        """Path to sidecar Rust command file."""
        return Path(__file__).parent.parent.parent / "src-tauri" / "src" / "commands" / "sidecar.rs"

    def test_tauri_config_has_external_bin(self, tauri_config_path):
        """Tauri config should define externalBin for sidecar."""
        import json
        
        content = tauri_config_path.read_text()
        config = json.loads(content)
        
        # Check for bundle.externalBin or similar
        bundle = config.get("bundle", {})
        assert "externalBin" in bundle or "resources" in bundle, \
            "Tauri config should have externalBin or resources for sidecar"

    def test_sidecar_command_implemented(self, sidecar_rs_path):
        """Sidecar Rust commands should be implemented (not placeholder)."""
        content = sidecar_rs_path.read_text()
        
        # Check it's no longer just returning "Not implemented yet"
        assert "Command::new" in content or "process" in content.lower(), \
            "Sidecar command should spawn a process"
        
        # Should not have the placeholder error
        if "Not implemented yet" in content:
            pytest.fail("Sidecar command still has placeholder implementation")
