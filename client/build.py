"""
Build Script for VPN Client EXE
Automates PyInstaller build with optimizations and cleanup.
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VPNClientBuilder:
    """Build VPN Client executable with PyInstaller."""
    
    def __init__(self, project_root: Path = None):
        """
        Initialize builder.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.spec_file = self.project_root / "build_config.spec"
        
        logger.info(f"Project root: {self.project_root}")
    
    def check_dependencies(self) -> bool:
        """
        Check if required tools are installed.
        
        Returns:
            True if all dependencies are available
        """
        logger.info("Checking dependencies...")
        
        # Check PyInstaller
        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✓ PyInstaller: {result.stdout.strip()}")
            else:
                logger.error("✗ PyInstaller not found. Install with:")
                logger.error("  pip install pyinstaller")
                return False
        
        except Exception as e:
            logger.error(f"Error checking PyInstaller: {e}")
            return False
        
        # Check PySide6
        try:
            import PySide6
            logger.info(f"✓ PySide6 installed")
        except ImportError:
            logger.error("✗ PySide6 not found. Install with:")
            logger.error("  pip install PySide6")
            return False
        
        return True
    
    def clean_build_artifacts(self) -> None:
        """Remove old build artifacts."""
        logger.info("Cleaning old build artifacts...")
        
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                logger.info(f"Removing {directory}")
                shutil.rmtree(directory)
        
        # Remove .spec backup
        spec_backup = self.project_root / (self.spec_file.name + "~")
        if spec_backup.exists():
            spec_backup.unlink()
    
    def run_pyinstaller(self) -> bool:
        """
        Run PyInstaller build.
        
        Returns:
            True if successful
        """
        logger.info("Running PyInstaller...")
        
        try:
            cmd = [
                sys.executable,
                "-m", "PyInstaller",
                "--noconfirm",  # Don't ask for confirmation
                "--distpath", str(self.dist_dir),
                "--workpath", str(self.build_dir),
                str(self.spec_file)
            ]
            
            result = subprocess.run(cmd, capture_output=False, text=True)
            
            if result.returncode != 0:
                logger.error("PyInstaller build failed")
                return False
            
            logger.info("✓ PyInstaller build successful")
            return True
        
        except Exception as e:
            logger.error(f"Error running PyInstaller: {e}")
            return False
    
    def optimize_dist(self) -> None:
        """
        Optimize distribution by removing unnecessary files.
        
        This reduces size and improves startup time.
        """
        logger.info("Optimizing distribution...")
        
        app_dir = self.dist_dir / "VPN_Client"
        
        if not app_dir.exists():
            logger.warning(f"App directory not found: {app_dir}")
            return
        
        # Extensions to remove
        remove_extensions = [
            '.pyc', '.pyo',  # Compiled Python
            '.dist-info',    # Package metadata
            'tests',         # Test files
            '__pycache__'    # Cache directories
        ]
        
        # Specific files/dirs to remove
        remove_names = [
            'tcl', 'tk',     # Not needed
            'libssl',        # Not all parts needed
            'libcrypto',
            '*.dll.a',       # Static libs
        ]
        
        removed_size = 0
        
        for root, dirs, files in os.walk(app_dir):
            # Remove directories
            for dir_name in list(dirs):
                dir_path = Path(root) / dir_name
                
                # Check if should remove
                should_remove = False
                
                for pattern in remove_names:
                    if pattern in dir_name:
                        should_remove = True
                        break
                
                if should_remove and dir_path.exists():
                    try:
                        size = sum(
                            p.stat().st_size for p in dir_path.rglob('*')
                            if p.is_file()
                        )
                        removed_size += size
                        shutil.rmtree(dir_path)
                        logger.debug(f"Removed: {dir_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {dir_path}: {e}")
            
            # Remove files
            for file_name in list(files):
                file_path = Path(root) / file_name
                
                # Check by extension
                if file_path.suffix in remove_extensions:
                    try:
                        size = file_path.stat().st_size
                        removed_size += size
                        file_path.unlink()
                        logger.debug(f"Removed: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {file_path}: {e}")
        
        if removed_size > 0:
            removed_mb = removed_size / (1024 * 1024)
            logger.info(f"✓ Removed {removed_mb:.1f} MB")
    
    def calculate_size(self, directory: Path) -> float:
        """
        Calculate total size of directory.
        
        Args:
            directory: Directory path
        
        Returns:
            Size in MB
        """
        if not directory.exists():
            return 0
        
        total_size = sum(
            p.stat().st_size for p in directory.rglob('*')
            if p.is_file()
        )
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def build(self) -> bool:
        """
        Build VPN Client executable.
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("VPN Client Build Process")
        logger.info("=" * 60)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Clean old artifacts
        self.clean_build_artifacts()
        
        # Run PyInstaller
        if not self.run_pyinstaller():
            return False
        
        # Optimize distribution
        self.optimize_dist()
        
        # Calculate sizes
        dist_size = self.calculate_size(self.dist_dir)
        build_size = self.calculate_size(self.build_dir)
        
        logger.info("=" * 60)
        logger.info("Build Complete!")
        logger.info("=" * 60)
        logger.info(f"Distribution size: {dist_size:.1f} MB")
        logger.info(f"Build artifacts: {build_size:.1f} MB")
        logger.info(f"Executable: {self.dist_dir / 'VPN_Client' / 'VPN_Client.exe'}")
        logger.info("=" * 60)
        
        return True


def main():
    """Main entry point."""
    builder = VPNClientBuilder()
    
    success = builder.build()
    
    if success:
        logger.info("\n✓ Build successful! Run the executable:")
        logger.info(f"  {builder.dist_dir / 'VPN_Client' / 'VPN_Client.exe'}")
        sys.exit(0)
    else:
        logger.error("\n✗ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
