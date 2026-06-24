""" test_collection_clients.py """

from contextlib import nullcontext as does_not_raise
from datetime import timedelta
import copy
import pytest

from ateme.um_backend.dao.collections import Collections
from ateme.um_backend.dao.collection_clients import (
    DEPRECATED_INDEXES,
    INDEXES,
    utcnow,
    DeleteClientError
)

from .index_utils import son_to_indexmodels, compare_indexmodels_unordered


DEFAULT_CLIENTS = [
    {
        "remote": "france",
        "username": "dembele",
        "idp_name": "psg",
        "attempts": 1,
        "last_attempt_date": (utcnow() - timedelta(seconds=100)).timestamp(),
        "enabled": True
    },
    {
        "remote": "spain",
        "username": "yamal",
        "idp_name": "fcb",
        "attempts": 3,
        "last_attempt_date": (utcnow() - timedelta(seconds=100)).timestamp(),
        "enabled": False
    },
    {
        "remote": "brazil",
        "username": "raphinha",
        "idp_name": "fcb",
        "attempts": 2,
        "last_attempt_date": (utcnow() - timedelta(seconds=100)).timestamp(),
        "enabled": False
    },
    {
        "remote": "germany",
        "username": "wirtz",
        "idp_name": "lfc",
        "attempts": 2,
        "last_attempt_date": (utcnow() - timedelta(seconds=100)).timestamp(),
        "enabled": False
    },
    {
        "remote": "england",
        "username": "rice",
        "idp_name": "afc",
        "attempts": 2,
        "last_attempt_date": (utcnow() - timedelta(seconds=800)).timestamp(),
        "enabled": False
    },
    {
        "remote": "france",
        "username": "giroud",
        "idp_name": "losc",
        "attempts": 1,
        "last_attempt_date": (utcnow() - timedelta(seconds=800)).timestamp(),
        "enabled": True
    }
]


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
async def test_initialize(
    init_database,
    indexes_to_remove: list,
    expected_indexes: list
):
    """ test_initialize checks the collection creation and the management of indexes (remove/create)
    """
    collection_name = Collections.clients.name
    db_fixture = init_database

    if indexes_to_remove:
        await db_fixture.db.create_collection(collection_name)
        await db_fixture.db[collection_name].create_indexes(indexes_to_remove)

    await db_fixture.collection_clients.initialize()

    db_names = await db_fixture.db.list_collection_names()
    assert collection_name in db_names
    son_indexes = await (await db_fixture.db[collection_name].list_indexes()).to_list()
    current_indexes = son_to_indexmodels(son_indexes)
    assert compare_indexmodels_unordered(current_indexes, expected_indexes)


@pytest.mark.parametrize(
    "populate_data, remote, username, idp_name, expected_client_idx", [
        pytest.param(
            {Collections.clients.name: copy.deepcopy(DEFAULT_CLIENTS[:2])},
            "france", "dembele", "psg",
            0,
            id="found client idx=0"
        ),
        pytest.param(
            {Collections.clients.name: copy.deepcopy(DEFAULT_CLIENTS[:2])},
            "spain", "yamal", "fcb",
            1,
            id="found client idx=1"
        ),
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS[:2]},
            "spain", "dembele", "fcb",
            None,
            id="client not found, incoherent arguments"
        ),
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS[:2]},
            "england", "rice", "afc",
            None,
            id="client not existing"
        ),
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_get(
    init_database,
    populate_data,
    remote: str,
    username: str,
    idp_name: str,
    expected_client_idx: int | None
):
    """ test_get
    """
    db_fixture = init_database
    _ = populate_data

    client = await db_fixture.collection_clients.get(
        remote=remote,
        username=username,
        idp_name=idp_name
    )
    if expected_client_idx is None:
        assert client is None
    else:
        assert client.to_dict() == DEFAULT_CLIENTS[expected_client_idx]


@pytest.mark.parametrize(
    "attempts, max_successive_failed_login, user_deactivation_period", [
        pytest.param(
            2, 3, 600,
            id="successive failed login not reached and deactivation period enabled, client not blocked"
        ),
        pytest.param(
            3, 3, 600,
            id="successive failed login reached and deactivation period enabled, client blocked"
        ),
        pytest.param(
            4, 3, 600,
            id="successive failed login exceeded and deactivation period enabled, client blocked"
        ),
        pytest.param(
            4, 3, -1,
            id="successive failed login exceeded and deactivation period disabled, client not blocked"
        ),
    ],
)
@pytest.mark.asyncio
async def test_update(
    init_database,
    attempts: int,
    max_successive_failed_login: int,
    user_deactivation_period: int,
):
    """ test_update
    """
    remote = "france"
    username = "dembele"
    idp_name = "psg"

    db_fixture = init_database

    expected_client_enabled = attempts < max_successive_failed_login
    if user_deactivation_period == -1:
        expected_client_enabled = True

    for i in range(1, attempts + 1):
        client = await db_fixture.collection_clients.update(
            remote=remote,
            username=username,
            idp_name=idp_name,
            max_successive_failed_login=max_successive_failed_login,
            user_deactivation_period=user_deactivation_period,
        )
        assert client.remote == remote
        assert client.username == username
        assert client.idp_name == idp_name
        assert client.attempts == i

    # Check enabled flag
    assert client.enabled == expected_client_enabled


@pytest.mark.parametrize(
    "populate_data, input_args, context, expected_result", [
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS},
            {"username": "dembele"},
            pytest.raises(DeleteClientError, match="idp_name must be set if username is set"),
            0,
            id="delete client error, missing idp_name argument"
        ),
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS},
            {"username": "dembele", "idp_name": "psg"},
            does_not_raise(),
            1,
            id="delete one client"
        ),
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS},
            {"remote": "france"},
            does_not_raise(),
            2,
            id="delete many clients using remote argument"
        ),
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS},
            {"user_deactivation_period": 600},
            does_not_raise(),
            2,
            id="delete many clients using user_deactivation_period argument"
        ),
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS},
            {},
            does_not_raise(),
            None,
            id="empty arguments, no deletion"
        ),
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_delete_many(
    init_database,
    populate_data,
    input_args: dict,
    context,
    expected_result: int | None
):
    """ test_delete_client
    """
    db_fixture = init_database
    _ = populate_data
    with context:
        result = await db_fixture.collection_clients.delete_many(**input_args)
        if expected_result:
            assert expected_result == result.deleted_count
        else:
            assert result is None


@pytest.mark.parametrize(
    "populate_data, expected_result", [
        pytest.param(
            {Collections.clients.name: DEFAULT_CLIENTS},
            11
        ),
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_get_login_attempts_number(
    init_database,
    populate_data,
    expected_result: int
):
    """ test_get_login_attempts_number
    """
    db_fixture = init_database
    _ = populate_data
    result = await db_fixture.collection_clients.get_login_attempts_number()
    assert result == expected_result
