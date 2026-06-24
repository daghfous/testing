"""

Test login/logout endpoint
"""
from typing import List
import re
import asyncio
from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import call

import pytest
from pymongo.results import UpdateResult
from yarl import URL

from ateme.um_backend.types import DEFAULT_LOCAL_IDP_NAME, Configuration, Token
from ateme.um_backend.utils import utcnow
from ateme.openapi import Request, Response, HTTPException, HTTPBadRequest, HTTPInternalServerError

DoesNotRaise = ExitStack


@pytest.mark.parametrize(
    "body, status_expected, body_expected",
    [
        ({"username": "jean", "password": "Pkdzgh84@!"}, 401, "Invalid username or password"),
        ({"username": "", "password": "Pkdzgh84@!"}, 400, "Bad credentials"),
        ({"username": "jean", "password": ""}, 400, "Bad credentials"),
    ],
)
async def test_login_schema(init_backend, body: dict, status_expected: int, body_expected: dict):
    """
    Check API schema validation on /token endpoint.
    """
    login_resp = await init_backend[0].post("/token", json=body)
    assert login_resp.status == status_expected
    assert (await login_resp.text()) == body_expected


@pytest.mark.parametrize("create_and_log_users, user_login, skip_headers, mocks_func, expected_result", [
    pytest.param(
        [{"username": "Hugo", "password": "=LeMur_2018"}],
        "Hugo",
        False,
        {},
        (200, {"body": "Successfully logged out !"}),
        id="logout-success-custom-user"
    ),
    pytest.param(
        [],
        "admin",
        False,
        {},
        (200, {"body": "Successfully logged out !"}),
        id="logout-success-admin"
    ),
    pytest.param(
        [],
        "admin",
        True,
        {},
        (400, "Can't find token in request"),
        id="logout-failed-no-token"
    ),
    pytest.param(
        [],
        "admin",
        False,
        {"ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_access_token": {"return_value": None}},
        (400, "Can't delete token"),
        id="logout-failed-invalid-token"
    ),
], indirect=["create_and_log_users", "mocks_func"])
async def test_logout(
    mocker,
    init_backend_with_admin,
    create_and_log_users: List[dict],
    user_login: str,
    skip_headers: bool,
    mocks_func: dict,
    expected_result: tuple[int, dict | str],
):
    # pylint: disable=unused-argument
    """
    Check logout endpoint behavior.
    """
    _api = init_backend_with_admin[0]
    token = create_and_log_users[user_login]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check token validity with query /user/me/actions
    validity_resp = await _api.get("/user/me/actions", headers=headers)
    assert validity_resp.status == 200

    # 2. Logout
    logout_resp = await _api.delete("/logout", headers={} if skip_headers else headers)
    assert logout_resp.status == expected_result[0]
    if 200 == logout_resp.status:
        assert expected_result[1] == await logout_resp.json()
    else:
        assert expected_result[1] == await logout_resp.text()

    # 3. Check token non validity
    validity_resp = await _api.get("/user/me/actions", headers=headers)
    assert validity_resp.status == (401 if 200 == expected_result[0] else 200)


@pytest.mark.parametrize(
    "create_users",
    [
        ([{"username": "Pavard", "password": "SecondPoteau!0"}]),
    ],
    indirect=["create_users"],
)
async def test_delete_token(init_backend_with_admin, create_users):
    """

    Login with the same user two times.
    Delete the token should logout both user connections
    """
    _api, _, admin_token = init_backend_with_admin
    _username = create_users[0]["username"]
    _headers = {"Authorization": f"Bearer {admin_token}"}

    # First login without the idp_name (default value DEFAULT_LOCAL_IDP_NAME)
    first_login = await _api.post("/token", json=create_users[0])
    assert first_login.status == 206

    # Second login with the right idp_name (DEFAULT_LOCAL_IDP_NAME)
    second_login = await _api.post("/token", json={**create_users[0], "idp_name": DEFAULT_LOCAL_IDP_NAME})
    assert second_login.status == 206

    # Fail to login because invalid idp_name
    idp_name = "invalid_idp_name"
    third_login = await _api.post("/token", json={**create_users[0], "idp_name": idp_name})
    assert third_login.status == 500
    assert (await third_login.text()) == f"Can't find an identity provider configured with this name {idp_name}"

    # delete the token a first time (success)
    first_delete = await _api.delete(
        "/token", json={"username": _username, "idp_name": DEFAULT_LOCAL_IDP_NAME}, headers=_headers
    )
    assert first_delete.status == 200
    assert (await first_delete.json()) == {"body": f"{_username} successfully disconnected !"}

    # delete the token a second time (failed)
    second_delete = await _api.delete(
        "/token", json={"username": _username, "idp_name": DEFAULT_LOCAL_IDP_NAME}, headers=_headers
    )
    assert second_delete.status == 500
    assert (await second_delete.text()) == "Can't delete token, maybe the user is not connected"


@pytest.mark.parametrize(
    "create_users", [
        [
            {"username": "Dembouze", "password": "BallonDor!25"}
        ]
    ], indirect=["create_users"]
)
async def test_block_user_client_ip_exceeding_max_failed_login_attempts_by_reenabling_user_deactivation_period(
    mocker,
    init_database,
    init_backend_with_admin,
    create_users
):
    """
    @Goals: Re-enable the user desactivation period and block a user client ip who exceed the max number of failed
        login attempt when the user deactivation period was disabled @End
    @Type: Functional @End
    @Priority: Critical @End
    @Automating Status: Automated @End
    @Reference: MS-4390 @End

    @Preconditions: Start user management backend with "Dembouze" as user @End
    @Step: Patch the configuration to disable the user deactivation period @End
    @Expected: Request succeed (status=200) @End
    @Step: Exceed the max number of failed login attempts for the user "Dembouze" @End
    @Expected: "Dembouze" user always enabled and login requests returned 400 @End
    @Step: Patch the configuration to enable the user deactivation period @End
    @Expected: Request succeed (status=200) @End
    @Step: Do a first failed login attempt with "Dembouze" user @End
    @Expected: Login request must return 400 @End
    @Step: Do a second failed login attempt with "Dembouze" user @End
    @Expected: Login request must return 403 @End
    """
    _api, _webapp, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database

    good_credentials = create_users[0]
    username = good_credentials["username"]
    bad_credentials = {"username": username, "password": "Yamal!2026"}

    configuration = {
        "user_deactivation_period": -1,
        "max_successive_failed_login": 3,
    }

    # Mock the user management to be configured with MAX_NUMBER_FAILED_CLIENT_LOGINS
    mocker.patch.object(_webapp.settings, "max_number_failed_client_logins", 200)

    # update the configuration
    resp = await _api.put("/configuration", json=configuration, headers=_admin_headers)
    assert resp.status == 200

    # Exceed the max_successive_failed_login
    # (return 401 unauthorized and client must not be blocked)
    for i in range(1, configuration["max_successive_failed_login"] + 2):
        resp = await _api.post("/token", json=bad_credentials)
        assert resp.status == 401
        client = await _db.collection_clients.get(
            remote="127.0.0.1",
            username=username,
            idp_name=DEFAULT_LOCAL_IDP_NAME
        )
        assert client.attempts == i
        assert client.enabled

    # Re-enabling the user_deactivation_period
    configuration["user_deactivation_period"] = 600
    resp = await _api.put("/configuration", json=configuration, headers=_admin_headers)
    assert resp.status == 200

    # First failed login attempt must return 401 unauthorized
    resp = await _api.post("/token", json=bad_credentials)
    assert resp.status == 401

    # Second failed login attempt must return 403
    resp = await _api.post("/token", json=bad_credentials)
    assert resp.status == 403


@pytest.mark.parametrize(
    "create_users", [
        [
            {"username": "ZizouIsBack", "password": "defaultPassword0!"}
        ]
    ], indirect=["create_users"]
)
async def test_remove_enabled_user_client_ip_after_login(
    init_database,
    init_backend_with_admin,
    create_users
):
    """
    @Goals: Remove user client ip attempts when an enabled user does a valid login @End
    @Type: Functional @End
    @Priority: Critical @End
    @Automating Status: Automated @End
    @Reference: MS-4390 @End

    @Preconditions: Start user management backend with "ZizouIsBack" as user @End
    @Step: Patch the configuration with max_successive_failed_login=3 @End
    @Expected: Request succeed (status=200) @End
    @Step: Do failed login attempts without reaching the max_successive_failed_login with "ZizouIsBack" user @End
    @Expected: "ZizouIsBack" user always enabled with the expected attempts and login requests returned 400 @End
    @Step: Do a valid login attempt with "ZizouIsBack" user @End
    @Expected: Request succeed (status=206) @End
    @Step: Search the user client ip in DB for "ZizouIsBack" user @End
    @Expected: No user client ip relative to "ZizouIsBack" user @End
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database

    good_credentials = create_users[0]
    username = good_credentials["username"]
    bad_credentials = {"username": username, "password": "Wrong_pwd123"}

    # Get the configuration and check its content
    resp = await _api.get("/configuration", headers=_admin_headers)
    assert resp.status == 200
    configuration = await resp.json()
    assert configuration["max_successive_failed_login"] == 3

    # Make several failed login attempts without reaching the max_successive_failed_login
    for i in range(0, configuration["max_successive_failed_login"] - 1):
        resp = await _api.post("/token", json=bad_credentials)
        assert resp.status == 401
        client = await _db.collection_clients.get(
            remote="127.0.0.1",
            username=username,
            idp_name=DEFAULT_LOCAL_IDP_NAME
        )
        assert client.attempts == i + 1
        assert client.enabled

    # Make a valid login attempt (first login)
    resp = await _api.post("/token", json=good_credentials)
    assert resp.status == 206

    # Client IP must be removed
    client = await _db.collection_clients.get(
        remote="127.0.0.1",
        username=username,
        idp_name=DEFAULT_LOCAL_IDP_NAME
    )
    assert not client


@pytest.mark.parametrize(
    "create_users", [
        [
            {"username": "ZizouIsBack", "password": "defaultPassword0!"}
        ]
    ], indirect=["create_users"]
)
async def test_unlock_user_client_ip_by_updating_user(init_database, init_backend_with_admin, create_users):
    """
    @Goals: Unlock a disabled user who reached the max failed login attempts by updating the user @End
    @Type: Functional @End
    @Priority: Critical @End
    @Automating Status: Automated @End
    @Reference: MS-4390 @End

    @Preconditions: Start user management backend with "ZizouIsBack" as user @End
    @Step: Get the current configuration @End
    @Expected: Request succeed (status=200) and the default configuration is active @End
    @Step: Reach the max failed login attempts with "ZizouIsBack" user @End
    @Expected: "ZizouIsBack" user disabled @End
    @Step: Do another failed login attempt with "ZizouIsBack" user @End
    @Expected: User is blocked, the request must fail with status=403 @End
    @Step: Re-enabling the user @End
    @Expected: Request succeed (status=200) @End
    @Step: Find the user client ip for "ZizouIsBack" user @End
    @Expected: No user client ip relative to "ZizouIsBack" user @End
    @Step: Do a valid login attempt with "ZizouIsBack" user @End
    @Expected: Request succeed (status=206) @End
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database

    good_credentials = create_users[0]
    username = good_credentials["username"]
    bad_credentials = {"username": username, "password": "Wrong_pwd123"}

    # Get the configuration and check its content
    resp = await _api.get("/configuration", headers=_admin_headers)
    assert resp.status == 200
    configuration = await resp.json()
    assert configuration["max_successive_failed_login"] == 3
    assert configuration["user_deactivation_period"] == 600

    # Check there is no client attached to the username
    client = await _db.collection_clients.get(
        remote="127.0.0.1",
        username=username,
        idp_name=DEFAULT_LOCAL_IDP_NAME
    )
    assert not client

    # Reached the max_successive_failed_login attempts
    for i in range(1, configuration["max_successive_failed_login"] + 1):
        resp = await _api.post("/token", json=bad_credentials)
        assert resp.status == 401
        client = await _db.collection_clients.get(
            remote="127.0.0.1",
            username=username,
            idp_name=DEFAULT_LOCAL_IDP_NAME
        )
        assert client.attempts == i

    client = await _db.collection_clients.get(
        remote="127.0.0.1",
        username=username,
        idp_name=DEFAULT_LOCAL_IDP_NAME
    )
    assert not client.enabled

    # New login attempts with valid credentials
    resp = await _api.post("/token", json=good_credentials)
    assert resp.status == 403

    # Re-enable the user via update_users
    resp = await _api.patch(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{username}",
        json={"enabled": True},
        headers=_admin_headers,
    )
    assert resp.status == 200

    # Client IP must be removed
    client = await _db.collection_clients.get(
        remote="127.0.0.1",
        username=username,
        idp_name=DEFAULT_LOCAL_IDP_NAME
    )
    assert not client

    # Login must succeed (first login)
    resp = await _api.post("/token", json=good_credentials)
    assert resp.status == 206


@pytest.mark.parametrize(
    "create_users",
    [
        [
            {
                "username": "Dembouze",
                "password": "BallonD0r!25",
            }
        ],
    ],
    indirect=["create_users"],
)
async def test_unlock_user_client_ip_after_delay(init_database, init_backend_with_admin, create_users):
    """
    @Goals: Unlock a disabled user after the deactivation period expiration @End
    @Type: Functional @End
    @Priority: Critical @End
    @Automating Status: Automated @End
    @Reference: MS-4390 @End

    @Preconditions: Start user management backend with "Dembouze" as user @End
    @Step: Patch the configuration with user_deactivation_period=5 and max_successive_failed_login=3 @End
    @Expected: Request succeed (status=200) and configuration taken account @End
    @Step: Reach the max failed login attempts with "Dembouze" user @End
    @Expected: "ZizouIsBack" user disabled @End
    @Step: Do another failed login attempt with "Dembouze" user @End
    @Expected: User is blocked, the request must fail with status=403 @End
    @Step: Do a valid login attempt with "Dembouze" user @End
    @Expected: User is blocked, the request must fail with status=403 @End
    @Step: Wait until the user_deactivation_period expires @End
    @Expected: Barney, wait for it @End
    @Step: Do a failed login attempt with "Dembouze" user @End
    @Expected: User is no more blocked (attempt=1), the request must fail with status=400 @End
    @Step: Do a valid login attempt with "Dembouze" user @End
    @Expected: Request succeed (status=206) @End
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database

    good_credentials = create_users[0]
    username = good_credentials["username"]
    bad_credentials = {"username": username, "password": "Wrong_pwd123"}

    configuration = {
        "user_deactivation_period": 5,
        "max_successive_failed_login": 3
    }

    # Before: Patching the configuration
    resp = await _api.put("/configuration", json=configuration, headers=_admin_headers)
    assert resp.status == 200

    # Reach the max_successive_failed_login
    for i in range(1, configuration["max_successive_failed_login"] + 1):
        resp = await _api.post("/token", json=bad_credentials)
        assert resp.status == 401

        client = await _db.collection_clients.get(
            remote="127.0.0.1",
            username=username,
            idp_name=DEFAULT_LOCAL_IDP_NAME
        )
        assert client.attempts == i
        assert not client.enabled if i == configuration["max_successive_failed_login"] else client.enabled

    # Client IP is disabled, all attempts with the same client IP must be blocked (failed or valid)
    resp = await _api.post("/token", json=bad_credentials)
    assert resp.status == 403
    pattern_message = re.compile(r"Client disabled for (\d+) seconds after too many attempts")
    assert pattern_message.match(await resp.text())
    resp = await _api.post("/token", json=good_credentials)
    assert resp.status == 403
    pattern_message = re.compile(r"Client disabled for (\d+) seconds after too many attempts")
    assert pattern_message.match(await resp.text())

    # Wait until the user deactivation period expires
    await asyncio.sleep(configuration["user_deactivation_period"])

    # Failed login attempt
    resp = await _api.post("/token", json=bad_credentials)
    assert resp.status == 401
    client = await _db.collection_clients.get(
        remote="127.0.0.1",
        username=username,
        idp_name=DEFAULT_LOCAL_IDP_NAME
    )
    assert client.enabled
    assert client.attempts == 1

    # Valid login attempt
    resp = await _api.post("/token", json=good_credentials)
    assert resp.status == 206
    client = await _db.collection_clients.get(
        remote="127.0.0.1",
        username=username,
        idp_name=DEFAULT_LOCAL_IDP_NAME
    )
    assert not client


async def test_login_with_scope_deleted(init_backend_with_admin):
    # pylint: disable=unused-argument
    """

    Check that after deleting scope, this one will not be refernce on next login.
    """
    _api, _, admin_token = init_backend_with_admin
    _headers = {"Authorization": f"Bearer {admin_token}"}
    new_user = {"username": "captain", "password": "Morgan99!A"}
    new_scope_id = "toto:full_access"

    # Create new scope
    scope_creation_resp = await _api.post(
        "/scopes",
        json=[
            {
                "id": new_scope_id,
                "label": "usr",
                "description": "description",
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            }
        ],
        headers=_headers,
    )
    assert scope_creation_resp.status == 200

    # Create a user with this new scope
    user_creation_resp = await _api.post(
        "/users",
        json=[
            {
                "username": new_user["username"],
                "password": new_user["password"],
                "scopes": ["usr:engineer", new_scope_id],
            }
        ],
        headers=_headers,
    )
    assert user_creation_resp.status == 201

    # Delete scope
    delete_scope_resp = await _api.delete(
        "/scopes",
        json=[
            {"id": new_scope_id},
        ],
        headers=_headers,
    )
    assert delete_scope_resp.status == 200

    # Login with new user
    login_resp = await _api.post("/token", json={"username": new_user["username"], "password": new_user["password"]})
    assert login_resp.status == 206
    body = await login_resp.json()

    current_user_resp = await _api.get("/user/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert current_user_resp.status == 200
    response = await current_user_resp.json()

    # Deleted scope must be removed from db
    assert new_scope_id not in response["scopes"]


@pytest.mark.parametrize(
    "user_deactivation_period, expected_results", [
        pytest.param(
            3,
            [
                (403, re.compile(r"Client disabled for (\d+) seconds after too many attempts")),
                (403, re.compile(r"Client disabled for (\d+) seconds after too many attempts")),
                (401, re.compile(r"Invalid username or password"))
            ],
            id="user deactivation period enabled"
        ),
        pytest.param(
            -1,
            [
                (401, re.compile(r"Invalid username or password")),
                (200, None),
                (401, re.compile(r"Invalid username or password"))
            ],
            id="user deactivation period disabled"
        )
    ]
)
async def test_max_successive_failed_login(
    init_backend_with_admin,
    admin_user,
    user_deactivation_period: int,
    expected_results: list[tuple[int, re.Pattern[str] | None]]
):
    """test_max_successive_failed_logins
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    configuration = {
        "max_successive_failed_login": 3,
        "user_deactivation_period": user_deactivation_period
    }

    # Update the configuration
    resp = await _api.put("/configuration", json=configuration, headers=_admin_headers)
    assert resp.status == 200

    bad_credentials = {"username": admin_user["username"], "password": "Totodu35!"}
    good_credentials = admin_user

    # Reach the `max_successive_failed_login`
    for _ in range(configuration["max_successive_failed_login"]):
        resp = await _api.post("/token", json=bad_credentials)
        assert resp.status == 401

    # The client IP must be disabled (for failed and valid attempts)
    #
    # attempt with bad credentials
    resp = await _api.post("/token", json=bad_credentials)
    status_code, pattern_message = expected_results.pop(0)
    assert resp.status == status_code
    if pattern_message:
        assert pattern_message.match(await resp.text())
    # attempt with valid credentials
    resp = await _api.post("/token", json=good_credentials)
    status_code, pattern_message = expected_results.pop(0)
    assert resp.status == status_code
    if pattern_message:
        assert pattern_message.match(await resp.text())

    # Sleep until the client is enabled again
    await asyncio.sleep(user_deactivation_period + 1)

    # One failed login attempt
    resp = await _api.post("/token", json=bad_credentials)
    status_code, pattern_message = expected_results.pop(0)
    assert resp.status == status_code
    if pattern_message:
        assert pattern_message.match(await resp.text())

    # One valid login attempt
    resp = await _api.post("/token", json=good_credentials)
    assert resp.status == 200


@pytest.mark.parametrize(
    "create_users", [
        [
            {"username": "picasso", "password": "Pablo!1235"},
            {"username": "escobar", "password": "1235!Pablo"}
        ]
    ], indirect=["create_users"],
)
@pytest.mark.parametrize(
    "user_deactivation_period, expected_response", [
        pytest.param(3, 503, id="max number failed client logins reached when user deactivation enabled"),
        pytest.param(-1, 206, id="max number failed client logins reached when user deactivation disabled"),
    ]
)
async def test_max_number_failed_client_logins(
    mocker,
    init_backend_with_admin,
    create_users,
    admin_user,
    user_deactivation_period: int,
    expected_response: int
):
    """ test_max_number_failed_client_logins
    """
    _api, _webapp, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    user_0 = create_users[0]
    user_1 = create_users[1]

    configuration = {
        "max_successive_failed_login": 10,
        "user_deactivation_period": user_deactivation_period,
    }
    max_number_failed_client_logins = 5

    # Mock the user management to be configured with MAX_NUMBER_FAILED_CLIENT_LOGINS
    mocker.patch.object(_webapp.settings, "max_number_failed_client_logins", max_number_failed_client_logins)

    # Update the configuration
    resp = await _api.put("/configuration", json=configuration, headers=_admin_headers)
    assert resp.status == 200

    # Reached the max number failed client logins
    users = [user_0["username"], admin_user["username"]]
    for i in range(1, max_number_failed_client_logins + 1):
        username = users[i % 2]
        resp = await _api.post("/token", json={"username": username, "password": "Totdu1235!"})
        assert resp.status == 401

    resp = await _api.post("/token", json=user_1)
    assert resp.status == expected_response
    if user_deactivation_period != -1:
        assert await resp.text() == "The number of maximum failed logins has been reached"
        # Sleep until the user management login is unlocked
        await asyncio.sleep(user_deactivation_period + 1)
        # Can login again with new_user_bis
        resp = await _api.post("/token", json=user_1)
        assert resp.status == 206


@pytest.mark.parametrize(
    "create_users",
    [[{"username": "annunaki", "password": "Picasso!35", "scopes": ["usr:engineer"]}]],
    indirect=["create_users"],
)
async def test_enable_client_by_patching_user(init_backend_with_admin, create_users, admin_user):
    # pylint: disable=unused-argument
    """
    Patching a user corresponding to a client must enabled it
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    # Create a user
    new_user = create_users[0]

    # Disable the client corresponding to the new_user
    for _ in range(3):
        login_resp = await _api.post("/token", json={"username": new_user["username"], "password": "Totdu35!"})
        assert login_resp.status == 401

    # Client is disabled
    login_resp = await _api.post("/token", json={"username": new_user["username"], "password": new_user["password"]})
    assert login_resp.status == 403

    # Patch the user
    # Re-enable the user via update_users
    update_user_resp = await _api.patch(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{new_user['username']}",
        json={"level": 25},
        headers=_admin_headers,
    )
    assert update_user_resp.status == 200

    # Client is enabled
    login_resp = await _api.post("/token", json={"username": new_user["username"], "password": new_user["password"]})
    assert login_resp.status == 206


@pytest.mark.parametrize(
    "create_users", [[{"username": "Yaya", "password": "defaultPassword0!"}]], indirect=["create_users"]
)
async def test_first_login(init_backend_with_admin, create_users):
    # pylint: disable=unused-argument
    """

    Check first login behavior, first create a new user, then log with his credential.
    We should have a HTTP 206 response and a reason in body response.
    After update password, next login response must be a 200 without reason in body.
    """
    _api, user_api, _admin_token = init_backend_with_admin

    username_1 = "Yaya"
    password = "defaultPassword0!"

    # Login with user 1 credentials (local)
    login_resp = await _api.post("/token", json={"username": username_1, "password": password})
    assert login_resp.status == 206

    body = await login_resp.json()
    assert isinstance(body, dict)
    assert "access_token" in body
    assert body["reason"] == "First login"
    token = body["access_token"]
    user1_headers = {"content-type": "application/json", "Authorization": f"Bearer {token}"}
    new_password = "dfjgkrtz1567434sdgeq45A!"

    # Change password
    update_password_resp = await _api.patch(
        "/user/me/password",
        json={
            "old_password": password,
            "new_password": new_password,
        },
        headers=user1_headers,
    )
    assert update_password_resp.status == 200

    # Assert that old token has been removed
    db_token = await user_api.db.collection_tokens.get_by_access_token(token)
    assert not db_token

    # Logout doesn't work because the deprecated token has been removed
    logout_resp = await _api.delete("/logout", headers=user1_headers)
    assert logout_resp.status == 400

    # Login old password
    login_resp = await _api.post("/token", json={"username": username_1, "password": password})
    assert login_resp.status == 401

    # Login new password
    login_resp = await _api.post("/token", json={"username": username_1, "password": new_password})
    assert login_resp.status == 200

    body = await login_resp.json()
    assert isinstance(body, dict)
    assert "access_token" in body
    assert "reason" not in body


@pytest.mark.parametrize(
    "create_users", [[{"username": "Zizou", "password": "defaultPassword0!"}]], indirect=["create_users"]
)
async def test_multiple_login(init_backend_with_admin, create_users):
    # pylint: disable=unused-argument
    """
    Login multiple times with the same user and check that uniq token are deliver.
    """
    _api, _, _ = init_backend_with_admin

    # Login a first time
    login_resp = await _api.post("/token", json=create_users[0])
    assert login_resp.status == 206

    body1 = await login_resp.json()
    assert body1
    assert isinstance(body1, dict)
    # That's default value
    assert body1["expires_in"] == 3600
    assert body1["token_type"] == "bearer"
    assert body1["reason"] == "First login"

    # Login a second time
    login_resp = await _api.post("/token", json=create_users[0])
    assert login_resp.status == 206

    body2 = await login_resp.json()
    assert body2
    assert isinstance(body2, dict)
    # That's default value
    assert body2["expires_in"] == 3600
    assert body2["token_type"] == "bearer"
    assert body2["reason"] == "First login"

    assert body1["access_token"] != body2["access_token"]
    assert body1["refresh_token"] != body2["refresh_token"]

    # Refresh token
    refresh_token_resp = await _api.post("/refresh_token", json={"refresh_token": body1["refresh_token"]})
    assert refresh_token_resp.status == 200
    body11 = await refresh_token_resp.json()
    assert body11
    assert isinstance(body11, dict)
    # That's default value
    assert body11["expires_in"] == 3600
    assert body11["token_type"] == "bearer"

    assert body1["access_token"] != body2["access_token"]
    assert body1["refresh_token"] != body2["refresh_token"]
    assert body1["access_token"] != body11["access_token"]
    assert body2["access_token"] != body11["access_token"]

    assert body1["refresh_token"] == body11["refresh_token"]
    assert body2["refresh_token"] != body11["refresh_token"]



DEFAULT_CONFIGURATION = Configuration()
FAKE_NOW = utcnow()
EXPECTED_TOKEN_EXPIRATION_DATE = FAKE_NOW + DEFAULT_CONFIGURATION.token_expiration

@pytest.mark.parametrize(
    "req, mocks_func, assert_mock_called, expected_result",
    [
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "return_value": Token(
                        token="007007",
                        refresh_token="987654321",
                        started_date=utcnow(),
                        expiration_date=utcnow() - timedelta(hours=1),
                        refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                        user_id="zizou_id"
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id" : {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
                "ateme.um_backend.database.Database.get_configuration": {"return_value": DEFAULT_CONFIGURATION},
                "ateme.um_backend.types.token._generate_token": {"return_value": "123456"},
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": {
                    "return_value": UpdateResult(acknowledged=True, raw_result={"n": 1})
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
                "ateme.um_backend.database.Database.get_user_by_id": [call(user_id="zizou_id")],
                "ateme.um_backend.database.Database.get_configuration": [call()],
                "ateme.um_backend.types.token._generate_token": [call()],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": [
                    call(
                        token="007007",
                        new_token="123456",
                        new_expiration_date=EXPECTED_TOKEN_EXPIRATION_DATE,
                        current_version=0,
                    )
                ],
            },
            Response(
                200,
                {
                    "access_token": "123456",
                    "refresh_token": "987654321",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
                {"Content-Type": "application/json"},
            ),
            id="refresh-token-success",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "invalid_user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "return_value": None
                },
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
            },
            HTTPBadRequest(data="Refresh token not found or expired"),
            id="refresh-token-failed-not-found-or-expired",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "invalid_user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "return_value": Token(
                        token="007007",
                        refresh_token="987654321",
                        started_date=utcnow(),
                        expiration_date=utcnow() - timedelta(hours=1),
                        refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                        user_id="zizou_id",
                        user_ip="user_ip"
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id" : {
                    "return_value": None
                },
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
                "ateme.um_backend.database.Database.get_user_by_id": [call(user_id="zizou_id")],
            },
            HTTPBadRequest(data="Can't find user with id: zizou_id"),
            id="refresh-token-user-not-found",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "invalid_user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "return_value": Token(
                        token="007007",
                        refresh_token="987654321",
                        started_date=utcnow(),
                        expiration_date=utcnow() - timedelta(hours=1),
                        refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                        user_id="zizou_id",
                        user_ip="user_ip"
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id" : {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
                "ateme.um_backend.database.Database.get_user_by_id": [call(user_id="zizou_id")],
            },
            HTTPBadRequest(data="remote ip invalid: invalid_user_ip != user_ip"),
            id="refresh-token-failed-invalid-user-ip",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                # First call returns old token, second call returns fallback (also old token)
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "side_effect": [
                        Token(
                            token="007007",
                            refresh_token="987654321",
                            started_date=utcnow(),
                            expiration_date=utcnow() - timedelta(hours=1),
                            refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                            user_id="zizou_id",
                            user_ip="user_ip",
                            version=0,
                        ),
                        Token(
                            token="007007", # fallback returns the same old token
                            refresh_token="987654321",
                            started_date=utcnow(),
                            expiration_date=utcnow() - timedelta(hours=1),
                            refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                            user_id="zizou_id",
                            user_ip="user_ip",
                            version=0,
                        )
                    ]
                },
                "ateme.um_backend.database.Database.get_user_by_id": {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
                "ateme.um_backend.database.Database.get_configuration": {
                    "return_value": DEFAULT_CONFIGURATION
                },
                "ateme.um_backend.types.token._generate_token": {
                    "return_value": "123456"
                },
                # Simulate concurrent update: matched_count=0 triggers fallback
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": {
                    "return_value": UpdateResult(
                        acknowledged=True,
                        raw_result={"n": 0, "nModified": 0}
                    )
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [
                    call("987654321"),
                    call("987654321"),  # fallback call
                ],
                "ateme.um_backend.database.Database.get_user_by_id": [
                    call(user_id="zizou_id")
                ],
                "ateme.um_backend.database.Database.get_configuration": [call()],
                "ateme.um_backend.types.token._generate_token": [call()],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": [
                    call(
                        token="007007",
                        new_token="123456",
                        new_expiration_date=EXPECTED_TOKEN_EXPIRATION_DATE,
                        current_version=0,
                    )
                ],
            },
            Response(
                200,
                {
                    # fallback token returned
                    "access_token": "007007",
                    "refresh_token": "987654321",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
                {"Content-Type": "application/json"},
            ),
            id="refresh-token-concurrent-update-return-existing-token",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "side_effect": [
                        Token(
                            token="007007",
                            refresh_token="987654321",
                            started_date=utcnow(),
                            expiration_date=utcnow() - timedelta(hours=1),
                            refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                            user_id="zizou_id",
                            user_ip="user_ip"
                        ),
                        None,  # ← fallback fetch fails
                    ]
                },
                "ateme.um_backend.database.Database.get_user_by_id": {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
                "ateme.um_backend.database.Database.get_configuration": {
                    "return_value": DEFAULT_CONFIGURATION
                },
                "ateme.um_backend.types.token._generate_token": {
                    "return_value": "123456"
                },
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": {
                    "return_value": UpdateResult(acknowledged=True, raw_result={"n": 0})
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [
                    call("987654321"),
                    call("987654321"),
                ],
                "ateme.um_backend.database.Database.get_user_by_id": [
                    call(user_id="zizou_id")
                ],
                "ateme.um_backend.database.Database.get_configuration": [call()],
                "ateme.um_backend.types.token._generate_token": [call()],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": [
                    call(
                        token="007007",
                        new_token="123456",
                        new_expiration_date=EXPECTED_TOKEN_EXPIRATION_DATE,
                        current_version=0,
                    )
                ],
            },
            HTTPInternalServerError(data="Unable to refresh the token"),
            id="refresh-token-concurrent-update-token-missing",
        ),
    ],
    indirect=["mocks_func"],
)
@pytest.mark.parametrize("settings", [
    {"token_ip_validation": True},
], indirect=["settings"])
async def test_refresh_token_with_ip_validation(
    mocker,
    settings,
    init_backend,
    req: Request,
    mocks_func: dict[str, dict],
    assert_mock_called: dict[str, dict],
    expected_result: Response | HTTPException,
):
    """

    Check `refresh_token` handler use on POST /refresh_token.

    Args:
        req: (Request): Request pass to refresh_token handler.
        mocks_func (dict[str, dict]): Function to mock with args.
        assert_mock_called: (dict[str, dict]): Args expected from mock calls.
        expected_result: (Response | HTTPException): Response expected return by handler or Exception expected.
    """
    client, _ = init_backend

    mocker.patch("ateme.um_backend.types.token.utcnow", return_value=FAKE_NOW)

    response = await client.post("/refresh_token", json=req.body, headers=req.headers)
    # Check response status, data and headers
    assert response.status == expected_result.status_code
    if expected_result.status_code == 200:
        assert response.headers["Content-Type"] == expected_result.headers["Content-Type"]
        assert await response.json() == expected_result.data
    else:
        assert response.headers["Content-Type"] == "text/plain"
        assert await response.text() == expected_result.data

    # Check args of mock called
    for _mock_func, _calls in assert_mock_called.items():
        mocks_func[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize(
    "req, mocks_func, assert_mock_called, expected_result",
    [
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "return_value": Token(
                        token="007007",
                        refresh_token="987654321",
                        started_date=utcnow(),
                        expiration_date=utcnow() - timedelta(hours=1),
                        refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                        user_id="zizou_id"
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id" : {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
                "ateme.um_backend.database.Database.get_configuration": {"return_value": DEFAULT_CONFIGURATION},
                "ateme.um_backend.types.token._generate_token": {"return_value": "123456"},
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": {
                    "return_value": UpdateResult(acknowledged=True, raw_result={"n": 1})
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
                "ateme.um_backend.database.Database.get_user_by_id": [call(user_id="zizou_id")],
                "ateme.um_backend.database.Database.get_configuration": [call()],
                "ateme.um_backend.types.token._generate_token": [call()],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": [
                    call(
                        token="007007",
                        new_token="123456",
                        new_expiration_date=EXPECTED_TOKEN_EXPIRATION_DATE,
                        current_version=0
                    )
                ],
            },
            Response(
                200,
                {
                    "access_token": "123456",
                    "refresh_token": "987654321",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
                {"Content-Type": "application/json"},
            ),
            id="refresh-token-success",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "invalid_user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "return_value": Token(
                        token="007007",
                        refresh_token="987654321",
                        started_date=utcnow(),
                        expiration_date=utcnow() - timedelta(hours=1),
                        refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                        user_id="zizou_id",
                        user_ip="user_ip"
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id" : {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
                "ateme.um_backend.database.Database.get_configuration": {"return_value": DEFAULT_CONFIGURATION},
                "ateme.um_backend.types.token._generate_token": {"return_value": "123456"},
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": {
                    "return_value": UpdateResult(acknowledged=True, raw_result={"n": 1})
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
                "ateme.um_backend.database.Database.get_user_by_id": [call(user_id="zizou_id")],
                "ateme.um_backend.database.Database.get_configuration": [call()],
                "ateme.um_backend.types.token._generate_token": [call()],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": [
                    call(
                        token="007007",
                        new_token="123456",
                        new_expiration_date=EXPECTED_TOKEN_EXPIRATION_DATE,
                        current_version=0
                    )
                ],
            },
            Response(
                200,
                {
                    "access_token": "123456",
                    "refresh_token": "987654321",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
                {"Content-Type": "application/json"},
            ),
            id="refresh-token-failed-invalid-user-ip",
        ),
        pytest.param(
            Request(
                parameters={},
                body={"refresh_token": "987654321"},
                headers={"X-Real-IP": "user_ip"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": {
                    "side_effect": [
                        Token(
                            token="007007",
                            refresh_token="987654321",
                            started_date=utcnow(),
                            expiration_date=utcnow() - timedelta(hours=1),
                            refresh_token_expiration_date=utcnow() + timedelta(hours=1),
                            user_id="zizou_id",
                            user_ip="user_ip"
                        ),
                        None,  # ← fallback fetch fails
                    ]
                },
                "ateme.um_backend.database.Database.get_user_by_id" : {
                    "return_value": {
                        "username": "zizou",
                        "idp_name": "local"
                    }
                },
                "ateme.um_backend.database.Database.get_configuration": {"return_value": DEFAULT_CONFIGURATION},
                "ateme.um_backend.types.token._generate_token": {"return_value": "123456"},
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": {
                    "return_value": UpdateResult(acknowledged=True, raw_result={"n": 0})
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_refresh_token": [call("987654321")],
                "ateme.um_backend.database.Database.get_user_by_id": [call(user_id="zizou_id")],
                "ateme.um_backend.database.Database.get_configuration": [call()],
                "ateme.um_backend.types.token._generate_token": [call()],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.refresh_token": [
                    call(
                        token="007007",
                        new_token="123456",
                        new_expiration_date=EXPECTED_TOKEN_EXPIRATION_DATE,
                        current_version=0
                    )
                ],
            },
            HTTPInternalServerError(data="Unable to refresh the token"),
            id="refresh-token-update-failed",
        ),
    ],
    indirect=["mocks_func"],
)
@pytest.mark.parametrize("settings", [
    {"token_ip_validation": False},
], indirect=["settings"])
async def test_refresh_token_without_ip_validation(
    mocker,
    settings,
    init_backend,
    req: Request,
    mocks_func: dict[str, dict],
    assert_mock_called: dict[str, dict],
    expected_result: Response | HTTPException,
):
    """

    Check `refresh_token` handler use on POST /refresh_token.

    Args:
        req: (Request): Request pass to refresh_token handler.
        mocks_func (dict[str, dict]): Function to mock with args.
        assert_mock_called: (dict[str, dict]): Args expected from mock calls.
        expected_result: (Response | HTTPException): Response expected return by handler or Exception expected.
    """
    client, _ = init_backend

    mocker.patch("ateme.um_backend.types.token.utcnow", return_value=FAKE_NOW)

    response = await client.post("/refresh_token", json=req.body, headers=req.headers)
    # Check response status, data and headers
    assert response.status == expected_result.status_code
    if expected_result.status_code == 200:
        assert response.headers["Content-Type"] == expected_result.headers["Content-Type"]
        assert await response.json() == expected_result.data
    else:
        assert response.headers["Content-Type"] == "text/plain"
        assert await response.text() == expected_result.data

    # Check args of mock called
    for _mock_func, _calls in assert_mock_called.items():
        mocks_func[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize(
    "create_users, data",
    [
        pytest.param(
            [{"username": "TestUsername", "password": "AdminAA04!"}],
            {
                "max_successive_failed_login": 3,
                "user_deactivation_period": 600,
                "token_expiration": 5,
                "refresh_token_expiration": 9,
                "token_cleaning_period": 24
            },
        )
    ],
    indirect=["create_users"],
)
async def test_refresh_token_expiration_date(init_backend_with_admin, create_users, data: dict):
    """
    Test that we can refresh a token only if the token expiration date
    is not exceeds, else we shall receive a 400 Bad Request Error
    MS-6208
    Args:
        data (dict): Data Configuration
    """
    _api, _, _admin_token = init_backend_with_admin
    admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Put config in DB
    update_conf_resp = await _api.put("/configuration", json=data, headers=admin_headers)
    assert update_conf_resp.status == 200

    # Login request a token
    login_resp = await _api.post("/token", json=create_users[0])
    assert login_resp.status == 206
    body = await login_resp.json()
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check token validity with query /user/me/actions -> Token Must be valid
    current_user_resp = await _api.get("/user/me/actions", headers=headers)
    assert current_user_resp.status == 200

    # Token should be expired after some seconds
    await asyncio.sleep(data["token_expiration"])
    current_user_resp = await _api.get("/user/me/actions", headers=headers)
    assert current_user_resp.status == 401

    # Refresh Token
    refresh_token_resp = await _api.post("/refresh_token", json={"refresh_token": body["refresh_token"]})
    assert refresh_token_resp.status == 200
    refreshed_token = await refresh_token_resp.json()

    headers["Authorization"] = f"Bearer {refreshed_token['access_token']}"
    # Check token validity with query /user/me/actions -> Token Must be valid
    current_user_resp = await _api.get("/user/me/actions", headers=headers)
    assert current_user_resp.status == 200

    # We Repeat the process
    await asyncio.sleep(data["token_expiration"])
    current_user_resp = await _api.get("/user/me/actions", headers=headers)
    assert current_user_resp.status == 401

    # Refresh Token should be expired and we shall receive a HTTPBadRequest 400 Error, because
    # refresh_token_expiration_date is exceeded
    refresh_token_resp = await _api.post("/refresh_token", json={"refresh_token": refreshed_token["refresh_token"]})
    assert refresh_token_resp.status == 400

@pytest.mark.parametrize(
    "create_users, data",
    [
        pytest.param(
            [{"username": "TestUsername", "password": "AdminAA04!"}],
            {
                "max_successive_failed_login": 3,
                "user_deactivation_period": 600,
                "token_expiration": 5,
                "refresh_token_expiration": 9,
                "token_cleaning_period": 24
            },
        )
    ],
    indirect=["create_users"],
)
async def test_login_with_session_timeout_disabled(init_backend_with_admin, create_users, data: dict):
    # pylint: disable=unused-argument
    """Test login with session timeout disabled
    It must keep the token valid even after the token expiration date
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Put config in DB
    update_conf_resp = await _api.put("/configuration", json=data, headers=_admin_headers)
    assert update_conf_resp.status == 200

    # check Login with session_timeout_disabled with default value False
    login_resp = await _api.post("/token", json=create_users[0])
    assert login_resp.status == 206
    body = await login_resp.json()
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Token should be expired after some seconds
    await asyncio.sleep(data["token_expiration"])
    current_user_resp = await _api.get("/user/me/actions", headers=headers)
    assert current_user_resp.status == 401

    # Patch the user
    # Disable session timeout
    update_user_resp = await _api.patch(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{create_users[0]['username']}",
        json={"session_timeout_disabled": True},
        headers=_admin_headers,
    )
    assert update_user_resp.status == 200

    # Login request a token
    login_resp = await _api.post("/token", json=create_users[0])
    assert login_resp.status == 206
    body = await login_resp.json()
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Token should not be expired after some seconds
    await asyncio.sleep(data["token_expiration"])
    current_user_resp = await _api.get("/user/me/actions", headers=headers)
    assert current_user_resp.status == 200
