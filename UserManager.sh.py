#!/usr/bin/env python3
"""
User Management Script
Supports Linux and Windows systems for creating, deleting users, and updating passwords.
Must be run with appropriate privileges (root/sudo on Linux, Administrator on Windows).
"""

import argparse
import getpass
import sys
import logging
from typing import Optional

# Platform-specific imports
try:
    if sys.platform == "win32":
        import pywin32_wrapper as win32
    else:
        import pwd
        import grp
        import spwd
        import subprocess
except ImportError as e:
    print(f"Required module not available: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('user_management.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        self.system = sys.platform
        
    def user_exists(self, username: str) -> bool:
        """Check if a user exists on the system."""
        try:
            if self.system == "win32":
                # Windows implementation
                try:
                    import win32net
                    win32net.NetUserGetInfo(None, username, 1)
                    return True
                except Exception:
                    return False
            else:
                # Linux/Unix implementation
                pwd.getpwnam(username)
                return True
        except (KeyError, Exception):
            return False

    def create_user(self, username: str, password: Optional[str] = None, 
                   shell: str = "/bin/bash", home_dir: Optional[str] = None,
                   create_home: bool = True, system_user: bool = False) -> bool:
        """
        Create a new user on the system.
        
        Args:
            username: Name of the user to create
            password: User password (if None, will be prompted or account disabled)
            shell: Default shell for the user
            home_dir: Home directory path
            create_home: Whether to create home directory
            system_user: Whether to create as system user
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        if self.user_exists(username):
            logger.error(f"User '{username}' already exists")
            return False
            
        try:
            if self.system == "win32":
                return self._create_user_windows(username, password)
            else:
                return self._create_user_linux(username, password, shell, home_dir, create_home, system_user)
        except Exception as e:
            logger.error(f"Failed to create user '{username}': {e}")
            return False

    def _create_user_linux(self, username: str, password: Optional[str], 
                          shell: str, home_dir: Optional[str], 
                          create_home: bool, system_user: bool) -> bool:
        """Create user on Linux systems."""
        try:
            # Build useradd command
            cmd = ["sudo", "useradd"]
            
            if system_user:
                cmd.append("-r")
                
            if home_dir:
                cmd.extend(["-d", home_dir])
            elif create_home:
                cmd.extend(["-m", "-d", f"/home/{username}"])
            else:
                cmd.append("-M")
                
            if shell:
                cmd.extend(["-s", shell])
                
            cmd.append(username)
            
            # Execute user creation
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Set password if provided
            if password:
                self.update_password(username, password)
            else:
                logger.warning(f"User '{username}' created without password - account may be disabled")
                
            logger.info(f"Successfully created user '{username}'")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"useradd command failed: {e.stderr}")
            return False

    def _create_user_windows(self, username: str, password: Optional[str]) -> bool:
        """Create user on Windows systems."""
        try:
            import win32net
            import win32netcon
            
            user_info = {
                'name': username,
                'password': password or "",
                'priv': win32netcon.USER_PRIV_USER,
                'home_dir': None,
                'comment': f"Created by Python UserManager",
                'flags': win32netcon.UF_SCRIPT | win32netcon.UF_DONT_EXPIRE_PASSWD,
            }
            
            win32net.NetUserAdd(None, 1, user_info)
            
            if not password:
                logger.warning(f"User '{username}' created with empty password")
            else:
                logger.info(f"Successfully created user '{username}' with password")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Windows user '{username}': {e}")
            return False

    def delete_user(self, username: str, remove_home: bool = False) -> bool:
        """
        Delete a user from the system.
        
        Args:
            username: Name of the user to delete
            remove_home: Whether to remove home directory (Linux) or profile (Windows)
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        if not self.user_exists(username):
            logger.error(f"User '{username}' does not exist")
            return False
            
        try:
            if self.system == "win32":
                return self._delete_user_windows(username, remove_home)
            else:
                return self._delete_user_linux(username, remove_home)
        except Exception as e:
            logger.error(f"Failed to delete user '{username}': {e}")
            return False

    def _delete_user_linux(self, username: str, remove_home: bool) -> bool:
        """Delete user on Linux systems."""
        try:
            cmd = ["sudo", "userdel"]
            if remove_home:
                cmd.append("-r")
            cmd.append(username)
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully deleted user '{username}'")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"userdel command failed: {e.stderr}")
            return False

    def _delete_user_windows(self, username: str, remove_home: bool) -> bool:
        """Delete user on Windows systems."""
        try:
            import win32net
            win32net.NetUserDel(None, username)
            
            if remove_home:
                # Note: Windows profile removal is more complex and may require additional steps
                logger.warning("Home directory removal not implemented for Windows in this script")
                
            logger.info(f"Successfully deleted user '{username}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Windows user '{username}': {e}")
            return False

    def update_password(self, username: str, password: Optional[str] = None) -> bool:
        """
        Update user password.
        
        Args:
            username: Name of the user
            password: New password (if None, will be prompted)
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        if not self.user_exists(username):
            logger.error(f"User '{username}' does not exist")
            return False
            
        if password is None:
            password = getpass.getpass(f"Enter new password for {username}: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                logger.error("Passwords do not match")
                return False
                
        try:
            if self.system == "win32":
                return self._update_password_windows(username, password)
            else:
                return self._update_password_linux(username, password)
        except Exception as e:
            logger.error(f"Failed to update password for '{username}': {e}")
            return False

    def _update_password_linux(self, username: str, password: str) -> bool:
        """Update password on Linux systems."""
        try:
            # Use chpasswd for secure password setting
            process = subprocess.Popen(
                ["sudo", "chpasswd"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=f"{username}:{password}\n")
            
            if process.returncode == 0:
                logger.info(f"Successfully updated password for '{username}'")
                return True
            else:
                logger.error(f"chpasswd failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Password update failed for '{username}': {e}")
            return False

    def _update_password_windows(self, username: str, password: str) -> bool:
        """Update password on Windows systems."""
        try:
            import win32net
            import win32netcon
            
            user_info = {
                'name': username,
                'password': password,
                'priv': win32netcon.USER_PRIV_USER,
            }
            
            win32net.NetUserSetInfo(None, username, 1, user_info)
            logger.info(f"Successfully updated password for '{username}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Windows password for '{username}': {e}")
            return False

    def list_users(self, pattern: Optional[str] = None) -> None:
        """List all users on the system, optionally filtered by pattern."""
        try:
            if self.system == "win32":
                self._list_users_windows(pattern)
            else:
                self._list_users_linux(pattern)
        except Exception as e:
            logger.error(f"Failed to list users: {e}")

    def _list_users_linux(self, pattern: Optional[str]) -> None:
        """List users on Linux systems."""
        try:
            users = []
            for user in pwd.getpwall():
                username = user.pw_name
                if pattern and pattern.lower() not in username.lower():
                    continue
                if user.pw_uid >= 1000 or user.pw_uid == 0:  # Filter system users
                    users.append((username, user.pw_uid, user.pw_gecos or "No description"))
            
            if users:
                print(f"\n{'Username':<20} {'UID':<10} {'Description':<30}")
                print("-" * 60)
                for username, uid, desc in sorted(users):
                    print(f"{username:<20} {uid:<10} {desc:<30}")
            else:
                print("No users found")
                
        except Exception as e:
            logger.error(f"Failed to list Linux users: {e}")

    def _list_users_windows(self, pattern: Optional[str]) -> None:
        """List users on Windows systems."""
        try:
            import win32net
            
            users = []
            resume_handle = 0
            
            while True:
                result, total, resume_handle = win32net.NetUserEnum(
                    None, 0, win32netcon.FILTER_NORMAL_ACCOUNT, resume_handle
                )
                
                for user in result:
                    username = user['name']
                    if pattern and pattern.lower() not in username.lower():
                        continue
                    users.append((username, user['full_name'] or "No full name"))
                
                if not resume_handle:
                    break
            
            if users:
                print(f"\n{'Username':<30} {'Full Name':<30}")
                print("-" * 60)
                for username, fullname in sorted(users):
                    print(f"{username:<30} {fullname:<30}")
            else:
                print("No users found")
                
        except Exception as e:
            logger.error(f"Failed to list Windows users: {e}")

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="User Management Script")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create user command
    create_parser = subparsers.add_parser('create', help='Create a new user')
    create_parser.add_argument('username', help='Username to create')
    create_parser.add_argument('-p', '--password', help='User password')
    create_parser.add_argument('--shell', default='/bin/bash', help='User shell (Linux only)')
    create_parser.add_argument('--home-dir', help='Home directory path')
    create_parser.add_argument('--no-create-home', action='store_true', help='Do not create home directory')
    create_parser.add_argument('--system', action='store_true', help='Create as system user')
    
    # Delete user command
    delete_parser = subparsers.add_parser('delete', help='Delete a user')
    delete_parser.add_argument('username', help='Username to delete')
    delete_parser.add_argument('-r', '--remove-home', action='store_true', help='Remove home directory')
    
    # Update password command
    password_parser = subparsers.add_parser('password', help='Update user password')
    password_parser.add_argument('username', help='Username to update')
    password_parser.add_argument('-p', '--password', help='New password')
    
    # List users command
    list_parser = subparsers.add_parser('list', help='List users')
    list_parser.add_argument('-p', '--pattern', help='Filter users by pattern')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = UserManager()
    
    try:
        if args.command == 'create':
            success = manager.create_user(
                username=args.username,
                password=args.password,
                shell=args.shell,
                home_dir=args.home_dir,
                create_home=not args.no_create_home,
                system_user=args.system
            )
            if not success:
                sys.exit(1)
                
        elif args.command == 'delete':
            success = manager.delete_user(args.username, args.remove_home)
            if not success:
                sys.exit(1)
                
        elif args.command == 'password':
            success = manager.update_password(args.username, args.password)
            if not success:
                sys.exit(1)
                
        elif args.command == 'list':
            manager.list_users(args.pattern)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if running with appropriate privileges
    if sys.platform != "win32" and getpass.getuser() != "root":
        print("Error: This script must be run as root on Linux systems", file=sys.stderr)
        sys.exit(1)
        
    main()