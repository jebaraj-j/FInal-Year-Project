"""
Application launcher controller for Windows desktop automation.
Launches applications using subprocess with path validation and error handling.
"""

import os
import subprocess
import time
import threading
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from ..utils.logger import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class ApplicationLauncher:
    """
    Controls application launching on Windows systems.
    Supports configurable app paths with validation and error handling.
    """
    
    def __init__(self):
        """Initialize application launcher."""
        self.logger = get_logger()
        
        # Load app configuration
        self.app_paths = self._load_app_config()
        
        # Launch tracking to prevent duplicates
        self._recent_launches = {}
        self._launch_lock = threading.Lock()
        self._duplicate_prevention_window = 3.0  # 3 seconds
        
        self.logger.info("ApplicationLauncher initialized")
        self.logger.info(f"Loaded {len(self.app_paths)} application configurations")
    
    def _load_app_config(self) -> Dict[str, str]:
        """
        Load application paths from configuration file.
        
        Returns:
            Dictionary mapping app names to executable paths
        """
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'apps.json'
            
            if not config_path.exists():
                self.logger.log_error("AppConfigNotFound", f"Configuration file not found: {config_path}")
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
            
            # Validate and normalize paths
            validated_paths = {}
            for app_name, app_path in config.items():
                if self._validate_app_path(app_path, app_name):
                    validated_paths[app_name.lower()] = app_path
                else:
                    self.logger.log_error("InvalidAppPath", f"Invalid path for {app_name}: {app_path}")
            
            self.logger.info(f"Validated {len(validated_paths)} application paths")
            return validated_paths
            
        except Exception as e:
            self.logger.log_error("AppConfigLoadError", str(e))
            return {}
    
    def _validate_app_path(self, app_path: str, app_name: str) -> bool:
        """
        Validate application path exists and is accessible.
        
        Args:
            app_path: Path to application executable
            app_name: Name of application for logging
            
        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Handle special cases (Windows settings, system commands)
            if app_path.startswith('ms-settings:') or app_path in ['notepad.exe', 'explorer.exe']:
                return True
            
            # Check if path exists
            path_obj = Path(app_path)
            if path_obj.exists() and path_obj.is_file():
                return True
            
            # Try to resolve environment variables
            expanded_path = os.path.expandvars(app_path)
            path_obj = Path(expanded_path)
            if path_obj.exists() and path_obj.is_file():
                return True
            
            # Check if executable exists in system PATH
            if os.path.isfile(app_path) or any(
                Path(os.path.join(path, app_path)).exists()
                for path in os.environ.get('PATH', '').split(os.pathsep)
            ):
                return True
            
            return False
            
        except Exception as e:
            self.logger.log_error("AppPathValidationError", str(e), f"App: {app_name}")
            return False
    
    def _is_duplicate_launch(self, app_name: str) -> bool:
        """
        Check if application was recently launched to prevent duplicates.
        
        Args:
            app_name: Name of application to check
            
        Returns:
            True if launch would be duplicate, False otherwise
        """
        current_time = time.time()
        
        with self._launch_lock:
            if app_name in self._recent_launches:
                last_launch_time = self._recent_launches[app_name]
                if current_time - last_launch_time < self._duplicate_prevention_window:
                    return True
            
            # Update launch time
            self._recent_launches[app_name] = current_time
            
            # Clean old entries
            old_apps = [
                app for app, launch_time in self._recent_launches.items()
                if current_time - launch_time > self._duplicate_prevention_window * 2
            ]
            for old_app in old_apps:
                del self._recent_launches[old_app]
            
            return False
    
    def get_app_path(self, app_name: str) -> Optional[str]:
        """
        Get application path from configuration.
        
        Args:
            app_name: Name of application
            
        Returns:
            Application path or None if not found
        """
        app_key = app_name.lower()
        return self.app_paths.get(app_key)
    
    def validate_app(self, app_name: str) -> bool:
        """
        Validate application exists in configuration.
        
        Args:
            app_name: Name of application to validate
            
        Returns:
            True if app is valid, False otherwise
        """
        app_path = self.get_app_path(app_name)
        return app_path is not None
    
    def open_app(self, app_name: str) -> bool:
        """
        Launch application with validation and error handling.
        
        Args:
            app_name: Name of application to launch
            
        Returns:
            True if launch successful, False otherwise
        """
        try:
            # Validate app name
            if not app_name or not app_name.strip():
                self.logger.log_error("AppLaunchError", "Empty app name provided")
                return False
            
            app_name = app_name.strip().lower()
            
            # Check for duplicate launch
            if self._is_duplicate_launch(app_name):
                self.logger.info(f"Prevented duplicate launch of {app_name}")
                print(f"⚠️  {app_name} was recently launched, preventing duplicate")
                return True  # Consider this successful as app is already being launched
            
            # Get app path
            app_path = self.get_app_path(app_name)
            if not app_path:
                self.logger.log_error("AppNotFoundError", f"Application not found in configuration: {app_name}")
                print(f"❌ Application '{app_name}' not found in configuration")
                return False
            
            # Launch application
            success = self._launch_application(app_name, app_path)
            
            if success:
                self.logger.log_app_launch(app_name, app_path)
                print(f"✅ Launched {app_name}")
            else:
                self.logger.log_error("AppLaunchFailed", f"Failed to launch {app_name}")
                print(f"❌ Failed to launch {app_name}")
            
            return success
            
        except Exception as e:
            self.logger.log_error("AppLaunchError", str(e), f"App: {app_name}")
            print(f"❌ Error launching {app_name}: {e}")
            return False
    
    def _launch_application(self, app_name: str, app_path: str) -> bool:
        """
        Launch application using appropriate method.
        
        Args:
            app_name: Name of application
            app_path: Path to application executable
            
        Returns:
            True if launch successful, False otherwise
        """
        try:
            # Handle special cases
            if app_path.startswith('ms-settings:'):
                # Windows Settings
                subprocess.Popen(['start', app_path], shell=True)
                return True
            
            elif app_path == 'notepad.exe':
                # Notepad
                subprocess.Popen(['notepad.exe'], shell=True)
                return True
            
            elif app_path == 'explorer.exe':
                # File Explorer
                subprocess.Popen(['explorer.exe'], shell=True)
                return True
            
            else:
                # Regular executable
                # Expand environment variables
                expanded_path = os.path.expandvars(app_path)
                
                # Check if path exists
                if not os.path.exists(expanded_path):
                    self.logger.log_error("AppPathNotFound", f"Application path not found: {expanded_path}")
                    return False
                
                # Launch application
                subprocess.Popen([expanded_path], shell=True)
                return True
                
        except FileNotFoundError as e:
            self.logger.log_error("AppFileNotFoundError", str(e), f"App: {app_name}, Path: {app_path}")
            return False
        except PermissionError as e:
            self.logger.log_error("AppPermissionError", str(e), f"App: {app_name}")
            return False
        except subprocess.SubprocessError as e:
            self.logger.log_error("AppSubprocessError", str(e), f"App: {app_name}")
            return False
        except Exception as e:
            self.logger.log_error("AppLaunchUnexpectedError", str(e), f"App: {app_name}")
            return False

    def close_app(self, app_name: str) -> bool:
        """
        Close application process with validation and error handling.

        Args:
            app_name: Name of application to close

        Returns:
            True if close successful (or app is already not running), False otherwise
        """
        try:
            if not app_name or not app_name.strip():
                self.logger.log_error("AppCloseError", "Empty app name provided")
                return False

            app_name = app_name.strip().lower()
            success = self._close_application(app_name)

            if success:
                self.logger.info(f"Closed {app_name}")
            else:
                self.logger.log_error("AppCloseFailed", f"Failed to close {app_name}")

            return success
        except Exception as e:
            self.logger.log_error("AppCloseError", str(e), f"App: {app_name}")
            return False

    def _close_application(self, app_name: str) -> bool:
        """
        Close application using Windows taskkill.

        Args:
            app_name: Logical app name from config/action (e.g., code, chrome)

        Returns:
            True when process closes or is already not running, False otherwise
        """
        process_map = {
            "chrome": "chrome.exe",
            "code": "Code.exe",
            "notepad": "notepad.exe",
            "settings": "SystemSettings.exe",
            "explorer": "explorer.exe",
        }
        process_name = process_map.get(app_name, f"{app_name}.exe")

        try:
            result = subprocess.run(
                ["taskkill", "/IM", process_name, "/F"],
                capture_output=True,
                text=True,
                timeout=6,
            )

            if result.returncode == 0:
                return True

            combined_output = f"{result.stdout}\n{result.stderr}".lower()
            if "not found" in combined_output or "no running instance" in combined_output:
                return True

            return False
        except Exception as e:
            self.logger.log_error("AppCloseUnexpectedError", str(e), f"App: {app_name}")
            return False
    
    def execute_action(self, action: str, value: Optional[Any] = None) -> bool:
        """
        Execute app launch action (for consistency with other controllers).
        
        Args:
            action: Action name (e.g., "open_chrome", "open_code")
            value: Not used for app launcher, kept for consistency
            
        Returns:
            True if successful, False otherwise
        """
        # Extract app name from action (e.g., "open_chrome" -> "chrome")
        if action.startswith("open_"):
            app_name = action.replace("open_", "")
            return self.open_app(app_name)
        if action.startswith("close_"):
            app_name = action.replace("close_", "")
            return self.close_app(app_name)

        app_name = action
        return self.open_app(app_name)
    
    def get_available_apps(self) -> Dict[str, str]:
        """
        Get list of available applications.
        
        Returns:
            Dictionary of app names and their paths
        """
        return self.app_paths.copy()
    
    def get_app_info(self, app_name: str) -> Dict[str, Any]:
        """
        Get information about an application.
        
        Args:
            app_name: Name of application
            
        Returns:
            Dictionary with app information
        """
        app_path = self.get_app_path(app_name)
        
        if not app_path:
            return {
                "available": False,
                "error": f"Application '{app_name}' not found in configuration"
            }
        
        info = {
            "available": True,
            "name": app_name,
            "path": app_path,
            "validated": self._validate_app_path(app_path, app_name)
        }
        
        # Add additional info if path exists
        if info["validated"] and not app_path.startswith('ms-settings:'):
            try:
                path_obj = Path(os.path.expandvars(app_path))
                if path_obj.exists():
                    info["file_size"] = path_obj.stat().st_size
                    info["modified_time"] = path_obj.stat().st_mtime
            except:
                pass  # Ignore additional info errors
        
        return info
    
    def test_app_launcher(self) -> Dict[str, Any]:
        """
        Test application launcher functionality.
        
        Returns:
            Test results dictionary
        """
        test_results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
        
        # Test configuration loading
        try:
            apps_count = len(self.app_paths)
            test_results["details"].append(f"✓ Configuration loaded: {apps_count} applications")
            test_results["tests_passed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ Configuration loading failed: {e}")
            test_results["tests_failed"] += 1
        
        # Test app validation
        try:
            valid_apps = [app for app in self.app_paths.keys() if self.validate_app(app)]
            test_results["details"].append(f"✓ App validation: {len(valid_apps)} valid applications")
            test_results["tests_passed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ App validation failed: {e}")
            test_results["tests_failed"] += 1
        
        # Test duplicate prevention
        try:
            test_app = list(self.app_paths.keys())[0] if self.app_paths else None
            if test_app:
                # First launch should succeed
                result1 = self._is_duplicate_launch(test_app)
                # Second launch within window should be prevented
                result2 = self._is_duplicate_launch(test_app)
                
                if not result1 and result2:
                    test_results["details"].append("✓ Duplicate prevention working correctly")
                    test_results["tests_passed"] += 1
                else:
                    test_results["details"].append("✗ Duplicate prevention not working")
                    test_results["tests_failed"] += 1
            else:
                test_results["details"].append("⚠️  No apps available for duplicate test")
                test_results["tests_passed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ Duplicate prevention test failed: {e}")
            test_results["tests_failed"] += 1
        
        return test_results
    
    def cleanup(self) -> None:
        """Cleanup launcher resources."""
        with self._launch_lock:
            self._recent_launches.clear()
        
        self.logger.info("ApplicationLauncher cleanup completed")
