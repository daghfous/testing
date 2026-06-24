"""

Test parallels purpose is to simulate replica use case.
"""
import asyncio
import pytest

from ateme.um_backend.database import ScopeFilter


@pytest.mark.parametrize("multiple_api", [2], indirect=True)
async def test_parallels_initialize(multiple_api, init_database, caplog):
    """

    Check that there is no side effect when multiple initialize at the same time.
    multiple_api fixture will create multiple instance of UserManagementApi, number can be
    parametrize.

    Use asyncio.wait to parallelize initialize, as we use transaction we should trigger an exception
    on some replicas.
    """
    await asyncio.wait([asyncio.create_task(api.initialize()) for api in multiple_api])

    actions = await init_database.collection_actions.get_list({"internal": {"$ne": True}})
    internal_actions = await init_database.collection_actions.get_list({"internal": True})

    # There 45 actions define on user_management api
    assert len(actions) == 47
    assert len(internal_actions) == 1

    scopes = await init_database.collection_scopes.get_list()
    assert len(scopes) == 8
    scope_filter = ScopeFilter(internal=True)
    internal_scopes = await init_database.collection_scopes.get_list(scope_filter=scope_filter)
    assert len(internal_scopes) == 2
