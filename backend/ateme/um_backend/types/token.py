"""
token
"""
import os
import binascii
from typing import Self
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from bson import ObjectId

from ateme.um_backend.utils import utcnow

# Default version number of a token
DEFAULT_VERSION: int = 0

def _generate_token(nbytes: int = 32) -> str:
    """ Generate a token as hexadecimal string

    Args:
        nbytes (int): number of bytes, default to 32.

    Returns:
        str: token
    """
    return binascii.b2a_hex(os.urandom(nbytes)).decode('ascii')


@dataclass(kw_only=True)
class Token:
    """ Token dataclass
    """
    # pylint: disable=too-many-instance-attributes
    token: str
    version: int = DEFAULT_VERSION
    started_date: datetime | None = None
    expiration_date: datetime | None
    refresh_token: str
    refresh_token_expiration_date: datetime | None
    user_id: str
    user_ip: str | None = None
    _id: ObjectId | None = None
    # saml metadata
    session_index: str | None = None
    nameidentifier: str | None = None
    idp_name: str | None = None

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    @classmethod
    def generate(
        cls,
        user_id: str,
        token_expiration: timedelta,
        refresh_token_expiration: timedelta,
        session_timeout_disabled: bool,
        user_ip: str,
        **kwargs
    ) -> Self:
        """ Generate a token instance according to these parameters

        Args:
            user_id (str): user_id
            token_expiration (timedelta): token_expiration
            refresh_token_expiration (timedelta): refresh_token_expiration
            session_timeout_disabled (bool): session_timeout_disabled
            user_ip (str): user_ip

        Returns:
            Token: a token instance
        """
        started_date = utcnow()
        expiration_date = started_date + token_expiration
        refresh_token_expiration_date = started_date + refresh_token_expiration
        if session_timeout_disabled:
            expiration_date = None
            refresh_token_expiration_date = None
        return cls(
            token=_generate_token(),
            started_date=started_date,
            version=DEFAULT_VERSION,
            expiration_date=expiration_date,
            refresh_token=_generate_token(),
            refresh_token_expiration_date=refresh_token_expiration_date,
            user_id=user_id,
            user_ip=user_ip,
            **kwargs
        )

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """ Create a token instance based on the dataclass fields to skip extra keys.

        Args:
            data (dict): dict to convert into token dataclass

        Returns:
            Token: a token instance
        """
        # Filter only the keys that match the dataclass fields
        filtered_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}  # pylint: disable=no-member
        return cls(**filtered_data)

    def as_dict(self) -> dict:
        """ Convert the token instance into a dict.
        Some optional fields are removed.

        Returns:
            dict: the token as dict
        """
        optional_keys = ["user_ip", "session_index", "nameidentifier", "idp_name", "_id"]

        def _dict_factory(data: list):
            return {key: value for key, value in data if key not in optional_keys or value is not None}
        return asdict(self, dict_factory=_dict_factory)

    def refresh_access_token(self, token_expiration: timedelta):
        """ Refresh the access token

        Args:
            token_expiration (timedelta): token_expiration
        """
        self.started_date = utcnow()
        self.expiration_date = self.started_date + token_expiration
        self.token = _generate_token()
