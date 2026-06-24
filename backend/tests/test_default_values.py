# pylint: disable=no-member,unused-argument,too-few-public-methods,protected-access
"""
Tests default scopes
"""
import json
import logging
import os
from dataclasses import dataclass
from bson import ObjectId

import pytest
from ateme.openapi import OpenApiDefinition

import ateme.um_backend
from ateme.um_backend import User
from ateme.um_backend.database import Database, Collections, ScopeFilter
from ateme.um_backend.user_management import UserManagementApi
from ateme.um_backend.utils import generate_scopes_and_actions

CURRENT_PATH = os.path.dirname(__file__)

API_UM_PATH = os.path.join(
    os.path.dirname(ateme.um_backend.__file__), "api", "api.yaml"
)
API_DEFINITION = OpenApiDefinition(API_UM_PATH, full_validation=True)

TEST_ACTIONS = [
    {
        "name": "get_truc",
        "prefix": "usr",
        "request": {"method": "GET", "route": "/bidule"},
        "description": "test endpoint",
        "label": "usr",
    }
]

TEST_ACTIONS_APM = [
    {
        "name": "get_truc",
        "prefix": "apm",
        "request": {"method": "GET", "route": "/bidule"},
        "description": "test endpoint",
        "label": "apm",
    }
]

TEST_SCOPES = [
    {
        "id": "usr:my_administrator",
        "label": "usr",
        "title": "usr my_administrator",
        "content": [
            {"action": "usr:get_admin", "policy": "allow", "resource": {}},
            {"action": "usr:create_admin_user", "policy": "allow", "resource": {}},
            {"action": "usr:get_idp_configs", "policy": "allow", "resource": {}},
            {"action": "usr:store_idp_config", "policy": "allow", "resource": {}},
            {"action": "usr:remove_idp_config", "policy": "allow", "resource": {}},
            {
                "action": "usr:get_idp_config_by_domain",
                "policy": "allow",
                "resource": {},
            },
            {"action": "usr:update_idp_config", "policy": "allow", "resource": {}},
            {"action": "usr:logout", "policy": "allow", "resource": {}},
            {"action": "usr:change_password", "policy": "allow", "resource": {}},
            {"action": "usr:remove_scopes", "policy": "allow", "resource": {}},
            {"action": "usr:get_scopes", "policy": "allow", "resource": {}},
            {"action": "usr:update_scopes", "policy": "allow", "resource": {}},
            {"action": "usr:store_scopes", "policy": "allow", "resource": {}},
            {"action": "usr:remove_scope_by_id", "policy": "allow", "resource": {}},
            {"action": "usr:get_scope_by_id", "policy": "allow", "resource": {}},
            {"action": "usr:update_scope_by_id", "policy": "allow", "resource": {}},
            {
                "action": "usr:change_token_expiration",
                "policy": "allow",
                "resource": {},
            },
            {"action": "usr:get_current_user", "policy": "allow", "resource": {}},
            {"action": "usr:delete_users", "policy": "allow", "resource": {}},
            {"action": "usr:get_users", "policy": "allow", "resource": {}},
            {"action": "usr:update_users", "policy": "allow", "resource": {}},
            {"action": "usr:add_users", "policy": "allow", "resource": {}},
            {"action": "usr:remove_user_by_name", "policy": "allow", "resource": {}},
            {"action": "usr:get_user_by_name", "policy": "allow", "resource": {}},
            {"action": "usr:update_user_by_name", "policy": "allow", "resource": {}},
            {"action": "usr:validate_ldap", "policy": "allow", "resource": {}},
        ],
        "default": True,
    },
    {
        "id": "usr:default_ldap_scope",
        "label": "usr",
        "title": "usr default_ldap_scope",
        "content": [
            {"action": "usr:logout", "policy": "allow", "resource": {}},
            {"action": "usr:change_password", "policy": "allow", "resource": {}},
            {"action": "usr:get_current_user", "policy": "allow", "resource": {}},
        ],
        "default": True,
    },
    {
        "id": "usr:default_users_scope",
        "label": "usr",
        "title": "usr default_users_scope",
        "content": [
            {"action": "usr:logout", "policy": "allow", "resource": {}},
            {"action": "usr:change_password", "policy": "allow", "resource": {}},
            {"action": "usr:get_current_user", "policy": "allow", "resource": {}},
            {"action": "usr:update_user_by_name", "policy": "allow", "resource": {}},
        ],
        "default": True,
    },
]

TEST_SCOPES_APM = [
    {
        "id": "apm:administrator",
        "label": "apm",
        "content": [
          {
            "action": "apm:uninstall_app_by_name",
            "policy": "allow",
            "resource": {}
          },

        ],
        "default": True,
    }
]

TEST_USERS = [{"username": "Import-export user", "password": "Secret@123", 'scopes': []},
              {"username": "Upgrade user", "password": "Secret@123", 'scopes': []}]

TEST_AUTH_DATA_DESCRIPTORS = [
    {
        "prefix": "um:usr",
        "url": "http://127.0.0.1:1234",
        # no app_name -> no app scope managed
    },
    {
        "prefix": "app:apm",
        "url": "http://127.0.0.1:5678",
        # no app_name -> no app scope managed
    }
]
TEST_ADMIN_USERNAME = "default_admin"
TEST_ADMIN_PASSWORD = "adminAAA0!"

# Auth_dat
TEST_AUTH_DATA = {
    "actions": TEST_ACTIONS,
    "api_descriptors": TEST_AUTH_DATA_DESCRIPTORS,
    "scopes": TEST_SCOPES
}

# An admin user that will be stored in database prior to test of the loading an default admin
ALREADY_EXIST_ADMIN_USER = {
    'creation_id': ObjectId('6650ac7f0cb98cfe6fb8dd16'),
    'user_id': '65146ef20fbd9a927c4d51bf7d8faa28531564b4', 'username': 'existing_admin',
    'password': 'qJkI58AnBCqQofr2rhjgotqq+mbbJsJrcPGtY/+VJw+rgPUaEstzwMiQMGK+3BFjdG5I+OXE50ZvZT11TGOSdg==',
    'enabled': True, 'password_last_update': 1716555871.919945, 'scopes': ['all:administrator'],
    'idp_name': 'local', 'first_login': False, 'default': False}


@dataclass
class MockSettings:
    """
    For storage of default paths
    """
    default_actions_path = None
    default_scopes_path = None
    default_users_paths = None
    default_descriptor_path = None
    default_admin_path = None
    default_auth_data_path = None


@pytest.mark.parametrize(
    "default_scopes, expected_result",
    [
        pytest.param(
            [],
            [item.to_dict() for item in generate_scopes_and_actions(API_DEFINITION)[0]]
        ),
        pytest.param(TEST_SCOPES, TEST_SCOPES),
    ],
)
@pytest.mark.asyncio
async def test_scopes(init_database, default_scopes, expected_result, settings):
    """ test_scopes """
    # pylint: disable=too-many-locals
    database = init_database

    # write scopes file
    settings = settings # pylint: disable=self-assigning-variable
    scope_path = None
    if default_scopes:
        scope_path = os.path.join(CURRENT_PATH, 'default_data', 'default_scopes')
        with open(scope_path, "w", encoding="utf-8") as scope_file:
            scope_file.write(json.dumps(default_scopes))

        mock_settings = MockSettings()
        mock_settings.default_scopes_path = scope_path
        settings.default_scopes_path = mock_settings.default_scopes_path
    api = UserManagementApi(
        database=Database(database.client, settings.um_database_name),
        settings=settings,
        executor=None,
        service="service",
        origin="origin",
    )

    await api.initialize()

    db_scopes = await api.db.collection_scopes.get_list()
    api_scopes = [
        "usr:administrator",
        "usr:engineer",
        "usr:guest",
        "all:administrator",
        "all:engineer",
        "all:operator",
        "all:monitoring",
        "all:guest",
    ]
    assert len(db_scopes) == len(api_scopes) + len(default_scopes)
    scopes_ids = [scope.id for scope in db_scopes]
    assert all(scope in scopes_ids for scope in api_scopes)
    assert all(scope['id'] in scopes_ids for scope in default_scopes)

    unexpected_scopes = []
    if api.default_scopes is not None:
        for idx, scope in enumerate(api.default_scopes):
            actions = sorted(scope.to_dict()["content"], key=lambda d: d["action"])
            actions_expected = sorted(
                expected_result[idx]["content"], key=lambda d: d["action"]
            )
            if actions_expected != actions or scope.to_dict()["id"] != expected_result[idx]["id"]:
                unexpected_scopes.append(scope.to_dict())
    if unexpected_scopes:
        print(unexpected_scopes)
    assert not unexpected_scopes
    if scope_path:
        os.remove(scope_path)


@pytest.mark.parametrize(
    "default_actions, expected_result",
    [
        pytest.param(TEST_ACTIONS, [], id='add-default-actions'),
    ],
)
@pytest.mark.asyncio
async def test_actions(init_database, default_actions, expected_result, settings):
    """ Test actions default values are correctly added """
    database = init_database

    # write actions file
    action_path = None
    if default_actions:
        action_path = os.path.join(CURRENT_PATH, 'default_data', 'default_actions')
        with open(action_path, "w", encoding="utf-8") as action_file:
            action_file.write(json.dumps(default_actions))

    settings = settings # pylint: disable=self-assigning-variable
    mock_settings = MockSettings()
    mock_settings.default_actions_path = action_path
    settings.default_actions_path = mock_settings.default_actions_path
    api = UserManagementApi(
        database=Database(database.client, settings.um_database_name),
        settings=settings,
        executor=None,
        service="service",
        origin="origin",
    )

    await api.initialize()

    if default_actions:
        db_actions = await api.db.collection_actions.get_list()
        dict_actions = [act.to_dict() for act in db_actions]
        for action in default_actions:
            assert action in dict_actions


@pytest.mark.parametrize(
    "default_users, expected_result, init_failed",
    [
        pytest.param(
            [{"username": "Import-export user", "password": "Secret@123", 'scopes': []}],
            ['Import-export user'],
            False,
            id='add-default-users'
        ),
        pytest.param(
            [{"username": "Import-export user", "password": "Secret@123", 'scopes': [], 'internal': True}],
            [],
            False,
            id='add-internal-default-users'
        ),
        pytest.param(
            [{"username": "Import-export user", "password": "Secret@123", 'scopes': [], 'idp_name': 'foo'}],
            ['Import-export user'],
            False,
            id='add-default-users-custom-idp'
        ),
    ],
)
async def test_users_default_values(
    init_database, default_users, expected_result, init_failed, caplog, settings
):
    # pylint: disable=too-many-locals, too-many-arguments
    """ Test users default values are correctly added """
    database = init_database

    # write actions file
    user_path = None
    if default_users:
        user_path = os.path.join(CURRENT_PATH, 'default_data', 'default_users')
        with open(user_path, "w", encoding="utf-8") as action_file:
            action_file.write(json.dumps(default_users))

    settings = settings # pylint: disable=self-assigning-variable
    mock_settings = MockSettings()
    mock_settings.default_users_paths = user_path
    settings.default_users_paths = mock_settings.default_users_paths
    with caplog.at_level(logging.ERROR):
        api = UserManagementApi(
            database=Database(database.client, settings.um_database_name),
            settings=settings,
            executor=None,
            service="service",
            origin="origin",
        )
        await api.initialize()

    error_log = [record for record in caplog.records if 'Failed to load users file' in record.msg]
    assert len(error_log) == (1 if init_failed else 0)
    if default_users:
        db_users = await api.db.get_all_users()
        assert sorted([user.get('username') for user in db_users]) == sorted(expected_result)


@pytest.mark.parametrize(
    "default_admin, already_exist_admin_in_db, expected_admin_username, init_failed",
    [
        pytest.param(
            {"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
            None,
            TEST_ADMIN_USERNAME,
            False,
            id='add-default-admin'
        ),
        pytest.param(
            {},
            None,
            None,
            False,
            id='no-default-to-add'
        ),
        pytest.param(
            {"username": TEST_ADMIN_USERNAME, "password": "adminAAA0!"},
            ALREADY_EXIST_ADMIN_USER,
            ALREADY_EXIST_ADMIN_USER["username"],
            False,
            id='no-default-admin-added-because-existing-admin-in-db'
        )
    ],
)
async def test_admin(
    init_database,
    default_admin,
    already_exist_admin_in_db,
    expected_admin_username,
    init_failed,
    caplog,
    settings,
):
    # pylint: disable=too-many-locals, too-many-arguments
    """ Test admin default value is correctly added """
    database = init_database

    # write actions file
    admin_path = None
    if default_admin:
        admin_path = os.path.join(CURRENT_PATH, 'default_data', 'default_admin')
        with open(admin_path, "w", encoding="utf-8") as admin_file:
            admin_file.write(json.dumps(default_admin))

    settings = settings # pylint: disable=self-assigning-variable
    mock_settings = MockSettings()
    mock_settings.default_admin_path = admin_path
    settings.default_admin_path = mock_settings.default_admin_path
    with caplog.at_level(logging.ERROR):
        api = UserManagementApi(
            database=Database(database.client, settings.um_database_name),
            settings=settings,
            executor=None,
            service="service",
            origin="origin",
        )
        if already_exist_admin_in_db:
            # store an admin in db to simulate an existing admin: no default admin will be loaded
            admin = User.from_dict(already_exist_admin_in_db)
            res = await api.db.create_user(admin, Collections.admin.name)
            assert res.acknowledged
        await api.initialize()

    error_log = [record for record in caplog.records if 'Failed to load admin file' in record.msg]
    assert len(error_log) == (1 if init_failed else 0)
    db_admin = await api.db.get_admin_user()
    if init_failed or not default_admin:
        assert db_admin is None
    else:
        assert db_admin.get('username') == expected_admin_username # the default admin or the already existing admin


@pytest.mark.asyncio
async def test_scopes_users(init_database, caplog, settings):
    """ Test to ensure scopes and users are correctly created for Appliance Deployer use case """
    # pylint: disable=too-many-locals
    database = init_database

    # write actions file
    scope_path = os.path.join(CURRENT_PATH, 'default_data', 'default_scopes.json')
    user_path = os.path.join(CURRENT_PATH, 'default_data', 'default_users.json')

    settings = settings # pylint: disable=self-assigning-variable
    mock_settings = MockSettings()
    mock_settings.default_scopes_path = scope_path
    mock_settings.default_users_paths = user_path
    settings.default_scopes_path = mock_settings.default_scopes_path
    settings.default_users_paths = mock_settings.default_users_paths
    with caplog.at_level(logging.ERROR):
        api = UserManagementApi(
            database=Database(database.client, settings.um_database_name),
            settings=settings,
            executor=None,
            service="service",
            origin="origin",
        )
        await api.initialize()

    error_log = [record for record in caplog.records if 'Failed to load' in record.msg]
    assert len(error_log) == 0

    # Ensure data is not returned by API
    db_scopes = await api.db.collection_scopes.get_list()
    db_users = await api.db.get_all_users()
    assert 'technical:import_export_user' not in [scope.id for scope in db_scopes]
    assert 'Import-export user' not in [user.get('username') for user in db_users]

    # Ensure data exists
    scope_filter = ScopeFilter(internal=True)
    db_scopes = await api.db.collection_scopes.get_list(scope_filter=scope_filter)
    db_users = await api.db.get_all_users(internal=True)
    assert 'technical:import_export_user' in [scope.id for scope in db_scopes]
    assert 'Import-export user' in [user.get('username') for user in db_users]


@pytest.mark.parametrize(
    "default_auth_data, expected_actions, expected_scopes, expected_api_descriptor_prefix",
    [
        pytest.param(TEST_AUTH_DATA, TEST_ACTIONS, TEST_SCOPES, ["app:apm", "um:usr"],
                     id='add-default-auth-data')
    ]
)
async def test_auth_data(init_database, default_auth_data, expected_actions, expected_scopes,
                         expected_api_descriptor_prefix, settings):
    # pylint: disable=too-many-arguments, too-many-locals
    """
    Test actions, scopes, api-descriptor from default auth_data are correctly added
    """
    database = init_database

    # write auth_data file
    auth_data_path = os.path.join(CURRENT_PATH, 'default_data', 'default_auth_data')
    with open(auth_data_path, "w", encoding="utf-8") as action_file:
        action_file.write(json.dumps(default_auth_data))

    settings = settings # pylint: disable=self-assigning-variable
    mock_settings = MockSettings()
    mock_settings.default_auth_data_path = [auth_data_path]
    settings.default_auth_data_path = mock_settings.default_auth_data_path
    api = UserManagementApi(
        database=Database(database.client, settings.um_database_name),
        settings=settings,
        executor=None,
        service="service",
        origin="origin",
    )

    await api.initialize()

    db_actions = await api.db.collection_actions.get_list()
    db_scopes = await api.db.collection_scopes.get_list()
    db_api_descriptors = await api.db.collection_api_descriptors.get_list()

    default_actions = [act.to_dict() for act in db_actions]
    default_scopes = [scope.to_dict() for scope in db_scopes]
    default_api_descriptor_prefix = [desc.to_dict()["prefix"] for desc in db_api_descriptors]

    for action in expected_actions:
        assert action in default_actions
    for scope in expected_scopes:
        assert scope in default_scopes
    for prefix in expected_api_descriptor_prefix:
        assert prefix in default_api_descriptor_prefix
    for prefix in expected_api_descriptor_prefix:
        assert prefix in default_api_descriptor_prefix


@pytest.mark.parametrize(
    "file_list, expected_action_nb, expected_scope_nb, expected_api_descriptor_app_name, expected_appmgr_scope_ids, \
    expected_all_administrator_content, expected_all_engineer_content",
    [
        pytest.param([],
                     0, 0, [], [], [{"scope": "usr:administrator"}], [{"scope": "usr:engineer"}],
                     id='empty-auth-data-files'),
        # auth_data_appmgr.json contains some app scopes
        # and auth_data_sysm.json does not contain any app scopes
        pytest.param([os.path.join(CURRENT_PATH, "default_data", "auth_data_appmgr.json"),
                      os.path.join(CURRENT_PATH, "default_data", "auth_data_sysm.json"),
                      ],
                     12 + 11,
                     2 + 3 + 2,  # 2 app scopes for apm should be generated"
                     ["appapm", "app2apm", "appsysm"
                      ],
                     ['appapm:administrator'
                      ],
                     [{"scope": 'usr:administrator'},
                      {"scope": 'appapm:administrator'},
                      {"scope": 'appsysm:administrator'}],
                     [{"scope": 'usr:engineer'},
                      {"scope": 'appapm:engineer'},
                      {"scope": 'appsysm:engineer'}],
                     id='two-auth-data-files'
                     )
    ]
)
async def test_auth_data_from_files(init_database, file_list,
                                    expected_action_nb, expected_scope_nb, expected_api_descriptor_app_name,
                                    expected_appmgr_scope_ids,
                                    expected_all_administrator_content, expected_all_engineer_content,
                                    settings):
    # pylint: disable=too-many-arguments, too-many-locals
    """
    Test that actions, scopes and admin from default auth_data are correctly added.
    These data are loaded from files generated by the generate_auth script.
     """
    database = init_database

    settings = settings  # pylint: disable=self-assigning-variable
    mock_settings = MockSettings()
    mock_settings.default_auth_data_path = file_list
    settings.default_auth_data_path = mock_settings.default_auth_data_path
    api = UserManagementApi(
        database=Database(database.client, settings.um_database_name),
        settings=settings,
        executor=None,
        service="service",
        origin="origin",
    )

    await api.initialize()

    db_actions = await api.db.collection_actions.get_list()
    db_scopes = await api.db.collection_scopes.get_list()
    scopes = [sc.to_dict() for sc in db_scopes]
    db_api_descriptors = await api.db.collection_api_descriptors.get_list()

    dict_appmgr_actions = [act.to_dict() for act in db_actions if act.label == "apm"]
    dict_appmgr_scopes = [sc.to_dict() for sc in db_scopes if sc.label == "apm"]
    # To get expected generated app scopes
    dict_appmgr_app_scope_ids = [sc.to_dict()["id"] for sc in db_scopes if sc.label == "appapm"]
    dict_sysm_actions = [act.to_dict() for act in db_actions if act.label == "sysm"]
    dict_sysm_scopes = [sc.to_dict() for sc in db_scopes if sc.label == "sysm"]
    api_descriptors = [desc.to_dict()["app_name"] for desc in db_api_descriptors]

    assert len(dict_appmgr_actions) + len(dict_sysm_actions) == expected_action_nb
    assert len(dict_appmgr_scopes) + len(dict_appmgr_app_scope_ids) + len(dict_sysm_scopes) == expected_scope_nb
    for scope_id in expected_appmgr_scope_ids:
        assert scope_id in dict_appmgr_app_scope_ids
    assert len(api_descriptors) == len(expected_api_descriptor_app_name)
    for desc in expected_api_descriptor_app_name:
        assert desc in api_descriptors

    # Check hat scopes content
    all_administrator_scope_content = [scope["content"] for scope in scopes if scope["id"] == "all:administrator"][0]
    assert all(elem in all_administrator_scope_content for elem in expected_all_administrator_content)
    all_engineer_scope_content = [scope["content"] for scope in scopes if scope["id"] == "all:engineer"][0]
    assert all(elem in all_engineer_scope_content for elem in expected_all_engineer_content)
