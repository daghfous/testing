"""
Test Introspection utils
"""
import re
import pytest

from ateme.um_backend.types import (
    Action,
)
from ateme.um_backend.introspection import (
    UserDynamicResource,
    _generate_url_pattern,
    _is_action_allowed,
    _is_scope_to_process,
)


@pytest.mark.parametrize("pattern, url, parameters_dict", [
    ("/user/{id}", "/user/louis", {"id": "louis"}),
    ("/user/{id}", "/user/louis?full=yes&creation_id=oooaoao",
     {"id": "louis", "full": "yes", "creation_id": "oooaoao"}),
    ("/user/{id}/scopes", "/user/louis/scopes?full=yes&creation_id=oooaoao",
     {"id": "louis", "full": "yes", "creation_id": "oooaoao"}),
    ("/user/{user_id}/scope/{scope_id}", "/user/louis/scope/root", {"user_id": "louis", "scope_id": "root"}),
    pytest.param("/user/{id}/scopes",
                 "/user/louis?full=yes&creation_id=oooaoao",
                 {"id": "louis", "full": "yes", "creation_id": "oooaoao"},
                 marks=pytest.mark.xfail),
    pytest.param("/user/{id}", "/user/bidule", {"id": "machin"}, marks=pytest.mark.xfail),
])
def test_user_dynamic_resource_build_from_url(pattern: str, url: str, parameters_dict: dict):
    """

    test build_from_url of UserDynamicResource
    """
    assert UserDynamicResource(pattern).build_from_url(url) == parameters_dict


@pytest.mark.parametrize("uri, url", [
    ("/users", "/users"),
    (r"/user/[a-zA-Z0-9-_:.]+", "/user/5"),
    ("/users", "/api/users"),
    ("/events", "/alarm/api/events"),
    ("/users", "/users?offset=100&limit=500&attrs=user_id,groups"),
    (r"/xml/jobs/[a-zA-Z0-9-_:.]+/esam_report", "/api/xml/jobs/a13b5fd1-0a4c-428f-a7e5-6495d1b2185a/esam_report"),
    pytest.param("/user/[a-zA-Z0-9-_:.]+", "/user/5/4", marks=pytest.mark.xfail),
])
def test_url_pattern(uri: str, url: str):
    """

    test generate_url_pattern
    :param uri:
    :param url:
    """
    pattern = _generate_url_pattern(uri)
    assert pattern
    assert re.compile(pattern).search(url)


@pytest.mark.parametrize("scope_action, requested_action, expected_result", [
    pytest.param(
        'usr:action',
        Action(prefix='usr', name='action'),
        True,
        id='action-full-match-no-appname'
    ),
    pytest.param(
        'app:usr:action',
        Action(prefix='app:usr', name='action'),
        True,
        id='action-full-match-with-appname'
    ),
    pytest.param(
        'usr:*',
        Action(prefix='usr', name='action'),
        True,
        id='action-prefix-match-no-appname'
    ),
    pytest.param(
        'app:usr:*',
        Action(prefix='app:usr', name='action'),
        True,
        id='action-prefix-match-with-appname'
    ),
    pytest.param(
        'app:*',
        Action(prefix='app:usr', name='action'),
        False,
        id='action-prefix-not-match'
    ),
    pytest.param(
        '*:action',
        Action(prefix='usr', name='action'),
        True,
        id='action-name-match-no-appname'
    ),
    pytest.param(
        '*:action',
        Action(prefix='app:usr', name='action'),
        True,
        id='action-name-match-with-appname'
    ),
    pytest.param(
        '*:action',
        Action(prefix='app:usr', name='subapp:action'),
        True,
        id='subapp-action-name-match-with-appname'
    ),
    pytest.param(
        '*:action2',
        Action(prefix='usr', name='action'),
        False,
        id='action-name-not-match'
    ),
])
def test__is_action_allowed(scope_action: str, requested_action: Action, expected_result: bool):
    """
    Test _is_action_allowed function
    """
    assert _is_action_allowed(scope_action, requested_action) == expected_result


@pytest.mark.parametrize("scope_id, prefix, app_name, non_default_scope_ids, expected_result", [
    pytest.param(
        "all:administrator", "usr", None, [], True,
        id="L1 scope with valid prefix"
    ),
    pytest.param(
        "usr:administrator", "usr", None, [], True,
        id="L2 scope with valid prefix"
    ),
    pytest.param(
        "usr:administrator", "test", None, [], False,
        id="L2 scope with invalid prefix"
    ),
    pytest.param(
        "app:administrator", "api", "app", [], True,
        id="L2 scope with valid prefix and app_name"
    ),
    pytest.param(
        "app:api:administrator", "api", "app", [], True,
        id="L3 scope with valid prefix and app_name"
    ),
    pytest.param(
        "app:api:administrator", "test", "app", [], False,
        id="L3 scope with invalid app_name"
    ),
    pytest.param(
        "app:api:administrator", "api", "test", [], False,
        id="L3 scope with invalid prefix"
    ),
    pytest.param(
        "custom:administrator", "api", "test", ["custom:administrator"], True,
        id="Custom scope, should be always processed"
    ),
    pytest.param(
        "titi:administrator", "api", "test", ["custom:administrator"], False,
        id="Invalid custom scope"
    )
])
def test__is_scope_to_process(
    scope_id: str,
    prefix: str,
    app_name: str | None,
    non_default_scope_ids: list[str],
    expected_result: bool
):
    """
    Test _is_scope_to_process function
    """
    result = _is_scope_to_process(scope_id, prefix, app_name, non_default_scope_ids)
    assert expected_result == result
