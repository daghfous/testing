"""
Client class

"""
import os

from .base import Base, BASE_SCHEMA_PATH


class Client(Base):
    """
    class Client
    """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "client.yaml")

    @property
    def remote(self) -> str:
        """

        remote getter
        Return:
            str: remote
        """
        return self._data["remote"]

    @remote.setter
    def remote(self, remote: str):
        """

        remote setter
        Args:
            remote (str): remote ip
        """
        self._data["remote"] = remote

    @property
    def username(self) -> str:
        """

        username getter
        Return:
            str: client identifiant
        """
        return self._data["username"]

    @username.setter
    def username(self, username: str):
        """

        client id setter
        Args:
            str: client id
        """
        self._data["username"] = username

    @property
    def idp_name(self) -> str:
        """

        idp_name getter
        Return:
            str: idp_name
        """
        return self._data["idp_name"]

    @idp_name.setter
    def idp_name(self, idp_name: str):
        """

        idp_name setter
        Args:
            str: idp_name
        """
        self._data["idp_name"] = idp_name

    @property
    def attempts(self) -> int:
        """

        attempts getter
        Return:
            str: client identifiant
        """
        return self._data["attempts"]

    @attempts.setter
    def attempts(self, attempts: int):
        """

        client id setter
        Args:
            str: client id
        """
        self._data["attempts"] = attempts

    @property
    def enabled(self) -> bool:
        """

        enabled getter
        Return:
            str: client identifiant
        """
        return self._data["enabled"]

    @enabled.setter
    def enabled(self, enabled: bool):
        """

        client id setter
        Args:
            str: client id
        """
        self._data["enabled"] = enabled

    @property
    def last_attempt_date(self) -> float:
        """

        last_attempt_date getter
        Return:
            str: client identifiant
        """
        return self._data["last_attempt_date"]

    @last_attempt_date.setter
    def last_attempt_date(self, last_attempt_date: float):
        """

        client id setter
        Args:
            str: client id
        """
        self._data["last_attempt_date"] = last_attempt_date
