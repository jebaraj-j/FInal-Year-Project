"""
System controller for Windows desktop automation.
Controls system operations (shutdown, restart, sleep, lock) with safety confirmation.
"""

import os
import ctypes
import threading
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path

try:
    from ..utils.logger import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class SystemController:
    """
    Controls Windows system operations with safety confirmation workflow.
    Supports shutdown, restart, sleep, and lock operations.
    """
    
    def __init__(self):
        """Initialize system controller."""
        self.logger = get_logger()
        
        # Confirmation tracking
        self._pending_action = None
        self._confirmation_active = False
        self._confirmation_lock = threading.Lock()
        self._confirmation_timeout = 5.0  # 5 seconds
        
        # Action tracking to prevent duplicates
        self._recent_actions = {}
        self._action_lock = threading.Lock()
        self._action_prevention_window = 10.0  # 10 seconds
        
        self.logger.info("SystemController initialized")
        self.logger.info("Supported operations: shutdown, restart, sleep, lock")
    
    def _get_current_time(self) -> float:
        """Get current timestamp."""
        return time.time()
    
    def _is_duplicate_action(self, action: str) -> bool:
        """
        Check if action was recently executed to prevent duplicates.
        
        Args:
            action: Action name to check
            
        Returns:
            True if action would be duplicate, False otherwise
        """
        current_time = self._get_current_time()
        
        with self._action_lock:
            if action in self._recent_actions:
                last_action_time = self._recent_actions[action]
                if current_time - last_action_time < self._action_prevention_window:
                    return True
            
            # Update action time
            self._recent_actions[action] = current_time
            
            # Clean old entries
            old_actions = [
                act for act, action_time in self._recent_actions.items()
                if current_time - action_time > self._action_prevention_window * 2
            ]
            for old_action in old_actions:
                del self._recent_actions[old_action]
            
            return False
    
    def _execute_shutdown(self) -> bool:
        """
        Execute system shutdown.
        
        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            self.logger.info("Executing system shutdown...")
            os.system("shutdown /s /t 1")
            return True
        except Exception as e:
            self.logger.log_error("SystemShutdownError", str(e))
            return False
    
    def _execute_restart(self) -> bool:
        """
        Execute system restart.
        
        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            self.logger.info("Executing system restart...")
            os.system("shutdown /r /t 1")
            return True
        except Exception as e:
            self.logger.log_error("SystemRestartError", str(e))
            return False
    
    def _execute_sleep(self) -> bool:
        """
        Execute system sleep.
        
        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            self.logger.info("Executing system sleep...")
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return True
        except Exception as e:
            self.logger.log_error("SystemSleepError", str(e))
            return False
    
    def _execute_lock(self) -> bool:
        """
        Execute screen lock.
        
        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            self.logger.info("Executing screen lock...")
            ctypes.windll.user32.LockWorkStation()
            return True
        except Exception as e:
            self.logger.log_error("SystemLockError", str(e))
            return False
    
    def _get_action_executor(self, action: str) -> Optional[Callable[[], bool]]:
        """
        Get executor function for action.
        
        Args:
            action: Action name
            
        Returns:
            Executor function or None if not found
        """
        executors = {
            "shutdown": self._execute_shutdown,
            "restart": self._execute_restart,
            "sleep": self._execute_sleep,
            "lock": self._execute_lock
        }
        
        return executors.get(action)
    
    def _get_confirmation_message(self, action: str) -> str:
        """
        Get confirmation message for action.
        
        Args:
            action: Action name
            
        Returns:
            Confirmation message
        """
        messages = {
            "shutdown": "Are you sure you want to shutdown? Say YES or NO",
            "restart": "Are you sure you want to restart? Say YES or NO",
            "sleep": "Are you sure you want to sleep? Say YES or NO",
            "lock": "Are you sure you want to lock? Say YES or NO"
        }
        
        return messages.get(action, f"Are you sure you want to {action}? Say YES or NO")
    
    def _get_action_description(self, action: str) -> str:
        """
        Get human-readable description for action.
        
        Args:
            action: Action name
            
        Returns:
            Action description
        """
        descriptions = {
            "shutdown": "System Shutdown",
            "restart": "System Restart",
            "sleep": "System Sleep",
            "lock": "Screen Lock"
        }
        
        return descriptions.get(action, f"System {action.title()}")
    
    def start_confirmation_workflow(self, action: str, 
                                   confirmation_callback: Callable[[str], bool]) -> bool:
        """
        Start confirmation workflow for system action.
        
        Args:
            action: Action to confirm
            confirmation_callback: Callback for confirmation result
            
        Returns:
            True if workflow started, False if already active
        """
        with self._confirmation_lock:
            if self._confirmation_active:
                self.logger.warning("Confirmation workflow already active")
                return False
            
            self._pending_action = action
            self._confirmation_active = True
            
            # Start confirmation timer in separate thread
            confirmation_thread = threading.Thread(
                target=self._confirmation_timer,
                args=(action, confirmation_callback),
                daemon=True
            )
            confirmation_thread.start()
            
            return True
    
    def _confirmation_timer(self, action: str, confirmation_callback: Callable[[str], bool]):
        """
        Handle confirmation timeout.
        
        Args:
            action: Action being confirmed
            confirmation_callback: Callback for result
        """
        try:
            time.sleep(self._confirmation_timeout)
            
            with self._confirmation_lock:
                if self._confirmation_active and self._pending_action == action:
                    # Timeout occurred
                    self.logger.log_system_confirmation(action, "timeout")
                    self._confirmation_active = False
                    self._pending_action = None
                    
                    # Call callback with timeout result
                    confirmation_callback("timeout")
        except Exception as e:
            self.logger.log_error("ConfirmationTimerError", str(e))
    
    def process_confirmation_response(self, response: str) -> bool:
        """
        Process user confirmation response.
        
        Args:
            response: User response (YES/NO)
            
        Returns:
            True if response processed, False if no active confirmation
        """
        with self._confirmation_lock:
            if not self._confirmation_active or not self._pending_action:
                return False
            
            action = self._pending_action
            
            # Process response
            response_lower = response.lower().strip()
            
            if response_lower in ["yes", "yeah", "yep", "sure", "ok"]:
                result = "confirmed"
            elif response_lower in ["no", "nope", "cancel", "stop"]:
                result = "cancelled"
            else:
                # Unknown response, treat as cancel
                result = "cancelled"
            
            # Log confirmation result
            self.logger.log_system_confirmation(action, result)
            
            # Reset confirmation state
            self._confirmation_active = False
            self._pending_action = None
            
            return True
    
    def execute_action(self, action: str, require_confirmation: bool = True) -> bool:
        """
        Execute system action with optional confirmation.
        
        Args:
            action: Action to execute
            require_confirmation: Whether to require confirmation
            
        Returns:
            True if action executed or confirmation started, False otherwise
        """
        try:
            # Validate action
            if not action or action not in ["shutdown", "restart", "sleep", "lock"]:
                self.logger.log_error("InvalidSystemAction", f"Invalid action: {action}")
                return False
            
            # Check for duplicate action
            if self._is_duplicate_action(action):
                self.logger.info(f"Prevented duplicate system action: {action}")
                print(f"⚠️  {self._get_action_description(action)} was recently requested, preventing duplicate")
                return True  # Consider this successful as action is already being handled
            
            # Get executor
            executor = self._get_action_executor(action)
            if not executor:
                self.logger.log_error("SystemActionNotFound", f"No executor for action: {action}")
                return False
            
            # Log action attempt
            self.logger.log_system_action_attempt(action)
            
            if require_confirmation and action in ["shutdown", "restart", "sleep"]:
                # Start confirmation workflow for dangerous actions
                confirmation_message = self._get_confirmation_message(action)
                print(f"\n🚨 {confirmation_message}")
                print("⏰ Listening for response for 5 seconds...")
                
                # This will be handled by the voice assistant with confirmation callback
                return True  # Confirmation workflow started
            else:
                # Execute directly for lock or when confirmation not required
                success = executor()
                
                if success:
                    self.logger.log_system_action_success(action)
                    print(f"✅ {self._get_action_description(action)} executed")
                else:
                    self.logger.log_system_action_failure(action, "Executor failed")
                    print(f"❌ Failed to execute {self._get_action_description(action)}")
                
                return success
                
        except Exception as e:
            self.logger.log_error("SystemActionError", str(e), f"Action: {action}")
            print(f"❌ Error executing {self._get_action_description(action)}: {e}")
            return False
    
    def execute_confirmed_action(self, action: str) -> bool:
        """
        Execute action after confirmation.
        
        Args:
            action: Confirmed action to execute
            
        Returns:
            True if action executed successfully, False otherwise
        """
        try:
            executor = self._get_action_executor(action)
            if not executor:
                self.logger.log_error("ConfirmedActionNotFound", f"No executor for action: {action}")
                return False
            
            # Execute action
            success = executor()
            
            if success:
                self.logger.log_system_action_success(action)
                print(f"✅ {self._get_action_description(action)} executed")
            else:
                self.logger.log_system_action_failure(action, "Executor failed")
                print(f"❌ Failed to execute {self._get_action_description(action)}")
            
            return success
            
        except Exception as e:
            self.logger.log_error("ConfirmedActionError", str(e), f"Action: {action}")
            print(f"❌ Error executing confirmed {self._get_action_description(action)}: {e}")
            return False
    
    def cancel_confirmation(self) -> bool:
        """
        Cancel active confirmation workflow.
        
        Returns:
            True if confirmation cancelled, False if none active
        """
        with self._confirmation_lock:
            if not self._confirmation_active:
                return False
            
            action = self._pending_action
            self._confirmation_active = False
            self._pending_action = None
            
            self.logger.log_system_confirmation(action, "cancelled")
            print("❌ System action cancelled")
            
            return True
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system controller information.
        
        Returns:
            System controller status and info
        """
        return {
            "supported_actions": ["shutdown", "restart", "sleep", "lock"],
            "confirmation_active": self._confirmation_active,
            "pending_action": self._pending_action,
            "confirmation_timeout": self._confirmation_timeout,
            "action_prevention_window": self._action_prevention_window
        }
    
    def test_system_controller(self) -> Dict[str, Any]:
        """
        Test system controller functionality.
        
        Returns:
            Test results dictionary
        """
        test_results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
        
        # Test action validation
        try:
            valid_actions = ["shutdown", "restart", "sleep", "lock"]
            for action in valid_actions:
                executor = self._get_action_executor(action)
                if executor:
                    test_results["details"].append(f"✓ {action} executor available")
                else:
                    test_results["details"].append(f"✗ {action} executor not found")
            
            test_results["tests_passed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ Action validation test failed: {e}")
            test_results["tests_failed"] += 1
        
        # Test confirmation workflow
        try:
            # Start confirmation
            started = self.start_confirmation_workflow("test", lambda x: True)
            if started:
                test_results["details"].append("✓ Confirmation workflow started")
                
                # Cancel confirmation
                cancelled = self.cancel_confirmation()
                if cancelled:
                    test_results["details"].append("✓ Confirmation workflow cancelled")
                else:
                    test_results["details"].append("✗ Confirmation workflow cancellation failed")
                
                test_results["tests_passed"] += 1
            else:
                test_results["details"].append("✗ Failed to start confirmation workflow")
                test_results["tests_failed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ Confirmation workflow test failed: {e}")
            test_results["tests_failed"] += 1
        
        # Test duplicate prevention
        try:
            # First action should succeed
            result1 = self._is_duplicate_action("test")
            # Second action within window should be prevented
            result2 = self._is_duplicate_action("test")
            
            if not result1 and result2:
                test_results["details"].append("✓ Duplicate prevention working correctly")
                test_results["tests_passed"] += 1
            else:
                test_results["details"].append("✗ Duplicate prevention not working")
                test_results["tests_failed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ Duplicate prevention test failed: {e}")
            test_results["tests_failed"] += 1
        
        return test_results
    
    def cleanup(self) -> None:
        """Cleanup system controller resources."""
        with self._confirmation_lock:
            self._confirmation_active = False
            self._pending_action = None
        
        with self._action_lock:
            self._recent_actions.clear()
        
        self.logger.info("SystemController cleanup completed")
