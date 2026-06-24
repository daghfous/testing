"""
Test Introspector._check_action
"""
import pytest

from ateme.um_backend.types import (
    Action,
    Request as RequestType,
)
from ateme.um_backend.introspection import (
    Introspector,
)


@pytest.mark.parametrize("action, content_actions, uri, expected_result", [
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [],
        "/event/{id}",
        False,
        id="action not present"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "allow", "resource": {}}],
        "/baseurl/event/eventid",
        True,
        id="action present and allowed with base url"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "allow", "resource": {}}],
        "/event/eventid",
        True,
        id="action present and allowed"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "allow", "resource": {"id": "*"}}],
        "/event/eventid",
        True,
        id="action present and allowed all resources"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "allow", "resource": {"id": "eventid"}}],
        "/event/eventid",
        True,
        id="action present and allowed on a specific resource id, id match"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "allow", "resource": {"id": "eventid"}}],
        "/event/totoid",
        False,
        id="action present and allowed on a specific resource id, id not match"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "deny", "resource": {"id": "*"}}],
        "/event/eventid",
        False,
        id="action present and denied for all resources"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "deny", "resource": {"id": "eventid"}}],
        "/event/eventid",
        False,
        id="action present and denied on a specific resource id, id match"
    ),
    pytest.param(
        Action(name="put_event", prefix="appname:alaint", request=RequestType(method="PUT", route="/event/{id}")),
        [{"action": "appname:alaint:put_event", "policy": "deny", "resource": {"id": "eventid"}}],
        "/event/totoid",
        True,
        id="action present and denied on a specific resource id, id not match"
    )
])
def test__check_action(
    action: Action,
    content_actions: list[dict],
    uri: str,
    expected_result: bool
):
    """
    Test Introspector._check_action method
    """
    introspector = Introspector(None)
    # pylint: disable=protected-access
    result = introspector._check_action(action, content_actions, uri)
    assert result == expected_result
