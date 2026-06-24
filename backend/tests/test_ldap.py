# pylint: disable=no-member, too-many-lines
"""

test ldap server
"""
import time
import os
import logging
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import pytest
from pymongo.collection import DeleteResult, InsertOneResult, UpdateResult
import ldap

from ateme.encryption_lib import AESCipher  # pylint: disable=no-name-in-module
from ateme.um_backend.types import (
    LdapConfig,
    IdpType,
)
from ateme.um_backend.ldap import LdapClient, LdapSearchResult
from ateme.um_backend.ldap_provider import LdapProvider
from ateme.um_backend.database import Collections
from ateme.um_backend.user_management import UserManagementApi

# Skip ldap test if we haven't access to ATEME_HUB_RELEASE_USR password (via var env)
# TODO find a better way to use hub ldap user mail.
ATEME_HUB_RELEASE_USR = os.environ.get('ATEME_HUB_RELEASE_USR', '') + "@ateme.com"
ATEME_HUB_RELEASE_PWD = os.environ.get('ATEME_HUB_RELEASE_PWD', '')
SKIP_LDAP_TEST = (os.environ.get('ATEME_HUB_RELEASE_PWD', '') == '') \
    or (os.environ.get('ATEME_HUB_RELEASE_USR', '') == '')

IDP_NAME = "ldap_ateme.com"
IDP_LABEL = "LDAP ateme.com"
IDP_SERVER = "atm-infra.corp.ateme.com"
IDP_DOMAIN = "ateme.com"
IDP_BASE_DN = "CN=Users,DC=corp,DC=ateme,DC=com"
IDP_GROUP = "S_SUPPORT"
SEARCH_FILTER = "(objectClass=person)"

LDAP_CONFIG = {
    "idp_name": IDP_NAME,
    "idp_type": IdpType.ldap.name,
    "idp_label": IDP_LABEL,
    "server": IDP_SERVER,
    "domain": IDP_DOMAIN,
    "search": IDP_BASE_DN,
    "group": IDP_GROUP,
    "use_ssl": True,
    "scopes": ["all:guest"],
    "deny_access": False,
}
IDP_LDAP_CONFIG = LdapConfig(idp_type=IdpType.ldap.name,
                             idp_name=IDP_NAME,
                             idp_label=IDP_LABEL,
                             domain=IDP_DOMAIN,
                             server='atm-infra.corp.ateme.com',
                             search='CN=Users,DC=corp,DC=ateme,DC=com',
                             group='S_SUPPORT')

@pytest.mark.skip(reason='Unskip this test, if you want to test LDAP functions locally')
def test_ldap_tls_bind_simple_admin(init_ldap_server):
    """
    Test LDAP bind locally with a running container
    Args:
        init_ldap_server (fixture)
    Remarks:
        Unskip this test, if you want to test LDAP functions locally
        Make sure that the image osixia/openldap:1.5.0 from nexus
        is available on your machine
    """
    _, server, config = init_ldap_server
    conn = server.bind(config["admin"]["username"],
                       config["admin"]["password"])
    assert conn

@pytest.mark.skip(reason='Unskip this test, if you want to test LDAP functions locally')
def test_ldap_tls_bind_simple_user(init_ldap_server_with_user):
    """
    Test LDAP bind user locally with a running container
    Args:
        init_ldap_server_with_user (fixture)
    Remarks:
        Unskip this test, if you want to test LDAP locally
        Make sure that the image osixia/openldap:1.5.0 from nexus
        is available on your machine
    """
    _, server, config = init_ldap_server_with_user
    conn = server.bind(config["user"]["username"],
                       config["user"]["password"])
    assert conn

def test_ldap_search_without_filter():
    """
    Test ldap search without search_filter
    """
    client = LdapClient({})
    result = client.search(connection=None, attributes=["uid", "mail"], search_base="", search_filter="")
    assert not result

async def _check_if_data_present_ldap_cache(db, idp_name: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ldap_cache_data = await db.get_ldap_cache_by_idp_name(idp_name=idp_name)
        if ldap_cache_data:
            return True
        await asyncio.sleep(1)
    return False

@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
@pytest.mark.parametrize("server, user, user_filter, status_code, response_text, search_filter", [
    pytest.param(IDP_SERVER, ATEME_HUB_RELEASE_USR, None, 200,
                 "Ok - Valid LDAP config", SEARCH_FILTER, id="ok_without_user_filter"),
    pytest.param(IDP_SERVER, ATEME_HUB_RELEASE_USR, "mail", 200, "Ok - Valid LDAP config", SEARCH_FILTER,
                 id="ok_valid_user"),
    pytest.param(IDP_SERVER, ATEME_HUB_RELEASE_USR.split("@")[0], "mail",
                 200, "Ok - Valid LDAP config", SEARCH_FILTER, id="ok_valid_user_without_domain"),
    pytest.param(IDP_SERVER, "invalid_user", "mail", 406, "Invalid credentials", SEARCH_FILTER,
                 id="ko_invalid_user"),
    pytest.param("invalid_server", ATEME_HUB_RELEASE_USR, "mail", 406, "Can\'t contact LDAP server",
                 SEARCH_FILTER,
                 id="ko_invalid_server"),
    pytest.param(IDP_SERVER, ATEME_HUB_RELEASE_USR, "mail", 200, "Ok - Valid LDAP config", "",
                 id="ok_without_search_filter"),
])
async def test_validate_ldap(init_backend_with_admin, server, user, user_filter, status_code,
                             response_text, search_filter):
    """
    Test the idp ldap config validation (bind or bind+search if user_filter is set)
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    ldap_config = {
        "idp_name": IDP_NAME,
        "idp_type": IdpType.ldap.name,
        "idp_label": IDP_LABEL,
        "server": server,
        "domain": IDP_DOMAIN,
        "search": IDP_BASE_DN,
        "search_filter": search_filter,
        "group": IDP_GROUP,
        "use_ssl": True,
        "username": user,
        "password": ATEME_HUB_RELEASE_PWD
    }
    if user_filter:
        ldap_config["user_filter"] = user_filter
    validate_resp = await _api.post(
        "/idpconfigs/validate",
        json=ldap_config,
        headers=_admin_headers,
    )
    assert validate_resp.status == status_code
    assert response_text in (await validate_resp.text())

@pytest.mark.parametrize("bind_side_effect,search_side_effect,expected_bind_exception, expected_search_exception", [
    pytest.param((MagicMock(), True), MagicMock(), None, None,
                 id="ok"),
    pytest.param(ldap.LDAPError("bind failed"), None, ldap.LDAPError, None,
                 id="bind_internal_exception"),
    pytest.param((MagicMock(), True), Exception("search failed"), None, Exception("search failed"),
                 id="search_internal_exception"),
])
async def test_validate_error_cases(bind_side_effect, expected_bind_exception, search_side_effect,
                                    expected_search_exception):
    """
    Test the idp ldap config validation error cases
    """
    provider = LdapProvider(db=MagicMock(), executor=MagicMock())
    provider._executor = MagicMock()  # pylint: disable=protected-access
    loop = MagicMock()

    with patch('ateme.um_backend.ldap_provider.LdapConfig.from_dict') as mock_from_dict:
        mock_config = MagicMock()
        mock_config.idp_name = "test_idp"
        mock_config.search = "base_dn"
        mock_config.user_filter = "user"
        mock_config.search_filter = "filter"
        mock_from_dict.return_value = mock_config

        # set the side effects for the 2 subsequent calls of loop.run_in_executor
        # 1 for bind and then 1 for search
        loop.run_in_executor = AsyncMock(side_effect=[bind_side_effect, search_side_effect])

        if not expected_bind_exception and not expected_search_exception:
            result = await provider.validate_idp_config("user", "pwd", {}, False, loop)
            assert result
        elif expected_bind_exception:
            with pytest.raises(expected_bind_exception):
                await provider.validate_idp_config("user", "pwd", {}, False, loop)
        elif expected_search_exception:
            with pytest.raises(expected_search_exception.__class__):
                await provider.validate_idp_config("user", "pwd", {}, False, loop)

async def test_ldap_configs(init_backend_with_admin, init_database):
    """

    :return:
    """
    # pylint: disable=too-many-locals, too-many-statements
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # create ldap config
    create_idp_resp = await _api.post("/idpconfigs", json={'idp_name': IDP_NAME,
                                              'idp_type': IdpType.ldap.name,
                                              'idp_label': IDP_LABEL,
                                              'server': 'atm-infra.corp.ateme.com',
                                              'domain': IDP_DOMAIN,
                                              'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
                                              'group': 'S_SUPPORT',
                                              'use_ssl': True,
                                              'bind_dn': 'username',
                                              'bind_password': 'password'
                                              }, headers=_admin_headers)
    assert create_idp_resp.status == 201
    assert (await create_idp_resp.text()) == "OK"
    # check ldap config persist
    get_idp_resp = await _api.get(f"/idpconfigs/{IDP_NAME}", headers=_admin_headers)
    assert get_idp_resp.status == 200
    ldap_config = await get_idp_resp.json()
    assert ldap_config
    assert ldap_config["use_ssl"]
    assert ldap_config["idp_name"] == IDP_NAME
    assert ldap_config["idp_type"] == IdpType.ldap.name
    assert ldap_config["group"] == 'S_SUPPORT'
    assert ldap_config["search"] == 'CN=Users,DC=corp,DC=ateme,DC=com'
    assert ldap_config["server"] == 'atm-infra.corp.ateme.com'
    # Assert that default value has been set
    assert ldap_config['deny_access']
    # Assert that real bind_password is not returned and has been replaced by an empty string
    assert ldap_config['bind_password'] == ''

    # the password in db has been encrypted
    ldap_config_in_db = await _db.db[Collections.idp_config.name].find({"idp_name": IDP_NAME}).to_list(None)
    aes_cipher = AESCipher()
    assert aes_cipher.encrypt('password') == ldap_config_in_db[0]['bind_password']

    get_all_idps_resp = await _api.get("/idpconfigs", headers=_admin_headers)
    assert get_all_idps_resp.status == 200
    all_configs = await get_all_idps_resp.json()

    assert all_configs[1]["idp_name"] == IDP_NAME

    for bind_dn, bind_password in [(None, None), ('', ''), ('user', 'pwd')]:
        # patch ldap config
        patch_idp_by_name_resp = await _api.patch(f"/idpconfigs/{IDP_NAME}", json={'idp_type': IdpType.ldap.name,
                                                  'idp_label': IDP_LABEL,
                                                  'server': 'ecorp.ateme.com',
                                                  'search': 'CN=Users,DC=evilcorp',
                                                  'group': 'BOSS',
                                                  'bind_dn': bind_dn,
                                                  'bind_password': bind_password,
                                                  'use_ssl': False}, headers=_admin_headers)
        assert patch_idp_by_name_resp.status == 200
        assert (await patch_idp_by_name_resp.text()) == "ldap idp_config ldap_ateme.com updated"

        # check ldap config persist
        get_idp_config = await _api.get(f"/idpconfigs/{IDP_NAME}", headers=_admin_headers)
        assert get_idp_config.status == 200
        ldap_config = await get_idp_config.json()
        assert ldap_config
        assert not ldap_config["use_ssl"]
        assert ldap_config["group"] == 'BOSS'
        assert ldap_config["search"] == 'CN=Users,DC=evilcorp'
        assert ldap_config["server"] == 'ecorp.ateme.com'
        # bind_dn has been reset
        assert ldap_config["bind_dn"] == bind_dn
        # the password in db has been encrypted
        ldap_config_in_db = await _db.db[Collections.idp_config.name].find({"idp_name": IDP_NAME}).to_list(None)
        if bind_password is not None:
            assert aes_cipher.encrypt(bind_password) == ldap_config_in_db[0]['bind_password']
        else:
            assert bind_password == ldap_config_in_db[0]['bind_password']

    # try to patch ldap config with invalid body: fields from both ldap_config and saml_config definitions
    patch_failed_resp = await _api.patch(
        f"/idpconfigs/{IDP_NAME}",
        json={"idp_type": IdpType.ldap.name, "group": "BOSS", "sign_logout_request": False},
        headers=_admin_headers,
    )
    assert patch_failed_resp.status == 400
    assert (await patch_failed_resp.json()) == {
        "errors": [
            "Failed validating discriminator in schema[root]: "
            "Additional properties are not allowed ('sign_logout_request' was unexpected)"
        ]
    }

    # try to patch ldap config with invalid body: unknown property
    patch_failed_resp = await _api.patch(f"/idpconfigs/{IDP_NAME}", json={"grou": "BOSS"}, headers=_admin_headers)
    assert patch_failed_resp.status == 400
    assert (await patch_failed_resp.json()) == {
        "errors": ["Failed validating discriminator in schema[root]: Property idp_type not found for discriminating"]
    }

    # delete ldap config
    delete_idp_config_resp = await _api.delete(f"/idpconfigs/{IDP_NAME}", headers=_admin_headers)
    assert delete_idp_config_resp.status == 200
    assert (await delete_idp_config_resp.text()) == "ldap idp_config ldap_ateme.com and users to this config removed"


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_ldap_authentication(init_backend_with_admin, mocker):
    """

    :return:
    """
    # pylint: disable=protected-access
    _api, _api_backend, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    # Create a ldap user: not allowed thanks to the API
    resp = await _api.post(
        "/users",
        json=[{"username": ATEME_HUB_RELEASE_USR, "idp_name": IDP_NAME}],
        headers=_admin_headers,
    )
    assert resp.status == 400
    # call directly the backend to create this user (as this user is requested during this test)
    await _api_backend._add_user({"username": ATEME_HUB_RELEASE_USR, "idp_name": IDP_NAME}, internal=False)

    # Initialization of LDAP authentication missing parameters
    resp = await _api.post(
        "/idpconfigs",
        json={"server": "0.0.0.0", "domain": IDP_DOMAIN},
        headers=_admin_headers,
    )
    assert resp.status == 400

    # Initialization of LDAP authentication
    resp = await _api.post(
        "/idpconfigs",
        json=LDAP_CONFIG,
        headers=_admin_headers,
    )
    assert resp.status == 201
    # Fail Login to LDAP with bad password
    resp = await _api.post(
        "/token",
        json={
            "username": ATEME_HUB_RELEASE_USR,
            "password": "invalid",
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    body = await resp.text()
    assert resp.status == 401
    body = await resp.text()
    assert body == "Invalid username or password"

    # Fail Login with bad LDAP domain
    invalid_idp_name = 'ldap_example.com'
    resp = await _api.post(
        "/token",
        json={
            "username": ATEME_HUB_RELEASE_USR,
            "password": ATEME_HUB_RELEASE_PWD,
            "idp_name": invalid_idp_name,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == 500
    body = await resp.text()
    assert body == f"Can't find an identity provider configured with this name {invalid_idp_name}"

    # Login with LDAP
    resp = await _api.post(
        "/token",
        json={
            "username": ATEME_HUB_RELEASE_USR,
            "password": ATEME_HUB_RELEASE_PWD,
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
    body = await resp.json()

    assert isinstance(body, dict)
    assert 'access_token' in body

    token = body["access_token"]

    headers = {"content-type": "application/json", 'Authorization': f"Bearer {token}"}

    # user me
    resp = await _api.get("/user/me", headers=headers)
    assert resp.status == 200
    body = await resp.json()
    # first_login must be set to False for a ldap user
    assert not body['first_login']

    # Logout
    resp = await _api.delete("/logout", headers=headers)
    assert resp.status == 200

    # Login with LDAP full username (with ldap domain)
    resp = await _api.post(
        "/token",
        json={
            "username": ATEME_HUB_RELEASE_USR,
            "password": ATEME_HUB_RELEASE_PWD,
            "ipd_type": IdpType.ldap.name,
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200
    body = await resp.json()

    assert isinstance(body, dict)
    assert 'access_token' in body

    token = body["access_token"]

    headers = {"content-type": "application/json", 'Authorization': f"Bearer {token}"}

    # Logout
    resp = await _api.delete("/logout", headers=headers)
    assert resp.status == 200

    # Login with LDAP full username and wrong password
    resp = await _api.post(
        "/token",
        json={
            "username": ATEME_HUB_RELEASE_USR,
            "password": "wrong password",
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == 401

    # Login with LDAP wrong username
    resp = await _api.post(
        "/token",
        json={"username": "hap", "password": "@a.V?@`B\\", "idp_name": IDP_NAME},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 401

    # Test Login with LDAP Exception case
    async def mock_ldap_bind(username: str, password: str):
        raise ldap.LDAPError
    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", mock_ldap_bind)

    resp = await _api.post(
        "/token",
        json={
            "username": ATEME_HUB_RELEASE_USR,
            "password": ATEME_HUB_RELEASE_PWD,
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == 500


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_store_ldap_config(init_backend_with_admin, mocker):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    # Success case
    data = IDP_LDAP_CONFIG.to_dict()
    resp = await _api.post("/idpconfigs", json=data, headers=_admin_headers)
    assert resp.status == 201

    # Fail case - Need group & search attrs
    data_fail = {"idp_name": "infra.com", "idp_type": IdpType.ldap.name, "idp_label": "infra.com",
                 "server": "infra.com", "domain": "infra.com"}
    resp = await _api.post("/idpconfigs", json=data_fail, headers=_admin_headers)
    assert resp.status == 400
    body = await resp.json()
    assert body == {'errors': ["Failed validating discriminator in schema[root]: 'search' is a required property"]}

    # Retry case, should fail !
    data = IDP_LDAP_CONFIG.to_dict()
    resp = await _api.post("/idpconfigs", json=data, headers=_admin_headers)
    assert resp.status == 409
    body = await resp.text()
    assert body == f"Can't store IDP config, entry with name {data['idp_name']} already exists."

    # Can't store token DB in trouble
    mocker.patch("ateme.um_backend.database.Database.store_idp_config",
                 return_value=InsertOneResult(inserted_id="None", acknowledged=False))

    ldapconfig = LdapConfig(idp_type=IdpType.ldap.name,
                            idp_label='ldap_balls.com',
                            idp_name='ldap_balls.com',
                            domain='balls.com',
                            server='atm-infra.corp.balls.com',
                            search='CN=Users,DC=corp,DC=balls,DC=com',
                            group='S_SUPPORT').to_dict()
    resp = await _api.post("/idpconfigs", json=ldapconfig, headers=_admin_headers)
    assert resp.status == 500
    body = await resp.text()
    assert body == "Can't store ldap config"
    mocker.stopall()

    # Can't store token exception
    mocker.patch("ateme.um_backend.database.Database.store_idp_config", side_effect=Exception("Bad ass exception"))
    resp = await _api.post("/idpconfigs", json=ldapconfig, headers=_admin_headers)
    assert resp.status == 500
    body = await resp.text()
    assert body == "Can't store ldap config"
    mocker.stopall()


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_get_ldap_configs(init_backend_with_admin):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    data = IDP_LDAP_CONFIG.to_dict()
    resp = await _api.post("/idpconfigs", json=data, headers=_admin_headers)
    assert resp.status == 201

    resp = await _api.get("/idpconfigs", headers=_admin_headers)
    assert resp.status == 200
    all_configs = await resp.json()
    assert all_configs, "result from get /idpconfigs should be defined"
    assert isinstance(all_configs, list), "http resp should be a list"
    assert len(all_configs) == 2, "result from get /idpconfigs should return an array of length == 2"
    ldap_configs = [LdapConfig.from_dict(config)
                    for config in all_configs if config["idp_type"] == IdpType.ldap.name]
    assert ldap_configs[0] == IDP_LDAP_CONFIG


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_get_ldap_config_by_domain(init_backend_with_admin):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    data = IDP_LDAP_CONFIG.to_dict()
    resp = await _api.post("/idpconfigs", json=data, headers=_admin_headers)
    assert resp.status == 201

    # Found case
    resp = await _api.get(f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}", headers=_admin_headers)
    assert resp.status == 200
    ldap_config = await resp.json()
    assert ldap_config, "result from get /idpconfigs/{} should be define"
    assert ldap_config == IDP_LDAP_CONFIG.to_dict()

    # Not found case
    resp = await _api.get("/idpconfigs/random_config", headers=_admin_headers)
    assert resp.status == 404
    body = await resp.text()
    assert body == "Not Found"


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_update_ldap_config(init_backend_with_admin, mocker):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    data = IDP_LDAP_CONFIG.to_dict()
    resp = await _api.post("/idpconfigs", json=data, headers=_admin_headers)
    assert resp.status == 201

    new_domain = "new_domain.com"
    new_label = "new_label"
    new_server = "example.com"
    new_group = "boss"
    new_search = "CN=Test,OU=jsaisap"
    resp = await _api.patch(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        json={
            "idp_type": IdpType.ldap.name,
            "domain": new_domain,
            "idp_label": new_label,
            "server": new_server,
            "group": new_group,
            "search": new_search,
        },
        headers=_admin_headers,
    )
    assert resp.status == 200
    res = await resp.text()
    assert res
    resp = await _api.get(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    assert body, "result from get /idpconfigs/{} should be define"
    ldap_config = LdapConfig.from_dict(body)
    # domain is updatable
    assert ldap_config.domain == new_domain
    assert ldap_config.idp_label == new_label
    assert ldap_config.group == new_group
    assert ldap_config.server == new_server
    assert ldap_config.search == new_search

    # Can't update ldap_config DB in trouble
    mocker.patch("ateme.um_backend.database.Database.update_idp_config",
                 return_value=UpdateResult(None, acknowledged=False))
    resp = await _api.patch(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        json={
            "idp_type": IdpType.ldap.name,
            "idp_label": new_label,
            "server": new_server,
            "group": new_group,
            "search": new_search,
        },
        headers=_admin_headers,
    )
    assert resp.status == 500
    res = await resp.text()
    assert res == f"Error occurred during update ldap idp_config {IDP_LDAP_CONFIG.idp_name}"
    mocker.stopall()


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_remove_ldap_config(init_backend_with_admin, mocker):
    """

    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    data = IDP_LDAP_CONFIG.to_dict()
    resp = await _api.post("/idpconfigs", json=data, headers=_admin_headers)
    assert resp.status == 201

    resp = await _api.delete(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    body = await resp.text()
    assert body
    resp = await _api.get(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        headers=_admin_headers,
    )
    assert resp.status == 404
    body = await resp.text()
    assert body == "Not Found"

    # Can't remove ldap_config DB in trouble not acknowledged
    mocker.patch("ateme.um_backend.database.Database.remove_idp_config",
                 return_value=DeleteResult(None, acknowledged=False))
    resp = await _api.delete(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        headers=_admin_headers,
    )
    assert resp.status == 500
    body = await resp.text()
    assert body == f"Error occurred during remove ldap idp_config {IDP_LDAP_CONFIG.idp_name}"
    mocker.stopall()

    # Can't remove ldap_config DB in trouble deleted_count = 0
    mocker.patch("ateme.um_backend.database.Database.remove_idp_config",
                 return_value=DeleteResult(raw_result={'n': 0}, acknowledged=True))
    resp = await _api.delete(
        f"/idpconfigs/{IDP_LDAP_CONFIG.idp_name}",
        headers=_admin_headers,
    )
    assert resp.status == 404
    res = await resp.text()
    assert res == f"Error occurred during remove ldap idp_config {IDP_LDAP_CONFIG.idp_name}"
    mocker.stopall()


@pytest.mark.parametrize("fake_bind_return_value, status_code", [
    (None, 200),
    (Exception("bind exception"), 500)
])
async def test_automatically_add_user(init_backend_with_admin, mocker, fake_bind_return_value, status_code):
    # pylint: disable=too-many-locals
    """
    Check if the automatically add user flag
    in ldap configuration api works
    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    user_login = {"username": "testlogin", "password": "adminA0!"}

    ldap_config_req = LdapConfig.from_dict(LDAP_CONFIG)

    # Create ldap config with automatically add user set by True
    resp = await _api.post(
        "/idpconfigs", json=ldap_config_req.to_dict(), headers=_admin_headers
    )
    assert resp.status == 201

    # Retrieve LDAP Configuration and check params
    resp = await _api.get(
        f"/idpconfigs/{IDP_NAME}",
        headers=_admin_headers
    )
    assert resp.status == 200
    ldap_config = await resp.json()
    ldap_config_rsp = LdapConfig.from_dict(ldap_config)
    # Check equals rsp and request
    assert ldap_config_rsp == ldap_config_req

    # Mock bind
    if isinstance(fake_bind_return_value, Exception):
        async def mock_ldap_bind(username: str, password: str):
            raise fake_bind_return_value
        mocker.patch.object(LdapClient, "bind", mock_ldap_bind)
    else:
        mocker.patch.object(LdapClient, "bind", return_value=fake_bind_return_value)

    # Ldap login using automatically add user flag
    resp = await _api.post(
        "/token",
        json={
            "username": user_login["username"],
            "password": user_login["password"],
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == status_code
    if status_code == 200:
        body = await resp.json()
        token = body['access_token']
        headers = {}
        headers['Authorization'] = f"Bearer {token}"

        # Check token validity with query /user/me/actions and users scopes and object
        resp = await _api.get("/user/me/actions", headers=headers)
        assert resp.status == 200
        body = await resp.json()
        # Check if user is created and in DB
        resp = await _api.get("/users", headers=_admin_headers)
        assert resp.status == 200
        users = await resp.json()
        user = [user for user in users if user["username"] == user_login["username"]]
        assert user, "user should be defined"
        assert len(user) == 1, "Only one user with this name should exist"
        user = user[0]
        assert isinstance(user, dict), "user should be type of dict"
        assert user.get('scopes') == ['all:guest']
        assert user.get('idp_name') == IDP_NAME

    # Stop mocker
    mocker.stopall()


async def test_ldap_config_delete_users(init_backend_with_admin, mocker):
    """
    Check if every user attached to a
    ldap configuration is deleted as well
    when ldap configuration is deleted
    :return:
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    user_login = {"username": "testloginn", "password": "adminA0!"}

    # Create ldap config with automatically add user set by True
    resp = await _api.post(
        "/idpconfigs",
        json=LDAP_CONFIG,
        headers=_admin_headers,
    )
    assert resp.status == 201

    # Mock bind
    mocker.patch.object(LdapClient, "bind", return_value=None)

    # Add user to this domain
    resp = await _api.post(
        "/token",
        json={
            "username": user_login["username"],
            "password": user_login["password"],
            "idp_name": IDP_NAME,
        },
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200

    # Check if user is created and in DB
    resp = await _api.get("/users", headers=_admin_headers)
    assert resp.status == 200
    users = await resp.json()
    user = [user for user in users if user["username"] == user_login["username"]]
    assert user, "user should be defined"
    assert len(user) == 1, "Only one user with this name should exist"
    user = user[0]
    assert isinstance(user, dict), "user should be type of dict"
    assert user.get('scopes') == ['all:guest']
    assert user.get('idp_name') == IDP_NAME

    # Delete LDAP Configuration
    resp = await _api.delete(
        f"/idpconfigs/{IDP_NAME}",
        headers=_admin_headers
    )
    assert resp.status == 200

    # Check that the user is no more present in the user list from DB
    resp = await _api.get("/users", headers=_admin_headers)
    assert resp.status == 200
    users = await resp.json()
    user = [user for user in users if user["username"] == user_login["username"]]
    assert len(user) == 0, "User with this name should not exist"

    # Stop mocker
    mocker.stopall()


@pytest.mark.parametrize("with_bind_dn", [True, False])
@pytest.mark.parametrize("deny_access", [True, False])
@pytest.mark.parametrize("mappers", [
    [
        {'type': 'simple',
         'attributes': [{'name': 'memberof', 'value': "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com"}],
         'scopes_to_add': ['usr:administrator']}
    ],
    [
        {'type': 'simple',
         'attributes': [{'name': 'memberof', 'value': "CN=FAKE_GROUP,OU=Groups_Mails,DC=corp,DC=ateme,DC=com"}],
         'scopes_to_add': ['usr:administrator']}
    ],
    []
])
async def test_ldap_login_with_mappers(init_backend_with_admin, mocker, with_bind_dn, deny_access, mappers):
    """
    Test if when updating ldap config it updates the scopes for the config and for all the users attached to this config
    :return:
    """
    # pylint: disable=too-many-locals
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", return_value=None)
    mocker.patch("ateme.um_backend.ldap.LdapClient.search", return_value=[
        LdapSearchResult(
            dn="CN=Account SSO HUB,CN=Users,DC=corp,DC=ateme,DC=com",
            attributes={
                "memberOf": [
                    "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com",
                    "CN=RODC_PWD-USERS_RENNES,CN=Users,DC=corp,DC=ateme,DC=com",
                    "CN=Allowed RODC Password Replication Group,CN=Users,DC=corp,DC=ateme,DC=com"
                ]
            }
        )
    ])

    user_mail = "hub.ldap@ateme.com"
    user_password = "password"
    idp_name = "mapper_ateme.com"
    # Post LDAP conf
    scopes_to_add = ['all:guest']
    if mappers:
        scopes_to_add = mappers[0]['scopes_to_add']
    ldap_config = {"idp_name": idp_name,
                   'idp_type': IdpType.ldap.name,
                   'idp_label': IDP_LABEL,
                   'server': 'atm-infra.corp.ateme.com',
                   'domain': IDP_DOMAIN,
                   'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
                   'group': 'S_SUPPORT',
                   'user_filter': 'mail',
                   'mappers': mappers,
                   'deny_access': deny_access
                   }
    if with_bind_dn:
        ldap_config['bind_dn'] = user_mail
        ldap_config['bind_password'] = user_password
    resp = await _api.post("/idpconfigs", json=ldap_config, headers=_admin_headers)
    assert resp.status == 201

    # Login with LDAP
    status_code = 200
    if deny_access and not mappers:
        status_code = 403
    resp = await _api.post(
        "/token",
        json={"username": user_mail, "password": user_password, "idp_name": idp_name},
        headers={"content-type": "application/json"},
    )
    assert resp.status == status_code

    # Check if user is created with correct scopes
    if not deny_access:
        resp = await _api.get(
            f"/users/{idp_name}/{user_mail}",
            headers=_admin_headers,
        )
        assert resp.status == 200
        user = await resp.json()
        if mappers and 'FAKE_GROUP' in mappers[0]['attributes'][0]['value']:
            scopes_to_add = ['all:guest']

        assert user['scopes'] == scopes_to_add

    # Update mappers
    new_scopes = ['usr:engineer']
    ldap_config['mappers'] = [
        {'type': 'simple',
         'attributes': [{'name': 'memberof', 'value': "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com"}],
         'scopes_to_add': new_scopes}
    ]
    resp = await _api.patch(
        f"/idpconfigs/{idp_name}",
        json=ldap_config,
        headers=_admin_headers,
    )
    assert resp.status == 200

    # Login with LDAP
    resp = await _api.post(
        "/token",
        json={"username": user_mail, "password": user_password, "idp_name": idp_name},
        headers={"content-type": "application/json"},
    )
    assert resp.status == 200

    # Check if user is created with correct scopes
    if not deny_access:
        resp = await _api.get(
            f"/users/{idp_name}/{user_mail}",
            headers=_admin_headers,
        )
        assert resp.status == 200
        user = await resp.json()
        assert user['scopes'] == new_scopes
        assert user['scopes'] == new_scopes


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
async def test_ldap_cache_data_patching_config(init_database, init_backend_with_admin):
    """
    :return:
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    user_filter = 'mail'
    idp_name = "ldap-cache-test"
    # create ldap config with bind dn, bind password and user filter (mandatory)
    resp = await _api.post(
        "/idpconfigs",
        json={
            "idp_name": idp_name,
            "idp_type": IdpType.ldap.name,
            "idp_label": IDP_LABEL,
            "domain": IDP_DOMAIN,
            "server": IDP_SERVER,
            "search": IDP_BASE_DN,
            "group": IDP_GROUP,
            "use_ssl": True,
        },
        headers=_admin_headers,
    )
    assert resp.status == 201

    # patch ldap config with bind dn, bind password and user filter (mandatory)
    resp = await _api.patch(
        f"/idpconfigs/{idp_name}",
        json={
            "idp_type": IdpType.ldap.name,
            "idp_label": IDP_LABEL,
            "domain": IDP_DOMAIN,
            "server": IDP_SERVER,
            "search": IDP_BASE_DN,
            "group": IDP_GROUP,
            "bind_dn": ATEME_HUB_RELEASE_USR,
            "bind_password": ATEME_HUB_RELEASE_PWD,
            "user_filter": user_filter,
        },
        headers=_admin_headers,
    )
    assert resp.status == 200

    # After the bind dn is configured, a background task needs to be
    # launched to insert data in 'ldap_cache' collection
    # Once patched the configuration with bind
    # wait some time till the data is updated
    assert True is await _check_if_data_present_ldap_cache(_db, idp_name=idp_name, timeout=60)
    # Test the aggregate function
    find_user_in_ldap_cache = await _db.find_user_in_ldap_cache(
        username=ATEME_HUB_RELEASE_USR, user_filter=user_filter, idp_name=idp_name
    )
    assert find_user_in_ldap_cache
    assert idp_name == find_user_in_ldap_cache['idp_name']


@pytest.mark.skipif(SKIP_LDAP_TEST, reason='ATEME_HUB_RELEASE_USR password available only in ci context')
@pytest.mark.parametrize("with_cache", [
    False,
    True
])
async def test_validate_ldap_with_and_without_cache(init_database, init_backend_with_admin, with_cache):
    """
    Test the idp ldap config validation
    """
    _db = init_database
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    user_filter = 'mail'
    idp_name = "ldap-cache-test"
    if with_cache:
        # create ldap config with bind dn, bind password and user filter (mandatory) (force ldap cache)
        resp = await _api.post(
            "/idpconfigs",
            json={
                "idp_name": idp_name,
                "idp_type": IdpType.ldap.name,
                "idp_label": IDP_LABEL,
                "server": IDP_SERVER,
                "domain": IDP_DOMAIN,
                "search":IDP_BASE_DN,
                "group": IDP_GROUP,
                "use_ssl": True,
                "bind_dn": ATEME_HUB_RELEASE_USR,
                "bind_password": ATEME_HUB_RELEASE_PWD,
                "user_filter": user_filter,
            },
            headers=_admin_headers,
        )
        assert resp.status == 201
        # After the bind dn is configured, a background task needs to be
        # launched to insert data in 'ldap_cache' collection
        # wait some time till the data is updated
        assert True is await _check_if_data_present_ldap_cache(_db, idp_name=idp_name, timeout=60)
        # validate the configuration
        resp = await _api.post(
            "/idpconfigs/validate",
            json={
                "idp_name": idp_name,
                "idp_type": IdpType.ldap.name,
                "idp_label": IDP_LABEL,
                "server": IDP_SERVER,
                "domain": IDP_DOMAIN,
                "search": IDP_BASE_DN,
                "group": IDP_GROUP,
                "use_ssl": True,
                "bind_dn": ATEME_HUB_RELEASE_USR,
                "bind_password": ATEME_HUB_RELEASE_PWD,
                "user_filter": user_filter,
                "username": ATEME_HUB_RELEASE_USR,
                "password": ATEME_HUB_RELEASE_PWD,
            },
            headers=_admin_headers,
        )
        assert resp.status == 200
    else:
        # Without cache, we perform an ldap search manually and retrieve the bind dn
        # validate the configuration
        resp = await _api.post(
            "/idpconfigs/validate",
            json={
                "idp_name": idp_name,
                "idp_type": IdpType.ldap.name,
                "idp_label": IDP_LABEL,
                "server": IDP_SERVER,
                "domain": IDP_DOMAIN,
                "search": IDP_BASE_DN,
                "group": IDP_GROUP,
                "use_ssl": True,
                "bind_dn": ATEME_HUB_RELEASE_USR,
                "bind_password": ATEME_HUB_RELEASE_PWD,
                "user_filter": user_filter,
                "username": ATEME_HUB_RELEASE_USR,
                "password": ATEME_HUB_RELEASE_PWD,
            },
            headers=_admin_headers,
        )
        assert resp.status == 200

@pytest.mark.asyncio
async def test_sync_ldap_cache_with_safe_upsert(caplog):
    """"
    Test the _sync_ldap_cache method with safe upsert logic."""
    # pylint: disable=protected-access, expression-not-assigned
    mock_self = MagicMock()
    mock_self.settings.ldap_sync_period = 60

    # Fake LDAP configs
    config1 = MagicMock(name="mock_idp_config1")
    config2 = MagicMock(name="mock_idp_config2")
    config1.idp_name = "idp_config1"
    config2.idp_name = "idp_config2"
    # 2 configs in database
    mock_self.db.get_idp_configs_by_type = AsyncMock(return_value=[config1, config2])
    # Simulate config2 raising error during upsert
    mock_self._upsert_ldap_cache_data = AsyncMock(side_effect=[None, Exception("fail")])

    # Fake asyncio.sleep to raise CancelledError and break the infinite loop
    async def mock_sleep(_):
        raise asyncio.CancelledError()

    with (patch("asyncio.sleep", new=mock_sleep),
          caplog.at_level(logging.INFO)):
        try:
            await UserManagementApi._sync_ldap_cache(mock_self)
        except asyncio.CancelledError:
            pass

    # Assert upserts were called for both configs
    assert mock_self._upsert_ldap_cache_data.await_count == 2
    mock_self._upsert_ldap_cache_data.assert_any_await(ldap_config=config1),\
     "_upsert_ldap_cache_data should be called for config 1"
    mock_self._upsert_ldap_cache_data.assert_any_await(ldap_config=config2), \
     "_upsert_ldap_cache_data should be called for config 2"
    # Assert an exception was raised for the config 2 (by checking the log)
    warning_log =\
        [record for record in caplog.records if "Exception when updating LDAP cache for config " in record.msg]
    assert len(warning_log) == 1, "Should log a warning when upsert fails for a config"
    info_log = [record for record in caplog.records if "Successfully updated LDAP cache for config" in record.msg]
    assert len(info_log) == 1, "Should log an info when upsert is successful for a config"
