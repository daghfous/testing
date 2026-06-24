"""
User management module
"""
# pylint: disable=too-many-lines
import argparse
import asyncio
import inspect
import io
import json
import logging
import tempfile
import os
import functools
import zipfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from base64 import b64decode
from datetime import datetime, timedelta
from typing import Any, List, Tuple, Optional, Coroutine, Callable, Awaitable
import binascii
import multidict
import yaml
from bson import ObjectId, json_util
import ldap
from pymongo.errors import DuplicateKeyError, OperationFailure
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.errors import OneLogin_Saml2_Error

from ateme.encryption_lib import AESCipher  # pylint: disable=no-name-in-module
from ateme.log import log_activity, set_activity_log
from ateme.openapi import (
    OpenApiDefinition,
    OpenApiWebApplication,
    Request,
    Response,
    Path,
    Method,
    DictWithDefault,
    HTTPUnauthorized,
    HTTPNotFound,
    HTTPInternalServerError,
    HTTPBadRequest,
    HTTPForbidden,
    HTTPServiceUnavailable,
    HTTPConflict,
    HTTPGone,
    HTTPException,
    HTTPRangeNotSatisfiable
)

from ateme.um_backend.database import Database, Collections, UserAlreadyExist
from ateme.um_backend.saml_provider import SamlProvider, IdpCallbackMode
from ateme.um_backend.ldap_provider import LdapProvider, build_user_search_filter
from ateme.um_backend.ldap import LdapClient
from ateme.um_backend.identity_provider import LocalProvider
from ateme.um_backend.loggers import (
    LOG,
    show_activity_log,
    generate_audit_log_for_idp_config_update,
    generate_audit_log_for_scope_update,
    generate_audit_log_for_user_update
)
from ateme.um_backend.types import (
    Token,
    User,
    Scope,
    ScopeFilterMode,
    ScopeFilter,
    ScopeIdSortOrder,
    Action,
    ApiDescriptor,
    IdpType,
    LdapConfig,
    SamlConfig,
    Configuration,
    Session,
    load_default_actions,
    load_default_scopes,
    DEFAULT_LOCAL_IDP_NAME
)
from ateme.um_backend.roles_mapper import (
    Attributes,
    retrieve_scopes_from_roles_mapper
)
from ateme.um_backend.types.auth_data import AuthData
from ateme.um_backend.types.auth_data_descriptor import AuthDataDescriptor
from ateme.um_backend.types.configuration import PublicConfiguration
from ateme.um_backend.types.user import load_default_users, load_default_admin
from ateme.um_backend.updater import UserUpdater
from ateme.um_backend.utils import (
    generate_scopes_and_actions,
    parse_scopes_and_actions,
    DEFAULT_API_DESCRIPTORS_KEY,
    DEFAULT_SCOPES_KEY,
    DEFAULT_ACTIONS_KEY,
    utcnow
)
from ateme.um_backend.exceptions import (
    LocalUserInvalidCredentials,
    LdapUnavailableCache,
    LdapNoCacheEntry,
    InvalidUserException,
    CheckTokenError,
    CheckRemoteIPInvalid,
    RequestExtractError,
    IdpConfigNotFound,
    IntrospectionError,
)
from ateme.um_backend.request_utils import (
    HttpHeaders,
    extract_username_and_idpname,
    extract_token,
    extract_uri_and_method,
    extract_api_url,
    extract_user_ip,
    extract_user_agent_as_string,
    extract_activity_extra_data,
    show_headers
)
from ateme.um_backend.introspection import Introspector

SYNC_SCHEMA_FILE = "sync_schema/um_sync_data.json"
MIGRATION_FILE = "migration_files/um_migration.json"

def inject_internal_user_param(func):
    """

    Decorator to inject internal args on UserManagementApi handler
    """
    func_inspect = inspect.getfullargspec(func)
    if "internal" not in func_inspect.args:
        raise Exception(f"{func} function haven't 'internal' as argument, so it's impossible to inject this parameter")

    @functools.wraps(func)
    async def _inject_internal_user_param(self, *args: Any, **kwargs: Any):
        try:
            token = extract_token(args[0])
            token_db = await self.db.collection_tokens.get_by_access_token(token)
            user_info = await self.db.get_user_by_id(token_db.user_id, internal_projection=True)
            kwargs["internal"] = user_info.get("internal", False)
        except Exception as error:
            LOG.warning("Fail to extract user from token, got %s", error)
            raise HTTPUnauthorized(data="Fail to extract user from token") from error
        return await func(self, *args, **kwargs)
    return _inject_internal_user_param


class UserManagementApi(OpenApiWebApplication):
    """
    UserManagementApi class
    """
    # pylint: disable=too-many-arguments, too-many-instance-attributes, too-many-public-methods, too-many-positional-arguments

    def __init__(self,
                 database: Database,
                 settings: argparse.Namespace,
                 executor: ThreadPoolExecutor,
                 origin: str = 'origin',
                 service: str = 'user-ms',
                 configuration: Configuration = Configuration(),
                 validate_response: bool = False):
        """
        User Management API
        Args:
            database:
            settings:
            origin:
            service:
            configuration:
            validate_response:
        """
        self.settings = settings
        self.origin = origin
        self.service = service
        self._executor = executor
        self.loop = None

        # Default values to create at launch
        self.default_scopes: Optional[List[Scope]] = None
        self.default_actions: Optional[List[Action]] = None
        self.default_users: Optional[List[User]] = None
        self.default_admin: Optional[User] = None
        self.default_descriptor: Optional[ApiDescriptor] = None
        self.default_auth_data: Optional[AuthData] = None

        #  the user DB object
        self.db = database
        self.saml_idp = SamlProvider(db=self.db)
        self.ldap_idp = LdapProvider(db=self.db, executor=self._executor)
        self.local_idp = LocalProvider(db=self.db)
        aes_cipher = AESCipher()
        self.encrypt = aes_cipher.encrypt
        self.decrypt = aes_cipher.decrypt
        self.api_definition = OpenApiDefinition(os.path.join(os.path.dirname(__file__), 'api', 'api.yaml'))
        # if any login are done since TOKEN_CLEANING (s) the token is removed from db
        # by default this value is set to 1d = 24 * 3600s = 86400s
        self.token_cleaning = settings.token_cleaning
        self.init_configuration = configuration

        self.internal_admin_username = None
        self.internal_admin_password = None

        self.clean_token_task = None
        self.updater = UserUpdater(db=self.db, migration_file=MIGRATION_FILE)
        self.sync_updater = UserUpdater(db=self.db,
                                        migration_file=SYNC_SCHEMA_FILE)
        self.introspector = Introspector(self.db)

        # Background tasks: asyncio tasks of update ldap cache
        self.background_tasks: set[asyncio.Task] = set()
        self.sync_ldap_cache_task = None

        super().__init__(definition=self.api_definition,
                         implementation=self,
                         allow_not_implemented=True,
                         logger=LOG,
                         validate_response=validate_response)

    def handler_factory(
        self,
        route_instance: Path,
        method_instance: Method,
        implementation_method: Callable[[Request], Awaitable[Response]],
        operation_id: str
    ):
        """
        Overload `OpenApiWebApplication.handler_factory` to be able to wrap
        the `implementation_method` with a custom wrapper. This wrapper will
        manage the activity logs.

        Args:
            route_instance: current openapi `Path`
            method_instance: current openapi `Method`
            implementation_method: method to process the request
            operation_id: handler name associated to the endpoint.

        Returns:
            Return the custom wrapper.
        """

        @functools.wraps(implementation_method)
        async def implementation_wrapper(request: Request) -> Response:
            """ Custom wrapper to manage the activity logs.

            Args:
                request: request object

            Returns:
                Response: response object
            """
            show_headers(request)
            extra = extract_activity_extra_data(request)
            try:
                response = await implementation_method(request)
                show_activity_log(logging.INFO, response, extra)
                return response
            except HTTPException as error:
                show_activity_log(logging.ERROR, error, extra)
                raise

        return super().handler_factory(route_instance, method_instance, implementation_wrapper, operation_id)

    def __load_default_values(self):
        """
        Load default descriptor, actions, scopes and users provided if path are defined
        """
        # pylint: disable=too-many-branches, too-many-statements, too-many-locals

        # Load default auth_data from a list of file defined in settings.default_auth_data_path
        if self.settings.default_auth_data_path:
            merged_auth_data = {DEFAULT_ACTIONS_KEY: [], DEFAULT_API_DESCRIPTORS_KEY: [], DEFAULT_SCOPES_KEY: []}
            try:
                for file_path in self.settings.default_auth_data_path:
                    # Merge the content of the files and pass the result to load_default_auth_data method
                    with open(file_path, 'r', encoding='utf-8') as default_auth_data_file:
                        auth_data = json.load(default_auth_data_file)
                        if DEFAULT_ACTIONS_KEY in auth_data:
                            merged_auth_data[DEFAULT_ACTIONS_KEY].extend(auth_data[DEFAULT_ACTIONS_KEY])
                        if DEFAULT_SCOPES_KEY in auth_data:
                            merged_auth_data[DEFAULT_SCOPES_KEY].extend(auth_data[DEFAULT_SCOPES_KEY])
                        if DEFAULT_API_DESCRIPTORS_KEY in auth_data:
                            merged_auth_data[DEFAULT_API_DESCRIPTORS_KEY].extend(auth_data[DEFAULT_API_DESCRIPTORS_KEY])
                self.default_auth_data = self.load_default_auth_data(merged_auth_data)
                LOG.info('auth_data files %s were successfully loaded', self.settings.default_auth_data_path)
            except Exception:  # pylint: disable=broad-except
                LOG.exception('Failed to load api auth_data file: %s',
                              self.settings.default_auth_data_path)

        # Load default API descriptor from file defined in settings.default_descriptor_path
        if not self.default_auth_data and not self.default_descriptor and self.settings.default_descriptor_path:
            try:
                with open(self.settings.default_descriptor_path, 'r', encoding='utf-8') as default_descriptor_file:
                    default_descriptor = json.load(default_descriptor_file)
                api_descriptor = ApiDescriptor.from_dict(default_descriptor)
                if api_descriptor is None or not api_descriptor.validate():
                    raise Exception('invalid default api descriptor')
                self.default_descriptor = api_descriptor
                LOG.info('API descriptor file %s was successfully loaded', self.settings.default_descriptor_path)
            except Exception:  # pylint: disable=broad-except
                LOG.exception('Failed to load api descriptor file: %s', self.settings.default_descriptor_path)

        # Load default actions from file defined in settings.default_actions_path
        if (not self.default_auth_data and not self.default_descriptor and not self.default_actions
                and self.settings.default_actions_path):
            try:
                with open(self.settings.default_actions_path, 'r', encoding='utf-8') as default_actions_file:
                    default_actions = json.load(default_actions_file)
                self.default_actions = load_default_actions(default_actions)
                if len(default_actions) != len(self.default_actions):
                    raise Exception('invalid default actions')
                LOG.info('Default actions file %s was successfully loaded', self.settings.default_actions_path)
            except Exception:  # pylint: disable=broad-except
                LOG.exception("Failed to load actions file '%s'", self.settings.default_actions_path)

        # Load default scopes from file defined in settings.default_scopes_path
        if (not self.default_auth_data and not self.default_descriptor and not self.default_scopes
                and self.settings.default_scopes_path):
            try:
                with open(self.settings.default_scopes_path, 'r', encoding='utf-8') as default_scopes_file:
                    default_scopes = json.load(default_scopes_file)
                self.default_scopes = load_default_scopes(default_scopes)
                if len(default_scopes) != len(self.default_scopes):
                    raise Exception('invalid default scopes')
                LOG.info('Default scopes file %s was successfully loaded', self.settings.default_scopes_path)
            except Exception:  # pylint: disable=broad-except
                LOG.exception("Failed to load scopes file '%s'", self.settings.default_scopes_path)

        # Load default users from file defined in settings.default_users_path
        if not self.default_users and self.settings.default_users_paths:
            try:
                with open(self.settings.default_users_paths, 'r', encoding='utf-8') as default_users_file:
                    default_users = json.load(default_users_file)
                self.default_users = load_default_users(default_users, self.encrypt)
                if len(default_users) != len(self.default_users):
                    raise Exception('invalid default users')
                LOG.info('Default users file %s was successfully loaded', self.settings.default_users_paths)
            except Exception:  # pylint: disable=broad-except
                LOG.exception("Failed to load users file '%s'", self.settings.default_users_paths)

        # Load default admin credentials from file defined in settings.default_admin_path
        if not self.default_admin and self.settings.default_admin_path:
            try:
                with open(self.settings.default_admin_path, 'r', encoding='utf-8') as default_admin_file:
                    default_admin = json.load(default_admin_file)
                self.default_admin = load_default_admin(default_admin, self.encrypt)
                if not self.default_admin:
                    raise Exception('invalid default admin')
                LOG.info('Default admin file %s was successfully loaded', self.settings.default_admin_path)
            except Exception:  # pylint: disable=broad-except
                LOG.exception("Failed to load admin file '%s'", self.settings.default_admin_path)

    def load_default_auth_data(self, default_auth_data: dict) -> AuthData:
        """
        Load actions, scopes, api_descriptor from a default auth_data
        Args:
            default_auth_data:

        Returns:
            AuthData:

        """
        auth_data: AuthData = None
        if default_auth_data and not self.default_auth_data:
            auth_data_descriptors: List[AuthDataDescriptor] = []
            auth_data_actions: List[Action] = []
            auth_data_scopes: List[Scope] = []

            descriptors = default_auth_data.get(DEFAULT_API_DESCRIPTORS_KEY)
            for descriptor in descriptors:
                app_name = descriptor.get("app_name", "")
                auth_data_descriptor = AuthDataDescriptor(descriptor["prefix"], descriptor["url"], app_name)
                auth_data_descriptors.append(auth_data_descriptor)
            LOG.info('%d default auth data descriptors were successfully loaded from %s',
                     len(auth_data_descriptors), self.settings.default_auth_data_path)

            actions = default_auth_data.get(DEFAULT_ACTIONS_KEY)
            if actions:
                auth_data_actions = load_default_actions(actions)
                if len(auth_data_actions) != len(actions):
                    raise Exception('invalid default auth data actions')
                LOG.info('%d auth data actions were successfully loaded from %s',
                         len(auth_data_actions), self.settings.default_auth_data_path)

            scopes = default_auth_data.get(DEFAULT_SCOPES_KEY)
            if scopes:
                auth_data_scopes = load_default_scopes(scopes)
                if len(auth_data_scopes) != len(scopes):
                    raise Exception('invalid default auth data scopes')
                LOG.info('%d default auth data scopes were successfully loaded from %s',
                         len(auth_data_scopes), self.settings.default_auth_data_path)
            if auth_data_actions and auth_data_scopes and auth_data_descriptors:
                # Build auth data from the descriptors, actions and scopes
                auth_data = AuthData(auth_data_descriptors, auth_data_actions, auth_data_scopes)
                LOG.debug("default auth data loaded with %d descriptors, %d actions and %d scopes",
                          len(auth_data_descriptors), len(auth_data_actions), len(auth_data_scopes))

        return auth_data

    async def initialize(self):  # pylint: disable=too-many-branches,too-many-statements
        """ Initialize user management api """
        self.loop = asyncio.get_running_loop()
        await self.db.initialize()
        await self.local_idp.initialize()

        # Load default values
        self.__load_default_values()

        # Insert User Management default actions/scopes
        um_default_scopes, um_default_actions = generate_scopes_and_actions(api_definition=self.api_definition)
        await self.db.collection_actions.replace_many(um_default_actions, self.api_definition.auth.prefix)
        await self.db.collection_scopes.replace_many(um_default_scopes, self.api_definition.auth.prefix)

        # insert application default auth_data, api descriptor, actions, scopes
        if self.default_auth_data:
            await self.db.publish_auth_data(self.default_auth_data)
        elif self.default_descriptor:
            await self.db.publish_api_descriptor(self.default_descriptor)
        else:
            if self.default_actions:
                await self.db.collection_actions.replace_defaults(self.default_actions)
            if self.default_scopes:
                await self.db.collection_scopes.replace_defaults(self.default_scopes)

        # insert application default users
        if self.default_users:
            await self.db.update_default_users(self.default_users)

        # insert default admin
        if self.default_admin:
            if not await self.db.get_admin_user():
                await self.db.create_user(self.default_admin, Collections.admin.name)
            else:
                LOG.warning("An admin already exists. Could not store the default one.")

        await self.create_internal_admin_user()

        configuration = await self.db.insert_configuration(self.init_configuration)
        LOG.debug("Init configuration %s", configuration.to_dict())

        # Start the clean expired tokens task
        self.reset_cleaning_task()

        # Create ldap_cache task
        self.sync_ldap_cache_task = asyncio.create_task(self._sync_ldap_cache())
        self.background_tasks.add(self.sync_ldap_cache_task)  # add task to the set, so it is not garbage collected

    async def finalize(self):
        """ Finalize callback """
        self.clean_token_task.cancel()
        if self.background_tasks:
            for task in self.background_tasks:
                task.cancel()

    async def _upsert_ldap_cache_data(self, ldap_config: LdapConfig):
        """
        Insert or Update the data in 'ldap_cache' collection
        for a specific ldap configuration
        In this operation, we perform ldap bind and ldap search
        using the data from ldap search, we then upsert the data

        Args:
            ldap_config (LdapConfig): The ldap configuration
        Raises:
            IdpConfigNotFound: Can't find idp config
        """
        LOG.debug("Retrieve ldap config of %s", ldap_config.idp_name)
        ldap_config = await self.db.get_idp_config_by_name(ldap_config.idp_name)
        if not ldap_config:
            raise IdpConfigNotFound("Can't find ldap config")
        # Remove LDAP cache
        cache_res = await self.db.remove_ldap_cache_by_idp_name(ldap_config.idp_name)
        LOG.info("Remove ldap cache for idp %s: %d document removed", ldap_config.idp_name, cache_res.deleted_count)

        # Perform the ldap search and stock the data
        ldap_client = LdapClient(ldap_config=ldap_config)
        LOG.debug("Bind with bind_dn '%s' on idp '%s'", ldap_config.bind_dn, ldap_config.idp_name)
        connection = await self.loop.run_in_executor(
            self._executor,
            ldap_client.bind,
            ldap_config.bind_dn,
            self.decrypt(ldap_config.bind_password) if ldap_config.bind_password else None,
            True
        )
        LOG.info("Search request with user_filter '%s' from base_dn '%s' on idp '%s'",
                 ldap_config.user_filter,
                 ldap_config.search,
                 ldap_config.idp_name
        )
        search_response = await self.loop.run_in_executor(
            self._executor,
            ldap_client.search,
            connection,
            [ldap_config.user_filter],
            ldap_config.search,
            ldap_config.search_filter
        )
        LOG.info("search_response for idp %s: %d entries", ldap_config.idp_name, len(search_response))

        # Prepare the data
        data_to_insert = {}
        entries = []
        data_to_insert['idp_name'] = ldap_config.idp_name

        for entry in search_response:
            entry_dict = entry.attributes
            entry_dict['dn'] = entry.dn
            entries.append(entry_dict)

        data_to_insert['entries'] = entries
        data_to_insert['last_sync_date'] = utcnow().timestamp()

        # Insert or update data if present
        _upserted_result = await self.db.upsert_ldap_cache_by_idp_name(idp_name=ldap_config.idp_name, entries=entries)
        LOG.info(
            "Update ldap cache for idp %s modified_count: %d upserted_id: %s",
            ldap_config.idp_name,
            _upserted_result.modified_count,
            _upserted_result.upserted_id,
        )

    async def _sync_ldap_cache(self):
        """
        Task that will constantly synchronize the 'ldap_cache'
        db collection for each ldap configuration
        """
        async def safe_upsert_ldap_cache_data(ldap_config: LdapConfig):
            try:
                await self._upsert_ldap_cache_data(ldap_config=ldap_config)
                LOG.info("Successfully updated LDAP cache for config %s", ldap_config.idp_name)
            except asyncio.CancelledError as cancel_error:
                # Catch `asyncio.CancelledError` to avoid being treated like an unexpected exception.
                # Re-raise it.
                raise cancel_error
            except Exception as e:
                LOG.warning("Exception when updating LDAP cache for config %s: %s", ldap_config.idp_name, e)

        while True:
            try:
                # Retrieve all ldap idp configurations and for each configuration, run a task to update the cache
                ldap_configs = await self.db.get_idp_configs_by_type(idp_type=IdpType.ldap.name, bind_dn_field=True)
                await asyncio.gather(*[safe_upsert_ldap_cache_data(ldap_config=config) for config in ldap_configs])
                # Sleep here
                await asyncio.sleep(self.settings.ldap_sync_period)
            except asyncio.CancelledError:
                LOG.info("_sync_ldap_cache is cancelled")
                return
            except Exception as exception:
                LOG.warning("Exception occurred while syncing ldap cache %s", exception)
                # Sleep here too
                await asyncio.sleep(self.settings.ldap_sync_period)

    def _run_task_in_background(self, task: Coroutine):
        """
        Run an operation as a background task and add it to the list.

        Args:
            task (Coroutine): Coroutine to be executed
        """
        background_task = asyncio.create_task(task)  # create and run the task
        self.background_tasks.add(background_task)  # add task to the set, so it is not garbage collected
        background_task.add_done_callback(self.background_tasks.discard)  # discard from the set, once finished

    def reset_cleaning_task(self):
        """
        Method used to run the cleaning task
        """
        if self.clean_token_task:
            # Cancel the task if it already exists
            self.clean_token_task.cancel()

        self.clean_token_task = asyncio.create_task(self._cleaning_task())

    async def _cleaning_task(self):
        """
        Launch an infinite loop to check if the tokens in db are expired
        Raises:
            cancel_error: occurs when posted a new configuration to restart the coroutine.
        """
        try:
            # Retrieve the cleaning conf
            configuration = await self.db.get_configuration()

            LOG.info("Start cleaning task")

            while True:
                try:
                    await self.db.collection_tokens.clean_expired_refresh_token()
                except asyncio.CancelledError as cancel_error:
                    # Catch `asyncio.CancelledError` to avoid being treated like an unexpected exception.
                    # Re-raise it to kill the coroutine when occurs.
                    raise cancel_error
                except Exception as exception:
                    # An unexpected exception occurs, catch it to avoid killing the coroutine.
                    # Log the error and print the traceback if `logger` has a `DEBUG` level.
                    if LOG.getEffectiveLevel() in [logging.DEBUG]:
                        LOG.exception("An unexpected exception occurs: %s", exception)
                    else:
                        LOG.warning("An unexpected exception occurs: %s", exception)
                finally:
                    await asyncio.sleep(configuration.token_cleaning_period.total_seconds())

        except asyncio.CancelledError:
            # This exception is deadly, catch it to die with honors.
            LOG.warning("Exit cleaning task")
        except Exception:
            # We SHOULD never pass here !
            LOG.exception("Unexpected exit cleaning task")

    def generate_internal_admin_credentials(self):
        """
        Generate internal_admin credentials from the username
        :return:
        """
        self.internal_admin_username = "internal_admin"
        # encrypt password based on username
        self.internal_admin_password = b64decode(self.encrypt(self.internal_admin_username).decode('utf-8'))
        self.internal_admin_password = binascii.hexlify(self.internal_admin_password).decode("utf-8")

    async def create_internal_admin_user(self):
        """

        Create an internal admin user with usr:internal_administrator scope
        :return:
        """
        self.generate_internal_admin_credentials()
        # Internal admin is by definition a local user
        idp_name = DEFAULT_LOCAL_IDP_NAME
        # Salt the password before encryption
        # creation_id is used to salt the password
        # it replaced _id in previous versions
        creation_id = ObjectId()
        salted_password = User.generate_salted_encrypted_password(password=self.internal_admin_password,
                                                                  creation_id=creation_id.binary,
                                                                  encrypt=self.encrypt)
        user_object = User(creation_id=creation_id,
                           username=self.internal_admin_username,
                           password=str(salted_password),
                           enabled=True,
                           scopes=["usr:internal_administrator", "usr:internal"],
                           level=self.settings.default_level,
                           internal=True,
                           idp_name=idp_name)
        try:
            await self.db.create_user(user_object, Collections.admin.name)
        except Exception as exception:
            LOG.error("Exception when creating an internal_admin %s", exception)

    async def get_ping(self, _) -> Response:
        """

        Get ping, check if api is up
        Returns:
            Response: 200 OK
        """
        return Response(200, "OK", {"content-type": "text/plain"})

    async def get_readiness(self, _) -> Response:
        """

        Get the readiness of the service based on the availability of the database
        Returns:
            Response: 200 OK
        """
        database_status = await self.db.is_database_available()
        if not database_status:
            raise HTTPServiceUnavailable(data="Database not available")
        return Response(200, "OK", {"content-type": "text/plain"})

    # *** ADMIN methods implementation ****
    async def get_admin(self, _) -> Response:
        """

        Get admin username
        :param request:
        :return:
        """
        admin = await self.db.get_admin_user()
        if admin:
            # Users just want to see admin name, no sensitive data
            admin = {'username': admin['username']}
            return Response(200, admin, {"content-type": "application/json"})
        raise HTTPNotFound(data='No user admin exists')

    async def create_admin_user(self, request: Request) -> Response:
        """
        Create admin user (allow one user as admin)

        :param request:
        :return:
        """
        username = request.body.get('username')
        password = request.body.get('password')
        # Admin is by definition a local user
        idp_name = DEFAULT_LOCAL_IDP_NAME

        level = request.body.get('level', self.settings.default_level)
        # do not create a admin with same user name as internal_admin
        if username == self.internal_admin_username:
            return Response(403, "This admin username is reserved", {
                "content-type": "text/plain"})
        if await self.db.get_admin_user() is not None:
            return Response(403, "An admin user is already created, only one admin is allowed...", {
                "content-type": "text/plain"})

        # Check password constraint for admin
        configuration = await self.db.get_configuration()
        if not configuration.password_policy.validate_password_constraints(password):
            raise HTTPBadRequest(data="the password doesn't match the constraints")

        # Salt the password before encryption
        # creation_id is used to salt the password
        # it replaced '_id' in previous versions
        creation_id = ObjectId()
        salted_password = User.generate_salted_encrypted_password(password=password,
                                                                  creation_id=creation_id.binary,
                                                                  encrypt=self.encrypt)
        user_object = User(creation_id=creation_id,
                           username=username,
                           password=str(salted_password),
                           enabled=True,
                           password_last_update=utcnow().timestamp(),
                           level=level,
                           scopes=["all:administrator"],
                           internal=False,
                           idp_name=idp_name)
        await self.db.create_user(user_object, Collections.admin.name)
        return Response(201, "OK", {"content-type": "text/plain"})

    @log_activity("updated configuration", "failed to update configuration")
    async def update_configuration(self, request: Request) -> Response:
        """
        Update the configuration in db

        :param request:
        :return: Response
        """
        data = request.body

        # Check token_expiration is strictly lower to refresh_token_expiration before updating in DB
        token_expiration = data.get('token_expiration', None)
        refresh_token_expiration = data.get('refresh_token_expiration', None)

        # get the value of force all users to change their password
        force_change_password = request.parameters.get('force_change_password')

        if token_expiration is not None and \
           refresh_token_expiration is not None and \
           token_expiration >= refresh_token_expiration:
            LOG.error('token_expiration (%s) is greater or equal then refresh_token_expiration (%s)',
                      token_expiration, refresh_token_expiration)
            raise HTTPBadRequest(data="token_expiration must be strictly lower to refresh_token_expiration")

        await self.db.update_configuration(
            max_successive_failed_login=data.get('max_successive_failed_login', None),
            user_deactivation_period=data.get('user_deactivation_period', None),
            token_expiration=data.get('token_expiration', None),
            refresh_token_expiration=data.get('refresh_token_expiration', None),
            token_cleaning_period=data.get('token_cleaning_period', None),
            logout_timeout=data.get('logout_timeout', None),
            expiration_delay_in_days=data.get("password_policy", {}).get("expiration_delay_in_days"),
            password_min_length=data.get("password_policy", {}).get("password_min_length")
        )
        # Force all local users to change their passwords
        if force_change_password:
            result = await self.db.force_password_expiration_for_local_users()
            if result.modified_count > 0:
                LOG.debug("%d user's passwords have been forced to expire.",
                          result.modified_count)
        # Reset the cleaning task
        self.reset_cleaning_task()
        return Response(200, "OK", {"content-type": "text/plain"})

    async def get_configuration(self, _: Request) -> Response:
        """

        Get the configuration
        :param request:
        :return: Response
        """
        conf = await self.db.get_configuration()
        return Response(200, conf.to_dict(), {"content-type": "application/json"})

    async def get_public_configuration(self, _: Request) -> Response:
        """

        Get the public configuration
        :param request:
        :return: Response
        """
        conf = await self.db.get_configuration()
        public_conf = PublicConfiguration.create(conf)
        return Response(200, public_conf.to_dict(), {"content-type": "application/json"})

    # *** USERS methods implementation ****
    async def _add_user(self, user: dict, internal: bool):
        """
        Add a user in database
        Args:
            user: the user to create
            internal: whether the user to create is internal

        Raises:
            InvalidUserException: if the user is invalid
        """
        # pylint: disable=too-many-locals
        username = user.get('username')
        password = user.get('password', "")
        idp_name = user.get('idp_name', DEFAULT_LOCAL_IDP_NAME)
        session_timeout_disabled = user.get('session_timeout_disabled', False)
        password_expiration_disabled = user.get('password_expiration_disabled', False)

        if await self.db.is_admin(username=username):
            raise InvalidUserException(f"{username} is the administrator's name, please choose another one!")

        if internal:
            first_login = False
            if idp_name != DEFAULT_LOCAL_IDP_NAME:
                # Internal user is by definition a local user
                raise InvalidUserException("impossible to create an internal user with an idp_name")
        else:
            first_login = True
            if idp_name == DEFAULT_LOCAL_IDP_NAME and not password:
                raise InvalidUserException("a password is required for local users")

        if password:
            # Check the password
            configuration = await self.db.get_configuration()
            if not configuration.password_policy.validate_password_constraints(password):
                raise InvalidUserException("the password doesn't match the constraints")

        scopes = {"usr:internal"} if internal else set()
        user_scopes = user.get('scopes')
        if user_scopes:
            for scope in user_scopes:
                if await self.db.collection_scopes.get_by_id(_id=scope, internal=internal):
                    scopes.add(scope)
        # If the user has no scope with prefix all or usr, add the usr:guest scope
        # in order for him to be able to authenticate to basic path like logout
        if not any(prefix in scope for scope in scopes for prefix in ["all", "usr"]):
            scopes.add("usr:guest")
        # Salt the password before encryption
        # creation_id is used to salt the password
        # it replaced '_id' in previous versions
        creation_id = ObjectId()
        salted_password = User.generate_salted_encrypted_password(password=password,
                                                                  creation_id=creation_id.binary,
                                                                  encrypt=self.encrypt)
        user_object = User(creation_id=creation_id,
                           username=username,
                           password=salted_password,
                           enabled=True,
                           password_last_update=utcnow().timestamp(),
                           scopes=scopes,
                           level=user.get('level', self.settings.default_level),
                           first_login=first_login,
                           idp_name=idp_name,
                           internal=internal,
                           session_timeout_disabled=session_timeout_disabled,
                           password_expiration_disabled=password_expiration_disabled)
        await self.db.create_user(user_object, Collections.users.name)

    @log_activity("added user %(username)s:%(idp_name)s with disable session timeout set to %(session_timeout)s",
                  "failed to add user %(username)s:%(idp_name)s",
                  context_func=lambda req: {"username": req.body.get("username"),
                                            "idp_name": req.body.get("idp_name", IdpType.local.name),
                                            "session_timeout": req.body.get("session_timeout_disabled", False)})
    @inject_internal_user_param
    async def add_user(self, request: Request, internal: bool = False) -> Response:
        """ Create user (only admin is allowed to create new internal or non-internal users) """
        try:
            await self._add_user(request.body, internal)
        except UserAlreadyExist as e:
            raise HTTPConflict(data=str(e)) from e
        except InvalidUserException as e:
            raise HTTPBadRequest(data=str(e)) from e
        return Response(201, "OK", {"content-type": "text/plain"})

    @inject_internal_user_param
    async def add_users(self, request: Request, internal: bool = False) -> Response:
        """ Create users (only admin is allowed to create new internal or non-internal users) """
        errors = []
        for user in request.body:
            try:
                await self._add_user(user, internal)
            except (UserAlreadyExist, InvalidUserException) as e:
                errors.append(f"Unable to create user '{user.get('username', '')}': {str(e)}")
        return Response(201, {"errors": errors} if errors else {}, {"content-type": "application/json"})

    @inject_internal_user_param
    async def delete_users(self, request: Request, internal: bool = False) -> Response:
        """

        Delete list of users internal xor non internal
        :param request:
        :param internal:
        :return:
        """
        LOG.warning("The endpoint /users is deprecated. Please use the endpoint /users/{idp_name}/{username} instead.")
        message = "OK"
        code = 200

        for user in request.body:
            # User to delete is specified either by an object {username, idp_name}
            # or by its username (api < v5.0) (assuming that idp_name is 'local')
            if isinstance(user, dict):
                idp_name = user.get('idp_name', DEFAULT_LOCAL_IDP_NAME)
                username = user['username']
            else:
                idp_name = DEFAULT_LOCAL_IDP_NAME
                username = user
            user = await self.db.get_user_by_name(username=username, internal=internal, idp_name=idp_name)
            if user:
                # user with username and internal exists
                user_id = user.get('user_id')
                result = await self.db.delete_user_by_name(username=username,
                                                           internal=internal,
                                                           idp_name=idp_name)
                if result and result.acknowledged:
                    await self.db.collection_tokens.remove_by_user_id(user_id=user_id)
                else:
                    message = "You are trying to delete a user with administrator scope, which is not allowed !"
                    code = 409
            else:
                message = "You are trying to delete a user that doesn't exist !"
                code = 409
        return Response(code, message, {"content-type": "text/plain"})

    @inject_internal_user_param
    async def get_users(self, request: Request, internal: bool = False) -> Response:  # pylint: disable=unused-argument
        """

        Get users username for internal users xor for non internal users
        :param request:
        :return:
        """
        users = await self.db.get_all_users(internal=internal)
        return Response(200, users, {"content-type": "application/json"})

    async def get_user_by_name(self, request: Request) -> Response:  # pylint: disable=unused-argument
        """

        Get non internal users username
        :param request:
        :return:
        """
        username = request.parameters.get('username')
        idp_name = request.parameters.get('idp_name')
        user = await self.db.get_user_by_name(username=username, _id=False,
                                              internal=False, internal_projection=False,
                                              idp_name=idp_name)
        if not user:
            raise HTTPNotFound()
        return Response(200, user, {"content-type": "application/json"})

    async def deprecated_update_users(self, request: Request) -> Response:
        # pylint: disable=too-many-locals,too-many-branches
        """

        Update non internal users
        :param request:
        :return:
        """
        raise HTTPGone(data="this endpoint is deprecated")

    async def reactivate_user_by_name(self, request: Request) -> Response:
        """

        Enable or disable user
        :param request:
        :return:
        """
        username = request.parameters.get('username')
        idp_name = request.parameters.get('idp_name')

        await self.db.collection_clients.delete_many(username=username, idp_name=idp_name)
        user_db = await self.db.set_user_enabled(username=username, idp_name=idp_name)
        if not user_db:
            raise HTTPNotFound(data="User not found")
        return Response(200, "OK", {"content-type": "text/plain"})

    @log_activity("%(success_message)s",
                  "%(failure_message)s",
                  context_func=generate_audit_log_for_user_update)
    async def update_user_by_name(self, request: Request) -> Response:
        """
        Update non internal user by name

        Args:
            request (Request): Request body
        """
        username = request.parameters.get('username')
        idp_name = request.parameters.get('idp_name')
        user: dict = request.body

        user_db = await self.db.get_user_by_name(username=username, internal=False, internal_projection=True,
                                                 idp_name=idp_name)
        if not user_db:
            raise HTTPNotFound(data="Incorrect username, user not found")
        # if the scopes are not patched, reuse scopes in db
        if user.get("scopes") is None:
            if user_db.get("scopes"):
                user["scopes"] = user_db.get("scopes")
            else:
                user["scopes"] = set()
        user["scopes"] = set(user["scopes"])
        # If the user has no scope with prefix all or usr, add the usr:guest scope
        # in order for him to be able to authenticate to basic path like logout
        if not any(prefix in scope for scope in user.get("scopes", []) for prefix in ["all", "usr"]):
            user["scopes"].add("usr:guest")

        return await self.update_user(request, username=username, user=user, user_db=user_db, idp_name=idp_name)

    async def update_user_preferences(self, request: Request) -> Response:
        """
        Update user preferences

        Args:
            request (Request): Request instance

        Returns:
            Response: Response instance
        """
        user = await self._find_user_by_headers(request)
        await self.db.update_user_by_name(username=user['username'],
                                          idp_name=user['idp_name'],
                                          preferences=request.body)
        return Response(200, 'OK', {'content-type': 'text/plain'})

    # pylint: disable=unused-argument, too-many-positional-arguments
    async def update_user(self, headers: Request, username: str, user: dict, user_db: dict, idp_name: str) -> Response:
        """
        Update non internal user by name

        :param headers: Only used for the decorator is_admin
        :param username:
        :param user:
        :param user_db:
        :param idp_name:
        :return:
        """
        # pylint: disable=too-many-locals, too-many-statements
        password_last_update = None
        if user.get("password"):
            # Check the password
            configuration = await self.db.get_configuration()
            if not configuration.password_policy.validate_password_constraints(user.get("password")):
                raise HTTPBadRequest(data="The password doesn't match the constraints")
            password = User.generate_salted_encrypted_password(password=user.get("password"),
                                                               creation_id=user_db["creation_id"].binary,
                                                               encrypt=self.encrypt)
            password_last_update = utcnow().timestamp()
        else:
            password = user_db.get("password")
        # Delete every client corresponding to this username
        await self.db.collection_clients.delete_many(username=username, idp_name=idp_name)
        # if the scopes are not updated, reuse scopes in db
        if user.get("scopes") is None:
            if user_db.get("scopes"):
                user["scopes"] = user_db.get("scopes")
            else:
                user["scopes"] = set()
        user["scopes"] = set(user["scopes"])
        # If the user has no scope with prefix all or usr, add the usr:guest scope
        # in order for him to be able to authenticate to basic path like logout
        if not any(prefix in scope for scope in user.get("scopes", []) for prefix in ["all", "usr"]):
            user["scopes"].add("usr:guest")
        # If the first_login (aka force change password) boolean is set to True
        # we want to force user disconnection
        if (user.get('first_login') and not user_db.get('first_login')
                or user.get('session_timeout_disabled', False) != user_db.get('session_timeout_disabled', False)):
            await self.db.collection_tokens.remove_by_user_id(user_id=user_db['user_id'])
        await self.db.update_user_by_name(username=username, scopes=user.get('scopes'), password=password,
                                          level=user.get("level"), enabled=user.get("enabled"),
                                          password_last_update=password_last_update,
                                          internal=False,
                                          idp_name=idp_name,
                                          first_login=user.get("first_login"),
                                          session_timeout_disabled=user.get("session_timeout_disabled", False),
                                          password_expiration_disabled=user.get("password_expiration_disabled", False))
        return Response(200, 'OK', {'content-type': 'text/plain'})

    @log_activity("removed user %(username)s:%(idp_name)s",
                  "failed to remove user %(username)s:%(idp_name)s",
                  context_func=lambda req: {"username": req.parameters.get('username'),
                                            "idp_name": req.parameters.get('idp_name', IdpType.local.name)})
    async def remove_user_by_name(self, request: Request) -> Response:
        """
        Remove non internal user by username
        :param request:
        :return:
        """
        username = request.parameters.get('username')
        idp_name = request.parameters.get('idp_name')

        result = await self.db.delete_user_by_name(username=username,
                                                   internal=False,
                                                   idp_name=idp_name)
        if not result:
            raise HTTPBadRequest(data="You are trying to delete a user with administrator scope,"
                                      "which is not allowed!")
        if not result.acknowledged:
            raise HTTPInternalServerError(data=f"Delete user {username} failed")
        if not result.deleted_count:
            raise HTTPNotFound(data=f"Delete user {username} failed")
        return Response(200, f"User {username} deleted", {"content-type": "text/plain"})

    # *** LOGIN/OUT methods implementation ****
    @log_activity("%(username)s:%(idp_name)s logged in",
                  "%(username)s:%(idp_name)s with IP %(remote)s failed to login",
                  context_func=lambda req: {"username": req.body.get('username'),
                                            "remote": extract_user_ip(req),
                                            "idp_name": req.body.get('idp_name', DEFAULT_LOCAL_IDP_NAME)})
    async def login(self, request: Request) -> Response:
        # pylint: disable=too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
        """

        Login handler
        :param request:
        :return:
        """
        username = request.body.get('username')
        password = request.body.get('password')
        idp_name = request.body.get('idp_name', DEFAULT_LOCAL_IDP_NAME)
        configuration = await self.db.get_configuration()
        LOG.debug("Current configuration: %s", configuration)

        # Get the user's IP address
        remote = extract_user_ip(request)

        # We override openapi validation, in order to raise generic message
        if not username or not password:
            raise HTTPBadRequest(data="Bad credentials")

        if configuration.user_deactivation_period != -1:
            # Delete every disabled clients that expired
            await self.db.collection_clients.delete_many(
                user_deactivation_period=configuration.user_deactivation_period
            )
            # Check the maximum number of failed client logins has been reached
            login_attempts_number = await self.db.collection_clients.get_login_attempts_number()
            if login_attempts_number >= self.settings.max_number_failed_client_logins:
                raise HTTPServiceUnavailable(data="The number of maximum failed logins has been reached")
            # Get client, it exists in db only if a login failed with this IP
            client = await self.db.collection_clients.get(
                remote=remote,
                username=username,
                idp_name=idp_name
            )
            if client:
                LOG.debug("User client exists: %s", client.to_dict())
                # check client enabling
                if not client.enabled:
                    delta = int(
                        configuration.user_deactivation_period - (utcnow().timestamp()-client.last_attempt_date)
                    )
                    raise HTTPForbidden(data=f"Client disabled for {delta} seconds after too many attempts")

        try:
            # Retrieve the user in database
            # (both internal and non internal user use this route)
            user = await self.db.get_user_by_name(
                username=username,
                all_users=True,
                internal_projection=True,
                idp_name=idp_name
            )
            if idp_name == DEFAULT_LOCAL_IDP_NAME:
                # Local user must be present in database
                if user:
                    salting_key = user["creation_id"] if "creation_id" in user else user["_id"]
                    salted_password = User.generate_salted_encrypted_password(
                        password=password, creation_id=salting_key.binary, encrypt=self.encrypt
                    )
                    # Check password
                    user = await self.db.get_user_by_generated_id(
                        username=username,
                        password=salted_password,
                        idp_name=idp_name,
                        internal_projection=True
                    )

                if not user:
                    raise LocalUserInvalidCredentials()
            else:
                idp_config = await self.db.get_idp_config_by_name(idp_name=idp_name)
                if not idp_config:
                    raise HTTPInternalServerError(
                        data=f"Can't find an identity provider configured with this name {idp_name}"
                    )
                if idp_config.idp_type != IdpType.ldap.name:
                    raise HTTPInternalServerError(
                        data=f"Idp {idp_name} cannot be used to login, invalid type {idp_config.idp_type}"
                    )
                if idp_config.deny_access and not idp_config.mappers:
                    # Deny access
                    raise HTTPForbidden(data="Access denied")
                # Ldap user can be automatically created if not exists
                user = await self._handle_ldap_authentication(idp_config, username, password, user)
        except HTTPException:
            raise
        except (ldap.INVALID_CREDENTIALS, LocalUserInvalidCredentials) as error: # pylint: disable=no-member
            # Update clients
            client = await self.db.collection_clients.update(
                remote=remote,
                username=username,
                idp_name=idp_name,
                max_successive_failed_login=configuration.max_successive_failed_login,
                user_deactivation_period=configuration.user_deactivation_period
            )
            LOG.debug("User client updated: %s", client.to_dict())
            raise HTTPUnauthorized(data='Invalid username or password') from error
        except Exception as exception:
            raise HTTPInternalServerError(
                data=f"Identity provider exception with user `{username}` on `{idp_name}`: {exception}"
            ) from exception

        # Check user enabling
        if not user['enabled']:
            raise HTTPForbidden(data="User disabled")

        internal = user.get("internal", False)

        # Generate token and expiration date
        token = Token.generate(
            user_id=user["user_id"],
            token_expiration=configuration.token_expiration,
            refresh_token_expiration=configuration.refresh_token_expiration,
            session_timeout_disabled=user.get("session_timeout_disabled", False),
            user_ip=remote
        )
        response_data = {
            "access_token": token.token,
            "refresh_token": token.refresh_token,
            "expires_in": int(configuration.token_expiration.total_seconds()),
            "token_type": 'bearer'
        }
        async with self.db.client.start_session() as session:
            async with await session.start_transaction():

                # Store token and update user
                await self.db.collection_tokens.store(token, session=session)

                # Check password expiration:
                # Only for local non-internal user with disable_password_expiration set to False
                # except if this feature is globally disabled
                if (idp_name == DEFAULT_LOCAL_IDP_NAME
                    and ("password_expiration_disabled" not in user or not user["password_expiration_disabled"])
                    and not internal):

                    # If the user is already with password expired flag set to True, then we return 206
                    # This behavior can come from two things:
                    # Either the password expiration was forced via the Configuration
                    if 'password_expired' in user and user["password_expired"]:
                        # FrontEnd wait for a 206 to redirect user to password page
                        response_data["reason"] = "Password expired"
                        return Response(206, response_data, {"content-type": "application/json"})

                    # Or, the expiration of the password happened
                    if configuration.password_policy.expiration_delay_in_days != -1:
                        delta = utcnow().timestamp() - user['password_last_update']
                        if delta > configuration.password_policy.expiration_delay_in_days * \
                            timedelta(days=1).total_seconds():
                            await self.db.update_user_by_name(
                                username,
                                idp_name,
                                password_expired=True,
                                session=session,
                                session_timeout_disabled=user.get("session_timeout_disabled")
                            )
                            # FrontEnd wait for a 206 to redirect user to password page
                            response_data["reason"] = "Password expired"
                            return Response(206, response_data, {"content-type": "application/json"})

                # Update user
                await self.db.update_user_by_name(
                    username=username,
                    enabled=True,
                    internal=internal,
                    idp_name=idp_name,
                    session=session,
                    session_timeout_disabled=user.get("session_timeout_disabled")
                )
                # Login ok, we can delete the client from database if it exists
                await self.db.collection_clients.delete_many(
                    remote=remote,
                    username=username,
                    idp_name=idp_name,
                    session=session
                )

        if user.get("first_login"):
            # FrontEnd wait for a 206 to redirect user to password page
            response_data["reason"] = "First login"
            return Response(206, response_data, {"content-type": "application/json"})

        return Response(200, response_data, {"content-type": "application/json"})

    async def _retrieve_user_dn_manually(self, idp_config: LdapConfig, username: str) -> str | None:
        """
        Method that will perform an ldap search operation and look up for the username
        in the active directory
        Args:
            idp_config (LdapConfig): Ldap Config
            username (str): User name to look for
        Returns:
            str: the user bind dn from the search response
        """

        # Create the client
        ldap_client = LdapClient(ldap_config=idp_config)
        connection = await self.loop.run_in_executor(
            self._executor,
            ldap_client.bind,
            idp_config.bind_dn,
            self.decrypt(idp_config.bind_password)
        )

        # This is to avoid possible injection of malicious code
        search_filter = build_user_search_filter(
            user_filter=idp_config.user_filter,
            username=username
            )

        LOG.debug(
            "Retrieving user DN for username=%s using filter attribute=%s on idp=%s",
            username,
            idp_config.user_filter,
            idp_config.idp_name,
        )

        search_response = await self.loop.run_in_executor(
            self._executor,
            ldap_client.search,
            connection,
            None, # We dont need a specific attributes to look for, we only need the entry user dn
            idp_config.search,
            search_filter
        )

        if not search_response:
            return None

        # Normally we look only for one person, the search result should be only one and we return
        # the first entry user dn
        return search_response[0].dn

    async def _retrieve_user_dn_from_ldap_cache(self, idp_config: LdapConfig, username: str) -> str:
        """
        Method used to check if the username exists in ldap cache collection
        and retrieve the bind dn
        Args:
            idp_config (LdapConfig): Ldap Config
            username (str): User name

        Returns:
            str: the user bind dn from the cache
        """
        ldap_cache = await self.db.get_ldap_cache_by_idp_name(idp_name=idp_config.idp_name)
        if not ldap_cache:  # Check if there is cache for this idp name
            raise LdapUnavailableCache(f"The cache for {idp_config.idp_name} is unavailable")

        # Find the user and take the dn for login
        user = await self.db.find_user_in_ldap_cache(
            username=username,
            user_filter=idp_config.user_filter,
            idp_name=idp_config.idp_name
        )
        if not user:
            raise LdapNoCacheEntry(f"The user {username} cannot be found in the cache {idp_config.idp_name} "
                                   f"using {idp_config.user_filter} as user filter")

        LOG.debug("User data retrieved from cache: %s on idp %s", user, idp_config.idp_name)
        return user['entries']['dn']

    async def _retrieve_scopes(self, idp_config: LdapConfig, username: str, password: str) -> Tuple[list, bool]:
        """
        Method used to retrieve ldap scopes

        Args:
            idp_config (LdapConfig): Ldap Config
            username (str): User name
            password (str): User password

        Returns:
            tuple: scopes, idp_bound
        """
        scopes = idp_config.scopes
        idp_bound = False
        if idp_config.mappers:
            # Retrieve scopes thanks to given mappers
            if idp_config.bind_password:
                idp_config.bind_password = self.decrypt(idp_config.bind_password)
            try:
                scopes = await self.ldap_idp.retrieve_scopes(idp_config, username, password, loop=self.loop)
                LOG.debug("Scopes %s have been retrieve from roles mapping on idp %s", scopes, idp_config.idp_name)
                if not idp_config.bind_password:
                    # No need to bind the user credentials again because it's
                    # already done by the LDAP retrieve_scopes method
                    idp_bound = True
            except ldap.INVALID_CREDENTIALS as exception: # pylint: disable=no-member
                raise HTTPInternalServerError(
                    data=f"Idp scopes mapping failed with user {username} on {idp_config.idp_name}: {exception}"
                ) from exception
            if not scopes:
                scopes = idp_config.scopes
                if idp_config.deny_access:
                    scopes = []
        return scopes, idp_bound

    async def _handle_ldap_authentication(
        self,
        idp_config: LdapConfig,
        username: str,
        password: str,
        user: dict | None = None
    ) -> dict:
        """
        Method used to manage LDAP authentication

        Args:
            idp_config (LdapConfig): Ldap Config
            username (str): User name
            password (str): User password
            user (dict | None): User dict

        Returns:
            dict: User dict updated
        """
        # First apply role mapping and retrieve scopes, this will use bind_dn or user credentials
        # to perform an LDAP search. If user credentials are used, `idp_bound` will be True in case
        # of login success and no new bind request will be done.
        LOG.debug("Check roles mapping for user %s on idp %s", username, idp_config.idp_name)
        scopes, idp_bound = await self._retrieve_scopes(idp_config, username, password)
        if not idp_bound:
            try:
                LOG.debug("Check if user %s of %s is already in LDAP cache", username, idp_config.idp_name)
                _username = await self._retrieve_user_dn_from_ldap_cache(idp_config, username)
                LOG.debug("Cache hit for user %s of %s", username, idp_config.idp_name)
            except (LdapUnavailableCache, LdapNoCacheEntry) as exception:
                _username = None
                LOG.warning(
                    "Exception occured when retrieving user dn from cache: %s on idp %s",
                    exception,
                    idp_config.idp_name,
                )

            _is_user_dn = bool(_username)
            LOG.debug("Bind user %s on idp %s", _username if _is_user_dn else username, idp_config.idp_name)
            await self.ldap_idp.bind(
                idp_name=idp_config.idp_name,
                username=_username if _is_user_dn else username,
                password=password,
                is_user_dn=_is_user_dn,
                loop=self.loop
            )
            LOG.debug("Bind user %s on idp %s was successful",
                      _username if _is_user_dn else username, idp_config.idp_name)

        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                if user:
                    LOG.debug("Update user %s with scopes %s on idp %s", username, scopes, idp_config.idp_name)
                    await self.db.update_user_by_name(
                        username=username,
                        idp_name=idp_config.idp_name,
                        scopes=scopes,
                        session=session
                    )
                else:
                    LOG.debug("Create user %s with scopes %s on idp %s", username, scopes, idp_config.idp_name)
                    creation_id = ObjectId()
                    # Create user in DB here
                    user_obj = User(creation_id=creation_id,
                                    username=username,
                                    password=None,
                                    enabled=True,
                                    level=self.settings.default_level,
                                    scopes=scopes,
                                    internal=False,
                                    idp_name=idp_config.idp_name)
                    # Add User to DB here
                    res = await self.db.create_user(user_obj, Collections.users.name, session=session)
                    user = user_obj.to_dict()
                    user["_id"] = res.inserted_id
        return user

    @log_activity("logged out", "failed to logout")
    async def logout(self, request: Request) -> Response:
        """

        Logout handler
        :param request:
        :return:
        """
        try:
            token = extract_token(request)
        except RequestExtractError as error:
            raise HTTPBadRequest(data=str(error)) from error

        db_token = await self.db.collection_tokens.get_by_access_token(token)
        slo_url = None
        if db_token and db_token.session_index:
            # User is logged in with saml idp
            relay_state = request.parameters.get('relay_state')
            idp_config = await self.db.get_idp_config_by_name(idp_name=db_token.idp_name)
            if not idp_config:
                raise HTTPInternalServerError(
                    data=f"Idp {idp_config.idp_name} has been deleted"
                )
            try:
                _, slo_url = self.saml_idp.generate_auth_url(
                    idp_config, relay_state, db_token.as_dict(), deploying_with_pmf=self.settings.deploying_with_pmf)
            except Exception as exception:
                raise HTTPInternalServerError(
                    data=f"Idp {idp_config.idp_name} is badly configured: {exception}"
                ) from exception

        token_deleted = await self.db.collection_tokens.remove_by_access_token(token)
        if not token_deleted or not token_deleted.acknowledged or not token_deleted.deleted_count:
            raise HTTPBadRequest(data="Can't delete token")
        body = {"body": "Successfully logged out !"}
        if slo_url:
            body['slo_url'] = slo_url
        return Response(200, body, {"content-type": "application/json"})

    async def saml_callback_get(self, request: Request) -> Response:
        """
        Handle SAML callback for GET requests

        Args:
            request (Request): Request object containing SAMLResponse and RelayState in parameters
        Returns:
            Response: Response object
        """
        saml_response = request.parameters.get('SAMLResponse')
        relay_state = request.parameters.get('RelayState')
        return await self._saml_callback(relay_state=relay_state, saml_response=saml_response, request=request)

    async def saml_callback_post(self, request: Request) -> Response:
        """
        Handle SAML callback for POST requests

        Args:
            request (Request): Request object containing SAMLResponse and RelayState in body
        Returns:
            Response: Response object
        """
        saml_response = request.body.get('SAMLResponse')[0]
        relay_state = request.body.get('RelayState')[0]
        return await self._saml_callback(relay_state=relay_state, saml_response=saml_response, request=request)

    async def _saml_callback(self, relay_state: str, saml_response: str, request: Request) -> Response:
        """
        URL Location where the login <Response> from the IdP will be returned

        Args:
            relay_state (str): Relay state url redirection
            saml_response (str): SAML response string
            request (Request): Request object
        Returns:
            Response: Response object
        """
        try:
            idp_name = request.parameters.get('idp_name')
            mode = request.parameters.get('mode')
            user_ip = extract_user_ip(request)
            headers = await self.assertion_consumer_service(saml_response, relay_state, idp_name, mode, user_ip)
        except Exception as exception:
            cookie_path = urlparse(relay_state).path
            headers = multidict.MultiDict([
                ('Set-Cookie', f"saml_error={str(exception)}; Path={cookie_path}"),
                ('Location', relay_state),
                ('content-type', "application/json")])
            return Response(302, {}, headers)
        return Response(302, {}, headers)

    async def assertion_consumer_service(
        self,
        saml_response: str,
        relay_state: str,
        idp_name: str,
        mode: str | None,
        user_ip: str | None
    ) -> dict:
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-positional-arguments
        """
        SAML assertion consumer service

        Args:
            saml_response (str): Saml response string
            relay_state (str): Relay state url redirection
            idp_name (str): IDP name
            mode (str, optional): mode (login/logout)
            user_ip (str, optional): user ip

        Returns:
            dict: Headers used for redirect
        """
        cookie_path = urlparse(relay_state).path

        # Get SAML config
        saml_config = await self.db.get_idp_config_by_name(idp_name)
        if not saml_config:
            raise HTTPNotFound(data=f"Saml config {idp_name} not found")

        # Get the child containing the username information
        # pylint: disable=too-many-nested-blocks
        try:
            callback_mode = IdpCallbackMode(mode) if mode else self.saml_idp.get_mode(saml_response)
            response = self.saml_idp.compute_saml_response(saml_config, saml_response, relay_state, callback_mode)
            # Checks that the response has the SUCCESS status
            if callback_mode == IdpCallbackMode.LOGIN:
                response.check_status()
            else:
                assert response.get_status() == OneLogin_Saml2_Constants.STATUS_SUCCESS
        except Exception as e:
            self.logger.warning(f'Unable to parse SAML callback response: {str(e)}')
            raise HTTPInternalServerError(data="Bad SAMLResponse") from e

        if callback_mode == IdpCallbackMode.LOGOUT:
            headers = {'location': relay_state, 'content-type': 'application/json'}
            return headers

        nameidentifier = response.get_nameid()
        session_index = response.get_session_index()
        _attributes = response.get_attributes()
        username = None
        for attr_key, attr_value in _attributes.items():
            if 'emailaddress' in attr_key:
                username = attr_value[0]
                break
        if not username:
            username = response.get_nameid()

        # Default scopes define on saml config
        default_scopes = saml_config.scopes
        scopes = retrieve_scopes_from_roles_mapper(
            saml_config.mappers,
            Attributes(_attributes)
        )

        if len(scopes) > 0:
            db_scopes = await self.db.collection_scopes.get_list()
            _existing_scopes_ref = [item.id for item in db_scopes]
            scopes = [scope for scope in scopes if scope in _existing_scopes_ref]

        if not scopes:
            if saml_config.deny_access:
                await self.db.update_user_by_name(username, idp_name, False, [])
                _headers = multidict.MultiDict([('Set-Cookie', f"saml_error=Access Forbidden; Path={cookie_path}"),
                                               ('Location', relay_state),
                                               ('content-type', "application/json")])
                return _headers
            scopes = default_scopes

        configuration = await self.db.get_configuration()

        user = await self.db.get_user_by_name(username=username, idp_name=saml_config.idp_name)
        if not user:
            try:
                creation_id = ObjectId()
                # Create user in DB here
                user_obj = User(creation_id=creation_id,
                                username=username,
                                password=None,
                                enabled=True,
                                level=self.settings.default_level,
                                scopes=scopes,
                                internal=False,
                                idp_name=saml_config.idp_name)

                # Add User to DB here
                await self.db.create_user(user_obj, Collections.users.name)
                user = user_obj.to_dict()

            except Exception as exception:
                raise HTTPInternalServerError(
                    data=f"Identity provider exception with user {username} on {saml_config.idp_name}: {exception}"
                ) from exception
        elif user["scopes"] != scopes:
            await self.db.update_user_by_name(
                user["username"], user["idp_name"], user.get("internal", False), scopes
            )

        # Generate token
        token = Token.generate(
            user_id=user["user_id"],
            token_expiration=configuration.token_expiration,
            refresh_token_expiration=configuration.refresh_token_expiration,
            session_timeout_disabled=user.get("session_timeout_disabled", False),
            user_ip=user_ip,
            session_index=session_index,
            nameidentifier=nameidentifier,
            idp_name=saml_config.idp_name
        )

        # Store token
        result = await self.db.collection_tokens.store(token)
        if not result or not result.acknowledged:
            raise HTTPInternalServerError(data="Can't store token")

        headers = multidict.MultiDict([('Set-Cookie', f"access_token={token.token}; Path={cookie_path}"),
                                       ('Set-Cookie', f"refresh_token={token.refresh_token}; Path={cookie_path}"),
                                       ('Set-Cookie',
                                        f"expires_in={int(configuration.token_expiration.total_seconds())};"
                                        f" Path={cookie_path}"),
                                       ('Set-Cookie', f"token_type=bearer; Path={cookie_path}"),
                                       ('Set-Cookie', f"username={username}; Path={cookie_path}"),
                                       ('Location', relay_state),
                                       ('content-type', "application/json")])
        return headers

    async def generate_sso(self, request: Request) -> Response:
        """
        Generate sso url

        Args:
            request (Request): Request

        Returns:
            Response: Response
        """
        idp_name = request.parameters.get('idp_name')
        relay_state = request.parameters.get('relay_state')
        idp_config = await self.db.get_idp_config_by_name(idp_name=idp_name)
        if not idp_config:
            raise HTTPNotFound(data=f"Idp {idp_name} does not exist")
        sso_url, _ = self.saml_idp.generate_auth_url(
            idp_config, relay_state, deploying_with_pmf=self.settings.deploying_with_pmf)

        headers = multidict.MultiDict([('Location', sso_url),
                                       ('content-type', "application/json")])

        return Response(302, {}, headers)

    async def get_sp_metadata(self, request: Request) -> Response:
        """ Generate and return SP metadata """
        idp_name = request.parameters.get('idp_name')
        try:
            idp_config = await self.db.get_idp_config_by_name(idp_name=idp_name)
            if not idp_config:
                raise HTTPNotFound(data=f"Idp {idp_name} does not exist")

            # If relay_state was provided, compute complete SP metadata
            relay_state = request.parameters.get('relay_state')
            if relay_state:
                acs, slo, entity_id = self.saml_idp.get_callback_urls(relay_state, idp_config.idp_name)
                settings = self.saml_idp.get_saml_settings(idp_config, acs, slo, entity_id)
            else:
                settings = self.saml_idp.get_saml_settings(idp_config)

            metadata = settings.get_sp_metadata()

            # If SP certificates were provided, metadata will be encoded
            if isinstance(metadata, (bytes, bytearray)):
                metadata = metadata.decode('utf-8')
        except HTTPNotFound:
            raise
        except OneLogin_Saml2_Error as exception:
            msg = f'Invalid IDP metadata: {str(exception)}'
            self.logger.warning(msg)
            raise HTTPBadRequest(headers={"content-type": "text/plain"}, data=msg) from exception

        except Exception as exception:
            self.logger.error(f"Exception: {exception}")
            raise HTTPInternalServerError(headers={"content-type": "text/plain"},
                                          data=f"Internal Server Error - {exception}") from exception
        return Response(200, metadata, {"content-type": "text/xml"})

    @inject_internal_user_param
    async def force_user_disconnection(self, request: Request, internal: bool = False) -> Response:
        """
        Force user disconnection handler

        Args:
            request (Request): request input
            internal (bool): internal flag set by inject_internal_user_param decorator

        Returns:
            Response: Response openapi

        Raises:
            HTTPNotFound: User not found
            HTTPInternalServerError: Can't delete token.
        """
        username = request.body.get('username')
        idp_name = request.body.get('idp_name', DEFAULT_LOCAL_IDP_NAME)

        user = await self.db.get_user_by_name(username=username, internal=internal, idp_name=idp_name)
        if not user:
            raise HTTPNotFound(data="User not found")
        token_deleted = await self.db.collection_tokens.remove_by_user_id(user_id=user['user_id'])
        if not token_deleted or not token_deleted.acknowledged or not token_deleted.deleted_count:
            raise HTTPInternalServerError(data="Can't delete token, maybe the user is not connected")
        return Response(200, {"body": f"{username} successfully disconnected !"}, {"content-type": "application/json"})

    @log_activity(
        success_message="updated session timeout to %(session_timeout)s",
        failure_message="failed to update session timeout to %(session_timeout)s",
        context_func=lambda req: {
            "session_timeout": req.body["disabled"]
        }
    )
    async def change_session_timeout(self, request: Request) -> Response:
        """
        Change session timeout handler for non-internal user

        Args:
            request (Request): request input

        Returns:
            Response: Response openapi
        """
        user_dict = await self._find_user_by_headers(request, _id=True, creation_id=True)

        # Use transaction because we manipulates several collections
        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                await self.db.update_user_by_name(
                    username=user_dict["username"],
                    idp_name=user_dict["idp_name"],
                    session_timeout_disabled=request.body["disabled"]
                )
                await self.db.collection_tokens.remove_by_user_id(
                    user_id=user_dict['user_id']
                )

        return Response(200, {"body": "Session timeout changed successfully !"}, {"content-type": "application/json"})

    # *** PASSWORD methods implementation ****
    @log_activity(
        success_message="updated user %(username)s:%(idp_name)s password",
        failure_message="failed to update user %(username)s:%(idp_name)s password",
        context_func=lambda req: {
            "username": req.body["username"],
            "idp_name": req.body["idp_name"],
        }
    )
    async def deprecated_change_password(self, request: Request) -> Response:
        """
        DEPRECATED endpoint to change password
        """
        raise HTTPGone(data="this endpoint is deprecated")

    @log_activity(
        success_message="updated his password",
        failure_message="failed to update his password",
    )
    async def change_password(self, request: Request) -> Response:
        """
        Change password handler for non-internal user

        Args:
            request (Request): request input

        Returns:
            Response: Response openapi

        Raises:
            HTTPBadRequest: Bad Request
        """
        user = await self._find_user_by_headers(request, _id=True, creation_id=True)

        user_id = user["user_id"]
        old_password = request.body.get("old_password")
        new_password = request.body.get("new_password")
        salted_old_password = User.generate_salted_encrypted_password(
            old_password,
            user['creation_id'].binary,
            encrypt=self.encrypt
        )
        generated_user_id = User.generate_hash([user['username'], salted_old_password, user['idp_name']])
        if user_id != generated_user_id:
            raise HTTPBadRequest(data="Incorrect old password, please retry")

        if new_password == old_password:
            raise HTTPBadRequest(data="Password must be different from previous one")

        # Check the password
        configuration = await self.db.get_configuration()
        if not configuration.password_policy.validate_password_constraints(new_password):
            raise HTTPBadRequest(
                data="The password doesn't match the constraints",
                headers={"content-type": "text/plain"}
            )

        salted_new_password = User.generate_salted_encrypted_password(
            new_password,
            user['creation_id'].binary,
            encrypt=self.encrypt
        )
        updated_user = User(
            _id=user['_id'],
            creation_id=user['creation_id'],
            username=user.get("username"),
            password=salted_new_password,
            password_last_update=utcnow().timestamp(),
            scopes=user.get("scopes"),
            first_login=False,
            password_expired=False,
            session_timeout_disabled=user.get("session_timeout_disabled"),
            internal=False,
            password_expiration_disabled=user.get("password_expiration_disabled")
        )

        # Use transaction because we manipulates several collections
        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                await self.db.update_user_by_id(user_id=user_id,
                                                user_object=updated_user,
                                                session=session)
                user_tokens = await self.db.collection_tokens.get_list_by_user_id(user_id=user_id)
                for user_token in user_tokens:
                    await self.db.collection_tokens.update_user_id(user_token.token,
                                                                   updated_user.user_id,
                                                                   session=session)
                # Remove the deprecated token
                token = extract_token(request)
                await self.db.collection_tokens.remove_by_access_token(token, session=session)

        return Response(200, {"body": "Password changed successfully !"}, {"content-type": "application/json"})

    async def get_actions(self, _) -> Response:
        """

        Get the available actions
        :return:
        """
        # internal actions shall not be returned
        actions = await self.db.collection_actions.get_list({"internal": {"$ne": True}})
        return Response(
            200,
            [action.to_dict() for action in actions],
            {"content-type": "application/json"}
        )

    # *** SCOPES methods implementation ****
    @inject_internal_user_param
    async def get_scopes_deprecated(self, request: Request, internal: bool = False) -> Response: # pylint: disable=unused-argument
        """
        Get the available scopes
        Legacy GET /scopes doesn't support filter mode and can only retrieve expert scopes,
        filtering was only done on frontend side.
        :param request:
        :param internal:
        :return:
        """
        scope_filter = ScopeFilter(
            internal=internal
        )
        scopes = await self.db.collection_scopes.get_list(scope_filter=scope_filter)
        return Response(200, [scope.to_dict() for scope in scopes], {"content-type": "application/json"})

    @inject_internal_user_param
    async def get_scopes(self, request: Request, internal: bool = False) -> Response:
        """
        Get the available scopes
        :param request:
        :param internal:
        :return:
        """
        # pylint: disable=too-many-locals,too-many-branches
        id_sort_order = ScopeIdSortOrder(request.parameters.get('sort', ScopeIdSortOrder.ASCENDING.value))
        # default filter_mode is expert mode
        filter_mode = ScopeFilterMode[request.parameters.get('mode', ScopeFilterMode.EXPERT.value).upper()]
        app_name = request.parameters.get('app_name')
        scope_type = request.parameters.get('type')
        label = request.parameters.get('label')
        default_flag = request.parameters.get('default', None) # to get only the default scopes
        _range = request.parameters.get('range')

        page_limit = self.settings.scopes_page_limit
        req_start = 0
        req_end = None
        if _range:
            req_start, req_end = map(int, _range.split('-'))
            if req_end < req_start:
                raise HTTPBadRequest(headers={"content-type": "text/plain"},
                                     data=f"Invalid range requested {request.parameters.get('range')}")

        # compute the skip and limit parameters for Mongo (limit=0 means no limit)
        if page_limit > 0:
            if req_end is not None:
                # the number of scopes to return (requested nb: req_end - req_start + 1) could not be greater
                # than page_limit
                limit = min(req_end - req_start + 1, page_limit)
            else:
                # No range specified: the page_limit scopes are requested
                limit = page_limit
        else:
            if req_end is not None:
                limit = req_end - req_start + 1 # if range specified, all the requested scopes are returned
            else:
                limit = 0 # no range specified, no limit
        skip = req_start

        scope_filter = ScopeFilter(
            mode=filter_mode,
            internal=internal,
            pmf_release_name=self.settings.release_name,
            app_name=app_name,
            scope_type=scope_type,
            label=label,
            default=default_flag
        )
        scopes_paginated_response = await self.db.collection_scopes.get_list_paginated(
            scope_filter=scope_filter,
            id_sort=id_sort_order,
            skip=skip,
            limit=limit
        )
        res_scopes = scopes_paginated_response.scopes
        res_total = scopes_paginated_response.total
        res_start = scopes_paginated_response.start
        res_end = res_start + len(res_scopes) - 1 if len(res_scopes) > 0 else res_start
        headers = {
            "content-type": "application/json",
            "Accept-Ranges": f"scopes {page_limit}" if page_limit > 0 else "scopes"
        }
        if _range and (req_end is not None and req_end + 1 > res_total or res_total == 0):
            # the requested range exceeds the total available items
            headers["Content-Range"] = f"scopes */{res_total}"
            raise HTTPRangeNotSatisfiable(headers=headers)
        if res_total > 0:
            headers["Content-Range"] = f"scopes {res_start}-{res_end}/{res_total}"
        else:
            headers["Content-Range"] = "scopes */0"
        if (req_start == 0 and res_end + 1 == res_total) or (res_total == 0 and _range is None):
            # all scopes returned if any
            status_code = 200
        else:
            # partial result
            status_code = 206
        return Response(status_code, [scope.to_dict() for scope in res_scopes], headers=headers)

    @inject_internal_user_param
    async def get_scope_by_id(self, request: Request, internal: bool = False) -> Response:
        """
        Get the available scopes
        :param request:
        :param internal:
        :return:
        """
        _id = request.parameters.get('id')
        scope = await self.db.collection_scopes.get_by_id(_id=_id, internal=internal)
        if not scope:
            raise HTTPNotFound()
        return Response(200, scope, {"content-type": "application/json"})

    # TODO: should we inject internal arg to predict if scope to store is internal or not ?
    @log_activity("added scope %(scope_name)s",
                  "failed to add scope %(scope_name)s",
                  context_func=lambda req: {"scope_name": req.body.get('id')})
    async def store_scope(self, request: Request) -> Response:
        """ Store a scope into database """
        scope: Scope = Scope.from_dict(request.body)

        async with self.db.client.start_session() as session:
            async with await session.start_transaction():
                if not await self.db.collection_scopes.store(scope, session=session):
                    raise HTTPConflict(data=f"Scope with id '{scope.id}' already exists")

        return Response(201, "OK", {"content-type": "text/plain"})

    # TODO: should we inject internal arg to predict if scope to store are internal or not ?
    async def store_scopes(self, request: Request) -> Response:
        """
        Store scopes into database
        :param request:
        :return:
        """
        already_exist = []
        scopes = request.body
        for _scope in scopes:
            scope: Scope = Scope.from_dict(_scope)
            _id = scope.id
            if not await self.db.collection_scopes.store(scope):
                already_exist.append(_id)
        if already_exist:
            message = f"Scopes added except {already_exist} that already are in scopes db"
        else:
            message = "All required scopes added"
        return Response(200, {"body": message}, {"content-type": "application/json"})

    @inject_internal_user_param
    async def remove_scopes(self, request: Request, internal: bool = False) -> Response:
        """
        Remove scopes from database
        :param request:
        :param internal:
        :return:
        """
        not_found = []
        scopes = request.body
        for scope in scopes:
            _id = scope.get('id')
            scope_db = await self.db.collection_scopes.get_by_id(_id=_id, internal=internal)
            should_skip = (
                not scope_db or
                scope_db.get('default') or
                not await self.db.collection_scopes.remove_by_id(_id=_id, internal=internal)
            )
            if should_skip:
                not_found.append(_id)
            if _id not in not_found:
                # remove scope from user
                await self.db.remove_scope_from_users(scope_id=_id)

        if not_found:
            message = f"Scopes removed except {not_found} that are not in scopes db or are default ones"
        else:
            message = "All required scopes deleted"
        return Response(200, {"body": message}, {"content-type": "application/json"})

    @log_activity("%(success_message)s",
                  "%(failure_message)s",
                  context_func=generate_audit_log_for_scope_update)
    @inject_internal_user_param
    async def update_scope_by_id(self, request: Request, internal: bool = False) -> Response:
        """
        Update some scopes
        :param request:
        :param internal:
        :return:
        """
        _id = request.parameters.get('id')
        scope = request.body
        result = await self.db.collection_scopes.update_by_id(
            _id=_id, scope=Scope.from_dict(scope), internal=internal
        )
        if not result or not result.acknowledged:
            raise HTTPInternalServerError(data=f"Update scope {_id} failed")
        if not result.matched_count:
            raise HTTPNotFound(data=f"Can't find scope {_id}")
        return Response(200, f"Scope {_id} updated", {"content-type": "text/plain"})

    @log_activity("removed scope %(scope_name)s",
                  "failed to remove scope %(scope_name)s",
                  context_func=lambda req: {"scope_name": req.parameters.get('id')})
    @inject_internal_user_param
    async def remove_scope_by_id(self, request: Request, internal: bool = False) -> Response:
        """
        Update some scopes
        :param request:
        :param internal:
        :return:
        """
        _id = request.parameters.get('id')
        scope_db = await self.db.collection_scopes.get_by_id(_id=_id, internal=internal)
        if not scope_db:
            raise HTTPNotFound(data=f"Can't find scope {_id}")
        if scope_db.get('default'):
            raise HTTPBadRequest(data="Can't remove a default scope!")
        result = await self.db.collection_scopes.remove_by_id(_id=_id, internal=internal)
        await self.db.remove_scope_from_users(scope_id=_id)
        if not result or not result.acknowledged:
            raise HTTPInternalServerError(data=f"Delete scope {_id} failed")
        if not result.deleted_count:
            raise HTTPNotFound(data=f"Delete scope {_id} failed")
        return Response(200, f"Scope {_id} deleted", {"content-type": "text/plain"})

    async def change_token_expiration(self, request: Request) -> Response:
        """

        :param request:
        :return:
        """
        token_expiration = request.body
        # Check token_expiration is strictly lower to refresh_token_expiration before updating in DB
        configuration = await self.db.get_configuration()
        if configuration and token_expiration is not None and \
           configuration.refresh_token_expiration is not None and \
           token_expiration >= configuration.refresh_token_expiration.total_seconds():
            LOG.error('token_expiration (%s) is greater or equal then refresh_token_expiration (%s)',
                      token_expiration, configuration.refresh_token_expiration)
            raise HTTPBadRequest(data="token_expiration must be strictly lower to refresh_token_expiration")
        await self.db.update_configuration(token_expiration=token_expiration)
        return Response(200, f"Token expiration set to {token_expiration} seconds",
                        {"content-type": "text/plain"})

    @log_activity("validated idp configuration", "failed to validate idp configuration")
    async def validate_idp_config(self, request: Request) -> Response:
        """
        Validate an idp config

        :param request: [description]
        :return: [description]
        """
        username = request.body.get('username')
        password = request.body.get('password')
        idp_config = request.body
        try:
            if idp_config["idp_type"] == IdpType.ldap.name:
                _username = None
                # Check the cache
                if "bind_dn" in idp_config and idp_config["bind_dn"] not in [None, ""]:
                    # Retrieve user dn from cache here
                    idp_ldap_config = LdapConfig.from_dict(idp_config)
                    try:
                        _username = await self._retrieve_user_dn_from_ldap_cache(idp_ldap_config, username)
                    except LdapUnavailableCache as exception:
                        # If there is no cache, try finding it manually
                        LOG.warning("Exception occured when retrieving user dn from cache"
                                    "(trying to find it manually): %s", exception)
                        idp_ldap_config.bind_password = self.encrypt(idp_ldap_config.bind_password)
                        _username = await self._retrieve_user_dn_manually(idp_ldap_config, username)
                    except LdapNoCacheEntry as exception:
                        LOG.warning("Exception occured when retrieving user dn from cache"
                                    "(will use the default username): %s", exception)
                _is_user_dn = bool(_username)
                username = _username if _is_user_dn else username
                await self.ldap_idp.validate_idp_config(username=username, password=password,
                                                        idp_config=idp_config, is_user_dn=_is_user_dn,
                                                        loop=self.loop)
            else:
                self.saml_idp.validate_idp_config(idp_config=idp_config)
        except Exception as error:
            return Response(406,
                            f'Not acceptable - Invalid {idp_config["idp_type"].upper()} config: {error}',
                            {"content-type": "text/plain"})
        return Response(200, f'Ok - Valid {idp_config["idp_type"].upper()} config',
                        {"content-type": "text/plain"})

    @log_activity("added idp configuration %(idp_name)s",
                  "failed to add idp configuration %(idp_name)s",
                  context_func=lambda req: {"idp_name": req.body.get('idp_name', DEFAULT_LOCAL_IDP_NAME)})
    async def store_idp_config(self, request: Request) -> Response:
        """

        :param request:
        :return:
        """
        config_updated = False
        idp_type = request.body.get("idp_type")
        if idp_type not in [IdpType.ldap.name, IdpType.saml.name]:
            raise HTTPInternalServerError(data="Can't store idp config different from ldap or saml")
        # to deal with default values
        dict_idp_config = None
        if idp_type == IdpType.ldap.name:
            config_updated = True
            idp_config = LdapConfig.from_dict(request.body)
            if idp_config.bind_password:
                idp_config.bind_password = self.encrypt(idp_config.bind_password)
            dict_idp_config = idp_config.to_dict(with_bind_password=True)
        elif idp_type == IdpType.saml.name:
            idp_config = SamlConfig.from_dict(request.body)
        try:
            if not dict_idp_config:
                dict_idp_config = idp_config.to_dict()
            result = await self.db.store_idp_config(dict_idp_config)
            if not result or not result.acknowledged:
                raise HTTPInternalServerError(data="Can't store ldap config")
            if config_updated:
                # In this case update the 'ldap_cache' db collection as a background task
                self._run_task_in_background(task=self._upsert_ldap_cache_data(ldap_config=idp_config))
        except DuplicateKeyError as e:
            raise HTTPConflict(
                data=f"Can't store IDP config, entry with name {idp_config.idp_name} already exists."
            ) from e
        except Exception as e:
            raise HTTPInternalServerError(data="Can't store ldap config") from e
        return Response(201, "OK", {"content-type": "text/plain"})

    async def get_idp_configs(self, request: Request) -> Response:  # pylint: disable=unused-argument
        """

        :param request:
        :return:
        """
        idp_configs = await self.db.get_idp_configs(projection={'bind_password': False})
        return Response(200, [item.to_dict() for item in idp_configs], {"content-type": "application/json"})

    async def get_idp_config_by_type(self, request: Request) -> Response:  # pylint: disable=unused-argument
        """

        :param request:
        :return:
        """
        idp_type = request.parameters.get('idp_type')
        idp_configs = await self.db.get_idp_configs_by_type(idp_type=idp_type)
        return Response(200, [item.to_dict() for item in idp_configs], {"content-type": "application/json"})

    async def get_idp_config_by_name(self, request: Request) -> Response:
        """

        :param request:
        :return:
        """
        idp_name = request.parameters.get('idp_name')
        idp_config_config = await self.db.get_idp_config_by_name(idp_name=idp_name)
        if not idp_config_config:
            raise HTTPNotFound()
        return Response(200, idp_config_config.to_dict(), {"content-type": "application/json"})

    @log_activity("%(success_message)s",
                  "%(failure_message)s",
                  context_func=generate_audit_log_for_idp_config_update)
    async def update_idp_config(self, request: Request) -> Response:
        # pylint: disable=too-many-branches,too-many-statements
        """
        :param request:
        :return:
        """
        idp_name = request.parameters.get('idp_name')
        update_users_scopes = request.parameters.get('update_users_scopes')
        idp_config = await self.db.get_idp_config_by_name(idp_name)
        if idp_config.idp_type not in [IdpType.ldap.name, IdpType.saml.name]:
            raise HTTPBadRequest(data="Can't update idp config different from ldap or saml")

        if idp_config.idp_type != request.body.get('idp_type'):
            raise HTTPBadRequest(data="Can't update idp config. idp_type from config in database")
        del request.body["idp_type"]

        data = request.body
        if request.body.get('bind_password', None) is not None:
            data['bind_password'] = self.encrypt(request.body['bind_password'])

        # Create a transaction and update two collections in a transaction
        try:
            async with self.db.client.start_session() as session:
                async with await session.start_transaction():
                    res = await self.db.update_idp_config(idp_name=idp_name, data=data, session=session)
                    if not res or not res.acknowledged:
                        raise HTTPInternalServerError(data=f"Error occurred during update ldap idp_config {idp_name}")
                    updated_scopes = request.body.get('scopes')
                    if update_users_scopes and updated_scopes is not None:
                        # Update users scopes in DB
                        res_update_scopes = await self.db.update_users_by_idp_scopes(idp_name=idp_name,
                                                                                     scopes=updated_scopes,
                                                                                     session=session)
                        if not res_update_scopes:
                            raise HTTPInternalServerError(data="Error occurred during update users scopes")
        except OperationFailure as err:
            raise HTTPInternalServerError(data=f"Internal error while updating collections: {err}") from err

        if idp_config.idp_type == IdpType.ldap.name:
            LOG.debug("Run populate cache task for %s", idp_config.idp_name)
            self._run_task_in_background(task=self._upsert_ldap_cache_data(ldap_config=idp_config))
        return Response(200, f"ldap idp_config {idp_name} updated", {"content-type": "text/plain"})

    @log_activity("removed idp configuration %(idp_name)s",
                  "failed to remove idp configuration %(idp_name)s",
                  context_func=lambda req: {"idp_name": req.parameters.get('idp_name')})
    async def remove_idp_config(self, request: Request) -> Response:
        """
        :param request:
        :return:
        """
        idp_name = request.parameters.get('idp_name')

        # Create a transaction and update two collections in a transaction
        try:
            async with self.db.client.start_session() as session:
                async with await session.start_transaction():
                    # Remove idp configuration from db
                    res = await self.db.remove_idp_config(idp_name=idp_name, session=session)
                    if not res or not res.acknowledged:
                        raise HTTPInternalServerError(data=f"Error occurred during remove ldap idp_config {idp_name}")
                    if not res.deleted_count:
                        raise HTTPNotFound(data=f"Error occurred during remove ldap idp_config {idp_name}")

                    # Remove all the users attached to this configuration
                    res_delete_users = await self.db.delete_users_by_idp_name(idp_name=idp_name, session=session)
                    if not res_delete_users or not res_delete_users.acknowledged:
                        raise HTTPInternalServerError(
                            data=f"Error occurred during remove ldap idp_config {idp_name} users")

                    # Remove LDAP cache
                    cache_res = await self.db.remove_ldap_cache_by_idp_name(idp_name, session=session)
                    LOG.debug("Remove ldap cache for idp %s: %d document removed", idp_name, cache_res.deleted_count)
        except OperationFailure as err:
            raise HTTPInternalServerError(data=f"Internal error while updating collections: {err}") from err
        return Response(200, f"ldap idp_config {idp_name} and users to this config removed",
                        {"content-type": "text/plain"})

    async def _check_token(self, request: Request, introspection: bool = False) -> Token:
        """ Check the token availability.

        Args:
            request (Request): request with token to check
            introspection (bool): introspection flag, default to False.

        Raises:
            `RequestExtractError` when the token cannot be extracted from the request.
            `CheckTokenError` when the token is not in the database.
            `CheckTokenError` when the token is expired.

        Returns:
            Token: database token associated with the access token in the request.
        """
        # Extract the access token from the request
        token = extract_token(request, introspection)
        # Retrieve the database token associated with the access token
        token_db = await self.db.collection_tokens.get_by_access_token(token)
        if not token_db:
            raise CheckTokenError("Missing token in headers")
        # Check its expiration date
        # Caution: when a datetime is stored in mongodb, tzinfo is lost
        if token_db.expiration_date and token_db.expiration_date < datetime.utcnow():
            raise CheckTokenError("Token expired")
        return token_db

    def _check_remote_ip(self, request: Request, token: Token, user_dict: dict):
        """ Check the request remote IP against the token user IP in database (save at login).
        NOTE: `token.user_ip` CANNOT BE required to support old tokens.

        Args:
            request (Request): request with remote IP to check
            token (Token): token from the database
            user (dict): current user token as dict

        Raises:
            `CheckRemoteIPInvalid` when the request remote IP does not match with token user IP.
        """
        # Extract user-agent
        user_agent: str = extract_user_agent_as_string(request)
        if user_agent in ["axios/1.3.4", "axios/1.6.5"]:
            # When the user-agent matches to this constraint, we skip the check to
            # support PMS versions. For more details, go and see the comment:
            # https://myateme.atlassian.net/browse/MS-9466?focusedCommentId=1467515.
            # TODO: Remove when we won't support these PMF versions.
            return
        # Extract remote IP address from the request
        remote = extract_user_ip(request)
        # Check the request remote IP against the token user IP when available.
        if token.user_ip and token.user_ip != remote:
            username = user_dict["username"]
            idp_name = user_dict["idp_name"]
            raise CheckRemoteIPInvalid(username, idp_name, remote, token.user_ip)

    async def token_introspection(self, request: Request) -> Response:
        """ Check if the token given in the request is allowed to make this request.

        Args:
            request (Request): request to process

        Raises:
            HTTPUnauthorized:
                when the token cannot be extracted from the request.
                when the token is not found in the database.
                when the token is expired.
                when the request remote IP does not match with the token user IP in database.
            HTTPBadRequest:
                when `uri` or `method` cannot be extracted from the request.
            HTTPForbidden:
                when the user is not found in the database.
                when the user is not allowed to make the request.

        Returns:
            Response: a response with the required introspection headers (username and idp_name).
        """
        try:
            token = await self._check_token(request, introspection=True)
        except (RequestExtractError, CheckTokenError) as error:
            raise HTTPUnauthorized(data=str(error)) from error
        user_dict = await self.db.get_user_by_id(token.user_id, internal_projection=True)
        if not user_dict:
            raise HTTPForbidden(data=f"Can't find user with id: {token.user_id}")
        try:
            self._check_remote_ip(request, token, user_dict)
        except CheckRemoteIPInvalid as error:
            http_error = HTTPUnauthorized(data=str(error))
            set_activity_log(http_error, error.activity_message, error.activity_extra)
            if self.settings.token_ip_validation:
                raise http_error from error
            # Else display the corresponding log activity
            extra = extract_activity_extra_data(request)
            show_activity_log(logging.ERROR, http_error, extra)
        try:
            uri, method = extract_uri_and_method(request)
        except (RequestExtractError) as error:
            raise HTTPBadRequest(data=str(error)) from error
        # `api_url` CANNOT BE required due to user-management auth ingress
        api_url: str = extract_api_url(request)
        try:
            await self.introspector.check_introspection(user_dict, uri, method, api_url)
        except IntrospectionError as error:
            raise HTTPForbidden(data=str(error)) from error
        return Response(
            200,
            {"active": True, "sub": user_dict["user_id"]},
            {
                "content-type": "application/json",
                HttpHeaders.X_USER: user_dict["username"],
                HttpHeaders.X_IDP_NAME: user_dict["idp_name"],
            }
        )

    async def refresh_token(self, request: Request) -> Response:
        """
        Refresh the access_token thanks to the given refresh_token
        TODO: rework to use the expired token and the refresh_token as filters.

        Args:
            request (Request): request with the refresh token

        Raises:
            HTTPBadRequest
                when the refresh_token is not found or expired.
                when the user is not found in the database.
                when the request remote IP does not match with the token user IP in database.
            HTTPInternalServerError
                when the Unable to refresh the token.

        Returns:
            Response: a response with the new access_token.
        """
        refresh_token = request.body['refresh_token']

        # Retrieve the database token associated with the refresh token
        token = await self.db.collection_tokens.get_by_refresh_token(refresh_token)
        if not token:
            raise HTTPBadRequest(data="Refresh token not found or expired")

        # Retrieve the user associated with the token
        user_dict = await self.db.get_user_by_id(user_id=token.user_id)
        if not user_dict:
            raise HTTPBadRequest(data=f"Can't find user with id: {token.user_id}")

        # Check remote IP
        try:
            self._check_remote_ip(request, token, user_dict)
        except CheckRemoteIPInvalid as error:
            http_error = HTTPBadRequest(data=str(error))
            set_activity_log(http_error, error.activity_message, error.activity_extra)
            if self.settings.token_ip_validation:
                raise http_error from error
            # Else display the corresponding log activity
            extra = extract_activity_extra_data(request)
            show_activity_log(logging.ERROR, http_error, extra)

        # Generate a new access token
        configuration = await self.db.get_configuration()
        old_access_token = token.token
        token.refresh_access_token(configuration.token_expiration)

        # Attempt atomic versioned update of the token
        result = await self.db.collection_tokens.refresh_token(
            token=old_access_token,
            new_token=token.token,
            new_expiration_date=token.expiration_date,
            current_version=token.version
        )
        if result.matched_count == 0:
            # Maybe another request has updated the token in the meantime
            # Fetch the latest token and return it
            token = await self.db.collection_tokens.get_by_refresh_token(refresh_token)
            if not token:
                raise HTTPInternalServerError(data="Unable to refresh the token")

        body = {
            "access_token": token.token,
            "refresh_token": token.refresh_token,
            "expires_in": int(configuration.token_expiration.total_seconds()),
            "token_type": "bearer"
        }
        return Response(200, body, {"content-type": "application/json"})

    async def _find_user_by_headers(self, request: Request, _id: bool = False, creation_id: bool = False) -> dict:
        """Find current user using the request headers
        Args:
            request (Request): Request
            _id: whether the user's ``_id`` field must be given
            creation_id: whether the user's ``creation_id`` field must be given
        Raises:
            HTTPUnauthorized: 401 Client HTTPUnauthorized
            HTTPNotFound: 404 User HTTPNotFound
        Returns:
            dict: Current user
        """
        username, idp_name = extract_username_and_idpname(request)
        if username and idp_name:
            # these metadata comes from the headers added by the introspection,
            # so we don't need to check the token again.
            user_dict = await self.db.get_user_by_name(
                username=username,
                idp_name=idp_name,
                all_users=True,
                _id=_id,
            )
            if not user_dict:
                LOG.error("User %s:%s not found from introspection headers", username, idp_name)
                raise HTTPNotFound(data="User not found")
            return user_dict

        # Fallback mode, no introspection metadata in the headers,
        # so we need to check the token.
        try:
            token = await self._check_token(request)
        except (RequestExtractError, CheckTokenError) as error:
            raise HTTPUnauthorized(data=str(error)) from error
        user_dict = await self.db.get_user_by_id(
            user_id=token.user_id,
            _id=_id,
            creation_id=creation_id
        )
        if not user_dict:
            LOG.error("User id %s not found from authorization token %s", token.user_id, token.token)
            raise HTTPNotFound(data="User not found")
        return user_dict

    async def get_current_user(self, request: Request) -> Response:
        """

        :param request:
        :return:
        """
        user_dict = await self._find_user_by_headers(request)
        return Response(200, user_dict, {"content-type": "application/json"})

    async def get_current_user_actions(self, request: Request) -> Response:
        """

        :param request:
        :return:
        """
        user_dict = await self._find_user_by_headers(request)
        actions = await self.db.collection_scopes.list_all_actions(user_dict["scopes"])
        return Response(200, actions, {"content-type": "application/json"})

    async def get_authenticate_mode(self, _) -> Response:
        """

        :return:
        """
        idp_configs = await self.db.get_idp_configs(projection={'idp_type': True, 'idp_name': True, 'idp_label': True})
        # deny_access is automatically added in ldap.to_dict(), it can be returned because not a sensitive data
        return Response(200, [item.to_dict() for item in idp_configs], {"content-type": "application/json"})

    @staticmethod
    def fill_api_descriptor(app_api_json: DictWithDefault, api_descriptor: ApiDescriptor,
                            subapp_path: str = "", main_def: dict = None, validation: bool = False) -> None:
        """
        Add API of main app or subapp
        Args:
            app_api_json (DictWithDefault): API definition in JSON format
            api_descriptor (ApiDescriptor): API descriptor to fill
            subapp_path (str, optional): Path of the subapp, if any. Defaults to "".
            main_def (dict, optional): Main API definition, if subapp. Defaults to None.
            validation (bool, optional): Whether to validate the API definition or not. Defaults to False.
        Raises:
            HTTPBadRequest: If the API definition is invalid or if there is an error during parsing.
            HTTPInternalServerError: If there is an internal error while populating scopes and actions.
        """

        # Convert the app_api_json from DictWithDefault to a (Python) dict to use yaml.dump
        app_api_json = json.loads(json.dumps(app_api_json))

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as tmp_file:
            tmp_file.write(yaml.dump(app_api_json, Dumper=yaml.CSafeDumper))
            tmp_file.flush() # using CSafeDumper, we need to flush the file to ensure it's written
            try:
                api_definition_yaml = OpenApiDefinition(tmp_file.name, full_validation=validation)
            except Exception as error:
                raise HTTPBadRequest(data=f"Query content error : {error}") from error
            try:
                parse_scopes_and_actions(api_descriptor, api_definition_yaml, subapp_path, main_def)
            except Exception as exception:
                LOG.warning("Fail to parse scope and actions, got %s", exception)
                raise HTTPInternalServerError(data="Internal error while populating scopes and actions") from exception

    async def post_api_definition(self, request: Request) -> Response:
        # pylint: disable=too-many-branches,too-many-locals,too-many-nested-blocks
        """
        Define an API
        :param request:
        :return: Response
        """
        prefix = ""
        try:
            prefix = request.body['main_api']['info']['x-auth']['prefix']
        except Exception as e:
            raise HTTPBadRequest(data="'main_api.info.x-auth.prefix' is a required property") from e
        if not 'base_url' in request.body:
            raise HTTPBadRequest(data="'base_url' is a required property")

        api_descriptor = ApiDescriptor(prefix=prefix,
                                       url=request.body['base_url'],
                                       app_name=request.body.get('app_name'))

        # User management scopes and actions cannot be altered this way
        if api_descriptor.prefix != "usr":
            self.fill_api_descriptor(
                app_api_json=request.body['main_api'],
                api_descriptor=api_descriptor,
                validation=not request.parameters.get("disable_validation", False))

            if 'subapp_apis' in request.body:
                for subapp_api in request.body['subapp_apis']:
                    self.fill_api_descriptor(
                        app_api_json=subapp_api['definition'],
                        api_descriptor=api_descriptor,
                        subapp_path=subapp_api['path'],
                        main_def=request.body['main_api'],
                        validation=not request.parameters.get("disable_validation", False))

            await self.db.publish_api_descriptor(api_descriptor)
            return Response(201, "OK", {"content-type": "text/plain"})
        raise HTTPBadRequest(data="Can't update user management own api descriptor")

    async def delete_api_definition(self, request: Request) -> Response:
        """
        Delete scopes and actions linked to an API definition
        :param request:
        :return: Response
        """
        prefix = request.body.get("prefix")
        app_name = request.body.get("app_name")
        api_url = request.body.get("api_url")
        api_descriptor = None
        if prefix:
            api_descriptor = await self.db.collection_api_descriptors.get_by_prefix_app_name(prefix, app_name)
        else:
            api_descriptor = await self.db.collection_api_descriptors.get_by_url(api_url)
        if not api_descriptor:
            return Response(204, "No Content", {"content-type": "text/plain"})
        await self.db.delete_api_descriptor(api_descriptor)
        return Response(204, "No Content", {"content-type": "text/plain"})

    async def _generate_backup(self, updater: UserUpdater, file_name: str = None,
                               include_admin_credentials: bool = False) -> Tuple[bytes, str]:
        """
        Extract and write backup data into a file

        Args:
            updater (UserUpdater): The updater to use for exporting the data.
            file_name (str, optional): File name. Defaults to None.
            include_admin_credentials (bool, optional): Whether to include admin credentials. Defaults to False.

        Returns:
            Tuple[bytes, str]: A tuple containing the backup data as bytes and the export file name as a string.
        """
        current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        package_version = updater.get_package_version()
        default_file_name = f"user_management_{current_date}_{package_version}_{self.settings.release_name}"
        export_file_name = file_name if file_name else default_file_name
        # Skip collections List, default contains only admin collection
        skip_collections = [Collections.admin.name] if not include_admin_credentials else []

        file_content = await updater.export_full_configuration(skip_collections)

        data = None
        with io.BytesIO() as _file:
            with zipfile.ZipFile(_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                # Encode the JSON data to bytes and write it to the zipfile
                zip_file.writestr(f"{export_file_name}.json", json_util.dumps(file_content).encode())
            data = _file.getvalue()
        return data, export_file_name

    async def _import_backup(self, updater: UserUpdater, request: Request,
                             skip_collections: List[str], force_override: bool) -> None:
        """
        Import backup data

        Args:
            updater (UserUpdater): The updater to use for importing the data.
            request (Request): The request containing the backup data.
            skip_collections (List[str]): List of collections to skip during import.
            force_override (bool): Whether to force override existing data.
        """
        zip_f = zipfile.ZipFile(io.BytesIO(request.body), "r")
        for item in zip_f.infolist():
            raw_data = zip_f.read(item).decode('ascii')
            data = json_util.loads(raw_data)
            updater.validate_full_migration_file(
                full_configuration_file_content=data
            )
            LOG.info("Try to import full configuration")
            await updater.import_full_configuration(data, skip_collections, force_override)

    @log_activity("exported sync data", "failed to export sync data")
    async def get_sync_data(self, request: Request) -> Response:
        """
        Api to get data to synchronize
        Args
            request: Request
        Returns
            The appropriate response
        """
        data, export_file_name = await self._generate_backup(self.sync_updater)
        return Response(
            200,
            data=data,
            headers={
                "content-type": "application/zip",
                "content-disposition": f"attachment; filename=\"{export_file_name}.zip\""
            }
        )

    @log_activity("imported sync data", "failed to import sync data")
    async def import_sync_data(self, request: Request) -> Response:
        """
        Api to import data to synchronize
        Args
            request: Request
        Returns
            The appropriate response
        """
        skip_collections = [Collections.admin.name]
        await self._import_backup(self.sync_updater, request, skip_collections, force_override=True)
        return Response(200, "OK", {"content-type": "text/plain"})

    @log_activity("exported full configuration", "failed to export full configuration")
    async def export_full_configuration(self, request: Request) -> Response:
        """
        Api to get to export the full configuration
        Args
            request: Request
        Returns
            The appropriate response
        """
        export_file_name = request.parameters.get('file_name')
        include_admin_credentials = request.parameters.get('include_admin_credentials', False)
        data, export_file_name = await self._generate_backup(self.updater, export_file_name, include_admin_credentials)

        return Response(
            200,
            data=data,
            headers={
                "content-type": "application/octet-stream",
                "content-disposition": f"attachment; filename=\"{export_file_name}.zip\""
            }
        )

    @log_activity("imported full configuration", "failed to import full configuration")
    async def import_full_configuration(self, request: Request) -> Response:
        """

        Args
            request: Request

        Returns
            The appropriate response
        """
        include_admin_credentials = request.parameters.get('include_admin_credentials', False)
        force_override = request.parameters.get('force_override', False)
        skip_collections = [Collections.admin.name] if not include_admin_credentials else []
        await self._import_backup(self.updater, request, skip_collections, force_override)

        return Response(200, "OK", {"content-type": "text/plain"})

    async def post_auth_data(self, request: Request) -> Response:
        """

        Post auth data, the purpose of this endpoint is to update auth data.
        This will update update actions, scopes and api_descriptors passed in the request body
        in case of an event type 'ADDED' or 'MODIFIED'. And in the case of a 'DELETED', this
        will remove associated auth data.

        Args:
            request (Request): request object

        Returns:
            The appropriate response
        """
        content = request.body["content"]
        actions = [Action.from_dict(item) for item in content["actions"]]
        scopes = [Scope.from_dict(item) for item in content["scopes"]]
        api_descriptors = [ApiDescriptor.from_dict(item) for item in content["api_descriptors"]]

        if request.body["type"] in ("ADDED", "MODIFIED"):
            await self.db.update_auth_data(actions, scopes, api_descriptors)
        elif request.body["type"] == "DELETED":
            await self.db.remove_auth_data(actions, scopes, api_descriptors)

        return Response(
            200,
            data="OK",
            headers={
                "content-type": "text/plain"
            }
        )

    async def get_sessions(self, _) -> Response:
        """
        Returns the list of active sessions

        Returns:
            Response: The list of active sessions
        """
        _tokens = await self.db.collection_tokens.get_list()
        _sessions = []
        for _token in _tokens:
            user = await self.db.get_user_by_id(_token.user_id, internal_projection=True)
            if not user or user.get('internal'):
                continue
            _session = Session.generate(user, _token)
            _sessions.append(_session.as_dict())
        return Response(200, data=_sessions, headers={"content-type": "application/json"})

    @log_activity(
        success_message="deleted user session",
        failure_message="failed to delete user session",
    )
    async def disable_session(self, request: Request) -> Response:
        """
        Disable a session

        Args:
            request (Request): request object

        Returns:
            The appropriate response
        """
        _id = request.parameters["id"]
        _success_message = None
        _failure_message = None

        token_deleted = await self.db.collection_tokens.remove_by_object_id(_id)

        if token_deleted:
            # Retrieve the token owner
            user_dict = await self.db.get_user_by_id(token_deleted.user_id)
            if user_dict:
                # Owner found, complete the log activity message
                _extra = f"{user_dict['username']} session with ip {token_deleted.user_ip}"
                if token_deleted.started_date:
                    login_date = token_deleted.started_date.strftime("%Y-%m-%d %H:%M:%S")
                    _extra += f" and login date {login_date}"
                _success_message = f"deleted user {_extra}"
                _failure_message = f"failed to delete user {_extra}"

        if not token_deleted:
            http_error = HTTPNotFound(data="Session not found")
            if _failure_message:
                set_activity_log(http_error, message=_failure_message)
            raise http_error

        response = Response(200, data="OK", headers={"content-type": "text/plain"})
        if _success_message:
            set_activity_log(response, message=_success_message)
        return response
