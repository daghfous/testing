"""
Database class
"""
# pylint: disable=C0302
from typing import Dict, Any, List, Optional, Union, Tuple

from bson import ObjectId
from pymongo import AsyncMongoClient, errors as mongo_errors, ASCENDING, ReplaceOne, InsertOne
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.collection import ReturnDocument
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult, InsertManyResult
from pymongo.server_type import SERVER_TYPE

from ateme.um_backend.loggers import LOG
from ateme.um_backend.types import (
    Action,
    ApiDescriptor,
    AuthData,
    AuthDataDescriptor,
    Configuration,
    DEFAULT_LOCAL_IDP_NAME,
    IdpConfig,
    IdpLocalConfig,
    IdpType,
    LdapConfig,
    SamlConfig,
    Scope,
    ScopeFilter,
    User
)
from ateme.um_backend.dao import (
    Collections,
    CollectionTokens,
    CollectionConfiguration,
    CollectionClients,
    CollectionActions,
    CollectionScopes,
    CollectionApiDescriptors
)
from ateme.um_backend.types.roles_mapper import RolesMapperType
from ateme.um_backend.utils import compute_app_scopes


class UserAlreadyExist(Exception):
    """

    UserAlreadyExist class
    """


class UpdateFilterKeyError(Exception):
    """

    Fail to generate bulk_write operations, due to KeyError on filter build
    """


class Database:  # pylint: disable=too-many-public-methods
    """
    Database class
    """

    def __init__(self, client: AsyncMongoClient, db_name: Optional[str] = None):
        """

        :param client:
        :param db_name:
        """
        self._db = client[db_name]
        self._db_name = db_name
        self._collection_configuration = CollectionConfiguration(db=self.db)
        self._collection_tokens = CollectionTokens(db=self.db)
        self._collection_clients = CollectionClients(db=self.db)
        self._collection_actions = CollectionActions(db=self.db)
        self._collection_scopes = CollectionScopes(db=self.db)
        self._collection_api_descriptors = CollectionApiDescriptors(db=self.db)

    @property
    def db(self) -> AsyncDatabase:
        """

        db getter
        :return:
        """
        return self._db

    @property
    def client(self) -> AsyncMongoClient:
        """

        return mongo client
        :return:
        """
        return self.db.client

    @property
    def collection_tokens(self) -> CollectionTokens:
        """ Property collection_tokens

        Returns:
            CollectionTokens: collection tokens instance
        """
        return self._collection_tokens

    @property
    def collection_configuration(self) -> CollectionConfiguration:
        """ Property collection_configuration

        Returns:
            CollectionTokens: collection configuration instance
        """
        return self._collection_configuration

    @property
    def collection_clients(self) -> CollectionClients:
        """ Property collection_clients

        Returns:
            CollectionClients: collection clients instance
        """
        return self._collection_clients

    @property
    def collection_actions(self) -> CollectionActions:
        """ Property collection_actions

        Returns:
            CollectionActions: collection actions instance
        """
        return self._collection_actions

    @property
    def collection_scopes(self) -> CollectionScopes:
        """ Property collection_scopes

        Returns:
            CollectionScopes: collection scopes instance
        """
        return self._collection_scopes

    @property
    def collection_api_descriptors(self) -> CollectionApiDescriptors:
        """ Property collection_api_descriptors

        Returns:
            CollectionApiDescriptors: collection api descriptors instance
        """
        return self._collection_api_descriptors

    async def initialize(self):
        # pylint: disable=too-many-nested-blocks,too-many-branches
        """
        initialize database collections
        """
        # To deal with upgrade from v4.0 to v5.0,
        # drop existing indexes on users & idp_config (previously ldap_config) collection created by UM v4.0
        await self.drop_index(Collections.users.name, ('user_id', ASCENDING))
        await self.drop_index(Collections.users.name, ('username', ASCENDING))
        await self.drop_index(Collections.idp_config.name, ('domain', ASCENDING))

        # Create all need collections in db
        for collection in Collections:

            if collection in [
                Collections.tokens,
                Collections.configuration,
                Collections.clients,
                Collections.actions,
                Collections.scopes,
                Collections.api_descriptors
            ]:
                # skip the collections based on the new implementation
                continue

            # create collections if it does not already exist
            if collection.name not in await self.db.list_collection_names():
                try:
                    await self.db.create_collection(collection.name)
                except mongo_errors.CollectionInvalid:
                    pass  # collection probably already exists, we ignore the creation.
                except mongo_errors.OperationFailure:
                    pass  # collection probably already exists, we ignore the creation.

            # create indexes if it does not already exist
            if collection.name == Collections.users.name:
                await self.db[collection.name].create_index([('user_id', ASCENDING), ('idp_name', ASCENDING)],
                                                            unique=True)
                await self.db[collection.name].create_index([('username', ASCENDING), ('idp_name', ASCENDING)],
                                                            unique=True)
            elif collection.name == Collections.admin.name:
                await self.db[collection.name].create_index([('user_id', ASCENDING)], unique=True)
                await self.db[collection.name].create_index([('username', ASCENDING)], unique=True)
            elif collection.name == Collections.idp_config.name:
                await self.db[collection.name].create_index([('idp_name', ASCENDING)], unique=True)
            elif collection.name == Collections.ldap_cache.name:
                await self.db[collection.name].create_index([('idp_name', ASCENDING)], unique=True)

        # Collections with new implementation
        await self.collection_configuration.initialize()
        await self.collection_tokens.initialize()
        await self.collection_clients.initialize()
        await self.collection_actions.initialize()
        await self.collection_scopes.initialize()
        await self.collection_api_descriptors.initialize()

    async def drop_index(self, collection_name: str, index: tuple[str, int] | list[tuple[str, int]]) -> None:
        """
        Drop index of a given collection
        :param collection_name:
        :param index:
        """
        try:
            await self.db[collection_name].drop_index(index if isinstance(index, list) else [index])
            LOG.info("Drop index %s on %s collection", index, collection_name)
        except mongo_errors.OperationFailure:
            pass  # index doesn't exist (anymore)

    async def is_database_available(self) -> bool:
        """
        Checks whether the database is available and ready to use.

        This method attempts to connect to the database by sending a "ping" command,
        and then checks the topology description of the MongoDB cluster to ensure
        that a primary or standalone server is available.

        Returns:
            bool: True if the database is available, False otherwise
        """
        try:
            # Trigger a connection attempt for a minimal check
            await self.run_admin_command("ping")
        except Exception as exception:
            LOG.error("MongoDB ping fails: %s", exception)
            return False

        # Based on the topology, check whether the Primary member is available
        # If only RSSecondary server(s) is/are available, we assume that the database is not available.
        # Also search for a Standalone server (for non Replicaset configuration)
        topology = self.client.topology_description
        if not topology:
            LOG.error("None database topology available.")
            return False

        server_descriptions = topology.server_descriptions()
        if len(server_descriptions) > 0:
            for server_address, server_info in server_descriptions.items():
                LOG.debug("Server Info: Address=%s, Type=%s, Readable=%s, Writable=%s",
                          server_address, server_info.server_type, server_info.is_readable, server_info.is_writable)
                if (server_info.is_readable and server_info.is_writable and
                        server_info.server_type in (SERVER_TYPE.RSPrimary, SERVER_TYPE.Standalone)):
                    LOG.debug("A primary (or standalone) database server is available.")
                    return True
        LOG.error("None database server available.")
        return False

    async def run_admin_command(self, command: str):
        """
        Run an admin command on the database client.
        Args:
            command (str): The command to run.
        Returns:
            None
        """
        await self.client.admin.command(command)

    @staticmethod
    def __prepare_filters(internal: bool = False) -> Dict[str, bool | Dict[str, bool]]:
        """
        Prepare filters to give MongoDB about ``internal`` field.
        Args:
            internal: whether the `'internal`' field must be True
        Returns:
            dict: the generated filters.

            Default to: ``{"internal": {"$ne": True}}`` meaning objects will be returned if field is ``False`` or absent
        """
        filters = {
            "internal": {"$ne": True}
        }
        if internal:
            filters['internal'] = True
        return filters

    @staticmethod
    def __prepare_user_projection(_id: bool = False, creation_id: bool = False, internal: bool = False) -> dict:
        """
        Prepare projection to give MongoDB about fields that must not be returned for requests related to the User
        By default, ``password``, ``_id``, ``creation_id`` and ``internal`` fields are not returned.
        Args:
            _id: whether the ``_id`` field must be returned
            creation_id: whether the ``creation_id`` field must be returned
            internal: whether the ``internal`` field must be returned
        Returns:
            dict: the generated projection
        """
        projection = {"password": 0}
        if not _id:
            projection['_id'] = 0
        if not creation_id:
            projection['creation_id'] = 0
        if not internal:
            projection['internal'] = 0
        return projection

    # Configuration #m
    async def insert_configuration(self, configuration: Configuration) -> Configuration:
        """
        Insert configuration in db
        Return the configuration from db if it already exists, else the inserted one

        :param configuration: [description]
        :return: The configuration from db
        """
        _configuration = await self.db[Collections.configuration.name].find_one({})
        if not _configuration:
            _result = await self.db[Collections.configuration.name].insert_one(configuration.to_dict())
            if not _result.acknowledged:
                raise Exception("Fail to insert configuration")
            return configuration
        return Configuration.from_dict(_configuration)

    async def get_configuration(self) -> Configuration:
        """
        Return the configuration

        :return: Configuration
        """
        conf = await self.db[Collections.configuration.name].find_one({})
        if conf:
            return Configuration.from_dict(conf)
        return Configuration()

    # pylint: disable-msg=too-many-arguments, too-many-positional-arguments
    async def update_configuration(self, max_successive_failed_login: int = None,
                                   user_deactivation_period: int = None, token_expiration: int = None,
                                   refresh_token_expiration: int = None,
                                   token_cleaning_period: int = None,
                                   logout_timeout: int = None,
                                   expiration_delay_in_days: int = None,
                                   password_min_length: int = None) -> Configuration:
        """
        Update completely or partially the configuration
        Args:
            max_successive_failed_login: Max successive failed logins before disabling a user
            user_deactivation_period: Period (in minutes) during the user is disabled after
                                      max_successive_failed_login ('-1' for an admin re-enables the user)
            token_expiration: Expiration period (in seconds) for the token auth
            refresh_token_expiration: Expiration period (in seconds) for the refresh token auth
            token_cleaning_period:Period (in hours) at the end of which token auth is removed from db
            logout_timeout:Period (in seconds) for the timeout duration
            expiration_delay_in_days: Number of days before a password must be changed
            password_min_length: Password minimum length
        """
        data = {}
        if max_successive_failed_login is not None:
            data['max_successive_failed_login'] = max_successive_failed_login
        if user_deactivation_period is not None:
            data['user_deactivation_period'] = user_deactivation_period
        if token_expiration is not None:
            data['token_expiration'] = token_expiration
        if refresh_token_expiration is not None:
            data['refresh_token_expiration'] = refresh_token_expiration
        if token_cleaning_period is not None:
            data['token_cleaning_period'] = token_cleaning_period
        if logout_timeout is not None:
            data['logout_timeout'] = logout_timeout
        if expiration_delay_in_days is not None:
            data["password_policy.expiration_delay_in_days"] = expiration_delay_in_days
        if password_min_length is not None:
            data["password_policy.password_min_length"] = password_min_length
        result = await self.db[Collections.configuration.name].find_one_and_update(
            {}, {"$set": data}, return_document=ReturnDocument.AFTER)
        return Configuration.from_dict(result)

    # Users #
    async def get_admin_user(self) -> dict:
        """ Retrieve user admin, only one admin user """
        return await self.db[Collections.admin.name].find_one({**self.__prepare_filters(),
                                                               "scopes": {"$regex": "administrator"}},
                                                              {"_id": 0, "internal": 0})

    async def create_user(self, user_object: User, collection_name: str,
                          session: Optional[AsyncClientSession] = None) -> InsertOneResult:
        """

        :param user_object:
        :param collection_name:
        :param session:
        :return:
        """
        try:
            return await self.db[collection_name].insert_one(
                user_object.to_dict(with_creation_id=True), session=session)
        except mongo_errors.DuplicateKeyError as exc:
            raise UserAlreadyExist(f'{user_object.username} already exists') from exc
        except Exception as exception:
            raise exception

    async def update_user_by_id(self, user_id: str, user_object: User,
                                session: Optional[AsyncClientSession] = None) -> UpdateResult:
        """
        Update user

        Args:
            user_id (str): User ID
            user_object (User): User data
            session (AsyncClientSession, optional): Database transaction session. Defaults to None.

        Returns:
            UpdateResult: Mongo update result
        """
        data = user_object.to_dict(with_creation_id=True)
        is_admin = await self.is_admin(user_id=user_id)
        if is_admin:
            result = await self.db[Collections.admin.name].update_one(
                {"user_id": user_id}, {"$set": data}, session=session)
        else:
            result = await self.db[Collections.users.name].update_one(
                {"user_id": user_id}, {"$set": data}, session=session)
        return result

    async def force_password_expiration_for_local_users(self) -> UpdateResult:
        """
        Change password expiration for local users having
        password expiration enabled
        :return:
        """
        return await self.db[Collections.users.name].update_many(
            {**self.__prepare_filters(), "idp_name": DEFAULT_LOCAL_IDP_NAME, "password_expiration_disabled": False},
            {"$set":  {"password_expired": True}}
        )

    async def update_users_by_idp_scopes(self, idp_name: str, scopes: list,
                                         session: Optional[AsyncClientSession] = None) -> UpdateResult:
        """
        :param idp_name: idp name
        :param scopes: new modified scopes
        :param session: pymongo async session
        """
        result = await self.db[Collections.users.name].update_many(
            {**self.__prepare_filters(), "idp_name": idp_name},
            {"$set":  {"scopes": scopes}}, session=session
        )
        return result

    async def delete_user_by_name(self, username: str, idp_name: str, internal: bool = False) \
            -> Optional[DeleteResult]:
        """

        :param username:
        :param idp_name:
        :param internal:
        :return:
        """
        # Assert that the user to delete is not an admin
        is_admin = await self.is_admin(username=username)
        if is_admin:
            return None
        user_filter = {**self.__prepare_filters(internal=internal), "username": username, "idp_name": idp_name}
        return await self.db[Collections.users.name].delete_one(user_filter)

    async def delete_users_by_idp_name(self, idp_name: str, session: Optional[AsyncClientSession] = None)\
            -> DeleteResult:
        """
        :param idp_name:
        :param session:
        :return:
        """
        users_filter = {**self.__prepare_filters(), "idp_name": idp_name}
        return await self.db[Collections.users.name].delete_many(users_filter, session=session)

    # pylint: disable=too-many-branches,too-many-locals,too-many-positional-arguments
    async def update_user_by_name(
        self, username: str, idp_name: str, internal: bool = False, scopes: list = None,
        password: Optional[str] = None, level: Optional[str] = None,
        enabled: Optional[bool] = None,
        first_login: Optional[bool] = None, password_last_update: Optional[int] = None,
        preferences: Optional[dict] = None, session: Optional[AsyncClientSession] = None,
        session_timeout_disabled: Optional[bool] = None,
        password_expiration_disabled: Optional[bool] = None,
        password_expired: Optional[bool] = None
    ) -> set:
        """
        Update user

        Args:
            username (str): Username
            idp_name (str): Idp name
            internal (bool, optional): True if user is internal. Defaults to False.
            session (AsyncClientSession, optional): Database transaction session. Defaults to None.
            scopes (list, optional): List of scopes. Defaults to None.
            password (str, optional): Password. Defaults to None.
            level (str, optional): Level. Defaults to None.
            enabled (bool, optional): False if user is disabled. Defaults to None.
            first_login (bool, optional): True if its first login. Defaults to None.
            preferences (dict, optional): User preferences (E.g. {favorite_application: app_name})
            password_last_update (int, optional): Date of last update password. Defaults to None.
            session_timeout_disabled (bool, optional): True if the timeout feature is turned off. Defaults to False.
            password_expiration_disabled (bool): Flag to disable password expiration for the user
            password_expired (bool): True if the password is expired

        Returns:
            set: Set of non-existing scopes
        """
        update_object = {}
        inexisting_scopes = set()
        if scopes is not None:
            user = await self.get_user_by_name(username=username, internal=internal,
                                               idp_name=idp_name, session=session)
            if not user:
                return []
            user_scopes = set()
            for scope in scopes:
                # only scope with the same internal value as user could be added
                if await self.collection_scopes.get_by_id(_id=scope, internal=internal, session=session):
                    user_scopes.add(scope)
                else:
                    inexisting_scopes.add(scope)
            update_object.update({"scopes": list(user_scopes)})
        if password:
            user_id = User.generate_hash([username, str(password), idp_name])
            update_object.update({"user_id": user_id})
            # password is not store in database if the user is not a local one
            if idp_name == DEFAULT_LOCAL_IDP_NAME:
                update_object.update({"password": password})
        if level is not None:
            # level can be equal to 0 (!)
            update_object.update({"level": level})
        if password_last_update is not None:
            update_object.update({"password_last_update": password_last_update})
        if enabled is not None:
            update_object.update({"enabled": enabled})
        if first_login is not None:
            update_object.update({"first_login": first_login})
        if preferences is not None:
            update_object.update({"preferences": preferences})
        if session_timeout_disabled is not None:
            update_object.update({"session_timeout_disabled": session_timeout_disabled})
        if password_expiration_disabled is not None:
            update_object.update({"password_expiration_disabled": password_expiration_disabled})
        if password_expired is not None:
            update_object.update({"password_expired": password_expired})
        update_object.update({"internal": internal})

        if update_object:
            user_filter = {**self.__prepare_filters(internal=internal), "username": username, "idp_name": idp_name}
            is_admin = await self.is_admin(username=username)
            if is_admin:
                await self.db[Collections.admin.name].update_one(user_filter,
                                                                 {"$set": update_object},
                                                                 session=session)
            else:
                await self.db[Collections.users.name].update_one(user_filter,
                                                                 {"$set": update_object},
                                                                 session=session)
        return inexisting_scopes

    async def update_default_users(
            self,
            default_users: List[User],
            session: Optional[AsyncClientSession] = None
    ) -> Tuple[bool, Optional[InsertManyResult]]:
        """
        Update the default users: delete existing default users then create the provided ones.
        Args:
            default_users: default users to create
            session: optional session to use
        Returns:
            Tuple[bool, Optional[InsertManyResult]]: whether the operation was a success, operation result
        """
        update_result = None
        try:
            await self.db[Collections.users.name].delete_many({"default": True}, session=session)
        except Exception as exc:
            LOG.exception("Unable to remove default users: %s", exc)
            return False, update_result

        try:
            update_result = await self.db[Collections.users.name].insert_many(
                [user.to_dict(with_creation_id=True) for user in default_users],
                session=session)
        except mongo_errors.BulkWriteError as errors:
            for error in errors.details['writeErrors']:
                LOG.error("User %s was not inserted because of %s",
                          error['keyValue']['username'], error['errmsg'])
            return False, update_result
        return True, update_result

    async def set_user_enabled(self, username: str, idp_name: str) -> UpdateResult:
        """

        Set user enabled: reactivate user
        :param username:
        :param idp_name:
        """
        is_admin = await self.is_admin(username=username)
        collection = self.db[Collections.admin.name] if is_admin else self.db[Collections.users.name]
        return await collection.find_one_and_update(
            {"username": username, "idp_name": idp_name},
            {"$set": {"enabled": True,
                      "attempts": 0}},
            upsert=True)

    async def get_user_by_generated_id(self, username: str, password: str, idp_name: str,
                                       internal_projection: bool = False) -> dict:
        """

        Retrieve user by generate hash on username and password
        :param username:
        :param password:
        :param internal_projection:
        :param idp_name:
        :return:
        """
        projection = self.__prepare_user_projection(creation_id=True, internal=internal_projection)
        user_id = User.generate_hash([username, str(password), idp_name])
        user = await self.db[Collections.users.name].find_one({"user_id": user_id}, projection)
        if user:
            return user
        # admin
        return await self.db[Collections.admin.name].find_one({"user_id": user_id}, projection)

    # pylint: disable-msg=too-many-locals,too-many-positional-arguments
    async def get_user_by_name(self, username: str, idp_name: str, internal: bool = False, all_users: bool = False,
                               _id: bool = True, internal_projection: bool = False,
                               session: Optional[AsyncClientSession] = None) -> dict:
        """

        Retrieve user by generate hash on username and password
        :param session:
        :param username:
        :param internal:
        :param all_users:
        :param _id:
        :param internal_projection:
        :param idp_name:
        :return:
        """
        if all_users:
            user_filter = {"username": username, "idp_name": idp_name}
        else:
            user_filter = {**self.__prepare_filters(internal=internal), "username": username, "idp_name": idp_name}
        projection = self.__prepare_user_projection(_id=_id, creation_id=_id, internal=internal_projection)
        admin = await self.db[Collections.admin.name].find_one(user_filter, projection, session=session)
        if admin:
            return admin

        return await self.db[Collections.users.name].find_one(user_filter, projection, session=session)

    async def get_user_by_id(self, user_id: str, _id: bool = False, creation_id: bool = False,
                             internal_projection: bool = False) -> dict:
        """
        Retrieve user by generate hash on username and password
        Args:
            user_id: ID of the user to retrieve
            _id: whether the ``_id`` field must be given
            creation_id: whether the ``creation_id`` field must be given
            internal_projection: whether the ``internal`` field must be given

        Returns:
            dict: the retrieved user
        """
        projection = {**self.__prepare_user_projection(_id=_id, creation_id=creation_id, internal=internal_projection)}
        user = await self.db[Collections.users.name].find_one({"user_id": user_id}, projection)
        if user:
            return user
        # Else it is the admin
        return await self.db[Collections.admin.name].find_one({"user_id": user_id}, projection)

    async def get_all_users(self, internal: bool = False) -> List[dict]:
        """
        Retrieve users list
        Args:
            internal: whether to return internal field
        Returns:
            list of user without _id, password and internal fields
        """
        user_filter = self.__prepare_filters(internal=internal)
        # We don't return creation_id (_id in previous versions used to salt password
        users = await self.db[Collections.users.name].find(user_filter, self.__prepare_user_projection()).to_list(None)
        admin = await self.db[Collections.admin.name].find(user_filter, self.__prepare_user_projection()).to_list(None)
        return users + admin

    async def remove_scope_from_users(self, scope_id: str):
        """
        Remove scope id from users scopes list

        :param scope_id: id of the scope
        """
        await self.db[Collections.users.name].update_many(
            {"scopes": {"$elemMatch": {"$eq": scope_id}}},
            [{"$set": {
                "scopes": {
                    "$filter": {
                        "input": "$scopes",
                        "cond": {"$ne": ["$$this", scope_id]}}}}},
             {"$set": {
                 "scopes": {
                     "$cond": {
                         "if": {
                             "$not": {
                                 "$size": {
                                     "$filter": {
                                         "input": "$scopes",
                                         "as": "line",
                                         "cond": {"$regexFind": {"input": "$$line", "regex": "usr|all"}}}}}},
                         "then": {"$concatArrays": [["usr:guest"], "$scopes"]},
                         "else": "$scopes"}}}}])

    async def is_admin(self, token: Optional[str] = None, user_id: Optional[str] = None, username: Optional[str] = None,
                       session: Optional[AsyncClientSession] = None) -> bool:
        """
        Return true if user is admin

        Args:
            token (str, optional): Token. Defaults to None.
            user_id (str, optional): User ID. Defaults to None.
            username (str, optional): User name. Defaults to None.
            session (AsyncClientSession, optional): Database transaction session. Defaults to None.

        Returns:
            bool: True if user is admin
        """
        admin = None
        if token:
            _user_id = await self.db[Collections.tokens.name].find_one(
                {"token": token}, session=session)
            admin = await self.db[Collections.admin.name].find_one(
                {"user_id": _user_id["user_id"]}, session=session)
        elif user_id:
            admin = await self.db[Collections.admin.name].find_one(
                {"user_id": user_id}, session=session)
        elif username:
            admin = await self.db[Collections.admin.name].find_one(
                {"username": username}, session=session)
        if admin:
            return True
        return False

    # Idp #
    async def store_idp_config(self, idp_config: Dict) -> InsertOneResult:
        """
        Store idp config

        :return:
        """
        return await self.db[Collections.idp_config.name].insert_one(idp_config)

    @staticmethod
    def idp_config_from_dict(idp_config):
        """
        Converts IDP configuration to an object based on its IDP type.
        :param idp_config:
        """
        from_dict_method = {
            IdpType.default.name: IdpConfig.from_dict,
            IdpType.ldap.name: LdapConfig.from_dict,
            IdpType.local.name: IdpLocalConfig.from_dict,
            IdpType.saml.name: SamlConfig.from_dict,
        }
        if idp_config["idp_type"] in from_dict_method:
            obj = (from_dict_method[idp_config["idp_type"]])(idp_config)
        else:
            obj = IdpConfig.from_dict(idp_config)
        return obj

    async def get_idp_configs(self, projection: Optional[dict] = None) \
            -> List[Union[IdpConfig, LdapConfig, IdpLocalConfig, SamlConfig]]:
        """
        Retrieve all idp config

        :param projection: Mongo db projection

        :return:
        """
        idp_config_objs: List = []
        _projection = {"_id": 0}
        if projection:
            _projection.update(projection)
        idp_configs = await self.db[Collections.idp_config.name].find({}, _projection).to_list(None)
        for idp_config in idp_configs:
            obj = Database.idp_config_from_dict(idp_config)
            idp_config_objs.append(obj)
        return idp_config_objs

    async def get_idp_configs_by_type(self, idp_type: Optional[str] = None, bind_dn_field: bool = False) -> \
            List[Union[IdpConfig, LdapConfig, IdpLocalConfig, SamlConfig]]:
        """
        Get all idp configs by idp_type
        'bin_dn_field' True if it have to exists, False by default
        :return:
        """
        idp_config_objs: List = []
        _filter = {}
        if idp_type:
            _filter["idp_type"] = idp_type
        if bind_dn_field:
            _filter["bind_dn"] = {'$nin': [None, ""]}
        idp_configs = await self.db[Collections.idp_config.name].find(_filter, {"_id": 0}).to_list(None)
        for idp_config in idp_configs:
            obj = Database.idp_config_from_dict(idp_config)
            idp_config_objs.append(obj)
        return idp_config_objs

    async def get_idp_config_by_name(
        self,
        idp_name: str,
        session: Optional[AsyncClientSession] = None,
        projection: Optional[dict] = None
    ) -> Union[LdapConfig, IdpLocalConfig, SamlConfig]:
        """
        Get one idp config by idp_name

        :param idp_name:
        :param session:
        :param projection: Mongo db projection

        :return:
        """
        _projection = {"_id": 0}
        if projection:
            _projection.update(projection)
        idp_config = await self.db[Collections.idp_config.name].find_one({"idp_name": idp_name},
                                                                         _projection, session=session)
        if not idp_config:
            return None
        return Database.idp_config_from_dict(idp_config)

    # pylint: disable-msg=too-many-arguments
    async def update_idp_config(self, idp_name: str, data: dict,
                                session: Optional[AsyncClientSession] = None) -> UpdateResult:
        """
        Update idp_config entry

        :param idp_name:
        :param data:
        :param session:
        :return:
        """
        await self.prepare_idp_mappers(data.get('mappers', []))
        return await self.db[Collections.idp_config.name].update_one({"idp_name": idp_name},
                                                                     {"$set": data},
                                                                     session=session)

    async def prepare_idp_mappers(self, mapper_list: list):
        """
        Prepare IDP mappers for insertion in database. Add an _id if not already present and check for scopes presence.
        Also, cast the _id into an ObjectId if necessary
        """
        for mapper in mapper_list:
            if not mapper.get('_id'):
                mapper['_id'] = ObjectId()
            elif isinstance(mapper.get('_id'), str):
                # Dirty hack to save the id as an ObjectId in database.
                # This way, Mongo can handle the update of the nested object instead of overriding it
                mapper['_id'] = ObjectId(mapper['_id'])
            if mapper.get('type') == RolesMapperType.simple.name:
                mapper_scopes = set()
                for scope in mapper.get('scopes_to_add', []):
                    if await self.collection_scopes.get_by_id(_id=scope):
                        mapper_scopes.add(scope)
                mapper.update({"scopes_to_add": list(mapper_scopes)})

    async def remove_idp_config(
        self,
        idp_name: str,
        session: Optional[AsyncClientSession] = None
    ) -> DeleteResult:
        """
        Remove idp_config
        :param idp_name:
        :param session:
        :return:
        """
        return await self.db[Collections.idp_config.name].delete_one({"idp_name": idp_name}, session=session)

    # Api descriptor #
    async def publish_api_descriptor(self, api_descriptor: ApiDescriptor):
        """_summary_

        Args:
            api_descriptor (ApiDescriptor): The api descriptor
        """
        # Create a transaction and update two collections in a transaction
        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                await self.collection_actions.replace_many(
                    api_descriptor.actions,
                    api_descriptor.prefix,
                    api_descriptor.app_name,
                    session
                )
                await self.collection_scopes.replace_many(
                    api_descriptor.scopes,
                    api_descriptor.prefix,
                    api_descriptor.app_name,
                    session
                )
                await self.collection_api_descriptors.replace(
                    api_descriptor,
                    session
                )

    async def publish_auth_data(self, auth_data: AuthData) -> bool:
        """
        Store in db the api_descriptors, the actions and the scopes from the auth_data

        Args:
            auth_data (AuthData): The auth data

        Returns:
            bool: Successfully published
        """
        await self.update_auth_data(auth_data.actions, auth_data.scopes, auth_data.auth_data_descriptors)
        return True

    async def get_generic_data(self,
                               collection_name: str,
                               filters: Optional[dict] = None,
                               projection: Optional[dict] = None) -> List:
        """

        Get data from Db for a collection with the specified filters and projection
        :param collection_name:
        :param filters:
        :param projection:
        :return: List
        """
        if projection:
            result = await self.db[collection_name].find(filters, projection=projection).to_list(None)
        else:
            result = await self.db[collection_name].find(filters).to_list(None)
        return result

    async def get_ldap_cache_by_idp_name(self, idp_name: str) -> dict:
        """Get ldap cache from db by idp_name

        Args:
            idp_name (str): idp name

        Returns:
            dict: idp data
        """
        return await self.db[Collections.ldap_cache.name].find_one({"idp_name": idp_name})

    async def upsert_ldap_cache_by_idp_name(self, idp_name: str, entries: List[Dict[str, Any]]) -> UpdateResult:
        """Update ldap cache in db by idp_name

        Args:
            idp_name (str): idp name
            entries (List[Dict[str, Any]]): ldap cache entries

        Returns:
            UpdateResult: update_one result
        """
        return await self.db[Collections.ldap_cache.name].update_one(
            {"idp_name": idp_name},
            {'$set': {"entries": entries}},
            upsert=True
        )

    async def find_user_in_ldap_cache(self, username: str, user_filter: str, idp_name: str) -> dict | None:
        """Find a user entry in the ldap cache in db

        Args:
            username (str): username
            user_filter (str): filter to use to retrieve the user entry
            idp_name (str): idp ndame

        Returns:
            dict or None: the user if exists else None
        """
        users = await (await self.db[Collections.ldap_cache.name].aggregate(
            [
                {"$unwind": "$entries"},
                {"$match": {
                    f"entries.{user_filter}": username,
                    "idp_name": idp_name
                }}
            ]
        )).to_list(None)
        return users[0] if users else None

    async def remove_ldap_cache_by_idp_name(
        self,
        idp_name: str,
        session: Optional[AsyncClientSession] = None
    ):
        """

        Remove ldap cache entries by idp_name.

        Args:
            idp_name (str): IDP name
            session (AsyncClientSession): pymongo async session
        """
        return await self.db[Collections.ldap_cache.name].delete_one({"idp_name": idp_name}, session=session)

    @staticmethod
    def _generate_filter_from_import_policy(import_policy: dict, data: dict) -> dict:
        """

        Generate mongo filter from import_policy

        Args:
            import_policy (dict): import policy data
            data (dict): data set

        Returns:
            dict: mongo filter
        """
        if not import_policy["key_index"]:
            return {}
        return {"$and": [{key: data[key] for key in item.keys()} for item in import_policy["key_index"]]}

    def _generate_bulk_write(
            self,
            import_policy: dict,
            data: list,
            collection_name: str
    ) -> List[Union[ReplaceOne, InsertOne]]:
        """

        Generate bulk_write operations from import_policy and data

        Args:
            import_policy (dict): import policy
            data (list): List of data to import
            collection_name (str): Collection name, usefull for UpdateFilterKeyError exception

        Returns:
            List[Union[ReplaceOne, InsertOne]]: List of operations generated

        Raises:
            UpdateFilterKeyError: Fail to build ReplaceOne filter due to KeyError
        """
        try:
            _ops = [
                ReplaceOne(
                    filter=self._generate_filter_from_import_policy(import_policy, doc),
                    replacement={
                        key: value for key, value in doc.items() if key != "_id"
                    },
                    upsert=True
                )
                if import_policy["conflict_management"] == "override"
                else InsertOne({key: value for key, value in doc.items() if key != "_id"})
                for doc in data
            ]
        except KeyError as _exception:
            raise UpdateFilterKeyError(
                f"Can't generate bulk_write operations for {collection_name} collection, "
                f"don't find key {_exception.args[0]} in data"
            ) from _exception
        return _ops

    async def import_full_configuration(self, data: list, skip_collections: List[str] = None):
        """

        Import full configuration, we start a transaction and for each collection to import
        we generate bulk write operation and apply to the collection.

        Args:
            data (list): list of collection to import
            skip_collections (List): List that contains the collections we want to skip when import data
        Raises:
            BulkWriteError: DuplicateKeyError, this error will abort transaction
        """
        if skip_collections is None:
            skip_collections = []
        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                for item in data:
                    if not item["data"]:
                        continue
                    try:
                        collection = Collections[item["collection"]]
                    except KeyError:
                        LOG.warning("Collection %s doesn't exist", item['collection'])
                        continue
                    # We check if we need to skip a collection
                    if collection.name in skip_collections:
                        continue
                    operations = self._generate_bulk_write(item["import_policy"], item["data"], collection.name)
                    res = await self.db[collection.name].bulk_write(operations, session=session)
                    LOG.debug(
                        "Bulk write on %s collection inserted_count: %d modified_count: %d",
                        collection.name,
                        res.upserted_count + res.inserted_count,
                        res.modified_count
                    )

    async def update_auth_data(
        self,
        actions: List[Action],
        scopes: List[Scope],
        api_descriptors: List[ApiDescriptor | AuthDataDescriptor],
    ):
        """
        Publish auth data from a list of action, scope and api_descriptor.

        Args:
            actions (List[Action]): List of action
            scopes (List[Scope]): List of scope
            api_descriptors (List[ApiDescriptor]): List of api_descriptor
        """
        # Compute the app scopes from both the app_names (from descriptors) and the default scope list.
        # Then, remove them from the scopes list (if present).
        manage_app_scopes, app_scopes = compute_app_scopes(api_descriptors, scopes)
        scopes = [scope for scope in scopes if scope.id not in app_scopes]

        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                if actions:
                    _, update_action_result = await self.collection_actions.replace_defaults(actions, session)
                    LOG.debug("%s actions inserted during current session", len(update_action_result.inserted_ids))
                if scopes:
                    _, update_scope_result = await self.collection_scopes.replace_defaults(
                        default_scopes=scopes,
                        manage_app_scopes=manage_app_scopes,
                        session=session
                    )
                    LOG.debug("%s scopes inserted during current session", len(update_scope_result.inserted_ids))
                if api_descriptors:
                    update_api_descriptor_result = []
                    for api_descriptor in api_descriptors:
                        update_api_descriptor_result.append(
                            await self.collection_api_descriptors.replace(api_descriptor, session)
                        )
                    _sum_modified = sum(item.modified_count for item in update_api_descriptor_result)
                    _sum_inserted = sum(1 if item.upserted_id else 0 for item in update_api_descriptor_result)
                    LOG.debug("%s api_descriptor updated and %s api_descriptor inserted during current session",
                              _sum_modified, _sum_inserted)

    async def remove_auth_data(
            self,
            actions: List[Action],
            scopes: List[Scope],
            api_descriptors: List[ApiDescriptor],
    ):
        """

        Remove auth data from a list of action, scope and api_descriptor.

        Args:
            actions (List[Action]): List of action
            scopes (List[Scope]): List of scope
            api_descriptors (List[ApiDescriptor]): List of api_descriptor
        """
        # Compute the app scopes from both the app_names (from descriptors) and the default scope list.
        # Then, remove them from the scopes list.
        manage_app_scopes, app_scopes = compute_app_scopes(api_descriptors, scopes)
        scopes = [scope for scope in scopes if scope.id not in app_scopes]

        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                if actions:
                    _action_filter = {"$or": []}
                    for action in actions:
                        _action_filter["$or"].append({"prefix": action.prefix, "name": action.name})
                    await self.collection_actions.delete_many(
                        filters=_action_filter,
                        session=session
                    )
                if scopes:
                    await self.collection_scopes.clean_hat_scopes(scopes, manage_app_scopes, session=session)
                if api_descriptors:
                    urls = [item.url for item in api_descriptors]
                    api_descriptor_result = await self.db[
                        Collections.api_descriptors.name
                    ].delete_many({"url": {"$in": urls}}, session=session)
                    LOG.debug("Delete %s api_descriptors", api_descriptor_result.deleted_count)

    async def delete_api_descriptor(self, api_descriptor: ApiDescriptor):
        """
        Delete all actions, scopes and api_descriptors for a given api_descriptor

        Args:
            api_descriptor (ApiDescriptor): An Api Descriptor
        """
        prefix = api_descriptor.prefix
        app_name = api_descriptor.app_name
        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                # Actions
                action_filter = {"prefix": prefix}
                if app_name:
                    action_filter["prefix"] = f"{app_name}:{prefix}"
                await self.collection_actions.delete_many(
                    filters=action_filter,
                    session=session
                )
                # Scopes
                scope_filter = ScopeFilter(
                    prefix=prefix,
                    app_name=app_name,
                    default=True
                )
                scopes_to_remove = await self.collection_scopes.get_list(
                    scope_filter=scope_filter, session=session
                )
                await self.collection_scopes.clean_hat_scopes(scopes_to_remove, manage_app_scopes=True, session=session)
                LOG.debug("Delete scopes with filter %s", scope_filter)
                # Api descriptors
                await self.collection_api_descriptors.remove_by_prefix_app_name(
                    prefix=prefix,
                    app_name=app_name,
                    session=session
                )
