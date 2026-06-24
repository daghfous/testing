"""
Configuration class
"""
from os import path
from datetime import timedelta
from typing import Self, Optional

from .password_policy import PasswordPolicy

from .base import Base, BASE_SCHEMA_PATH

class Configuration(Base):
    """
    Configuration class
    """

    SCHEMA_PATH = path.join(BASE_SCHEMA_PATH, "configuration.yaml")

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
            self, max_successive_failed_login: int = 3,
            user_deactivation_period: int = 600, token_expiration: int = 3600, refresh_token_expiration: int = 7200,
            token_cleaning_period: int = 24, logout_timeout: int = -1,
            password_policy: Optional[PasswordPolicy] = PasswordPolicy()):
        """
        Initialize the configuration
        Args:
            max_successive_failed_login: Max successive failed logins before disabling a user
            user_deactivation_period: Period (in minutes) during the user is disabled after
                                      max_successive_failed_login ('-1' for an admin re-enables the user)
            token_expiration: Expiration period (in seconds) for the token auth
            refresh_token_expiration: Expiration period (in seconds) for the refresh token auth
            token_cleaning_period: Period (in hours) at the end of which token auth is removed from db
            logout_timeout: Period (in seconds) for the timeout duration
            password_policy: Password Policy
        """
        super().__init__(max_successive_failed_login=max_successive_failed_login,
                         user_deactivation_period=user_deactivation_period,
                         token_expiration=token_expiration,
                         refresh_token_expiration=refresh_token_expiration,
                         token_cleaning_period=token_cleaning_period,
                         logout_timeout=logout_timeout,
                         password_policy=password_policy)

    @classmethod
    def from_dict(cls, data: dict):
        """

        from_dict class method
        :param data:
        :return:
        """
        self = cls()

        self._load(data)  # pylint: disable=protected-access

        if not isinstance(self.password_policy, PasswordPolicy):
            self.password_policy = PasswordPolicy.from_dict(self.password_policy)
        return self

    @property
    def user_deactivation_period(self) -> int:
        """
        Return user_deactivation_period in int
        :return
        """
        return self._data["user_deactivation_period"]

    @user_deactivation_period.setter
    def user_deactivation_period(self, user_deactivation_period):
        """
        user_deactivation_period setter
        """
        self._data["user_deactivation_period"] = user_deactivation_period

    @property
    def max_successive_failed_login(self) -> int:
        """
        Return max_successive_failed_login in int
        :return
        """
        return self._data["max_successive_failed_login"]

    @max_successive_failed_login.setter
    def max_successive_failed_login(self, max_successive_failed_login):
        """
        max_successive_failed_login setter
        """
        self._data["max_successive_failed_login"] = max_successive_failed_login

    @property
    def token_expiration(self) -> timedelta:
        """
        Return token_expiration in timedelta
        """
        return timedelta(seconds=self._data["token_expiration"])

    @token_expiration.setter
    def token_expiration(self, token_expiration: int):
        """
        token_expiration setter
        """
        self._data["token_expiration"] = token_expiration

    @property
    def refresh_token_expiration(self) -> timedelta:
        """
        Return refresh_token_expiration in timedelta
        """
        return timedelta(seconds=self._data["refresh_token_expiration"])

    @refresh_token_expiration.setter
    def refresh_token_expiration(self, refresh_token_expiration: int):
        """
        refresh_token_expiration setter
        """
        self._data["refresh_token_expiration"] = refresh_token_expiration

    @property
    def token_cleaning_period(self) -> timedelta:
        """
        Return token_cleaning_period in timedelta
        """
        return timedelta(hours=self._data["token_cleaning_period"])

    @token_cleaning_period.setter
    def token_cleaning_period(self, token_cleaning_period: int):
        """
        token_cleaning_period setter
        """
        self._data["token_cleaning_period"] = token_cleaning_period

    @property
    def logout_timeout(self) -> int:
        """
        Return logout_timeout (int)
        """
        return self._data["logout_timeout"]

    @logout_timeout.setter
    def logout_timeout(self, logout_timeout: int):
        """
        logout_timeout setter
        """
        self._data["logout_timeout"] = logout_timeout

    @property
    def password_policy(self) -> PasswordPolicy:
        """
        Return password_policy
        :return
        """
        return self._data["password_policy"]

    @password_policy.setter
    def password_policy(self, password_policy: PasswordPolicy):
        """
        password_policy setter
        """
        self._data["password_policy"] = password_policy


class PublicConfiguration(Base):
    """
    PublicConfiguration class
    """
    SCHEMA_PATH = path.join(BASE_SCHEMA_PATH, "public_configuration.yaml")

    @classmethod
    def create(cls, configuration: Configuration) -> Self:
        """
        Create public configuration from Configuration object
        """
        return cls(configuration)

    def __init__(self, configuration: Configuration):
        """
        Initialize the public configuration
        Args:
            configuration: Configuration source object
        """
        super().__init__(logout_timeout=configuration.logout_timeout,
                         password_policy=configuration.password_policy)

    @classmethod
    def from_dict(cls, data: dict):
        """

        from_dict class method
        :param data:
        :return:
        """
        self = super().from_dict(data)
        # pylint: disable=protected-access,no-member
        if self.password_policy is not None:
            self._data['password_policy'] = PasswordPolicy.from_dict(self.password_policy)
        else:
            self._data['password_policy'] = PasswordPolicy()
        return self

    @property
    def logout_timeout(self) -> int:
        """
        Return logout_timeout (int)
        """
        return self._data["logout_timeout"]

    @logout_timeout.setter
    def logout_timeout(self, logout_timeout: int):
        """
        logout_timeout setter
        """
        self._data["logout_timeout"] = logout_timeout

    @property
    def password_policy(self) -> PasswordPolicy:
        """
        Return password_policy
        :return
        """
        return self._data["password_policy"]

    @password_policy.setter
    def password_policy(self, password_policy: PasswordPolicy):
        """
        password_policy setter
        """
        self._data["password_policy"] = password_policy
