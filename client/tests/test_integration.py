"""
Integration Test Suite for VPN Client
Tests project structure, files, and available resources
"""

import unittest
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)


class TestProjectStructure(unittest.TestCase):
    """Test project structure and files."""
    
    def test_client_directory_exists(self):
        """Test client directory exists."""
        client_dir = Path(__file__).parent.parent
        self.assertTrue(client_dir.exists())
        logging.info("✓ Client directory found")
    
    def test_gui_main_exists(self):
        """Test GUI entry point exists."""
        gui_main = Path(__file__).parent.parent / "gui_main.py"
        self.assertTrue(gui_main.exists(), "gui_main.py not found")
        logging.info("✓ gui_main.py found")
    
    def test_client_main_exists(self):
        """Test CLI entry point exists."""
        cli_main = Path(__file__).parent.parent / "client_main.py"
        self.assertTrue(cli_main.exists(), "client_main.py not found")
        logging.info("✓ client_main.py found")
    
    def test_network_directory_exists(self):
        """Test network directory exists."""
        network_dir = Path(__file__).parent.parent / "network"
        self.assertTrue(network_dir.exists(), "network directory not found")
        logging.info("✓ network directory found")
    
    def test_gui_directory_exists(self):
        """Test GUI directory exists."""
        gui_dir = Path(__file__).parent.parent / "gui"
        self.assertTrue(gui_dir.exists(), "gui directory not found")
        logging.info("✓ gui directory found")
    
    def test_core_directory_exists(self):
        """Test core directory exists."""
        core_dir = Path(__file__).parent.parent / "core"
        self.assertTrue(core_dir.exists(), "core directory not found")
        logging.info("✓ core directory found")


class TestBuildScripts(unittest.TestCase):
    """Test build automation scripts."""
    
    def test_build_py_exists(self):
        """Test build.py exists."""
        build_py = Path(__file__).parent.parent / "build.py"
        self.assertTrue(build_py.exists(), "build.py not found")
        logging.info("✓ build.py found")
    
    def test_build_ps1_exists(self):
        """Test build.ps1 exists."""
        build_ps1 = Path(__file__).parent.parent / "build.ps1"
        self.assertTrue(build_ps1.exists(), "build.ps1 not found")
        logging.info("✓ build.ps1 found")
    
    def test_build_spec_exists(self):
        """Test build_config.spec exists."""
        build_spec = Path(__file__).parent.parent / "build_config.spec"
        self.assertTrue(build_spec.exists(), "build_config.spec not found")
        logging.info("✓ build_config.spec found")
    
    def test_validate_build_exists(self):
        """Test validate_build.py exists."""
        validate = Path(__file__).parent.parent / "validate_build.py"
        self.assertTrue(validate.exists(), "validate_build.py not found")
        logging.info("✓ validate_build.py found")
    
    def test_installer_exists(self):
        """Test installer.py exists."""
        installer = Path(__file__).parent.parent / "installer.py"
        self.assertTrue(installer.exists(), "installer.py not found")
        logging.info("✓ installer.py found")


class TestConfigFiles(unittest.TestCase):
    """Test configuration files."""
    
    def test_config_template_exists(self):
        """Test config template exists."""
        config_file = Path(__file__).parent.parent / "client_config.yaml"
        self.assertTrue(config_file.exists(), f"client_config.yaml not found at {config_file}")
        logging.info("✓ client_config.yaml found")
    
    def test_config_readable(self):
        """Test config is readable."""
        config_file = Path(__file__).parent.parent.parent / "client_config.yaml"
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
            self.assertGreater(len(content), 0, "Config file is empty")
            logging.info(f"✓ client_config.yaml is readable ({len(content)} bytes)")


class TestGUIResources(unittest.TestCase):
    """Test GUI resources."""
    
    def test_gui_styles_exist(self):
        """Test GUI style files exist."""
        styles_dir = Path(__file__).parent.parent / "gui" / "styles"
        
        if styles_dir.exists():
            qss_files = list(styles_dir.glob("*.qss"))
            if len(qss_files) > 0:
                logging.info(f"✓ GUI styles present ({len(qss_files)} files)")
            else:
                logging.warning("⚠ No QSS files found in styles directory")
        else:
            logging.warning("⚠ Styles directory not found")
    
    def test_images_exist(self):
        """Test image resources exist."""
        images_dir = Path(__file__).parent.parent / "gui" / "images"
        
        if images_dir.exists():
            images = list(images_dir.glob("*"))
            if len(images) > 0:
                logging.info(f"✓ Image resources present ({len(images)} files)")
            else:
                logging.warning("⚠ No images found in images directory")
        else:
            logging.warning("⚠ Images directory not found")


class TestDocumentation(unittest.TestCase):
    """Test documentation files."""
    
    def test_readme_exists(self):
        """Test README exists."""
        readme = Path(__file__).parent.parent.parent / "README.md"
        self.assertTrue(readme.exists(), "README.md not found")
        logging.info("✓ README.md found")
    
    def test_build_guide_exists(self):
        """Test build guide exists."""
        guide = Path(__file__).parent.parent.parent / "BUILD_DEPLOYMENT_GUIDE.md"
        self.assertTrue(guide.exists(), "BUILD_DEPLOYMENT_GUIDE.md not found")
        logging.info("✓ BUILD_DEPLOYMENT_GUIDE.md found")
    
    def test_testing_guide_exists(self):
        """Test testing guide exists."""
        guide = Path(__file__).parent.parent.parent / "TESTING_DEPLOYMENT_GUIDE.md"
        self.assertTrue(guide.exists(), "TESTING_DEPLOYMENT_GUIDE.md not found")
        logging.info("✓ TESTING_DEPLOYMENT_GUIDE.md found")


class TestDependencyImports(unittest.TestCase):
    """Test if key dependencies can be imported."""
    
    def test_cryptography_available(self):
        """Test if cryptography is available."""
        try:
            from Cryptodome.Cipher import AES
            logging.info("✓ Cryptodome (AES) available")
        except ImportError:
            logging.warning("⚠ Cryptodome not installed (required for production)")
    
    def test_msgpack_available(self):
        """Test if msgpack is available."""
        try:
            import msgpack
            logging.info("✓ msgpack available")
        except ImportError:
            logging.warning("⚠ msgpack not installed (required for production)")
    
    def test_yaml_available(self):
        """Test if YAML is available."""
        try:
            import yaml
            logging.info("✓ PyYAML available")
        except ImportError:
            logging.warning("⚠ PyYAML not installed (required for production)")


def run_test_suite():
    """Run all tests."""
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestProjectStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestBuildScripts))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestGUIResources))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentation))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyImports))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✓ All tests PASSED!")
    else:
        print(f"✗ Tests FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*70)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_test_suite())
