"""
Test Introspector._get_content_actions_from_scopes
"""
import pytest

from ateme.um_backend.types import (
    Scope,
)
from ateme.um_backend.database import (
    Database,
)
from ateme.um_backend.introspection import (
    Introspector,
)

# pylint: disable=too-many-positional-arguments,too-many-arguments

@pytest.mark.asyncio
@pytest.mark.parametrize("scopes, user_scopes, prefix, app_name, expected_result", [
    pytest.param(
        [
            Scope(
                id="alaint:administrator",
                content=[
                    {"action": "alaint:get_events", "policy": "allow", "resource": {}}
                ],
                default=True
            ),
            Scope(
                id="alaext:guest",
                content=[
                    {"action": "alaext:get_events", "policy": "allow", "resource": {}}
                ],
                default=True
            )
        ],
        ["usr:administrator", "alaint:administrator", "alaext:guest"],
        "alaint",
        None,
        [
            {"action": "alaint:get_events", "policy": "allow", "resource": {}}
        ],
        id="default-scope-without-appname"
    ),
    pytest.param(
        [
            Scope(
                id="appname:alaint:administrator",
                content=[
                    {"action": "appname:alaint:get_events", "policy": "allow", "resource": {}},
                    {"action": "appname:alaint:post_event", "policy": "allow", "resource": {}},
                ],
                default=True,
            ),
            Scope(
                id="appname:alaext:guest",
                content=[
                    {"action": "appname:alaext:get_events", "policy": "allow", "resource": {}}
                ],
                default=True,
            )
        ],
        ["usr:administrator", "appname:alaint:administrator", "appname:alaext:guest"],
        "alaint",
        "appname",
        [
            {"action": "appname:alaint:get_events", "policy": "allow", "resource": {}},
            {"action": "appname:alaint:post_event", "policy": "allow", "resource": {}},
        ],
        id="default-scope-with-appname"
    ),
    pytest.param(
        [
            Scope(
                id="appname:alaint:administrator",
                content=[
                    {"action": "appname:alaint:get_events", "policy": "allow", "resource": {}},
                    {"action": "appname:alaint:post_event", "policy": "allow", "resource": {}},
                ],
                default=True,
            ),
            Scope(
                id="appname:alaext:guest",
                content=[
                    {"action": "appname:alaext:get_events", "policy": "allow", "resource": {}}
                ],
                default=True,
            ),
            Scope(
                id="test",
                content=[
                    {"scope": "usr:administrator"},
                    {"action": "fake:action", "policy": "allow", "resource": {}},
                ]
            ),
            Scope(
                id="custom:test",
                content=[
                    {"action": "appname:alaint:get_events", "policy": "allow", "resource": {}},
                    {"scope": "appname:alaext:administrator"},
                    {"scope": "usr:administrator"},
                    {"scope": "test"},
                    {"scope": "appname:alaint:unknown_scope"}
                ]
            )
        ],
        ["custom:test"],
        "alaint",
        "appname",
        [
            {"action": "appname:alaint:get_events", "policy": "allow", "resource": {}},
            {"action": "fake:action", "policy": "allow", "resource": {}},
        ],
        id="custom-scopes"
    )
])
async def test__get_content_actions_from_scopes(
    mocker,
    scopes: list[Scope],
    user_scopes: list[str],
    prefix: str,
    app_name: str | None,
    expected_result: list[dict],
):
    """
    Test Introspector._get_content_actions_from_scopes method
    """
    mock_client = mocker.AsyncMock()
    database = Database(mock_client, "fake_db")

    async def mock_get_list_non_default_ids() -> list[str]:
        non_default_scope_ids = []
        for scope in scopes:
            if scope.default:
                continue
            non_default_scope_ids.append(scope.id)
        return non_default_scope_ids
    mocker.patch(
        "ateme.um_backend.dao.collection_scopes.CollectionScopes.get_list_non_default_ids",
        side_effect=mock_get_list_non_default_ids
    )

    async def mock_get_by_id(_id: str, all_scopes: bool) -> dict:
        # pylint: disable=unused-argument
        for scope in scopes:
            if scope.id == _id:
                return scope.to_dict()
        return None
    mocker.patch(
        "ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id",
        side_effect=mock_get_by_id
    )

    introspector = Introspector(database)
    # pylint: disable=protected-access
    result = await introspector._get_content_actions_from_scopes(user_scopes, prefix, app_name)
    assert expected_result == result
