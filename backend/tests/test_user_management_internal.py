# pylint: disable=too-many-lines
# pylint: disable=no-member
"""
User management tests
"""
from datetime import timedelta, datetime

from ateme.um_backend.database import Collections
from ateme.um_backend.types import (
    User,
    Scope,
    DEFAULT_LOCAL_IDP_NAME
)
from .conftest import generate_internal_user_password
from .utils import (
    NEW_SCOPE,
)


DEFAULT_PASSWORD = "defaultPassword0!"

NEW_SCOPE_FOR_INTERNAL_USER = Scope(id='lic:filew9replay', label='usr', description="scope for FileW9Replay lic",
                                    content=[{"action": "lic:put_stats", "policy": "allow", "resource": {}},
                                             {"action": "lic:check_license", "policy": "allow", "resource": {}}],
                                    internal=True)
NEW_SCOPE_FOR_INTERNAL_USER_2 = Scope(id='lic:filew9live', label='usr', description="scope for FileW9Live lic",
                                      content=[{"action": "lic:get_license", "policy": "allow", "resource": {}}],
                                      internal=True)


async def test_create_admin(init_backend, admin_user, internal_admin_user):
    """

    :return:
    """
    _api, _ = init_backend
    _admin_headers = {}

    #  fail to create admin user with internal_admin username
    resp = await _api.post(
        "/admin",
        json={
            "username": internal_admin_user["username"],
            "password": admin_user["password"],
        },
        headers=_admin_headers,
    )
    assert resp.status == 403
    # create admin user
    resp = await _api.post("/admin", json=admin_user, headers=_admin_headers)
    assert resp.status == 201
    # Login with admin credentials
    resp = await _api.post(
        "/token", json=admin_user
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    assert 'refresh_token' in body
    assert 'expires_in' in body
    assert 'token_type' in body
    token = body['access_token']
    _admin_headers['Authorization'] = f"Bearer {token}"

    # create non internal user used in the following tests
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": "user_name_1",
                "password": DEFAULT_PASSWORD,
                "scopes": ["usr:engineer"],
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201

    resp = await _api.get("/users", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2

    resp = await _api.post(
        "/scopes",
        json=[NEW_SCOPE.to_dict()],
        headers=_admin_headers,
    )
    assert resp.status == 200


async def test_login_internal_admin(init_backend, internal_admin_user):
    """

    :return:
    """
    _api, _ = init_backend
    _internal_admin_headers = {"content-type": "application/json"}

    # Login with internal admin credentials
    resp = await _api.post(
        "/token", json=internal_admin_user, headers={"content-type": "application/json"}
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    assert 'refresh_token' in body
    assert 'expires_in' in body
    assert 'token_type' in body
    token = body['access_token']
    _internal_admin_headers['Authorization'] = f"Bearer {token}"

    # Re-login with internal admin credentials
    resp = await _api.post(
        "/token", json=internal_admin_user, headers={"content-type": "application/json"}
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    token_re = body['access_token']
    # a new token is generated for each connection even if it's the same user
    assert token_re != token

    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 1
    assert isinstance(body[0], dict)
    assert body[0]['username'] == internal_admin_user['username']


async def test_internal_users_by_internal_admin(
    init_backend_with_admin, init_backend_with_internal_admin, internal_admin_user
):
    # pylint: disable=too-many-statements,too-many-locals
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _, _, _internal_admin_token = init_backend_with_internal_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _internal_admin_headers = {"Authorization": f"Bearer {_internal_admin_token}"}

    internal_user_name_1 = "internal_user_1"
    internal_user_name_2 = "internal_user_2"
    internal_user_name_3 = "internal_user_3"
    internal_user_password_1 = generate_internal_user_password(username=internal_user_name_1)
    internal_user_password_2 = generate_internal_user_password(username=internal_user_name_2)
    internal_user_password_3 = generate_internal_user_password(username=internal_user_name_3)

    # Get all non internal users (admin credentials -> non internal users)
    resp = await _api.get("/users", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    existing_users_nb = len(body)
    assert all("internal" not in user for user in body), "internal field should not be returned"

    # create an internal scope
    resp = await _api.post(
        "/scopes",
        json=[NEW_SCOPE_FOR_INTERNAL_USER.to_dict()],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200

    # Create 3 internal users by internal_admin
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": internal_user_name_1,
                "password": internal_user_password_1,
                "scopes": ["usr:engineer", NEW_SCOPE_FOR_INTERNAL_USER.id],
            },
            {"username": internal_user_name_2, "password": internal_user_password_2},
            {"username": internal_user_name_3, "password": internal_user_password_3},
        ],
        headers=_internal_admin_headers,
    )
    assert resp.status == 201

    # Fail to create internal user by internal_admin with idp_name/idp_type
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": "internal_ldap_user_name",
                "idp_name": "ldap_ateme.com",
                "scopes": ["usr:engineer", NEW_SCOPE_FOR_INTERNAL_USER.id],
            }
        ],
        headers=_internal_admin_headers,
    )
    assert resp.status == 400
    body = await resp.json()
    assert body == {'errors': ["Failed validating additionalProperties in schema[root]['items']: "
                               "Additional properties are not allowed ('idp_name' was unexpected)"]}

    # Get all users (non internal): should be unchanged
    resp = await _api.get("/users", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == existing_users_nb
    # Get all internal users
    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 4, "4 internal users should exist"  # 3 users + internal admin
    user_1 = User.from_dict(body[0])
    assert user_1.username == internal_user_name_1
    assert not user_1.first_login
    assert user_1.enabled
    assert len(user_1.scopes) == 2
    assert "lic:filew9replay" in user_1.scopes, "lic:filew9replay should be in user scope"
    assert "usr:internal" in user_1.scopes, "usr:internal should be in user scope"
    assert "usr:engineer" not in user_1.scopes, "internal user should not have non internal scope"
    assert "usr:guest" not in user_1.scopes, "internal user should not have non internal scope"
    user_2 = User.from_dict(body[1])
    assert user_2.username == internal_user_name_2
    user_3 = User.from_dict(body[2])
    assert user_3.username == internal_user_name_3
    user_4 = User.from_dict(body[3])
    assert user_4.username == internal_admin_user['username']

    # fail to create an internal user with the same name as an existing internal user
    resp = await _api.post(
        "/users",
        json=[{"username": internal_user_name_1, "password": "passwordA0!"}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 201
    body = await resp.json()
    assert body["errors"] == ["Unable to create user 'internal_user_1': internal_user_1 already exists"]

    # delete an internal user
    resp = await _api.delete(
        "/users",
        json=[{"username": internal_user_name_2, "idp_name": DEFAULT_LOCAL_IDP_NAME}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    # Check if user deleted
    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 3, "3 internal users should exist"  # 2 user + internal admin

    # delete an internal user just by passing its username, (not an object with username + idp_name)
    resp = await _api.delete(
        "/users",
        json=[internal_user_name_3],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    # Check if user deleted
    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2, "2 internal users should exist"  # 1 user + internal admin

    # delete the last internal user
    resp = await _api.delete(
        "/users",
        json=[{"username": internal_user_name_1, "idp_name": DEFAULT_LOCAL_IDP_NAME}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200

    # Get all internal users
    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 1, "1 internal user should exist"  # internal admin
    user_1 = User.from_dict(body[0])
    assert user_1.username == internal_admin_user['username']


async def test_internal_scope(init_backend_with_admin, init_backend_with_internal_admin):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _, _, _internal_admin_token = init_backend_with_internal_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _internal_admin_headers = {"Authorization": f"Bearer {_internal_admin_token}"}

    # create an internal scope
    resp = await _api.post(
        "/scopes",
        json=[NEW_SCOPE_FOR_INTERNAL_USER.to_dict()],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200

    # create a 2nd internal scope
    resp = await _api.post(
        "/scopes",
        json=[NEW_SCOPE_FOR_INTERNAL_USER_2.to_dict()],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    # Check created scope by its id
    resp = await _api.get(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    scope = await resp.json()
    assert scope, "scope should be defined"
    assert isinstance(scope, dict), "scope should be type of dict"
    assert scope.get('content') == NEW_SCOPE_FOR_INTERNAL_USER_2.content

    # fail to update internal scope by admin
    resp = await _api.patch(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        json={
            "label": "usr",
            "content": [{"action": "lic:get_stats", "policy": "allow", "resource": {}}],
        },
        headers=_admin_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body == "Can't find scope lic:filew9live"
    # Update internal scope by internal_admin
    resp = await _api.patch(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        json={
            "label": "usr",
            "content": [{"action": "lic:get_stats", "policy": "allow", "resource": {}}],
        },
        headers=_internal_admin_headers,
    )
    assert resp.status == 200

    # Check updated scope by its id
    resp = await _api.get(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    scope = await resp.json()
    assert scope.get('content') == [{"action": "lic:get_stats", "policy": "allow", "resource": {}}]

    # Only internal scopes are returned when getting all scopes by internal admin
    resp = await _api.get(
        "/scopes", headers=_internal_admin_headers
    )
    assert resp.status == 200
    scopes = await resp.json()
    assert len(scopes) == 4
    assert any(Scope.from_dict(scope).id == NEW_SCOPE_FOR_INTERNAL_USER.id for scope in scopes)
    assert any(Scope.from_dict(scope).id == NEW_SCOPE_FOR_INTERNAL_USER_2.id for scope in scopes)
    # internal scope should not be returned when getting all scopes by admin
    resp = await _api.get("/scopes", headers=_admin_headers)
    assert resp.status == 200
    scopes = await resp.json()
    assert all(Scope.from_dict(scope).id != NEW_SCOPE_FOR_INTERNAL_USER.id for scope in scopes)
    assert all(Scope.from_dict(scope).id != NEW_SCOPE_FOR_INTERNAL_USER_2.id for scope in scopes)

    # get scope by id by internal admin
    resp = await _api.get(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER.id}",
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    scope = await resp.json()
    assert Scope.from_dict(scope).id == NEW_SCOPE_FOR_INTERNAL_USER.id
    # fail to get an internal scope by id by admin
    resp = await _api.get(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER.id}",
        headers=_admin_headers,
    )
    assert resp.status == 404

    # fail to remove first internal scope by admin with route /scopes
    resp = await _api.delete(
        "/scopes",
        json=[{"id": NEW_SCOPE_FOR_INTERNAL_USER.id}],
        headers=_admin_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    assert "Scopes removed except ['lic:filew9replay']" in body["body"]
    # remove first internal scope by internal admin with route /scopes, non internal scope not removed
    resp = await _api.delete(
        "/scopes",
        json=[{"id": NEW_SCOPE_FOR_INTERNAL_USER.id}, {"id": NEW_SCOPE.id}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    assert "Scopes removed except ['usr:wheel']" in body["body"]

    # fail to remove second internal scope by admin with route /scopes/{}
    resp = await _api.delete(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        headers=_admin_headers,
    )
    assert resp.status == 404
    # remove second internal scope with route /scopes/{}
    resp = await _api.delete(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        headers=_internal_admin_headers,
    )
    assert resp.status == 200

    # Check scope deletions
    resp = await _api.get(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER.id}",
        headers=_internal_admin_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body
    resp = await _api.get(
        f"/scopes/{NEW_SCOPE_FOR_INTERNAL_USER_2.id}",
        headers=_internal_admin_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body


async def test_internal_user_login(init_backend_with_admin, init_backend_with_internal_admin, init_database):
    """

    :return:
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _, _, _internal_admin_token = init_backend_with_internal_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _internal_admin_headers = {"Authorization": f"Bearer {_internal_admin_token}"}

    internal_user_name = "license_agent"
    internal_user_password = generate_internal_user_password(username=internal_user_name)

    # create an internal scope
    resp = await _api.post(
        "/scopes",
        json=[NEW_SCOPE_FOR_INTERNAL_USER.to_dict()],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200

    # Create 1 internal user with the internal scope
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": internal_user_name,
                "password": internal_user_password,
                "scopes": [NEW_SCOPE_FOR_INTERNAL_USER.id],
            }
        ],
        headers=_internal_admin_headers,
    )
    assert resp.status == 201

    # Check internal user creation with the expected scope
    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2, "2 internal users should exist"  # 1 user + internal admin
    user = User.from_dict(body[0])
    assert user.username == internal_user_name
    assert not user.first_login
    assert user.enabled
    assert len(user.scopes) == 2
    assert NEW_SCOPE_FOR_INTERNAL_USER.id in user.scopes

    # login for this internal user:
    resp = await _api.post(
        "/token",
        json={"username": internal_user_name, "password": internal_user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    token = body['access_token']

    # new login for this internal user with the same password: No first_login constraint
    resp = await _api.post(
        "/token",
        json={"username": internal_user_name, "password": internal_user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    assert token != body['access_token']  # new token
    token = body['access_token']

    user = await _db.get_user_by_name(username=internal_user_name, internal=True, internal_projection=True,
                                               idp_name=DEFAULT_LOCAL_IDP_NAME)
    assert user["internal"], "internal flag should be unchanged"

    # Get me for this user
    headers = {"content-type": "application/json",
               'Authorization': f"Bearer {token}"}
    resp = await _api.get("/user/me", headers=headers)
    assert resp.status == 200
    user = await resp.json()
    assert user, "user should be defined"
    assert User.from_dict(user).username == internal_user_name

    # Check actions for this user
    resp = await _api.get("/user/me/actions", headers=headers)
    assert resp.status == 200
    actions = await resp.json()
    assert any(action["action"] == "lic:check_license" for action in actions)
    assert any(action["action"] == "lic:put_stats" for action in actions)

    # Get all actions
    resp = await _api.get("/actions", headers=_admin_headers)
    assert resp.status == 200
    actions = await resp.json()

    assert all(action["name"] != "lic:check_license" for action in actions), "internal act. shall not be returned"
    assert all(action["name"] != "lic:put_stats" for action in actions), "internal act. shall not be returned"

    # logout
    resp = await _api.delete("/logout", headers=headers)
    assert resp.status == 200


async def test_internal_user_access_by_admin(init_backend_with_admin, init_backend_with_internal_admin):
    """

    Test that internal user could not been updated, disconnected or deleted by admin
    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _, _, _internal_admin_token = init_backend_with_internal_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _internal_admin_headers = {"Authorization": f"Bearer {_internal_admin_token}"}

    internal_user_name = "license_agent"
    internal_user_password = generate_internal_user_password(username=internal_user_name)

    # Create 1 internal user by internal admin
    resp = await _api.post(
        "/users",
        json=[{"username": internal_user_name, "password": internal_user_password}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 201

    # login for this internal user:
    resp = await _api.post(
        "/token",
        json={"username": internal_user_name, "password": internal_user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body
    token = body["access_token"]

    headers = {"content-type": "application/json", 'Authorization': f"Bearer {token}"}

    # fail to create a user with the same name as an internal user by admin
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": internal_user_name,
                "password": DEFAULT_PASSWORD,
                "scopes": ["usr:monitoring"],
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201
    body = await resp.json()
    assert body["errors"] == ["Unable to create user 'license_agent': license_agent already exists"]

    # fail to force disconnection by admin for this internal user
    resp = await _api.delete(
        "/token",
        json={"username": internal_user_name, "idp_name": DEFAULT_LOCAL_IDP_NAME},
        headers=_admin_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body == 'User not found'

    # force disconnection by internal_admin for this internal user
    resp = await _api.delete(
        "/token",
        json={"username": internal_user_name, "idp_name": DEFAULT_LOCAL_IDP_NAME},
        headers=_internal_admin_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    # logout fails because disconnected
    resp = await _api.delete("/logout", headers=headers)
    assert resp.status == 400

    # Create internal scope
    resp = await _api.post(
        "/scopes",
        json=[
            {
                "id": "lic:internal",
                "label": "lic",
                "description": "description",
                "internal": True,
                "content": [{"action": "usr:get_test", "policy": "allow", "resource": {}}],
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 200

    # Update internal user thanks to internal admin creds (deprecated endpoint)
    resp = await _api.patch(
        "/users",
        json=[
            {
                "username": internal_user_name,
                "idp_name": DEFAULT_LOCAL_IDP_NAME,
                "scopes": ["lic:internal"],
            }
        ],
        headers=_internal_admin_headers,
    )
    assert resp.status == 410

    # fail to update this user by name with route /users/{} by admin
    resp = await _api.patch(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{internal_user_name}",
        json={"enabled": False},
        headers=_admin_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body == 'Incorrect username, user not found'

    # Check that the internal user is unchanged
    resp = await _api.get(
        "/users", headers=_internal_admin_headers
    )
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2, "2 internal users should exist"  # 1 user + internal admin
    user = User.from_dict(body[0])
    assert user.username == internal_user_name
    assert user.enabled
    assert "usr:guest" not in user.scopes
    assert "usr:engineer" not in user.scopes

    # fail delete an internal user by route /users by admin
    resp = await _api.delete(
        "/users",
        json=[{"username": internal_user_name, "idp_name": DEFAULT_LOCAL_IDP_NAME}],
        headers=_admin_headers,
    )
    assert resp.status == 409

    # fail delete an internal user by route /users/{username} by admin
    resp = await _api.delete(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{internal_user_name}",
        headers=_admin_headers,
    )
    assert resp.status == 404

    # delete the internal user by internal admin succeeds
    resp = await _api.delete(
        "/users",
        json=[{"username": internal_user_name, "idp_name": DEFAULT_LOCAL_IDP_NAME}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 200


async def test_internal_user_no_password_expiration(
    init_database, init_backend_with_admin, init_backend_with_internal_admin
):
    """

    Test that internal user could not been updated, disconnected or deleted through the /users route
    :return:
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _, _, _internal_admin_token = init_backend_with_internal_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _internal_admin_headers = {"Authorization": f"Bearer {_internal_admin_token}"}

    internal_user_name = "license_agent"
    internal_user_password = generate_internal_user_password(username=internal_user_name)
    other_user_name = "other_user"
    other_user_password = "passwordA0!"

    update_conf_resp = await _api.put("/configuration",
                                      json={"password_policy": {"expiration_delay_in_days": -1}},
                                      headers=_admin_headers)
    assert update_conf_resp.status == 200

    # Create 1 internal user by internal admin
    resp = await _api.post(
        "/users",
        json=[{"username": internal_user_name, "password": internal_user_password}],
        headers=_internal_admin_headers,
    )
    assert resp.status == 201

    # Create 1 non internal user with password expiration
    resp = await _api.post(
        "/users",
        json=[
            {
                "username": other_user_name,
                "password": other_user_password,
                "first_login": False,
            }
        ],
        headers=_admin_headers,
    )
    assert resp.status == 201

    # patch the password_expiration in configuration
    await _api.put("/configuration", json={"password_policy": {"expiration_delay_in_days": 1}},
                   headers=_admin_headers)

    # Update password_last_update for these users to make it expired
    delta = timedelta(days=2)
    password_last_update = datetime.utcnow().timestamp() - delta.total_seconds()
    await _db.update_user_by_name(username=internal_user_name,
                                  internal=True,
                                  password_last_update=password_last_update,
                                  idp_name=DEFAULT_LOCAL_IDP_NAME)

    await _db.update_user_by_name(username=other_user_name,
                                  first_login=False,
                                  password_last_update=password_last_update,
                                  idp_name=DEFAULT_LOCAL_IDP_NAME)

    # login for this internal user succeeds because no password expiration check for internal users
    resp = await _api.post(
        "/token",
        json={"username": internal_user_name, "password": internal_user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert 'access_token' in body

    # login for the other user returns 206 with reason 'password expired'
    resp = await _api.post(
        "/token",
        json={"username": other_user_name, "password": other_user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()
    assert isinstance(body, dict)
    assert body["reason"] == "Password expired"

    # Patch internal flag for the internal user directly in db
    await _db.db[Collections.users.name].update_one({"username": internal_user_name,
                                                          "idp_name": DEFAULT_LOCAL_IDP_NAME},
                                                         {"$set": {"internal": False}})

    # Now, login for this modified internal user fails because password expiration
    resp = await _api.post(
        "/token",
        json={"username": internal_user_name, "password": internal_user_password},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 206
    body = await resp.json()

    assert body["reason"] == "Password expired"
