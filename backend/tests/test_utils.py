#pylint: disable=no-member
"""
Test utils
"""
import json
import os

import pytest
from ateme.openapi import OpenApiDefinition
from ateme.um_backend import (
    ApiDescriptor,
    MissingParameterException,
    AuthDataDescriptor
)
from ateme.um_backend.utils import (
    generate_scopes_and_actions,
    parse_scopes_and_actions,
    build_action_name_from_method_and_uri,
    compute_app_scopes, Scope
)
from ateme.um_backend import load_default_scopes, load_default_actions


ACTIONS_DATA_EXPECTED = [
    {
        "name": "get_ping",
        "label": "Users",
        "title": "Get ping",
        "request": {"method": "GET", "route": "/ping"},
        "prefix": "usr",
        "description": "Ping server",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "get_test",
        "label": "Users",
        "title": "Get test",
        "request": {"method": "GET", "route": "/test"},
        "prefix": "usr",
        "description": "Get test",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "get_def",
        "label": "Users",
        "title": "Get API's JSON Definition",
        "request": {"method": "GET", "route": "/definition"},
        "prefix": "usr",
        "description": "Get API Definition",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "get_doc",
        "label": "Users",
        "title": "Get API Documentation",
        "request": {"method": "GET", "route": "/documentation"},
        "prefix": "usr",
        "description": "Get API Documentation",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "get_internal_users_test",
        "label": "Users",
        "title": "Get internal users test",
        "request": {"method": "GET", "route": "/internal_users_test"},
        "prefix": "usr",
        "description": "Get Internal users test",
        "internal": True,
        "x_scope_match_children": False
    },
    {
        "name": "get_without_description",
        "label": "Users",
        "title": "Get Blop without description",
        "request": {"method": "GET", "route": "/without_description"},
        "prefix": "usr",
        "description": "Get Blop without description",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "get_without_description_and_summary",
        "label": "Users",
        "title": "Get without description and summary",
        "request": {"method": "GET", "route": "/without_description_and_summary"},
        "prefix": "usr",
        "description": "Missing description ...",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        'name': 'get_v1_0_test_users_user_id',
        'label': 'Users',
        'title': 'Get v1 0 test users user id',
        'request': {'method': 'GET', 'route': '/V1.0/test-users/{user.id}'},
        'prefix': 'usr',
        'description': 'Get a user by id with version prefix without operationId',
        'internal': False,
         'x_scope_match_children': False
    }
]


ACTIONS_DATA_EXPECTED_SUB = [
    {
        "name": "usr:get_ping",
        "label": "Users",
        "title": "Get ping",
        "request": {"method": "GET", "route": "/sub/ping"},
        "prefix": "usr",
        "description": "Ping server",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "usr:get_test",
        "label": "Users",
        "title": "Get test",
        "request": {"method": "GET", "route": "/sub/test"},
        "prefix": "usr",
        "description": "Get test",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "usr:get_def",
        "label": "Users",
        "title": "Get API's JSON Definition",
        "request": {"method": "GET", "route": "/sub/definition"},
        "prefix": "usr",
        "description": "Get API Definition",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "usr:get_doc",
        "label": "Users",
        "title": "Get API Documentation",
        "request": {"method": "GET", "route": "/sub/documentation"},
        "prefix": "usr",
        "description": "Get API Documentation",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "usr:get_internal_users_test",
        "label": "Users",
        "title": "Get internal users test",
        "request": {"method": "GET", "route": "/sub/internal_users_test"},
        "prefix": "usr",
        "description": "Get Internal users test",
        "internal": True,
        "x_scope_match_children": False
    },
    {
        "name": "get_without_description",
        "label": "Users",
        "title": "Get Blop without description",
        "request": {"method": "GET", "route": "/sub/without_description"},
        "prefix": "usr",
        "description": "Get Blop without description",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        "name": "get_without_description_and_summary",
        "label": "Users",
        "title": "Get without description and summary",
        "request": {"method": "GET", "route": "/sub/without_description_and_summary"},
        "prefix": "usr",
        "description": "Missing description ...",
        "internal": False,
        "x_scope_match_children": False
    },
    {
        'name': 'get_v1_0_test_users_user_id',
        'label': 'Users',
        'title': 'Get v1 0 test users user id',
        'request': {'method': 'GET', 'route': '/sub/V1.0/test-users/{user.id}'},
        'prefix': 'usr',
        'description': 'Get a user by id with version prefix without operationId',
        'internal': False,
        'x_scope_match_children': False
    }
]


SCOPES_DATA_EXPECTED_SIMPLE = [
    {
        "id": "usr:administrator",
        "label": "Users",
        "content": [
            {"action": "usr:get_ping", "policy": "allow", "resource": {}},
            {"action": "usr:get_test", "policy": "allow", "resource": {}},
            {"action": "usr:get_without_description", "policy": "allow", "resource": {}},
            {"action": "usr:get_without_description_and_summary", "policy": "allow", "resource": {}},
            {'action': 'usr:get_v1_0_test_users_user_id', 'policy': 'allow', 'resource': {}}
        ],
        "default": True,
        "internal": False,
        "title": "Administrator - users",
        "description": "Role granting full access to all users, roles, and identity management functionalities.",
    },
    {
        "id": "usr:engineer",
        "label": "Users",
        "content": [
            {"action": "usr:get_ping", "policy": "allow", "resource": {}},
            {"action": "usr:get_test", "policy": "allow", "resource": {}},
        ],
        "default": True,
        "internal": False,
        "title": "Engineer - users",
        "description": "Role allowing configuration-related actions with additional permissions on users, roles," \
                       " and identity management functionalities.",
    },
    {
        "id": "usr:guest",
        "label": "Users",
        "content": [
            {"action": "usr:get_ping", "policy": "allow", "resource": {}},
            {"action": "usr:get_test", "policy": "allow", "resource": {}},
        ],
        "default": True,
        "internal": False,
        "title": "Guest - users",
        "description": "Role with minimal access, limited to viewing personal information, logging out, and changing" \
                       " the password.",
    },
    {
        "id": "usr:internal_administrator",
        "label": "Users",
        "content": [
            {"action": "usr:get_internal_users_test", "policy": "allow", "resource": {}}
        ],
        "default": True,
        "internal": True,
        "title": "Internal_administrator - users",
        "description": "Scope internal_administrator for Users",
    },
]


SCOPES_DATA_EXPECTED_SIMPLE_SUB = [
    {
        "id": "usr:administrator",
        "label": "Users",
        "content": [
            {"action": "usr:usr:get_ping", "policy": "allow", "resource": {}},
            {"action": "usr:usr:get_test", "policy": "allow", "resource": {}},
            {"action": "usr:usr:get_without_description", "policy": "allow", "resource": {}},
            {"action": "usr:usr:get_without_description_and_summary", "policy": "allow", "resource": {}}
        ],
        "default": True,
        "internal": False,
        "title": "Administrator - users",
        "description": "Role granting full access to all users, roles, and identity management functionalities.",
    },
    {
        "id": "usr:engineer",
        "label": "Users",
        "content": [
            {"action": "usr:usr:get_ping", "policy": "allow", "resource": {}},
            {"action": "usr:usr:get_test", "policy": "allow", "resource": {}},
        ],
        "default": True,
        "internal": False,
        "title": "Engineer - users",
        "description": "Role allowing configuration-related actions with additional permissions on users, roles, and" \
                       " identity management functionalities.",
    },
    {
        "id": "usr:guest",
        "label": "Users",
        "content": [
            {"action": "usr:usr:get_ping", "policy": "allow", "resource": {}},
            {"action": "usr:usr:get_test", "policy": "allow", "resource": {}},
        ],
        "default": True,
        "internal": False,
        "title": "Guest - users",
        "description": "Role with minimal access, limited to viewing personal information, logging out, and changing" \
                       " the password.",
    },
    {
        "id": "usr:internal_administrator",
        "label": "Users",
        "content": [
            {
                "action": "usr:usr:get_internal_users_test",
                "policy": "allow",
                "resource": {},
            }
        ],
        "default": True,
        "internal": True,
        "title": "Internal_administrator - users",
        "description": "Scope internal_administrator for Users",
    }
]

DEFAULT_ADMIN_USER = {'username': 'default_admin', 'password': 'AtemeAAA0!'}


@pytest.mark.parametrize("subapp_path", [None, "", "/sub"])
def test_generate_scopes_and_actions(usr_api_path, subapp_path):
    """

    test generate_actions from types/action.py
    """
    api_definition = OpenApiDefinition(usr_api_path, full_validation=True)
    scopes, actions = generate_scopes_and_actions(api_definition=api_definition,
                                                  subapp_path=subapp_path,
                                                  mainapp_prefix=api_definition.auth.prefix if subapp_path else "")
    # Actions
    assert isinstance(actions, list)
    assert [json.loads(json.dumps(item.to_dict())) for item in actions] == ACTIONS_DATA_EXPECTED if not subapp_path \
        else ACTIONS_DATA_EXPECTED_SUB
    # Scopes
    assert len(scopes) == 4
    results = [dict(item.to_dict()) for item in scopes]
    assert results == SCOPES_DATA_EXPECTED_SIMPLE if not subapp_path else SCOPES_DATA_EXPECTED_SIMPLE_SUB


def test_generate_scopes_and_actions_fails(api_path):
    """

    test generate_actions from types/action.py
    """
    api_definition = OpenApiDefinition(api_path, full_validation=True)
    scopes, actions = generate_scopes_and_actions(api_definition=api_definition, subapp_path="/sub")
    assert not scopes
    assert not actions

    scopes, actions = generate_scopes_and_actions(api_definition=api_definition, mainapp_prefix="/main")
    assert not scopes
    assert not actions


def test_populate_scopes_and_actions(usr_api_path, subapp_api_path):
    """

    :return:
    """
    main_def = OpenApiDefinition(definition_file=usr_api_path)
    api_descriptor = ApiDescriptor(prefix=main_def.auth.prefix,
                                   url="mainapp:8080")

    def custom_populate_scopes_and_actions(descriptor: ApiDescriptor):
        parse_scopes_and_actions(api_descriptor, main_def)
        descriptor.validate()

    custom_populate_scopes_and_actions(api_descriptor)

    subappa_def = OpenApiDefinition(definition_file=subapp_api_path)
    subappa_def.definition["info"]["x-auth"]["prefix"] = "suba"

    with pytest.raises(MissingParameterException):
        parse_scopes_and_actions(api_descriptor, subappa_def, "subappA", main_def)

    parse_scopes_and_actions(api_descriptor, subappa_def, "/subappA", main_def)

    subappb_def = OpenApiDefinition(definition_file=subapp_api_path)
    subappb_def.definition["info"]["x-auth"]["prefix"] = "subb"
    parse_scopes_and_actions(api_descriptor, subappb_def, "/subappB", main_def)

    with open(os.path.join(os.path.dirname(__file__), 'default_data', "apidescriptor.json"), 'r',
              encoding="utf-8") as file:
        api_json = json.loads(file.read())
        set_default_internal_actions_and_scopes(api_json)
        to_test = api_descriptor.to_dict()
        to_test.pop('app_name')
        assert json.loads(json.dumps(to_test)) == api_json


def set_default_internal_actions_and_scopes(descr: dict) -> dict:
    """

    Fill actions and scopes with internal field set to default value False (if not set)
    :return:
    """
    for action in descr["actions"]:
        action.setdefault("internal", False)
    for scope in descr["scopes"]:
        scope.setdefault("internal", False)




EXPECTED_SCOPES = [{'id': 'usr:full_access', 'label': 'usr', 'content': [], 'title': 'usr full_access'},
                   {'id': 'usr:admintwo', 'label': 'usr', 'title': 'usr admintwo'},
                   {'id': 'usr:admin', 'label': 'usr',
                    'content': [{'action': 'usr:logout', 'policy': 'allow', 'resource': {}}],
                    'title': 'usr admin'},
                   {'id': 'usr:bad_action', 'label': 'usr',
                    'content': [{'toto': 'usr:*', 'policy': 'allow', 'resource': {}}],
                    'title': 'usr bad_action'},
                   {'id': 'usr:bad_resource', 'label': 'usr',
                    'content': [{'action': 'usr:*', 'policy': 'allow', 'toto': {}}],
                    'title': 'usr bad_resource'},
                   {'id': 'usr:title', 'label': 'usr', 'title': "Pilot manager title",
                    'content': [{'action': 'usr:*', 'policy': 'allow', 'toto': {}}]}]


@pytest.mark.parametrize("data,failed", [
    pytest.param([], True),
    pytest.param([{"id": "usr:full_access", "label": "usr", "content": []},
                  {"id": "usr:adminun", "label": "usr", "content": ["/api"]},
                  {"id": "usr:admintwo", "label": "usr", "spin": []},
                  {"id": "usr:admin", "label": "usr",
                   "content": [{"action": "usr:logout", "policy": "allow", "resource": {}}]},
                  {"id": "usr:bad_default_scope", "label": "usr",
                   'toto': [{'action': 'usr:*', 'policy': 'allow', 'resource': {}}]},
                  {'id': 'usr:bad_action', "label": "usr",
                   'content': [{'toto': 'usr:*', 'policy': 'allow', 'resource': {}}]},
                  {'id': 'usr:bad_policy', "label": "usr",
                   'content': [{'action': 'usr:*', 'toto': 'allow', 'resource': {}}]},
                  {'id': 'usr:bad_resource', "label": "usr",
                   'content': [{'action': 'usr:*', 'policy': 'allow', 'toto': {}}]},
                  {'id': 'usr:title', "label": "usr", "title": "Pilot manager title",
                   'content': [{'action': 'usr:*', 'policy': 'allow', 'toto': {}}]}
                  ], False),
])
def test_load_default_scope(data, failed):
    """

    test load default scope
    :param data:
    :return:
    """
    # encrypted_scopes = AESCipher(hash_key=True).encrypt(str(data))
    if failed:
        assert not load_default_scopes(data)
    else:
        scopes = load_default_scopes(data)
        assert scopes
        assert len(scopes) == 6
        results = [dict(item.to_dict()) for item in scopes]
        assert results == EXPECTED_SCOPES


@pytest.mark.parametrize("data,failed", [
    pytest.param([], True),
    pytest.param([{"name": "delete_alarm",
                   "request": {"method": "POST", "route": "/alarm/{id}"},
                   "prefix": "ala", "version": 1,
                   "description": "Another desc"},
                  {"name": "not_complete"},
                  {"name": "wrong_action", "request": {}}], True),
    pytest.param([{"name": "delete_alarm",
                   "request": {"method": "POST", "route": "/alarm/{id}"},
                   "prefix": "ala", "version": 1},
                  {"name": "wrong_action", "request": {}, "description": "Another desc"}], False),
])
def test_load_default_action(data, failed):
    """
    test load default action

    :param data:
    :return:
    """
    if failed:
        assert not load_default_actions(data)
    else:
        actions = load_default_actions(data)
        assert actions
        assert len(actions) == 1


@pytest.mark.parametrize("data, failed", [
    pytest.param({
        "actions": [], "scopes": [], "api_descriptors": []},
        True, id="no-data-to-load"),
    pytest.param({
        "actions": [
            {
                "name": "get_ping",
                "label": "Users",
                "title": "Get ping",
                "request": {
                    "method": "GET",
                    "route": "/ping"
                },
                "prefix": "mainapp:usr",
                "description": "Ping server"
            },
            {
                "name": "get_def",
                "label": "Users",
                "title": "Get API Definition",
                "request": {
                    "method": "GET",
                    "route": "/definition"
                },
                "prefix": "mainapp:usr",
                "description": "Get API Definition"
            }],
        "api_descriptors": [{"prefix":"usr", "url":"mainapp:8080", "app_name": "app"}],
        "scopes": [{
            "id": "usr:administrator",
            "label": "Users",
            "content": [
                {
                    "action": "mainapp:usr:get_ping",
                    "policy": "allow",
                    "resource": {
                    }
                },
                {
                    "action": "mainapp:usr:get_def",
                    "policy": "allow",
                    "resource": {
                    }
                }
            ],
            "default": True,
            "title": "Administrator - users",
            "description": "Role granting full access to all users, roles, and identity management functionalities."
        }]
    }, False, id="data-loaded"),
    pytest.param({
        "actions": [],
        "api_descriptors": [{"prefix": "usr", "url": "mainapp:8080", "app_name": "app"}],
        "scopes": [{
            "id": "usr:administrator",
            "label": "Users",
            "content": [
                {
                    "action": "mainapp:usr:get_ping",
                    "policy": "allow",
                    "resource": {
                    }
                },
                {
                    "action": "mainapp:usr:get_def",
                    "policy": "allow",
                    "resource": {
                    }
                }
            ],
            "default": True,
            "title": "Administrator - users",
            "description": "Role granting full access to all users, roles, and identity management functionalities."
        }]
    }, True, id="missing-actions")

])
async def test_load_default_auth_data(init_api, data, failed):
    """
    Test the load_default_auth_data method.
    Params:
        data: A dictionary containing the data to be loaded.
        failed: A boolean indicating whether the loading of the data is expected to fail.
    """
    init_api.default_auth_data = None

    auth_data = init_api.load_default_auth_data(data)
    if failed:
        assert not auth_data
    else:
        assert auth_data.actions and len(auth_data.actions) == len(data["actions"])
        assert auth_data.scopes and len(auth_data.scopes) == len(data["scopes"])
        assert (auth_data.auth_data_descriptors and len(auth_data.auth_data_descriptors)
                == len(data["api_descriptors"]))


@pytest.mark.parametrize("method_name, uri, expected_value", [
    pytest.param("GET", "/users_/", "get_users__"),
    pytest.param("GET", "/{id}", "get_id"),
    pytest.param("GET", "/users/actions", "get_users_actions"),
    pytest.param("GET", "/users/{id}/actions", "get_users_id_actions"),
    pytest.param("GET", "/users/{id}/actions/{id_2}/{id_3}", "get_users_id_actions_id_2_id_3"),
    pytest.param("PATCH", "/V1.1.0/Users/sub-actions/{id-2}/", "patch_v1_1_0_users_sub_actions_id_2_"),
    pytest.param("GET", "/", "get_")
])
def test_build_action_name(method_name, uri, expected_value):
    """
    test build action name from method and uri

    :param method_name:
    :param uri:
    :param expected_value:
    :return:
    """
    action_name = build_action_name_from_method_and_uri(method_name=method_name, uri=uri)
    assert action_name == expected_value, "The action name does not correspond to the expected value"


@pytest.mark.parametrize(
    "input_args, expected_manage_app_scopes, expected_app_scopes", [
    pytest.param(
        {
            "api_descriptors": [],
            "scopes": []
        },
        False,
        [],
        id="no-api-descriptors"
    ),
    pytest.param(
        {
            "api_descriptors": [
                ApiDescriptor("apm", "http://127.0.0.1:2200"),
                ApiDescriptor("sysm", "http://127.0.0.1:2300")
            ],
            "scopes": []
        },
        False,
        [],
        id="api-descriptors"
    ),
    pytest.param(
        {
            "api_descriptors": [
                AuthDataDescriptor("apm", "http://127.0.0.1:2200", "app1"),
                AuthDataDescriptor("almext", "http://127.0.0.1:2200", "app1"),
                AuthDataDescriptor("sysm", "http://127.0.0.1:2300", "app2")
            ],
            "scopes": [
                # level 2 (app scopes)
                Scope(id="app1:administrator"), Scope(id="app1:engineer"), Scope(id="app1:operator"),
                Scope(id="app1:monitoring"), Scope(id="app1:guest"),
                Scope(id="app2:administrator"), Scope(id="app2:engineer"), Scope(id="app2:operator"),
                Scope(id="app2:monitoring"), Scope(id="app2:guest"),
                # level 3
                Scope(id="app1:apm:administrator"), Scope(id="app1:apm:engineer"),
                Scope(id="app1:apm:operator"), Scope(id="app1:apm:monitoring"), Scope(id="app1:apm:guest"),
                Scope(id="app1:almext:administrator"), Scope(id="app1:almext:engineer"),
                Scope(id="app1:almext:operator"), Scope(id="app1:almext:monitoring"), Scope(id="app1:almext:guest"),
                Scope(id="app2:sysm:administrator"), Scope(id="app2:sysm:engineer"),
                Scope(id="app2:sysm:operator"), Scope(id="app2:sysm:monitoring"), Scope(id="app2:sysm:guest")
            ]
        },
        True,
        [
            'app1:administrator', 'app1:engineer', 'app1:operator', 'app1:monitoring', 'app1:guest',
            'app2:administrator', 'app2:engineer', 'app2:operator', 'app2:monitoring', 'app2:guest'
        ],
        id="auth-data-descriptors"
    ),
    pytest.param(
        {
            "api_descriptors": [],
            "scopes": [
                # level 2 (app scopes)
                Scope(id="app1:administrator"), Scope(id="app1:engineer"), Scope(id="app1:operator"),
                Scope(id="app1:monitoring"), Scope(id="app1:guest"),
                Scope(id="app2:administrator"), Scope(id="app2:engineer"), Scope(id="app2:operator"),
                Scope(id="app2:monitoring"), Scope(id="app2:guest"),
                # level 3
                Scope(id="app1:apm:administrator"), Scope(id="app1:apm:engineer"),
                Scope(id="app1:apm:operator"), Scope(id="app1:apm:monitoring"), Scope(id="app1:apm:guest"),
                Scope(id="app1:almext:administrator"), Scope(id="app1:almext:engineer"),
                Scope(id="app1:almext:operator"), Scope(id="app1:almext:monitoring"), Scope(id="app1:almext:guest"),
                Scope(id="app2:sysm:administrator"), Scope(id="app2:sysm:engineer"),
                Scope(id="app2:sysm:operator"), Scope(id="app2:sysm:monitoring"), Scope(id="app2:sysm:guest")
            ]
        },
        True,
        [
            'app1:administrator', 'app1:engineer', 'app1:operator', 'app1:monitoring', 'app1:guest',
            'app2:administrator', 'app2:engineer', 'app2:operator', 'app2:monitoring', 'app2:guest'
        ],
        id="scopes-lvl2-lvl3-and-without-api-descriptors"
    ),
    pytest.param(
        {
            "api_descriptors": [],
            "scopes": [
                # level 3
                Scope(id="app1:apm:administrator"), Scope(id="app1:apm:engineer"),
                Scope(id="app1:apm:operator"), Scope(id="app1:apm:monitoring"), Scope(id="app1:apm:guest"),
                Scope(id="app1:almext:administrator"), Scope(id="app1:almext:engineer"),
                Scope(id="app1:almext:operator"), Scope(id="app1:almext:monitoring"), Scope(id="app1:almext:guest"),
                Scope(id="app2:sysm:administrator"), Scope(id="app2:sysm:engineer"),
                Scope(id="app2:sysm:operator"), Scope(id="app2:sysm:monitoring"), Scope(id="app2:sysm:guest")
            ]
        },
        True,
        [],
        id="scopes-lvl3-and-without-api-descriptors"
    )
])
def test_compute_app_scopes(input_args, expected_manage_app_scopes, expected_app_scopes):
    """
    Test compute_app_scopes
    :param input_args:
    :param expected_app_scopes:
    """
    manage_app_scopes, app_scopes = compute_app_scopes(**input_args)
    assert manage_app_scopes == expected_manage_app_scopes
    assert set(app_scopes) == set(expected_app_scopes)
