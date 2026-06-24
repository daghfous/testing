""" test_collection_api_descriptors.py
"""

import pytest

from ateme.um_backend.dao.collections import Collections
from ateme.um_backend.dao.collection_api_descriptors import (
    DEPRECATED_INDEXES,
    INDEXES,
    ApiDescriptor
)

from .index_utils import son_to_indexmodels, compare_indexmodels_unordered
from ..utils import (
    PMF_API_DESCRIPTOR,
    SM_API_DESCRIPTOR
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
    collection_name = Collections.api_descriptors.name
    db_fixture = init_database

    if indexes_to_remove:
        await db_fixture.db.create_collection(collection_name)
        await db_fixture.db[collection_name].create_indexes(indexes_to_remove)

    await db_fixture.collection_api_descriptors.initialize()

    db_names = await db_fixture.db.list_collection_names()
    assert collection_name in db_names
    son_indexes = await (await db_fixture.db[collection_name].list_indexes()).to_list()
    current_indexes = son_to_indexmodels(son_indexes)
    assert compare_indexmodels_unordered(current_indexes, expected_indexes)



@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.api_descriptors.name: [
                PMF_API_DESCRIPTOR.to_dict(),
                SM_API_DESCRIPTOR.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "api_descriptor, expected_count",
    [
        pytest.param(
            PMF_API_DESCRIPTOR,
            2,
            id="replace existing api_descriptor",
        ),
        pytest.param(
            ApiDescriptor(
                app_name="new_app",
                prefix="new_prefix",
                url="http://new-url.cluster",
            ),
            3,
            id="new api_descriptor",
        )
    ]
)
@pytest.mark.asyncio
async def test_replace_api_descriptor(
    init_database, populate_data, api_descriptor, expected_count
):
    """ test replace_api_descriptor
    :param api_descriptors:
    :param count:
    """
    db_fixture = init_database
    _ = populate_data

    data = await db_fixture.collection_api_descriptors.replace(api_descriptor)
    assert data.upserted_id
    data = await db_fixture.collection_api_descriptors.collection.find({}).to_list(None)
    assert len(data) == expected_count


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.api_descriptors.name: [
                PMF_API_DESCRIPTOR.to_dict(),
                SM_API_DESCRIPTOR.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_get_list(
    init_database, populate_data
):
    """ test get_list
    """
    db_fixture = init_database
    _ = populate_data

    data = await db_fixture.collection_api_descriptors.get_list()
    assert len(data) == 2


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.api_descriptors.name: [
                PMF_API_DESCRIPTOR.to_dict(),
                SM_API_DESCRIPTOR.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_api_descriptor", [
        pytest.param(
            {"prefix": PMF_API_DESCRIPTOR.prefix},
            PMF_API_DESCRIPTOR,
            id="prefix only",
        ),
        pytest.param(
            {"prefix": SM_API_DESCRIPTOR.prefix, "app_name": SM_API_DESCRIPTOR.app_name},
            SM_API_DESCRIPTOR,
            id="prefix and app_name",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_by_prefix_app_name(
    init_database, populate_data, input_args, expected_api_descriptor
):
    """ test get_by_prefix_app_name
    """
    db_fixture = init_database
    _ = populate_data

    data = await db_fixture.collection_api_descriptors.get_by_prefix_app_name(**input_args)
    assert data.to_dict() == expected_api_descriptor.to_dict()


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.api_descriptors.name: [
                PMF_API_DESCRIPTOR.to_dict(),
                SM_API_DESCRIPTOR.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_api_descriptor", [
        pytest.param(
            {"url": PMF_API_DESCRIPTOR.url},
            PMF_API_DESCRIPTOR,
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_by_url(init_database, populate_data, input_args, expected_api_descriptor):
    """

    test get_by_url
    :param api_descriptor:
    """
    db_fixture = init_database
    _ = populate_data

    data = await db_fixture.collection_api_descriptors.get_by_url(**input_args)
    assert data.to_dict() == expected_api_descriptor.to_dict()


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.api_descriptors.name: [
                PMF_API_DESCRIPTOR.to_dict(),
                SM_API_DESCRIPTOR.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_deleted_count", [
        pytest.param(
            {"prefix": PMF_API_DESCRIPTOR.prefix},
            1,
            id="prefix only",
        ),
        pytest.param(
            {"prefix": SM_API_DESCRIPTOR.prefix, "app_name": SM_API_DESCRIPTOR.app_name},
            1,
            id="prefix and app_name",
        ),
    ],
)
@pytest.mark.asyncio
async def test_remove_by_prefix_app_name(
    init_database, populate_data, input_args, expected_deleted_count
):
    """ test remove_by_prefix_app_name
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_api_descriptors.remove_by_prefix_app_name(**input_args)
    assert result.deleted_count == expected_deleted_count
