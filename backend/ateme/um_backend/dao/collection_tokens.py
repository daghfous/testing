"""
collection tokens
"""
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo import ASCENDING, IndexModel
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from bson import ObjectId

from ateme.um_backend.types import Token, DEFAULT_VERSION
from ateme.um_backend.utils import utcnow
from .collections import Collections, CollectionBase


DEPRECATED_INDEXES: list[IndexModel] = [
]

INDEXES: list[IndexModel] = [
    IndexModel(
        keys=[('token', ASCENDING)],
        unique=True
    ),
    IndexModel(
        keys=[('user_id', ASCENDING)]
    )
]


@dataclass(kw_only=True)
class CollectionTokens(CollectionBase):
    """ CollectionTokens inherits from CollectionBase.
    It manages the collection `tokens`.
    """
    name: str = Collections.tokens.name

    def __post_init__(self):
        # init indexes
        self.deprecated_indexes = DEPRECATED_INDEXES
        self.indexes = INDEXES

    async def initialize(self):
        """
        Initialize the collection + backfill version field in existing documents
        Args:
            None
        Returns:
            None
        """
        await super().initialize()
        # backfill version field before creating unique index on (token, version)
        await self.backfill_version()

    async def store(self, token: Token, session: AsyncClientSession | None = None) -> InsertOneResult:
        """
        Store token

        Args:
            token (Token): token dataclass
            session (AsyncClientSession, optional): Database transaction session. Defaults to None.

        Returns:
            InsertOneResult: insert result
        """
        return await self.collection.insert_one(token.as_dict(), session=session)

    async def get_by_access_token(self, access_token: str) -> Token | None:
        """ Returns the token data according the provided access token.

        Args:
            access_token (str): token

        Returns:
            Token | None: token dataclass or None
        """
        result = await self.collection.find_one({"token": access_token})
        return Token.from_dict(result) if result else None

    async def get_by_refresh_token(self, refresh_token: str) -> Token | None:
        """ Returns the token data according the provided refresh token.
        NOTES:
        - the refresh_token MUST NOT be expired
        - `refresh_token` is not an unique field

        Args:
            refresh_token (str): refresh_token

        Returns:
            Token | None: token dataclass or None
        """
        result = await self.collection.find_one(
            {"refresh_token": refresh_token, "refresh_token_expiration_date": {"$gte": utcnow()}}
        )
        return Token.from_dict(result) if result else None

    async def get_list_by_user_id(self, user_id: str) -> List[Token]:
        """ Returns a list of token(s) relative to the user_id.

        Args:
            user_id (str): user id

        Returns:
            List[Token]: List of token data for this user_id
        """
        tokens = await self.collection.find({"user_id": user_id}).to_list(None)
        return [Token.from_dict(token) for token in tokens]

    async def refresh_token(self,
                            token: str,
                            new_token: str,
                            new_expiration_date: datetime,
                            current_version: int) -> UpdateResult:
        """ Refresh the token with a new access token and a new expiration date.
        TODO: should be rework because `refresh_token` is not an unique field.
        May be use the expired token.
        Uses version-based optimistic locking to avoid race conditions.

        Args:
            token (str): token to update
            new_token (str): new access token
            new_expiration_date (datetime): new access token expiration date
            current_version (int): current version of the token document
        Returns:
            UpdateResult: update result
        """
        return await self.collection.update_one(
            {"token": token, "version": current_version},
            {"$set": {
                "token": new_token,
                "expiration_date": new_expiration_date
            },
            "$inc": {
                "version": 1 # increment version atomically
            }},
            upsert=False
        )

    async def update_user_id(
        self,
        token: str,
        new_user_id: str,
        session: AsyncClientSession | None = None
    ) -> UpdateResult:
        """ Update the token data according the provided access token.

        Args:
            token (str): access token to update
            new_user_id (str): new user_id
            session (AsyncClientSession | None): transaction session, default None

        Returns:
            UpdateResult: update result
        """
        return await self.collection.update_one(
            {"token": token},
            {"$set": {"user_id": new_user_id}},
            upsert=False,
            session=session
        )

    async def remove_by_access_token(
        self,
        access_token: str,
        session: AsyncClientSession | None = None
    ) -> DeleteResult:
        """ Remove a token according to the access_token.

        Args:
            access_token (str): token to remove.
            session (AsyncClientSession | None): transaction session, default None

        Returns:
            DeleteResult: delete result
        """
        return await self.collection.delete_one({"token": access_token}, session=session)

    async def remove_by_user_id(self, user_id: str) -> DeleteResult:
        """ Remove several tokens according to the user_id.

        Args:
            user_id (str): user_id whose the tokens must be removed.

        Returns:
            DeleteResult: delete result
        """
        return await self.collection.delete_many({"user_id": user_id})

    async def remove_by_object_id(self, object_id: str) -> Optional[Token]:
        """ Remove token according to the object id.

        Args:
            object_id (str): db object id

        Returns:
            Optional[Token]: deleted token or None
        """
        result = await self.collection.find_one_and_delete({"_id": ObjectId(object_id)})
        return Token.from_dict(result) if result else None

    async def clean_expired_refresh_token(self):
        """
        Method to remove expired refresh token fron db
        """
        await self.collection.delete_many({"refresh_token_expiration_date": {"$lte": utcnow()}})

    async def get_list(self) -> List[Token]:
        """
        Returns all tokens

        Returns:
            List[Token]: List of tokens
        """
        _tokens = await self.collection.find().to_list(None)
        return [Token.from_dict(token) for token in _tokens]


    async def backfill_version(self, default_version: int = DEFAULT_VERSION) -> UpdateResult:
        """
        Add the `version` field to all documents that don't have it yet.
        This field is required for the refresh token management.

        Args:
            default_version (int, optional): default version to set. Defaults to 0.
        Returns:
            UpdateResult: update result
        """
        return await self.collection.update_many(
            {"version": {"$exists": False}}, # only documents missing the version
            {"$set": {"version": default_version}}
        )
