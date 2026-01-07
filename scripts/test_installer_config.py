#!/usr/bin/env python3
"""Tests for installer configuration validation."""

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TAURI_CONF_PATH = PROJECT_ROOT / "src-tauri" / "tauri.conf.json"
CARGO_TOML_PATH = PROJECT_ROOT / "src-tauri" / "Cargo.toml"
LICENSE_PATH = PROJECT_ROOT / "LICENSE"


class TestTauriConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TAURI_CONF_PATH) as f:
            cls.config = json.load(f)
    
    def test_config_has_valid_identifier(self):
        identifier = self.config.get("identifier")
        self.assertIsNotNone(identifier)
        self.assertNotEqual(identifier, "com.tauri.dev")
        self.assertTrue(identifier.startswith("com."))
    
    def test_config_has_product_name(self):
        product_name = self.config.get("productName")
        self.assertEqual(product_name, "Live Interview Agent")
    
    def test_config_has_version(self):
        version = self.config.get("version")
        self.assertIsNotNone(version)
        self.assertRegex(version, r"^\d+\.\d+\.\d+")
    
    def test_bundle_section_exists(self):
        bundle = self.config.get("bundle")
        self.assertIsNotNone(bundle)
        self.assertTrue(bundle.get("active", False))
    
    def test_bundle_has_icons(self):
        icons = self.config["bundle"].get("icon", [])
        self.assertGreater(len(icons), 0)
        
        icon_dir = PROJECT_ROOT / "src-tauri" / "icons"
        for icon in icons:
            icon_path = PROJECT_ROOT / "src-tauri" / icon
            self.assertTrue(icon_path.exists(), f"Icon not found: {icon_path}")
    
    def test_bundle_has_external_bin(self):
        external_bin = self.config["bundle"].get("externalBin", [])
        self.assertIn("binaries/sidecar-server", external_bin)
    
    def test_bundle_has_metadata(self):
        bundle = self.config["bundle"]
        self.assertIn("copyright", bundle)
        self.assertIn("shortDescription", bundle)
        self.assertIn("longDescription", bundle)
        self.assertIn("publisher", bundle)
        self.assertIn("category", bundle)
    
    def test_bundle_has_license(self):
        bundle = self.config["bundle"]
        self.assertIn("licenseFile", bundle)
        self.assertIn("license", bundle)
        self.assertEqual(bundle["license"], "MIT")


class TestWindowsConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TAURI_CONF_PATH) as f:
            cls.config = json.load(f)
        cls.windows_config = cls.config.get("bundle", {}).get("windows", {})
    
    def test_windows_section_exists(self):
        self.assertIsNotNone(self.windows_config)
        self.assertIsInstance(self.windows_config, dict)
    
    def test_webview_install_mode(self):
        webview_mode = self.windows_config.get("webviewInstallMode", {})
        self.assertIn(webview_mode.get("type"), ["downloadBootstrapper", "fixedRuntime", "offlineInstaller", "skip"])
    
    def test_nsis_config(self):
        nsis = self.windows_config.get("nsis", {})
        self.assertIn("installMode", nsis)
        self.assertIn(nsis.get("installMode"), ["currentUser", "perMachine"])
    
    def test_wix_config(self):
        wix = self.windows_config.get("wix", {})
        self.assertIn("language", wix)
        self.assertIn("upgradeCode", wix)
        
        upgrade_code = wix.get("upgradeCode", "")
        self.assertRegex(upgrade_code, r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class TestMacOSConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TAURI_CONF_PATH) as f:
            cls.config = json.load(f)
        cls.macos_config = cls.config.get("bundle", {}).get("macOS", {})
    
    def test_macos_section_exists(self):
        self.assertIsNotNone(self.macos_config)
        self.assertIsInstance(self.macos_config, dict)
    
    def test_minimum_system_version(self):
        min_version = self.macos_config.get("minimumSystemVersion")
        self.assertIsNotNone(min_version)
        
        major, minor = map(int, min_version.split(".")[:2])
        self.assertGreaterEqual(major, 10)
        if major == 10:
            self.assertGreaterEqual(minor, 13)
    
    def test_dmg_config(self):
        dmg = self.macos_config.get("dmg", {})
        self.assertIn("windowSize", dmg)
        
        window_size = dmg.get("windowSize", {})
        self.assertIn("width", window_size)
        self.assertIn("height", window_size)
        self.assertGreater(window_size.get("width", 0), 0)
        self.assertGreater(window_size.get("height", 0), 0)


class TestLinuxConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TAURI_CONF_PATH) as f:
            cls.config = json.load(f)
        cls.linux_config = cls.config.get("bundle", {}).get("linux", {})
    
    def test_linux_section_exists(self):
        self.assertIsNotNone(self.linux_config)
        self.assertIsInstance(self.linux_config, dict)
    
    def test_appimage_config(self):
        appimage = self.linux_config.get("appimage", {})
        self.assertIn("bundleMediaFramework", appimage)
    
    def test_deb_config(self):
        deb = self.linux_config.get("deb", {})
        self.assertIn("depends", deb)
        self.assertIn("section", deb)
        
        depends = deb.get("depends", [])
        self.assertIsInstance(depends, list)
        self.assertGreater(len(depends), 0)
    
    def test_rpm_config(self):
        rpm = self.linux_config.get("rpm", {})
        self.assertIn("depends", rpm)
        
        depends = rpm.get("depends", [])
        self.assertIsInstance(depends, list)


class TestLicenseFile(unittest.TestCase):
    def test_license_exists(self):
        self.assertTrue(LICENSE_PATH.exists(), "LICENSE file not found")
    
    def test_license_not_empty(self):
        content = LICENSE_PATH.read_text()
        self.assertGreater(len(content), 100)
    
    def test_license_contains_mit(self):
        content = LICENSE_PATH.read_text()
        self.assertIn("MIT", content)


class TestCargoToml(unittest.TestCase):
    def test_cargo_toml_exists(self):
        self.assertTrue(CARGO_TOML_PATH.exists())
    
    def test_cargo_has_required_fields(self):
        content = CARGO_TOML_PATH.read_text()
        
        self.assertIn("name", content)
        self.assertIn("version", content)
        self.assertIn("description", content)
        self.assertIn("license", content)
    
    def test_cargo_has_proper_name(self):
        content = CARGO_TOML_PATH.read_text()
        self.assertIn('name = "live-interview-agent"', content)


class TestBuildScript(unittest.TestCase):
    def test_build_script_exists(self):
        build_script = PROJECT_ROOT / "scripts" / "build-installer.py"
        self.assertTrue(build_script.exists())
    
    def test_build_script_is_executable(self):
        build_script = PROJECT_ROOT / "scripts" / "build-installer.py"
        content = build_script.read_text()
        self.assertTrue(content.startswith("#!/usr/bin/env python3"))
    
    def test_build_script_has_main(self):
        build_script = PROJECT_ROOT / "scripts" / "build-installer.py"
        content = build_script.read_text()
        self.assertIn("def main():", content)
        self.assertIn("if __name__", content)


class TestSidecarBinary(unittest.TestCase):
    def test_binaries_directory_exists(self):
        binaries_dir = PROJECT_ROOT / "src-tauri" / "binaries"
        self.assertTrue(binaries_dir.exists())
    
    def test_placeholder_or_binary_exists(self):
        binaries_dir = PROJECT_ROOT / "src-tauri" / "binaries"
        files = list(binaries_dir.glob("sidecar-server*"))
        self.assertGreater(len(files), 0, "No sidecar binary or placeholder found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
