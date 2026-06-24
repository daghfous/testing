"""
Test Introspector._resolve_action
"""
from unittest.mock import call
import pytest

from ateme.um_backend.types import (
    Action,
    Request as RequestType,
    RequestMethod,
)
from ateme.um_backend.introspection import (
    Introspector,
)

# pylint: disable=too-many-positional-arguments,too-many-arguments

@pytest.mark.parametrize("uri, method, prefix, app_name, action_expected, mocks_func, mocks_func_args_expected", [
    pytest.param(
        "/",
        "GET",
        "ala",
        None,
        Action(
            name="get_root",
            prefix="ala",
            request=RequestType(method=RequestMethod.GET, route="/"),
        ),
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": {
                "return_value": [
                    Action(
                        name="get_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
                    ),
                    Action(
                        name="get_root",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.GET, route="/"),
                    ),
                ]
            }
        },
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": [
                call({"prefix": "ala", "request.method": "GET"})
            ],
        },
        id="root-path"
    ),
    pytest.param(
        "/user/local_local/waza",
        "GET",
        "ala",
        None,
        Action(
            name="get_user_by_app",
            prefix="ala",
            request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
        ),
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": {
                "return_value": [
                    Action(
                        name="get_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
                    ),
                    Action(
                        name="delete_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.DELETE, route="/user/{app}/{username}"),
                    ),
                ]
            }
        },
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": [
                call({"prefix": "ala", "request.method": "GET"})
            ],
        },
        id="with-query-param"
    ),
    pytest.param(
        "/user/waza",
        "GET",
        "ala",
        None,
        None,
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": {
                "return_value": [
                    Action(
                        name="get_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
                    ),
                    Action(
                        name="delete_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.DELETE, route="/user/{app}/{username}"),
                    ),
                ]
            }
        },
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": [
                call({"prefix": "ala", "request.method": "GET"})
            ],
        },
        id="not-found-with-query-param"
    ),
    pytest.param(
        "/api/user/local_local/waza",
        "GET",
        "ala",
        None,
        Action(
            name="get_user_by_app",
            prefix="ala",
            request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
        ),
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": {
                "return_value": [
                    Action(
                        name="get_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
                    ),
                    Action(
                        name="delete_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.DELETE, route="/user/{app}/{username}"),
                    ),
                ]
            }
        },
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": [
                call({"prefix": "ala", "request.method": "GET"})
            ],
        },
        id="without-rewrite-url"
    ),
    pytest.param(
        "/api/user",
        "GET",
        "ala",
        None,
        None,
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": {
                "return_value": [
                    Action(
                        name="get_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.GET, route="/user/{app}/{username}"),
                    ),
                    Action(
                        name="delete_user_by_app",
                        prefix="ala",
                        request=RequestType(method=RequestMethod.DELETE, route="/user/{app}/{username}"),
                    ),
                ]
            }
        },
        {
            "ateme.um_backend.dao.collection_actions.CollectionActions.get_list": [
                call({"prefix": "ala", "request.method": "GET"})
            ],
        },
        id="not-found-without-rewrite-url"
    ),
], indirect=["mocks_func"])
async def test__resolve_action(
    init_api,
    uri: str,
    method: str,
    prefix: str,
    app_name: str | None,
    action_expected: Action | None,
    mocks_func: dict[str, dict],
    mocks_func_args_expected: dict[str, dict],
):
    """

    Test `resolve_action` from UserManagementApi, use in introspection endpoint.
    Take request in input and search action in database and apply regex to match query parameter in path.

    Args:
        uri (str): URI of request forward to introspection.
        method (str): Method of request  input.
        prefix (str): Prefix in order to filter action.
        action_expected (Action | None): Action expected or None if not found.
        mocks_func (dict[str, dict]): Function to mock.
        mocks_func_args_expected (dict[str, dict]): Args of mock calls expected.
    """
    introspector = Introspector(init_api.db)
    # pylint: disable=protected-access
    action = await introspector._resolve_action(uri, method, prefix, app_name)

    if action_expected:
        assert action.to_dict() == action_expected.to_dict()
    else:
        assert not action

    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mocks_func_args_expected.items():
        mocks_func[_mock_func].assert_has_calls(_calls)
