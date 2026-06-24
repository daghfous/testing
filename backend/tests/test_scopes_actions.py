# pylint: disable=too-many-lines
# pylint: disable=no-member
"""
Scopes/actions tests
"""
from contextlib import ExitStack as DoesNotRaise

from pymongo.collection import DeleteResult
import pytest
import pytest_asyncio
from yarl import URL

from ateme.openapi import HTTPConflict, Request
from ateme.um_backend.types import (
    Action,
    DEFAULT_LOCAL_IDP_NAME
)
from ateme.um_backend.request_utils import HttpHeaders

from .conftest import init_log_record, get_activity_log
from .utils import (
    TEST_SCOPE,
    MIX_SCOPE,
    NEW_USER,
    NEW_SCOPE,
    APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
    APP_SM_DEFAULT_BASIC_SCOPE_2
)

DEFAULT_SCOPES_PAGE_LIMIT = 10

@pytest_asyncio.fixture(scope="function", name="init_scopes")
async def _init_scopes(init_backend_with_admin, request):
    """

    This fixture inherit init_backend_with_admin fixture and create n scopes based on the NEW_SCOPE.
    """
    # Default to 1 if no param was provided
    nb_scopes = getattr(request, "param", 1)
    _api, backend, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    scopes = []
    for i in range(nb_scopes):
        scope = NEW_SCOPE.to_dict()
        scope["id"] = scope['id'].replace("wheel", f"wheel_{i}") if i > 0 else scope['id']
        scope["label"] = scope['label'].replace("wheel", f"wheel_{i}") if i > 0 else scope['label']
        scope["title"] = scope['title'].replace("wheel", f"wheel_{i}") if i > 0 else scope['title']
        scopes.append(scope)
    resp = await _api.post("/scopes", json=scopes, headers=_admin_headers)
    assert resp.status == 200
    assert (await resp.json()) == {"body": "All required scopes added"}

    if nb_scopes > 0: # As we want to have the use case with 0 scope in DB, we create extra scopes only if nb_scopes > 0
        # Add 2 extra scopes belonging to the application 'sm', required to filter by app_name
        resp = await _api.post("/scopes",
                               json=[APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1.to_dict(),
                                     APP_SM_DEFAULT_BASIC_SCOPE_2.to_dict()], headers=_admin_headers)
        assert resp.status == 200

    try:
        yield init_backend_with_admin, nb_scopes
    finally:
        # Cleanup scopes
        for i in range(nb_scopes):
            scope_id = NEW_SCOPE.id.replace("wheel", f"wheel_{i}") if i > 0 else NEW_SCOPE.id
            resp = await _api.delete(f"/scopes/{scope_id}", headers=_admin_headers)
            assert resp.status in [200, 404]
        if nb_scopes > 0:
            resp = await _api.delete(f"/scopes/{APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1.id}", headers=_admin_headers)
            assert resp.status in [200, 404]
            # delete directly from db as it is a default scope, not allowed through the api
            res = await backend.db.collection_scopes.remove_by_id(_id=APP_SM_DEFAULT_BASIC_SCOPE_2.id)
            assert res.acknowledged is True

async def test_scopes(init_backend_with_admin, mocker):
    """

    :return:
    """
    # pylint: disable=too-many-statements,too-many-locals
    _api, _, _admin_token = init_backend_with_admin
    _user = "admin"
    _idp_name = "local"
    _headers = {
        "Authorization": f"Bearer {_admin_token}",
        HttpHeaders.X_USER: _user,
        HttpHeaders.X_IDP_NAME: _idp_name
    }

    # Fail to create scope without id
    resp = await _api.post(
        "/scopes",
        json=[{"content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}]}],
        headers=_headers,
    )
    assert resp.status == 400

    # Fail to create scope without label
    resp = await _api.post(
        "/scopes",
        json=[{"id": "usr:get_test", "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}]}],
        headers=_headers,
    )
    assert resp.status == 400

    # Create scopes
    resp = await _api.post(
        "/scopes",
        json=[
            {
                "id": "usr:full_access",
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "usr:restricted",
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "usr:test_scope_description",
                "label": "usr",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
                "description": "test_create_description",
            },
            {
                "id": "usr:instructor",
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
        ],
        headers=_headers,
    )
    assert resp.status == 200

    # Add new scope thanks to the /v2 api
    custom_scope_id = "usr:custom"
    q, handler = init_log_record()
    resp = await _api.post(
        "/v2/scopes",
        json={
                "id": custom_scope_id,
                "label": "custom scope",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
        headers=_headers,
    )
    assert resp.status == 201
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} added scope {custom_scope_id}"

    # failed to add an already existing scope
    q, handler = init_log_record()
    resp = await _api.post(
        "/v2/scopes",
        json={
                "id": custom_scope_id,
                "label": "custom scope",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
        headers=_headers,
    )
    assert resp.status == 409
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} failed to add scope {custom_scope_id}"

    # Get all scopes
    resp = await _api.get("v2/scopes?mode=expert", headers=_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 13

    # Add existing scope => fail
    resp = await _api.post(
        "/scopes",
        json=[
            {
                "id": "usr:full_access",
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            }
        ],
        headers=_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    assert body["body"] == "Scopes added except ['usr:full_access'] that already are in scopes db"

    # Remove non existing scope => fail
    resp = await _api.delete(
        "/scopes",
        json=[
            {"id": "usr:full_access", "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}]},
            {"id": "fail", "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}]},
        ],
        headers=_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    assert body["body"] == "Scopes removed except ['fail'] that are not in scopes db or are default ones"

    # Remove default scopes => fail
    resp = await _api.delete("/scopes", json=[{"id": "operator"}, {"id": "engineer"}], headers=_headers)
    assert resp.status == 200
    body = await resp.json()
    assert body["body"] == "Scopes removed except ['operator', 'engineer'] " \
                           "that are not in scopes db or are default ones"

    # Get all scopes after deletion
    resp = await _api.get("v2/scopes?mode=expert", headers=_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 12

    # Update scopes
    for _id in ["usr:restricted", "usr:instructor"]:
        q, handler = init_log_record()
        resp = await _api.patch(
            f"/scopes/{_id}",
            json={"label": "usr", "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}},
                                              {"action": "usr:ping", "policy": "allow", "resource": {}}]},
            headers=_headers,
        )
        assert resp.status == 200
        log = get_activity_log(q, handler)
        assert log.message == f"{_user}:{_idp_name} updated scope {_id}, adding action usr:get_test, action usr:ping"

    # Patch scopes again
    for _id in ["usr:restricted", "usr:instructor"]:
        body = {"label": "usr",
                "content": [{"action": "usr:get_test",
                             "policy": "allow",
                             "resource": {}}]}
        if _id == "usr:instructor":
            body['description'] = "test_update_description"
        resp = await _api.patch(
            f"/scopes/{_id}",
            json=body,
            headers=_headers
        )
        assert resp.status == 200

    # Update custom scope (based on scopes, not action)
    q, handler = init_log_record()
    resp = await _api.patch(
        f"/scopes/{custom_scope_id}",
        json={"label": "custom scope",
              "content": [{"scope": "usr:instructor"},
                          {"scope": "usr:restricted"}]},
        headers=_headers)
    assert resp.status == 200
    log = get_activity_log(q, handler)
    assert log.message == (f"{_user}:{_idp_name} updated scope {custom_scope_id},"
                           f" adding scope usr:instructor, scope usr:restricted")

    # Patch unexist scopes
    q, handler = init_log_record()
    _id = "std:invalid"
    resp = await _api.patch(
        f"/scopes/{_id}",
        json={"label": "usr", "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}]},
        headers=_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body == f"Can't find scope {_id}"
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} failed to update scope {_id}"

    # Patch scopes DB in trouble
    mocker.patch("ateme.um_backend.dao.collection_scopes.CollectionScopes.update_by_id", return_value=None)
    resp = await _api.patch(
        "/scopes/usr:instructor",
        json={"label": "usr", "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}]},
        headers=_headers,
    )
    assert resp.status == 500
    body = await resp.text()
    assert body == 'Update scope usr:instructor failed'
    mocker.stopall()

    q, handler = init_log_record()
    resp = await _api.delete(f"/scopes/{custom_scope_id}", headers=_headers)
    assert resp.status == 200
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} removed scope {custom_scope_id}"

    # Get all scopes after update
    resp = await _api.get("v2/scopes?mode=expert", headers=_headers)
    assert resp.status == 200
    body = await resp.json()
    scopes_data_expected = [
        {
            "id": "usr:administrator",
            "label": "Users",
            "content": [{'action': 'usr:get_admin', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:create_admin_user', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_current_user', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_current_user_actions', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:update_user_preferences', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:change_password', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:change_session_timeout', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:update_configuration', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_configuration', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:store_idp_config', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_idp_configs', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:validate_idp_config', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_idp_config_by_name', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:update_idp_config', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:remove_idp_config', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:logout', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:deprecated_change_password', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_scopes', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:store_scope', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_scopes_deprecated', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:store_scopes', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:remove_scopes', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_scope_by_id', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:update_scope_by_id', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:remove_scope_by_id', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_actions', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:force_user_disconnection', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:change_token_expiration', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:add_user', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_users', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:add_users', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:delete_users', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:deprecated_update_users', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_user_by_name', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:update_user_by_name', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:remove_user_by_name', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:reactivate_user_by_name', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_sync_data', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:import_sync_data', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:export_full_configuration', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:import_full_configuration', 'policy': 'allow', 'resource': {}},
                        {'action': 'usr:get_sessions','policy': 'allow','resource': {},},
                        {'action': 'usr:disable_session','policy': 'allow','resource': {},},],
            "default": True,
            "title": "Administrator - users",
            "description": "Role granting full access to all users, roles, and identity management functionalities.",
        },
        {
            "id": "usr:engineer",
            "label": "Users",
            # pylint: disable=line-too-long
            "content": [{'action': 'usr:get_current_user', 'policy': 'allow', 'resource': {}}, {'action': 'usr:get_current_user_actions', 'policy': 'allow', 'resource': {}}, {'action': 'usr:update_user_preferences', 'policy': 'allow', 'resource': {}}, {'action': 'usr:change_password', 'policy': 'allow', 'resource': {}}, {'action': 'usr:logout', 'policy': 'allow', 'resource': {}}, {'action': 'usr:deprecated_change_password', 'policy': 'allow', 'resource': {}}, {'action': 'usr:get_scopes', 'policy': 'allow', 'resource': {}}, {'action': 'usr:get_scopes_deprecated', 'policy': 'allow', 'resource': {}}, {'action': 'usr:force_user_disconnection', 'policy': 'allow', 'resource': {}}, {'action': 'usr:get_users', 'policy': 'allow', 'resource': {}}],
            "default": True,
            "title": "Engineer - users",
            "description": "Role allowing configuration-related actions with additional permissions on users, roles, and identity management functionalities.",
        },
        {
            "id": "usr:guest",
            "label": "Users",
            # pylint: disable=line-too-long
            "content": [{'action': 'usr:get_current_user', 'policy': 'allow', 'resource': {}}, {'action': 'usr:get_current_user_actions', 'policy': 'allow', 'resource': {}}, {'action': 'usr:update_user_preferences', 'policy': 'allow', 'resource': {}}, {'action': 'usr:change_password', 'policy': 'allow', 'resource': {}}, {'action': 'usr:logout', 'policy': 'allow', 'resource': {}}, {'action': 'usr:deprecated_change_password', 'policy': 'allow', 'resource': {}}],
            "default": True,
            "title": "Guest - users",
            # pylint: disable=line-too-long
            "description": "Role with minimal access, limited to viewing personal information, logging out, and changing the password.",
        },
        {
            "id": "all:administrator",
            "label": "Global Role",
            "content": [{"scope": "usr:administrator"}],
            "title": "Administrator",
            "description": "Role granting full access to all features and functionalities of the applications.",
            "default": True,
        },
        {
            "id": "all:engineer",
            "label": "Global Role",
            "content": [{"scope": "usr:engineer"}],
            "title": "Engineer",
            "description": "Role allowing configuration management across all features of the applications.",
            "default": True,
        },
        {
            "id": "all:operator",
            "label": "Global Role",
            "content": [{"scope": "usr:guest"}],
            "title": "Operator",
            "description": "Role permitting control and operational actions across all features of the applications.",
            "default": True,
        },
        {
            "id": "all:monitoring",
            "label": "Global Role",
            "content": [{"scope": "usr:guest"}],
            "title": "Monitoring",
            "description": "Role providing view-only access across all features of the applications.",
            "default": True,
        },
        {
            "id": "all:guest",
            "label": "Global Role",
            "content": [{"scope": "usr:guest"}],
            "title": "Guest",
            "description": "Role with minimal access, restricted to basic usage and limited features.",
            "default": True,
        },
        {
            "id": "usr:restricted",
            "label": "usr",
            "description": "description",
            "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            "title": "usr restricted",
        },
        {
            "id": "usr:test_scope_description",
            "label": "usr",
            "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            "description": "test_create_description",
            "title": "usr test_scope_description",
        },
        {
            "id": "usr:instructor",
            "label": "usr",
            "description": "test_update_description",
            "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            "title": "usr instructor",
        }
    ]
    # sort expected scope list by id to match with returned result
    scopes_data_expected = sorted(scopes_data_expected, key=lambda d: d['id'])

    for expected_scope, actual_scope in zip(scopes_data_expected, body):
        assert expected_scope == actual_scope, f"Expected: {expected_scope}, but got: {actual_scope}"

@pytest.mark.parametrize("settings_page_limit", [
    0, # undefined limit
    DEFAULT_SCOPES_PAGE_LIMIT
])
@pytest.mark.parametrize("init_scopes", [
    0,
    1,
    5,
    DEFAULT_SCOPES_PAGE_LIMIT,
    DEFAULT_SCOPES_PAGE_LIMIT + 10
], indirect=True)
async def test_get_scopes_pagination(init_scopes, settings_page_limit):
    """
    Test the pagination of the GET /v2/scopes endpoint with various ranges.
    The db is filled with nb_scopes scopes having a label starting with the pattern "wheel".
    The backend is configured with a settings_page_limit for scopes pagination having 2 possible values:
    0 (no limit) or DEFAULT_SCOPES_PAGE_LIMIT.
    The get_scopes requests are performed only on these scopes
    Test cases:
    - no range specified
    - range to get a partial result
    - range to request exactly all the scopes in db
    - range to request the settings_page_limit scopes whatever the nb of scopes in db
    - range to get the first scope
    - range to get a partial result, range within [0, settings_page_limit]
    - range with 'end' greater than the settings_page_limit or the total scopes in db
    - range with 'end' < 'start'
    - retrieval all the scopes in db with successive requests having consecutive ranges

    Args:
        init_scopes:

    Returns:

    """
    # pylint: disable=too-many-statements,too-many-branches,too-many-locals
    (_api, backend, _admin_token), nb_scopes = init_scopes
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    backend.settings.scopes_page_limit = settings_page_limit

    if settings_page_limit == 0:
        # limit = 0 means no limit set at the backend level: no pagination enforced

        # Get all scopes without pagination:
        # - status code 200
        # - content-range header function to the nb of scopes in db
        resp = await _api.get("/v2/scopes?mode=expert&label=wheel", headers=_admin_headers)
        assert resp.status == 200, f"status code should be 200 but is {resp.status}"
        body = await resp.json()
        expected_returned_scopes_nb = nb_scopes
        assert resp.headers["Accept-Ranges"] == "scopes" # no limit set -> no limit in accept-ranges
        assert len(body) == expected_returned_scopes_nb

        if nb_scopes != 0:
            assert resp.headers["Content-Range"] == f"scopes 0-{expected_returned_scopes_nb-1}/{nb_scopes}"
        else:
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"

        # range to get a partial result: 2 scopes from 2 to 3
        # - status code 416 if nb_scopes in db = 0
        # - status code 206 if nb_scopes in db > 0
        start = 2
        end = 3
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        if nb_scopes in [0, 1]:
            # range out of db scopes
            assert resp.status == 416, f"status code should be 416 but is {resp.status}"
            assert resp.headers["Accept-Ranges"] == "scopes"
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"
        else:
            # more scopes in db than requested
            assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            body = await resp.json()
            assert len(body) == end - start + 1
            assert resp.headers["Accept-Ranges"] == "scopes"
            assert resp.headers["Content-Range"] == f"scopes {start}-{end}/{nb_scopes}"
    else:
        # limit > 0 set at the backend level:
        # the maximum number of scopes returned by a get_scopes request is this limit

        # Get all scopes without pagination/range specified:
        # - status code 200 if no scope in db or less than the limit, 206 otherwise
        # - content-range header function to the nb of scopes in db
        resp = await _api.get("/v2/scopes?mode=expert&label=wheel", headers=_admin_headers)
        assert resp.status == 200 if nb_scopes <= settings_page_limit else 206,\
            f"status code should be 200 or 206 but is {resp.status}"
        body = await resp.json()
        all_wheel_scopes = body
        expected_returned_scopes_nb = min(nb_scopes, settings_page_limit)
        assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
        assert len(body) == expected_returned_scopes_nb
        if nb_scopes != 0:
            assert resp.headers["Content-Range"] == f"scopes 0-{expected_returned_scopes_nb-1}/{nb_scopes}"
        else:
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"

        # range to request exactly all the scopes in db
        # - status code 416 if nb_scopes in db = 0
        # - status code 200 if nb_scopes in db <= limit
        # - status code 206 if nb_scopes in db > limit
        start = 0 # start from the beginning
        end = max(nb_scopes - 1, 0) # end to the last scope if any, else 0
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        if nb_scopes == 0:
            assert resp.status == 416, f"status code should be 416 but is {resp.status}"
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"
        else:
            # the nb of scopes returned is limited to settings_page_limit
            expected_returned_scopes_nb = min(nb_scopes, settings_page_limit)
            body = await resp.json()
            assert len(body) == expected_returned_scopes_nb
            if nb_scopes > settings_page_limit:
                assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            else:
                assert resp.status == 200, f"status code should be 200 but is {resp.status}"
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes {start}-{expected_returned_scopes_nb-1}/{nb_scopes}"

        # range to request the settings_page_limit scopes whatever the nb of scopes in db
        # - status code 416 if nb_scopes in db = 0 or nb_scopes in db < requested limit
        # - status code 200 if nb_scopes in db = requested limit
        # - status code 206 if nb_scopes in db > requested limit
        start = 0
        end = settings_page_limit - 1
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        if nb_scopes == 0 or nb_scopes < settings_page_limit:
            # there are less scopes in db than the settings_page_limit requested
            assert resp.status == 416, f"status code should be 416 but is {resp.status}"
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"
        else:
            if nb_scopes == settings_page_limit:
                # exactly settings_page_limit scopes in db: all are returned
                assert resp.status == 200, f"status code should be 200 but is {resp.status}"
            elif nb_scopes > settings_page_limit:
                assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            body = await resp.json()
            assert len(body) == min(nb_scopes, end - start + 1)
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes {start}-{end}/{nb_scopes}"

        # range to get the first scope
        # - status code 416 if nb_scopes in db = 0
        # - status code 200 if nb_scopes in db = 1
        # - status code 206 if nb_scopes in db > 1
        start = 0
        end = 0
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        if nb_scopes == 0:
            assert resp.status == 416, f"status code should be 416 but is {resp.status}"
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"
        else:
            assert resp.status == 206 if nb_scopes > 1 else 200,\
                f"status code should be 206 or 200 but is {resp.status}"
            body = await resp.json()
            assert len(body) == end - start + 1
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes {start}-{end}/{nb_scopes}"

        # range to get a partial result, range within [0, settings_page_limit]: 2 scopes from 2 to 3
        # - status code 416 if nb_scopes in db = 0 or 1
        # - status code 206 if nb_scopes in db > 2
        start = 2
        end = 3
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        if nb_scopes in [0, 1]:
            # range out of db scopes
            assert resp.status == 416, f"status code should be 416 but is {resp.status}"
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"
        else:
            # more scopes in db than requested
            assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            body = await resp.json()
            assert len(body) == end - start + 1
            assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
            assert resp.headers["Content-Range"] == f"scopes {start}-{end}/{nb_scopes}"

        # range with 'end' greater than the settings_page_limit or the total scopes in db
        # - status code 416 whatever the nb scopes in db
        start = 1 # start inside the limit
        end = max(settings_page_limit, nb_scopes) + 1  # +1 to have a end outside the limit or the nb of scopes in db
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        assert resp.status == 416, f"status code should be 416 but is {resp.status}"
        assert resp.headers["Accept-Ranges"] == f"scopes {settings_page_limit}"
        assert resp.headers["Content-Range"] == f"scopes */{nb_scopes}"

        # range with 'end' < 'start'
        # - status code 400 whatever the nb scopes in db
        start = 1 # start valid
        end = 0   # end < start
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        assert resp.status == 400, f"status code should be 400 but is {resp.status}"
        assert await resp.text() == 'Invalid range requested 1-0'

        # range with 'start' < 0
        # - status code 400 whatever the nb scopes in db (openapi validation error)
        start = -1 # start valid
        end = 1   # end < start
        resp = await _api.get(f"/v2/scopes?mode=expert&label=wheel&range={start}-{end}", headers=_admin_headers)
        assert resp.status == 400, f"status code should be 400 but is {resp.status}"
        assert "Failed validating pattern in schema[root]" in await resp.text()

        # retrieval all the scopes in db with successive requests having consecutive ranges
        if nb_scopes == 5 and settings_page_limit != 0:
            resp = await _api.get("/v2/scopes?mode=expert&label=wheel&range=0-0", headers=_admin_headers)
            scopes_0_0 = await resp.json()
            assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            assert len(scopes_0_0) == 1
            assert scopes_0_0 == all_wheel_scopes[0:1]
            resp = await _api.get("/v2/scopes?mode=expert&label=wheel&range=1-3", headers=_admin_headers)
            scopes_1_3 = await resp.json()
            assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            assert len(scopes_1_3) == 3
            assert scopes_1_3 == all_wheel_scopes[1:4]
            resp = await _api.get("/v2/scopes?mode=expert&label=wheel&range=4-4", headers=_admin_headers)
            scopes_4_4 = await resp.json()
            assert resp.status == 206, f"status code should be 206 but is {resp.status}"
            assert len(scopes_4_4) == 1
            assert scopes_4_4 == all_wheel_scopes[4:5]
            assert len(scopes_0_0) + len(scopes_1_3) + len(scopes_4_4) == len(all_wheel_scopes),\
                "all scopes should have been retrieved"

@pytest.mark.parametrize("init_scopes", [
    5
], indirect=True)
async def test_get_scopes_filter(init_scopes):
    """
    Test the pagination of the GET /v2/scopes endpoint with various filters
    The db is filled with nb_scopes scopes having a label starting with the pattern "wheel".
    The get_scopes requests is performed only on these scopes

    Args:
        init_scopes:

    Returns:

    """
    # pylint: disable=too-many-statements,too-many-branches
    (_api, _, _admin_token), _ = init_scopes
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Get all scopes:
    resp = await _api.get("/v2/scopes", headers=_admin_headers)
    assert resp.status == 200
    all_scopes = await resp.json()
    all_scopes_nb = len(all_scopes)

    resp = await _api.get("/v2/scopes?mode=expert", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert all_scopes == body

    resp = await _api.get("/v2/scopes?sort=-id", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert body == list(reversed(all_scopes))

    resp = await _api.get("/v2/scopes?mode=expert&sort=id", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert all_scopes_nb == len(body)
    assert body == all_scopes

    resp = await _api.get("/v2/scopes?mode=basic", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 15

    resp = await _api.get("/v2/scopes?app_name=sm", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2

    resp = await _api.get("/v2/scopes?app_name=unknown", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 0

    resp = await _api.get("/v2/scopes?type=administrator", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2

    resp = await _api.get("/v2/scopes?label=sm_non_default_", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 1

    resp = await _api.get("/v2/scopes?label=not_present", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 0

    resp = await _api.get("/v2/scopes?default=false", headers=_admin_headers)
    assert resp.status == 200
    non_default_scopes = await resp.json()
    assert len(non_default_scopes) == 6

    resp = await _api.get("/v2/scopes?default=true", headers=_admin_headers)
    assert resp.status == 200
    default_scopes = await resp.json()
    assert len(default_scopes) == 9
    assert all(scope in default_scopes or scope in non_default_scopes for scope in all_scopes)

    resp = await _api.get(
        "/v2/scopes?mode=expert&sort=id&app_name=sm&type=guest&label=scope_2&range=0-0",
        headers=_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    # 'internal' not returned
    scope_filtered = {k: v for k, v in APP_SM_DEFAULT_BASIC_SCOPE_2.to_dict().items() if k != "internal"}
    assert body == [scope_filtered]

    resp = await _api.get("/v2/scopes?mode=expert&sort=id&app_name=sm&type=guest&label=scope_x", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 0

async def test_get_actions(init_backend_with_admin):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    resp = await _api.get("/actions", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, list)
    assert len(body) == 47
    # TODO verify where are from the additionnal actions
#       assert len(body) == 41
    assert [Action.from_dict(item).validate() for item in body]

async def test_get_scope_by_name(init_scopes):
    """

    :return:
    """
    (_api, _, _admin_token), _ = init_scopes
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Not found case
    resp = await _api.get("/scopes/azerty", headers=_admin_headers)
    assert resp.status == 404

    # Success case
    resp = await _api.get(f"/scopes/{NEW_SCOPE.id}", headers=_admin_headers)
    assert resp.status == 200
    scope = await resp.json()
    assert scope, "scope should be define"
    assert isinstance(scope, dict), "scope should be type of dict"
    assert scope.get('content') == NEW_SCOPE.content


async def test_create_user_with_duplicate_scope(init_scopes):
    """

    Bug ms-1506, which allow to create or update a user with duplicate scope
    :return:
    """
    (_api, _, _admin_token), _ = init_scopes
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    new_scopes = [NEW_SCOPE.id, NEW_SCOPE.id]
    user = {'username': 'johndoe', 'password': 'p4ss0rD!AA', 'scopes': new_scopes}
    # Create user
    resp = await _api.post("/users", json=[user], headers=_admin_headers)
    assert resp.status == 201
    insert_res = await resp.json()
    assert insert_res == {}

    resp = await _api.get(f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user['username']}", headers=_admin_headers)
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted([NEW_SCOPE.id])

    resp = await _api.patch(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user['username']}",
        json={"scopes": new_scopes},
        headers=_admin_headers,
    )
    assert resp.status == 200
    update_res = await resp.text()

    assert update_res == "OK"

    resp = await _api.get(f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user['username']}", headers=_admin_headers)
    assert resp.status == 200
    user_result = await resp.json()
    assert user_result["scopes"] == [NEW_SCOPE.id]


async def test_update_scope_by_id(init_scopes, mocker):
    """

    :return:
    """
    (_api, _, _admin_token), _ = init_scopes
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    new_scope_data = {'label': 'usr', 'content': []}
    # Update scope DB in trouble

    async def mock_update_by_id(*_):
        return None
    mocker.patch("ateme.um_backend.dao.collection_scopes.CollectionScopes.update_by_id", mock_update_by_id)
    resp = await _api.patch("/scopes/user", json=new_scope_data, headers=_admin_headers)
    assert resp.status == 500
    mocker.stopall()

    # Update non existing scope
    resp = await _api.patch("/scopes/user", json=new_scope_data, headers=_admin_headers)
    assert resp.status == 404

    # Update scope
    new_scope_data = {'label': 'usr', 'content': []}
    resp = await _api.patch(f"/scopes/{NEW_SCOPE.id}", json=new_scope_data, headers=_admin_headers)
    assert resp.status == 200
    res = await resp.text()

    # Get scope
    assert res, 'Result should be define'
    resp = await _api.get(f"/scopes/{NEW_SCOPE.id}", headers=_admin_headers)
    assert resp.status == 200
    scope = await resp.json()
    assert scope, "scope should be define"
    assert isinstance(scope, dict), "scope should be type of dict"
    assert scope.get('content') == new_scope_data.get('content')


async def test_remove_scope_by_id(init_scopes, mocker):
    """

    :return:
    """
    (_api, _, _admin_token), _ = init_scopes
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Delete inexisting scope
    resp = await _api.delete("/scopes/user", headers=_admin_headers)
    assert resp.status == 404

    # Delete scope DB in trouble not acknowledged
    mocker.patch("ateme.um_backend.dao.collection_scopes.CollectionScopes.remove_by_id",
                 return_value=DeleteResult(raw_result=None, acknowledged=False))
    resp = await _api.delete(f"/scopes/{NEW_SCOPE.id}", headers=_admin_headers)
    assert resp.status == 500
    assert await resp.text() == f"Delete scope {NEW_SCOPE.id} failed"
    mocker.stopall()

    # Delete scope DB in trouble deleted_count = 0
    mocker.patch("ateme.um_backend.dao.collection_scopes.CollectionScopes.remove_by_id",
                 return_value=DeleteResult(raw_result={'n': 0}, acknowledged=True))
    resp = await _api.delete(f"/scopes/{NEW_SCOPE.id}", headers=_admin_headers)
    assert resp.status == 404
    assert await resp.text() == f"Delete scope {NEW_SCOPE.id} failed"
    mocker.stopall()

    resp = await _api.delete(f"/scopes/{NEW_SCOPE.id}", headers=_admin_headers)
    assert resp.status == 200
    res = await resp.text()
    assert res, 'Result should be define'
    resp = await _api.get("/scopes/{NEW_SCOPE.id}", headers=_admin_headers)
    assert resp.status == 404
    res = await resp.text()
    assert res == '404: Not Found', "scope should delete"


@pytest.mark.parametrize("scope_id", ["usr:wheel", "all:wheel"])
async def test_remove_scope_check_user(init_backend_with_admin, scope_id):
    """

    :return:
    """
    # pylint: disable=too-many-statements
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Create scopes
    resp = await _api.post(
        "/scopes",
        json=[
            {
                "id": scope_id,
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "usr:bit",
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "lic:bit",
                "label": "lic",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
        ],
        headers=_admin_headers,
    )
    assert resp.status == 200

    # Create user
    user_1 = {'username': f'johndoe_{scope_id}_1',
              'password': 'p4ss0rD!AA',
              'scopes': [scope_id, "usr:bit", "lic:bit"]}
    user_2 = {'username': f'johndoe_{scope_id}_2',
              'password': 'p4ss0rD!AA',
              'scopes': [scope_id, "usr:bit", "lic:bit"]}
    resp = await _api.post("/users", json=[user_1, user_2], headers=_admin_headers)
    assert resp.status == 201
    insert_res = await resp.json()
    assert insert_res == {}

    # Delete the scope scope_id
    resp = await _api.delete(f"/scopes/{scope_id}", headers=_admin_headers)
    assert resp.status == 200
    res = await resp.text()
    assert res, 'Result should be define'

    # Users should only have usr:bit and lic:bit scopes
    resp = await _api.get(f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user_1['username']}", headers=_admin_headers)
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted(["usr:bit", "lic:bit"])
    assert not all(scope_id in scope for scope in user_result["scopes"])

    resp = await _api.get(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user_1['username']}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted(["usr:bit", "lic:bit"])
    assert not all(scope_id in scope for scope in user_result["scopes"])

    # Delete the scope usr:bit
    resp = await _api.delete("/scopes/usr:bit", headers=_admin_headers)
    assert resp.status == 200
    res = await resp.text()
    assert res, 'Result should be define'

    # Users should have usr:guest and lic:bit scopes
    resp = await _api.get(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user_1['username']}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted(["usr:guest", "lic:bit"])
    assert not all(scope_id in scope for scope in user_result["scopes"])

    resp = await _api.get(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user_2['username']}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted(["usr:guest", "lic:bit"])
    assert not all(scope_id in scope for scope in user_result["scopes"])

    # Delete the scope lic:bit
    resp = await _api.delete("/scopes/lic:bit", headers=_admin_headers)
    assert resp.status == 200
    res = await resp.text()
    assert res, 'Result should be define'

    # Users should only have the usr:guest scope
    resp = await _api.get(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user_1['username']}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted(["usr:guest"])
    assert not all(scope_id in scope for scope in user_result["scopes"])

    resp = await _api.get(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{user_2['username']}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    user_result = await resp.json()
    assert sorted(user_result["scopes"]) == sorted(["usr:guest"])
    assert not all(scope_id in scope for scope in user_result["scopes"])


async def test_mix_scope(init_backend_with_admin):
    """

    test mix scope
    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    resp = await _api.post("/scopes", json=[TEST_SCOPE.to_dict(), MIX_SCOPE.to_dict()], headers=_admin_headers)
    assert resp.status == 200

    # Create user
    resp = await _api.post(
        "/users",
        json=[{"username": NEW_USER.username, "password": NEW_USER.password, "scopes": NEW_USER.scopes}],
        headers=_admin_headers,
    )
    assert resp.status == 201

    resp = await _api.post(
        "/token",
        json={"username": NEW_USER.username, "password": NEW_USER.password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()

    user_token = body["access_token"]
    assert user_token


@pytest.mark.parametrize(
    "already_exists, assert_raise",
    [
        pytest.param(False, DoesNotRaise(), id="create-scope-success"),
        pytest.param(
            True,
            pytest.raises(
                HTTPConflict, match="Scope with id 'test:scope' already exists"
            ),
            id="create-scope-conflict",
        )
    ])
async def test_store_scope(mocker, init_api, already_exists, assert_raise):
    """
    Test single scope creation
    """
    mocker.patch(
        'ateme.um_backend.dao.collection_scopes.CollectionScopes.store',
        return_value=not already_exists
    )
    with assert_raise:
        await init_api.store_scope(Request(parameters={}, body={'id': 'test:scope'},
                                           headers={}, url=URL(''), method='', remote=''))

@pytest.mark.parametrize(
    "scopes, expected_result_basic_mode, expected_not_in_result_basic_mode",
    [
        (
            # Scopes to post
            [{
                "id": "pmf-release-name:apm:administrator",
                "label": "app manager custom scope",
                "description": "description",
                "content": [{"action": "apm:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "pmf-release-name:apmon:administrator",
                "label": "app monitoring custom scope",
                "description": "description",
                "content": [{"action": "apmon:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "app-name-one:administrator",
                "label": "custom application scope",
                "description": "description",
                "content": [{"action": "app:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "usr:monitoring",
                "label": "custom user management scope",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            },
            # The last ones shall be excluded from the basic mode result
            {
                "id": "pmf-release-name:administrator",
                "label": "custom application scope",
                "description": "description",
                "content": [{"action": "pmf:get_test", "policy": "allow", "resource": {}}],
            },
            {
                "id": "app-name-test:app:administrator",
                "label": "custom application scope",
                "description": "description",
                "content": [{"action": "app:get_test", "policy": "allow", "resource": {}}],
            }],
            # expected_result_basic_mode
            [
                {
                    'id': 'app-name-one:administrator',
                    'label': 'custom application scope',
                    'description': 'description',
                    'content': [
                    {
                        'action': 'app:get_test',
                        'policy': 'allow',
                        'resource': {

                        }
                    }
                    ],
                    'title': 'custom application scope administrator'
                },
                {
                    'id': 'pmf-release-name:apm:administrator',
                    'label': 'app manager custom scope',
                    'description': 'description',
                    'content': [
                    {
                        'action': 'apm:get_test',
                        'policy': 'allow',
                        'resource': {

                        }
                    }
                    ],
                    'title': 'app manager custom scope apm'
                },
                {
                    'id': 'pmf-release-name:apmon:administrator',
                    'label': 'app monitoring custom scope',
                    'description': 'description',
                    'content': [
                    {
                        'action': 'apmon:get_test',
                        'policy': 'allow',
                        'resource': {

                        }
                    }
                    ],
                    'title': 'app monitoring custom scope apmon'
                },
                # usr scope that should be presented also in basic mode
                {
                    'id': 'usr:monitoring',
                    'label': 'custom user management scope',
                    'description': 'description',
                    'content': [
                    {
                        'action': 'usr:get_test',
                        'policy': 'allow',
                        'resource': {

                        }
                    }
                    ],
                    'title': 'custom user management scope monitoring'
                }
            ],
            # expected_not_in_result_basic_mode
            [
                {
                    "id": "pmf-release-name:administrator",
                    "label": "custom application scope",
                    "description": "description",
                    "content": [{"action": "pmf:get_test", "policy": "allow", "resource": {}}],
                    'title': 'custom application scope administrator',
                },
                {
                    "id": "app-name-test:app:administrator",
                    "label": "custom application scope",
                    "description": "description",
                    "content": [{"action": "app:get_test", "policy": "allow", "resource": {}}],
                   'title': 'custom application scope app',
                }
            ]
        ),
        (
            # Scopes to post
            [{
                "id": "custom:custom_scope",
                "label": "my custom scope",
                "description": "description",
                "content": [{"action": "apm:get_test", "policy": "allow", "resource": {}}],
            }],
            # expected_result_basic_mode
            [
                {'id': 'custom:custom_scope',
                 'label': 'my custom scope',
                 'description': 'description',
                 'content': [{'action': 'apm:get_test', 'policy': 'allow', 'resource': {}}],
                 'title': 'my custom scope custom_scope'},
            ],
            # expected_not_in_result_basic_mode
            []
        )

    ]
)
async def test_scopes_basic_and_expert_mode(
    init_backend_with_admin,
    init_database,
    scopes,
    expected_result_basic_mode,
    expected_not_in_result_basic_mode
):
    """
    Test GET Scopes basic mode
    :param api_descriptors:
    :param scopes:
    :param expected_result_basic_mode:
    :param expected_not_in_result_basic_mode:
    :return:
    """
    # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    _api, _, _admin_token = init_backend_with_admin
    _db = init_database
    _user = "admin"
    _idp_name = "local"
    _headers = {
        "Authorization": f"Bearer {_admin_token}",
        HttpHeaders.X_USER: _user,
        HttpHeaders.X_IDP_NAME: _idp_name
    }

    for scope in scopes:
        # Create scopes
        resp = await _api.post(
            "/v2/scopes",
            json=scope,
            headers=_headers,
        )
        assert resp.status == 201

    # Get all scopes in basic mode
    resp = await _api.get("v2/scopes?mode=basic", headers=_headers)
    assert resp.status == 200
    body = await resp.json()
    assert body
    assert all(scope in body for scope in expected_result_basic_mode)
    # Check that the not basic scopes are not in the body
    assert all(scope not in body for scope in expected_not_in_result_basic_mode)

    # In expert mode we need to have all the scopes
    resp = await _api.get("v2/scopes", headers=_headers)
    assert resp.status == 200
    body = await resp.json()
    assert body
    assert all(scope in body for scope in expected_result_basic_mode + expected_not_in_result_basic_mode)
