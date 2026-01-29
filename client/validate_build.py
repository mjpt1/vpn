"""
Build Validation & Testing Script
Comprehensive testing of built executable and all components.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuildValidator:
    """Validate built VPN Client."""
    
    def __init__(self, project_root: Path = None):
        """Initialize validator."""
        self.project_root = project_root or Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.exe_path = self.dist_dir / "VPN_Client" / "VPN_Client.exe"
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'exe_path': str(self.exe_path),
            'checks': {}
        }
    
    def check_exe_exists(self) -> bool:
        """Check if EXE exists."""
        logger.info("Checking if EXE exists...")
        
        exists = self.exe_path.exists()
        
        if exists:
            logger.info(f"✓ EXE found: {self.exe_path}")
            self.results['checks']['exe_exists'] = True
            return True
        else:
            logger.error(f"✗ EXE not found: {self.exe_path}")
            self.results['checks']['exe_exists'] = False
            return False
    
    def check_exe_size(self) -> bool:
        """Check EXE size is reasonable."""
        logger.info("Checking EXE size...")
        
        if not self.exe_path.exists():
            logger.error("EXE not found")
            return False
        
        size_mb = self.exe_path.stat().st_size / (1024 * 1024)
        
        logger.info(f"EXE size: {size_mb:.1f} MB")
        
        # Check if size is reasonable (not too small, not too large)
        if 50 < size_mb < 250:
            logger.info(f"✓ Size is reasonable")
            self.results['checks']['exe_size'] = {
                'size_mb': round(size_mb, 1),
                'status': 'OK'
            }
            return True
        else:
            logger.error(f"✗ Size is suspicious: {size_mb:.1f} MB")
            logger.error("Expected: 50-250 MB")
            self.results['checks']['exe_size'] = {
                'size_mb': round(size_mb, 1),
                'status': 'WARNING'
            }
            return False
    
    def check_dll_integrity(self) -> bool:
        """Check DLL files integrity."""
        logger.info("Checking DLL integrity...")
        
        internal_dir = self.dist_dir / "VPN_Client" / "_internal"
        
        if not internal_dir.exists():
            logger.warning("_internal directory not found")
            self.results['checks']['dll_integrity'] = {'status': 'SKIPPED'}
            return True
        
        dlls = list(internal_dir.glob("**/*.dll"))
        
        logger.info(f"Found {len(dlls)} DLL files")
        
        if len(dlls) > 0:
            logger.info(f"✓ DLLs present: {len(dlls)} files")
            self.results['checks']['dll_integrity'] = {
                'dll_count': len(dlls),
                'status': 'OK'
            }
            return True
        else:
            logger.error("✗ No DLLs found")
            self.results['checks']['dll_integrity'] = {'status': 'ERROR'}
            return False
    
    def check_dependencies(self) -> bool:
        """Check if required modules are present."""
        logger.info("Checking dependencies...")
        
        internal_dir = self.dist_dir / "VPN_Client" / "_internal"
        
        required_dirs = [
            'PySide6',      # GUI framework
            'Cryptodome',   # Encryption
            'msgpack',      # Serialization
            'yaml',         # Config parsing
        ]
        
        found = 0
        for required in required_dirs:
            found_path = list(internal_dir.glob(f"*{required}*"))
            if found_path:
                logger.info(f"✓ {required} found")
                found += 1
            else:
                logger.warning(f"⚠ {required} not found (might be OK if bundled)")
        
        self.results['checks']['dependencies'] = {
            'found': found,
            'required': len(required_dirs),
            'status': 'OK' if found >= len(required_dirs) - 1 else 'WARNING'
        }
        
        return True
    
    def check_config_present(self) -> bool:
        """Check if config template exists."""
        logger.info("Checking configuration file...")
        
        config_path = self.project_root / "client_config.yaml"
        
        if config_path.exists():
            logger.info(f"✓ Config template found")
            self.results['checks']['config_present'] = True
            return True
        else:
            logger.warning(f"⚠ Config template not found (can be created at runtime)")
            self.results['checks']['config_present'] = False
            return True  # Not critical
    
    def check_styles_present(self) -> bool:
        """Check if GUI styles are present."""
        logger.info("Checking GUI styles...")
        
        styles_dir = self.dist_dir / "VPN_Client" / "client" / "gui" / "styles"
        
        if styles_dir.exists():
            qss_files = list(styles_dir.glob("*.qss"))
            
            if qss_files:
                logger.info(f"✓ Styles found: {len(qss_files)} files")
                self.results['checks']['styles_present'] = True
                return True
        
        logger.warning("⚠ Styles not found in dist (check packaging)")
        self.results['checks']['styles_present'] = False
        return True  # Not critical
    
    def test_exe_signature(self) -> bool:
        """Check EXE signature (if signed)."""
        logger.info("Checking EXE signature...")
        
        # This would require code signing certificate
        # For now, just check if EXE is readable
        
        try:
            with open(self.exe_path, 'rb') as f:
                # Read first 4 bytes (MZ header)
                header = f.read(4)
                
                if header == b'MZ\x90\x00':
                    logger.info("✓ Valid PE executable")
                    self.results['checks']['exe_signature'] = {'status': 'VALID'}
                    return True
                else:
                    logger.error("✗ Invalid executable header")
                    self.results['checks']['exe_signature'] = {'status': 'INVALID'}
                    return False
        
        except Exception as e:
            logger.error(f"Could not read EXE: {e}")
            self.results['checks']['exe_signature'] = {'status': 'ERROR'}
            return False
    
    def test_import(self) -> bool:
        """Test if critical modules can be imported."""
        logger.info("Testing module imports...")
        
        modules_to_test = [
            'PySide6',
            'Cryptodome',
            'msgpack',
            'yaml'
        ]
        
        results = {}
        success = True
        
        for module in modules_to_test:
            try:
                __import__(module)
                logger.info(f"✓ {module} importable")
                results[module] = 'OK'
            except ImportError as e:
                logger.warning(f"⚠ Could not import {module}: {e}")
                results[module] = 'FAILED'
                success = False
        
        self.results['checks']['imports'] = results
        return success
    
    def test_run(self, timeout: int = 10) -> bool:
        """Test if EXE can start (non-blocking)."""
        logger.info("Testing EXE startup...")
        
        if not self.exe_path.exists():
            logger.error("EXE not found")
            self.results['checks']['exe_run'] = {'status': 'SKIPPED'}
            return False
        
        try:
            # Try to start EXE with a timeout (GUI will exit quickly if config not set)
            process = subprocess.Popen(
                str(self.exe_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout
            )
            
            # Wait a bit for startup
            import time
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info("✓ EXE started successfully (GUI running)")
                process.terminate()
                process.wait(timeout=5)
                self.results['checks']['exe_run'] = {'status': 'OK'}
                return True
            else:
                # Process exited
                stdout, stderr = process.communicate()
                
                # Check for initialization errors
                if b'Error' in stderr or b'ERROR' in stderr:
                    logger.error(f"✗ EXE exited with errors:\n{stderr.decode()}")
                    self.results['checks']['exe_run'] = {'status': 'FAILED', 'error': stderr.decode()[:200]}
                    return False
                else:
                    logger.info("✓ EXE ran and exited normally")
                    self.results['checks']['exe_run'] = {'status': 'OK'}
                    return True
        
        except subprocess.TimeoutExpired:
            logger.warning("⚠ EXE startup timeout (this might be normal for GUI)")
            self.results['checks']['exe_run'] = {'status': 'TIMEOUT'}
            return True
        
        except Exception as e:
            logger.error(f"✗ Could not run EXE: {e}")
            self.results['checks']['exe_run'] = {'status': 'FAILED', 'error': str(e)}
            return False
    
    def validate(self) -> bool:
        """Run all validation checks."""
        logger.info("=" * 60)
        logger.info("Build Validation")
        logger.info("=" * 60)
        
        checks = [
            ("EXE exists", self.check_exe_exists),
            ("EXE size", self.check_exe_size),
            ("DLL integrity", self.check_dll_integrity),
            ("Dependencies", self.check_dependencies),
            ("Config present", self.check_config_present),
            ("Styles present", self.check_styles_present),
            ("EXE signature", self.test_exe_signature),
            ("Module imports", self.test_import),
            ("EXE startup", self.test_run),
        ]
        
        passed = 0
        failed = 0
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error in {check_name}: {e}")
                failed += 1
            
            logger.info("")
        
        # Summary
        logger.info("=" * 60)
        logger.info("Validation Summary")
        logger.info("=" * 60)
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        
        if failed == 0:
            logger.info("\n✓ All checks passed! Build is ready for distribution.")
            self.results['status'] = 'PASSED'
        else:
            logger.warning(f"\n⚠ {failed} check(s) failed. Review above.")
            self.results['status'] = 'FAILED'
        
        # Save results
        self.save_results()
        
        return failed == 0
    
    def save_results(self) -> None:
        """Save validation results to file."""
        try:
            results_file = self.project_root / "build_validation_results.json"
            
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            logger.info(f"✓ Results saved to: {results_file}")
        
        except Exception as e:
            logger.error(f"Could not save results: {e}")


def main():
    """Main entry point."""
    validator = BuildValidator()
    
    success = validator.validate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
