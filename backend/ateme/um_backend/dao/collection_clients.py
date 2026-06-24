"""
collection clients
"""
from typing import Any
from dataclasses import dataclass
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo import ASCENDING, IndexModel, ReturnDocument
from pymongo.results import DeleteResult

from ateme.um_backend.utils import utcnow
from ateme.um_backend.types import Client
from ateme.um_backend.dao.collections import Collections, CollectionBase


DEPRECATED_INDEXES: list[IndexModel] = [
    # To deal with upgrade from v4.0 to v5.0
    IndexModel(keys=[("remote", ASCENDING), ("username", ASCENDING)])
]

INDEXES: list[IndexModel] = [
    IndexModel(
        keys=[("remote", ASCENDING), ("username", ASCENDING), ('idp_name', ASCENDING)],
        unique=True
    )
]


class DeleteClientError(Exception):
    """ DeleteClientError
    """


@dataclass(kw_only=True)
class CollectionClients(CollectionBase):
    """ CollectionClients inherits from CollectionBase.
    It manages the collection `clients`.
    """
    name: str = Collections.clients.name

    def __post_init__(self):
        # init indexes
        self.deprecated_indexes = DEPRECATED_INDEXES
        self.indexes = INDEXES

    async def get(
        self,
        remote: str,
        username: str,
        idp_name: str
    ) -> Client | None:
        """
        Return a client (IP + username + idp_name),
        A client is in the db if the requested IP + username + idp_name + password has already failed
        The client is removed from db when he's enabled after user_deactivation_period seconds.

        Args:
            remote (string): remote ip address
            username (string): username of username
            idp_name (string): idp name

        Returns:
            Client | None
        """
        # Retrieve the client, None if not known or enabled
        client = await self.collection.find_one(
            {
                "username": username,
                "remote": remote,
                "idp_name": idp_name
            }
        )
        return Client.from_dict(client) if client else None

    async def update(
        self,
        remote: str,
        username: str,
        idp_name: str,
        max_successive_failed_login: int,
        user_deactivation_period: int
    ) -> Client:
        """
        Create or update a client by managing the attempts and the enabled flag.
        NOTE: `find_one_and_update` with `upsert=True` is used.

        Args:
            remote (str): remote ip address
            username (str): username
            idp_name (str): idp name
            max_successive_failed_login (int): number of authorized successive failed login
            user_deactivation_period (int): user deactivation period (in seconds), -1 when disabled

        Returns:
            Client
        """
        _filter = {
            "remote": remote,
            "username": username,
            "idp_name": idp_name
        }
        _update_pipeline = [
            # At document creation, initialize the `attempts` field to `0`
            {
                "$set": {
                    "attempts": {"$cond": {"if": {"$not": ["$attempts"]}, "then": 0, "else": "$attempts"}},
                }
            },
            # Increment `attempts` and set `last_attempt_date` as UTC timestamp
            {
                "$set": {
                    "attempts": {"$add": ["$attempts", 1]},
                    "last_attempt_date": utcnow().timestamp(),
                }
            }
        ]
        if user_deactivation_period != -1:
            # Manage `enabled` flag according to attempts and max_successive_failed_login
            # - attempts < max_successive_failed_login => enabled=True
            # - attempts >= max_successive_failed_login => enabled=False
            _update_pipeline.append(
                {
                    "$set": {
                        "enabled": {
                            "$cond": [
                                {"$gte": ["$attempts", max_successive_failed_login]},
                                False,
                                True
                            ]
                        }
                    }
                }
            )
        else:
            _update_pipeline.append(
                {
                    "$set": {
                        "enabled": True
                    }
                }
            )
        result = await self.collection.find_one_and_update(
            filter=_filter,
            update=_update_pipeline,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        # As `upsert=True`, we always return a client
        return Client.from_dict(result)


    # pylint: disable=too-many-positional-arguments
    async def delete_many(
        self,
        idp_name: str | None = None,
        remote: str | None = None,
        username: str | None = None,
        user_deactivation_period: int | None = None,
        session: AsyncClientSession | None = None
    ) -> DeleteResult | None:
        """
        Delete many clients from database

        Args:
            remote (str | None): remote ip address
            username (str | None): remove every client corresponding to username if not None
            In this case, the idp_name should be set
            idp_name (str | None): remove every client corresponding to idp_name
            user_deactivation_period (int | None): period of user deactivation
            session (AsyncClientSession | None): database transaction session

        Raises:
            DeleteClientError:
                - when arguments are not coherent

        Returns:
            DeleteResult or None
        """
        _filter: dict[str, Any] = {}
        if username and not idp_name:
            # Can't delete client based only on the username: idp_name should be set
            raise DeleteClientError("idp_name must be set if username is set")
        if username:
            _filter.update({"username": username, "idp_name": idp_name})
        if remote:
            _filter.update({"remote": remote})
        if user_deactivation_period:
            _filter.update({"last_attempt_date": {'$lte': utcnow().timestamp() - user_deactivation_period}})
        if _filter:
            return await self.collection.delete_many(_filter, session=session)
        return None

    async def get_login_attempts_number(self) -> int:
        """
        Return the sum of every attempts in clients collection

        Returns:
            int: login attempts sum number
        """
        result = await (await self.collection.aggregate(
            # mongo groups input documents by specified _id expression and
            # for each distinct grouping, outputs a document
            [{"$group": {"_id": None, "count": {"$sum": "$attempts"}}}]
        )).to_list(None)
        login_attempts_number = 0
        if result:
            login_attempts_number = result[0]['count']
        return login_attempts_number
