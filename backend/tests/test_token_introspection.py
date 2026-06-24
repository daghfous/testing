# pylint: disable=no-member,too-many-positional-arguments,too-many-arguments
"""

Test token_introspection route
"""
import copy
from datetime import timedelta
import pytest
from bson import ObjectId

from ateme.um_backend.types import (
    Token,
    Action,
    ApiDescriptor,
    User,
    Request as RequestType,
    Scope,
)
from ateme.um_backend.user_management import (
    UserManagementApi
)
from ateme.um_backend.database import (
    Collections
)
from ateme.um_backend.request_utils import (
    HttpHeaders
)
from ateme.um_backend.utils import utcnow


async def _populate_database(
    api: UserManagementApi,
    api_descriptors: list[ApiDescriptor],
    actions: list[Action],
    scopes: list[Scope],
    user: User,
    token: Token
):
    """ Populate the database with api_descriptors, actions, scopes, user and token.

    Args:
        api (UserManagementApi): UserManagementApi instance
        api_descriptors (list[ApiDescriptor]): list of api_descriptor
        actions (list[Action]): list of action
        scopes (list[Scope]): list of scope
        user (User): a user (assume that its password is not encrypted)
        token (Token): a token (need to patch the user_id to associate them)
    """
    # Populate api_descriptors
    for api_descriptor in api_descriptors:
        result = await api.db.collection_api_descriptors.replace(api_descriptor)
        assert result
    # Populate actions
    for action in actions:
        result = await api.db.collection_actions.store(action)
        assert result
    # Populate actions
    for scope in scopes:
        result = await api.db.collection_scopes.store(scope)
        assert result
    # Assume that the password may be not encrypted
    result = await api.db.create_user(user, Collections.users.name)
    assert result
    # Need to patch the `user_id` to associate token and user
    token.user_id = user.user_id
    result = await api.db.collection_tokens.store(token)
    assert result


def _prepare_headers_and_body(headers: dict, use_body: bool) -> tuple[dict, dict]:
    """ Prepare the headers and the body according to the `use_body` flag.

    Args:
        headers (dict): headers
        use_body (bool): flag

    Returns:
        tuple[dict, dict]: updated headers and body
    """
    # Add required header
    _headers = copy.deepcopy(headers)
    _headers.update({
        "Content-type": "application/x-www-form-urlencoded",
    })
    # Prepare body
    body = {}
    if use_body:
        body = {
            "token": _headers.pop("Authorization", "").replace("Bearer ", ""),
            "method": _headers.pop("X-Original-Method", ""),
            "uri": _headers.pop("X-Original-URI", "")
        }
    return _headers, body



@pytest.mark.asyncio
@pytest.mark.parametrize("use_body", [True, False])
@pytest.mark.parametrize("actions, api_descriptors, scopes, user, token, headers, expected_result", [
    # X-api-url vs api descriptors
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-ext.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (403, "", ""),
        id="X-api-url invalid"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (403, "", ""),
        id="X-api-url missing"
    ),
    # Token
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer tokenOSS117",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (401, "", ""),
        id="Authorization invalid"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (401, "", ""),
        id="Authorization missing"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() - timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (401, "", ""),
        id="Authorization expired"
    ),
    # X-Original-Method vs action method
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "POST",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (403, "", ""),
        id="X-Original-Method invalid"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.107"
        },
        (400, "", ""),
        id="X-Original-Method missing"
    ),
    # X-Original-URI vs action route
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/test",
            "X-Real-IP": "172.29.71.107"
        },
        (403, "", ""),
        id="X-Original-URI invalid"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Real-IP": "172.29.71.107"
        },
        (400, "", ""),
        id="X-Original-URI missing"
    ),
    pytest.param(
        [Action(name="get_articles", prefix="alaint", request=RequestType(method="GET", route="/articles"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_articles", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/api1/articles?offset=5&limit=1&query=name,test,price=50",
            "X-Real-IP": "172.29.71.107"
        },
        (200, "didier", "local"),
        id="X-Original-URI valid with query parameters"
    ),
    pytest.param(
        [
            Action(
                name="import_full_configuration", prefix="any-product",
                request=RequestType(method="GET", route="/fullconfiguration")
            )
        ],
        [
            ApiDescriptor(url="http://any-product.cluster", prefix="any-product")
        ],
        [
            Scope(id="all:technical:customScope",
                  content=[{"action": "*:import_full_configuration", "policy": "allow", "resource": {}}]
            )
        ],
        User(
            creation_id=ObjectId(),
            username="jean",
            idp_name="local",
            password="123456",
            scopes=["all:technical:customScope"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://any-product.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/fullconfiguration",
            "X-Real-IP": "172.29.71.107"
        },
        (200, "jean", "local"),
        id="X-Original-URI valid for action pattern"
    ),
    pytest.param(
        [
            Action(
                name="import_full_configuration", prefix="any-product",
                request=RequestType(method="GET", route="/fullconfiguration")
            )
        ],
        [
            ApiDescriptor(url="http://any-product.cluster", prefix="any-product")
        ],
        [
            Scope(
                id="all:technical:customScope",
                content=[{"action": "*:import_full_configuration", "policy": "allow", "resource": {}}]
            )
        ],
        User(
            creation_id=ObjectId(),
            username="jean",
            password="123456",
            scopes=["all:technical:customScope"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://any-product.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/other-fullconfiguration",
            "X-Real-IP": "172.29.71.107"
        },
        (403, "", ""),
        id="X-Original-URI invalid for action pattern"
    ),
    pytest.param(
        [Action(name="get_root", prefix="alaint", request=RequestType(method="GET", route="/"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_root", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="florent",
            idp_name="idp_name_40",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/api1/"
        },
        (200, "florent", "idp_name_40"),
        id="X-Original-URI valid with prefix ended by slash for root action"
    ),
    pytest.param(
        [Action(name="get_root", prefix="alaint", request=RequestType(method="GET", route="/"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_root", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="florent",
            idp_name="idp_name_27",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/api1"
        },
        (200, "florent", "idp_name_27"),
        id="X-Original-URI valid with prefix not ended by slash for root action"
    ),
    pytest.param(
        [
            Action(
                name="checklicense",
                prefix="lcs",
                request=RequestType(
                    method="GET",
                    route="/checklicense/customer/{customer_id}/deployment/{deployment_id}/{startup_key}"
                )
            )
        ],
        [ApiDescriptor(url="http://lcs.cluster", prefix="lcs")],
        [
            Scope(
                id="lcs:operator",
                content=[
                    {
                        "action": "lcs:checklicense",
                        "policy": "allow",
                        "resource": {"customer_id": "123456", "startup_key": "test+*$iaoo-_dza"}
                    }
                ]
            )
        ],
        User(
            creation_id=ObjectId(),
            username="jean",
            password="123456",
            scopes=["lcs:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://lcs.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/checklicense/customer/123456/deployment/456789/test+",
            "X-Real-IP": "172.29.71.107"
        },
        (403, "", ""),
        id="X-Original-URI invalid with a bad resource parameter in path"
    ),
    pytest.param(
        [
            Action(
                name="checklicense",
                prefix="lcs",
                request=RequestType(
                    method="GET",
                    route="/checklicense/customer/{customer_id}/deployment/{deployment_id}/{startup_key}"
                )
            )
        ],
        [ApiDescriptor(url="http://lcs.cluster", prefix="lcs")],
        [
            Scope(
                id="lcs:operator",
                content=[
                    {
                        "action": "lcs:checklicense",
                        "policy": "allow",
                        "resource": {"customer_id": "123456", "startup_key": "test+*$iaoo-_dza"}
                    }
                ]
            )
        ],
        User(
            creation_id=ObjectId(),
            username="jean",
            password="123456",
            scopes=["lcs:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://lcs.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/checklicense/customer/123456/deployment/456789/test+*$iaoo-_dza?limit=100&offset=50",
            "X-Real-IP": "172.29.71.107"
        },
        (200, "jean", "local"),
        id="X-Original-URI valid with the expected resource parameters in path and some query parameters"
    )
])
@pytest.mark.parametrize("init_backend", [{"mock_initialize": True, "db_initialize": True}], indirect=True)
async def test_simple_token_introspection(
    init_backend,
    actions: list[Action],
    api_descriptors: list[ApiDescriptor],
    scopes: list[Scope],
    user: User,
    token: Token,
    headers: dict,
    use_body: bool,
    # Result format:
    # [0] - status_code
    # [1] - header X-User
    # [2] - header X-IDP-Name
    expected_result: tuple[int, str, str],
):
    """

    test simple token_introspection
    :param init_test:
    :param action:
    :param api_descriptor:
    :param headers:
    :param body:
    :param status_code:
    """
    client, api = init_backend

    # Context init
    await _populate_database(
        api=api,
        api_descriptors=api_descriptors,
        actions=actions,
        scopes=scopes,
        user=user,
        token=token
    )

    # `deepcopy` because `headers` argument is twice used
    # (first with use_body=True, then use_body=False)
    _headers, body = _prepare_headers_and_body(copy.deepcopy(headers), use_body)

    # Introspection
    resp = await client.post("/token_introspection", data=body, headers=_headers)
    assert resp.status == expected_result[0]
    if resp.status == 200:
        assert resp.headers[HttpHeaders.X_USER] == expected_result[1]
        assert resp.headers[HttpHeaders.X_IDP_NAME] == expected_result[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("actions, api_descriptors, scopes, user, token, headers, expected_results", [
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.255"
        },
        {
            True: (401, "", ""),
            False: (200, "didier", "local"),
        },
        id="X-Real-IP invalid"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced",
            user_ip="172.29.71.107"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
        },
        {
            True: (401, "", ""),
            False: (200, "didier", "local"),
        },
        id="X-Real-IP missing when token has user_ip"
    ),
    pytest.param(
        [Action(name="get_ping", prefix="alaint", request=RequestType(method="GET", route="/ping"))],
        [ApiDescriptor(url="http://alarm-int.cluster", prefix="alaint")],
        [Scope(id="alaint:operator", content=[{"action": "alaint:get_ping", "policy": "allow", "resource": {}}])],
        User(
            creation_id=ObjectId(),
            username="didier",
            password="123456",
            scopes=["alaint:operator"]
        ),
        Token(
            token="token007",
            started_date=utcnow(),
            expiration_date=utcnow() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=utcnow() + timedelta(hours=2),
            user_id="this id will be replaced"
        ),
        {
            "X-api-url": "http://alarm-int.cluster",
            "Authorization": "Bearer token007",
            "X-Original-Method": "GET",
            "X-Original-URI": "/ping",
            "X-Real-IP": "172.29.71.255"
        },
        {
            True: (200, "didier", "local"),
            False: (200, "didier", "local"),
        },
        id="X-Real-IP when token has no user_ip"
    )
])
@pytest.mark.parametrize("settings", [
    {"token_ip_validation": False},
    {"token_ip_validation": True},
], indirect=["settings"])
@pytest.mark.parametrize("init_backend", [
    {"mock_initialize": True, "db_initialize": True}
], indirect=True)
async def test_token_introspection_ip_validation(
    settings,
    init_backend,
    actions: list[Action],
    api_descriptors: list[ApiDescriptor],
    scopes: list[Scope],
    user: User,
    token: Token,
    headers: dict,
    # `expected_results` is dict depending on `token_ip_validation`.
    # Each result is a tuple which must match to this schema:
    # [0] - status_code
    # [1] - header X-User
    # [2] - header X-IDP-Name
    expected_results: dict[bool, tuple[int, str, str]],
):
    """ test_token_introspection_ip_validation
    """
    client, api = init_backend

    # Context init
    await _populate_database(
        api=api,
        api_descriptors=api_descriptors,
        actions=actions,
        scopes=scopes,
        user=user,
        token=token
    )

    # `deepcopy` because `headers` argument is twice used
    # (first with use_body=True, then use_body=False)
    _headers, body = _prepare_headers_and_body(copy.deepcopy(headers), use_body=False)

    # Introspection
    resp = await client.post("/token_introspection", data=body, headers=_headers)
    expected_result = expected_results[settings.token_ip_validation]
    assert resp.status == expected_result[0]
    if resp.status == 200:
        assert resp.headers[HttpHeaders.X_USER] == expected_result[1]
        assert resp.headers[HttpHeaders.X_IDP_NAME] == expected_result[2]
