"""
collection api desriptors
"""
from dataclasses import dataclass
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo import ASCENDING, IndexModel
from pymongo.results import UpdateResult, DeleteResult

from ateme.um_backend.types import (
    ApiDescriptor,
    AuthDataDescriptor
)
from ateme.um_backend.dao.collections import Collections, CollectionBase
from ateme.um_backend.loggers import LOG


DEPRECATED_INDEXES: list[IndexModel] = [
    # To deal with upgrade from v4.0 to v5.0
    IndexModel(keys=[('prefix', ASCENDING)])
]

INDEXES: list[IndexModel] = [
    IndexModel(
        keys=[('url', ASCENDING)],
        unique=True
    ),
    IndexModel(
        keys=[('prefix', ASCENDING), ('app_name', ASCENDING)],
        unique=True
    )
]


@dataclass(kw_only=True)
class CollectionApiDescriptors(CollectionBase):
    """ CollectionApiDescriptors inherits from CollectionBase.
    It manages the collection `api descriptors`.
    """
    name: str = Collections.api_descriptors.name

    def __post_init__(self):
        # init indexes
        self.deprecated_indexes = DEPRECATED_INDEXES
        self.indexes = INDEXES

    async def get_list(self) -> list[ApiDescriptor]:
        """ Get all api_descriptors

        Returns:
            List of ApiDescriptor
        """
        api_descriptors: list[dict] = await \
            self.db[Collections.api_descriptors.name].find({}, {"_id": 0}).to_list(None)
        return [ApiDescriptor.from_dict(item) for item in api_descriptors]

    async def get_by_prefix_app_name(
        self,
        prefix: str,
        app_name: str | None = None
    ) -> ApiDescriptor | None:
        """ Get the api_descriptor matching with prefix and app_name.

        Args:
            prefix (str): app prefix
            app_name (str, optional): app name. Defaults to None.

        Returns:
            ApiDescriptor or None
        """
        _filter = {"prefix": prefix}
        if app_name:
            _filter["app_name"] = app_name
        result = await self.db[Collections.api_descriptors.name].find_one(_filter)
        if result:
            return ApiDescriptor.from_dict(result)

    async def get_by_url(self, url: str) -> ApiDescriptor | None:
        """ Get the api_descriptor matching with url.

        Args:
            url (str): api url

        Returns:
            ApiDescriptor or None
        """
        result = await self.db[Collections.api_descriptors.name].find_one({"url": url})
        if result:
            return ApiDescriptor.from_dict(result)

    async def replace(
        self,
        api_descriptor: ApiDescriptor | AuthDataDescriptor,
        session: AsyncClientSession | None = None
    ) -> UpdateResult:
        """ Replace api_descriptor in the collection (by prefix and app_name).
        Before inserting it, delete any existing entry with same url or same (app_name, prefix).

        Args:
            api_descriptor (ApiDescriptor | AuthDataDescriptor): api_descriptor to push into db
            session (AsyncClientSession, optional): client session. Defaults to None.

        Returns:
            UpdateResult
        """
        _filter = {"prefix": api_descriptor.prefix, "app_name": api_descriptor.app_name}
        await self.db[Collections.api_descriptors.name].delete_one(
            {
                "$or": [
                    {"url": api_descriptor.url},
                    {"app_name": api_descriptor.app_name, "prefix": api_descriptor.prefix},
                ]
            },
            session=session
        )
        return await self.db[Collections.api_descriptors.name].update_one(
            _filter,
            {
                "$set": {
                    "prefix": api_descriptor.prefix,
                    "url": api_descriptor.url,
                    "app_name": api_descriptor.app_name
                }
            },
            upsert=True,
            session=session
        )

    async def remove_by_prefix_app_name(
        self,
        prefix: str,
        app_name: str | None = None,
        session: AsyncClientSession | None = None
    ) -> DeleteResult:
        """ Remove the api_descriptor matching with prefix and app_name.

        Args:
            prefix (str): api prefix
            app_name (str, optional): app name. Defaults to None.
            session (AsyncClientSession, optional): client session. Defaults to None.

        Returns:
            DeleteResult
        """
        # Api descriptors
        api_desc_filter = {"prefix": prefix}
        if app_name:
            api_desc_filter["app_name"] = app_name
        delete_res = await self.db[Collections.api_descriptors.name].delete_one(
            api_desc_filter, session=session
        )
        LOG.debug("Delete api_descriptors result: %d with filter %s", delete_res.deleted_count, api_desc_filter)
        return delete_res
