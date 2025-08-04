"""
Keycloak Management Utility
"""

import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class KeycloakUser:
    """Data class for Keycloak user"""

    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    enabled: bool = True
    email_verified: bool = False
    password: Optional[str] = "TemporaryPass123!"
    temporary_password: bool = True
    groups: Optional[List[str]] = None
    attributes: Optional[Dict[str, List[str]]] = None


class KeycloakManager:
    """Keycloak management utility for group and user management"""

    def __init__(
        self, keycloak_url: str, realm: str, admin_username: str, admin_password: str
    ):
        """
        Initialize Keycloak Manager

        Args:
            keycloak_url: Base Keycloak URL (e.g., 'http://kc.odl.local:7080')
            realm: Keycloak realm name
            admin_username: Admin username
            admin_password: Admin password
        """
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.access_token = None

    def get_admin_token(self) -> str:
        """Get admin access token for Keycloak API calls"""
        token_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]
        return self.access_token

    def get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token"""
        if not self.access_token:
            self.get_admin_token()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # GROUP MANAGEMENT METHODS
    def get_groups(self) -> List[Dict]:
        """Get all groups in the realm"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/groups"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def find_group_by_name(self, group_name: str) -> Optional[Dict]:
        """Find a group by name"""
        groups = self.get_groups()
        for group in groups:
            if group["name"] == group_name:
                return group
        return None

    def create_group(self, group_name: str, attributes: Optional[Dict] = None) -> Dict:
        """Create a new group"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/groups"

        group_data = {
            "name": group_name,
            "attributes": attributes or {"source": ["odl_video_service"]},
        }

        response = requests.post(url, json=group_data, headers=self.get_headers())
        response.raise_for_status()

        # Get the created group
        return self.find_group_by_name(group_name)

    def get_group_members(self, group_id: str) -> List[Dict]:
        """Get all members of a specific group"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/groups/{group_id}/members"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to a group"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/users/{user_id}/groups/{group_id}"
        response = requests.put(url, headers=self.get_headers())
        response.raise_for_status()
        return response.status_code == 204

    def list_exists(self, group_name: str) -> bool:
        """
        Check if a group exists

        Args:
            group_name (str): Name of the group to check

        Returns:
            bool: True if the group exists, False otherwise
        """
        group = self.find_group_by_name(group_name)
        return bool(group)

    def get_user_groups(self, username: str) -> List[str]:
        """
        Get a list of all groups a user is a member of

        Args:
            username (str): The username to query groups for

        Returns:
            List[str]: A list of names of groups which contain the user as a member
        """
        try:
            # Find the user first
            user = self.find_user_by_username(username)
            if not user:
                logger.warning(f"User {username} not found in Keycloak")
                return []

            # Get all groups
            all_groups = self.get_groups()
            user_groups = []

            # For each group, check if the user is a member
            for group in all_groups:
                group_members = self.get_group_members(group["id"])
                if any(member["username"] == username for member in group_members):
                    user_groups.append(group["name"])

            return user_groups
        except Exception as exc:
            logger.error(f"Error querying Keycloak groups for {username}: {exc}")
            return []

    def get_group_members_by_name(self, group_name: str) -> List[Dict]:
        """
        Get all members of a specific group by group name

        Args:
            group_name (str): Name of the group

        Returns:
            List[Dict]: List of user dictionaries in the group
        """
        try:
            # Find the group first
            group = self.find_group_by_name(group_name)
            if not group:
                logger.warning(f"Group {group_name} not found in Keycloak")
                return []

            # Get the group members
            return self.get_group_members(group["id"])
        except Exception as exc:
            logger.error(f"Error getting members for group {group_name}: {exc}")
            raise Exception(
                f"Something went wrong with getting Keycloak users for {group_name}"
            ) from exc

    # USER MANAGEMENT METHODS
    def get_users(self, max_users: int = 100, search: str = None) -> List[Dict]:
        """Get all users in the realm"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
        params = {"max": max_users}
        if search:
            params["search"] = search

        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def find_user_by_username(self, username: str) -> Optional[Dict]:
        """Find a user by username"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
        params = {"username": username, "exact": "true"}
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()

        users = response.json()
        return users[0] if users else None

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find a user by email"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
        params = {"email": email, "exact": "true"}
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()

        users = response.json()
        return users[0] if users else None

    def create_user(self, user: KeycloakUser) -> Dict:
        """Create a new user"""
        user_data = {
            "username": user.username,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "enabled": user.enabled,
            "emailVerified": True,
            "attributes": user.attributes or {"source": ["odl_video_service"]},
        }

        # Create the user
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
        response = requests.post(url, json=user_data, headers=self.get_headers())

        if response.status_code == 409:  # User already exists
            logger.warning(f"User '{user.username}' already exists")
            return self.find_user_by_username(user.email)

        response.raise_for_status()

        # Get the created user
        created_user = self.find_user_by_username(user.email)
        if not created_user:
            raise RuntimeError("Failed to retrieve created user")

        # Set password if provided
        if user.password:
            self.set_user_password(
                created_user["id"], user.password, user.temporary_password
            )

        # Add to groups if specified
        if user.groups:
            for group_name in user.groups:
                group = self.find_group_by_name(group_name)
                if group:
                    self.add_user_to_group(created_user["id"], group["id"])
                else:
                    logger.warning(
                        f"Group '{group_name}' not found, skipping group assignment"
                    )

        return created_user

    def set_user_password(
        self, user_id: str, password: str, temporary: bool = False
    ) -> bool:
        """Set user password"""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/users/{user_id}/reset-password"
        password_data = {"type": "password", "value": password, "temporary": temporary}

        response = requests.put(url, json=password_data, headers=self.get_headers())
        response.raise_for_status()
        return response.status_code == 204

    def create_users_bulk(self, users: List[KeycloakUser]) -> List[Dict]:
        """Create multiple users at once"""
        created_users = []
        for user in users:
            try:
                created_user = self.create_user(user)
                created_users.append(created_user)
                logger.info(f"Created/found user: {user.username}")
            except Exception as e:
                logger.error(f"Failed to create user {user.username}: {e}")

        return created_users


def get_keycloak_client() -> KeycloakManager:
    """
    Creates a new Keycloak client configured with settings from Django settings.
    This creates a fresh connection each time without caching the instance.

    Returns:
        KeycloakManager: A new Keycloak client instance
    """
    try:
        # Ensure we have the necessary settings
        if (
            not hasattr(settings, "KEYCLOAK_SERVER_URL")
            or not settings.KEYCLOAK_SERVER_URL
        ):
            raise ValueError("KEYCLOAK_SERVER_URL setting is missing")
        if not hasattr(settings, "KEYCLOAK_REALM") or not settings.KEYCLOAK_REALM:
            raise ValueError("KEYCLOAK_REALM setting is missing")
        if (
            not hasattr(settings, "KEYCLOAK_SVC_ADMIN")
            or not settings.KEYCLOAK_SVC_ADMIN
        ):
            raise ValueError("KEYCLOAK_SVC_ADMIN setting is missing")
        if (
            not hasattr(settings, "KEYCLOAK_SVC_ADMIN_PASSWORD")
            or not settings.KEYCLOAK_SVC_ADMIN_PASSWORD
        ):
            raise ValueError("KEYCLOAK_SVC_ADMIN_PASSWORD setting is missing")

        return KeycloakManager(
            keycloak_url=settings.KEYCLOAK_SERVER_URL,
            realm=settings.KEYCLOAK_REALM,
            admin_username=settings.KEYCLOAK_SVC_ADMIN,
            admin_password=settings.KEYCLOAK_SVC_ADMIN_PASSWORD,
        )
    except Exception as exc:
        logger.error(f"Failed to create Keycloak client: {exc}")
        raise Exception("Something went wrong with creating a Keycloak client") from exc
