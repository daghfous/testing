"""Test user management logs activity
"""
import logging
import os
from queue import SimpleQueue
import sys
from yarl import URL
import pytest
from pymongo.errors import ServerSelectionTimeoutError

from ateme.openapi import Request
from ateme.um_backend.loggers import (
    LOG_ACTIVITY,
    generate_audit_log_for_user_update,
    generate_audit_log_for_scope_update,
    generate_audit_log_for_idp_config_update
)
from ateme.um_backend.request_utils import HttpHeaders
from ateme.um_backend.__main__ import main as app_main

def test_log_file(tmp_path):
    """
    Test if the log file passed as args is created and contains some logs
    """
    log_file_path = os.path.join(tmp_path, "test_log.txt")
    sys.argv = [
        "__main__.py",
        "--um-log-file", log_file_path
    ]
    try:
        app_main()
    except ServerSelectionTimeoutError:
        # Catch the exception raised by app_main (because the MongoDB server is not available)
        pass

    # Check if the log file is created and has content:
    # 'INFO um_backend main [Starting...]'
    assert os.path.exists(log_file_path)

    with open(log_file_path, 'r', encoding="utf-8") as log_file:
        log_content = log_file.read()
        assert "ATEME" in log_content
        assert "INFO um_backend main [Starting...]" in log_content


@pytest.mark.parametrize("username, idp_name, clientip", [
    ("John", "local", "127.0.0.1"),
    (None, None, None)
])
async def test_logs_add_user(init_backend_with_admin, mocker, username, idp_name, clientip):
    """ Test user creation logs """
    # pylint: disable=too-many-locals
    client, _, admin_token = init_backend_with_admin

    async def mock_is_admin(*_args, **kwargs):
        return kwargs['username'] == 'admin'
    mocker.patch('ateme.um_backend.database.Database.is_admin', mock_is_admin)
    mocker.patch('ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id', return_value=True)
    mocker.patch('ateme.um_backend.database.Database.create_user')

    q = SimpleQueue()
    handler = logging.handlers.QueueHandler(q)
    LOG_ACTIVITY.addHandler(handler)

    expected_user = "-"
    expected_clientip = "-"
    if clientip:
        expected_clientip = clientip
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Real-IP": expected_clientip
    }
    if username and idp_name:
        headers[HttpHeaders.X_USER] = username
        headers[HttpHeaders.X_IDP_NAME] = idp_name
        expected_user = username + ":" + idp_name
    if clientip:
        expected_clientip = clientip
    body = {
        "username": "foo",
        "password": "AtemeAAA0!",
        "scopes": [],
        "session_timeout_disabled": True
    }
    resp = await client.post("/v2/users", json=body, headers=headers)
    assert 201 == resp.status
    LOG_ACTIVITY.removeHandler(handler)
    log_record = q.get_nowait()
    assert log_record.user == expected_user
    assert log_record.clientip == expected_clientip
    assert log_record.getMessage() == f"{expected_user} added user foo:local with disable session timeout set to True"

    # Test login failure logs
    LOG_ACTIVITY.addHandler(handler)
    body = {
        "username": "John",
        "password": "AtemeAAA0!",
        "idp_name": "local",
    }
    resp = await client.post("/token", json=body, headers=headers)
    assert resp.status == 401
    LOG_ACTIVITY.removeHandler(handler)
    log_record = q.get_nowait()
    # In pmf deployment, the X-User info is unavailable. (username won't be redundant)
    assert log_record.getMessage() == f'{expected_user} John:local with IP {expected_clientip} failed to login'


@pytest.mark.parametrize("parameters, body, expected_success_message, expected_failure_message", [
    pytest.param({"username": "test_user", "idp_name": "test_idp"},
                 {"session_timeout_disabled": True, "scopes": ["scope1", "scope2"], "password": "new_password",
                  "first_login": True, "password_expiration_disabled": True},
                 "updated user test_user:test_idp with disable session timeout set to True, "
                 "with password expiration disabled, adding scopes scope1, scope2, "
                 "resetting the password, forcing to change the password",
                 "failed to update user test_user:test_idp",
                 id="all fields"),
    pytest.param({"username": "test_user", "idp_name": "test_idp"},
                 {"session_timeout_disabled": False, "first_login": False, "password_expiration_disabled": False},
                 "updated user test_user:test_idp with disable session timeout set to False, "
                 "with password expiration enabled",
                 "failed to update user test_user:test_idp",
                 id="no_password_no_scopes_no_first_login"),
    pytest.param({"username": "test_user", "idp_name": "test_idp"},
                 {},
                 "updated user test_user:test_idp",
                 "failed to update user test_user:test_idp",
                 id="no_body"),
])
@pytest.mark.asyncio
async def test_generate_audit_log_for_user_update(parameters, body, expected_success_message, expected_failure_message):
    """
    Test generate_audit_log_for_user_update

    Args:
        parameters (dict): request parameters
        body (dict): request body
        expected_success_message (str): expected success message
        expected_failure_message (str): expected failure message
    """
    request = Request(parameters=parameters,
                      body=body,
                      headers=None,
                      url=URL("http://test.com"),
                      method="PATCH",
                      remote=None)

    result = generate_audit_log_for_user_update(request)

    assert result["success_message"] == expected_success_message
    assert result["failure_message"] == expected_failure_message

@pytest.mark.parametrize("parameters, body, expected_success_message, expected_failure_message", [
    pytest.param({"id": "scope_id"},
                 {"content": [{"action": "usr:get_test", "policy": "allow", "resource": {}},
                              {"action": "usr:post_test", "policy": "allow", "resource": {}}]},
                 "updated scope scope_id, adding action usr:get_test, action usr:post_test",
                 "failed to update scope scope_id",
                 id="actions_in_body"),
    pytest.param({"id": "scope_id"},
                 {"content": [{"scope": "all:administrator"}]},
                 "updated scope scope_id, adding scope all:administrator",
                 "failed to update scope scope_id",
                 id="scopes_in_body"),
    pytest.param({"id": "scope_id"},
                 {},
                 "updated scope scope_id",
                 "failed to update scope scope_id",
                 id="no_body"),
])
@pytest.mark.asyncio
async def test_generate_audit_log_for_scope_update(
        parameters, body, expected_success_message, expected_failure_message):
    """
    Test generate_audit_log_for_scope_update

    Args:
        parameters (dict): request parameters
        body (dict): request body
        expected_success_message (str): expected success message
        expected_failure_message (str): expected failure message
    """
    request = Request(parameters=parameters,
                      body=body,
                      headers=None,
                      url=URL("http://test.com"),
                      method="PATCH",
                      remote=None)

    result = generate_audit_log_for_scope_update(request)

    assert result["success_message"] == expected_success_message
    assert result["failure_message"] == expected_failure_message

@pytest.mark.parametrize("parameters, body, expected_success_message, expected_failure_message", [
    pytest.param({"idp_name": "test_idp"},
                 {"scopes": ["test:scope1", "test:scope2"], "deny_access": True, "mappers": []},
                 "updated idp configuration test_idp, set default behavior to add default roles with roles test:scope1,"
                 " test:scope2, to deny access",
                 "failed to update idp configuration test_idp",
                 id="scopes_in_body_denied_access"),
    pytest.param({"idp_name": "test_idp"},
                 {"scopes": [], "deny_access": False,
                  "mappers": [{"_id": "test_mapper", "type": "simple", "id": "mapper_id"},
                              {"_id": "test_mapper2", "type": "direct"}]},
                 "updated idp configuration test_idp, set default behavior to allow access, "
                 "with mappers simple/mapper_id, direct/unknown_id",
                 "failed to update idp configuration test_idp",
                 id="mappers_in_body_allowed_access"),
    pytest.param({"idp_name": "test_idp"},
                 {"scopes": [], "deny_access": False, "mappers": []},
                 "updated idp configuration test_idp, set default behavior to allow access",
                 "failed to update idp configuration test_idp",
                 id="no_scopes_no_mappers"),
    pytest.param({"idp_name": "test_idp"},
                 {},
                 "updated idp configuration test_idp",
                 "failed to update idp configuration test_idp",
                 id="no_body"),
])
@pytest.mark.asyncio
async def test_generate_audit_log_for_idp_config_update(
        parameters, body, expected_success_message, expected_failure_message):
    """
    Test generate_audit_log_for_idp_config_update

    Args:
        parameters (dict): request parameters
        body (dict): request body
        expected_success_message (str): expected success message
        expected_failure_message (str): expected failure message
    """
    request = Request(parameters=parameters,
                      body=body,
                      headers=None,
                      url=URL("http://test.com"),
                      method="PATCH",
                      remote=None)

    result = generate_audit_log_for_idp_config_update(request)

    assert result["success_message"] == expected_success_message
    assert result["failure_message"] == expected_failure_message
