"""
PasswordPolicy class
"""
from os import path
import re
from typing import Self
import yaml

from .base import Base, BASE_SCHEMA_PATH

class PasswordPolicy(Base):
    """
    Configuration class
    """

    SCHEMA_PATH = path.join(BASE_SCHEMA_PATH, "password_policy.yaml")

    @staticmethod
    def get_password_regex_pattern() -> str:
        """
        Get password regex pattern from schema
        """
        with open(path.join(BASE_SCHEMA_PATH, 'password.yaml'),
                  encoding="utf-8") as _file:
            regex_pattern = yaml.load(_file, Loader=yaml.FullLoader)['pattern']
        return regex_pattern

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(self, expiration_delay_in_days: int = -1, password_min_length: int = 10):
        """
        Initialize the password policy
        Args:
            expiration_delay_in_days: Number of days before a password must be changed
            password_min_length: Minimal length for the password
        """
        regex_pattern = self.get_password_regex_pattern()
        super().__init__(regex_pattern=regex_pattern,
                         expiration_delay_in_days=expiration_delay_in_days,
                         password_min_length=password_min_length)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Class Method From Dict
        Args: 
            cls: the class
            data: the dict to convert
        Returns:
            Self: Reference to the instance object
        """
        self = cls()
        # Remove 'regex_pattern' from the data to ensure
        # that we load always the good pattern from the yaml file
        data.pop("regex_pattern", None)
        self._load(data)  # pylint: disable=protected-access
        return self

    def validate_password_constraints(self, password: str) -> bool:
        """
        Validate password constraints
        Args:
            password (str): the password to validate
        Returns:
            bool: True if the given password is validated else False
        """
        parser = re.compile(self.regex_pattern)
        return bool(parser.match(password)) and len(password) >= self.password_min_length

    @property
    def regex_pattern(self) -> str:
        """
        Return regex_pattern in str
        :return
        """
        return self._data["regex_pattern"]

    @regex_pattern.setter
    def regex_pattern(self, regex_pattern: str):
        """
        regex_pattern setter
        Args:
            regex_pattern (str): the value to set
        """
        self._data["regex_pattern"] = regex_pattern

    @property
    def expiration_delay_in_days(self) -> int:
        """
        Return expiration_delay_in_days in int
        :return
        """
        return self._data["expiration_delay_in_days"]

    @expiration_delay_in_days.setter
    def expiration_delay_in_days(self, expiration_delay_in_days: int):
        """
        expiration_delay_in_days setter
        """
        self._data["expiration_delay_in_days"] = expiration_delay_in_days

    @property
    def password_min_length(self) -> int:
        """
        Return password_min_length in int
        :return
        """
        return self._data["password_min_length"]

    @password_min_length.setter
    def password_min_length(self, password_min_length: int):
        """
        password_min_length setter
        """
        self._data["password_min_length"] = password_min_length
