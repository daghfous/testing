"""
Test Introspector.check_introspection
"""
from unittest.mock import call
from contextlib import ExitStack as DoesNotRaise
import pytest
from bson import ObjectId

from ateme.um_backend.types import (
    Action,
    ApiDescriptor,
    User,
    Request as RequestType,
)
from ateme.um_backend.database import (
    Database,
)
from ateme.um_backend.introspection import (
    Introspector,
    IntrospectionError
)


FAKE_ACTION = Action(name="get_events", prefix="alaext", request=RequestType(method="GET", route="/events"))


# pylint: disable=too-many-positional-arguments,too-many-arguments

@pytest.mark.parametrize("user_dict, uri, method, api_url, context, mocks_func, mocks_func_args_expected", [
    pytest.param(
        User(
            creation_id=ObjectId(),
            username="admin",
            password="password",
            scopes=[]
        ).to_dict(),
        "/events",
        "GET",
        "http://0.0.0.0:8080/alarms-ext",
        pytest.raises(IntrospectionError),
        {},
        {},
        id="user with empty scopes"
    ),
    pytest.param(
        User(
            creation_id=ObjectId(),
            username="admin",
            password="password",
            scopes=["alaext:administrator"]
        ).to_dict(),
        "/events",
        "GET",
        "http://0.0.0.0:8080/alarms-ext",
        pytest.raises(IntrospectionError),
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": {
                "return_value": ApiDescriptor(url="http://0.0.0.0:8080/alarms-ext", prefix="alaext")
            },
            "ateme.um_backend.introspection.Introspector._resolve_action": {
                "return_value": None
            }
        },
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": [
                call("http://0.0.0.0:8080/alarms-ext")
            ],
            "ateme.um_backend.introspection.Introspector._resolve_action": [call("/events", "GET", "alaext", None)]
        },
        id="no action found"
    ),
    pytest.param(
        User(
            creation_id=ObjectId(),
            username="admin",
            password="password",
            scopes=["alaext:administrator"]
        ).to_dict(),
        "/events",
        "GET",
        "http://0.0.0.0:8080/alarms-ext",
        pytest.raises(IntrospectionError),
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": {
                "return_value": ApiDescriptor(url="http://0.0.0.0:8080/alarms-ext", prefix="alaext")
            },
            "ateme.um_backend.introspection.Introspector._resolve_action": {
                "return_value": FAKE_ACTION
            },
            "ateme.um_backend.introspection.Introspector._get_content_actions_from_scopes": {
                "return_value": []
            },
        },
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": [
                call("http://0.0.0.0:8080/alarms-ext")
            ],
            "ateme.um_backend.introspection.Introspector._resolve_action": [
                call("/events", "GET", "alaext", None)
            ],
            "ateme.um_backend.introspection.Introspector._get_content_actions_from_scopes": [
                call(["alaext:administrator"], "alaext", None)
            ],
        },
        id="empty content actions"
    ),
    pytest.param(
        User(
            creation_id=ObjectId(),
            username="admin",
            password="password",
            scopes=["alaext:administrator"]
        ).to_dict(),
        "/events",
        "GET",
        "http://0.0.0.0:8080/alarms-ext",
        pytest.raises(IntrospectionError),
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": {
                "return_value": ApiDescriptor(url="http://0.0.0.0:8080/alarms-ext", prefix="alaext")
            },
            "ateme.um_backend.introspection.Introspector._resolve_action": {
                "return_value": FAKE_ACTION
            },
            "ateme.um_backend.introspection.Introspector._get_content_actions_from_scopes": {
                "return_value": [
                    {"action": "alaext:get_events", "policy": "allow", "resource": {}}
                ]
            },
            "ateme.um_backend.introspection.Introspector._check_action": {
                "return_value": False
            },
        },
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": [
                call("http://0.0.0.0:8080/alarms-ext")
            ],
            "ateme.um_backend.introspection.Introspector._resolve_action": [
                call("/events", "GET", "alaext", None)
            ],
            "ateme.um_backend.introspection.Introspector._get_content_actions_from_scopes": [
                call(["alaext:administrator"], "alaext", None)
            ],
            "ateme.um_backend.introspection.Introspector._check_action": [
                call(
                    FAKE_ACTION,
                    [{"action": "alaext:get_events", "policy": "allow", "resource": {}}],
                    "/events"
                )
            ],
        },
        id="action denied"
    ),
    pytest.param(
        User(
            creation_id=ObjectId(),
            username="admin",
            password="password",
            scopes=["alaext:administrator"]
        ).to_dict(),
        "/events",
        "GET",
        "http://0.0.0.0:8080/alarms-ext",
        DoesNotRaise(),
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": {
                "return_value": ApiDescriptor(url="http://0.0.0.0:8080/alarms-ext", prefix="alaext")
            },
            "ateme.um_backend.introspection.Introspector._resolve_action": {
                "return_value": FAKE_ACTION
            },
            "ateme.um_backend.introspection.Introspector._get_content_actions_from_scopes": {
                "return_value": [
                    {"action": "alaext:get_events", "policy": "allow", "resource": {}}
                ]
            },
        },
        {
            "ateme.um_backend.dao.collection_api_descriptors.CollectionApiDescriptors.get_by_url": [
                call("http://0.0.0.0:8080/alarms-ext")
            ],
            "ateme.um_backend.introspection.Introspector._resolve_action": [
                call("/events", "GET", "alaext", None)
            ],
            "ateme.um_backend.introspection.Introspector._get_content_actions_from_scopes": [
                call(["alaext:administrator"], "alaext", None)
            ],
        },
        id="action authorized"
    )
], indirect=["mocks_func"])
async def test_check_introspection(
    mocker,
    user_dict: dict,
    uri: str,
    method: str,
    api_url: str,
    context,
    mocks_func: dict[str, dict],
    mocks_func_args_expected: dict[str, dict]
):
    """
    Test Introspector.check_introspection method
    """
    mock_client = mocker.AsyncMock()
    database = Database(mock_client, "fake_db")
    # Test check_introspection
    introspector = Introspector(database)
    with context:
        await introspector.check_introspection(user_dict, uri, method, api_url)
    # Check that mocked function have been called with the right arguments
    for _mock_func, _calls in mocks_func_args_expected.items():
        mocks_func[_mock_func].assert_has_calls(_calls)
