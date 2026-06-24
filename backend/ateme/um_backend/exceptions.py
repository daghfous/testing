"""
File containing custom Exceptions
"""

class LocalUserInvalidCredentials(Exception):
    """
    Custom exception for local user invalid credentials
    """

class InvalidUserException(Exception):
    """
    Custom exception for invalid user
    """

class LdapUnavailableCache(Exception):
    """
    Custom exception for cache not available
    """

class LdapNoCacheEntry(Exception):
    """
    Custom exception for no cache entry
    """

class IdpConfigNotFound(Exception):
    """
    Custom Exception for a specific case
    """

class CheckTokenError(Exception):
    """
    Custom exception for check token
    """

class CheckRemoteIPInvalid(Exception):
    """
    Custom exception when remote IP is invalid
    """
    def __init__(self, username: str, idp_name: str, remote: str, user_ip: str):
        """ init

        Args:
            username (str): username
            idp_name (str): idp name of the user
            remote (str): request remote IP address
            user_ip (str): token user IP address
        """
        super().__init__(f"remote ip invalid: {remote} != {user_ip}")
        self._activity_message: str = f"wrong remote IP address {remote} (expected {user_ip})"
        self._activity_extra: dict = {"user": f"{username}:{idp_name}"}

    @property
    def activity_message(self) -> str:
        """ Property to return the activity message.

        Returns:
            str: activity message
        """
        return self._activity_message

    @property
    def activity_extra(self) -> dict:
        """ Property to return the activity extra.

        Returns:
            str: activity log
        """
        return self._activity_extra

class RequestExtractError(Exception):
    """
    Custom exception for request extraction
    """

class IntrospectionError(Exception):
    """
    Custom Exception for token introspection
    """
