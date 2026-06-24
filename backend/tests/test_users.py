"""

TestUser test class, cover different endpoints of UserManagementApi
* change password
* update users, update user by name
* get current user
* Remove user by name
* Add user
* Force disconnection
"""
from unittest.mock import AsyncMock, call, _Call, ANY
from contextlib import ExitStack
from datetime import datetime, timedelta

import pytest
from pytest_mock.plugin import MockerFixture
from yarl import URL
from bson import ObjectId
from pymongo.results import DeleteResult

from ateme.openapi import (
    Request,
    Response,
    HTTPNotFound,
    HTTPBadRequest,
    HTTPUnauthorized,
    HTTPInternalServerError,
    HTTPConflict
)
from ateme.um_backend.database import Collections, UserAlreadyExist
from ateme.um_backend.types import DEFAULT_LOCAL_IDP_NAME, Token
from ateme.um_backend.loggers import get_activity_log
from ateme.um_backend.utils import utcnow


DEFAULT_PASSWORD = "defaultPassword0!"
LONG_PASSWORD = "NWKYEhMIPJs1dXxlJb8pj+ZxGJkkxYFNTiP2RxcuHU1cTu6X04ul7ezy9nZJ47KV0yjrzEhw4FA4WKhoiSK4vA=="
DoesNotRaise = ExitStack


@pytest.mark.parametrize("req, mocks_func, assert_mock_called, exception_expected, response_expected", [
    # No token use case
    pytest.param(
        Request(
            parameters={},
            body={"username": "test", "password": "aaa"},
            headers={},
            url=URL(),
            method="",
            remote="",
        ),
        {},
        {},
        pytest.raises(HTTPUnauthorized, match="Can't find token in request"),
        None,
        id="no-token"
    ),
    # Password constraints failed
    pytest.param(
        Request(
            parameters={},
            body={"username": "test", "old_password": "old", "new_password": "test"},
            headers={'Authorization': 'Bearer custom_token'},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="custom_token",
                    started_date=datetime.now(),
                    expiration_date=datetime.today() + timedelta(hours=1),
                    refresh_token="refresh_token",
                    refresh_token_expiration_date=datetime.today() + timedelta(hours=2),
                    user_id="c3e64a32008ec75839397a15007a322ddf9043d5"
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {
                    "username": "test",
                    "password": "aaa",
                    "old_password": "old",
                    "creation_id": ObjectId(b"foo-bar-quux"),
                    "idp_name": "local",
                    "user_id": "c3e64a32008ec75839397a15007a322ddf9043d5",
                    "_id": "123456",
                }
            }
        },
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call("custom_token")
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call(user_id="c3e64a32008ec75839397a15007a322ddf9043d5", _id=True, creation_id=True)
            ],
        },
        pytest.raises(HTTPBadRequest, match="The password doesn't match the constraints"),
        None,
        id="password-constraints-failed"
    ),
    # Identical password
    pytest.param(
        Request(
            parameters={},
            body={"username": "test", "old_password": "old", "new_password": "old"},
            headers={'Authorization': 'Bearer custom_token'},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="custom_token",
                    started_date=datetime.now(),
                    expiration_date=datetime.today() + timedelta(hours=1),
                    refresh_token="refresh_token",
                    refresh_token_expiration_date=datetime.today() + timedelta(hours=2),
                    user_id="c3e64a32008ec75839397a15007a322ddf9043d5"
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {
                    "username": "test",
                    "password": "aaa",
                    "old_password": "old",
                    "creation_id": ObjectId(b"foo-bar-quux"),
                    "idp_name": "local",
                    "user_id": "c3e64a32008ec75839397a15007a322ddf9043d5",
                    "_id": "123456",
                }
            }
        },
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call("custom_token")
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call(user_id="c3e64a32008ec75839397a15007a322ddf9043d5", _id=True, creation_id=True)
            ],
        },
        pytest.raises(HTTPBadRequest, match="Password must be different from previous one"),
        None,
        id="identical-password"
    ),
    # Incorrect password
    pytest.param(
        Request(
            parameters={},
            body={"username": "test", "old_password": "wrong_old", "new_password": "test"},
            headers={'Authorization': 'Bearer custom_token'},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="custom_token",
                    started_date=datetime.now(),
                    expiration_date=datetime.today() + timedelta(hours=1),
                    refresh_token="refresh_token",
                    refresh_token_expiration_date=datetime.today() + timedelta(hours=2),
                    user_id="c3e64a32008ec75839397a15007a322ddf9043d5"
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {
                    "username": "test",
                    "password": "aaa",
                    "old_password": "old",
                    "creation_id": ObjectId(b"foo-bar-quux"),
                    "idp_name": "local",
                    "user_id": "c3e64a32008ec75839397a15007a322ddf9043d5",
                    "_id": "123456",
                }
            }
        },
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call("custom_token")
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call(user_id="c3e64a32008ec75839397a15007a322ddf9043d5", _id=True, creation_id=True)
            ],
        },
        pytest.raises(HTTPBadRequest, match="Incorrect old password, please retry"),
        None,
        id="old-password-failed"
    ),
    # Change password success
    pytest.param(
        Request(
            parameters={},
            body={"old_password": "old", "new_password": "Azerty@123!"},
            headers={'Authorization': 'Bearer custom_token'},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="custom_token",
                    started_date=datetime.now(),
                    expiration_date=datetime.today() + timedelta(hours=1),
                    refresh_token="refresh_token",
                    refresh_token_expiration_date=datetime.today() + timedelta(hours=2),
                    user_id="c3e64a32008ec75839397a15007a322ddf9043d5"
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {
                    "username": "test",
                    "password": "aaa",
                    "old_password": "old",
                    "creation_id": ObjectId(b"foo-bar-quux"),
                    "idp_name": "local",
                    "user_id": "c3e64a32008ec75839397a15007a322ddf9043d5",
                    "_id": "123456",
                }
            },
            "ateme.um_backend.database.Database.update_user_by_id": {"return_value": None},
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_list_by_user_id": {
                "return_value": [
                    Token(
                        token="custom_token",
                        started_date=datetime.now(),
                        expiration_date=datetime.today() + timedelta(hours=1),
                        refresh_token="refresh_token",
                        refresh_token_expiration_date=datetime.today() + timedelta(hours=2),
                        user_id="c3e64a32008ec75839397a15007a322ddf9043d5"
                    )
                ]
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.update_user_id": {"return_value": None},
        },
        {
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call("custom_token")
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call(user_id="c3e64a32008ec75839397a15007a322ddf9043d5", _id=True, creation_id=True)
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_list_by_user_id": [
                call(user_id="c3e64a32008ec75839397a15007a322ddf9043d5")
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.update_user_id": [
                call("custom_token", "6039630d8ed521edd55f6cbae5f3ff76501d81ac", session=ANY)
            ],
        },
        DoesNotRaise(),
        Response(200, {"body": "Password changed successfully !"}, {"content-type": "application/json"}),
        id="success-change-password"
    ),
], indirect=["mocks_func"])
async def test_change_password_user(
    init_api,
    req: Request,
    mocks_func: dict[str, dict],
    assert_mock_called: dict[str, dict],
    exception_expected: ExitStack,
    response_expected: Response | None,
):
    # pylint: disable=too-many-arguments
    """

    Check /password endpoint behavior (change_password operationId)
    Try to update user password with admin user
    Args:
        req (Request): request pass to update_users
        mocks_func (dict): mock database function
        assert_mock_called (dict): map function mock into mock_database to args called match
        exception_expected: exception expected when calling handler
    """
    with exception_expected:
        response = await init_api.change_password(req)
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers

    # Check args of mock called
    for _mock_func, _calls in assert_mock_called.items():
        if not _calls:
            mocks_func[_mock_func].assert_not_called()
        else:
            mocks_func[_mock_func].assert_has_calls(_calls)


async def test_change_username_not_allowed(init_backend_with_admin, init_database, admin_user):
    """
    Try to update user password with admin user
    It's not revelant to allow update of username...
    TODO:
    * Always relevant to update username ?
    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    db = init_database
    test_scope = "usr:test_scope"
    res = await db.db[Collections.scopes.name].insert_one({"id": test_scope,
                                                           "content": [{"action": "usr:get_test",
                                                                        "resource": {},
                                                                        "policy": "allow"}]})
    assert res

    username_1 = "Yaya"
    username_2 = "Yoyo"
    password = DEFAULT_PASSWORD

    # Create a user with scope administrator
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": username_1,
                "password": password,
                "scopes": ["usr:guest", test_scope, "usr:administrator"],
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201

    # Create a second user
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": username_2,
                "password": password,
                "scopes": ["usr:guest", test_scope],
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201

    resp = await _api.get('/users', headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()

    assert len(body) == 3, f'{body}'
    assert body[0]["username"] == username_1
    assert sorted(body[0].get('scopes', [])) == \
        sorted([test_scope, 'usr:guest', 'usr:administrator']), body[0].get('scopes', [])
    assert body[1]["username"] == username_2
    assert sorted(body[1].get('scopes', [])) == \
        sorted([test_scope, 'usr:guest']), body[1].get('scopes', [])

    # Login to first user
    resp = await _api.post(
        "/token",
        json={"username": username_1, "password": password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()

    token_user = body["access_token"]
    headers_user = {"content-type": "application/json", 'Authorization': f"Bearer {token_user}"}

    # Change username with a wrong password
    url_user_1 = f"{DEFAULT_LOCAL_IDP_NAME}/{username_1}"
    url_user_2 = f"{DEFAULT_LOCAL_IDP_NAME}/{username_2}"
    resp = await _api.patch(
        f"/users/{url_user_1}",
        json={"username": username_2, "password": "456"},
        headers=_admin_headers,
    )
    assert await resp.text() == "The password doesn't match the constraints"
    assert resp.status == 400

    # Change username with a username (deprecated) already taken by another user
    resp = await _api.patch(
        f"/users/{url_user_1}",
        json={"username": username_2, "password": password},
        headers=_admin_headers,
    )
    assert resp.status == 200
    resp = await _api.get(
        f"/users/{url_user_1}",
        headers=_admin_headers,
    )
    user_data = await resp.json()
    assert user_data['username'] == username_1

    # Change username (deprecated) with the admin's username
    resp = await _api.patch(
        f"/users/{url_user_1}",
        json={"username": admin_user["username"], "password": password},
        headers=_admin_headers,
    )
    assert resp.status == 200
    assert (
        (await resp.text())
        == "OK"
    )

    # Change password of another user
    resp = await _api.patch(
        f"/users/{url_user_2}",
        json={"password": password},
        headers=headers_user,
    )
    assert resp.status == 200

    # Delete the second user and retry to change username
    resp = await _api.delete(
        "/users",
        json=[{"username": username_2, "idp_name": DEFAULT_LOCAL_IDP_NAME}],
        headers=_admin_headers,
    )
    assert resp.status == 200
    resp = await _api.patch(
        f"/users/{url_user_1}",
        json={"username": username_2, "password": password},
        headers=headers_user,
    )
    assert resp.status == 200

    # Scopes shall be unchanged after patchs: 'usr:test_scope', 'usr:guest', 'usr:administrator'
    resp = await _api.get("/users", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2, f'{body}'
    # Username should be unchanged (deprecated)
    assert body[0]["username"] == username_1
    assert sorted(body[0].get('scopes', [])) == \
        sorted([test_scope, 'usr:guest', 'usr:administrator']), body[0].get('scopes', [])

    # Login
    resp = await _api.post(
        "/token",
        json={"username": username_1, "password": password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206

    # Remove administrator scope from user
    resp = await _api.patch(
        f"/users/{url_user_1}",
        json={"scopes": ["usr:guest", test_scope]},
        headers=_admin_headers,
    )
    assert resp.status == 200


@pytest.mark.parametrize(
    "req, mock_database_func, mock_database_func_args_expected, exception_expected, response_expected", [
        pytest.param(
            Request(
                parameters={
                    "username": "jean",
                    "idp_name": "local"
                },
                body={},
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.database.Database.get_user_by_name": {"return_value": None},
            },
            {
                "ateme.um_backend.database.Database.get_user_by_name": [
                    call(
                        username="jean",
                        _id=False,
                        internal=False,
                        internal_projection=False,
                        idp_name="local",
                    )
                ]
            },
            pytest.raises(HTTPNotFound, match=""),
            None,
            id="user-not-found"
        ),
        pytest.param(
            Request(
                parameters={
                    "username": "jean",
                    "idp_name": "local"
                },
                body={},
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.database.Database.get_user_by_name": {"return_value": {"username": "jean"}},
            },
            {
                "ateme.um_backend.database.Database.get_user_by_name": [
                    call(
                        username="jean",
                        _id=False,
                        internal=False,
                        internal_projection=False,
                        idp_name="local",
                    )
                ]
            },
            DoesNotRaise(),
            Response(200, {"username": "jean"}, {"content-type": "application/json"}),
            id="retrieve-user-success"
        )
    ])
async def test_get_user_by_name(
    init_api,
    req: Request,
    mock_database_func: dict[str, dict],
    mock_database_func_args_expected: dict[str, _Call],
    exception_expected: ExitStack,
    response_expected: Response,
    mocker: MockerFixture,
):
    # pylint: disable=too-many-arguments
    """

    Test `get_user_by_name` handler of `UserManagementApi`, each parametrize define a use case
    and pass to handler a specific request, mock database calls with different return value.
    So we will expect a different response or HTTPException.
    """
    mocks: dict[str, AsyncMock] = {}
    # Apply mock patch on every database function used by `get_user_by_name` handler.
    for _mock_func, _mock_args in mock_database_func.items():
        mocks[_mock_func] = mocker.patch(_mock_func, **_mock_args)

    # If there is a http exception expected
    with exception_expected:
        # Call directly UserManagementApi.get_user_by_name handler.
        response = await init_api.get_user_by_name(req)

        # Check response status_code, data and headers
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mock_database_func_args_expected.items():
        mocks[_mock_func].assert_has_calls(_calls)

@pytest.mark.parametrize("status, assert_raise, username, passwords_and_reasons", [
(201, DoesNotRaise(), "good_user", [["@$!%*&aA1éà", "All special chars accepted"]]),
(400, pytest.raises(HTTPBadRequest), "bad_user", [["@$?&aA1", "Not enough chars"],
                   ["1aA$"*64, "Too much chars"],
                   ["aaaaaaaaaa", "Upper case, number and special char missings"],
                   ["AAAAAAAAAA", "Lower case, number and special char missings"],
                   ["!!!!!!!!!!", "Upper case, number and and lower case char"],
                   ["12345678910", "Lower case, upper case, number and special char missings"],
                   ["12345Aa.aa", "Special char missing"],
                   ["12345Aa;aa", "Special char missing"],
                   ["12345Aa:aa", "Special char missing"],
                   ["12345Aa/aa", "Special char missing"],
                   ["12345Aa,", "Special char missing"],
                   ["12345Aa§aa", "Special char missing"],
                   ["12345Aa_aa", "Special char missing"],
                   ["12345Aa-", "Special char missing"],
                   ["12345Aa[aa", "Special char missing"],
                   ["12345Aa{aa", "Special char missing"]])
])
async def test_password_constraints(init_api, init_backend_with_admin, status,
                                    assert_raise, username, passwords_and_reasons):
    """
    Make some request to create users, to test the regex
    password conf : 10/255 min/max char, 1 lowercase/uppercase/digit/special char
    """
    _, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    for password, reason in passwords_and_reasons:
        with assert_raise:
            resp: Response = await init_api.add_user(
                Request(parameters={}, body={"username": username, "password": password},
                        headers=_admin_headers, url=URL(''), method='', remote=''))
            assert resp.status_code == status, "Failed for case: " + reason

@pytest.mark.parametrize(
    "req, mocks_func, mock_database_func_args_expected, exception_expected, response_expected", [
        pytest.param(
            Request(
                parameters={},
                body={},
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {},
            {},
            pytest.raises(HTTPUnauthorized, match=""),
            None,
            id="no-token-provide"
        ),
        pytest.param(
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer 123456"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {"return_value": None},
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("123456")
                ],
            },
            pytest.raises(HTTPUnauthorized, match="Missing token in headers"),
            None,
            id="token-not-in-db"
        ),
        pytest.param(
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer 123456"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                    "return_value": Token(
                        token="123456",
                        started_date=utcnow(),
                        expiration_date=utcnow().replace(tzinfo=None) - timedelta(hours=1),
                        refresh_token="fake",
                        refresh_token_expiration_date="fake",
                        user_id="fake",
                    )
                },
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("123456")
                ],
            },
            pytest.raises(HTTPUnauthorized, match="Token expired"),
            None,
            id="token-expired"
        ),
        pytest.param(
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer 123456"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                    "return_value": Token(
                        token="123456",
                        started_date=datetime.now(),
                        expiration_date=datetime.now() + timedelta(days=1),
                        refresh_token="fake",
                        refresh_token_expiration_date="fake",
                        user_id="123456",
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id": {
                    "return_value": None
                },
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("123456")
                ],
                "ateme.um_backend.database.Database.get_user_by_id": [
                    call(user_id="123456", _id= False, creation_id= False)
                ],
            },
            pytest.raises(HTTPNotFound, match="User not found"),
            None,
            id="user-not-found"
        ),
        pytest.param(
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer 123456"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                    "return_value": Token(
                        token="123456",
                        started_date=datetime.now(),
                        expiration_date=datetime.now() + timedelta(days=1),
                        refresh_token="fake",
                        refresh_token_expiration_date="fake",
                        user_id="123456",
                    )
                },
                "ateme.um_backend.database.Database.get_user_by_id": {
                    "return_value": {"username": "jean"}
                },
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("123456")
                ],
                "ateme.um_backend.database.Database.get_user_by_id": [
                    call(user_id="123456", _id= False, creation_id= False)
                ],
            },
            DoesNotRaise(),
            Response(200, {"username": "jean"}, {"content-type": "application/json"}),
            id="user-retrieve-success"
        ),
    ], indirect=["mocks_func"])
async def test_get_current_user(
    init_api,
    req: Request,
    mocks_func: dict[str, dict],
    mock_database_func_args_expected: dict[str, _Call],
    exception_expected: ExitStack,
    response_expected: Response,
):
    # pylint: disable=too-many-arguments
    """

    Test `get_current_user` handler, each parametrize define a request pass to handler and
    mock database call with different return value, so we will expect a specific response or
    HTTPException.
    """
    # If there is a http exception expected
    with exception_expected:
        # Call directly UserManagementApi.get_current_user handler.
        response = await init_api.get_current_user(req)

        # Check response status_code, data and headers
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mock_database_func_args_expected.items():
        mocks_func[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize(
    "req, mocks_func, mock_database_func_args_expected, exception_expected, response_expected,  expected_log", [
        # Will be fix by https://myateme.atlassian.net/browse/MS-8154
        #       # Can't update admin user use case
        #       pytest.param(
        #           Request(
        #               parameters={
        #                   "username": "jean",
        #                   "idp_name": "local"
        #               },
        #               body={},
        #               headers={},
        #               url=URL(),
        #               method="",
        #               remote="",
        #           ),
        #           {
        #               "ateme.um_backend.database.Database.is_admin": {"return_value": True}
        #           },
        #           {
        #               "ateme.um_backend.database.Database.is_admin": [call(username="jean")],
        #           },
        #           pytest.raises(HTTPForbidden, match="Can't update admin user"),
        #           None,
        #           id="cant-update-admin-user"
        #       ),
        # Can't find user to update
        pytest.param(
            Request(
                parameters={
                    "username": "jean",
                    "idp_name": "local"
                },
                body={},
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.database.Database.get_user_by_name": {"return_value": None}
            },
            {
                "ateme.um_backend.database.Database.get_user_by_name": [
                    call(
                        username="jean",
                        internal=False,
                        internal_projection=True,
                        idp_name="local",
                    )
                ],
            },
            pytest.raises(HTTPNotFound, match="Incorrect username, user not found"),
            None,
            "failed to update user jean:local",
            id="user-not-found"
        ),
        # Update user scopes success
        pytest.param(
            Request(
                parameters={
                    "username": "jean",
                    "idp_name": "local"
                },
                body={
                    "session_timeout_disabled": True,
                    "scopes": ["usr:administrator", "usr:engineer"],
                    "first_login": True
                },
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.database.Database.get_user_by_name": {
                    "return_value": {"username": "jean", "scopes": ["usr:monitor"], "user_id": "654321"}
                },
                "ateme.um_backend.database.Database.update_user_by_name": {
                    "return_value": None
                },
                "ateme.um_backend.dao.collection_clients.CollectionClients.delete_many": {
                    "return_value": None
                },
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {
                    "return_value": None
                },
            },
            {
                "ateme.um_backend.database.Database.get_user_by_name": [
                    call(
                        username="jean",
                        internal=False,
                        internal_projection=True,
                        idp_name="local",
                    )
                ],
                "ateme.um_backend.database.Database.update_user_by_name": [
                    call(
                        username="jean",
                        scopes={"usr:administrator", "usr:engineer"},
                        password=None,
                        level=None,
                        enabled=None,
                        password_last_update=None,
                        internal=False,
                        idp_name="local",
                        first_login=True,
                        session_timeout_disabled=True,
                        password_expiration_disabled=False
                    )
                ],
                "ateme.um_backend.dao.collection_clients.CollectionClients.delete_many": [
                    call(username="jean", idp_name="local")
                ],
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": [
                    call(user_id="654321")
                ]
            },
            DoesNotRaise(),
            Response(
                200,
                "OK",
                {"content-type": "text/plain"}
            ),
            "updated user jean:local with disable session timeout set to True, "
            "adding scopes usr:administrator, usr:engineer, forcing to change the password",
            id="update-with-session-timeout-enabled"
        ),
        # Update user success with password_expiration_disabled set to true
        pytest.param(
            Request(
                parameters={
                    "username": "jean",
                    "idp_name": "local"
                },
                body={
                    "password_expiration_disabled": True
                },
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.database.Database.get_user_by_name": {
                    "return_value": {"username": "jean", "scopes": [], "user_id": "654321"}
                },
                "ateme.um_backend.database.Database.update_user_by_name": {
                    "return_value": None
                },
                "ateme.um_backend.dao.collection_clients.CollectionClients.delete_many": {
                    "return_value": None
                },
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {
                    "return_value": None
                },
            },
            {
                "ateme.um_backend.database.Database.get_user_by_name": [
                    call(
                        username="jean",
                        internal=False,
                        internal_projection=True,
                        idp_name="local",
                    )
                ],
                "ateme.um_backend.database.Database.update_user_by_name": [
                    call(
                        username="jean",
                        scopes={"usr:guest"},
                        password=None,
                        level=None,
                        enabled=None,
                        password_last_update=None,
                        internal=False,
                        idp_name="local",
                        first_login=None,
                        session_timeout_disabled=False,
                        password_expiration_disabled=True
                    )
                ],
                "ateme.um_backend.dao.collection_clients.CollectionClients.delete_many": [
                    call(username="jean", idp_name="local")
                ],
            },
            DoesNotRaise(),
            Response(
                200,
                "OK",
                {"content-type": "text/plain"}
            ),
            "updated user jean:local with password expiration disabled",
            id="update-with-password-expiration-disabled-true"
        ),
    ], indirect=["mocks_func"])
async def test_update_user_by_name(
    init_api,
    req: Request,
    mocks_func: dict[str, dict],
    mock_database_func_args_expected: dict[str, _Call],
    exception_expected: ExitStack,
    response_expected: Response,
    expected_log: str
):
    # pylint: disable=too-many-arguments
    """

    Test `update_user_by_name` handler of `UserManagementApi`, mock database call and check args of this mock calls.
    Each parametrize configure a request to pass to handler and different return value for database function so we will
    expect a specific response or HTTPException.
    """
    # If there is a http exception expected
    with exception_expected as e:
        # Call directly UserManagementApi.update_user_by_name handler.
        response = await init_api.update_user_by_name(req)

        # Check response status_code, data and headers
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers
        activity_metadata = get_activity_log(response)
        assert expected_log == activity_metadata.message

    if not response_expected:
        activity_metadata = get_activity_log(e.value)
        assert expected_log == activity_metadata.message

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mock_database_func_args_expected.items():
        mocks_func[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize("req, mocks_func, mock_database_func_args_expected, exception_expected, response_expected,"
                         "expected_log", [
    # Don't find user to delete
    pytest.param(
        Request(
            parameters={
                "username": "jean",
                "idp_name": "local"
            },
            body={},
            headers={},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.delete_user_by_name": {
                "return_value": DeleteResult({"n": 0}, acknowledged=True)
            }
        },
        {
            "ateme.um_backend.database.Database.delete_user_by_name": [
                call(username="jean", internal=False, idp_name="local")
            ],
        },
        pytest.raises(HTTPNotFound, match="Delete user jean failed"),
        None,
        "failed to remove user jean:local",
        id="user-not-found"
    ),
    # Failed to delete user, inconsistent result from database
    pytest.param(
        Request(
            parameters={
                "username": "jean",
                "idp_name": "local"
            },
            body={},
            headers={},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.delete_user_by_name": {
                "return_value": DeleteResult({"n": 0}, acknowledged=False)
            }
        },
        {
            "ateme.um_backend.database.Database.delete_user_by_name": [
                call(username="jean", internal=False, idp_name="local")
            ],
        },
        pytest.raises(HTTPInternalServerError, match="Delete user jean failed"),
        None,
        "failed to remove user jean:local",
        id="server-error"
    ),
    # Delete user success
    pytest.param(
        Request(
            parameters={
                "username": "jean",
                "idp_name": "local"
            },
            body={},
            headers={},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.delete_user_by_name": {
                "return_value": DeleteResult({"n": 1}, acknowledged=True)
            }
        },
        {
            "ateme.um_backend.database.Database.delete_user_by_name": [
                call(username="jean", internal=False, idp_name="local")
            ],
        },
        DoesNotRaise(),
        Response(200, "User jean deleted", {"content-type": "text/plain"}),
        "removed user jean:local",
        id="delete-success"
    ),
], indirect=["mocks_func"])
async def test_remove_user_by_name(
    init_api,
    req: Request,
    mocks_func: dict[str, dict],
    mock_database_func_args_expected: dict[str, _Call],
    exception_expected: ExitStack,
    response_expected: Response,
    expected_log: str
):
    # pylint: disable=too-many-arguments
    """

    Check `remove_user_by_name` handler of UserManagementApi on different use-case.
    So we to check every behavior we mock `delete_user_by_name` function on db layer.
    """
    # If there is a http exception expected
    with exception_expected as e:
        # Call directly UserManagementApi.remove_user_by_name handler.
        response = await init_api.remove_user_by_name(req)

        # Check response status_code, data and headers
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers
        activity_metadata = get_activity_log(response)
        assert expected_log == activity_metadata.message

    if not response_expected:
        activity_metadata = get_activity_log(e.value)
        assert expected_log == activity_metadata.message

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mock_database_func_args_expected.items():
        mocks_func[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize("internal", [False, True], indirect=["internal"])
async def test_add_users(init_api, mocker, internal):
    """ Test multiple user creation """
    headers = {"Authorization": "Bearer 123456"}

    async def mock_is_admin(*_args, **kwargs):
        return kwargs['username'] == 'admin'
    mocker.patch('ateme.um_backend.database.Database.is_admin', mock_is_admin)
    mocker.patch('ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id', return_value=True)

    async def mock_create_user(_, user, *_args, **_kwargs):
        if user.username == 'duplicate':
            raise UserAlreadyExist('duplicate already exists')
    mocker.patch('ateme.um_backend.database.Database.create_user', mock_create_user)

    with DoesNotRaise():
        resp: Response = await init_api.add_users(
            Request(parameters={}, body=[
                {'username': 'foo', 'password': 'AtemeAAA0!', 'idp_name': 'local', 'scopes': []},
                {'username': 'admin', 'password': 'AtemeAAA0!', 'idp_name': 'local', 'scopes': []},
                {'username': 'foo2', 'password': 'AtemeAAA0!', 'idp_name': 'myIdp', 'scopes': []},
                {'username': 'foo3', 'password': '', 'idp_name': 'local', 'scopes': []},
                {'username': 'foo4', 'password': 'aa', 'idp_name': 'local', 'scopes': []},
                {'username': 'duplicate', 'password': 'AtemeAAA0!', 'idp_name': 'local', 'scopes': []},
            ], headers=headers, url=URL(''), method='', remote=''))

    assert 201 == resp.status_code
    expected_errors = [
        "Unable to create user 'admin': admin is the administrator's name, please choose another one!",
        "Unable to create user 'foo4': the password doesn't match the constraints",
        "Unable to create user 'duplicate': duplicate already exists"
    ]
    if internal:
        expected_errors.append("Unable to create user 'foo2': impossible to create an internal user with an "
                               "idp_name")
    else:
        expected_errors.append("Unable to create user 'foo3': a password is required for local users")
    assert sorted(expected_errors) == sorted(resp.data.get('errors'))


@pytest.mark.parametrize(
    "body, internal, assert_raise, expected_log, expected_error",
    [
        pytest.param(
            {'username': 'foo', 'password': 'AtemeAAA0!', 'idp_name': 'local', 'scopes': []},
            False,
            DoesNotRaise(),
            'added user foo:local with disable session timeout set to False',
            '',
            id='create-user-success'
        ),
        pytest.param(
            {'username': 'admin', 'password': 'AtemeAAA0!', 'idp_name': 'local', 'scopes': []},
            False,
            pytest.raises(HTTPBadRequest),
            'failed to add user admin:local',
            "admin is the administrator's name",
            id='create-user-invalid-admin-name'
        ),
        pytest.param(
            {'username': 'foo', 'password': 'AtemeAAA0!', 'idp_name': 'myIdp', 'scopes': []},
            True,
            pytest.raises(HTTPBadRequest),
            'failed to add user foo:myIdp',
            "impossible to create an internal user with an idp_name",
            id='create-user-invalid-internal-with-idp'
        ),
        pytest.param(
            {'username': 'foo', 'password': '', 'idp_name': 'local', 'scopes': []},
            False,
            pytest.raises(HTTPBadRequest),
            'failed to add user foo:local',
            "a password is required for local users",
            id='create-user-invalid-missing-password'
        ),
        pytest.param(
            {'username': 'foo', 'password': 'aa', 'idp_name': 'local', 'scopes': []},
            False,
            pytest.raises(HTTPBadRequest),
            'failed to add user foo:local',
            "the password doesn't match the constraints",
            id='create-user-invalid-password'
        )
    ],
    indirect=["internal"]
)
async def test_add_user(init_api, init_backend_with_admin, mocker, body, internal, assert_raise,
                        expected_log, expected_error: str):
    """ Test single user creation """
    # pylint: disable=too-many-arguments,unused-argument
    _, _, admin_token = init_backend_with_admin
    headers = {"Authorization": f"Bearer {admin_token}"}

    async def mock_is_admin(*_args, **kwargs):
        return kwargs['username'] == 'admin'
    mocker.patch('ateme.um_backend.database.Database.is_admin', mock_is_admin)
    mocker.patch('ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id', return_value=True)
    mocker.patch('ateme.um_backend.database.Database.create_user')

    with assert_raise as e:
        resp: Response = await init_api.add_user(
            Request(parameters={}, body=body, headers=headers, url=URL(''), method='', remote=''))

    if expected_error:
        assert expected_error in str(e)
        activity_metadata = get_activity_log(e.value)
        assert expected_log == activity_metadata.message
    else:
        assert 201 == resp.status_code
        activity_metadata = get_activity_log(resp)
        assert expected_log == activity_metadata.message


@pytest.mark.parametrize("internal", [False], indirect=["internal"])
async def test_add_user_conflict(init_api, mocker, internal):
    # pylint: disable=unused-argument
    """ Test single user creation with conflict """
    headers = {"Authorization": "Bearer 123456"}

    mocker.patch('ateme.um_backend.database.Database.is_admin', return_value=False)
    mocker.patch('ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id', return_value=True)
    mocker.patch('ateme.um_backend.database.Database.create_user',
                 side_effect=UserAlreadyExist('foo already exists'))

    with pytest.raises(HTTPConflict) as e:
        await init_api.add_user(
            Request(parameters={},
                    body={'username': 'foo', 'password': 'AtemeAAA0!', 'idp_name': 'local', 'scopes': []},
                    headers=headers, url=URL(''), method='', remote=''))

    assert 'foo already exists' == str(e.value.data)


@pytest.mark.parametrize("req, mock_database, mock_database_args, exception_expected, response_expected", [
    # No token define in headers, so impossible to determine if it's internal or not
    pytest.param(
        Request(
            parameters={},
            body={"username": "test"},
            headers={},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {},
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {},
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {},
            "ateme.um_backend.database.Database.get_user_by_id": {},
        },
        {},
        pytest.raises(HTTPUnauthorized, match="Fail to extract user from token"),
        None,
        id="no-token-in-headers",
    ),
    # Can't find token in database so raise Unauthorized http response.
    pytest.param(
        Request(
            parameters={},
            body={"username": "test"},
            headers={"Authorization": "Bearer 123456"},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {},
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {},
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {"return_value": None},
            "ateme.um_backend.database.Database.get_user_by_id": {},
        },
        {"ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [call("123456")]},
        pytest.raises(HTTPUnauthorized, match="Fail to extract user from token"),
        None,
        id="no-token-in-db",
    ),
    # Can't find user to disconnect in database
    pytest.param(
        Request(
            parameters={},
            body={"username": "test"},
            headers={"Authorization": "Bearer 123456"},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": None
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {},
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="fake",
                    started_date="fake",
                    expiration_date="fake",
                    refresh_token="fake",
                    refresh_token_expiration_date="fake",
                    user_id="123456",
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {"internal": False}
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
                call(username="test", internal=False, idp_name="local")
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [call("123456")],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call("123456", internal_projection=True)
            ],
        },
        pytest.raises(HTTPNotFound, match="User not found"),
        None,
        id="user-not-found",
    ),
    # No token to deleted
    pytest.param(
        Request(
            parameters={},
            body={"username": "test"},
            headers={"Authorization": "Bearer 123456"},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": {"user_id": "987654321"}
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {
                "return_value": DeleteResult({"n": 0}, acknowledged=True)
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="fake",
                    started_date="fake",
                    expiration_date="fake",
                    refresh_token="fake",
                    refresh_token_expiration_date="fake",
                    user_id="123456",
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {"internal": False}
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
                call(username="test", internal=False, idp_name="local")
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": [
                call(user_id="987654321")
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [call("123456")],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call("123456", internal_projection=True)
            ],
        },
        pytest.raises(
            HTTPInternalServerError,
            match="Can't delete token, maybe the user is not connected",
        ),
        None,
        id="no-token-deleted",
    ),
    # Force user disconnect success
    pytest.param(
        Request(
            parameters={},
            body={"username": "test"},
            headers={"Authorization": "Bearer 123456"},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": {"user_id": "987654321"}
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": {
                "return_value": DeleteResult({"n": 1}, acknowledged=True)
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": Token(
                    token="fake",
                    started_date="fake",
                    expiration_date="fake",
                    refresh_token="fake",
                    refresh_token_expiration_date="fake",
                    user_id="123456",
                )
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": {"internal": False}
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
                call(username="test", internal=False, idp_name="local")
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.remove_by_user_id": [
                call(user_id="987654321")
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [call("123456")],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call("123456", internal_projection=True)
            ],
        },
        DoesNotRaise(),
        Response(
            200,
            {"body": "test successfully disconnected !"},
            {"content-type": "application/json"},
        ),
        id="user-disconnect-success",
    ),
])
async def test_force_disconnection(
    init_api,
    req: Request,
    mock_database: dict[str, dict],
    mock_database_args: dict[str, list[_Call]],
    exception_expected: ExitStack,
    response_expected: Response,
    mocker: MockerFixture,
):
    # pylint: disable=too-many-arguments
    """

    Check `force_disconnect` handler (DELETE /token).
    Mock database call to simulate each case.
    Args:
        req (Request): request input pass to handler
        mock_database (dict[str, dict]): Database function to mock
        mock_database_args (dict[str, list[_Call]]): Map called args of database function
        exception_expected (ExitStack): If there is a http excecption expected, if not DoesNotRaise will be used.
        mocker (MockerFixture): mocker fixture helpers

    {key: item.mock_calls for key, item in mocks.items()}
    """
    mocks: dict[str, AsyncMock] = {}
    # Apply mock patch on every database function used by `force_user_disconnction` handler.
    for _mock_func, _mock_args in mock_database.items():
        mocks[_mock_func] = mocker.patch(_mock_func, **_mock_args)

    # If there is a http exception expected
    with exception_expected:
        # Call directly UserManagementApi.force_user_disconnection handler.
        response = await init_api.force_user_disconnection(req)

        # Check response status_code, data and headers
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mock_database_args.items():
        mocks[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize("create_users", [
    [{"username": "jean.dupont", "password": "Admin!0ZAA"}]
], indirect=["create_users"])
async def test_creation_id_field(create_users, init_backend_with_admin, init_database):
    """"
    Test creation_id parameter
    'creation_id' replaced '_id' as salting key in User collection
    So we check that when we update UM version it still works
    """
    username = create_users[0]["username"]
    password = create_users[0]["password"]
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # 1. Create user
    resp = await _api.post(
        "/users",
        json=[{"username": username, "password": password, "scopes": ["usr:administrator"]}],
        headers=_admin_headers,
    )
    assert resp.status == 201

    # 2. Replace creation_id by _id to use as salting key
    result = await _db.db[Collections.users.name].find_one({"username": username})
    await _db.db[Collections.users.name].delete_one({"username": username})
    result["_id"] = result["creation_id"]
    del result["creation_id"]
    await _db.db[Collections.users.name].insert_one(result)

    # 3. Get user token
    resp = await _api.post("/token", json={"username": username, "password": password})
    assert resp.status == 206
    body = await resp.json()

    assert "access_token" in body


@pytest.mark.parametrize(
    "req, mocks_func, mock_database_func_args_expected, exception_expected, response_expected", [
        # Update user preferences success
        pytest.param(
            Request(
                parameters={
                    "username": "jean",
                    "idp_name": "local",
                },
                body={
                    "favorite_application": "TLCN",
                    "another_preference": "my_preference"
                },
                headers={},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.user_management.UserManagementApi._find_user_by_headers": {
                    "return_value": {"username": "jean", "idp_name": "local"}
                },
                "ateme.um_backend.database.Database.update_user_by_name": {
                    "return_value": None
                },
                "ateme.um_backend.dao.collection_clients.CollectionClients.delete_many": {
                    "return_value": None
                },
            },
            {
                "ateme.um_backend.database.Database.update_user_by_name": [
                    call(
                        username="jean",
                        idp_name="local",
                        preferences={"favorite_application": "TLCN",
                                     "another_preference": "my_preference"}
                    )
                ]
            },
            DoesNotRaise(),
            Response(
                200,
                "OK",
                {"content-type": "text/plain"}
            ),
            id="update-preferences-success"
        ),
    ], indirect=["mocks_func"])
async def test_update_user_preferences(
    init_api,
    req: Request,
    mocks_func: dict[str, dict],
    mock_database_func_args_expected: dict[str, _Call],
    exception_expected: ExitStack,
    response_expected: Response,
):
    # pylint: disable=too-many-arguments
    """

    Test `update_user_preferences` handler of `UserManagementApi`, mock database call and check args of this mock calls.
    Each parametrize configure a request to pass to handler and different return value for database function so we will
    expect a specific response or HTTPException.
    """
    # If there is a http exception expected
    with exception_expected:
        # Call directly UserManagementApi.update_user_preferences handler.
        response = await init_api.update_user_preferences(req)

        # Check response status_code, data and headers
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mock_database_func_args_expected.items():
        mocks_func[_mock_func].assert_has_calls(_calls)

@pytest.mark.parametrize("req, mocks_func, assert_mock_called, exception_expected, response_expected", [
    pytest.param(
        Request(
            parameters={
                "username": "jean",
                "idp_name": "local",
            },
            body={ "disabled": True },
            headers={},
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.user_management.UserManagementApi._find_user_by_headers": {
                "return_value": {
                    "username": "jean",
                    "idp_name": "local",
                    "user_id": "c3e64a32008ec75839397a15007a322ddf9043d5",
                    "creation_id": ObjectId(b"foo-bar-quux"),
                    "_id": "123456",
                },
            },
            "ateme.um_backend.database.Database.update_user_by_name": {
                "return_value": None
            },
            "ateme.um_backend.dao.collection_clients.CollectionClients.delete_many": {
                "return_value": None
            },
        },
        {
            "ateme.um_backend.database.Database.update_user_by_name": [
                call(
                    username="jean",
                    idp_name="local",
                    session_timeout_disabled=True
                )
            ]
        },
        DoesNotRaise(),
        Response(
            200,
            {'body': 'Session timeout changed successfully !'},
            {"content-type": "application/json"}
        ),
        id="success-change-user-session-timeout"
    ),
], indirect=["mocks_func"])
async def test_change_user_session_timeout(
    init_api,
    req: Request,
    mocks_func: dict[str, dict],
    assert_mock_called: dict[str, dict],
    exception_expected: ExitStack,
    response_expected: Response | None,
):
    # pylint: disable=too-many-arguments
    """

    Check /session_timeout endpoint behavior (change_session_timeout operationId)
    Try to update session timeout with admin user
    Args:
        req (Request): request pass to update_users
        mocks_func (dict): mock database function
        assert_mock_called (dict): map function mock into mock_database to args called match
        exception_expected: exception expected when calling handler
    """
    with exception_expected:
        response = await init_api.change_session_timeout(req)
        assert response.status_code == response_expected.status_code
        assert response.data == response_expected.data
        assert response.headers == response_expected.headers

    # Check args of mock called
    for _mock_func, _calls in assert_mock_called.items():
        if not _calls:
            mocks_func[_mock_func].assert_not_called()
        else:
            mocks_func[_mock_func].assert_has_calls(_calls)

async def test_password_expiration(init_database, init_backend_with_admin):
    """

    Test that user password expiration works
    :return:
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    user_name = "user"
    user_password = "passwordA0!"
    user_wo_expiration_name = "user_wo_expiration"
    user_wo_expiration_password = "passwordA0!"

    update_conf_resp = await _api.put("/configuration",
                                      json={"password_policy": {"expiration_delay_in_days": -1}},
                                      headers=_admin_headers)
    assert update_conf_resp.status == 200

    # Create 2 non internal users, one with password expiration and one without
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": user_name,
                "password": user_password,
            },
            {
                "username": user_wo_expiration_name,
                "password": user_password,
                "password_expiration_disabled": True
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201

    # User can login bit got a 206 because it is its first login
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()
    assert body["reason"] == "First login"
    user_token = body['access_token']

    # User can change its password with the returned token
    resp = await _api.patch(
        "/user/me/password",
        json={"old_password": user_password, "new_password": user_password+"1"},
        headers={"content-type": "application/json", "Authorization": f"Bearer {user_token}"},
    )
    assert resp.status == 200
    user_password = user_password+"1"

    # Check that the first_login flag has been reset
    user_desc = await _db.get_user_by_name(user_name, 'local')
    assert not user_desc["first_login"]
    # next login resp is 200
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200

    # Patch in db  password_last_update for these users to make it expired
    delta = timedelta(days=2)
    password_last_update = datetime.utcnow().timestamp() - delta.total_seconds()

    await _db.update_user_by_name(username=user_name,
                                  password_last_update=password_last_update,
                                  idp_name=DEFAULT_LOCAL_IDP_NAME)
    await _db.update_user_by_name(username=user_wo_expiration_name,
                                  password_last_update=password_last_update,
                                  idp_name=DEFAULT_LOCAL_IDP_NAME)

    # user can still login because password expiration is globally disabled
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200

    # Patch the password_expiration in configuration to 1 day
    await _api.put("/configuration",
                   json={"password_policy": {"expiration_delay_in_days": 1}},
                   headers=_admin_headers)

    # Login for the first user returns 206 with reason 'password expired'
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()
    assert isinstance(body, dict)
    assert body["reason"] == "Password expired"
    user_token = body['access_token']

    # Check that the password_expired is set to True for this user
    resp = await _api.get("/user/me", headers={"Authorization": f"Bearer {user_token}"})
    user_desc = await resp.json()
    assert user_desc["password_expired"]
    assert not user_desc["first_login"]  # first_login should not set

    # User can change its password with the returned token
    resp = await _api.patch(
        "/user/me/password",
        json={"old_password": user_password, "new_password": user_password+"1"},
        headers={"content-type": "application/json", "Authorization": f"Bearer {user_token}"},
    )
    assert resp.status == 200

    # Check that the password_expired is reset
    user_desc = await _db.get_user_by_name(user_name, 'local')
    assert not user_desc["password_expired"]

    # Now, the login for the user returns 200
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password+"1"},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200

    # Login for the user with password_expiration disabled returns 206 but with reason first login
    resp = await _api.post(
        "/token",
        json={"username": user_wo_expiration_name, "password": user_wo_expiration_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()
    assert body["reason"] == "First login"


async def test_force_change_user_password_via_configuration(
    init_database, init_backend_with_admin
):
    """
    Test that users are forced to change passwords via configuration
    :return:
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    user_name = "user"
    user_password = "passwordA0!"

    # Create 1 new user with initial length password 10
    resp = await _api.post(
        "v2/users",
        json={"username": user_name, "password": user_password},
        headers=_admin_headers,
    )
    assert resp.status == 201

    # User can login but got a 206 because it is its first login
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()
    assert body["reason"] == "First login"
    user_token = body['access_token']

    # User can change its password with the returned token
    resp = await _api.patch(
        "/user/me/password",
        json={"old_password": user_password, "new_password": user_password+"1"},
        headers={"content-type": "application/json", "Authorization": f"Bearer {user_token}"},
    )
    assert resp.status == 200

    # Login after the first login, now the user can login with the new password
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password+"1"},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200


    # Force users to change password and use a new password length
    await _api.put("/configuration?force_change_password=true",
                   json={"password_policy": {"password_min_length": 12}},
                   headers=_admin_headers)

    # Check in DB if "password_expired" is updated
    result = await _db.db[Collections.users.name].find_one({"username": user_name})
    assert result["password_expired"] is True

    # The login for the user should now return 206
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password+"1"},
        headers={"content-type": "application/json"},
    )

    assert resp.status == 206
    body = await resp.json()
    assert body["reason"] == "Password expired"
    user_token = body['access_token']

    # User should now modify the password
    resp = await _api.patch(
        "/user/me/password",
        json={"old_password": user_password+"1", "new_password": user_password+"123"},
        headers={"content-type": "application/json", "Authorization": f"Bearer {user_token}"},
    )
    assert resp.status == 200

    # User can now login with the new password respecting the new constraints
    resp = await _api.post(
        "/token",
        json={"username": user_name, "password": user_password+"123"},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
