#pylint: disable=no-member
"""
Test resource access policy
"""
import os

import pytest
import pytest_asyncio
import yaml


API_PATH = os.path.join(os.path.dirname(__file__), "definitions", "resource_api.yaml")

USERNAME = 'gianluigi'
PASSWORD = 'Buffonnn1!'


async def update_scope(api, admin_headers, scope_content):
    """
    Function used to update a scope by providing the new scope content
    """
    # Update test scope
    resp = await api.patch(
        "/scopes/test:goal",
        json={
            "id": "test:goal",
            "label": "test resource",
            "description": "description",
            "content": scope_content,
        },
        headers=admin_headers,
    )
    assert resp.status == 200


@pytest_asyncio.fixture(scope='function', name="init_definition")
# pylint: disable=unused-argument
async def _init_definition(init_backend_with_admin):
    """
    Create a scope and a user for test
    Login with this user
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    # populate with API_PATH
    with open(API_PATH, "r", encoding="utf-8") as _file:
        api_content = yaml.safe_load(_file.read())

    resp = await _api.post(
        "/api_definition",
        json={"main_api": api_content, "base_url": "http://test"},
        headers=_admin_headers,
    )
    assert resp.status == 201

    # Update the scope with one resource deny
    await update_scope(
        _api,
        _admin_headers,
        [
            {
                "action": "test:get_resource",
                "policy": "deny",
                "resource": {"name": "zizou"},
            }
        ],
    )

    # Create a user with the scope previously updated
    # TODO: how to init users
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": USERNAME,
                "password": PASSWORD,
                "scopes": ["test:goal"],
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201

    # Login with this new user
    resp = await _api.post(
        "/token",
        json={"username": USERNAME, "password": PASSWORD},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()
    token = body['access_token']

    yield token, init_backend_with_admin


@pytest.mark.parametrize("init_backend", [{"mock_initialize": True, "db_initialize": True}], indirect=True)
async def test_resource_deny(init_backend, init_definition):
    """
    test_resource_deny
    """
    # Get the resource deny
    token, init_backend_with_admin = init_definition
    _api, _, _ = init_backend_with_admin

    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/zizou/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 403

    # Get the resource allow
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/gianluigi/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 200

    # Get an allowed resource that contains one space
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/e%20kipchoge/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 200


@pytest.mark.parametrize("init_backend", [{"mock_initialize": True, "db_initialize": True}], indirect=True)
async def test_resource_allow(init_backend, init_definition):
    """
    test_resource_allow
    """
    token, init_backend_with_admin = init_definition
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    # Update scope
    await update_scope(
        _api,
        _admin_headers,
        [
            {
                "action": "test:get_resource",
                "policy": "allow",
                "resource": {"name": "zizou"},
            }
        ],
    )

    # Get the resource allow
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/zizou/hello",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 200

    # Get the resource deny
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/gianluigi/hello",
            "method": "GET",
        },
    )
    assert resp.status == 403


@pytest.mark.parametrize("init_backend", [{"mock_initialize": True, "db_initialize": True}], indirect=True)
async def test_resource_array_deny(init_backend, init_definition):
    """
    test_resource_array_deny
    """
    token, init_backend_with_admin = init_definition
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Update scope
    await update_scope(
        _api,
        _admin_headers,
        [{"action": "test:get_resource", "policy": "deny", "resource": {"name": ["zizou", "henry"]}}],
    )

    # Get the resource deny
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/henry/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 403

    # Get the resource allow
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/gianluigi/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 200


@pytest.mark.parametrize("init_backend", [{"mock_initialize": True, "db_initialize": True}], indirect=True)
async def test_resource_array_allow(init_backend, init_definition):
    """
    test_resource_array_allow
    """
    token, init_backend_with_admin = init_definition
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Update scope
    await update_scope(
        _api,
        _admin_headers,
        [{"action": "test:get_resource", "policy": "allow", "resource": {"name": ["zizou", "henry"]}}],
    )

    # Get the resource allow
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/henry/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 200

    # Get the resource deny
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/gianluigi/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 403


@pytest.mark.parametrize("init_backend", [{"mock_initialize": True, "db_initialize": True}], indirect=True)
async def test_resource_all_deny(init_backend, init_definition):
    """
    test_resource_all_deny
    """
    token, init_backend_with_admin = init_definition
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Update scope
    await update_scope(
        _api,
        _admin_headers,
        [
            {
                "action": "test:get_resource",
                "policy": "deny",
                "resource": {"name": ["*"]},
            }
        ],
    )

    # Get a resource deny
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/zizou/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 403

    # Get another resource deny
    resp = await _api.post(
        "/token_introspection",
        data={
            "token": token,
            "uri": "/resources/gianluigi/toto",
            "method": "GET",
        },
        headers={"X-api-url": "http://test"},
    )
    assert resp.status == 403
