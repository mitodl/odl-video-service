"""
Keycloak Management Utility
"""

import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from django.conf import settings

from ui.exceptions import KeycloakException

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
        """
        Get admin access token for Keycloak API calls

        Returns:
            str: The access token

        Raises:
            requests.exceptions.RequestException: If the token request fails
        """
        token_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
        }

        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            return self.access_token
        except requests.exceptions.RequestException as exc:
            logger.error(f"Failed to get Keycloak admin token: {exc}")
            raise

    def get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token"""
        if not self.access_token:
            self.get_admin_token()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _make_api_request(
        self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None
    ) -> Dict:
        """
        Make an API request to Keycloak

        Args:
            method: HTTP method (get, post, put, delete)
            endpoint: API endpoint path (without base URL and realm)
            params: Queparametery rs
            json_data: JSON body data for POST/PUT requests

        Returns:
            Dict: JSON response from the API

        Raises:
            requests.exceptions.HTTPError: If the API request fails with a non-2xx status
            requests.exceptions.RequestException: For other request errors (connection, timeout, etc.)
        """
        url = f"{self.keycloak_url}{endpoint}"

        try:
            if not self.access_token:
                self.get_admin_token()

            if method.lower() == "get":
                response = requests.get(url, headers=self.get_headers(), params=params)
            elif method.lower() == "post":
                response = requests.post(
                    url, headers=self.get_headers(), params=params, json=json_data
                )
            elif method.lower() == "put":
                response = requests.put(
                    url, headers=self.get_headers(), params=params, json=json_data
                )
            elif method.lower() == "delete":
                response = requests.delete(
                    url, headers=self.get_headers(), params=params
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # If we get a 401, the token might be expired, so we'll try again
            if response.status_code == 401:
                self.access_token = None
                self.get_admin_token()
                return self._make_api_request(method, endpoint, params, json_data)

            response.raise_for_status()

            # Some endpoints return no content
            if response.status_code == 204:
                return {"status_code": 204}

            # Return JSON for content responses
            return response.json() if response.content else {}

        except requests.exceptions.HTTPError as exc:
            logger.error(f"Keycloak API HTTP error: {exc}")
            raise

        except requests.exceptions.RequestException as exc:
            logger.error(f"Keycloak API request failed: {exc}")
            raise

    # GROUP MANAGEMENT METHODS
    def get_groups(self, params: Dict = None) -> List[Dict]:
        """Get all groups in the realm"""
        endpoint = f"/admin/realms/{self.realm}/groups"
        return self._make_api_request("get", endpoint, params)

    def find_group_by_name(self, group_name: str) -> Optional[Dict]:
        """Find a group by name"""
        params = {"search": group_name, "exact": "true"}
        groups = self.get_groups(params)
        return groups[0] if groups else None

    def create_group(self, group_name: str, attributes: Optional[Dict] = None) -> Dict:
        """Create a new group"""
        endpoint = f"/admin/realms/{self.realm}/groups"

        group_data = {
            "name": group_name,
            "attributes": attributes or {"source": ["odl_video_service"]},
        }

        self._make_api_request("post", endpoint, json_data=group_data)

        return self.find_group_by_name(group_name)

    def get_group_members(self, group_id: str) -> List[Dict]:
        """Get all members of a specific group"""
        endpoint = f"/admin/realms/{self.realm}/groups/{group_id}/members"
        return self._make_api_request("get", endpoint)

    def get_group_details(self, group_id: str) -> Dict:
        """
        Get detailed information about a group including its attributes

        Args:
            group_id (str): The ID of the group

        Returns:
            Dict: Group details including attributes
        """
        endpoint = f"/admin/realms/{self.realm}/groups/{group_id}"
        return self._make_api_request("get", endpoint)

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to a group"""
        endpoint = f"/admin/realms/{self.realm}/users/{user_id}/groups/{group_id}"
        response = self._make_api_request("put", endpoint)
        return response.get("status_code") == 204

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

    def get_user_groups_by_user_id(self, user_id: str) -> List[Dict]:
        """
        Get all groups a user belongs to by user ID

        Args:
            user_id (str): The ID of the user

        Returns:
            List[Dict]: A list of group objects the user belongs to
        """
        endpoint = f"/admin/realms/{self.realm}/users/{user_id}/groups"
        return self._make_api_request("get", endpoint)

    def get_user_groups(self, email: str) -> List[str]:
        """
        Get a list of all groups a user is a member of

        Args:
            email (str): The email to query groups for

        Returns:
            List[str]: A list of names of groups which contain the user as a member
        """
        try:
            # Find the user first
            user = self.find_user_by_email(email)
            if not user:
                logger.warning(f"User {email} not found in Keycloak")
                return []

            groups = self.get_user_groups_by_user_id(user["id"])
            user_groups = [group["name"] for group in groups]
            return user_groups
        except Exception as exc:
            logger.error(f"Error querying Keycloak groups for {email}: {exc}")
            raise KeycloakException(
                f"Something went wrong with getting groups for user {email}"
            ) from exc

    def get_group_members_by_name(self, group_name: str) -> List[Dict]:
        """
        Get all members of a specific group by group name

        Args:
            group_name (str): Name of the group

        Returns:
            List[Dict]: List of user dictionaries in the group
        """
        try:
            group = self.find_group_by_name(group_name)
            if not group:
                logger.warning(f"Group {group_name} not found in Keycloak")
                return []

            return self.get_group_members(group["id"])
        except Exception as exc:
            logger.error(f"Error getting members for group {group_name}: {exc}")
            raise KeycloakException(
                f"Something went wrong with getting members for group {group_name}"
            ) from exc

    def get_group_attributes_by_name(self, group_name: str) -> Dict:
        """
        Get attributes of a specific group by group name

        Args:
            group_name (str): Name of the group

        Returns:
            Dict: Dictionary of group attributes or empty dict if group not found
        """
        try:
            group = self.find_group_by_name(group_name)
            if not group:
                logger.warning(f"Group {group_name} not found in Keycloak")
                return {}

            group_details = self.get_group_details(group["id"])
            return group_details.get("attributes", {})
        except Exception as exc:
            logger.error(f"Error getting attributes for group {group_name}: {exc}")
            raise KeycloakException(
                f"Something went wrong with getting attributes for group {group_name}"
            ) from exc

    # USER MANAGEMENT METHODS
    def get_users(self, max_users: int = 999, search: str = None) -> List[Dict]:
        """Get all users in the realm"""
        endpoint = f"/admin/realms/{self.realm}/users"
        params = {"max": max_users}
        if search:
            params["search"] = search

        return self._make_api_request("get", endpoint, params=params)

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find a user by email"""
        endpoint = f"/admin/realms/{self.realm}/users"
        params = {"email": email, "exact": "true"}

        users = self._make_api_request("get", endpoint, params=params)
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
        endpoint = f"/admin/realms/{self.realm}/users"
        try:
            self._make_api_request("post", endpoint, json_data=user_data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:  # User already exists
                logger.warning(f"User '{user.username}' already exists")
                return self.find_user_by_email(user.email)
            raise KeycloakException(
                f"Failed to create user {user.username}: {e.response.text}"
            ) from e

        created_user = self.find_user_by_email(user.email)
        if not created_user:
            raise KeycloakException("Failed to retrieve created user")

        # Set password if provided
        if user.password:
            self.set_user_password(
                created_user["id"], user.password, user.temporary_password
            )

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
        endpoint = f"/admin/realms/{self.realm}/users/{user_id}/reset-password"
        password_data = {"type": "password", "value": password, "temporary": temporary}

        response = self._make_api_request("put", endpoint, json_data=password_data)
        return response.get("status_code") == 204


def get_keycloak_client() -> KeycloakManager:
    """
    Creates a new Keycloak client configured with settings from Django settings.
    This creates a fresh connection each time without caching the instance.

    Returns:
        KeycloakManager: A new Keycloak client instance
    """
    # Ensure we have the necessary settings
    required_settings = [
        "KEYCLOAK_SERVER_URL",
        "KEYCLOAK_REALM",
        "KEYCLOAK_SVC_ADMIN",
        "KEYCLOAK_SVC_ADMIN_PASSWORD",
    ]
    for setting in required_settings:
        if not getattr(settings, setting, None):
            logger.error(f"Missing required setting: {setting}")
            raise ValueError(f"{setting} setting is missing")

    try:
        return KeycloakManager(
            keycloak_url=settings.KEYCLOAK_SERVER_URL,
            realm=settings.KEYCLOAK_REALM,
            admin_username=settings.KEYCLOAK_SVC_ADMIN,
            admin_password=settings.KEYCLOAK_SVC_ADMIN_PASSWORD,
        )
    except Exception as exc:
        logger.error(f"Failed to create Keycloak client: {exc}")
        raise KeycloakException(
            "Something went wrong with creating a Keycloak client"
        ) from exc
