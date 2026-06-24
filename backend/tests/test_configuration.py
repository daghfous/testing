#pylint: disable=no-member
"""
Test Configuration
"""
import os

from datetime import datetime

import pytest
from pytest_mock.plugin import MockerFixture

from ateme.openapi import OpenApiDefinition

from ateme.um_backend import PasswordPolicy
from ateme.um_backend.types import (
    Configuration,
    User,
    DEFAULT_LOCAL_IDP_NAME
)
from ateme.um_backend.database import Collections, Database
from ateme.um_backend.user_management import UserManagementApi


API_PATH = os.path.join(os.path.dirname(__file__), "definitions", "simple_api.yaml")


@pytest.mark.parametrize(
    "data,failed",
    [pytest.param(
        {'password_policy': {'expiration_delay_in_days': -1},
         'max_successive_failed_login': 3, 'user_deactivation_period': -1,
         'token_expiration': 3600, 'token_cleaning_period': 24},
        False),
     pytest.param(
         {'max_successive_failed_login': 3, 'user_deactivation_period': -1},
         False),
    pytest.param(
     {'password_policy': {'expiration_delay_in_days': -1},
      'max_successive_failed_login': '11', 'user_deactivation_period': -1},
         True),
     pytest.param(
         {'password_policy': {'expiration_delay_in_days': -1},
          'max_successive_failed_login': 3, 'user_deactivation_period': '-2'},
         True),
     pytest.param(
         {'password_policy': {'expiration_delay_in_days': -1},
          'token_expiration': 0, 'max_successive_failed_login': 3,
          'user_deactivation_period': -1},
         True,
         id="token_expiration_lower_than_minimum"), ])
def test_configuration(data: dict, failed):
    """
    Test configuration init and validation
    """
    if 'password_policy' in data:
        password_policy = PasswordPolicy(
            expiration_delay_in_days=data.get('password_policy', {}).get('expiration_delay_in_days', -1)
        )
    else:
        password_policy = PasswordPolicy()
    configuration = Configuration(
        max_successive_failed_login=data['max_successive_failed_login'],
        user_deactivation_period=data['user_deactivation_period'],
        token_expiration=data.get('token_expiration', 3600),
        password_policy=password_policy
    )
    if failed:
        with pytest.raises(Exception):
            configuration.validate()
    else:
        assert configuration.validate()


async def test_initialize(init_database, settings):
    """
    Assert that the existing configuration is not reset
    """
    database = init_database
    api_definition = OpenApiDefinition(API_PATH, full_validation=True)
    password_policy = PasswordPolicy(expiration_delay_in_days=365, password_min_length=20)
    custom_conf = Configuration(user_deactivation_period=10, token_expiration=20, password_policy=password_policy)
    implem = UserManagementApi(Database(database.client, settings.um_database_name), settings,
                               api_definition, configuration=custom_conf)
    await implem.initialize()

    configuration = await implem.db.get_configuration()
    assert configuration.user_deactivation_period == custom_conf.user_deactivation_period
    assert configuration.token_expiration == custom_conf.token_expiration
    assert configuration.password_policy.expiration_delay_in_days == password_policy.expiration_delay_in_days
    assert configuration.password_policy.regex_pattern == PasswordPolicy.get_password_regex_pattern()
    assert configuration.password_policy.password_min_length == password_policy.password_min_length

    implem = UserManagementApi(Database(database.client, settings.um_database_name), settings, api_definition)
    await implem.initialize()

    # Assert that the configuration is exactly the same than before the initialize
    configuration = await implem.db.get_configuration()
    assert configuration.user_deactivation_period == custom_conf.user_deactivation_period
    assert configuration.token_expiration == custom_conf.token_expiration
    assert configuration.password_policy.expiration_delay_in_days == password_policy.expiration_delay_in_days
    assert configuration.password_policy.regex_pattern == PasswordPolicy.get_password_regex_pattern()

async def test_get_conf(init_backend_with_admin):
    """
    test_get_conf
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    get_conf_resp = await _api.get("/configuration", headers=_admin_headers)
    assert get_conf_resp.status == 200
    result = await get_conf_resp.json()

    conf = Configuration.from_dict(result)
    assert conf.validate()

async def test_get_public_configuration(init_backend_with_admin):
    """
    Test get_public_configuration
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    default_logout_timeout = -1
    default_expiration_delay_in_days = -1
    resp = await _api.get("/public/configuration", headers=_admin_headers)
    assert resp.status == 200
    result = await resp.json()
    assert result['logout_timeout'] == default_logout_timeout
    assert result['password_policy']['regex_pattern'] == PasswordPolicy.get_password_regex_pattern()
    assert result['password_policy']['expiration_delay_in_days'] == default_expiration_delay_in_days

    # Update configuration
    expected_logout_timeout_value = 10
    expected_expiration_delay_in_days = 365

    get_conf_resp = await _api.get("/configuration", headers=_admin_headers)
    assert get_conf_resp.status == 200
    body = {'logout_timeout': expected_logout_timeout_value,
            'password_policy': {'expiration_delay_in_days': expected_expiration_delay_in_days}}
    update_conf_resp = await _api.put("/configuration", json=body, headers=_admin_headers)
    assert update_conf_resp.status == 200

    resp = await _api.get("/public/configuration", headers=_admin_headers)
    assert resp.status == 200
    result = await resp.json()
    assert result['logout_timeout'] == expected_logout_timeout_value
    assert result['password_policy']['regex_pattern'] == PasswordPolicy.get_password_regex_pattern()
    assert result['password_policy']['expiration_delay_in_days'] == expected_expiration_delay_in_days


@pytest.mark.asyncio
async def test_enable_user(init_database, init_backend_with_admin):
    """
    test_enable_user
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    # create a user with wrong password
    username = "johnny"
    password = "B.good"
    create_user_resp = await _api.post(
        "/users",
        json=[{"username": username, "password": password}],
        headers=_admin_headers,
    )
    assert create_user_resp.status == 400

    # create a user
    username = "johnny"
    password = "Begooddd!0"
    create_user_resp = await _api.post(
        "/users",
        json=[{"username": username, "password": password}],
        headers=_admin_headers,
    )
    assert create_user_resp.status == 201

    # login should work (user enabled)
    login_resp = await _api.post("/token", json={"username": username, "password": password})
    assert login_resp.status == 206

    # disable the user
    patch_user_resp = await _api.patch(
        f"/users/{DEFAULT_LOCAL_IDP_NAME}/{username}",
        json={"enabled": False},
        headers=_admin_headers,
    )
    assert patch_user_resp.status == 200

    # disable the client
    client_id = User.generate_hash([username, '127.0.0.1'])
    await _db.db[Collections.clients.name].update_one(
        {"client_id": client_id},
        {
            "$inc": {"attempts": 1},
            "$setOnInsert": {"enabled": False},
            "$set": {"last_attempt_date": datetime.now().timestamp()},
        },
        upsert=True,
    )
    # login should fail (user disabled)
    login_resp = await _api.post(
        "/token",
        json={
            "username": username,
            "password": password,
            "idp_name": DEFAULT_LOCAL_IDP_NAME,
        },
    )
    assert login_resp.status == 403


@pytest.mark.parametrize("token_expiration, refresh_token_expiration, status, body_expected", [
    pytest.param(500, 1000, 200, "OK"),
    pytest.param(1000, 500, 400, "token_expiration must be strictly lower to refresh_token_expiration")
])
@pytest.mark.asyncio
async def test_bad_token_expiration_update(
    init_backend_with_admin,
    token_expiration,
    refresh_token_expiration,
    status,
    body_expected,
):
    """

    Check PUT /configuration with `token_expiration` & `refresh_token_expiration` parameters.
    If `token_expiration` is lower than `refresh_token_expiration` raise HTTP Bad Request.
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    body = {'token_expiration': token_expiration, 'refresh_token_expiration': refresh_token_expiration}
    update_conf_resp = await _api.put("/configuration", json=body, headers=_admin_headers)
    assert update_conf_resp.status == status
    assert (await update_conf_resp.text()) == body_expected


# pylint: disable=too-many-arguments,too-many-positional-arguments
@pytest.mark.parametrize("token_expiration, expected_http_code, expected_http_body, update_configuration_mock_called", [
    pytest.param(
        0,
        400,
        {
            'errors': [
                'Failed validating minimum in schema[root]: 0 is less than the minimum of 5'
            ]
        },
        False,
        id="invalid-body-schema"
    ),
    pytest.param(
        5,
        200,
        'Token expiration set to 5 seconds',
        True,
        id="success-update"
    ),
    pytest.param(
        31536000,
        400,
        'token_expiration must be strictly lower to refresh_token_expiration',
        False,
        id="lower-value-failed"
    )
])
async def test_tokenexp_endpoint(
    init_backend_with_admin,
    token_expiration: int,
    expected_http_code: int,
    expected_http_body: str | dict,
    update_configuration_mock_called: bool,
    mocker: MockerFixture,
):
    """

    Check POST /tokenexp endpoint, this endpoint "patch" configuration object
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    update_configuration_mock = mocker.patch(
        "ateme.um_backend.database.Database.update_configuration"
    )
    update_tokenexp_resp = await _api.post("/tokenexp", json=token_expiration, headers=_admin_headers)
    assert update_tokenexp_resp.status == expected_http_code
    body = (
        (await update_tokenexp_resp.json())
        if update_tokenexp_resp.headers["Content-Type"] == "application/json"
        else (await update_tokenexp_resp.text())
    )
    assert body == expected_http_body
    assert update_configuration_mock.called == update_configuration_mock_called
