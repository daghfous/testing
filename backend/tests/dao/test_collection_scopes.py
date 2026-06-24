""" test_collection_scopes.py
"""

# pylint: disable=no-member,protected-access

import os
import copy
import json
import pytest

from ateme.um_backend.types import (
    DefaultScopes,
    Scope,
    ScopeFilterMode,
    ScopeFilter,
    ScopeIdSortOrder
)
from ateme.um_backend.dao.collections import Collections
from ateme.um_backend.dao.collection_scopes import (
    DEPRECATED_INDEXES,
    INDEXES,
)

from .index_utils import son_to_indexmodels, compare_indexmodels_unordered
from ..utils import (
    PMF_DEFAULT_BASIC_SCOPE_0,
    APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
    APP_SM_DEFAULT_BASIC_SCOPE_2,
    APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
    USR_DEFAULT_BASIC_SCOPE_4,
    OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
    NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6,
    INTERNAL_ADMIN_SCOPE
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
    collection_name = Collections.scopes.name
    db_fixture = init_database

    if indexes_to_remove:
        await db_fixture.db.create_collection(collection_name)
        await db_fixture.db[collection_name].create_indexes(indexes_to_remove)

    await db_fixture.collection_scopes.initialize()

    db_names = await db_fixture.db.list_collection_names()
    assert collection_name in db_names
    son_indexes = await (await db_fixture.db[collection_name].list_indexes()).to_list()
    current_indexes = son_to_indexmodels(son_indexes)
    assert compare_indexmodels_unordered(current_indexes, expected_indexes)


@pytest.mark.asyncio
async def test_store(init_database):
    """ test_store
    """
    db_fixture = init_database

    res = await db_fixture.collection_scopes.store(NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6)
    assert res.inserted_id
    # retry again to check duplicate handling
    res = await db_fixture.collection_scopes.store(NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6)
    assert res is None
    res = await db_fixture.collection_scopes.store(INTERNAL_ADMIN_SCOPE)
    assert res.inserted_id


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                # internal
                INTERNAL_ADMIN_SCOPE.to_dict(),
                # non internal
                PMF_DEFAULT_BASIC_SCOPE_0.to_dict(),
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1.to_dict(),
                APP_SM_DEFAULT_BASIC_SCOPE_2.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "filter_args, expected_scopes_len", [
        pytest.param(
            {},
            3,
            id="default filter, only non-internal scopes",
        ),
        pytest.param(
            {"internal": True,},
            1,
            id="internal true, only internal scopes",
        ),
    ]
)
@pytest.mark.asyncio
async def test_get_list(init_database, populate_data, filter_args, expected_scopes_len):
    """ test_get_list
    """
    db_fixture = init_database
    _ = populate_data

    scope_filter = ScopeFilter(**filter_args)
    scopes = await db_fixture.collection_scopes.get_list(scope_filter=scope_filter)
    assert len(scopes) == expected_scopes_len


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                # internal
                INTERNAL_ADMIN_SCOPE.to_dict(),
                # non internal
                PMF_DEFAULT_BASIC_SCOPE_0.to_dict(),
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1.to_dict(),
                APP_SM_DEFAULT_BASIC_SCOPE_2.to_dict(),
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3.to_dict(),
                USR_DEFAULT_BASIC_SCOPE_4.to_dict(),
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5.to_dict(),
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.to_dict()
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "filter_args,"
    "id_sort, skip, limit,"
    "expected_total, expected_start,"
    "expected_scopes",
    [
        pytest.param(
            {},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            7, 0,
            [
                PMF_DEFAULT_BASIC_SCOPE_0,
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                USR_DEFAULT_BASIC_SCOPE_4,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="default-params-all"
        ),
        pytest.param(
            {"internal": True,},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            1, 0,
            [INTERNAL_ADMIN_SCOPE],
            id="internal-true"
        ),
        pytest.param(
            {
                "pmf_release_name": "pmf",
                "mode": ScopeFilterMode.BASIC
            },
            ScopeIdSortOrder.ASCENDING, 0, 0,
            6, 0,
            [
                PMF_DEFAULT_BASIC_SCOPE_0,
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                USR_DEFAULT_BASIC_SCOPE_4,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="basic-with-existent-pmf-release-name"
        ),
        pytest.param(
            {
                "pmf_release_name": "non existent",
                "mode": ScopeFilterMode.BASIC
            },
            ScopeIdSortOrder.ASCENDING, 0, 0,
            5, 0,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                USR_DEFAULT_BASIC_SCOPE_4,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="basic-with-non-existent-pmf-release-name"
        ),
        pytest.param(
            {},
            ScopeIdSortOrder.DESCENDING, 0, 0,
            7, 0,
            [
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                USR_DEFAULT_BASIC_SCOPE_4,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                PMF_DEFAULT_BASIC_SCOPE_0
            ],
            id="id-sort-desc-all"
        ),
        pytest.param(
            {"app_name": "sm"},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            3, 0,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3
            ],
            id="app-name-sm"
        ),
        pytest.param(
            {"app_name": "non-existent"},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            0, 0,
            [],
            id="app-name-non-existent"
        ),
        pytest.param(
            {"scope_type": "administrator"},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            3, 0,
            [
                PMF_DEFAULT_BASIC_SCOPE_0,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                USR_DEFAULT_BASIC_SCOPE_4
            ],
            id="scope-type-administrator"
        ),
        pytest.param(
            {"scope_type": "guest"},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            1, 0,
            [APP_SM_DEFAULT_BASIC_SCOPE_2],
            id="scope-type-guest"
        ),
        pytest.param(
            {"label": "non_basic"},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            4, 0,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="label-filter"
        ),
        pytest.param(
            {"default": True},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            4, 0,
            [
                PMF_DEFAULT_BASIC_SCOPE_0,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                USR_DEFAULT_BASIC_SCOPE_4
            ],
            id="default-only-true"
        ),
        pytest.param(
            {"default": False},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            3, 0,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="default-only-false"
        ),
        pytest.param(
            {
                "pmf_release_name": "pmf",
                "default": True,
                "mode": ScopeFilterMode.BASIC,
                "scope_type": "guest",
                "app_name": "sm",
                "label": "scope_2",
            },
            ScopeIdSortOrder.DESCENDING, 0, 0,
            1, 0,
            [APP_SM_DEFAULT_BASIC_SCOPE_2],
            id="default-basic-guest-for-sm-with-label-scope_2"
        ),
        pytest.param(
            {
                "pmf_release_name": "pmf",
                "default": True,
                "mode": ScopeFilterMode.BASIC,
                "scope_type": "guest",
                "app_name": "sm",
                "label": "non existent",
            },
            ScopeIdSortOrder.DESCENDING, 0, 0,
            0, 0,
            [],
            id="default-basic-guest-for-sm-with-non-existent-label"
        ),
        pytest.param(
            {},
            ScopeIdSortOrder.ASCENDING, 1, 5,
            7,1,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                USR_DEFAULT_BASIC_SCOPE_4,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5
            ],
            id="pagination-1-5"
        ),
        pytest.param(
            {},
            ScopeIdSortOrder.ASCENDING, 1, 10,
            7, 1,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                APP_SM_DEFAULT_NON_BASIC_SCOPE_3,
                USR_DEFAULT_BASIC_SCOPE_4,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="pagination-1-exceeding-end"
        ),
        pytest.param(
            {},
            ScopeIdSortOrder.ASCENDING, 10, 11,
            7, 10,
            [],
            id="pagination-exceeding-start-end"
        ),
        pytest.param(
            {
                "mode": ScopeFilterMode.BASIC,
                "pmf_release_name": "pmf"
            },
            ScopeIdSortOrder.ASCENDING, 0, 0,
            6, 0,
            [
                PMF_DEFAULT_BASIC_SCOPE_0,
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                APP_SM_DEFAULT_BASIC_SCOPE_2,
                USR_DEFAULT_BASIC_SCOPE_4,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="basic-pmf-release"
        ),
        pytest.param(
            {"pmf_release_name": "pmf", "default": False},
            ScopeIdSortOrder.ASCENDING, 0, 0,
            3, 0,
            [
                APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1,
                OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5,
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6
            ],
            id="pmf-release-non-default"
        )
    ]
)
@pytest.mark.asyncio
async def test_get_list_paginated(
    init_database,
    populate_data,
    filter_args,
    id_sort, skip, limit,
    expected_total, expected_start,
    expected_scopes
):
    """
    Test get_scopes with various filtering and sorting parameters.
    """
    # pylint: disable=too-many-arguments,too-many-locals,too-many-positional-arguments
    _ = populate_data
    db_fixture = init_database

    # internal scopes are not returned (ex: internal_administrator)
    # as well as old ones
    scope_filter = ScopeFilter(**filter_args)
    scopes_paginated_response = await db_fixture.collection_scopes.get_list_paginated(
        scope_filter=scope_filter,
        id_sort=id_sort,
        skip=skip,
        limit=limit
    )

    actual_scopes = scopes_paginated_response.scopes
    assert isinstance(actual_scopes, list), "scopes should be a list"
    if expected_scopes:
        actual_scope_ids = [s.id for s in actual_scopes]
        expected_scope_ids = [s.id for s in expected_scopes]
        assert actual_scope_ids == expected_scope_ids, f"scopes should be {expected_scope_ids} not {actual_scope_ids}"
    else:
        assert actual_scopes == [], "scopes should be empty list"
    assert scopes_paginated_response.start == expected_start, f"start should be equal to expected_start {expected_start}"
    assert scopes_paginated_response.total == expected_total, f"total should be equal to expected_total {expected_total}"


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                Scope(
                    id="test:default_scope",
                    label="default scope",
                    version=3,
                    content=[
                        {"action": "test:fake_action", "policy": "allow", "resource": {}},
                    ],
                    default=True,
                ).to_dict(),
                Scope(
                    id="test:non_default_scope",
                    label="non default scope",
                    version=3,
                    content=[
                        {"action": "test:fake_action", "policy": "allow", "resource": {}}
                    ],
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "expected_ids", [
        pytest.param(
            ["test:non_default_scope"],
        ),
    ]
)
@pytest.mark.asyncio
async def test_get_list_non_default_ids(
    init_database, populate_data, expected_ids: list[str]
):
    """ test_get_list_non_default_ids
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_scopes.get_list_non_default_ids()
    assert result == expected_ids


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.to_dict(),
                INTERNAL_ADMIN_SCOPE.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_get_by_id(init_database, populate_data):
    """ test_get_by_id
    """
    db_fixture = init_database
    _ = populate_data

    scope = await db_fixture.collection_scopes.get_by_id(NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id)
    assert scope, "scope return should be defined"
    assert Scope.from_dict(scope).to_dict() == NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.to_dict()

    scope = await db_fixture.collection_scopes.get_by_id(INTERNAL_ADMIN_SCOPE.id, internal=False)
    assert (
        not scope
    ), "internal scope should not be returned by default i.e.when internal == False"

    scope = await db_fixture.collection_scopes.get_by_id(INTERNAL_ADMIN_SCOPE.id, internal=True)
    assert scope, "internal scope return should be defined"
    assert Scope.from_dict(scope).id == INTERNAL_ADMIN_SCOPE.id


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.to_dict(),
                INTERNAL_ADMIN_SCOPE.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_update_by_id(init_database, populate_data):
    """ test_update_by_id
    """
    db_fixture = init_database
    _ = populate_data

    new_default_scope = Scope.from_dict(
        copy.deepcopy(NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.to_dict())
    )
    new_default_scope.content = []

    new_internal_scope = Scope.from_dict(
        copy.deepcopy(INTERNAL_ADMIN_SCOPE.to_dict())
    )
    new_internal_scope.content = []

    # update non-internal scope
    res = await db_fixture.collection_scopes.update_by_id(
        NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id,
        new_default_scope
    )
    assert res.modified_count == 1

    # update internal scope without internal flag set
    res = await db_fixture.collection_scopes.update_by_id(
        INTERNAL_ADMIN_SCOPE.id,
        new_internal_scope
    )
    assert res.modified_count == 0

    # update internal scope with internal flag set
    res = await db_fixture.collection_scopes.update_by_id(
        INTERNAL_ADMIN_SCOPE.id,
        new_internal_scope,
        internal=True
    )
    assert res.modified_count == 1


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.to_dict(),
                INTERNAL_ADMIN_SCOPE.to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.asyncio
async def test_remove_scope_by_id(init_database, populate_data):
    """ test_remove_scope_by_id
    """
    db_fixture = init_database
    _ = populate_data

    # delete non-internal scope
    res = await db_fixture.collection_scopes.remove_by_id(NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id)
    assert res.deleted_count == 1

    # delete internal scope without internal flag set
    res = await db_fixture.collection_scopes.remove_by_id(INTERNAL_ADMIN_SCOPE.id)
    assert res.deleted_count == 0

    # delete internal scope with internal flag set
    res = await db_fixture.collection_scopes.remove_by_id(INTERNAL_ADMIN_SCOPE.id, internal=True)
    assert res.deleted_count == 1


SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3 = Scope(
    id="test:demo:administrator",
    label="Admin test demo level 3",
    version=1,
    content=[],
    default=True,
)
SCOPE_APP_TEST_ADMINISTRATOR_LVL2 = Scope(
    id="test:administrator",
    label="Admin test level 2",
    version=1,
    content=[
        {"scope": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
    ],
    default=True,
)

@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                # internal scopes
                INTERNAL_ADMIN_SCOPE.to_dict(),
                # usr non-internal default scopes
                USR_DEFAULT_BASIC_SCOPE_4.to_dict(),
                # other non-internal default scopes
                SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.to_dict(),
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.to_dict(),
                Scope(
                    id="all:administrator",
                    label="Admin level 1",
                    version=1,
                    content=[
                        {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                        {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                    ],
                    default=True,
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_ids, expected_contents", [
        pytest.param(
            {
                "scopes": [
                    Scope(
                        id="test:operator",
                        label="Admin test level 2",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id="test:guest",
                        label="Guest test level 2",
                        version=1,
                        content=[],
                        default=True,
                    ),
                ],
                "prefix": "test",
            },
            [
                {"id": INTERNAL_ADMIN_SCOPE.id},
                {"id": USR_DEFAULT_BASIC_SCOPE_4.id},
                {"id": "test:operator"},
                {"id": "test:guest"},
            ],
            {
                "all:administrator": [
                    {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                    {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},    # NOTE: should it be here?
                ],
                "all:operator": [
                    {"scope": "test:operator"},
                ],
                "all:guest": [
                    {"scope": "test:guest"},
                ],
            },
            id="replace scopes by prefix",
        ),
        pytest.param(
            {
                "scopes": [
                    Scope(
                        id="test:prefix:administrator",
                        label="Administrator test prefix level 3",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id="test:prefix:operator",
                        label="Operator test prefix level 3",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id="test:prefix:monitoring",
                        label="Monitoring test prefix level 3",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id=SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id,
                        label="Administrator test level 2",
                        version=1,
                        content=[
                            {"scope": "test:prefix:administrator"},
                        ],
                        default=True,
                    ),
                ],
                "app_name": "test",
                "prefix": "prefix",
            },
            [
                {"id": INTERNAL_ADMIN_SCOPE.id},
                {"id": USR_DEFAULT_BASIC_SCOPE_4.id},
                {"id": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                {"id": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
                {"id": "test:prefix:administrator"},
                {"id": "test:prefix:operator"},
                {"id": "test:prefix:monitoring"}
            ],
            {
                "all:administrator": [
                    {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                    {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                ],
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id: [
                    {"scope": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
                    {"scope": "test:prefix:administrator"},
                ],
            },
            id="scopes, prefix and app_name",
        )
    ]
)
@pytest.mark.asyncio
async def test_replace_many(
    init_database, populate_data, input_args, expected_ids, expected_contents
):
    """ test_replace_many
    """
    db_fixture = init_database
    _ = populate_data

    # NOTE: `all:` scopes will be created when this function is called
    await db_fixture.collection_scopes.replace_many(**input_args)

    # Retrieve the scopes excluding the `all:` scopes
    # Then sort the lists before comparison
    scope_ids = await db_fixture.collection_scopes.collection.find(
        {"id": {"$regex": "^(?!all:).*"}},
        {"_id": 0, "id": 1}
    ).to_list(None)
    scope_ids_sorted = sorted(scope_ids, key=lambda x: x["id"])
    expected_ids_sorted = sorted(expected_ids, key=lambda x: x["id"])
    assert scope_ids_sorted == expected_ids_sorted

    # Verify contents of `all:` scopes
    for scope in DefaultScopes:
        scope_id = f"all:{scope.name}"
        scope_data = await db_fixture.collection_scopes.collection.find_one(
            {"id": scope_id},
            {"_id": 0, "content": 1}
        )
        expected_content = expected_contents.get(scope_id, [])
        assert scope_data["content"] == expected_content

    # Verify contents of app scopes if provided
    for scope_id in expected_contents:
        if not scope_id.startswith("all:"):
            scope_data = await db_fixture.collection_scopes.collection.find_one(
                {"id": scope_id},
                {"_id": 0, "content": 1}
            )
            expected_content = expected_contents.get(scope_id, [])
            assert scope_data["content"] == expected_content


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                # internal scopes
                INTERNAL_ADMIN_SCOPE.to_dict(),
                # usr non-internal default scopes
                USR_DEFAULT_BASIC_SCOPE_4.to_dict(),
                # other non-internal default scopes
                SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.to_dict(),
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.to_dict(),
                Scope(
                    id="all:administrator",
                    label="Admin level 1",
                    version=1,
                    content=[
                        {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                        {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                    ],
                    default=True,
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_inserted, expected_ids, expected_contents", [
        pytest.param(
            {
                "default_scopes": [
                    Scope(
                        id="test:operator",
                        label="Admin test level 2",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id="test:guest",
                        label="Guest test level 2",
                        version=1,
                        content=[],
                        default=True,
                    ),
                ]
            },
            2,
            [
                {"id": INTERNAL_ADMIN_SCOPE.id},
                {"id": USR_DEFAULT_BASIC_SCOPE_4.id},
                {"id": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
                {"id": "test:operator"},
                {"id": "test:guest"},
            ],
            {
                "all:administrator": [
                    {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                    {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},    # NOTE: should it be here?
                ],
                "all:operator": [
                    {"scope": "test:operator"},
                ],
                "all:guest": [
                    {"scope": "test:guest"},
                ],
            },
            id="default scopes",
        ),
        pytest.param(
            {
                "manage_app_scopes": True,
                "default_scopes": [
                    Scope(
                        id="test:prefix:administrator",
                        label="Administrator test prefix level 3",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id="test:prefix:operator",
                        label="Operator test prefix level 3",
                        version=1,
                        content=[],
                        default=True,
                    ),
                    Scope(
                        id="test:prefix:monitoring",
                        label="Monitoring test prefix level 3",
                        version=1,
                        content=[],
                        default=True,
                    )
                ],
            },
            3,
            [
                {"id": INTERNAL_ADMIN_SCOPE.id},
                {"id": USR_DEFAULT_BASIC_SCOPE_4.id},
                {"id": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                {"id": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
                {"id": "test:prefix:administrator"},
                {"id": "test:operator"},
                {"id": "test:prefix:operator"},
                {"id": "test:monitoring"},
                {"id": "test:prefix:monitoring"}
            ],
            {
                "all:administrator": [
                    {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                    {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                ],
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id: [
                    {"scope": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
                    {"scope": "test:prefix:administrator"},
                ],
                "all:operator": [
                    {"scope": "test:operator"},
                ],
                "test:operator": [
                    {"scope": "test:prefix:operator"},
                ],
                "all:monitoring": [
                    {"scope": "test:monitoring"},
                ],
                "test:monitoring": [
                    {"scope": "test:prefix:monitoring"},
                ],
            },
            id="default scopes and manage_app_scopes",
        ),
    ]
)
@pytest.mark.asyncio
async def test_replace_defaults(
    init_database, populate_data, input_args, expected_inserted, expected_ids, expected_contents
):
    """ test_replace_defaults
    """
    db_fixture = init_database
    _ = populate_data

    # NOTE: `all:` and `app` scopes will be created when this function is called
    status, result = await db_fixture.collection_scopes.replace_defaults(**input_args)
    assert status
    assert len(result.inserted_ids) == expected_inserted

    # Retrieve the scopes excluding the `all:` scopes
    # Then sort the lists before comparison
    scope_ids = await db_fixture.collection_scopes.collection.find(
        {"id": {"$regex": "^(?!all:).*"}},
        {"_id": 0, "id": 1}
    ).to_list(None)
    scope_ids_sorted = sorted(scope_ids, key=lambda x: x["id"])
    expected_ids_sorted = sorted(expected_ids, key=lambda x: x["id"])
    assert scope_ids_sorted == expected_ids_sorted

    # Verify contents of `all:` scopes
    for scope in DefaultScopes:
        scope_id = f"all:{scope.name}"
        scope_data = await db_fixture.collection_scopes.collection.find_one(
            {"id": scope_id},
            {"_id": 0, "content": 1}
        )
        expected_content = expected_contents.get(scope_id, [])
        assert scope_data["content"] == expected_content

    # Verify contents of app scopes if provided
    for scope_id in expected_contents:
        if not scope_id.startswith("all:"):
            scope_data = await db_fixture.collection_scopes.collection.find_one(
                {"id": scope_id},
                {"_id": 0, "content": 1}
            )
            expected_content = expected_contents.get(scope_id, [])
            assert scope_data["content"] == expected_content


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                # internal scopes
                INTERNAL_ADMIN_SCOPE.to_dict(),
                # usr non-internal default scopes
                USR_DEFAULT_BASIC_SCOPE_4.to_dict(),
                # other non-internal default scopes
                SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.to_dict(),
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.to_dict(),
                Scope(
                    id="all:administrator",
                    label="Admin level 1",
                    version=1,
                    content=[
                        {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                        {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                    ],
                    default=True,
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args", [
        pytest.param(
            {
                "default_scopes": [
                    USR_DEFAULT_BASIC_SCOPE_4,
                    Scope(
                        id="all:administrator",
                        label="New admin level 1",
                        version=1,
                        content=[
                            {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                        ],
                        default=True,
                    ),
                ]
            },
            id="invalid prefixes"
        ),
        pytest.param(
            {
                "default_scopes": [
                    Scope(
                        id="test:administrator",
                        default=True,
                    ),
                ]
            },
            id="scope validation error"
        )
    ]
)
@pytest.mark.asyncio
async def test_replace_defaults_errors(
    init_database, populate_data, input_args
):
    """ test_replace_defaults
    """
    db_fixture = init_database
    _ = populate_data

    status, result = await db_fixture.collection_scopes.replace_defaults(**input_args)
    assert not status
    assert result is None



@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                # usr non-internal default scopes
                USR_DEFAULT_BASIC_SCOPE_4.to_dict(),
                # other non-internal default scopes
                SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.to_dict(),
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.to_dict(),
                Scope(
                    id="all:administrator",
                    label="Admin level 1",
                    version=1,
                    content=[
                        {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                        {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                    ],
                    default=True,
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "input_args, expected_ids, expected_contents", [
        pytest.param(
            {
                "scopes": [SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3],
                "manage_app_scopes": False,
            },
            [
                {"id": USR_DEFAULT_BASIC_SCOPE_4.id},
                {"id": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
            ],
            {
                "all:administrator": [
                    {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                    {"scope": SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id},
                ],
                SCOPE_APP_TEST_ADMINISTRATOR_LVL2.id: [
                    {"scope": SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3.id},
                ],
            },
            id="clean hat scopes with manage_app_scopes"
        ),
        pytest.param(
            {
                "scopes": [SCOPE_APP_TEST_PREFIX_DEMO_ADMINISTRATOR_LVL3],
                "manage_app_scopes": True,
            },
            [
                {"id": USR_DEFAULT_BASIC_SCOPE_4.id},
            ],
            {
                "all:administrator": [
                    {"scope": USR_DEFAULT_BASIC_SCOPE_4.id},
                ]
            },
        )
    ]
)
@pytest.mark.asyncio
async def test_clean_hat_scopes(
    init_database, populate_data, input_args, expected_ids, expected_contents
):
    """ test_clean_hat_scopes
    """
    db_fixture = init_database
    _ = populate_data

    # Clean hat scopes
    await db_fixture.collection_scopes.clean_hat_scopes(**input_args)

    # Retrieve the scopes excluding the `all:` scopes
    # Then sort the lists before comparison
    scope_ids = await db_fixture.collection_scopes.collection.find(
        {"id": {"$nin": ["all:administrator"]}},
        {"_id": 0, "id": 1}
    ).sort("id", 1).to_list(None)
    scope_ids_sorted = sorted(scope_ids, key=lambda x: x["id"])
    expected_ids_sorted = sorted(expected_ids, key=lambda x: x["id"])
    assert scope_ids_sorted == expected_ids_sorted

    # Verify contents of app scopes if provided
    for scope_id in expected_contents:
        scope_data = await db_fixture.collection_scopes.collection.find_one(
            {"id": scope_id},
            {"_id": 0, "content": 1}
        )
        expected_content = expected_contents.get(scope_id, [])
        assert scope_data["content"] == expected_content


@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                Scope(
                    id="tcln:engineer",
                    content=[
                        {"scope": "tcln:sysm:engineer"},
                        {"scope": "tcln:apm:engineer"},
                    ],
                ).to_dict()
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "scope_ids_to_remove, expected_results, expected_content",
    [
        pytest.param(
            ["tcln:usr:engineer"],
            [None],
            {
                "tcln:engineer": [
                    {"scope": "tcln:sysm:engineer"},
                    {"scope": "tcln:apm:engineer"}
                ]
            },
            id="delete-unknown-scope-lvl3",
        ),
        pytest.param(
            ["tcln:usr:invalid_engineer"],
            [None],
            {
                "tcln:engineer": [
                    {"scope": "tcln:sysm:engineer",},
                    {"scope": "tcln:apm:engineer"}
                ]
            },
            id="delete-invalid-scope-lvl3",
        ),
        pytest.param(
            ["tcln:apm:engineer"],
            [None],
            {
                "tcln:engineer": [
                    {"scope": "tcln:sysm:engineer",},
                ]
            },
            id="delete-sysm-scope-lvl3",
        ),
        pytest.param(
            ["tcln:sysm:engineer"],
            [None],
            {
                "tcln:engineer": [
                    {"scope": "tcln:apm:engineer",},
                ]
            },
            id="delete-apm-scope-lvl3",
        ),
        pytest.param(
            ["tcln:apm:engineer", "tcln:sysm:engineer"],
            [None, "tcln:engineer"],
            {},
            id="delete-all-scope-lvl3",
        ),
    ],
)
@pytest.mark.asyncio
async def test__clean_app_scope(
    init_database,
    populate_data,
    scope_ids_to_remove,
    expected_results,
    expected_content
):
    """
    Test _clean_app_scope: Check if a app is updated when deleting a level3 scope.
    If the app scope content is then empty, the app scope should have been deleted.

    :param app_scope_in_db: The expected id and content of a app scope in db prior to the test execution
    :param scope_id_to_remove: The id of the scope to remove from a app scope
    :param updated_app_scope: The expected id and content of the updated app scope
    :param deleted: app scope deleted
    :param expected_result: The expected result of the _clean_app_scope returned by the method call
    :return:
    """
    db_fixture = init_database
    _ = populate_data

    for i, scope_id in enumerate(scope_ids_to_remove):
        result = await db_fixture.collection_scopes._clean_app_scope(scope_id)
        assert result == expected_results[i]

    for scope_id, scope_content in expected_content.items():
        data = await db_fixture.collection_scopes.get_by_id(scope_id)
        assert data["content"] == scope_content


async def test__compute_hat_scopes_from_app_scopes(init_database):
    """
    Test _compute_hat_scopes_from_app_scopes
    1) Create new hat scopes from a first App and check they are presents
    2) Create new hat scopes from a second App and check first and second app scopes are presents
    in hat scopes content
    """
    db_fixture = init_database
    # 1) Create new hat scopes from a first App and check they are presents
    app_scopes_ids = {"appsysm:administrator", "appsysm:operator"}
    expected_hat_scopes = {
        "all:administrator": [{"scope": "appsysm:administrator"}],
        "all:engineer": [],
        "all:operator": [{"scope": "appsysm:operator"}],
        "all:monitoring": [],
        "all:guest": [],
    }
    hat_scopes_created = db_fixture.collection_scopes._compute_hat_scopes_from_app_scopes(app_scopes_ids)
    assert hat_scopes_created == expected_hat_scopes


@pytest.mark.parametrize(
    "data_file, expected_hat_scopes",
    [
        pytest.param(
            "auth_data_sysm.json",
            {
                "all:administrator": [],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            id="not_appliance_mode_file",
        ),
        pytest.param(
            "auth_data_appmgr_no_app_name.json",
            {
                "all:administrator": [{"scope": "apm:administrator"}],
                "all:engineer": [{"scope": "apm:engineer"}],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            id="appliance_mode_file",
        ),
        pytest.param(
            "apidescriptor.json",
            {
                "all:administrator": [{"scope": "usr:administrator"}],
                "all:engineer": [{"scope": "usr:engineer"}],
                "all:operator": [{"scope": "usr:guest"}, {"scope": "usr:operator"}],
                "all:monitoring": [{"scope": "usr:guest"}],
                "all:guest": [{"scope": "usr:guest"}],
            },
            id="usr_app_file",
        ),
    ],
)
async def test__compute_hat_scopes_from_default_scopes(
    init_database, data_file, expected_hat_scopes
):
    """
    Test _compute_hat_scopes_from_default_scopes
    """
    db_fixture = init_database
    with open(
        os.path.join(os.path.dirname(__file__), "..", "default_data", data_file),
        "r",
        encoding="utf-8",
    ) as file:
        content = json.loads(file.read())
        default_scopes = [Scope.from_dict(scope) for scope in content["scopes"]]
        hat_scopes_created = db_fixture.collection_scopes._compute_hat_scopes_from_default_scopes(default_scopes)
        assert hat_scopes_created == expected_hat_scopes


async def test__update_hat_scopes(init_database):
    """
    Test _update_hat_scopes
    1) Add first scopes
    2) Update with new scopes
    """
    db_fixture = init_database
    # 1) Add first scopes
    first_hat_scopes = {
        "all:administrator": [{"scope": "appapm:administrator"}],
        "all:engineer": [{"scope": "appapm:engineer"}],
        "all:operator": [],
        "all:monitoring": [],
        "all:guest": [],
    }
    await db_fixture.collection_scopes._update_hat_scopes(first_hat_scopes, None)

    # Check the created or updated hat scope in db
    for id_, scope_content in first_hat_scopes.items():
        db_hat_scopes = await db_fixture.collection_scopes.get_by_id(id_)
        assert db_hat_scopes["content"] == scope_content

    # 2) Create new hat scopes from a second App
    second_hat_scopes = {
        "all:administrator": [{"scope": "appsysm:administrator"}],
        "all:engineer": [],
        "all:operator": [{"scope": "appsysm:operator"}],
        "all:monitoring": [],
        "all:guest": [],
    }
    await db_fixture.collection_scopes._update_hat_scopes(second_hat_scopes)

    expected_hat_scopes = {
        "all:administrator": [
            {"scope": "appapm:administrator"},
            {"scope": "appsysm:administrator"},
        ],
        "all:engineer": [{"scope": "appapm:engineer"}],
        "all:operator": [{"scope": "appsysm:operator"}],
        "all:monitoring": [],
        "all:guest": [],
    }

    # Check first and second app scopes are presents
    # in hat scopes content
    for id_, scope_content in expected_hat_scopes.items():
        db_hat_scope = await db_fixture.collection_scopes.get_by_id(id_)
        assert db_hat_scope["content"] == scope_content



@pytest.mark.parametrize(
    "populate_data", [
        {
            Collections.scopes.name: [
                Scope(
                    id="test1:operator",
                    content=[
                        {"action": "test1:change_password", "policy": "allow", "resource": {}},
                        {"action": "test1:logout", "policy": "allow", "resource": {}},
                    ],
                ).to_dict(),
                Scope(
                    id="test2:operator",
                    content=[
                        {"action": "test2:change_password", "policy": "allow", "resource": {}},
                        {"action": "test2:logout", "policy": "allow", "resource": {}},
                    ],
                ).to_dict(),
                Scope(
                    id="test3:administrator",
                    content=[
                        {"scope": "test1:operator"},
                        {"scope": "test2:operator"},
                        {"scope": "unknown:scope"},
                        {"action": "test3:get_ping", "policy": "allow", "resource": {}},
                    ],
                ).to_dict(),
            ]
        }
    ], indirect=["populate_data"]
)
@pytest.mark.parametrize(
    "scope_ids, expected_actions", [
        pytest.param(
            ["test3:administrator"],
            [
                {"action": "test1:change_password", "policy": "allow", "resource": {}},
                {"action": "test1:logout", "policy": "allow", "resource": {}},
                {"action": "test2:change_password", "policy": "allow", "resource": {}},
                {"action": "test2:logout", "policy": "allow", "resource": {}},
                {"action": "test3:get_ping", "policy": "allow", "resource": {}},
            ],
            id="scope-with-nested-scopes",
        ),
        pytest.param(
            ["test1:operator", "test2:operator"],
            [
                {"action": "test1:change_password", "policy": "allow", "resource": {}},
                {"action": "test1:logout", "policy": "allow", "resource": {}},
                {"action": "test2:change_password", "policy": "allow", "resource": {}},
                {"action": "test2:logout", "policy": "allow", "resource": {}},
            ],
            id="several-scope-ids",
        )
    ]
)
@pytest.mark.asyncio
async def test_list_all_actions(
    init_database, populate_data, scope_ids, expected_actions
):
    """

    test list_all_actions db function
    """
    db_fixture = init_database
    _ = populate_data

    result = await db_fixture.collection_scopes.list_all_actions(scope_ids)
    assert result == expected_actions


@pytest.mark.parametrize(
    "app_scope_in_db, scope_id_to_add, expected_app_scope_created, expected_app_scope_after_update",
    [
        pytest.param(
            {"id": "tcln:engineer", "content": []},
            "tcln:apm:invalid_engineer",
            None,
            {"id": "tcln:engineer", "content": []},
            id="invalid-scope-level3",
        ),
        pytest.param(
            {"id": "tcln:engineer", "content": []},
            "tcln:apm:engineer",
            None,
            {"id": "tcln:engineer", "content": [{"scope": "tcln:apm:engineer"}]},
            id="update-empty-app-scope-with-level3",
        ),
        pytest.param(
            {},
            "tcln:apm:engineer",
            "tcln:engineer",
            {"id": "tcln:engineer", "content": [{"scope": "tcln:apm:engineer"}]},
            id="create-app-scope-with-level3",
        ),
        pytest.param(
            {"id": "tcln:engineer", "content": [{"scope": "tcln:sysm:engineer"}]},
            "tcln:apm:engineer",
            None,
            {
                "id": "tcln:engineer",
                "content": [
                    {"scope": "tcln:sysm:engineer"},
                    {"scope": "tcln:apm:engineer"},
                ],
            },
            id="update-app-scope-with-level3",
        )
    ],
)
async def test__update_app_scope(
    init_database,
    app_scope_in_db,
    scope_id_to_add,
    expected_app_scope_created,
    expected_app_scope_after_update,
):
    """
    Test _update_app_scope: Check if a app is created or updated with the right content from a level3 scope

    :param app_scope_in_db: The expected id and content of a app scope in db prior to the test execution
    :param scope_id_to_add: The id of the scope to add in a app scope
    :param expected_app_scope_for_update: The expected id and content of the created or updated app scope
    :param scope_creation: Test scope creation if True, test update if False
    :return:
    """
    db_fixture = init_database

    # Create app scope if necessary
    if app_scope_in_db:
        scope = Scope(
            id=app_scope_in_db["id"],
            label="TLCN",
            content=app_scope_in_db["content"],
            title="TLCN - engineer",
            description="Scope engineer for TLCN",
            default=True,
            internal=False,
        )
        res = await db_fixture.collection_scopes.store(scope)
        assert res.acknowledged and res.inserted_id

    app_scope_created = await db_fixture.collection_scopes._update_app_scope(scope_id_to_add)
    assert app_scope_created == expected_app_scope_created

    if expected_app_scope_created:
        # Check the created app scope in db
        id_parts = scope_id_to_add.split(":")
        app_scope_label = id_parts[0]
        app_scope_name = db_fixture.collection_scopes._extract_app_scope_name(id_parts[-1])
        expected_scope = Scope(
            id=expected_app_scope_after_update["id"],
            label=app_scope_label,
            content=expected_app_scope_after_update["content"],
            title=f"{app_scope_name.capitalize()} - {app_scope_label.lower()}",
            description=f"Scope {app_scope_name} for {app_scope_label}",
            default=True,
            internal=False,
        )
        data = await db_fixture.collection_scopes.get_by_id(expected_app_scope_after_update["id"])
        assert data == { key: value for key, value in expected_scope.to_dict().items() if key != "internal" }
    elif expected_app_scope_after_update:
        # Check the updated app scope in db
        data = await db_fixture.collection_scopes.get_by_id(expected_app_scope_after_update["id"])
        assert data["content"] == expected_app_scope_after_update["content"]
