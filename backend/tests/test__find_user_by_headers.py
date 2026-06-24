"""
Test function UserManagementApi._find_user_by_headers
"""

# pylint: disable=protected-access,too-many-arguments,too-many-positional-arguments

from unittest.mock import call
from contextlib import ExitStack as DoesNotRaise
from datetime import timedelta
import pytest
from yarl import URL
from bson import ObjectId

from ateme.openapi import Request, HTTPNotFound, HTTPUnauthorized
from ateme.um_backend.utils import utcnow
from ateme.um_backend.types import Token
from ateme.um_backend.request_utils import HttpHeaders


ACCESS_TOKEN = "token"
USER_ID = "c3e64a32008ec75839397a15007a322ddf9043d5"
USERNAME = "jean"
IDP_NAME = "local"

DB_USER = {
    "username": USERNAME,
    "idp_name": IDP_NAME,
    "user_id": USER_ID,
    "creation_id": ObjectId(b"foo-bar-quux"),
    "_id": "123456",
}

TOKEN = Token(
    token=ACCESS_TOKEN,
    started_date=utcnow(),
    expiration_date=utcnow().replace(tzinfo=None) + timedelta(hours=1),
    refresh_token="refresh_token",
    refresh_token_expiration_date=utcnow() + timedelta(hours=2),
    user_id=USER_ID,
)


@pytest.mark.parametrize("req, mocks_func, assert_mock_called, exception_expected, result_expected", [
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
        pytest.raises(HTTPUnauthorized, match="Can't find token in request"),
        {},
        id="no-introspection-and-no-authorization-headers"
    ),
    pytest.param(
        Request(
            parameters={},
            body={},
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            },
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": None,
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": TOKEN
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": DB_USER,
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call(ACCESS_TOKEN)
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call(
                    user_id=USER_ID,
                    _id=True,
                    creation_id=True
                )
            ]
        },
        DoesNotRaise(),
        DB_USER,
        id="no-introspection-headers-user-found"
    ),
    pytest.param(
        Request(
            parameters={},
            body={},
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            },
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": None,
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": None,
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": None,
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call(ACCESS_TOKEN)
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
            ]
        },
        pytest.raises(HTTPUnauthorized, match="Missing token in headers"),
        {},
        id="no-introspection-headers-and-token-not-found"
    ),
    pytest.param(
        Request(
            parameters={},
            body={},
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            },
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": None,
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": TOKEN
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": None,
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
                call(ACCESS_TOKEN)
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
                call(
                    user_id=USER_ID,
                    _id=True,
                    creation_id=True
                )
            ]
        },
        pytest.raises(HTTPNotFound, match="User not found"),
        {},
        id="no-introspection-headers-user-not-found"
    ),
    pytest.param(
        Request(
            parameters={},
            body={},
            headers={
                HttpHeaders.X_USER: USERNAME,
                HttpHeaders.X_IDP_NAME: IDP_NAME,
            },
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": DB_USER,
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": None,
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": None,
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
                call(
                    username=USERNAME,
                    idp_name=IDP_NAME,
                    all_users=True,
                    _id=True,
                )
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
            ]
        },
        DoesNotRaise(),
        DB_USER,
        id="introspection-headers-user-found"
    ),
    pytest.param(
        Request(
            parameters={},
            body={},
            headers={
                HttpHeaders.X_USER: USERNAME,
                HttpHeaders.X_IDP_NAME: IDP_NAME,
            },
            url=URL(),
            method="",
            remote="",
        ),
        {
            "ateme.um_backend.database.Database.get_user_by_name": {
                "return_value": None,
            },
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": {
                "return_value": None,
            },
            "ateme.um_backend.database.Database.get_user_by_id": {
                "return_value": None,
            },
        },
        {
            "ateme.um_backend.database.Database.get_user_by_name": [
                call(
                    username=USERNAME,
                    idp_name=IDP_NAME,
                    all_users=True,
                    _id=True,
                )
            ],
            "ateme.um_backend.dao.collection_tokens.CollectionTokens.get_by_access_token": [
            ],
            "ateme.um_backend.database.Database.get_user_by_id": [
            ]
        },
        pytest.raises(HTTPNotFound, match="User not found"),
        {},
        id="introspection-headers-user-not-found"
    ),
], indirect=["mocks_func"])
async def test__find_user_by_headers(
    init_api,
    req,
    mocks_func,
    assert_mock_called,
    exception_expected,
    result_expected
):
    """ test__find_user_by_headers

    Args:
        init_api: fixture
        req: input request
        mocks_func: dict with mocked functions
        assert_mock_called: dict with mocked functions with expected args
        exception_expected: expected exception
        result_expected: expected result
    """
    with exception_expected:
        result = await init_api._find_user_by_headers(
            request=req, _id=True, creation_id=True
        )
        assert result == result_expected

    # Check args of mock called
    for _mock_func, _calls in assert_mock_called.items():
        if not _calls:
            mocks_func[_mock_func].assert_not_called()
        else:
            mocks_func[_mock_func].assert_has_calls(_calls)
