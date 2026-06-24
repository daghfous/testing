# pylint: disable=protected-access
"""
test_token.py
"""
from contextlib import nullcontext as does_not_raise
from datetime import timedelta
from unittest.mock import call
from yarl import URL
import pytest

from ateme.openapi import Request
from ateme.um_backend.utils import utcnow
from ateme.um_backend.types import Token
from ateme.um_backend.exceptions import CheckTokenError, RequestExtractError, CheckRemoteIPInvalid


DEFAULT_EXPIRATION_DATE = utcnow() + timedelta(hours=1)
DEFAULT_STARTED_DATE = utcnow()
DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE = utcnow() + timedelta(hours=2)


@pytest.mark.parametrize(
    "session_timeout_disabled, additional_args", [
        pytest.param(
            False,
            {"session_index": "session_index", "nameidentifier": "nameidentifier", "idp_name": "idp_name"},
            id="generate-session-timeout-disabled-False"
        ),
        pytest.param(
            True,
            {"session_index": "session_index", "nameidentifier": "nameidentifier", "idp_name": "idp_name"},
            id="generate-session-timeout-disabled-True"
        )
    ]
)
def test_token_generate(mocker, session_timeout_disabled, additional_args):
    """ test Token.generate
    """
    fake_now = utcnow()

    mocker.patch("ateme.um_backend.types.token._generate_token", return_value="token")
    mocker.patch("ateme.um_backend.types.token.utcnow", return_value=fake_now)

    token_expiration = timedelta(hours=1)
    refresh_token_expiration = timedelta(hours=2)
    token = Token.generate(
        user_id="user_id",
        token_expiration=token_expiration,
        refresh_token_expiration=refresh_token_expiration,
        session_timeout_disabled=session_timeout_disabled,
        user_ip="user_ip",
        **additional_args
    )
    assert token.token == "token"
    assert token.refresh_token == "token"
    if session_timeout_disabled:
        assert not token.expiration_date
        assert not token.refresh_token_expiration_date
    else:
        assert token.expiration_date == fake_now + token_expiration
        assert token.refresh_token_expiration_date == fake_now + refresh_token_expiration
    assert token.user_id == "user_id"
    assert token.user_ip == "user_ip"
    if additional_args:
        for key in additional_args:
            assert getattr(token, key) == additional_args[key]


@pytest.mark.parametrize(
    "context, requires, optionals, extras", [
        pytest.param(
            does_not_raise(),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id"
            },
            {},
            {},
            id="only required fields"
        ),
        pytest.param(
            does_not_raise(),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id"
            },
            {
                "user_ip": "user_ip",
                "session_index": "session_index",
                "nameidentifier": "nameidentifier",
                "idp_name": "idp_name"
            },
            {},
            id="with optional fields"
        ),
        pytest.param(
            does_not_raise(),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id"
            },
            {
                "user_ip": "user_ip",
                "session_index": "session_index",
                "nameidentifier": "nameidentifier",
                "idp_name": "idp_name"
            },
            {
                "_id": "id"
            },
            id="with optionals and extra fields"
        ),
        pytest.param(
            does_not_raise(),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id"
            },
            {
                "bad_arg": "user_ip",
            },
            {},
            id="invalid arg"
        ),
    ]
)
def test_token_from_dict(context, requires: dict, optionals: dict, extras: dict):
    """ test Token.from_dict
    """
    with context:
        token = Token.from_dict(requires | optionals | extras)
        assert token.token == requires["token"]
        assert token.expiration_date == requires["expiration_date"]
        assert token.refresh_token == requires["refresh_token"]
        assert token.refresh_token_expiration_date == requires["refresh_token_expiration_date"]
        assert token.user_id == requires["user_id"]
        if optionals and "user_ip" in optionals:
            assert token.user_ip == optionals["user_ip"]
        if optionals and "session_index" in optionals:
            assert token.session_index == optionals["session_index"]
        if optionals and "nameidentifier" in optionals:
            assert token.nameidentifier == optionals["nameidentifier"]
        if optionals and "idp_name" in optionals:
            assert token.idp_name == optionals["idp_name"]


@pytest.mark.parametrize(
    "token, expected_data", [
        pytest.param(
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=DEFAULT_EXPIRATION_DATE,
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                version=2
            ),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id",
                "version": 2
            },
            id="only required fields"
        ),
        pytest.param(
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=DEFAULT_EXPIRATION_DATE,
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="user_ip",
                session_index="session_index",
                nameidentifier="nameidentifier",
                idp_name="idp_name"
            ),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id",
                "user_ip": "user_ip",
                "session_index": "session_index",
                "nameidentifier": "nameidentifier",
                "idp_name": "idp_name",
                "version": 0
            },
            id="with optional fields"
        ),
        pytest.param(
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=DEFAULT_EXPIRATION_DATE,
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="user_ip",
                session_index=None,
                nameidentifier=None,
                idp_name=None
            ),
            {
                "token": "token",
                "started_date": DEFAULT_STARTED_DATE,
                "expiration_date": DEFAULT_EXPIRATION_DATE,
                "refresh_token": "refresh_token",
                "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                "user_id": "user_id",
                "user_ip": "user_ip",
                "version": 0
            },
            id="with some null optional fields"
        ),
    ]
)
def test_token_asdict(token: Token, expected_data: dict):
    """ test token.as_dict
    """
    result = token.as_dict()
    assert expected_data == result


def test_token_refresh_access_token(mocker):
    """ test Token.refresh_access_token
    """
    fake_now = utcnow()
    fake_token_expiration = timedelta(hours=5)

    mocker.patch("ateme.um_backend.types.token._generate_token", return_value="new_token")
    mocker.patch("ateme.um_backend.types.token.utcnow", return_value=fake_now)

    token = Token(
        token="token",
        started_date=DEFAULT_STARTED_DATE,
        expiration_date=DEFAULT_EXPIRATION_DATE,
        refresh_token="refresh_token",
        refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
        user_id="user_id"
    )
    token.refresh_access_token(fake_token_expiration)
    assert token.token == "new_token"
    assert token.expiration_date == fake_now + fake_token_expiration


@pytest.mark.parametrize(
    "context, _request, mocks_func, mocks_call_args, expected_result", [
        pytest.param(
            pytest.raises(RequestExtractError),
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
            "Can't find token in request",
            id="extract-token-failure"
        ),
        pytest.param(
            does_not_raise(),
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer token"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                    "return_value": Token(
                        token="token",
                        started_date=DEFAULT_STARTED_DATE,
                        expiration_date=DEFAULT_EXPIRATION_DATE.replace(tzinfo=None),
                        refresh_token="refresh_token",
                        refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                        user_id="user_id",
                    ),
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("token")
                ]
            },
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=DEFAULT_EXPIRATION_DATE.replace(tzinfo=None),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
            ),
            id="token-found"
        ),
        pytest.param(
            pytest.raises(CheckTokenError),
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer token"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                    "return_value": None,
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("token")
                ]
            },
            "Missing token in headers",
            id="token-not-found"
        ),
        pytest.param(
            pytest.raises(CheckTokenError),
            Request(
                parameters={},
                body={},
                headers={"Authorization": "Bearer token"},
                url=URL(),
                method="",
                remote="",
            ),
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                    "return_value": Token(
                        token="token",
                        started_date=DEFAULT_STARTED_DATE,
                        expiration_date=(utcnow() - timedelta(hours=1)).replace(tzinfo=None),
                        refresh_token="refresh_token",
                        refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                        user_id="user_id",
                    ),
                }
            },
            {
                "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                    call("token")
                ]
            },
            "Token expired",
            id="token-expired"
        )
    ],
    indirect=["mocks_func"]
)
@pytest.mark.asyncio
async def test__check_token(init_api, context, _request, mocks_func, mocks_call_args, expected_result):
    """ test _check_token
    """
    with context as error:
        result = await init_api._check_token(_request)
        assert result == expected_result
    if error:
        assert str(error.value) == expected_result
    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mocks_call_args.items():
        mocks_func[_mock_func].assert_has_calls(_calls)


@pytest.mark.parametrize(
    "create_and_log_users",
    [
        ([{"username": "Pavard", "password": "SecondPoteau!0"}]),
    ],
    indirect=["create_and_log_users"],
)
async def test_login_token_data(init_backend_with_admin, create_and_log_users):
    """ test login and check token data
    """
    _api, api, admin_token = init_backend_with_admin
    user_token = create_and_log_users["Pavard"]["token"]

    # Check if admin_token has a valid `user_ip`
    user_dict = await api.db.get_user_by_name(username="admin", idp_name="local")
    token = await api.db.collection_tokens.get_by_access_token(admin_token)
    assert token.user_id == user_dict["user_id"]
    assert token.user_ip == "127.0.0.1"

    # Check if user_token has a valid `user_ip`
    user_dict = await api.db.get_user_by_name(username="Pavard", idp_name="local")
    token = await api.db.collection_tokens.get_by_access_token(user_token)
    assert token.user_id == user_dict["user_id"]
    assert token.user_ip == "127.0.0.1"


@pytest.mark.parametrize(
    "create_and_log_users",
    [
        ([{"username": "Pavard", "password": "SecondPoteau!0"},
          {"username": "Test", "password": "SecondPoteau!0", "session_timeout_disabled": True}]),
    ],
    indirect=["create_and_log_users"],
)
async def test_token_sessions(init_backend_with_admin, create_and_log_users):
    """ test sessions endpoints
    """
    _api, _, admin_token = init_backend_with_admin

    # Check active sessions
    _admin_headers = {"Authorization": f"Bearer {admin_token}"}
    sessions = await _api.get("/sessions", headers=_admin_headers)
    sessions_before_delete = await sessions.json()
    for key_session in ['username', 'idp_name', 'user_ip', 'started_date', 'expiration_date', 'token_id']:
        assert key_session in sessions_before_delete[0]
    unlimited_session = None
    for _session in sessions_before_delete:
        if _session['username'] == 'Test':
            unlimited_session = _session
    assert unlimited_session['expiration_date'] == 'unlimited'

    # Delete a session
    await _api.delete(f"/sessions/{sessions_before_delete[1]['token_id']}", headers=_admin_headers)
    sessions = await _api.get("/sessions", headers=_admin_headers)
    sessions_after_delete = await sessions.json()
    assert len(sessions_before_delete) == len(sessions_after_delete) + 1

    # Try to delete the session again
    response = await _api.delete(f"/sessions/{sessions_before_delete[1]['token_id']}", headers=_admin_headers)
    assert response.status == 404


@pytest.mark.parametrize(
    "context, _request, token, user_dict, expected_result", [
        pytest.param(
            does_not_raise(),
            Request(
                parameters={},
                body={},
                headers={},
                url=URL(),
                method="",
                remote="172.29.3.27",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            None,
            id="remote-ip-when-no-token-user-ip"
        ),
        pytest.param(
            does_not_raise(),
            Request(
                parameters={},
                body={},
                headers={},
                url=URL(),
                method="",
                remote="172.29.3.27",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="172.29.3.27",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            None,
            id="remote-ip-match-with-token-user-ip"
        ),
        pytest.param(
            does_not_raise(),
            Request(
                parameters={},
                body={},
                headers={"User-Agent": "axios/1.6.5"},
                url=URL(),
                method="",
                remote="192.168.78.43",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="10.253.36.5",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            None,
            id="skip-remote-ip-check-user-agent-axios-165"
        ),
        pytest.param(
            does_not_raise(),
            Request(
                parameters={},
                body={},
                headers={"User-Agent": "axios/1.3.4"},
                url=URL(),
                method="",
                remote="192.168.78.43",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="10.253.36.5",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            None,
            id="skip-remote-ip-check-user-agent-axios-134"
        ),
        pytest.param(
            pytest.raises(CheckRemoteIPInvalid),
            Request(
                parameters={},
                body={},
                headers={"User-Agent": "axios/1.7.0"},
                url=URL(),
                method="",
                remote="192.168.78.43",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="10.253.36.5",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            (
                "remote ip invalid: 192.168.78.43 != 10.253.36.5",
                "wrong remote IP address 192.168.78.43 (expected 10.253.36.5)"
            ),
            id="skip-remote-ip-check-user-agent-axios-invalid"
        ),
        pytest.param(
            pytest.raises(CheckRemoteIPInvalid),
            Request(
                parameters={},
                body={},
                headers={"User-Agent": "axios/1.6.5 Mozilla/5.0"},
                url=URL(),
                method="",
                remote="192.168.78.43",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="10.253.36.5",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            (
                "remote ip invalid: 192.168.78.43 != 10.253.36.5",
                "wrong remote IP address 192.168.78.43 (expected 10.253.36.5)"
            ),
            id="skip-remote-ip-check-user-agent-axios-valid-but-not-alone"
        ),
        pytest.param(
            pytest.raises(CheckRemoteIPInvalid),
            Request(
                parameters={},
                body={},
                headers={},
                url=URL(),
                method="",
                remote="127.0.0.1",
            ),
            Token(
                token="token",
                started_date=DEFAULT_STARTED_DATE,
                expiration_date=utcnow() - timedelta(hours=1),
                refresh_token="refresh_token",
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="user_id",
                user_ip="172.29.3.27",
            ),
            {
                "username": "jdupont",
                "idp_name": "local",
            },
            (
                "remote ip invalid: 127.0.0.1 != 172.29.3.27",
                "wrong remote IP address 127.0.0.1 (expected 172.29.3.27)"
            ),
            id="remote-ip-invalid-against-token-user-ip"
        ),
    ]
)
def test__check_remote_ip(init_api, context, _request, token, user_dict, expected_result):
    """ test _check_remote_ip
    """
    with context as error:
        init_api._check_remote_ip(_request, token, user_dict)
    if error:
        assert str(error.value) == expected_result[0]
        assert error.value.activity_message == expected_result[1]
        assert error.value.activity_extra == {"user": user_dict["username"] + ":" + user_dict["idp_name"]}
