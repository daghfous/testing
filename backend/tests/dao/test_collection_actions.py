""" test_collection_actions.py """

import pytest
from pymongo.errors import BulkWriteError

from ateme.um_backend.types import (
    Action,
    Request,
    RequestMethod
)
from ateme.um_backend.dao.collections import Collections
from ateme.um_backend.dao.collection_actions import (
    DEPRECATED_INDEXES,
    INDEXES
)

from .index_utils import son_to_indexmodels, compare_indexmodels_unordered

from ..utils import (
    ACTION,
)


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
    collection_name = Collections.actions.name
    db_fixture = init_database

    if indexes_to_remove:
        await db_fixture.db.create_collection(collection_name)
        await db_fixture.db[collection_name].create_indexes(indexes_to_remove)

    await db_fixture.collection_actions.initialize()

    db_names = await db_fixture.db.list_collection_names()
    assert collection_name in db_names
    son_indexes = await (await db_fixture.db[collection_name].list_indexes()).to_list()
    current_indexes = son_to_indexmodels(son_indexes)
    assert compare_indexmodels_unordered(current_indexes, expected_indexes)


@pytest.mark.asyncio
async def test_store(init_database):
    """

    :return:
    """
    db_fixture = init_database
    res = await db_fixture.collection_actions.store(ACTION)
    assert res.acknowledged
    assert res.inserted_id


@pytest.mark.parametrize(
    "populate_data, input_args, expected_actions_in_db",
    [
        pytest.param(
            {
                Collections.actions.name: [
                    Action(
                        prefix="prefix",
                        name="get_ping_a",
                        request=Request(method=RequestMethod.GET, route="/ping"),
                    ).to_dict(),
                    Action(
                        prefix="prefix",
                        name="get_ping_b",
                        request=Request(method=RequestMethod.GET, route="/ping"),
                    ).to_dict(),
                ]
            },
            {
                "actions": [
                    Action(
                        prefix="prefix",
                        name="get_ping_c",
                        request=Request(method=RequestMethod.GET, route="/ping"),
                    ),
                ],
                "prefix": "prefix"
            },
            [
                Action(
                    prefix="prefix",
                    name="get_ping_c",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict()
            ],
            id="remove by prefix"
        ),
        pytest.param(
            {
                Collections.actions.name: [
                    Action(
                        prefix="appa:prefix",
                        name="get_ping_a",
                        request=Request(method=RequestMethod.GET, route="/ping"),
                    ).to_dict(),
                    Action(
                        prefix="appb:prefix",
                        name="get_ping_b",
                        request=Request(method=RequestMethod.GET, route="/ping"),
                    ).to_dict(),
                ]
            },
            {
                "actions": [
                    Action(
                        prefix="prefix",
                        name="get_ping_c",
                        request=Request(method=RequestMethod.GET, route="/ping"),
                    ),
                ],
                "prefix": "prefix",
                "app_name": "appa"
            },
            [
                Action(
                    prefix="appb:prefix",
                    name="get_ping_b",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
                Action(
                    prefix="prefix",
                    name="get_ping_c",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict()
            ],
            id="remove by prefix and appm"
        ),
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_replace_many(init_database, populate_data, input_args, expected_actions_in_db: list[dict]):
    """ test_replace_many
    """
    _ = populate_data
    collection_name = Collections.actions.name
    db_fixture = init_database

    await db_fixture.collection_actions.replace_many(**input_args)

    result = await db_fixture.db[collection_name].find(
        filter={},
        projection={"_id": 0}
        ).to_list(None)
    assert expected_actions_in_db == result


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.actions.name: [
                Action(
                    prefix="prefix",
                    name="get_ping_a",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
                Action(
                    prefix="prefix",
                    name="get_ping_b",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
            ]
        },
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_actions",
    [
        pytest.param(
            {
                "filters": {}
            },
            [
                Action(
                    prefix="prefix",
                    name="get_ping_a",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ),
                Action(
                    prefix="prefix",
                    name="get_ping_b",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ),
            ],
            id="no filter"
        ),
        pytest.param(
            {
                "filters": {
                    "prefix": {"$regex": "pre"}
                }
            },
            [
                Action(
                    prefix="prefix",
                    name="get_ping_a",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ),
                Action(
                    prefix="prefix",
                    name="get_ping_b",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ),
            ],
            id="with filter"
        )
    ]
)
@pytest.mark.asyncio
async def test_get_list(init_database, populate_data, input_args, expected_actions: list[Action]):
    """ test_get_list
    """
    _ = populate_data
    db_fixture = init_database

    result = await db_fixture.collection_actions.get_list(**input_args)
    assert [action.to_dict() for action in result] == [action.to_dict() for action in expected_actions]


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.actions.name: [
                Action(
                    prefix="usr",
                    name="get_documentation",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
                Action(
                    prefix="prefix",
                    name="get_ping_old",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args", [
        {
            "actions": [
                Action(
                    description="fake description",
                    label="fake label",
                    prefix="prefix",
                    name="get_ping_new",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ),
                Action(
                    description="fake description",
                    label="fake label",
                    prefix="usr",
                    name="get_ping",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                )
            ]
        }
    ]
)
@pytest.mark.parametrize(
    "mocks, expected_result, expected_actions_in_db",
    [
        pytest.param(
            {},
            True,
            [
                Action(
                    prefix="usr",
                    name="get_documentation",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
                Action(
                    description="fake description",
                    label="fake label",
                    prefix="prefix",
                    name="get_ping_new",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
                Action(
                    description="fake description",
                    label="fake label",
                    prefix="usr",
                    name="get_ping",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict()
            ],
            id="no error"
        ),
        pytest.param(
            {
                "delete_many": Exception("fake error")
            },
            False,
            [],
            id="delete_many error"
        ),
        pytest.param(
            {
                "insert_many": BulkWriteError(
                    {"writeErrors": [{"index": 0, "code": 11000, "errmsg": "duplicate key", "keyValue": "fake_key"}]}
                )
            },
            False,
            [],
            id="insert_many error"
        )
    ]
)
@pytest.mark.asyncio
async def test_replace_defaults(
    mocker,
    init_database,
    populate_data,
    input_args,
    mocks,
    expected_result,
    expected_actions_in_db: list[dict]
):
    """ test_replace_defaults
    """
    _ = populate_data
    collection_name = Collections.actions.name
    db_fixture = init_database

    for func_name, side_effect in mocks.items():
        mock_coll = mocker.AsyncMock()
        method_mock = mocker.AsyncMock()
        method_mock.side_effect = side_effect
        setattr(mock_coll, func_name, method_mock)
        mocker.patch.object(
            type(db_fixture.collection_actions),
            "collection",
            new_callable=mocker.PropertyMock,
            return_value=mock_coll
        )

    result, _ = await db_fixture.collection_actions.replace_defaults(**input_args)
    assert result == expected_result

    if expected_result:
        result = await db_fixture.db[collection_name].find(
            filter={},
            projection={"_id": 0}
            ).to_list(None)
        assert expected_actions_in_db == result


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.actions.name: [
                Action(
                    prefix="prefix",
                    name="get_ping_a",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
                Action(
                    prefix="prefix",
                    name="get_ping_b",
                    request=Request(method=RequestMethod.GET, route="/ping"),
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_filters, expected_deleted_count", [
        pytest.param(
            {
                "prefix": "prefix"
            },
            2,
            id="delete by prefix"
        ),
        pytest.param(
            {
                "name": "get_ping_a"
            },
            1,
            id="delete by name"
        ),
    ]
)
@pytest.mark.asyncio
async def test_delete_many(init_database, populate_data, input_filters, expected_deleted_count):
    """ test_delete_many
    """
    db_fixture = init_database
    _ = populate_data

    # Delete data
    delete_result = await db_fixture.collection_actions.delete_many(input_filters)
    assert delete_result.acknowledged
    assert delete_result.deleted_count == expected_deleted_count
