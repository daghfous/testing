""" test_collection_tokens.py """

from contextlib import nullcontext as does_not_raise
from datetime import datetime, timedelta
import pymongo
from pymongo.errors import DuplicateKeyError
import pytest

from ateme.um_backend.dao.collections import Collections
from ateme.um_backend.dao.collection_tokens import (
    DEPRECATED_INDEXES,
    INDEXES,
    Token
)

from .index_utils import son_to_indexmodels, compare_indexmodels_unordered


# CAUTION: mongo skips the milliseconds when storing a datetime field
DEFAULT_TOKEN_EXPIRATION_DATE = (datetime.now() + timedelta(hours=1)).replace(microsecond=0)
DEFAULT_TOKEN_STARTED_DATE = (datetime.now()).replace(microsecond=0)
DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE = (datetime.now() + timedelta(hours=2)).replace(microsecond=0)
EXPIRED_REFRESH_TOKEN_EXPIRATION_DATE = (datetime.now() - timedelta(hours=2)).replace(microsecond=0)


@pytest.mark.parametrize("indexes_to_remove, expected_indexes",
    [
        pytest.param(
            DEPRECATED_INDEXES,
            INDEXES,
        )
    ]
)
@pytest.mark.parametrize("init_database", [{"initialize": False}], indirect=True)
@pytest.mark.asyncio
async def test_initialize(init_database, indexes_to_remove: list, expected_indexes: list):
    """ test_initialize checks the collection creation and the management of indexes (remove/create)
    """
    collection_name = Collections.tokens.name
    db_fixture = init_database

    if indexes_to_remove:
        await db_fixture.db.create_collection(collection_name)
        await db_fixture.db[collection_name].create_indexes(indexes_to_remove)

    await db_fixture.collection_tokens.initialize()

    db_names = await db_fixture.db.list_collection_names()
    assert collection_name in db_names
    son_indexes = await (await db_fixture.db[collection_name].list_indexes()).to_list()
    current_indexes = son_to_indexmodels(son_indexes)
    assert compare_indexmodels_unordered(current_indexes, expected_indexes)


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou",
                    "version": 0, # to test unique index on token + version
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "context, token", [
        pytest.param(
            does_not_raise(),
            Token(
                token="token",
                refresh_token="refresh_token",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="fake_user_id",
                version=0
            ),
            id="basic token"
        ),
        pytest.param(
            does_not_raise(),
            Token(
                token="token",
                refresh_token="refresh_token",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="fake_user_id",
                user_ip="user_ip",
                session_index="session_index",
                nameidentifier="name_identifier",
                idp_name="idp_name",
                version=0
            ),
            id="full token"
        ),
        pytest.param(
            pytest.raises(DuplicateKeyError),
            Token(
                token="token1",
                refresh_token="refresh_token",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="fake_user_id",
                version=0 # to trigger duplicate key error
            ),
            id="duplicated token"
        ),
    ]
)
@pytest.mark.asyncio
async def test_store_token(
    init_database,
    populate_data,
    context,
    token: Token
):
    """ test store_token
    """
    db_fixture = init_database
    _ = populate_data

    with context:
        result = await db_fixture.collection_tokens.store(token)
        assert isinstance(result, pymongo.results.InsertOneResult)
        result = await db_fixture.collection_tokens.collection.find_one(
            {"_id": result.inserted_id},
            projection={"_id": 0}
        )
        assert token.as_dict() == result


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou",
                    "user_ip": "user_ip",
                    "session_index": "session_index",
                    "nameidentifier": "name_identifier",
                    "idp_name": "idp_name"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "access_token, expected_token", [
        pytest.param(
            "token",
            None,
            id="no token"
        ),
        pytest.param(
            "token1",
            Token(
                token="token1",
                refresh_token="refresh_token",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="zizou"
            ),
            id="basic token"
        ),
        pytest.param(
            "token2",
            Token(
                token="token2",
                refresh_token="refresh_token",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="zizou",
                user_ip="user_ip",
                session_index="session_index",
                nameidentifier="name_identifier",
                idp_name="idp_name"
            ),
            id="full token"
        ),
    ]
)
@pytest.mark.asyncio
async def test_get_by_access_token(
    init_database,
    populate_data,
    access_token: str,
    expected_token: Token | None
):
    """ test get_by_access_token
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_tokens.get_by_access_token(access_token)
    if expected_token:
        expected_token._id = result._id  # pylint: disable=protected-access
    assert expected_token == result


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                },
                {
                    "token": "token3",
                    "refresh_token": "refresh_token",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "user_id, expected_tokens", [
        pytest.param("zizou", ["token1", "token3"], id="user_id with 2 tokens"),
        pytest.param("didier", ["token2"], id="user_id with 1 tokens"),
        pytest.param("laurent", [], id="user_id with 0 tokens"),
    ]
)
@pytest.mark.asyncio
async def test_get_list_by_user_id(
    init_database,
    populate_data,
    user_id: str,
    expected_tokens: list
):
    """ test list_by_user_id
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_tokens.get_list_by_user_id(user_id)
    assert expected_tokens == [d.token for d in result]


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token1",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token2",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": EXPIRED_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                },
                {
                    "token": "token3",
                    "refresh_token": "refresh_token3",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": EXPIRED_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                },
                {
                    "token": "token4",
                    "refresh_token": "refresh_token3",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "refresh_token, expected_token", [
        pytest.param(
            "refresh_token1",
            Token(
                token="token1",
                refresh_token="refresh_token1",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="zizou"
            ),
            id="refresh token found"
        ),
        pytest.param(
            "refresh_token5",
            None,
            id="refresh token not found"
        ),
        pytest.param(
            "refresh_token2",
            None,
            id="refresh token expired"
        ),
        pytest.param(
            "refresh_token3",
            Token(
                token="token4",
                refresh_token="refresh_token3",
                started_date=DEFAULT_TOKEN_STARTED_DATE,
                expiration_date=DEFAULT_TOKEN_EXPIRATION_DATE,
                refresh_token_expiration_date=DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                user_id="didier"
            ),
            id="2 refresh tokens but only one not expired"
        )
    ]
)
async def test_get_by_refresh_token(
    init_database,
    populate_data,
    refresh_token: str,
    expected_token: Token | None
):
    """ test get_by_refresh_token
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_tokens.get_by_refresh_token(refresh_token)
    if expected_token:
        expected_token._id = result._id  # pylint: disable=protected-access
    assert expected_token == result


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token1",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou",
                    "version": 0,
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token2",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier",
                    "version": 0,
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "context, token, new_token, new_expiration_date, expected_modified_count, raise_on_refresh", [
        # Success: token exists, update works
        pytest.param(
            does_not_raise(),
            "token1",
            "new_token",
            DEFAULT_TOKEN_EXPIRATION_DATE,
            1,
            False,
            id="refresh token succeed"
        ),
        # Token not found: no update
        pytest.param(
            does_not_raise(),
            "token_not_existing",
            "new_token",
            DEFAULT_TOKEN_EXPIRATION_DATE,
            0,
            False,
            id="refresh token failed, token not found"
        ),
        # Conflict: raise DuplicateKeyError
        pytest.param(
            pytest.raises(DuplicateKeyError),
            "token1",
            "token2",  # conflicting new token
            DEFAULT_TOKEN_EXPIRATION_DATE,
            0,
            True,
            id="refresh token failed, conflict"
        ),
    ]
)
@pytest.mark.asyncio
async def test_refresh_token(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    init_database,
    populate_data,
    context,
    token: str,
    new_token: str,
    new_expiration_date: datetime,
    expected_modified_count: int,
    raise_on_refresh: bool
):
    """Test refresh_token with success, missing token, and conflict cases."""
    db_fixture = init_database
    _ = populate_data

    # Patch refresh_token to raise DuplicateKeyError if needed
    if raise_on_refresh:
        async def raise_duplicate(*args, **kwargs):
            """Simulate DuplicateKeyError during refresh_token"""
            raise DuplicateKeyError("Duplicate key conflict")

        db_fixture.collection_tokens.refresh_token = raise_duplicate

    with context:
        # Get the current token
        token_doc = await db_fixture.collection_tokens.get_by_access_token(token)
        current_version = token_doc.version if token_doc else 0

        # Attempt refresh
        result = await db_fixture.collection_tokens.refresh_token(
            token=token,
            new_token=new_token,
            new_expiration_date=new_expiration_date,
            current_version=current_version,
        )

        # Assertions for modified_count only if no exception was raised
        if not raise_on_refresh:
            assert result.modified_count == expected_modified_count

            if result.modified_count > 0:
                updated = await db_fixture.collection_tokens.get_by_access_token(new_token)
                assert updated.expiration_date == new_expiration_date
                assert updated.token == new_token
                assert updated.version == current_version + 1

@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token1",
                    "started_date": DEFAULT_TOKEN_STARTED_DATE,
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "token, user_id, expected_modified_count", [
        pytest.param(
            "token1",
            "gryzou",
            1,
            id="update token succeed"
        ),
        pytest.param(
            "token_unknown",
            "gryzou",
            0,
            id="update token failed, token not found"
        ),
    ]
)
@pytest.mark.asyncio
async def test_update_user_id(
    init_database,
    populate_data,
    token: str,
    user_id: str,
    expected_modified_count: int
):
    """ test update_token
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_tokens.update_user_id(token, user_id)
    assert result.modified_count == expected_modified_count
    if result.modified_count > 0:
        result = await db_fixture.collection_tokens.get_by_access_token(token)
        assert result.user_id == user_id


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                },
                {
                    "token": "token3",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "access_token, expected_deleted_count", [
        pytest.param(
            "token2",
            1,
            id="remove token succeed, token found"
        ),
        pytest.param(
            "token_unknown",
            0,
            id="remove token failed, token not found"
        )
    ]
)
@pytest.mark.asyncio
async def test_remove_by_access_token(
    init_database,
    populate_data,
    access_token: str | None,
    expected_deleted_count: int
):
    """test remove_by_access_token
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_tokens.remove_by_access_token(access_token)
    assert result.deleted_count == expected_deleted_count


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                },
                {
                    "token": "token3",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.parametrize(
    "user_id, expected_deleted_count", [
        pytest.param(
            "zizou",
            2,
            id="remove token succeed, user_id found"
        ),
        pytest.param(
            "fabien",
            0,
            id="remove token failed, user_id not found"
        ),
    ]
)
@pytest.mark.asyncio
async def test_remove_token(
    init_database,
    populate_data,
    user_id: str | None,
    expected_deleted_count: int
):
    """test remove_token
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_tokens.remove_by_user_id(user_id)
    assert result.deleted_count == expected_deleted_count


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.tokens.name: [
                {
                    "token": "token1",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": EXPIRED_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                },
                {
                    "token": "token2",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": DEFAULT_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "didier"
                },
                {
                    "token": "token3",
                    "refresh_token": "refresh_token",
                    "expiration_date": DEFAULT_TOKEN_EXPIRATION_DATE,
                    "refresh_token_expiration_date": EXPIRED_REFRESH_TOKEN_EXPIRATION_DATE,
                    "user_id": "zizou"
                }
            ]
        }
    ], indirect=True
)
@pytest.mark.asyncio
async def test_clean_expired_refresh_token(init_database, populate_data):
    """ test clean_expired_refresh_token
    """
    db_fixture = init_database
    _ = populate_data

    await db_fixture.collection_tokens.clean_expired_refresh_token()
    remaining_tokens = await db_fixture.collection_tokens.collection.find().to_list(None)
    assert len(remaining_tokens) == 1
