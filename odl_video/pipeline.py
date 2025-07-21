"""
Social Auth Pipeline for Keycloak OIDC integration.
Handles permission mapping based on Keycloak groups.
"""

import logging
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def assign_user_groups(strategy, details, backend, user=None, *args, **kwargs):
    """
    Custom pipeline function to assign Django permissions based on Keycloak groups.
    This runs after user creation/lookup to ensure permissions are properly assigned.

    Keycloak group mapping:
    - "Admin" group → Django superuser (is_superuser=True, is_staff=True)
    - "Staff" group → Django staff (is_staff=True)
    - Any other group or no group → regular user (no special flags)
    """
    if not user:
        logger.debug("assign_user_groups called but no user provided")
        return

    groups = []
    social_user = kwargs.get("social", None)

    if social_user and hasattr(social_user, "extra_data"):
        extra_data = social_user.extra_data

        if "user_groups" in extra_data:
            extra_groups = extra_data["user_groups"]
            groups.extend(extra_groups)

    logger.info(f"Groups found for user {user.username}: {groups}")

    # Store current state to check if changes are needed
    old_is_superuser = user.is_superuser
    old_is_staff = user.is_staff

    groups_lower = [group.lower() for group in groups]

    if "/admin" in groups_lower:
        user.is_superuser = True
        user.is_staff = True
        logger.info(f"Assigned superuser and staff privileges to user {user.username}")
    elif "/staff" in groups_lower:
        user.is_superuser = False
        user.is_staff = True
        logger.info(f"Assigned staff privileges to user {user.username}")
    else:
        user.is_superuser = False
        user.is_staff = False
        logger.info(f"Set regular user privileges for user {user.username}")

    # Only save if permissions changed
    if old_is_superuser != user.is_superuser or old_is_staff != user.is_staff:
        try:
            user.save()
            logger.info(
                f"Successfully updated permissions for user {user.username} - superuser: {user.is_superuser}, staff: {user.is_staff}"
            )
        except Exception as e:
            logger.error(f"Failed to save user {user.username}: {str(e)}")
    else:
        logger.info(f"No permission changes needed for user {user.username}")

    return {"user": user}
