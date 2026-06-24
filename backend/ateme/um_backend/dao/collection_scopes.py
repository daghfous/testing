"""
collection scopes
"""
from dataclasses import dataclass
from pymongo import ASCENDING, IndexModel
from pymongo.results import DeleteResult, InsertManyResult, InsertOneResult, UpdateResult
from pymongo.errors import BulkWriteError
from pymongo.collection import ReturnDocument
from pymongo.asynchronous.client_session import AsyncClientSession

from ateme.um_backend.types import (
    DefaultScopes,
    Scope,
    ScopeFilter,
    ScopeIdSortOrder,
    ScopesPaginatedResponse,
    AllScopesDescriptions,
    MissingParameterException
)
from ateme.um_backend.dao.collections import Collections, CollectionBase
from ateme.um_backend.loggers import LOG


DEPRECATED_INDEXES: list[IndexModel] = [
]

INDEXES: list[IndexModel] = [
    IndexModel(
        keys=[('id', ASCENDING)],
        unique=True
    ),
    IndexModel(
        keys=[('label', ASCENDING)]
    )
]


@dataclass(kw_only=True)
class CollectionScopes(CollectionBase):
    """ CollectionScopes inherits from CollectionBase.
    It manages the collection `scopes`.
    """
    name: str = Collections.scopes.name

    def __post_init__(self):
        # init indexes
        self.deprecated_indexes = DEPRECATED_INDEXES
        self.indexes = INDEXES

    @staticmethod
    def _prepare_projection(_id: bool = False, internal: bool = False) -> dict:
        """
        Prepare projection to give MongoDB about fields that must not be returned for the requests related to the Scope
        By default, ``_id`` and ``internal`` fields are not returned.
        Args:
            _id: whether the ``_id`` field must be returned
            internal: whether the ``internal`` field must be returned
        Returns:
            dict: the generated projection
        """
        projection = {}
        if not _id:
            projection['_id'] = 0
        if not internal:
            projection['internal'] = 0
        return projection

    @staticmethod
    def _extract_app_scope_name(last_part: str) -> str | None:
        """ Extracts the application scope name from the last part of scope_id.
        NOTE: Required to support PMS Use case.

        Args:
            last_part (str): last part of level3 scope_id

        Returns:
            str | None: extracted scope name or None if not found
        """
        for scope in DefaultScopes:
            if last_part == scope.name:
                return scope.name
        return None

    async def store(
        self,
        scope: Scope,
        session: AsyncClientSession | None = None,
    ) -> InsertOneResult | None:
        """ Store a scope in db if not already present, then update the hat scopes with new scope inserted.

        Args:
            scope (Scope): Scope to store
            session (AsyncClientSession | None): optional session to use

        Returns:
            InsertOneResult | None: Result of the insert_one operation, or None if the scope already exists.
        """
        if await self.collection.find_one({"id": scope.id}):
            return None
        result = await self.collection.insert_one(scope.to_dict(), session=session)
        if result.acknowledged:
            hat_scopes = self._compute_hat_scopes_from_default_scopes([scope])
            await self._update_hat_scopes(hat_scopes, session=session)
        return result

    async def get_list(
        self,
        scope_filter: ScopeFilter | None = None,
        session: AsyncClientSession | None = None
    ) -> list[Scope]:
        """
        Retrieve a list of Scope objects from the collection based on the provided filters and options.

        Args:
            scope_filter (ScopeFilter | None): Optional filter to apply when querying scopes.
            session (AsyncClientSession | None): Optional MongoDB session for the query.

        Returns:
            list[Scope]: A list of Scope objects matching the query criteria.
        """
        _scope_filter = scope_filter if scope_filter else ScopeFilter()
        cursor = self.collection.find(
            _scope_filter.to_mongo_filter(),
            self._prepare_projection(),
            session=session
        )
        return [Scope.from_dict(item) for item in await cursor.to_list(None)]

    async def get_list_paginated(
        self,
        scope_filter: ScopeFilter | None = None,
        id_sort: ScopeIdSortOrder = ScopeIdSortOrder.ASCENDING,
        skip: int = 0,
        limit: int = 0
    ) -> ScopesPaginatedResponse:
        """ Retrieves a paginated list of scopes based on the provided filter, sort order, skip, and limit.

        Args:
            scope_filter (ScopeFilter | None): Optional filter to apply when querying scopes.
            id_sort (ScopeIdSortOrder): Sort order for scope IDs (ascending or descending).
            skip (int): Number of documents to skip for pagination.
            limit (int): Maximum number of documents to return.

        Returns:
            ScopesPaginatedResponse: the list of scopes, the starting index, and the total count of matching scopes.
        """
        _scope_filter = scope_filter if scope_filter else ScopeFilter()
        mongo_filter = _scope_filter.to_mongo_filter()
        # Total count
        total = await self.collection.count_documents(mongo_filter)
        # Fetch documents
        id_sort = id_sort.mongo_sort
        cursor = self.collection.find(mongo_filter, self._prepare_projection())
        cursor = cursor.sort(id_sort[0], id_sort[1]).skip(skip).limit(limit)
        scopes = [Scope.from_dict(item) for item in await cursor.to_list(None)]
        return ScopesPaginatedResponse(scopes=scopes, start=skip, total=total)

    async def get_list_non_default_ids(self) -> list[str]:
        """
        Get non default scope ids
        `default` is a not required field in scope.
        Use `$ne` to get all scopes without default field or set to false.

        Returns:
            list[str]: list of scope ids
        """
        scope_filter = ScopeFilter(
            default=False
        )
        cursor = self.collection.find(
            scope_filter.to_mongo_filter(),
            {"_id": 0, "id": 1}
        )
        # return a list with only the scope ids
        return [doc["id"] for doc in await cursor.to_list(None)]

    async def list_all_actions(self, scopes: list[str]) -> list[str]:
        """ Recursively retrieves all unique actions from the provided list of scope IDs.

        Args:
            scopes (list[str]): A list of scope IDs to retrieve actions from.

        Returns:
            list[str]: A list of unique action dictionaries found within the scopes.
        """
        content = []
        for scope_item in scopes:
            scope = await self.get_by_id(_id=scope_item, all_scopes=True)
            if not scope:
                LOG.warning("Can't find scope %s", scope_item)
                continue
            for item in scope["content"]:
                if item.get("scope"):
                    content += await self.list_all_actions([item.get("scope")])
                else:
                    content.append(item)
        # Return a list of unique action
        # build dict in order to get unique "action" property
        return list({value["action"]: value for value in content}.values())

    async def get_by_id(
        self,
        _id: str,
        all_scopes: bool = False,
        internal: bool = False,
        session: AsyncClientSession | None = None
    ) -> dict:
        """

        Get scopes from db
        :param _id:
        :param all_scopes:
        :param internal:
        :param session:
        :return: list of scopes without _id
        """
        scope_filter = ScopeFilter(
            scope_ids=[_id],
            internal=None if all_scopes else internal
        )
        return await self.collection.find_one(
            scope_filter.to_mongo_filter(),
            self._prepare_projection(),
            session=session
        )

    async def update_by_id(self, _id: str, scope: Scope, internal: bool = False) -> UpdateResult:
        """ Update scope by id

        Args:
            _id (str): scope id
            scope (Scope): scope to update
            internal (bool, optional): Internal value of the scope

        Returns:
            UpdateResult: result of the update operation
        """
        scope_filter = ScopeFilter(scope_ids=[_id], internal=internal)
        return await self.collection.update_one(
            scope_filter.to_mongo_filter(),
            {"$set": scope.to_dict()}
        )

    async def remove_by_id(self, _id: str, internal: bool = False) -> DeleteResult:
        """ Remove scope by id

        Args:
            _id (str): scope id
            internal (bool, optional): Internal value of the scope

        Returns:
            DeleteResult: result of the delete operation
        """
        scope_filter = ScopeFilter(scope_ids=[_id], internal=internal)
        return await self.collection.delete_one(scope_filter.to_mongo_filter())

    async def replace_many(
        self,
        scopes: list[Scope],
        prefix: str,
        app_name: str | None = None,
        session: AsyncClientSession | None = None
    ):
        """ Replace the scopes in the collection based on the provided prefix and optional app name.
        This method deletes all existing scopes matching the given filter (prefix and app_name),
        then iterates through the provided scopes list. For each scope, it checks if the scope already exists:
        - If it exists, updates its content using $addToSet to avoid duplicates.
        - If it does not exist, inserts it as a new document.
        After updating/inserting scopes, computes and updates related "hat scopes".

        Args:
            scopes (list[Scope]): List of Scope objects to update or insert.
            prefix (str): Prefix used to filter scopes for deletion and update.
            app_name (str | None, optional): Application name used in the filter. Defaults to None.
            session (AsyncClientSession | None, optional): MongoDB session for transactional operations.

        Returns:
            None

        Raises:
            Any exceptions raised by MongoDB operations are propagated.
        """
        scope_filter = ScopeFilter(
            prefix=prefix,
            app_name=app_name,
            default=True
        )
        mongo_filter = scope_filter.to_mongo_filter()
        # Delete all scopes matching with the scope filter
        delete_res = await self.collection.delete_many(mongo_filter, session=session)
        LOG.debug("Delete scopes result: %s with filter %s", delete_res.deleted_count, mongo_filter)
        for scope in scopes:
            # In order the transaction can function without a problem, we need it to avoid
            # the "DuplicateKeyError" which was triggered from the method "insert_one"
            # That's why we first look up in the db the scope id and then we update or insert
            get_scope = await self.collection.find_one({"id": scope.id}, session=session)
            if get_scope:
                update_res = await self.collection.update_one(
                    {"id": scope.id},
                    {"$addToSet": {"content": {"$each": scope.content}}},
                    session=session
                )
                LOG.debug("Update scope %s, modified count: %d", scope.id, update_res.modified_count)
            else:
                insert_res = await self.collection.insert_one(scope.to_dict(), session=session)
                LOG.debug("Insert new scope %s, acknowledged: %d", scope.id, insert_res.acknowledged)

        hat_scopes = self._compute_hat_scopes_from_default_scopes(scopes)
        await self._update_hat_scopes(hat_scopes, session=session)

    async def replace_defaults(
        self,
        default_scopes: list[Scope],
        manage_app_scopes: bool = False,
        session: AsyncClientSession | None = None,
    ) -> tuple[bool, InsertManyResult | None]:
        """
        Replace the default scopes and then update the app scopes and hat scopes.
        Override the preexisting scopes.
        Create app scopes if required

        Default scopes are the scopes written on the api.yaml file
        Args:
            default_scopes (list[Scope]): list of scopes to create or update
            manage_app_scopes (bool): True if the app scopes should be created/updated based on the default scopes
            session: optional session to use
        Returns:
            bool: True if update is successful, False otherwise
            InsertManyResult | None: Result of the insert_many operation, or None if it failed
        """
        # TODO: replace "default" by "Base Level" scopes (idem with hat and app scopes,
        # should be "Top Level" and "Middle Level" remove default scopes with same prefix
        # scope.id format is either "<app-name>:<sub-app>:<prefix>:<scope>", "<app-name>:<prefix>:<scope>"
        # or "<prefix>:<scope>"
        update_result = None
        try:
            prefixes = []
            for scope in default_scopes:
                if not scope.default:
                    # Force default to True
                    scope.default = True
                scope.validate()
                id_parts = scope.id.split(':')
                prefix = id_parts[:-1]  # remove <scope> part
                if ":".join(prefix) not in prefixes:
                    # build prefix i.e. "<app-name>:<sub-app>:<prefix>", "<app-name>:<prefix>" or "<prefix>"
                    prefixes.append(":".join(prefix))
            for prefix in prefixes:
                # Get the last part of the prefix i.e. <prefix>
                if prefix.split(":")[-1] in ['usr', 'all']:
                    continue
                # Remove all the scopes with prefix starting with <app-name>:<sub-app>:<prefix>,
                # <app-name>:<prefix> (if <app-name> set) or with <prefix>, ([^:]+)$ corresponds to <scope> part
                await self.collection.delete_many(
                    {"default": True, "id": {"$regex": f"^{prefix}:([^:]+)$"}},
                    session=session,
                )
        except (BulkWriteError, MissingParameterException):
            LOG.exception("Update default scopes failed")
            return False, None

        try:
            update_result = await self.collection.insert_many(
                [scope.to_dict() for scope in default_scopes],
                session=session
            )
            hat_scopes = []
            if manage_app_scopes:
                # For a scope level3, there should be one app scope containing this scope
                # If not, the corresponding app scope is updated or created
                app_scopes_ids_created = set()
                for scope in default_scopes:
                    app_scope_created = await self._update_app_scope(scope_id_to_add=scope.id, session=session)
                    if app_scope_created:
                        app_scopes_ids_created.add(app_scope_created)
                hat_scopes = self._compute_hat_scopes_from_app_scopes(app_scopes_ids_created)
            else:
                hat_scopes = self._compute_hat_scopes_from_default_scopes(default_scopes)
            await self._update_hat_scopes(hat_scopes, session=session)

        except BulkWriteError as errors:
            for error in errors.details['writeErrors']:
                LOG.error("Scope %s was not inserted because of %s", error['keyValue']['id'], error['errmsg'])
            return False, None
        return True, update_result

    @staticmethod
    def _compute_hat_scopes_from_app_scopes(app_scopes_ids: set[str]) -> dict:
        """
        Compute hat scopes from app scopes, used for cluster mode with 3 levels of scopes (default, app and hat scopes).
        App scopes are generated from:
         - POST /auth_data query (Auth Loader)
         - command line arg --default-auth-data
        Args:
            app_scopes_ids (set[str]): set of app scopes related to the hat scopes to create
        Returns:
            hat_scopes (dict): hat_scopes computed
        """
        hat_scopes = {}
        for scope in DefaultScopes:
            hat_scopes[f"all:{scope.name}"] = []

        for app_scope_id in app_scopes_ids:
            role = app_scope_id.split(":")[-1]
            hat_scopes[f"all:{role}"].append({"scope": app_scope_id})
        return hat_scopes

    @staticmethod
    def _compute_hat_scopes_from_default_scopes(default_scopes: list[Scope]) -> dict:
        """
        Compute hat scopes from default scopes
        - appliance mode where there are no app scopes (command line args --default-auth-data)
        - user management for itself (initialize) or other PMF components loading auth data (POST /api_definition)
        Args:
            param default_scopes: default scopes (scopes containing actions only)
        Returns:
            hat_scopes (dict): hat scopes data created
        """
        default_scope_ids = []
        for scope in default_scopes:
            if scope.default and \
                'internal' not in scope.id and\
                    len(scope.id.split(':')) < 3:
                default_scope_ids.append(scope.id)
        hat_scopes = {}
        for scope in DefaultScopes:
            hat_scopes[f"all:{scope.name}"] = []
        for default_scope_id in default_scope_ids:
            # default_scope_id examples: 'my-app:usr_administrator' or 'usr:administrator'
            _scope_name = default_scope_id.split(':')[-1]
            if _scope_name in [scope.name for scope in DefaultScopes]:
                hat_scopes[f"all:{_scope_name}"].append({'scope': default_scope_id})
            if default_scope_id == "usr:guest":
                # As usr:operator and usr:monitoring scopes does not exist in the UM Api definition (api.yaml),
                # we add usr:guest to hat scopes all:operator and all:monitoring
                # for users with that roles be able to query User Management
                hat_scopes[f"all:{DefaultScopes.operator.name}"].append({'scope': default_scope_id})
                hat_scopes[f"all:{DefaultScopes.monitoring.name}"].append({'scope': default_scope_id})
        return hat_scopes

    async def _update_hat_scopes(
        self,
        hat_scopes: dict,
        session: AsyncClientSession | None = None
    ):
        """
        Create or update hat scopes content in database
        :param dict hat_scopes: data to insert or update in database
        :param session: Mongo session client
        :return:
        """
        for hat_scope_id, content in hat_scopes.items():
            label = 'Global Role'
            scope_name = hat_scope_id.split(':')[1]
            hat_scope = Scope(id=hat_scope_id,
                              label=label,
                              content=content,
                              title=scope_name.capitalize(),
                              description=AllScopesDescriptions[scope_name].value,
                              default=True,
                              internal=False).to_dict()
            # In order the transaction can function without a problem, we need it to avoid
            # the "DuplicateKeyError" which was triggered from the method "insert_one"
            # That's why we first look up in the db the hat scope id and then we update or insert
            scope = await self.collection.find_one({'id': hat_scope_id}, session=session)
            if not scope:
                result = await self.collection.insert_one(hat_scope, session=session)
                LOG.debug("Insert new hat scope %s, result: %s", hat_scope_id, result.acknowledged)
            else:
                result = await self.collection.update_one(
                    {"id": hat_scope_id},
                    {"$addToSet": {"content": {"$each": content}}},
                    session=session)
                LOG.debug("Update hat scope %s, result: %s", hat_scope_id, result.modified_count)

    async def clean_hat_scopes(
        self,
        scopes: list[Scope],
        manage_app_scopes: bool,
        session: AsyncClientSession | None = None
    ):
        """
        Clean hat scopes containing a list of scopes ids in their contents

        Args:
            scopes (list[Scope]): list of scopes to remove
            manage_app_scopes (bool): True if the app scopes should be cleaned based on the default scopes
            session (AsyncClientSession | None, optional): Session. Defaults to None.
        """
        scope_ids = [item.id for item in scopes]

        remove_app_scope_ids = set()
        for scope_id in scope_ids:
            delete_result = await self.collection.delete_one(
                {"id": scope_id},
                session=session
            )
            if manage_app_scopes:
                # Clean up app scope that contains this scope: Removing this level3 scope from its content
                # and delete this app scope if its content is empty now.
                app_scope_id = await self._clean_app_scope(scope_id, session=session)
                if app_scope_id:
                    remove_app_scope_ids.add(app_scope_id)
            LOG.debug("Delete scope %s, result: %s", scope_id, delete_result.deleted_count)

        update_hat_scope_result = await self.collection.update_many(
            {"id": {"$regex": "all:"}},
            {"$pull": {"content": {"scope": {"$in": scope_ids + list(remove_app_scope_ids)}}}},
        )
        LOG.debug("Update hat scopes, %s scopes modified after removing app and default scopes",
                  update_hat_scope_result.modified_count)

    async def _update_app_scope(
        self,
        scope_id_to_add: str,
        session: AsyncClientSession | None = None
    ) -> str | None:
        """
        Updates or creates an application scope in the database with the given scope ID.

        If the application scope does not exist, it creates a new scope document and adds the provided scope ID to its content.
        If the application scope already exists, it adds the scope ID to the content array if not already present.

        Args:
            scope_id_to_add (str): The scope ID to add to the application scope.
            session (AsyncClientSession | None, optional): The MongoDB session to use for the operation.

        Returns:
            str | None: The application scope ID if a new scope was created, otherwise None.
        """
        id_parts = scope_id_to_add.split(":")
        app_scope_label = id_parts[0]
        app_scope_name = self._extract_app_scope_name(id_parts[-1])
        if not app_scope_name:
            LOG.warning("Cannot extract app scope name from scope id %s, skipping app scope update.", scope_id_to_add)
            return None

        app_scope_id = f"{app_scope_label}:{app_scope_name}"
        content_to_add = {"scope": scope_id_to_add}
        app_scope = Scope(
            id=app_scope_id,
            label=app_scope_label,
            content=[],
            title=f"{app_scope_name.capitalize()} - {app_scope_label.lower()}",
            description=f"Scope {app_scope_name} for {app_scope_label}",
            default=True,
            internal=False
        ).to_dict()

        # In order the transaction can function without a problem, we need it to avoid
        # the "DuplicateKeyError" which was triggered from the method "insert_one"
        # That's why we first look up in the db this scope id and then we update or insert
        scope_in_db = await self.collection.find_one({'id': app_scope_id}, session=session)

        if not scope_in_db:
            # create app scope
            app_scope["content"].append(content_to_add)
            result = await self.collection.insert_one(app_scope, session=session)
            LOG.debug("Inserted new app scope %s, result: %s", app_scope_id, result.acknowledged)
            return app_scope_id

        # update app scope
        content_in_db = scope_in_db.get('content', [])
        # If the new content is already present in the app scope, we don't need to update it
        if content_to_add in content_in_db:
            LOG.debug(
                "Content scope %s already present in app scope %s, skipping update.", content_to_add, app_scope_id
            )
        else:
            # Update the document by adding the new content item
            result = await self.collection.update_one(
                {"id": app_scope_id},
                {"$addToSet": {"content": {"$each": [content_to_add]}}},
                session=session
            )
            LOG.debug(
                "Updated app scope %s with content %s, result: %s", app_scope_id, content_to_add, result.modified_count
            )
        return None

    async def _clean_app_scope(
        self,
        scope_id_to_remove: str,
        session: AsyncClientSession | None = None
    ) -> str | None:
        """ Removes a specific scope from the content of an application scope in the MongoDB collection.

        If the application scope's content becomes empty after removal, deletes the application scope document.

        Args:
            scope_id_to_remove (str): The ID of the scope to remove.
            session (AsyncClientSession | None, optional): The MongoDB session to use for the operation.

        Returns:
            str | None: The deleted app scope ID, otherwise None.
        """
        id_parts = scope_id_to_remove.split(":")
        app_scope_name = self._extract_app_scope_name(id_parts[-1])
        if not app_scope_name:
            LOG.warning("Cannot extract scope name from scope id %s, skipping app scope deletion.", scope_id_to_remove)
            return None

        app_scope_id = f"{id_parts[0]}:{app_scope_name}"
        content_to_remove = {"scope": scope_id_to_remove}

        # remove the level3 scope from the content of the app scope
        content_in_db = await self.collection.find_one_and_update(
            {'id': app_scope_id}, {'$pull': {'content': content_to_remove}},
            projection={'_id': 0, 'content': 1},
            return_document=ReturnDocument.AFTER, session=session)
        LOG.debug("Scope %s removed from app scope %s", scope_id_to_remove, app_scope_id)
        if content_in_db and not content_in_db["content"]:
            result = await self.collection.delete_one({"id": app_scope_id}, session=session)
            LOG.debug("No more content in db for app scope %s. Delete it: %s", app_scope_id, result.deleted_count)
            return app_scope_id

        return None
