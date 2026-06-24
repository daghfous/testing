# pylint: disable=no-member
"""

test ldap server
"""
import binascii
import asyncio
from contextlib import ExitStack as DoesNotRaise
from concurrent.futures import ThreadPoolExecutor
import pytest
import pytest_asyncio
import ldap
from ateme.um_backend import (
    LdapConfig,
    SamlConfig,
    IdpType,
    DEFAULT_LOCAL_IDP_NAME
)
from ateme.um_backend.identity_provider import LocalProvider
from ateme.um_backend.saml_provider import SamlProvider, IdpCallbackMode
from ateme.um_backend.ldap_provider import LdapProvider
from ateme.um_backend.ldap import LdapSearchResult
# TODO: should be import from constant file instead test file.
from tests.test_saml import SAML_RESPONSE, LOGOUT_RESPONSE

IDP_NAME = "ldap_domain.com"
IDP_LABEL = "LDAP domain.com"


IDP_LDAP_CONFIG = LdapConfig(idp_type=IdpType.ldap.name,
                             idp_name=IDP_NAME,
                             idp_label=IDP_LABEL,
                             domain='ateme.com',
                             server='atm-infra.corp.ateme.com',
                             search='CN=Users,DC=corp,DC=ateme,DC=com',
                             group='S_SUPPORT')

INVALID_IDP_LDAP_CONFIG = LdapConfig(idp_type=IdpType.ldap.name,
                                     idp_name="IDP NAME",
                                     idp_label=IDP_LABEL,
                                     domain='ateme.com',
                                     server='atm-infra.corp.ateme.com',
                                     group='S_SUPPORT')

IDP_SAML_CONFIG = SamlConfig(
    idp_name="saml",
    idp_label="SAML config",
    entity_id="http://local",
    idp_type="saml",
    single_sign_on_service="http://local/signon",
    single_logout_service="http://local/logout",
    cert_fingerprint="fake_cert",
)


@pytest_asyncio.fixture(scope='function', name="identity_provider")
async def _identity_provider(init_database):
    """ identity provider fixture """
    await init_database.initialize()
    identity_provider = LocalProvider(init_database)
    await identity_provider.initialize()
    yield identity_provider


@pytest_asyncio.fixture(scope='function', name='saml_provider')
async def _saml_provider(init_database):
    """ Saml provider fixture """
    await init_database.initialize()
    identity_provider = SamlProvider(init_database)
    yield identity_provider


@pytest_asyncio.fixture(scope='function', name="ldap_provider")
async def _ldap_provider(init_database, settings):
    """ Ldap provider fixture """
    await init_database.initialize()
    executor = ThreadPoolExecutor(max_workers=settings.executor_max_workers)
    identity_provider = LdapProvider(init_database, executor=executor)
    yield identity_provider


@pytest.mark.parametrize('idp_name, idp_config, username, password, ldap_bind_exception,'
     'type_exception', [
        pytest.param(
            "ldap_domain.com",
            LdapConfig(
                idp_type=IdpType.ldap.name,
                idp_name=IDP_NAME,
                idp_label=IDP_LABEL,
                domain="domain.com"
            ),
            "john_doe", "password123",
            None, None,
            id="bind ok"
        ),
        pytest.param(
            "ldap_domain.com",
            LdapConfig(
                idp_type=IdpType.ldap.name,
                idp_name=IDP_NAME,
                idp_label=IDP_LABEL,
                domain="domain.com"
            ),
            "john_doe", "invalid",
            ldap.INVALID_CREDENTIALS(), ldap.INVALID_CREDENTIALS(),
            id="ldap server bind exception"
        ),
        pytest.param(
            "ldap_invalid.com",
            None,
            "john_doe", "password123",
            None, "Idp ldap_invalid.com not found",
            id="idp_config not found"
        )
     ])
async def test_bind(mocker, ldap_provider, idp_name, idp_config, username, password,
                    ldap_bind_exception, type_exception):
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    """
    Test the bind method of the LdapProvider class.

    Parameters:
    - mocker: A mocker object from the pytest-mock library.
    - ldap_provider: The ldap_provider fixture
    - idp_name: The name of the identity provider.
    - idp_config: The configuration of the identity provider.
    - username: The username to bind with.
    - password: The password to bind with.
    - ldap_bind_exception: An exception to be raised during the bind operation.
    - type_exception: An exception to be raised during the bind method.
    """
    event_loop = asyncio.get_event_loop()
    mocker.patch(
        "ateme.um_backend.database.Database.get_idp_config_by_name", 
        return_value=idp_config
    )

    def mock_bind(*_):
        if ldap_bind_exception:
            raise ldap_bind_exception

    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", mock_bind)

    # Case 1: Specific LDAP bind exception
    if ldap_bind_exception:
        with pytest.raises(ldap.INVALID_CREDENTIALS):  # pylint: disable=no-member
            await ldap_provider.bind(idp_name, username, password, False, event_loop)

    # Case 2: IDP config not found or custom error (match string)
    elif isinstance(type_exception, str):
        with pytest.raises(Exception, match=type_exception):
            await ldap_provider.bind(idp_name, username, password, False, event_loop)

    # Case 3: Success (no exception expected)
    else:
        await ldap_provider.bind(idp_name, username, password, False, event_loop)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    'idp_config, username, password, bind_exception, type_exception',
    [
        # OK case: no exception expected
        (
            {"idp_type": IdpType.ldap.name, "idp_name": IDP_NAME,
             "label": IDP_LABEL, "domain": "domain.com",
             "search": "CN=Users,DC=corp,DC=domain,DC=com",
             "user_filter": "mail"},
            "john_doe", "password123",
            None, None
        ),
        # LDAP bind failure
        (
            {"idp_type": IdpType.ldap.name, "idp_name": IDP_NAME,
             "label": IDP_LABEL, "domain": "domain.com",
             "search": "CN=Users,DC=corp,DC=domain,DC=com",
             "user_filter": "mail"},
            "john_doe", "invalid",
            ldap.INVALID_CREDENTIALS(), ldap.INVALID_CREDENTIALS
        ),
    ]
)
async def test_validate_idp_config(mocker, ldap_provider, idp_config, username, password,
                                   bind_exception, type_exception):
    """
    Test the validate_idp_config method of the IdentityProvider class.

    Parameters:
    - mocker: A mocker object from the pytest-mock library.
    - ldap_provider: The ldap_provider fixture
    - idp_config: The configuration of the identity provider.
    - username: The username to bind with.
    - password: The password to bind with.
    - bind_exception: An exception to be raised during the bind operation.
    - type_exception: An exception to be raised during the bind method.

    Returns:
    - None
    
    """
    event_loop = asyncio.get_event_loop()

    def mock_bind(*_):
        if bind_exception:
            raise bind_exception
        return mocker.Mock()

    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", mock_bind)
    mocker.patch("ateme.um_backend.ldap.LdapClient.search", return_value=[])

    if type_exception:
        with pytest.raises(type_exception):  # expect a specific error
            await ldap_provider.validate_idp_config(
                username=username,
                password=password,
                idp_config=idp_config,
                is_user_dn=False,
                loop=event_loop,
            )
    else:
        # No exception expected — just ensure it completes successfully
        await ldap_provider.validate_idp_config(
            username=username,
            password=password,
            idp_config=idp_config,
            is_user_dn=False,
            loop=event_loop,
        )

@pytest.mark.parametrize(
    'response, expected_result, exception_expected',
    [pytest.param(SAML_RESPONSE, IdpCallbackMode.LOGIN, DoesNotRaise(), id='login'),
     pytest.param(LOGOUT_RESPONSE, IdpCallbackMode.LOGOUT, DoesNotRaise(), id='logout'),
     pytest.param('foo', None, pytest.raises(binascii.Error), id='exception')]
)
def test_get_mode(response: str, expected_result: IdpCallbackMode, exception_expected):
    """ Test get_mode static method from SamlProvider class """
    with exception_expected:
        assert SamlProvider.get_mode(response) == expected_result

@pytest.mark.asyncio
@pytest.mark.parametrize("mapper_attributes, bind_success, ldap_response, scopes_to_add, scopes_result", [
    (
        [
            {
                'name': 'memberof',
                'value': "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com"
            }
        ],
        True,
        [
            LdapSearchResult(
                dn="CN=Account SSO HUB,CN=Users,DC=corp,DC=ateme,DC=com",
                attributes={
                    "memberOf": [
                        "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com",
                        "CN=RODC_PWD-USERS_RENNES,CN=Users,DC=corp,DC=ateme,DC=com",
                        "CN=Allowed RODC Password Replication Group,CN=Users,DC=corp,DC=ateme,DC=com"
                    ]
                },
            )
        ],
        ['usr:administrator'],
        ['usr:administrator']
    ), (
        [
            {
                'name': 'memberof',
                'value': "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com"
            }
        ],
        False,
        [
            LdapSearchResult(
                dn="CN=Account SSO HUB,CN=Users,DC=corp,DC=ateme,DC=com",
                attributes={
                    "memberOf": [
                        "CN=G_R&D-MSS,OU=Groups_Mails,DC=corp,DC=ateme,DC=com",
                        "CN=RODC_PWD-USERS_RENNES,CN=Users,DC=corp,DC=ateme,DC=com",
                        "CN=Allowed RODC Password Replication Group,CN=Users,DC=corp,DC=ateme,DC=com"
                    ]
                },
            )
        ],
        ['usr:administrator'],
        []
    ), (
        [
            {
                "name": "sAMAccountName",
                "value": "test"
            }
        ],
        True,
        [
            LdapSearchResult(
                dn="CN=Account SSO HUB,CN=Users,DC=corp,DC=ateme,DC=com",
                attributes={"sAMAccountName": ["test"]},
            )
        ],
        ['usr:administrator'],
        ['usr:administrator']
    )
])
async def test_retrieve_scopes(mocker, ldap_provider, mapper_attributes, bind_success, ldap_response,
                               scopes_to_add, scopes_result):
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    """Unit test retrieve_scopes method"""
    event_loop = asyncio.get_event_loop()
    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", return_value=(None, True))

    def mock_ldap_server_mock_search(*_):
        if not bind_success:
            raise ldap.INVALID_CREDENTIALS # pylint: disable=no-member
        return ldap_response

    mocker.patch("ateme.um_backend.ldap.LdapClient.search", mock_ldap_server_mock_search)

    mappers = [
        {'type': 'simple',
         'attributes': mapper_attributes,
         'scopes_to_add': scopes_to_add}
    ]
    ldap_config = {"idp_name": IDP_NAME,
                   'idp_type': IdpType.ldap.name,
                   'idp_label': IDP_LABEL,
                   'server': 'atm-infra.corp.ateme.com',
                   'domain': "ateme.com",
                   'search': 'CN=Users,DC=corp,DC=ateme,DC=com',
                   'group': 'S_SUPPORT',
                   'user_filter': 'mail',
                   'mappers': mappers,
                   'deny_access': True
                   }

    context = DoesNotRaise() if bind_success else pytest.raises(ldap.INVALID_CREDENTIALS) # pylint: disable=no-member
    with context:
        scopes = await ldap_provider.retrieve_scopes(LdapConfig.from_dict(ldap_config),
                                               "toto@ateme.com", "password", event_loop)
        assert scopes == scopes_result


async def test_api_validate_idp_config(init_backend_with_admin, mocker):
    """
    Test API for the IDP configuration.

    Parameters:
        mocker (pytest.Mock): The mocker object used for mocking.
    Returns:
        None
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    username = "john_doe"
    password = "password123"

    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", return_value=(None, True))

    # Test ipdconfig/validate route
    resp = await _api.post(
        "/idpconfigs/validate",
        json={**IDP_LDAP_CONFIG.to_dict(), "username": username, "password": password},
        headers=_admin_headers,
    )
    assert resp.status == 200
    assert (await resp.text()) == 'Ok - Valid LDAP config', 'This LDAP config should be valid'

    # Test ipdconfig route: POST
    resp = await _api.post(
        "/idpconfigs",
        json=IDP_LDAP_CONFIG.to_dict(),
        headers=_admin_headers,
    )
    assert resp.status == 201
    assert (await resp.text()) == 'OK'

    # Test ipdconfig route: POST with invalid idp_config, missing search field
    resp = await _api.post(
        "/idpconfigs",
        json=INVALID_IDP_LDAP_CONFIG.to_dict(),
        headers=_admin_headers,
    )
    assert resp.status == 400
    body = await resp.json()
    assert body['errors'][0].startswith("Failed validating")

    # Test ipdconfig route: GET
    resp = await _api.get("/idpconfigs", headers=_admin_headers)
    assert resp.status == 200
    body = await resp.json()
    assert len(body) == 2, '2 idp configs should be found'
    local_idp_config = body[0]
    assert local_idp_config["idp_type"] == IdpType.local.name
    assert local_idp_config["idp_name"] == DEFAULT_LOCAL_IDP_NAME
    ldap_idp_config = body[1]
    assert ldap_idp_config["idp_type"] == IdpType.ldap.name
    assert ldap_idp_config["idp_name"] == IDP_NAME

    # Test ipdconfig/{idp_name} route: GET
    resp = await _api.get(
        f"/idpconfigs/{IDP_NAME}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    body = await resp.json()
    assert isinstance(body, dict)
    assert body["idp_type"] == IdpType.ldap.name
    assert body["idp_name"] == IDP_NAME
    assert body["idp_label"] == IDP_LABEL

    resp = await _api.get(
        "/idpconfigs/invalid", headers=_admin_headers
    )
    assert resp.status == 404
    assert (await resp.text()) == 'Not Found', 'None idp config should be found'

    # Test ipdconfig/{idpname} route: DELETE
    resp = await _api.delete(
        f"/idpconfigs/{IDP_NAME}",
        headers=_admin_headers,
    )
    assert resp.status == 200
    assert (await resp.text()) == 'ldap idp_config ldap_domain.com and users to this config removed', \
        'The config should be removed'

    # Check that the config is removed
    resp = await _api.get(
        f"/idpconfigs/{IDP_NAME}",
        headers=_admin_headers,
    )
    assert resp.status == 404
    assert (await resp.text()) == 'Not Found', 'The config should be removed'


@pytest.mark.parametrize("idp_config, body_expected", [
    pytest.param(
        IDP_LDAP_CONFIG,
        [
            {"idp_name": "local", "idp_type": "local", "idp_label": "Local"},
            {"idp_type": "ldap", "idp_name": "ldap_domain.com", "idp_label": "LDAP domain.com", "deny_access": True},
        ],
        id="ldap"
    ),
    pytest.param(
        IDP_SAML_CONFIG,
        [
            {"idp_name": "local", "idp_type": "local", "idp_label": "Local"},
            {"idp_name": "saml", "idp_label": "SAML config", "idp_type": "saml"},
        ],
        id="saml"
    )
])
async def test_authenticate_mode(init_backend_with_admin, idp_config, body_expected):
    """

    Test authenticate mode route, used by frontend.
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    resp = await _api.post("/idpconfigs", json=idp_config.to_dict(), headers=_admin_headers)
    assert resp.status == 201
    resp = await _api.get("/authenticate_mode")
    assert resp.status == 200
    body = await resp.json()
    assert body
    assert isinstance(body, list)
    # Must have only two idp configs
    # One local create at init and the config
    # previously created.
    assert body == body_expected


@pytest.mark.parametrize("idp_config", [
    pytest.param(
        IDP_LDAP_CONFIG,
        id="ldap"
    ),
    pytest.param(
        IDP_SAML_CONFIG,
        id="saml"
    )
])
async def test_duplicate_idp_config(init_backend_with_admin, idp_config):
    """

    Verify that insertion of same idp_config (same idp_name at least) raise an HTTP conflict 409.
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    resp = await _api.post("/idpconfigs", json=idp_config.to_dict(), headers=_admin_headers)
    assert resp.status == 201

    resp = await _api.post("/idpconfigs", json=idp_config.to_dict(), headers=_admin_headers)
    assert resp.status == 409
    body = await resp.text()
    assert body == f"Can't store IDP config, entry with name {idp_config.idp_name} already exists."
