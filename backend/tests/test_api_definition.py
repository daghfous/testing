# pylint: disable=no-member,unused-argument
"""

Test API definition
"""
import copy
import json
import time
from logging import getLogger
import yaml
from aiohttp.test_utils import TestClient
import pytest

from ateme.um_backend.user_management import UserManagementApi

LOG = getLogger(__name__)

def get_test_api_definition_contents(api_path, subapp_api_path):
    """
    get_test_api_definition_contents: prepare contenst for test_api_definition use cases content
    """
    main_api_json, subapp_api_definition1, subapp_api_definition2 = None, None, None
    with open(api_path, 'r', encoding="utf-8") as main_app_yaml_file:
        main_api_json = yaml.safe_load(main_app_yaml_file.read())

    with open(subapp_api_path, 'r', encoding="utf-8") as sub_app_yaml_file:
        subapp_api_definition1 = yaml.safe_load(sub_app_yaml_file.read())
    subapp_api_definition1['info']['x-auth']['prefix'] = 'subone'
    subapp_api_definition1['info']['x-auth']['label'] = 'subone'
    subapp_api_definition2 = copy.deepcopy(subapp_api_definition1)
    subapp_api_definition2['info']['x-auth']['prefix'] = 'subtwo'
    subapp_api_definition2['info']['x-auth']['label'] = 'subtwo'

    main_api_json_prefix_missing = copy.deepcopy(main_api_json)
    del main_api_json_prefix_missing["info"]["x-auth"]["prefix"]

    main_api_json_xauth_content_err = copy.deepcopy(main_api_json)
    main_api_json_xauth_content_err["info"]["x-auth"] = {'prefix': 'tata'}

    main_api_json_paths_content_err = copy.deepcopy(main_api_json)
    main_api_json_paths_content_err["paths"] = {'toto': 'toto'}

    main_api_json_operationid_err = copy.deepcopy(main_api_json)
    first_http_fonction_key = next(iter(main_api_json_operationid_err["paths"]))
    del main_api_json_operationid_err["paths"][first_http_fonction_key]["get"]["operationId"]

    main_api_json_responses_missing = copy.deepcopy(main_api_json)
    first_http_fonction_key = next(iter(main_api_json_responses_missing["paths"]))
    del main_api_json_responses_missing["paths"][first_http_fonction_key]["get"]["responses"]

    subapp_api_json1 = {"definition": subapp_api_definition1, "path": "/subapp1"}
    subapp_api_json2 = {"definition": subapp_api_definition2, "path": "/subapp2"}

    return [
        {"descr": "With a main API and no subapp", "base_url": "https://my_app/",
         "main_api": main_api_json, "http_code": 201},
        {"descr": "With a main API and one subapp API", "base_url": "https://my_app/",
         "main_api": main_api_json, "subapp_apis": [subapp_api_json1], "http_code": 201},
        {"descr": "With a main API and many subapps API", "base_url": "https://my_app/",
         "main_api": main_api_json, "subapp_apis": [subapp_api_json1, subapp_api_json2], "http_code": 201},
        {"descr": "With no main API", "base_url": "https://my_app/",
         "main_api": {}, "http_code": 400},
        {"descr": "With no main API but a subapp", "base_url": "https://my_app/",
         "main_api": {}, "subapp_apis": [subapp_api_json1], "http_code": 400},
        {"descr": "With a main API without key 'prefix'", "base_url": "https://my_app/",
         "main_api": main_api_json_prefix_missing, "http_code": 400},
        {"descr": "With a main API without key 'base_url'",
         "main_api": main_api_json, "http_code": 400},
        {"descr": "With a main API without key 'x-auth'", "base_url": "https://my_app/",
         "main_api": main_api_json_xauth_content_err, "http_code": 400},
        {"descr": "With a main API without key 'paths'", "base_url": "https://my_app/",
         "main_api": main_api_json_paths_content_err, "http_code": 400},
        {"descr": "With a main API without key 'operationId'", "base_url": "https://my_app/",
         "main_api": main_api_json_operationid_err, "http_code": 201},
        {"descr": "With a main API without key 'responses'", "base_url": "https://my_app/",
         "main_api": main_api_json_responses_missing, "http_code": 400},
    ]


async def test_api_definition(init_backend_with_admin, init_database, api_path, subapp_api_path):
    """
    Test API definition API
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database
    test_cases = get_test_api_definition_contents(api_path, subapp_api_path)

    # TODO: Should be rework as parametrize
    for content in test_cases:
        post_resp = await _api.post("/api_definition", json=content, headers=_admin_headers)
        assert post_resp.status == content["http_code"]
        # TODO: check content of POST /api_definition response

        if content["descr"] == "With a main API and many subapps API":
            # Check scopes and actions for this specific use case
            db_scopes = await _db.collection_scopes.get_list()
            expected_hat_scopes = {
                "all:administrator": [{'scope': 'usr:administrator'}, {'scope': 'test:administrator'}],
                "all:engineer": [{'scope': 'usr:engineer'}, {'scope': 'test:engineer'}],
                "all:operator": [{'scope': 'usr:guest'}, {'scope': 'test:operator'}],
                "all:monitoring": [{"scope": "usr:guest"}],
                "all:guest": [{"scope": "usr:guest"}, {'scope': 'test:guest'}]}
            db_scopes_contents = {scope_db.id: scope_db.content for scope_db in db_scopes}
            assert all(db_scopes_contents[id_] == content
                       for id_, content in expected_hat_scopes.items())
            db_actions = await _db.collection_actions.get_list()
            assert len(db_actions) == 66  # Expected number of actions

async def test_post_long_api_definition(
        init_backend_with_admin: tuple[TestClient, UserManagementApi, str],
        init_database: str,
        very_long_api_path: str
):
    """
    Test to POST API definition with a long API definition
    This is used to test the usefulness of the 'disable_validation' query parameter
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _ = init_database

    with open(very_long_api_path, 'r', encoding="utf-8") as main_app_json_file:
        main_api_json = json.load(main_app_json_file)

    body: dict = {
        "base_url": "https://my_app/",
        "main_api": main_api_json,
        "app_name": "my-app"
    }

    start: float = time.perf_counter()
    async with _api.post("/api_definition", json=body, headers=_admin_headers) as post_resp:
        elapsed_enable_validation: float = time.perf_counter() - start
        assert post_resp.status == 201, (await post_resp.text())
        assert (await post_resp.text()) == "OK"

    LOG.info(f'Elapsed time with validation enabled: {elapsed_enable_validation}' )

    # retry with 'disable_validation' query parameter
    start: float = time.perf_counter()
    async with _api.post("/api_definition?disable_validation=True", json=body, headers=_admin_headers) as post_resp:
        elapsed_disable_validation: float = time.perf_counter() - start
        assert post_resp.status == 201, (await post_resp.text())
        assert (await post_resp.text()) == "OK"

    LOG.info(f'Elapsed time with validation disabled: {elapsed_enable_validation}')

    # Check that the time is lower with 'disable_validation'
    assert elapsed_disable_validation < elapsed_enable_validation, \
        "Elapsed time with 'disable_validation' should be lower than without it"


# pylint: disable=too-many-locals
async def test_with_app_name(init_backend_with_admin, init_database, api_path):
    """
    Test to POST API definition with an application name
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database

    with open(api_path, 'r', encoding="utf-8") as main_app_yaml_file:
        main_api_json = yaml.safe_load(main_app_yaml_file.read())
    body = {"base_url": "https://my_app/",
            "main_api": main_api_json,
            "app_name": "my-app"}

    post_resp = await _api.post("/api_definition", json=body, headers=_admin_headers)
    assert post_resp.status == 201
    assert (await post_resp.text()) == "OK"

    db_scopes = await _db.collection_scopes.get_list()
    db_actions = await _db.collection_actions.get_list()
    db_actions_prefix = set([action.prefix for action in db_actions]) # pylint: disable=consider-using-set-comprehension

    # Check scope content
    app_admin_scope = [scope for scope in db_scopes if scope.id == 'my-app:test:administrator'][0]
    assert app_admin_scope.content[0]['action'] == 'my-app:test:GetHostname'
    assert app_admin_scope.content[1]['action'] == 'my-app:test:get_ping'

    # Check that the lower level scope is embedded
    all_admin_scope = [scope for scope in db_scopes if scope.id == 'all:administrator'][0]
    lower_level_scopes_ref = ['usr:administrator', 'my-app:administrator']
    for content in all_admin_scope.content:
        assert content['scope'] in lower_level_scopes_ref

    # Check scope ids
    db_scopes_ids = [scope.id for scope in db_scopes]
    ref_scopes_ids = ['usr:administrator', 'usr:engineer', 'usr:guest', 'all:administrator', 'all:engineer',
                      'all:operator', 'all:monitoring', 'all:guest', 'test:internal_administrator',
                      'my-app:test:administrator', 'my-app:administrator', 'my-app:test:engineer',
                      'my-app:engineer', 'my-app:test:guest', 'my-app:guest']

    assert all(scope_id in db_scopes_ids for scope_id in ref_scopes_ids)

    # Check action prefix
    for prefix_ref in ['usr', 'my-app:test']:
        assert prefix_ref in db_actions_prefix

    # Check token_introspection
    token = _admin_headers['Authorization'].split(' ')[-1]
    body = {"uri": "/test", "method": "GET", "token": token}
    headers = {"X-api-url": "https://my_app/", "token": token, "Content-type": "application/x-www-form-urlencoded"}
    introspection_resp = await _api.post("/token_introspection", data=body, headers=headers)
    assert introspection_resp.status == 200, (await introspection_resp.text())

    # Post a second api with different app_name
    body = {"base_url": "https://my_app_bis/",
            "main_api": main_api_json,
            "app_name": "my-app-bis"}

    post_resp = await _api.post("/api_definition", json=body, headers=_admin_headers)
    assert post_resp.status == 201
    assert (await post_resp.text()) == "OK"

    db_scopes = await _db.collection_scopes.get_list()
    app_scope = [scope for scope in db_scopes if scope.id == 'my-app:administrator'][0]
    assert {'scope': 'my-app:test:administrator'} in app_scope.content
    app_bis_scope = [scope for scope in db_scopes if scope.id == 'my-app-bis:administrator'][0]
    assert {'scope': 'my-app-bis:test:administrator'} in app_bis_scope.content

    # Assert that both api descriptors are in database
    descriptors = await _db.collection_api_descriptors.get_list()
    descr_app_names = [descr.app_name for descr in descriptors]
    for descr_ref in ['my-app', 'my-app-bis']:
        assert descr_ref in descr_app_names


# pylint: disable=too-many-locals
async def test_with_app_name_and_subapp(init_database, init_backend_with_admin, api_path, subapp_api_path):
    """
    Test to POST API definition with an application name and a subapp
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    with open(api_path, 'r', encoding="utf-8") as main_app_yaml_file:
        main_api_json = yaml.safe_load(main_app_yaml_file.read())
    with open(subapp_api_path, 'r', encoding="utf-8") as subapp_yaml_file:
        sub_api_json = yaml.safe_load(subapp_yaml_file.read())
    body = {"base_url": "https://my_app/",
            "main_api": main_api_json,
            "subapp_apis": [{"definition": sub_api_json, "path": "/subapp1"}],
            "app_name": "my-app"}

    post_resp = await _api.post("/api_definition", json=body, headers=_admin_headers)
    assert post_resp.status == 201
    assert (await post_resp.text()) == "OK"

    db_scopes = await _db.collection_scopes.get_list()
    db_actions = await _db.collection_actions.get_list()

    # Check scope ids
    ref_scopes_ids = ['usr:administrator', 'usr:engineer', 'usr:guest', 'all:administrator', 'all:engineer',
                      'all:operator', 'all:monitoring', 'all:guest', 'test:internal_administrator',
                      'my-app:test:administrator', 'my-app:administrator', 'my-app:test:engineer',
                      'my-app:engineer', 'my-app:test:guest', 'my-app:guest', 'my-app:test:operator']
    db_scopes_ids = [scope.id for scope in db_scopes]
    assert all(scope_id in db_scopes_ids for scope_id in ref_scopes_ids)

    # Check action prefix
    db_actions_prefix = set([action.prefix for action in db_actions]
                            )  # pylint: disable=consider-using-set-comprehension
    for prefix_ref in ['usr', 'my-app:test']:
        assert prefix_ref in db_actions_prefix
    # Check action names
    db_actions_names = [action.name for action in db_actions]
    for name_ref in ['get_ping', 'sub:get_ping']:
        assert name_ref in db_actions_names

    # Check token_introspection
    token = _admin_headers['Authorization'].split(' ')[-1]
    body = {"uri": "/subapp1/test", "method": "GET", "token": token}
    headers = {"X-api-url": "https://my_app/", "token": token,
               "Content-type": "application/x-www-form-urlencoded"}
    introspection_resp = await _api.post("/token_introspection", data=body, headers=headers)
    assert introspection_resp.status == 200

# pylint: disable=too-many-locals


@pytest.mark.parametrize("endpoint_body, expected_status_code", [
    pytest.param({"uri": "/test", "method": "GET", "token": ""}, 200, id='root-path'),
    pytest.param({"uri": "/test?123", "method": "GET", "token": ""}, 200, id='query-param'),
    pytest.param({"uri": "/test/v2", "method": "GET", "token": ""}, 200, id='with-child'),
    pytest.param({"uri": "/test/v2/v3", "method": "GET", "token": ""}, 200, id='with-children'),
    pytest.param({"uri": "/test/testid/v4?test_in_query=false", "method": "GET", "token": ""}, 200,
                 id='children-and-query'),
    pytest.param({"uri": "/tetv2", "method": "GET", "token": ""}, 403, id='other-path'),
    pytest.param({"uri": "/test123", "method": "GET", "token": ""}, 403, id='included-path'),
    pytest.param({"uri": "/tes", "method": "GET", "token": ""}, 403, id='partial-path')
])
@pytest.mark.asyncio
async def test_parent_children_endpoints(init_database, init_backend_with_admin, api_path, endpoint_body,
                                         expected_status_code):
    """
    Test Parent-Children endpoints and verify
    that they have authorization or not
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    with open(api_path, 'r', encoding="utf-8") as main_app_yaml_file:
        main_api_json = yaml.safe_load(main_app_yaml_file.read())
    body = {"base_url": "https://my_app/",
            "main_api": main_api_json,
            "app_name": "my-app"}

    post_resp = await _api.post("/api_definition", json=body, headers=_admin_headers)
    assert post_resp.status == 201

    # Check token_introspection
    token = _admin_headers['Authorization'].split(' ')[-1]
    endpoint_body['token'] = token
    headers = {"X-api-url": "https://my_app/", "token": token, "Content-type": "application/x-www-form-urlencoded"}

    introspection_resp = await _api.post("/token_introspection", data=endpoint_body, headers=headers)
    assert introspection_resp.status == expected_status_code


@pytest.mark.parametrize(
    "delete_body, delete_status, failed",
    [pytest.param({"prefix": "test"}, 204, False, id="delete with prefix"),
     pytest.param({"prefix": "test", "app_name": "my-app"}, 204, False, id="delete with prefix and app_name"),
     pytest.param({"api_url": "https://my_app/"}, 204, False, id="delete with api_url"),
     pytest.param({"prefix": "notexist"}, 204, True, id="delete with bad prefix"),
     pytest.param({"api_url": "notexist"}, 204, True, id="delete with bad api_url"),
     pytest.param({}, 400, True, id="delete with empty body")
     ])
# pylint: disable=too-many-arguments,too-many-positional-arguments
async def test_delete_api_definition(init_database, init_backend_with_admin,
                                     api_path, delete_body, delete_status, failed):
    """
    Test the delete action on api_definition endpoint

    Args:
        init_database (fisxture): Database initialized
        init_backend_with_admin (fixture): Api with admin created
        api_path (str): Simple Api .yaml path
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    with open(api_path, 'r', encoding="utf-8") as main_app_yaml_file:
        main_api_json = yaml.safe_load(main_app_yaml_file.read())
    body = {"base_url": "https://my_app/", "main_api": main_api_json}
    app_name = None
    if 'app_name' in delete_body:
        app_name = delete_body['app_name']
        body["app_name"] = app_name

    post_resp = await _api.post("/api_definition", json=body, headers=_admin_headers)
    assert post_resp.status == 201

    # Check that scopes and actions are correctly created in database
    all_api_desc_before_delete = await init_database.collection_api_descriptors.get_list()
    api_descriptor = await init_database.collection_api_descriptors.get_by_prefix_app_name(
        main_api_json['info']['x-auth']['prefix']
    )
    prefix = f"{app_name}:{main_api_json['info']['x-auth']['prefix']}" if app_name else \
        main_api_json['info']['x-auth']['prefix']
    actions = await init_database.collection_actions.get_list({"prefix": prefix})
    id_regex = f"{prefix}:*"
    scopes = await init_database.db['scopes'].find({"id": {'$regex': id_regex}}).to_list(None)
    if 'app_name' in delete_body:
        hat_scopes = await init_database.db['scopes'].find(
            {"id": {'$regex': f"{delete_body['app_name']}:*"}}).to_list(None)
        assert hat_scopes
    assert api_descriptor
    assert actions
    assert scopes

    # Request the delete endpoint
    delete_resp = await _api.delete("/api_definition", json=delete_body, headers=_admin_headers)
    assert delete_resp.status == delete_status
    all_api_desc_after_delete = await init_database.collection_api_descriptors.get_list()
    api_descriptor = await init_database.collection_api_descriptors.get_by_prefix_app_name(
        main_api_json['info']['x-auth']['prefix']
    )
    actions = await init_database.collection_actions.get_list({"prefix": prefix})
    scopes = await init_database.db['scopes'].find({"id": {'$regex': id_regex}}).to_list(None)
    hat_scopes = None
    if 'app_name' in delete_body:
        hat_scopes = await init_database.db['scopes'].find(
            {"id": {'$regex': f"{delete_body['app_name']}:*"}}).to_list(None)

    if failed:
        assert len(all_api_desc_before_delete) == len(all_api_desc_after_delete)
        assert api_descriptor
        assert actions
        assert scopes
    else:
        assert len(all_api_desc_before_delete) - 1 == len(all_api_desc_after_delete)
        assert not api_descriptor
        assert not actions
        assert not scopes
        assert not hat_scopes
