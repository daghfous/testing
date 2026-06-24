"""
Test um
"""
import os
import tempfile
import tarfile
import time
import binascii
import ssl
from queue import SimpleQueue
from concurrent.futures import ThreadPoolExecutor
from base64 import b64decode, b64encode
from logging import getLogger, handlers
from unittest.mock import AsyncMock
from urllib.parse import urlparse
from typing import Callable, Generator, TypeVar
from datetime import datetime, timedelta
import ldap
from ldap import modlist
from aiohttp.test_utils import TestClient
from aiohttp.web_app import Application
import docker
import pytest
import pytest_asyncio
from requests import HTTPError
from pymongo import AsyncMongoClient
from lxml import etree
from _pytest.fixtures import SubRequest
from pytest_mock.plugin import MockerFixture
from ateme.um_backend.user_management import UserManagementApi, MIGRATION_FILE
from ateme.um_backend.database import Collections
from ateme.encryption_lib import AESCipher  # pylint: disable=no-name-in-module
from ateme.um_backend import (
    Database,
    LdapTlsConfig,
    LdapConfig,
    IdpType
)
from ateme.um_backend.types import (
    Token,
    DEFAULT_SCOPES_PAGE_LIMIT
)
from ateme.um_backend.ldap import LdapClient
from ateme.um_backend.updater import UserUpdater
from ateme.api_tests_tools import (
    start_db,
    wait_for_db,
    stop_db,
    clean_db,
    get_free_port
)
from ateme.um_backend.loggers import LOG_ACTIVITY

# Get system CA directory from Python/OpenSSL defaults
ca_dir = ssl.get_default_verify_paths().capath

# Set python-ldap to use it
ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, ca_dir) # pylint: disable=no-member

T = TypeVar("T")
YieldFixture = Generator[T, None, None]

if not os.environ.get("DATABASE_HOST"):
    os.environ["DATABASE_HOST"] = "127.0.0.1"
if not os.environ.get("API_HOST"):
    os.environ["API_HOST"] = "127.0.0.1"
DATABASE_PORT = str(get_free_port())
DATABASE_NAME = "users"

MONGO_IMAGE = 'nexus-rennes.ateme.net:10443/services/mongo'
MONGO_TAG = '7.0.5'

ADMIN_USER = {"username": "admin",
              "password": "adminAAA0!"}
INTERNAL_ADMIN_USER = {"username": "internal_admin",
                       "password": "5c6845f876cf943ae7eb3f52705f804c"}
# User with admin rights
ADMIN_LIKE_USER = {"username": "admin_user",
                   "password": "adminAAA0!"}

API_PATH = os.path.join(os.path.dirname(__file__), "definitions", "simple_api.yaml")
USR_API_PATH = os.path.join(os.path.dirname(__file__), "definitions", "simple_api_usr.yaml")
SUBAPP_API_PATH = os.path.join(os.path.dirname(__file__), "definitions", "subapp_simple_api.yaml")
VERY_LONG_API_PATH = os.path.join(os.path.dirname(__file__), "definitions", "very_long_api.json")
DB_URL_ENV = "mongodb://" + os.environ["DATABASE_HOST"] + ':' + DATABASE_PORT + "/?directConnection=true"

LOG = getLogger(__name__)

@pytest.fixture(name="admin_user")
def _admin_user() -> YieldFixture[dict]:
    """

    Admin user credential fixture.
    """
    yield ADMIN_USER


@pytest.fixture(name="internal_admin_user")
def _internal_admin_user() -> YieldFixture[dict]:
    """

    Internal admin user credential fixture.
    """
    yield INTERNAL_ADMIN_USER


class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


@pytest.fixture(name="api_path")
def _api_path() -> str:
    """

    api_path fixture
    :return:
    """
    return API_PATH


@pytest.fixture(name="usr_api_path")
def _usr_api_path() -> YieldFixture[str]:
    """

    api_path fixture
    :return:
    """
    yield USR_API_PATH


@pytest.fixture(name="subapp_api_path")
def _subapp_api_path() -> YieldFixture[str]:
    """

    api_path fixture
    :return:
    """
    yield SUBAPP_API_PATH

@pytest.fixture(name="very_long_api_path")
def _very_long_api_path() -> YieldFixture[str]:
    """

    Very long api path fixture
    We took the API of Titan File for reference

    Yields:
        str: Path to the very long API definition file.
    """
    yield VERY_LONG_API_PATH

# Command line options
@pytest.fixture(scope="session", name="keep_containers")
def _keep_containers(pytestconfig) -> YieldFixture[bool]:
    """

    Keep containers fixture, retrieve from arg.
    """
    yield pytestconfig.getoption("--keep-containers")


@pytest.fixture(scope="session", name="remote_database_url")
def _remote_database_url(pytestconfig) -> YieldFixture[str]:
    """

    Remote database url fixture, retrieve from arg.
    """
    yield pytestconfig.getoption("--remote-database-url")


@pytest.fixture(scope="session", name="database_name")
def _database_name(pytestconfig) -> YieldFixture[str]:
    """

    Remote database name fixture, retrieve from arg.
    """
    yield pytestconfig.getoption("--database-name")


@pytest.fixture(scope="session", name="no_pull_image")
def _no_pull_image(pytestconfig) -> YieldFixture[bool]:
    """

    Don't pull image, retrieve from arg.
    """
    yield pytestconfig.getoption("--no-pull-image")


@pytest.fixture(scope="session", name="wait_database_timeout")
def _wait_database_timeout(pytestconfig) -> YieldFixture[int]:
    """

    Wait database initialize timeout fixture, retrieve from arg.
    """
    yield pytestconfig.getoption("--wait-database-timeout")


def pytest_addoption(parser):
    """

    Pytest custom arguments:
    """
    parser.addoption(
        "--keep-containers",
        action="store_true",
        default=False,
        help="Keep containers after tests suite finish. Default: False",
    )
    parser.addoption(
        "--no-pull-image",
        action="store_true",
        default=False,
        help="Don't pull mongodb image, default: False",
    )
    parser.addoption(
        "--remote-database-url",
        action="store",
        default=None,
        help="Database remote url, if set no database container will be created at setup. Default: None",
    )
    parser.addoption(
        "--database-name",
        action="store",
        default=DATABASE_NAME,
        help=f"Database remote name. Default: {DATABASE_NAME}",
    )
    parser.addoption(
        "--wait-database-timeout",
        action="store",
        default=30,
        help="Wait database replicaset init in seconds. Default 30",
    )


@pytest.fixture(scope='session', name="init_database_container")
def _init_database_container(
    remote_database_url: str,
    database_name: str,
    keep_containers: bool,
    wait_database_timeout: int,
    no_pull_image: bool,
) -> YieldFixture[str]:
    """

    init database container fixture
    Args:
        remote_database_url (str): Remote Database URL, if set no container started
        keep_containers (bool): Keep containers at test session teardown
        wait_database_timeout (int): Wait database timeout
    """
    db_host = None
    db_container = None

    if not remote_database_url:
        database_port = urlparse(DB_URL_ENV).port
        LOG.info("Start DB container (image: %s:%s)", MONGO_IMAGE, MONGO_TAG)
        db_host, db_container = start_db(
            database_port,
            replicaset=True,
            image_name=MONGO_IMAGE,
            image_tag=MONGO_TAG,
            pull_image=not no_pull_image,
        )

    # Let the DB initializing (60s timeout)
    LOG.info("Wait database %s init", remote_database_url or DB_URL_ENV)
    wait_for_db(remote_database_url or DB_URL_ENV, wait_database_timeout, replicaset=True)

    # Usefull to need if we have to clean database because remote db
    if bool(remote_database_url):
        LOG.info("Drop database %s", database_name)
        clean_db(remote_database_url, database_name)

    yield remote_database_url or DB_URL_ENV

    # Remove container if --keep-containers args not used and --database-url not set.
    if not keep_containers and not bool(remote_database_url):
        LOG.info("Stop DB container")
        stop_db(db_host, db_container)


@pytest_asyncio.fixture(scope="function", name="init_database")
async def _init_database(
    init_database_container: str, database_name: str, request: SubRequest
) -> YieldFixture[Database]:
    """

    Return db instance, at teardown drop database.
    """
    params = {}
    if hasattr(request, "param"):
        params = request.param

    client = AsyncMongoClient(init_database_container,
                                      socketTimeoutMS=1000,
                                      connectTimeoutMS=1000,
                                      serverSelectionTimeoutMS=1000)
    _db = Database(client, database_name)

    if params.get("initialize", True):
        await _db.initialize()

    yield _db

    LOG.info("Drop database %s", database_name)
    await _db.db.client.drop_database(database_name)
    await client.close()


@pytest_asyncio.fixture(scope="function", name="populate_data")
async def _populate_data(init_database: Database, request: SubRequest) -> YieldFixture[None]:
    """

    This fixture help to populate data from parametrize before run unit test.
    """
    if not hasattr(request, "param"):
        return
    data = request.param
    for collection_name, docs in data.items():
        insert_result = await init_database.db[collection_name].insert_many(docs)
        LOG.info("Insert data into %s collection, result: %s", collection_name, insert_result)

    yield


@pytest.fixture(scope="function", name="settings")
def _settings(remote_database_url: str, database_name: str, request: SubRequest) -> YieldFixture[DotDict]:
    """
    Settings init fixture, settings value can be customize via parametrize. Input expected is a dict
    with key as settings attribute to set and value as new value for this settings.
    """
    settings_object = DotDict({
        "um_database_url" : remote_database_url or DB_URL_ENV,
        "um_database_name": database_name,
        "mongo_tls_cert_path": None,
        "token_cleaning": 86400,
        "max_number_failed_client_logins": 5,
        "release_name": "unknown_release",
        "deploying_with_pmf": False,
        "executor_max_workers": 5,
        "loglevel": "DEBUG",
        "default_level": None,
        "default_descriptor_path": None,
        "default_users_paths": None,
        "default_scopes_path": None,
        "default_actions_path": None,
        "default_admin_path": None,
        "ldap_sync_period": 86400,
        "token_ip_validation": False,
        "scopes_page_limit": DEFAULT_SCOPES_PAGE_LIMIT
    })
    if hasattr(request, "param"):
        for key, val in request.param.items():
            setattr(settings_object, key, val)

    getLogger('um_backend').setLevel(settings_object.loglevel)
    yield settings_object


@pytest_asyncio.fixture(scope="function", name="init_api")
async def _init_api(settings: DotDict, init_database: Database) -> YieldFixture[UserManagementApi]:
    """

    Initialize UserManagementApi and yield it.
    """
    db = init_database
    executor = ThreadPoolExecutor(max_workers=settings.max_workers)
    LOG.info("Init UserManagementApi and web application")
    api = UserManagementApi(
        database=db, settings=settings, executor=executor, service="service", origin="origin", validate_response=True
    )
    # Set PMF Release Name for tests
    api.settings.release_name = "pmf-release-name"
    yield api


@pytest_asyncio.fixture(scope="function", name="multiple_api")
async def _multiple_api(
    settings: DotDict, init_database: Database, request: SubRequest
) -> YieldFixture[list[UserManagementApi]]:
    """

    Initialize multiple UserManagementApi and yield it.
    """
    db = init_database
    apis = []
    for _ in range(request.param):
        executor = ThreadPoolExecutor(max_workers=settings.max_workers)
        LOG.info("Init UserManagementApi and web application")
        api = UserManagementApi(
            database=db, settings=settings, executor=executor, service="service", origin="origin",
            validate_response=True
        )
        apis.append(api)

    yield apis


@pytest_asyncio.fixture(scope="function", name="init_backend")
async def _init_backend(
    init_api: UserManagementApi,
    aiohttp_client: Callable[[Application], TestClient],
    request: SubRequest,
) -> YieldFixture[tuple[TestClient, UserManagementApi]]:
    """

    Initialize web application and aiohttp_client, thanks to pytest-aiohttp.
    A TestClient will be return and UserManagementApi instance.
    """
    params = {}
    if hasattr(request, "param"):
        params = request.param

    if params.get("mock_initialize", False):
        init_api.initialize = None
        init_api.finalize = None

    if params.get("db_initialize", False):
        await init_api.db.initialize()

    return (await aiohttp_client(init_api.web_application), init_api)


@pytest_asyncio.fixture(scope="function", name="init_backend_with_admin")
async def _init_backend_with_admin(
    init_backend: TestClient,
    admin_user: dict
) -> YieldFixture[tuple[TestClient, UserManagementApi, str]]:
    """

    This fixture create and login admin user from admin_user fixture credentials
    Return http client instance, UserManagementApi instance and token freshly retrieve.
    """
    _cli, _api = init_backend
    LOG.info("Create admin user")
    admin_created = await _cli.post("/admin", json=admin_user)
    assert admin_created.status == 201

    LOG.info("Login admin user")
    login_resp = await _cli.post("/token", json=admin_user)
    assert login_resp.status == 200
    token_body = await login_resp.json()

    yield _cli, _api, token_body["access_token"]


@pytest_asyncio.fixture(scope="function", name="init_backend_with_internal_admin")
async def _init_backend_with_internal_admin(
    init_backend: TestClient,
    internal_admin_user: dict
) -> YieldFixture[tuple[TestClient, UserManagementApi, str]]:
    """

    This fixture create and login internal admin user from internal_admin_user fixture credentials
    Return http client instance, UserManagementApi instance and token freshly retrieve.
    """
    _cli, _api = init_backend
    LOG.info("Login internal admin user")
    login_resp = await _cli.post("/token", json=internal_admin_user)
    assert login_resp.status == 200
    token_body = await login_resp.json()

    yield _cli, _api, token_body["access_token"]


@pytest_asyncio.fixture(scope="function", name="create_users")
async def _create_users(
    init_backend_with_admin: tuple[TestClient, UserManagementApi, str],
    request: SubRequest
) -> YieldFixture[list[dict]]:
    """

    Create users fixture is a helpers to create users before running unit test.
    Users created are retrieve from parametrize as a list of user object.
    """
    init_backend, _, admin_token = init_backend_with_admin

    users = []

    if hasattr(request, "param"):
        users = request.param

    for user in users:
        create_resp = await init_backend.post(
            "/v2/users", json=user, headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert (
            create_resp.status == 201
        ), f"Failed to create user {user['username']}, status: {create_resp.status} body: {await (create_resp.text())}"

    yield users


@pytest_asyncio.fixture(scope="function", name="create_and_log_users")
async def _create_and_log_users(
    init_backend_with_admin: tuple[TestClient, UserManagementApi, str],
    admin_user: dict,
    request: SubRequest
) -> YieldFixture[dict[str, dict]]:
    """

    This fixture will create and log users, same as create_users users are retrieve from parametrize.
    """
    init_backend, _, admin_token = init_backend_with_admin

    results: dict[str, dict] = {admin_user["username"]: {"credential": admin_user, "token": admin_token}}

    users = []

    if hasattr(request, "param"):
        users = request.param

    for user in users:
        LOG.info("Create user %s", user["username"])
        create_resp = await init_backend.post(
            "/v2/users", json=user, headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_resp.status == 201
        LOG.info("Log user %s", user["username"])
        login_resp = await init_backend.post(
            "/token", json={"username": user["username"], "password": user["password"]}
        )
        assert login_resp.status == 206
        results[user["username"]] = {"credential": user, "token": (await login_resp.json())["access_token"]}

    yield results

@pytest.fixture(name="init_ldap_server")
def _init_ldap_server() -> YieldFixture[tuple[str, str, dict]]:
    """
    Initialize a temporary OpenLDAP server container for testing.

    This fixture sets up an LDAP server using a Docker container with the
    following steps:

    1. Creates a temporary directory to store generated certificates.
    2. Configures LDAP environment variables, including admin password,
       base DN, and domain.
    3. Starts an OpenLDAP Docker container with optional TLS support.
    4. Copies the generated certificate, key, and CA files from the container
       to the temporary directory.
    5. Configures a LdapClient instance to connect to the server.
    6. Generates a test user's encrypted password.

    The fixture yields a tuple containing:
        - hostname (str): The hostname of the LDAP server.
        - server (LdapClient): Configured LDAP client instance.
        - config (dict): Dictionary containing admin and test user credentials,
                         encrypted password, base DN, and group information.

    Cleanup:
        Stops and removes the LDAP container after the test completes.

    """
    # Deactivate cert validation and activate debug logging for
    # local testing using the image osixia/openldap
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER) # pylint: disable=no-member
    ldap.set_option(ldap.OPT_DEBUG_LEVEL, 255) # pylint: disable=no-member

    temp_dir = tempfile.TemporaryDirectory()
    hostname = os.environ.get("LDAP_HOST", "localhost")
    admin_password = "oiZai7iureijuho!"
    username = "bidule"
    user_password = "SaibahxeeL8quaR!"
    # base distinguished name
    # descend the tree from left to right
    base_dn = "dc=ateme,dc=test"
    ldap_env = {
        "LDAP_ORGANISATION": "Ateme test",
        "LDAP_DOMAIN": "ateme.test",
        "LDAP_ADMIN_PASSWORD": admin_password,
        "LDAP_BASE_DN": base_dn,
        "LDAP_TLS": "true",
        "LDAP_TLS_VERIFY_CLIENT": "try",  # allows self-signed certs
    }
    ldap_container = start_ldap_server(hostname,
                                       cert_dir=temp_dir,
                                       env=ldap_env)
    ldap_tls_config = LdapTlsConfig(certificate_file=os.path.join(temp_dir.name, "ldap.crt"),
                                    private_key_file=os.path.join(temp_dir.name, "ldap.key"),
                                    ca_certs_file=os.path.join(temp_dir.name, "ca.pem"))

    group_name = "S_SUPPORT"
    config = LdapConfig(idp_type=IdpType.ldap.name,
                        idp_label='LDAP ateme.com',
                        idp_name='ldap_ateme.com',
                        server=hostname,
                        search=base_dn,
                        group=group_name,
                        use_ssl=True,
                        tls_config=ldap_tls_config)
    server = LdapClient(config)
    # Generate encrypt password
    _, output = ldap_container.exec_run(["slappasswd", "-s", user_password])
    yield hostname, server, {"admin": {"username": f"cn=admin,{base_dn}",
                                       "password": admin_password},
                             "user": {"username": f"uid={username},ou={group_name},{base_dn}",
                                      "password": user_password,
                                      "given_name": "Bidule",
                                      "sn": "bidule"},
                             "encrypt_password": output.decode().strip(),
                             "base_dn": base_dn,
                             "group": group_name}
    ldap_container.stop()
    ldap_container.remove(force=True, v=True)

@pytest.fixture(name="init_ldap_server_with_user")
def _init_ldap_server_with_user(init_ldap_server):
    """
    Initialize the LDAP server fixture with a test user and a group.

    This fixture depends on `init_ldap_server`, which sets up a base LDAP
    container with admin credentials. It extends that setup by:

    1. Binding to the LDAP server using the admin credentials.
    2. Creating an organizational unit (OU) for the test group.
    3. Adding a test user under that group with necessary attributes.
    4. Adding an additional user entry for testing purposes.

    Args:
        init_ldap_server (tuple): The base LDAP server fixture, which yields
            (hostname, LdapClient instance, configuration dict).

    Yields:
        tuple: The same values as `init_ldap_server` but with the added users.
    """
    _, server, config = init_ldap_server
    # Need bind to init ldap connection
    conn = server.bind(config["admin"]["username"], config["admin"]["password"])
    # Add group (organisation unit in ldap)
    ou_dn = f"ou={config['group']},{config['base_dn']}"
    ou_attrs = {
        "objectClass": [b"organizationalUnit"],
        "ou": [config["group"].encode()],
    }
    conn.add_s(ou_dn, modlist.addModlist(ou_attrs))
    # Add user
    user_dn = config["user"]["username"]
    user_attrs = {
        "objectClass": [b"top", b"posixAccount", b"inetOrgPerson"],
        "userPassword": [config["encrypt_password"].encode()],
        "cn": [config["user"]["username"].encode()],
        "uidNumber": [b"14583102"],
        "gidNumber": [b"14564100"],
        "sn": [b"3"],
        "homeDirectory": [f"/home/{config['user']['username']}".encode()],
    }
    conn.add_s(user_dn, modlist.addModlist(user_attrs))
    # Add another user
    other_dn = f"cn=other,{config['base_dn']}"
    other_attrs = {
        "objectClass": [b"organizationalRole", b"simpleSecurityObject"],
        "userPassword": [config["encrypt_password"].encode()],
        "cn": [b"other"],
    }
    conn.add_s(other_dn, modlist.addModlist(other_attrs))

    yield init_ldap_server

def start_ldap_server(hostname: str, # pylint: disable=too-many-positional-arguments,too-many-arguments
                      image_name: str = "nexus-rennes.ateme.net:10443/osixia/openldap",
                      image_tag: str = "1.5.0",
                      container_name: str = None,
                      cert_dir: str = "/tmp",
                      env: dict = None):
    """
    Start an OpenLDAP server container (osixia/openldap) and optionally obtain TLS artifacts.

    This helper runs an OpenLDAP docker container and, when TLS is enabled in the container,
    waits briefly for the container to generate certificates and copies the generated
    certificate files (ca.crt, ldap.crt, ldap.key) from the container to the given cert_dir.

    Args:
        hostname (str): Hostname used by the LDAP container. IMPORTANT: the container uses
            this hostname when generating certificates, so provide the expected hostname to
            get certificates valid for that name.
        image_name (str): Docker image name to use (default: "nexus-rennes.ateme.net:10443/osixia/openldap").
        image_tag (str): Docker image tag to use (default: "1.5.0").
        container_name (str | None): Optional name for the created container. If not provided
            a name is generated using BUILD_NUMBER or the current USER.
        cert_dir (str | tempfile.TemporaryDirectory): Destination directory (or TemporaryDirectory
            object) where the certificate files will be written. If a TemporaryDirectory is
            passed, its .name attribute is used.
        env (dict | None): Environment variables passed to the container (for example:
            LDAP_ADMIN_PASSWORD, LDAP_BASE_DN, LDAP_TLS, LDAP_TLS_VERIFY_CLIENT, ...).

    Returns:
        docker.models.containers.Container: The running container instance.

    Notes:
        - The function maps container ports 389 and 636 to the same host ports by default.
        - The container must be allowed a short delay to generate certificates; this function
          performs a fixed sleep before attempting to copy cert files.
        - Caller is responsible for stopping/removing the returned container when no longer needed.
    """
    docker_client = docker.from_env()

    if not container_name:
        suffix = (
            "build_" + os.environ["BUILD_NUMBER"]
            if "BUILD_NUMBER" in os.environ
            else os.environ.get("USER", "test")
        )
        container_name = f"ldap_server_unittest_{suffix}"

    # Ensure any previous container is removed
    try:
        container = docker_client.containers.get(container_name)
        if container:
            container.remove(force=True)
    except HTTPError:
        # container not exist
        pass

    # Run the container
    full_image_name = f"{image_name}:{image_tag}"
    ldap_container = docker_client.containers.run(full_image_name,
                                                  name=container_name,
                                                  detach=True,
                                                  hostname=hostname,
                                                  environment=env,
                                                  ports={"636": "636",
                                                         "389": "389"})
    # Dynamically wait and copy TLS certificates
    copy_from_container_with_wait(
        ldap_container,
        "/container/service/slapd/assets/certs/ca.crt",
        os.path.join(cert_dir.name, "ca.pem")
    )
    copy_from_container_with_wait(
        ldap_container,
        "/container/service/slapd/assets/certs/ldap.key",
        os.path.join(cert_dir.name, "ldap.key")
    )
    copy_from_container_with_wait(
        ldap_container,
        "/container/service/slapd/assets/certs/ldap.crt",
        os.path.join(cert_dir.name, "ldap.crt")
    )

    return ldap_container

def copy_from_container_with_wait(container, src, dst, timeout=15):
    """
    Wait for the file to exist in the container and then copy it to host.

    Args:
        container: Docker container instance.
        src: Path inside container.
        dst: Path on host.
        timeout: Max seconds to wait for the file
    """
    wait_for_cert(container, src, timeout=timeout)
    copy_from_container(container, src, dst)

def wait_for_cert(container: docker.models.containers.Container, path: str, timeout: int = 15, interval: float = 0.5):
    """
    Wait until the given file exists inside the container.
    Args:
        container: Docker container instance.
        path: File path inside the container.
        timeout: Max seconds to wait.
        interval: Seconds between checks.
    """
    start = time.time()
    while time.time() - start < timeout:
        ret = container.exec_run(["test", "-f", path])
        if ret.exit_code == 0:
            return True
        time.sleep(interval)
    raise TimeoutError(f"File {path} not found in container after {timeout} seconds")

def copy_from_container(container: docker.models.containers.Container,
                        src: str,
                        dst: str):
    """
    Copy a file or directory from a Docker container to the host filesystem.

    This function retrieves the specified file or directory from the given
    container, extracts it from the tar archive returned by Docker, and saves
    it to the destination path on the host.

    Args:
        container (docker.models.containers.Container): The Docker container
            object to copy from.
        src (str): The path of the file or directory inside the container.
        dst (str): The destination path on the host filesystem where the
            file or directory should be saved.
    Notes:
        - This function uses a temporary file and directory to handle the
          tar archive during extraction.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        data, _ = container.get_archive(src)
        _file = tempfile.NamedTemporaryFile(delete=False)
        for chunk in data:
            _file.write(chunk)
        _file.close()
        tar = tarfile.open(_file.name)
        tar.extractall(path=temp_dir)
        tar.close()
        filename = os.path.basename(src)
        os.rename(os.path.join(temp_dir, filename), dst)

def generate_internal_user_password(username: str) -> str:
    """
    generate of password from the username for an internal user
    :param username:
    :return:
    """
    encrypt_username = b64decode(AESCipher().encrypt(username).decode('utf-8'))
    encrypt_username = binascii.hexlify(encrypt_username).decode("utf-8")
    password = f"Ateme@{encrypt_username}"
    return password


@pytest_asyncio.fixture(scope="function", name="populate_with_data_from_4_0")
async def _populate_with_data_from_4_0(request, updater) -> YieldFixture[None]:
    """

    Populate data fixture
    """
    # Clean actions, scopes, users, ldap_config & configuration collections
    await updater.db.initialize()
    # Populate with input define in parametrize (via indirect)
    for collname, data in request.param.items():
        await updater.db.db[collname].insert_many(data)
    yield

    await updater.db.db[Collections.actions.name].delete_many({})
    await updater.db.db[Collections.scopes.name].delete_many({})
    await updater.db.db[Collections.users.name].delete_many({})
    await updater.db.db[Collections.idp_config.name].delete_many({})
    await updater.db.db[Collections.configuration.name].delete_many({})


@pytest.fixture(name="updater")
def _updater(init_database, settings) -> YieldFixture[UserUpdater]:
    """

    Updater fixture, need settings to init logger.
    """
    yield UserUpdater(init_database, migration_file=MIGRATION_FILE)


@pytest.fixture(name="saml_payload")
def _saml_payload(request) -> YieldFixture[str]:
    """

    Craft SAML response payload, can add custom attribute via `request.param`
    with the format: `{"attributes": [{"attribute_name": "scopes", "attribute_value": "admin"}`
    """
    # pylint: disable=c-extension-no-member
    etree.register_namespace("saml", "urn:oasis:names:tc:SAML:2.0:assertion")
    root = etree.parse(open(os.path.join(os.path.dirname(__file__), "saml_payload", "okta_saml_response.xml"),
                            "r", encoding="utf-8"))
    namespaces = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
    destination = root.xpath("//saml:AttributeStatement", namespaces=namespaces)[0]
    for attribute in request.param.get("attributes", {}):
        attribute_name = attribute["name"]
        attribute_value = attribute["value"] if isinstance(attribute["value"], list) else [attribute["value"]]
        _attribute_value_element = "".join([
            f'<saml:AttributeValue xsi:type="xs:string">{item}</saml:AttributeValue>'
            for item in attribute_value
        ])
        destination.insert(
            0,
            etree.fromstring(
                f'<saml:Attribute xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"'
                f' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema"'
                f' Name="{attribute_name}" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">'
                f'{_attribute_value_element}</saml:Attribute>'
            ),
        )
    yield b64encode(etree.tostring(root)).decode()


@pytest.fixture(name="mocks_func")
def _mocks_func(mocker: MockerFixture, request: SubRequest) -> YieldFixture[dict[str, AsyncMock]]:
    """

    The goal of this fixture is to facilitate mocking of database call
    by example. Define in parametrize function to mock with the following format:
    {"path.to.myfunction": {"side_effect": Exception("Boom")}}
    Patched functions are collection into a dictionnary yield from
    this fixture, this will allow to check that function have been
    called.

    Args:
        mocker (MockerFixture): Mocker fixture, thanks to pytest-mock
        request (SubRequest): Sub request for handling getting a fixture from a test function/fixture.
    """
    mocks: dict[str, AsyncMock] = {}
    # Apply mock patch on every functions define in parametrize
    # mocks_func.
    for _mock_func, _mock_args in request.param.items():
        mocks[_mock_func] = mocker.patch(_mock_func, **_mock_args)

    yield mocks

    mocker.stopall()


@pytest.fixture(scope="function", name="internal")
def _internal(mocker, request) -> YieldFixture[bool]:
    """
    Internal fixture
    """
    token = Token(
        token="token",
        started_date=datetime.utcnow(),
        expiration_date=datetime.utcnow() + timedelta(hours=1),
        refresh_token="refresh_token",
        refresh_token_expiration_date=datetime.utcnow() + timedelta(hours=2),
        user_id="user"
    )
    mocker.patch('ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token', return_value=token)
    mocker.patch('ateme.um_backend.database.Database.get_user_by_id', return_value={'internal': request.param})

    yield request.param

def get_activity_log(q, handler) -> str:
    """
    Retrieve the activity log from the queue.

    Args:
        q (SimpleQueue): The queue containing log records.
        handler (QueueHandler): The handler associated with the log records.

    Returns:
        str: The log record retrieved from the queue.
    """
    LOG_ACTIVITY.removeHandler(handler)
    log_record = q.get_nowait()
    return log_record

def init_log_record():
    """
    Initialize activity log record and return the queue and handler.

    Returns:
        tuple: A tuple containing the queue and the handler.
    """
    q = SimpleQueue()
    handler = handlers.QueueHandler(q)
    LOG_ACTIVITY.addHandler(handler)
    return q, handler
