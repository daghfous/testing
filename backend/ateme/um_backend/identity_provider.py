"""
IdentityProvider module
"""
from abc import ABC

from . import Database
from .loggers import LOG
from .types.idp_local_config import IdpLocalConfig


class IdentityProvider(ABC):  # pylint: disable=too-few-public-methods
    """
    IdentityProvider class
    """

    def __init__(self, db: Database):
        """
        Constructor
        Args:
             db (Database): Database
        """
        self.db = db


class LocalProvider(IdentityProvider): # pylint: disable=too-few-public-methods
    """
    LocalProvider class
    """

    async def initialize(self):
        """
        Initializes the object.
        This method is used to initialize the object.
        It creates a default idp config for local user and stores it in the database.
        """
        # create a default idp config for local user
        local_idp_config = IdpLocalConfig()
        try:
            await self.db.store_idp_config(local_idp_config.to_dict())
        except Exception:
            LOG.error("'Local' Idp Config already in db")
