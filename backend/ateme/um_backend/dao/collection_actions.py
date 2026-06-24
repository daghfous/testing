"""
collection actions
"""
from dataclasses import dataclass
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo import ASCENDING, IndexModel
from pymongo.results import InsertOneResult, DeleteResult, InsertManyResult
from pymongo.errors import BulkWriteError

from ateme.um_backend.loggers import LOG
from ateme.um_backend.types import Action
from ateme.um_backend.dao.collections import Collections, CollectionBase


DEPRECATED_INDEXES: list[IndexModel] = [
]

INDEXES: list[IndexModel] = [
    IndexModel(
        keys=[('name', ASCENDING), ('prefix', ASCENDING)],
        unique=True
    )
]


@dataclass(kw_only=True)
class CollectionActions(CollectionBase):
    """ CollectionActions inherits from CollectionBase.
    It manages the collection `actions`.
    """
    name: str = Collections.actions.name

    def __post_init__(self):
        # init indexes
        self.deprecated_indexes = DEPRECATED_INDEXES
        self.indexes = INDEXES

    async def store(self, action: Action) -> InsertOneResult:
        """

        store action to database
        :param action:
        """
        return await self.db[Collections.actions.name].insert_one(action.to_dict())

    async def replace_many(
        self,
        actions: list[Action],
        prefix: str,
        app_name: str | None = None,
        session: AsyncClientSession | None = None
    ):
        """ Replace actions (delete the old ones by filtering by prefix and app_name, then insert the new ones).

        Args:
            actions (List[Action]): Actions to push into db
            prefix (str): app prefix
            app_name (str, optional): app name. Defaults to None.
            session (AsyncClientSession, optional): client session. Defaults to None.
        """
        _filter = {"prefix": prefix}
        if app_name:
            _filter["prefix"] = f"{app_name}:{prefix}"
        delete_res = await self.collection.delete_many(_filter, session=session)
        LOG.debug("Delete actions result: %s with filter %s", delete_res.deleted_count, _filter)
        insert_res = await self.collection.insert_many(
            [action.to_dict() for action in actions],
            session=session
        )
        LOG.debug("Inserted actions result: %s", len(insert_res.inserted_ids))

    async def replace_defaults(
        self,
        actions: list[Action],
        session: AsyncClientSession | None = None
    ) -> tuple[bool, InsertManyResult | None]:
        """ Replace default actions (delete the old ones by filtering on the prefix, then insert the new ones).
        NOTE: `usr` and `all` prefixes must be excluded from deletion.

        Args:
            actions (List[Action]): Actions to push into db
            session (AsyncClientSession, optional): client session. Defaults to None.

        Returns:
            bool: True if update is successful, False otherwise
            InsertManyResult | None: Result of the insert_many operation, or None if it failed
        """
        # remove default actions with same prefixes
        update_result = None
        try:
            prefixes = []
            for action in actions:
                action.validate()
                if action.prefix not in prefixes:
                    prefixes.append(action.prefix)
            for prefix in prefixes:
                if prefix in ['usr', 'all']:
                    continue
                await self.collection.delete_many({"prefix": prefix}, session=session)
        except Exception as e:
            LOG.exception("Update default actions failed: %s", e)
            return False, update_result
        try:
            update_result = await self.collection.insert_many(
                [action.to_dict() for action in actions], session=session
            )
        except BulkWriteError as errors:
            for error in errors.details['writeErrors']:
                LOG.error("Action %s was not inserted because of %s", error['keyValue'], error['errmsg'])
            return False, update_result
        return True, update_result

    async def get_list(self, filters: dict | None = None) -> list[Action]:
        """ Get actions from the collection

        Args:
            filters (dict, optional): filters to apply. Defaults to None.

        Returns:
            list[Action]: List of actions matching the filters
        """
        return [
            Action.from_dict(item)
            for item in await self.collection.find(
                filters,
                {"_id": 0, "internal": 0}
            ).to_list(None)
        ]

    async def delete_many(
        self,
        filters: dict | None = None,
        session: AsyncClientSession | None = None
    ) -> DeleteResult:
        """ Delete actions matching the filters

        Args:
            filters (dict, optional): filters to apply. Defaults to None.
            session (AsyncClientSession, optional): client session. Defaults to None.

        Returns:
            DeleteResult: result of the deletion
        """
        _filters = filters if filters else {}
        result = await self.collection.delete_many(_filters, session=session)
        LOG.debug("Delete %d actions with filters %s", result.deleted_count, _filters)
        return result
