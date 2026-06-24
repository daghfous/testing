"""
session
"""
from typing import Self
from dataclasses import dataclass, asdict
from .token import Token


@dataclass(kw_only=True)
class Session:
    """ Session dataclass
    """
    username: str
    idp_name: str
    user_id: str
    user_ip: str | None = None
    started_date: str | None = None
    expiration_date: str | None = None
    token_id: str

    @classmethod
    def generate(
        cls,
        user: dict,
        token: Token,
        **kwargs
    ) -> Self:
        """ Generate a session instance according to these parameters

        Args:
            user (dict): user object
            token (Token): token

        Returns:
            Session: a session instance
        """
        started_date = token.started_date
        if started_date:
            started_date = started_date.strftime("%Y-%m-%d %H:%M:%S")
        expiration_date = token.expiration_date
        if expiration_date:
            expiration_date = expiration_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            expiration_date = 'unlimited'
        # user_id is needed for user edition from the sessions table and token _id for session deletion
        return cls(
            username=user['username'],
            idp_name=user['idp_name'],
            user_id=token.user_id,
            user_ip=token.user_ip,
            started_date=started_date,
            expiration_date=expiration_date,
            token_id=str(token._id),  # pylint: disable=protected-access
            ** kwargs
        )

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """ Create a session instance based on the dataclass fields to skip extra keys.

        Args:
            data (dict): dict to convert into session dataclass

        Returns:
            Session: a session instance
        """
        # Filter only the keys that match the dataclass fields
        filtered_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}  # pylint: disable=no-member
        return cls(**filtered_data)

    def as_dict(self) -> dict:
        """ Convert the session instance into a dict.

        Returns:
            dict: the session as dict
        """
        return asdict(self)
