"""
collections
"""
from abc import ABCMeta
from dataclasses import dataclass, field
from enum import Enum, unique, auto
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection
from pymongo import IndexModel, errors as mongo_errors

from ateme.um_backend.loggers import LOG


@unique
class Collections(Enum):
    """[Collections]
    """
    # pylint: disable=invalid-name
    admin = auto()
    users = auto()
    tokens = auto()
    scopes = auto()
    idp_config = auto()
    configuration = auto()
    actions = auto()
    api_descriptors = auto()
    clients = auto()
    ldap_cache = auto()


@dataclass(kw_only=True)
class CollectionBase(metaclass=ABCMeta):
    """ CollectionBase is abstract class for all collection classes.
    """
    db: AsyncDatabase
    name: str
    # indexes
    deprecated_indexes: list[IndexModel] = field(init=False, default_factory=list)
    indexes: list[IndexModel] = field(init=False, default_factory=list)

    @property
    def collection(self) -> AsyncCollection:
        """ Collection property

        Returns:
            AsyncCollection: collection instance
        """
        return self.db[self.name]

    async def initialize(self):
        """ Create the collection if it does not already exist.
            Remove the obsolete indexes.
            Create the new required indexes.
        """
        if self.name not in await self.db.list_collection_names():
            try:
                await self.db.create_collection(self.name)
            except mongo_errors.CollectionInvalid:
                # Collection already exists, ignore this error.
                # Previous condition to check if the collection already exists is not
                # sufficient when several replicas are starting in the same time.
                pass
        # Drop indexes
        for index in self.deprecated_indexes:
            try:
                index_name = index.document["name"]
                await self.collection.drop_index(index_name)
                LOG.info("Drop index %s on %s collection", index_name, self.name)
            except mongo_errors.OperationFailure:
                pass  # index doesn't exist (anymore)
        # Create indexes
        for index in self.indexes:
            index_keys = index.document["key"]
            index_kwargs = {k: v for k, v in index.document.items() if k != "key"}
            await self.db[self.name].create_index(index_keys, **index_kwargs)
            LOG.info("Create index %s (%s) on %s collection", index_keys, index_kwargs, self.name)
