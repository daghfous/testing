"""
user-management-ms main module
"""

import argparse
import logging
import ssl
from concurrent.futures import ThreadPoolExecutor

from asyncio import get_event_loop
from aiohttp import web

from ateme.um_backend.user_management import UserManagementApi
from ateme.um_backend.database import Database
from ateme.um_backend.ldap import configure_ldap
from ateme.um_backend.utils import create_async_pymongo_client
from ateme.um_backend.loggers import LOG, LOGLEVEL_CHOICES
from ateme.um_backend.parser import (
    CustomArgsParser,
    int_checker,
    boolean_checker
)
from ateme.um_backend.types import DEFAULT_SCOPES_PAGE_LIMIT
from ateme.log import CustomFormatter


def display_args(args: argparse.Namespace) -> str:
    """
    Display args
    """
    args_dict = vars(args)
    temp = "\n==== Settings ====\n"
    for key, value in args_dict.items():
        temp += "+ " + key.upper() + f": {value}\n"
    return temp


def main():
    """
    Main entrypoint

    :return:
    """
    # pylint: disable=too-many-statements
    parser = CustomArgsParser()
    parser.add_custom_argument(
        '--loglevel',
        help='Log level',
        env_name="LOGLEVEL",
        default=LOGLEVEL_CHOICES[3],
        choices=LOGLEVEL_CHOICES
    )
    parser.add_custom_argument(
        "--um-log-file",
        type=str,
        env_name="UM_LOG_FILE",
        help="File to stock log data"
    )
    parser.add_custom_argument(
        "--default-actions-path",
        type=str,
        help="Default actions file path (DEPRECATED: use --default-auth-data-path instead)",
        env_name="DEFAULT_ACTIONS_PATH"
    )
    parser.add_custom_argument(
        "--default-scopes-path",
        type=str,
        env_name="DEFAULT_SCOPES_PATH",
        help="Default scopes file path (DEPRECATED: use --default-auth-data-path instead)"
    )
    parser.add_custom_argument(
        "--default-users-paths",
        type=str,
        env_name="DEFAULT_USERS_PATH",
        help="Default users file path"
    )
    parser.add_custom_argument(
        "--default-descriptor-path",
        help="Default api descriptor file path "
             "(DEPRECATED: use --default-auth-data-path instead)"
    )
    parser.add_custom_argument(
        "--default-admin-path",
        type=str,
        env_name="DEFAULT_ADMIN_PATH",
        help="Default admin file path"
    )
    parser.add_custom_argument(
        "--default-auth-data-path",
        type=str,
        env_name="DEFAULT_AUTH_DATA_PATH",
        help="Default auth-data file path",
        action="append"
    )
    parser.add_custom_argument(
        "--default-level",
        type=str,
        env_name="DEFAULT_LEVEL",
        help="Default level"
    )
    parser.add_custom_argument(
        "--hostname",
        type=str,
        env_name="UM_API_HOST",
        default="0.0.0.0",
        help="Hostname"
    )
    parser.add_custom_argument(
        "--um-api-port",
        type=int,
        env_name="UM_API_PORT",
        default=80,
        help="UM API port "
    )
    parser.add_custom_argument(
        "--um-database-url",
        type=str,
        env_name="UM_DATABASE_URL",
        default="mongodb://localhost:27017",
        help="UM Database URL"
    )
    parser.add_custom_argument(
        "--ssl-cert",
        type=str,
        env_name="SSL_CERT",
        help="SSL certificate"
    )
    parser.add_custom_argument(
        "--ssl-key",
        type=str,
        env_name="SSL_KEY",
        help="SSL key"
    )
    parser.add_custom_argument(
        "--um-database-name",
        type=str,
        env_name="UM_DATABASE_NAME",
        default="users",
        help="UM database name"
    )
    parser.add_custom_argument(
        "--token-cleaning",
        type=int,
        env_name="TOKEN_CLEANING",
        default=86400,
        help="Token cleaning"
    )
    parser.add_custom_argument(
        "--max-number-failed-client-logins",
        type=int,
        env_name="MAX_NUMBER_FAILED_CLIENT_LOGINS",
        default=2000,
        help="Max number of failed client logins"
    )
    parser.add_custom_argument(
        "--release-name",
        type=str,
        env_name="RELEASE_NAME",
        default="unknown_release",
        help="Release name"
    )
    parser.add_custom_argument(
        "--deploying-with-pmf",
        type=boolean_checker,
        env_name="DEPLOYING_WITH_PMF",
        default=False,
        help="True if user management is deployed in a PMF environment"
    )
    parser.add_custom_argument(
        "--mongo-tls-cert-path",
        type=str,
        env_name="MONGO_TLS_CERT_PATH",
        help="Certificate that enables the communication to external database"
    )
    parser.add_custom_argument(
        "--executor-max-workers",
        type=int_checker(min_value=1, max_value=16),
        env_name="EXECUTOR_MAX_WORKERS",
        default=5,
        help="Max workers used by ThreadPoolExecutor"
    )
    parser.add_custom_argument(
        "--ldap-sync-period",
        type=int,
        env_name="LDAP_SYNC_PERIOD",
        default=86400,
        help="Ldap Sync Period"
    )
    parser.add_custom_argument(
        "--token-ip-validation",
        type=boolean_checker,
        env_name="UM_TOKEN_IP_VALIDATION",
        default=False,
        help="Flag to enable/disable the token ip validation (disabled by default)"
    )
    parser.add_custom_argument("--ldap-log-detail-level",
                               type=int,
                               env_name="LDAP_LOG_DETAIL_LEVEL",
                               default=0,
                               help="Ldap Log Detail Level, default to 0"
                               )
    parser.add_custom_argument("--ldap-network-timeout",
                               type=int,
                               env_name="LDAP_NETWORK_TIMEOUT",
                               default=10,
                               help="LDAP Network Timeout in seconds, " \
                               "default to 10 seconds"
                               )
    parser.add_custom_argument(
        "--scopes-page-limit",
        type=int,
        env_name="SCOPES_PAGE_LIMIT",
        default=DEFAULT_SCOPES_PAGE_LIMIT,
        help="Maximum number of scopes that can be returned in a single page"
    )
    args = parser.parse_args()

    # Configure logger
    LOG.setLevel(args.loglevel)
    LOG.info(display_args(args))

    # Configure LDAP
    configure_ldap(log_detail_level=args.ldap_log_detail_level,
                   network_timeout=args.ldap_network_timeout)

    # LOG File
    if args.um_log_file:
        file_handler = logging.handlers.WatchedFileHandler(
            args.um_log_file,
            mode='a',
            encoding=None,
            delay=False
        )
        # create formatter and add it to the handler
        file_handler.setFormatter(CustomFormatter.build_default())
        # Add handler to the LOG
        LOG.addHandler(file_handler)

    client = create_async_pymongo_client(
        args.um_database_url,
        connect_timeout_ms=1000,
        server_selection_timeout_ms=5000,
        mongo_tls_cert_path=args.mongo_tls_cert_path
    )

    ssl_context = None
    if args.ssl_cert and args.ssl_key:
        LOG.debug("SSL_CERT: %s\nSSL_KEY: %s", args.ssl_cert, args.ssl_key)
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(args.ssl_cert, args.ssl_key)

    # Create a thread pool
    executor = ThreadPoolExecutor(max_workers=args.executor_max_workers)

    LOG.info("Starting...")
    loop = get_event_loop()
    database = Database(client, args.um_database_name)
    api = UserManagementApi(
        database=database,
        settings=args,
        executor=executor,
        service='user-ms',
        origin='origin'
    )

    # Add %Tf time taken to serve response in second
    access_log_format = '%a %t %Tfs "%r" %s %b "%{Referer}i" "%{User-Agent}i"'
    web.run_app(
        api.app,
        host=args.hostname,
        port=args.um_api_port,
        ssl_context=ssl_context,
        access_log=LOG,
        access_log_format=access_log_format,
        loop=loop
    )
    executor.shutdown(cancel_futures=True)  # shutdown the thread pool
    api.web_application.cleanup().close()
    LOG.info("End! Bye Bye.")


if __name__ == "__main__":
    main()
