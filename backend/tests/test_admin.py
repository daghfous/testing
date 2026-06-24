"""

Test admin user.
"""
import pytest
from aiohttp.test_utils import TestClient


async def test_check_admin_exist(init_backend: TestClient):
    """

    Check if no admin define in database, GET /admin must return 404.
    """
    _api, _ = init_backend
    # Get /admin endpoint without admin already configure
    resp = await _api.get("/admin")
    assert resp.status == 404
    assert resp.headers["Content-Type"] == "text/plain"
    assert (await resp.text()) == "No user admin exists"


async def test_create_admin(init_backend: TestClient, internal_admin_user: dict, admin_user: dict):
    """

    * Can't create admin with internal user
    * Check admin creation
    * Then can't create a second admin
    * Check login with admin previously created
    * Check scopes of admin user
    """
    # pylint: disable=too-many-statements
    _api, _ = init_backend
    admin_headers = {}

    internal_admin_resp = await _api.post(
        "/admin",
        json={"username": internal_admin_user["username"], "password": "Admin!A0"},
    )
    assert internal_admin_resp.status == 403
    assert (await internal_admin_resp.text()) == "This admin username is reserved"

    # Try to create admin that doesn't respect the password constraints
    admin_resp = await _api.post("/admin", json={"username": "admin", "password": "AdminA0!"})
    assert admin_resp.status == 400
    assert (await admin_resp.text()) == "the password doesn't match the constraints"

    admin_resp = await _api.post("/admin", json=admin_user)
    assert admin_resp.status == 201
    assert (await admin_resp.text()) == "OK"

    # Try to create a second admin user => Fail
    admin_resp = await _api.post("/admin", json=admin_user)
    assert admin_resp.status == 403
    assert (await admin_resp.text()) == "An admin user is already created, only one admin is allowed..."

    # Check admin exist
    get_admin_resp = await _api.get("/admin")
    assert get_admin_resp.status == 200
    assert (await get_admin_resp.json()) == {"username": "admin"}

    # Login with admin credentials
    login_admin_resp = await _api.post("/token", json=admin_user)
    assert login_admin_resp.status == 200
    body = await login_admin_resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    assert 'refresh_token' in body
    assert 'expires_in' in body
    assert 'token_type' in body
    token = body['access_token']
    admin_headers['Authorization'] = f"Bearer {token}"

    # Verify scopes are properly set
    get_users_resp = await _api.get("/users", headers=admin_headers)
    assert get_users_resp.status == 200
    body = await get_users_resp.json()
    assert len(body) == 1
    assert body[0].get("scopes", []) == ["all:administrator"]

    # Re-login with admin credentials
    login_admin_resp = await _api.post("/token", json=admin_user)
    assert login_admin_resp.status == 200
    body = await login_admin_resp.json()

    assert isinstance(body, dict)
    assert 'access_token' in body
    token_re = body['access_token']
    # a new token is generated for each connection even if it's the same user
    assert token_re != token

    # Test the patch of the password
    update_password_resp = await _api.patch(
        "/user/me/password",
        json={
            "new_password": "hHg3gV#073PjvW$m^zWm",
            "old_password": admin_user["password"],
        },
        headers={'Authorization': f'Bearer {token_re}'}
    )
    assert update_password_resp.status == 200
    assert (await update_password_resp.json()) == {"body": "Password changed successfully !"}


    # Re-login with admin credentials
    login_admin_resp = await _api.post("/token", json={"username": "admin", "password": "hHg3gV#073PjvW$m^zWm"})
    assert login_admin_resp.status == 200
    body = await login_admin_resp.json()
    token = body['access_token']
    admin_headers['Authorization'] = f"Bearer {token}"

    # Scopes shall be unchanged after patch
    get_users_resp = await _api.get("/users", headers=admin_headers)
    assert get_users_resp.status == 200
    body = await get_users_resp.json()

    assert len(body) == 1, f'{body}'
    assert body[0].get("scopes", []) == ["all:administrator"]


@pytest.mark.parametrize("endpoint, body, status_code_expected, body_expected", [
    # deprecated endpoint
    (
        "/users",
        [{"username": "admin", "idp_name": "local", "scopes": []}],
        410,
        "this endpoint is deprecated"
    ),
# Should be fix by https://myateme.atlassian.net/browse/MS-8154
#       (
#           "/users/local/admin",
#           {"username": "admin", "idp_name": DEFAULT_LOCAL_IDP_NAME, "scopes": []},
#           403,
#           b"Can't update admin user"
#       )
])
async def test_update_admin_fail(
    init_backend_with_admin,
    endpoint: str,
    body: str | list,
    status_code_expected: int,
    body_expected: dict | str,
):
    """
    Test update admin fail, Check different endpoints: first the legacy way to update users and
    finally the modern way: /users/{idp_name}/{username}.
    """
    _api, _, _admin_token = init_backend_with_admin
    patch_resp = await _api.patch(endpoint, json=body, headers={"Authorization": f"Bearer {_admin_token}"})
    assert patch_resp.status == status_code_expected
    result = await patch_resp.text()
    assert result == body_expected
