# pylint: disable=no-member,too-many-lines
"""
Unit test updater
"""
import hashlib
import os
import zipfile
import json
import io

import pytest
from bson import ObjectId, json_util
import pymongo
import pytest_asyncio

from ateme.updater.updater import find_collection
from ateme.um_backend import Configuration, PasswordPolicy
from ateme.um_backend.database import Collections, UpdateFilterKeyError
from ateme.um_backend.types import (
    User,
    Scope,
    Action,
    IdpType,
    LdapConfig,
    IdpLocalConfig,
    DEFAULT_LOCAL_IDP_NAME
)
from ateme.updater import (
    InvalidMigrationFileException,
    InvalidHash,
    VersionNotFound,
)

from .migration_test_files.types.ldap_config_4_0 import LdapConfig as LdapConfig_4_0

MIGRATION_VALIDATION_SCHEMA = "../ateme/um_backend/api/definitions/migration/migration_schema.yaml"
COLLECTION_VALIDATION_SCHEMA = "../ateme/um_backend/api/definitions/migration/migration_collection_schema.yaml"
FULL_CONFIGURATION_VALIDATION_SCHEMA = "../ateme/um_backend/api/definitions/migration/full_configuration_schema.yaml"

USER_JOE = User(creation_id=ObjectId(), username='Joe', password='123456', scopes=[], idp_name=DEFAULT_LOCAL_IDP_NAME)
USER_JIM = User(creation_id=ObjectId(), username='Jim', password='123456', scopes=[], idp_name=DEFAULT_LOCAL_IDP_NAME)
USER_BILL = User(creation_id=ObjectId(), username='Bill', password='123456', scopes=[])
INTERNAL_USER = User(creation_id=ObjectId(), username='TE_zerfgter51_14', password='123456',
                     scopes=[], internal=True)

SCOPE_1 = Scope(id='usr:actor', label="Actor", version=3,
                content=[])
SCOPE_2 = Scope(id='usr:director', label="Director", version=3,
                content=[])
INTERNAL_USER_SCOPE = Scope(id='usr:internal_user',
                            content=[{"action": "usr:get_internal_users_test_db",
                                      "policy": "allow", "resource": {}},
                                     {"action": "usr:add_internal_users_test_db",
                                      "policy": "allow", "resource": {}}],
                            internal=True)
IDP_LOCAL_CONFIG = IdpLocalConfig()
IDP_LDAP_CONFIG_1 = LdapConfig(idp_type=IdpType.ldap.name, idp_name='ldap_ateme.com',
                               domain='ateme.com', server='atm-infra.corp.ateme.com',
                               search='CN=Users,DC=corp,DC=ateme,DC=com', group='S_SUPPORT')
IDP_LDAP_CONFIG_2 = LdapConfig(idp_type=IdpType.ldap.name, idp_name='ldap_ateme-velizy.com',
                               idp_label='Ldap ateme-velizy.com', domain='ateme-velizy.com',
                               server='atm-extra.corp.ateme.com',
                               search='CN=Users,DC=corp,DC=ateme,DC=com', group='S_SUPPORT')
LDAP_CONFIG_4_0_1 = LdapConfig_4_0(domain='ateme.com', server='atm-infra.corp.ateme.com',
                                   search='CN=Users,DC=corp,DC=ateme,DC=com', group='S_SUPPORT')
LDAP_CONFIG_4_0_2 = LdapConfig_4_0(domain='ateme-velizy.com', server='atm-extra.corp.ateme.com',
                                   search='CN=Users,DC=corp,DC=ateme,DC=com', group='S_SUPPORT')

PASSWORD_POLICY = PasswordPolicy(expiration_delay_in_days=9999)
CONFIGURATION = Configuration(password_policy=PASSWORD_POLICY)

MIGRATION_FILE = os.path.join(os.path.dirname(__file__),
                              "..", "ateme", "um_backend", "migration_files", "um_migration.json")
MIGRATION_BASE_DIR = os.path.join(os.path.dirname(__file__),
                                  "..", "ateme", "um_backend", "migration_files")
SYNC_BASE_DIR = os.path.join(os.path.dirname(__file__),
                                  "..", "ateme", "um_backend", "sync_schema")


@pytest_asyncio.fixture(scope="function", name="updater_populate_data")
async def _updater_populate_data(updater):
    """
    Populate the database with data required for updater tests
    """
    db = updater.db.db
    await db[Collections.users.name].insert_one(USER_JOE.to_dict(with_creation_id=True))
    await db[Collections.users.name].insert_one(USER_JIM.to_dict(with_creation_id=True))
    await db[Collections.users.name].insert_one(USER_BILL.to_dict(with_creation_id=True))
    await db[Collections.users.name].insert_one(INTERNAL_USER.to_dict(with_creation_id=True))
    await db[Collections.scopes.name].insert_one(SCOPE_1.to_dict())
    await db[Collections.scopes.name].insert_one(SCOPE_2.to_dict())
    await db[Collections.scopes.name].insert_one(INTERNAL_USER_SCOPE.to_dict())
    try:
        await db[Collections.idp_config.name].insert_one(IDP_LOCAL_CONFIG.to_dict())
    except pymongo.errors.DuplicateKeyError:
        # For API test, this idp_config is already in DB
        pass
    await db[Collections.idp_config.name].insert_one(IDP_LDAP_CONFIG_1.to_dict())
    await db[Collections.idp_config.name].insert_one(IDP_LDAP_CONFIG_2.to_dict())
    await db[Collections.configuration.name].insert_one(CONFIGURATION.to_dict())

    yield

    await db[Collections.users.name].delete_one({"username": USER_JOE.username})
    await db[Collections.users.name].delete_one({"username": USER_JIM.username})
    await db[Collections.users.name].delete_one({"username": USER_BILL.username})
    await db[Collections.users.name].delete_one({"username": INTERNAL_USER.username})
    await db[Collections.scopes.name].delete_one({"id": SCOPE_1.id})
    await db[Collections.scopes.name].delete_one({"id": SCOPE_2.id})
    await db[Collections.scopes.name].delete_one({"id": INTERNAL_USER_SCOPE.id})
    await db[Collections.idp_config.name].delete_one({"idp_name": DEFAULT_LOCAL_IDP_NAME})
    await db[Collections.idp_config.name].delete_one({"domain": IDP_LDAP_CONFIG_1.domain})
    await db[Collections.idp_config.name].delete_one({"domain": IDP_LDAP_CONFIG_2.domain})
    await db[Collections.configuration.name].delete_one({"password_expiration": 9999})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version, collection_name, collection_file, expected_username_in_result, expected_ipd_name_in_result",
    [
        (
            "5.0",
            "users",
            "../ateme/um_backend/migration_files/5.0/um_users.json",
            ["Joe", "Jim", "Bill"], [DEFAULT_LOCAL_IDP_NAME, DEFAULT_LOCAL_IDP_NAME, "ldap_ateme.com"]
        ),
        (
            "4.0",
            "users",
            "../ateme/um_backend/migration_files/4.0/um_users.json",
            ["Joe", "Jim", "Bill"], [DEFAULT_LOCAL_IDP_NAME, DEFAULT_LOCAL_IDP_NAME]
        )
    ]
)
async def test_export_collection(updater,
                                 version,
                                 collection_name,
                                 collection_file,
                                 expected_username_in_result,
                                 expected_ipd_name_in_result,
                                 updater_populate_data):

    # pylint: disable=too-many-arguments,unused-argument
    """
    Test export_collection
    Export the elems of the collection specified in the collection file
    We check only user username.
     (other fields like creation_date are not constant)
    Check the coherency of the version and collection name set in the collection with the version/param
    Args:
        updater: Updater init
        version: the version expected to be in the export collection file
        collection_name: the collection expected to be in the export collection file
        collection_file: the collection file ith the data to export (with/without filter)
        expected_username_in_result: the usernames expected in the result
        expected_ipd_name_in_result: the ipd names expected in the result
    Returns:

    """
    # Patch the migration file to point to the one used for tests
    # pylint: disable=protected-access
    updater.migration_file = MIGRATION_FILE
    # pylint: disable=protected-access
    updater._migration_base_dir = MIGRATION_BASE_DIR

    base_dir = os.path.dirname(__file__)
    collection_file = os.path.join(base_dir, collection_file)
    # pylint: disable=protected-access
    content = updater._load_migration_file(collection_file)

    # Get the export filters and the list of fields to export
    filters = content["export_policy"]["filters"]
    fields_projection = content["export_policy"]["fields"]

    export_result = await updater.export_collection(collection_name, filters, fields_projection)
    # The number of exported items should be the same as the expected user nb
    assert len(export_result) == len(expected_username_in_result)
    # The username of exported users shall match with the expected ones
    all(user["username"] in expected_username_in_result for user in export_result)
    all(user["idp_name"] in expected_ipd_name_in_result for user in export_result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version, expected_result",
    [
        # Normal case
        (
            "9.0",
            [{'collection': 'users', 'data': 3,
              'import_policy': {'conflict_management': 'abort',
                                'key_index': [{'idp_name': 'ASCENDING', 'user_id': 'ASCENDING'},
                                              {'idp_name': 'ASCENDING', 'username': 'ASCENDING'}]}},
             {'collection': 'idp_config', 'data': 3,
              'import_policy': {'conflict_management': 'override',
                                'key_index': [{'idp_name': 'ASCENDING'}]}},
             {'collection': 'configuration', 'data': 1,
              'import_policy': {'conflict_management': 'override', 'key_index': []}},
             {'collection': 'scopes', 'data': 2,
              'import_policy': {'conflict_management': 'abort',
                                'key_index': [{'id': 'ASCENDING'}]}},
             {'collection': 'admin', 'data': 0,
              'import_policy': {'conflict_management': 'override',
                                'key_index': [{'user_id': 'ASCENDING'},
                                              {'username': 'ASCENDING'}]}}]
        ),
    ],
)
async def test_export_version(updater, version, expected_result, updater_populate_data):
    # pylint: disable=too-many-arguments,unused-argument
    """
    Test export_version
    Export the data for a set of collections
    Args:
        updater: Updater init
        version: the base version of the um
        expected_result: the expected exported collections with for each the number of items

    Returns:

    """
    # pylint: disable=protected-access
    updater._migration_base_dir = MIGRATION_BASE_DIR
    # pylint: disable=protected-access
    updater.migration_file = MIGRATION_FILE

    export_result = await updater.get_data_to_export(version=version)
    # To ease the content comparison,
    # for each collection, replace the exported entries in data by the nb of entries
    for collection_result in export_result:
        nb_elems = len(collection_result["data"])
        collection_result["data"] = nb_elems

    # The exported result matches with the expected one
    assert export_result == expected_result

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_result, "
    "exception_raised",
    [
        # Normal case with downgrade from 5.0 to 4.0,
        (
            {
                '9.0': [
                    {
                        'collection': 'users',
                        'import_policy': {
                            'conflict_management': 'abort',
                            'key_index': [
                                {"idp_name": "ASCENDING", "user_id": "ASCENDING"},
                                {"idp_name": "ASCENDING", "username": "ASCENDING"}
                            ]
                        },
                        'data': 3
                    },
                    {
                        'collection': 'idp_config',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': [
                                {'idp_name': 'ASCENDING'}
                            ]
                        },
                        'data': 3
                    },
                    {
                        'collection': 'configuration',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': []
                        },
                        'data': 1
                    },
                    {
                        'collection': 'scopes',
                        'import_policy': {
                            'conflict_management': 'abort',
                            'key_index': [
                                {'id': 'ASCENDING'}
                            ]
                        },
                        'data': 2
                    },
                    {
                        'collection': 'admin',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': [
                                {"user_id": "ASCENDING"},
                                {"username": "ASCENDING"}
                            ]
                        },
                        'data': 0
                    }
                ],
                '5.0': [
                    {
                        'collection': 'users',
                        'import_policy': {
                            'conflict_management': 'abort',
                            'key_index': [
                                {"idp_name": "ASCENDING", "user_id": "ASCENDING"},
                                {"idp_name": "ASCENDING", "username": "ASCENDING"}
                            ]
                        },
                        'data': 3
                    },
                    {
                        'collection': 'idp_config',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': [
                                {'idp_name': 'ASCENDING'}
                            ]
                        },
                        'data': 3
                    },
                    {
                        'collection': 'configuration',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': []
                        },
                        'data': 1
                    },
                    {
                        'collection': 'scopes',
                        'import_policy': {
                            'conflict_management': 'abort',
                            'key_index': [
                                {'id': 'ASCENDING'}
                            ]
                        },
                        'data': 2
                    },
                    {
                        'collection': 'admin',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': [
                                {"user_id": "ASCENDING"},
                                {"username": "ASCENDING"}
                            ]
                        },
                        'data': 0
                    }
                ],
                '4.0': [
                    {
                        'collection': 'users',
                        'import_policy': {
                            'conflict_management': 'abort',
                            'key_index': [
                                {'user_id': 'ASCENDING'},
                                {'username': 'ASCENDING'}
                            ]
                        },
                        'data': 3
                    },
                    {
                        'collection': 'ldap_config',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': [
                                {'domain': 'ASCENDING'}
                            ]
                        },
                        'data': 2
                    },
                    {
                        'collection': 'configuration',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': []
                        },
                        'data': 1
                    },
                    {
                        'collection': 'scopes',
                        'import_policy': {
                            'conflict_management': 'abort',
                            'key_index': [
                                {'id': 'ASCENDING'}
                            ]
                        },
                        'data': 2
                    },
                    {
                        'collection': 'admin',
                        'import_policy': {
                            'conflict_management': 'override',
                            'key_index': [
                                {"user_id": "ASCENDING"},
                                {"username": "ASCENDING"}
                            ]
                        },
                        'data': 0
                    }
                ]
            },
            False
        )
    ],
)
async def test_export_all_versions(
    updater,
    expected_result,
    exception_raised,
    updater_populate_data
):  # pylint: disable=unused-argument,too-many-locals
    """
    Test export_all_versions
    Export data for the migration file specified in the settings (used at the init of the updater)
    Args:
        updater: Updater init
        expected_result: the list of collections per version expected to be export with for each the number of data
        (for example {'collection': 'users', 'import_policy': 'abort', 'data': 3} means 3 users exported)
        exception_raised: true if an exception is expected to be raised
    Returns:

    """
    # Patch the migration file to point to the one used for tests
    # pylint: disable=protected-access
    updater._migration_base_dir = MIGRATION_BASE_DIR

    # pylint: disable=protected-access
    updater.migration_file = MIGRATION_FILE

    if exception_raised:
        with pytest.raises(InvalidMigrationFileException):
            await updater.export_all_versions()
    else:
        export_result = await updater.export_all_versions()

        # Check especially the migration of the ipd_config/ldap_config
        for version, version_data in export_result.items():
            if version != "5.0" and version != "9.0":
                # check that idp_config replaced by ldap_config
                assert find_collection(version_data, "idp_config") == -1
                ldap_config_idx = find_collection(version_data, "ldap_config")
                assert ldap_config_idx != -1
                for doc in version_data[ldap_config_idx]["data"]:
                    # "domain" should have been added, idp_name and idp_type removed
                    assert "idp_name" not in doc
                    assert "idp_type" not in doc
                    assert doc["domain"] == "ateme.com" or doc["domain"] == "ateme-velizy.com"

                user_config_idx = find_collection(version_data, "users")
                for doc in version_data[user_config_idx]["data"]:
                    assert "idp_name" not in doc
                    if doc["authenticate_mode"] == IdpType.ldap.name:
                        assert doc["domain_ldap"] == "ateme.com"
                    else:
                        assert "domain" not in doc
            else:
                # For version 5.0,
                # check that exported idp_configs matched with the ones set in db
                idp_config_idx = find_collection(version_data, "idp_config")
                idp_configs = version_data[idp_config_idx]["data"]
                assert all((IDP_LDAP_CONFIG_1.to_dict() == doc or
                            IDP_LDAP_CONFIG_2.to_dict() == doc or
                            IDP_LOCAL_CONFIG.to_dict() == doc)
                           for doc in idp_configs)

        # To ease the content comparison,
        # for each collection per version, replace the exported entries in data by the nb of entries
        for _, version_data in export_result.items():
            for collection_result in version_data:
                nb_elems = len(collection_result["data"]) \
                    if isinstance(collection_result["data"], list) else collection_result["data"]
                collection_result["data"] = nb_elems

        assert export_result == expected_result

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_exported_versions",
    [
        # Normal case
        (["9.0", "5.0", "4.0"])
    ],
)
async def test_export_full_configuration(updater, mocker,
                                         expected_exported_versions,
                                         updater_populate_data):
    # pylint: disable=too-many-locals,too-many-arguments,unused-argument
    """
    Test export_full_configuration
    Check that the data to export are properly exported for the versions specified in the migration file
    The file header and the data hash are also checked
    Args:
        updater: Updater init
        expected_exported_versions: the list of versions expected to be found in the exported zip file

    Returns:

    """
    # Patch the migration file to point to the one used for tests
    # pylint: disable=protected-access
    updater._migration_base_dir = MIGRATION_BASE_DIR
    # pylint: disable=protected-access
    updater.migration_file = MIGRATION_FILE

    # Patch the get_package_version to have a well-known version for test
    mocker.patch("ateme.um_backend.updater.UserUpdater.get_package_version", return_value="5.0.0-b.10")

    # Only the two first digits of the version are used
    um_version = '.'.join(updater.get_package_version().split('.')[:2])

    exported_content = await updater.export_full_configuration()
    # Check the results
    assert exported_content["component"] == "user-management"
    assert exported_content["version"] == um_version
    assert exported_content["generation_date"]
    # Check the expected exported versions are present in the data
    assert len(exported_content["data"]) == len(expected_exported_versions)
    assert all(version in exported_content["data"] for version in expected_exported_versions)
    # Check the hash (computed on the complete content except the hash itself) -> pop it before computing it
    exported_content_hash = exported_content.pop("hash")
    expected_hash = hashlib.md5(json.dumps(exported_content, sort_keys=True).encode('utf-8')).hexdigest()
    assert exported_content_hash == expected_hash


@pytest.mark.parametrize(
    ("populate_with_data_from_4_0, data_file, scopes_expected, users_expected, configuration_expected,"
     "idp_config_expected, log_expected, exception"),
    [
        # OK case with upgrade from 4.0 to 5.0 and 5.0 to 9.0
        (
            # Initialize data
            {
                "scopes": [{"id": "usr:engineer"}],
                "actions": [{"name": "get_current_user", "request": {"method": "GET", "route": "/user/me"}}],
                "configuration": [
                    {
                        "password_expiration": 100,
                        "max_successive_failed_login": 3,
                        "user_deactivation_period": 800,
                        "token_expiration": 13600,
                        "refresh_token_expiration": 17200,
                        "token_cleaning_period": 24
                    }
                ]
            },
            # Data to import, OK case
            "migration_test_files/imported_data_file_ok.json",
            # Scopes expected
            [
                {
                    'id': 'usr:actor',
                    'label': 'Actor',
                    'version': 3,
                    'content': [
                        {'scope': 'usr:engineer'},
                        {'action': 'get_current_user'}
                    ],
                    'title': 'Actor actor'
                }
            ],
            # Users expected
            [
                {
                    'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                    'user_id': '809c6f5139df17d4481fffc36183f4d66648a2cf',
                    'username': 'Jim',
                    'password': '123456',
                    'enabled': True,
                    'password_last_update': False,
                    'scopes': ['usr:engineer'],
                    'first_login': False,
                    'internal': False,
                    'idp_name': DEFAULT_LOCAL_IDP_NAME
                },
                {
                    'creation_id': ObjectId('63f8826a2b015ac6ae26ff1f'),
                    'user_id': '71a2a3a2eb085bdc1a8535657604a5cce7b3db37',
                    'username': 'John',
                    'password': '123456',
                    'enabled': True,
                    'password_last_update': False,
                    'scopes': ['usr:engineer'],
                    'first_login': False,
                    'internal': False,
                    'idp_name': "ldap_ateme-velizy.guest.com"
                }
            ],
            # Configuration expected
            [
                {
                    'max_successive_failed_login': 3,
                    'user_deactivation_period': 800,
                    'token_expiration': 13600,
                    'refresh_token_expiration': 17200,
                    'token_cleaning_period': 24,
                    'password_policy': {
                        'expiration_delay_in_days': 365,
                        'regex_pattern': PasswordPolicy.get_password_regex_pattern()
                    }
                }
            ],
            # Idp config expected
            [
                {
                    'idp_type': 'ldap',
                    'idp_name': 'ldap_ateme-velizy.guest.com',
                    'idp_label': 'ldap_ateme-velizy.guest.com',
                    'domain': 'ateme-velizy.guest.com',
                    'group': 'S_GUEST',
                    'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                    'server': 'atm-extra.guest.corp.ateme.com'
                }
            ],
            # Logs expected
            [
                'Bulk write on idp_config collection inserted_count: 1 modified_count: 0',
                'Bulk write on configuration collection inserted_count: 0 modified_count: 1',
                'Bulk write on users collection inserted_count: 2 modified_count: 0',
                'Bulk write on scopes collection inserted_count: 1 modified_count: 0'
            ],
            None,
        ),
        # Abort of import, can't import idp_config because we can't find "idp_name" key, used as index
        (
            {
                "scopes": [{"id": "usr:engineer"}],
                "actions": [{"name": "get_current_user", "request": {"method": "GET", "route": "/user/me"}}],
            },
            "migration_test_files/imported_data_file_key_error.json",
            # Scopes expected
            [],
            # Users expected
            [],
            # Configuration expected
            [],
            # Ldap config expected
            [],
            # Logs expected
            [],
            # Exception expected
            UpdateFilterKeyError,
        ),
        # Abort of Import because DuplicateKeyError
        (
            {
                "scopes": [{"id": "usr:engineer"}],
                "actions": [{"name": "get_current_user", "request": {"method": "GET", "route": "/user/me"}}],
            },
            "migration_test_files/imported_data_file_duplicate_key_error.json",
            # Scopes expected
            [],
            # Users expected
            [],
            # Configuration expected
            [],
            # Ldap config expected
            [],
            # Logs expected
            [],
            # Exception expected
            pymongo.errors.BulkWriteError
        ),
        # Abort of Import because invalid hash
        (
            {
                "scopes": [{"id": "usr:engineer"}],
                "actions": [{"name": "get_current_user", "request": {"method": "GET", "route": "/user/me"}}],
            },
            "migration_test_files/imported_data_file_invalid_hash.json",
            # Scopes expected
            [],
            # Users expected
            [],
            # Configuration expected
            [],
            # Ldap config expected
            [],
            # Logs expected
            [],
            # Exception expected
            InvalidHash
        ),
        (
            {
                "scopes": [{"id": "usr:engineer"}],
                "actions": [{"name": "get_current_user", "request": {"method": "GET", "route": "/user/me"}}],
            },
            "migration_test_files/imported_data_file_version_not_found.json",
            # Scopes expected
            [],
            # Users expected
            [],
            # Configuration expected
            [],
            # Ldap config expected
            [],
            # Logs expected
            [],
            # Exception expected
            VersionNotFound,
        ),
    ],
    indirect=["populate_with_data_from_4_0"]
)
async def test_import_full_configuration(
    updater,
    mocker,
    populate_with_data_from_4_0,
    data_file,
    scopes_expected,
    users_expected,
    configuration_expected,
    idp_config_expected,
    log_expected,
    exception,
    caplog,
):  # pylint: disable=too-many-arguments,too-many-locals,unused-argument
    """

    Test import_full_configuration with different input, we mock the package version.
    """
    data = None
    with open(
            os.path.join(
                os.path.dirname(__file__),
                data_file
            ),
            "r", encoding="utf-8"
    ) as _file:
        data = json_util.loads(_file.read())

    if exception:
        with pytest.raises(exception):
            if exception == VersionNotFound:
                # disable the upgrade/downgrade implementation
                updater.data_migration_imp = None
            await updater.import_full_configuration(data)
    else:
        await updater.import_full_configuration(data)

        scopes = await updater.db.db["scopes"].find({}, {"_id": 0}).to_list(None)
        assert all(item in scopes for item in scopes_expected), \
            f"Fail to find expected {scopes_expected} in {scopes}"
        users = await updater.db.db["users"].find({}, {"_id": 0}).to_list(None)
        assert all(item in users for item in users_expected), \
            f"Fail to find expected {users_expected} in {users}"
        assert all(user["idp_name"]
                   == DEFAULT_LOCAL_IDP_NAME for user in users if user["username"] == "Jim"), \
            f"Idp_name not set to {DEFAULT_LOCAL_IDP_NAME} for at least one local users"
        assert all(user["idp_name"]
                   == "ldap_ateme-velizy.guest.com" for user in users if user["username"] == "John"), \
            "Idp_name not set to ldap_ateme-velizy.guest.com for at least one ldap users"
        configuration = await updater.db.db["configuration"].find({}, {"_id": 0}).to_list(None)
        assert all(item in configuration[0] for item in configuration_expected[0]), \
            f"Fail to find expected {configuration_expected} in {configuration}"

        idp_configs = await updater.db.db["idp_config"].find({}, {"_id": 0}).to_list(None)
        assert all(item in idp_configs for item in idp_config_expected), \
            f"Fail to find expected {idp_config_expected} in {idp_configs}"

    assert all(item in caplog.messages for item in log_expected), \
        f"Fail to find expected {log_expected} in {caplog.messages}"


@pytest.mark.parametrize(
    "data, actions, scopes, data_expected",
    [
        (
            [
                {
                    'collection': 'users',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [
                            {"user_id": "ASCENDING"},
                            {"username": "ASCENDING"}
                        ]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff7e'),
                            'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                            'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                            'username': 'Jim',
                            'password': '123456',
                            'enabled': True,
                            'password_last_update': False,
                            'scopes': ['usr:engineer', 'usr:unexist'],
                            'authenticate_mode': 'local',
                            'first_login': False,
                            'internal': False
                        }
                    ]
                },
                {
                    'collection': 'scopes',
                    'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:actor',
                            'label': 'Actor',
                            'version': 3,
                            'content': [
                                {'scope': 'usr:engineer'},
                                {'action': 'get_current_user'},
                                {'scope': 'usr:unexist'},
                                {'action': 'unexist'}
                            ],
                            'title': 'Actor actor'
                        }
                    ]
                }
            ],
            # actions
            [
                Action(name="get_current_user")
            ],
            # scopes
            [
                Scope(id="usr:engineer")
            ],
            # data expected
            [
                {
                    'collection': 'users',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [
                            {"user_id": "ASCENDING"},
                            {"username": "ASCENDING"}
                        ]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff7e'),
                            'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                            'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                            'username': 'Jim',
                            'password': '123456',
                            'enabled': True,
                            'password_last_update': False,
                            'scopes': ['usr:engineer'],
                            'authenticate_mode': 'local',
                            'first_login': False,
                            'internal': False
                        }
                    ]
                }, {
                    'collection': 'scopes',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [{'id': 'ASCENDING'}]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:actor',
                            'label': 'Actor',
                            'version': 3,
                            'content': [
                                {'scope': 'usr:engineer'},
                                {'action': 'get_current_user'}
                            ],
                            'title': 'Actor actor'
                        }
                    ]
                }
            ]
        ),
        (
            [
                {
                    'collection': 'users',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [
                            {"username": "ASCENDING"}
                        ]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff7e'),
                            'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                            'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                            'username': 'Jim',
                            'password': '123456',
                            'enabled': True,
                            'password_last_update': False,
                            'scopes': ['usr:engineer', 'usr:unexist'],
                            'authenticate_mode': 'local',
                            'first_login': False,
                            'internal': False
                        }
                    ]
                },
                {
                    'collection': 'scopes',
                    'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:engineer',
                            'label': 'Engineer',
                            'version': 3,
                            'content': [
                                {'action': 'get_current_user'},
                            ],
                            'title': 'Actor actor'
                        },
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:actor',
                            'label': 'Actor',
                            'version': 3,
                            'content': [
                                {'scope': 'usr:engineer'},
                            ],
                            'title': 'Actor actor'
                        }
                    ]
                }
            ],
            # actions
            [
                Action(name="get_current_user")
            ],
            # scopes
            [],
            # data expected
            [
                {
                    'collection': 'users',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [
                            {"username": "ASCENDING"}
                        ]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff7e'),
                            'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                            'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                            'username': 'Jim',
                            'password': '123456',
                            'enabled': True,
                            'password_last_update': False,
                            'scopes': ['usr:engineer'],
                            'authenticate_mode': 'local',
                            'first_login': False,
                            'internal': False
                        }
                    ]
                }, {
                    'collection': 'scopes',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [{'id': 'ASCENDING'}]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:engineer',
                            'label': 'Engineer',
                            'version': 3,
                            'content': [
                                {'action': 'get_current_user'},
                            ],
                            'title': 'Actor actor'
                        },
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:actor',
                            'label': 'Actor',
                            'version': 3,
                            'content': [
                                {'scope': 'usr:engineer'},
                            ],
                            'title': 'Actor actor'
                        }
                    ]
                }
            ]
        ),
        # Users data without 'scopes' key should work
        (
            [
                {
                    'collection': 'users',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [
                            {"user_id": "ASCENDING"},
                            {"username": "ASCENDING"}
                        ]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff7e'),
                            'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                            'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                            'username': 'Jim',
                            'password': '123456',
                            'enabled': True,
                            'password_last_update': False,
                            'authenticate_mode': 'local',
                            'first_login': False,
                            'internal': False
                        }
                    ]
                },
                {
                    'collection': 'scopes',
                    'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:actor',
                            'label': 'Actor',
                            'version': 3,
                            'content': [
                                {'scope': 'usr:engineer'},
                                {'action': 'get_current_user'},
                                {'scope': 'usr:unexist'},
                                {'action': 'unexist'}
                            ],
                            'title': 'Actor actor'
                        }
                    ]
                }
            ],
            # actions
            [
                Action(name="get_current_user")
            ],
            # scopes
            [
                Scope(id="usr:engineer")
            ],
            # data expected
            [
                {
                    'collection': 'users',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [
                            {"user_id": "ASCENDING"},
                            {"username": "ASCENDING"}
                        ]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff7e'),
                            'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                            'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                            'username': 'Jim',
                            'password': '123456',
                            'enabled': True,
                            'password_last_update': False,
                            'scopes': [],
                            'authenticate_mode': 'local',
                            'first_login': False,
                            'internal': False
                        }
                    ]
                }, {
                    'collection': 'scopes',
                    'import_policy': {
                        'conflict_management': 'abort',
                        'key_index': [{'id': 'ASCENDING'}]
                    },
                    'data': [
                        {
                            '_id': ObjectId('63f882712b015ac6ae26ff80'),
                            'id': 'usr:actor',
                            'label': 'Actor',
                            'version': 3,
                            'content': [
                                {'scope': 'usr:engineer'},
                                {'action': 'get_current_user'}
                            ],
                            'title': 'Actor actor'
                        }
                    ]
                }
            ]
        ),
    ],
)
# pylint: disable=too-many-arguments
def test_consolidate_data(updater, data, actions, scopes, data_expected):
    """

    Test consolidate_data with different input and check if unexist ref are removed.
    """
    updater.consolidate_data(data, actions, scopes)
    assert data == data_expected

@pytest.mark.parametrize("data, actions, scopes, check_result_expected", [
    (
        {
            "action": "get_token"
        },
        ["get_def", "get_scope"],
        ["usr:operator", "usr:guest"],
        False
    ),
    (
        {
            "action": "get_token"
        },
        ["get_def", "get_scope", "get_token"],
        ["usr:operator", "usr:guest"],
        True
    ),
    (
        {
            "scope": "usr:guest"
        },
        ["get_def", "get_scope", "get_token"],
        ["usr:operator", "usr:guest"],
        True
    ),
    (
        {
            "scope": "usr:engineer"
        },
        ["get_def", "get_scope", "get_token"],
        ["usr:operator", "usr:guest"],
        False
    ),
    (
        {},
        ["get_def", "get_scope", "get_token"],
        ["usr:operator", "usr:guest"],
        False
    )
])
# pylint: disable=too-many-arguments
def test_check_ref(updater, data, actions, scopes, check_result_expected):
    """

    Call Updater._check_ref with different input
    """
    # pylint: disable=protected-access
    assert updater._check_ref(data, actions, scopes) == check_result_expected

@pytest.mark.asyncio
async def test_get_sync_data(init_backend_with_admin, updater_populate_data, mocker):
    """
    Test route /sync/data

    Args:
        init_backend_with_admin (_type_): _description_
    """
    _api, _, _admin_token = init_backend_with_admin
    # Patch the get_package_version to have a well-known version for test
    mocker.patch("ateme.um_backend.updater.UserUpdater.get_package_version", return_value="13.6")
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    resp = await _api.get("/sync/data", headers=_admin_headers)
    assert resp.status == 200
    result = await resp.read()
     # Write the returned file content in a .zip file and unzip it
    input_file = io.BytesIO()
    input_file.write(result)

    exported_content = None
    with zipfile.ZipFile(input_file, 'r') as file:
        names = file.namelist()
        with file.open(names[0], mode="r") as _file:
            exported_content = json.loads(_file.read())
    # 4 collections are exported
    assert len(exported_content['data']['latest']) == 4
    for data in exported_content['data']['latest']:
        # Check that conflict management is override for all collections
        assert data['import_policy']['conflict_management'] == 'override'

@pytest.mark.asyncio
@pytest.mark.parametrize("scopes_expected, users_expected, configuration_expected, idp_config_expected", [
    (
        ['usr:actor', 'usr:director'],
        ['Joe', 'Jim', 'Bill'],
        [
            {
                "max_successive_failed_login": 3,
                "user_deactivation_period": 600,
                "token_expiration": 3600,
                "refresh_token_expiration": 7200,
                "token_cleaning_period": 24,
                "logout_timeout": -1,
                "password_policy":
                {"regex_pattern": "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[#$^+=!*()@%&])\\S{,255}$",
                 "expiration_delay_in_days": -1,
                 "password_min_length": 10}
            }
        ],
        [
            {'idp_name': 'local',
             'idp_type': 'local',
             'idp_label': 'Local'
             },
            {'idp_type': 'ldap',
             'idp_name': 'ldap_ateme.com',
             'domain': 'ateme.com',
             'server': 'atm-infra.corp.ateme.com',
             'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
             'group': 'S_SUPPORT',
             'deny_access': True
             },
            {'idp_type': 'ldap',
             'idp_name': 'ldap_ateme-velizy.com',
             'idp_label': 'Ldap ateme-velizy.com',
             'domain': 'ateme-velizy.com',
             'server': 'atm-extra.corp.ateme.com',
             'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
             'group': 'S_SUPPORT',
             'deny_access': True
             }
        ]
    )
])
async def test_import_sync_data(
    init_backend_with_admin,
    updater,
    scopes_expected,
    users_expected,
    configuration_expected,
    idp_config_expected
):  # pylint: disable=too-many-arguments,too-many-locals
    """

    Test PUT /fullconfiguration endpoint
    Check if we find scopes, users, ldap_config and configuration coherency in database
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    raw_data = None
    base_dir = os.path.dirname(__file__)
    exported_data_file_path = \
        os.path.join(base_dir,
                     "migration_test_files/export_file_latest.zip")
    with open(exported_data_file_path, "rb") as _file:
        raw_data = {"files": _file.read()}

    resp = await _api.put("/sync/data", data=raw_data, headers=_admin_headers)
    assert resp.status == 200
    result = await resp.text()
    assert result == "OK"

    scopes = await updater.db.db["scopes"].find({}, {"_id": 0}).to_list(None)
    assert all(item in [item["id"] for item in scopes] for item in scopes_expected)

    users = await updater.db.db["users"].find({}, {"_id": 0}).to_list(None)
    assert all(item in [item["username"] for item in users] for item in users_expected)

    configuration = await updater.db.db["configuration"].find({}, {"_id": 0}).to_list(None)
    assert all(item in configuration[0] for item in configuration_expected[0])

    idp_config = await updater.db.db["idp_config"].find({}, {"_id": 0}).to_list(None)
    assert all(item in idp_config for item in idp_config_expected)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "migration_file, export_file_name, expected_exported_versions",
    [
        # Normal case
        (MIGRATION_FILE, "export_file_9.0", ["9.0", "5.0", "4.0"])
    ],
)
async def test_api_export_full_configuration(
    init_backend_with_admin,
    mocker,
    migration_file,
    export_file_name,
    expected_exported_versions,
    updater_populate_data
):
    # pylint: disable=too-many-locals,too-many-arguments,unused-argument
    """
    Test route /fullconfiguration
    Check the returned zip file with the exported data specified in the migration file
    First test case: status code 200, zip file ok
    For the second test case, a status code 500 (because exception):
    To raise this exception, mock the validate_collection_file method to patch a collection file with an invalid one
    Args:
        init_backend_with_admin: um server api
        migration_file: the migration file
        export_file_name: The name of the export file
        expected_exported_versions: the content of result zip file with exported data

    """
    _api, _um, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    # Patch the migration file to point to the one used for tests
    # pylint: disable=protected-access
    _um.updater.migration_file = os.path.join(os.path.dirname(__file__), migration_file)
    _um.updater._migration_base_dir = MIGRATION_BASE_DIR

    # Patch the get_package_version to have a well-known version for test
    mocker.patch("ateme.um_backend.updater.UserUpdater.get_package_version", return_value="5.0.0-b.10")
    # Only the two first digits of the version are used
    um_version = "5.0"

    resp = await _api.get(f"/fullconfiguration?file_name={export_file_name}", headers=_admin_headers)
    assert resp.status == 200
    result = await resp.read()

    # Write the returned file content in a .zip file and unzip it
    input_file = io.BytesIO()
    input_file.write(result)

    exported_content = None
    with zipfile.ZipFile(input_file, 'r') as file:
        names = file.namelist()
        assert names[0] == f"{export_file_name}.json"
        with file.open(names[0], mode="r") as _file:
            exported_content = json.loads(_file.read())

    assert exported_content["version"] == um_version
    assert len(exported_content["data"]) == len(expected_exported_versions)
    assert all(version in exported_content["data"] for version in expected_exported_versions)
    # Check the hash (computed on the complete content except the hash itself) -> pop it before computing it
    exported_content_hash = exported_content.pop("hash")
    expected_hash = hashlib.md5(json.dumps(exported_content, sort_keys=True).encode('utf-8')).hexdigest()
    assert exported_content_hash == expected_hash

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "migration_file_test, export_file_name",
    [
        # Normal case
        (MIGRATION_FILE, "export_file_with_admin_5.0"),
    ],
)
async def test_api_export_full_configuration_with_admin(
    init_backend_with_admin,
    updater,
    mocker,
    migration_file_test,
    export_file_name,
    updater_populate_data
):
    # pylint: disable=too-many-locals,too-many-arguments,unused-argument
    """
    Test route /fullconfiguration with export_admin_credentials query param set to True
    Check the returned zip file with the exported data specified in the migration file
    contains the admin credentials data
    Args:
        init_backend_with_admin: um server api
        migration_file_test: the migration file
        export_file_name: The name of the export file
    Returns:

    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # First check that Admin exists
    resp = await _api.get("/admin")
    assert resp.status == 200
    # pylint: disable=protected-access
    updater._migration_base_dir = MIGRATION_BASE_DIR
    # Patch migration file setter
    updater.migration_file = os.path.join(os.path.dirname(__file__), migration_file_test)
    # Patch the get_package_version to have a well-known version for test
    mocker.patch("ateme.um_backend.updater.UserUpdater.get_package_version", return_value="5.0.0-b.10")

    resp = await _api.get(
        f"/fullconfiguration?file_name={export_file_name}&include_admin_credentials=true",
        headers=_admin_headers,
    )
    assert resp.status == 200
    result = await resp.read()

    # Write the returned file content in a .zip file and unzip it
    input_file = io.BytesIO()
    input_file.write(result)

    exported_content = None
    with zipfile.ZipFile(input_file, 'r') as file:
        names = file.namelist()
        assert names[0] == f"{export_file_name}.json"
        with file.open(names[0], mode="r") as _file:
            exported_content = json.loads(_file.read())

    admin_col = None
    # Get exported content admin collection
    for collection in exported_content['data']['5.0']:
        if collection['collection'] == 'admin':
            admin_col = collection
    # Check scopes that are admin
    assert admin_col['data'][0]['scopes'] == ['all:administrator']

@pytest.mark.asyncio
@pytest.mark.parametrize("scopes_expected, users_expected, configuration_expected, idp_config_expected", [
    (
        ['usr:actor', 'usr:director'],
        ['Joe', 'Jim', 'Bill'],
        [
            {
                'max_successive_failed_login': 3,
                'user_deactivation_period': 600,
                'token_expiration': 3600,
                'refresh_token_expiration': 7200,
                'token_cleaning_period': 24,
                'password_policy': {
                    'expiration_delay_in_days': 9999*30,
                    'regex_pattern': PasswordPolicy.get_password_regex_pattern()
                }
            }
        ],
        [
            {
                'idp_type': 'ldap',
                'idp_name': 'ldap_ateme.com',
                'idp_label': 'ldap_ateme.com',
                'domain': 'ateme.com',
                'server': 'atm-infra.corp.ateme.com',
                'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
                'group': 'S_SUPPORT'
            },
            {
                'idp_type': 'ldap',
                'idp_name': 'ldap_ateme-velizy.com',
                'idp_label': 'ldap_ateme-velizy.com',
                'domain': 'ateme-velizy.com',
                'server': 'atm-extra.corp.ateme.com',
                'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
                'group': 'S_SUPPORT'
            }
        ]
    )
])
async def test_api_import_full_configuration(
    init_backend_with_admin,
    updater,
    scopes_expected,
    users_expected,
    configuration_expected,
    idp_config_expected
):  # pylint: disable=too-many-arguments,too-many-locals
    """

    Test PUT /fullconfiguration endpoint
    Check if we find scopes, users, ldap_config and configuration coherency in database
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    raw_data = None
    base_dir = os.path.dirname(__file__)
    exported_data_file_path = os.path.join(base_dir, "migration_test_files/result_file.zip")
    with open(exported_data_file_path, "rb") as _file:
        raw_data = {"files": _file.read()}

    resp = await _api.put("/fullconfiguration", data=raw_data, headers=_admin_headers)
    assert resp.status == 200
    result = await resp.text()
    assert result == "OK"

    scopes = await updater.db.db["scopes"].find({}, {"_id": 0}).to_list(None)
    assert all(item in [item["id"] for item in scopes] for item in scopes_expected)

    users = await updater.db.db["users"].find({}, {"_id": 0}).to_list(None)
    assert all(item in [item["username"] for item in users] for item in users_expected)

    configuration = await updater.db.db["configuration"].find({}, {"_id": 0}).to_list(None)
    assert all(item in configuration[0] for item in configuration_expected[0])

    idp_config = await updater.db.db["idp_config"].find({}, {"_id": 0}).to_list(None)
    assert all(item in idp_config for item in idp_config_expected)

@pytest.mark.asyncio
@pytest.mark.parametrize("override", [True, False])
@pytest.mark.parametrize("force_override", [True, False])
async def test_api_import_full_configuration_with_admin(
    override,
    force_override,
    init_backend_with_admin,
    init_database,
    admin_user,
    mocker
):  # pylint: disable=too-many-arguments,too-many-locals
    """

    Test PUT /fullconfiguration endpoint with import admin credentials query set to True,
    we mock package version.
    Check if we find admin coherency in database
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Patch the get_package_version to have a well-known version for test
    mocker.patch("ateme.um_backend.updater.UserUpdater.find_last_version", return_value="5.0")
    mocker.patch("ateme.um_backend.updater.UserUpdater.get_package_version", return_value="5.0.0-b.10")

    if not override:
        # Pre-requis
        await _db.db['admin'].delete_many({"internal": {"$ne": True}, "scopes": {"$regex": "administrator"}})
        await _db.db['users'].delete_many({})
        await _db.db['scopes'].delete_many({})
        # Only the two first digits of the version are used
        base_dir = os.path.dirname(__file__)
        exported_data_file_path = os.path.join(base_dir, "migration_test_files/result_with_admin_file.zip")

        with open(exported_data_file_path, "rb") as _file:
            raw_data = {"files": _file.read()}
    else:
        # We need to delete them, because the import policy is not override and it will cause a problem
        if not force_override:
            await _db.db['users'].delete_many({})
            await _db.db['scopes'].delete_many({})
        else:
            # Insert a User in order to test the force overload option
            await _db.create_user(
                User(username="user_updater", password="EnAvantGuingamp!", creation_id=ObjectId(), scopes=[]),
                "users")
        # We need to regenerate an export raw data to pass to the import
        # So we can simulate the override process of the admin
        resp = await _api.get(
            "/fullconfiguration?file_name=export_file_with_admin_5.0&include_admin_credentials=true",
            headers=_admin_headers,
        )
        assert resp.status == 200
        raw_data = await resp.read()
        raw_data = {"files": raw_data}

    resp = await _api.put(
        f"/fullconfiguration?include_admin_credentials=true&force_override={force_override}",
        data=raw_data,
        headers=_admin_headers,
    )
    assert (await resp.text()) == "OK"
    admin = await _db.db["admin"].find({}, {"_id": 0}).to_list(None)
    # Assert that the admin is present
    assert admin
    assert admin[1]['scopes'] == ['all:administrator']
    # Try to login with the admin user
    # Do this for the new constraints
    if not override:
        admin_user = {'password': 'adminA0!', 'username': 'admin'}
    resp = await _api.post("/token", json=admin_user)
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    # Assert that the user has been correctly overloaded
    if override and force_override:
        user_overloaded = await _db.db["users"].find_one({"username": "user_updater"})
        assert user_overloaded
