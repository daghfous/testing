"""

Test ldap_provider
"""
import asyncio

import pytest
from ldap.filter import escape_filter_chars

from ateme.um_backend.ldap_provider import LdapProvider, build_user_search_filter
from ateme.um_backend.types.ldap_config import LdapConfig
from ateme.um_backend.ldap import LdapSearchResult


class FakeDB: # pylint: disable=too-few-public-methods
    """
    Fake Database instance
    """

@pytest.fixture(name="ldap_provider")
def _ldap_provider():
    """

    LdapProvider fixture
    """
    yield LdapProvider(FakeDB(), None)


@pytest.mark.asyncio
@pytest.mark.parametrize("idp_config, mock_search, scopes_expected", [
    pytest.param(
        LdapConfig(
            idp_type="ldap",
            domain="example.org",
            server="localhost:389",
            search="dc=example,dc=org",
            idp_label="test",
            bind_dn="cn=admin,dc=example,dc=org",
            bind_password="password",
            user_filter="uid",
            deny_access=True,
            use_ssl=False,
            mappers=[
                {
                    "type": "simple",
                    "attributes": [{"name": "ou", "value": "Administrators"}],
                    "scopes_to_add": ["all:administrators"]
                }
            ]
        ),
        [
            LdapSearchResult(
                dn="uid=hbarbossa,ou=People,dc=example,dc=org",
                attributes={"ou": []}
            )
        ],
        [],
        id="no-match"
    ),
    pytest.param(
        LdapConfig(
            idp_type="ldap",
            domain="example.org",
            server="localhost:3089",
            search="dc=example,dc=org",
            idp_label="test",
            bind_dn="cn=admin,dc=example,dc=org",
            bind_password="password",
            user_filter="uid",
            deny_access=True,
            use_ssl=False,
            mappers=[
                {
                    "type": "simple",
                    "attributes": [{"name": "objectclass", "value": "organizationalPerson"}],
                    "scopes_to_add": ["all:monitor"]
                },
                {
                    "type": "simple",
                    "attributes": [{"name": "ou", "value": "Administrators"}],
                    "scopes_to_add": ["all:administrators"]
                },
            ]
        ),
        [
            LdapSearchResult(
                dn="uid=hbarbossa,ou=People,dc=example,dc=org",
                attributes={
                        "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"],
                        "ou": ["Administrators"],
                },
            )
        ],
        ["all:monitor", "all:administrators"],
        id="multiple-match"
    ),
    pytest.param(
        LdapConfig(
            idp_type="ldap",
            domain="example.org",
            server="localhost:389",
            search="dc=example,dc=org",
            idp_label="test",
            bind_dn="cn=admin,dc=example,dc=org",
            bind_password="password",
            user_filter="uid",
            deny_access=True,
            use_ssl=False,
            mappers=[
                {
                    "type": "simple",
                    "attributes": [{"name": "objectclass", "value": "organizationalPerson"}],
                    "scopes_to_add": ["all:monitor"]
                },
                {
                    "type": "simple",
                    "attributes": [{"name": "ou", "value": "Administrators"}],
                    "scopes_to_add": ["all:administrators"]
                },
            ]
        ),
        [
            LdapSearchResult(
                dn="uid=hbarbossa,ou=People,dc=example,dc=org",
                attributes={"objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"]}
            )
        ],
        ["all:monitor"],
        id="single-match"
    ),
    pytest.param(
        LdapConfig(
            idp_type="ldap",
            domain="example.org",
            server="localhost:3089",
            search="dc=example,dc=org",
            idp_label="test",
            bind_dn="cn=admin,dc=example,dc=org",
            bind_password="password",
            user_filter="uid",
            deny_access=True,
            use_ssl=False,
            mappers=[
                {
                    "type": "simple",
                    "attributes": [{"name": "uid", "value": "idm"}],
                    "scopes_to_add": ["all:monitor"]
                },
            ]
        ),
        [
            LdapSearchResult(
                dn="uid=idm,ou=Administrators,dc=example,dc=org",
                attributes={"uid": ["idm"]}
            )
        ],
        ["all:monitor"],
        id="single-match-attribute-not-list"
    ),
    pytest.param(
        LdapConfig(
            idp_type="ldap",
            server="85.222.92.98:9512",
            domain="tdrygiel.local",
            search="DC=tdrygiel,DC=local",
            idp_label="test",
            bind_dn="CN=Administrator,CN=Users,DC=tdrygiel,DC=local",
            bind_password="Server123",
            user_filter="sAMAccountName",
            search_filter="(objectClass=person)",
            deny_access=True,
            use_ssl=False,
            mappers=[
                {
                    "type": "simple",
                    "attributes": [{"name": "memberOf", "value": "CN=Guests,CN=Builtin,DC=tdrygiel,DC=local"}],
                    "scopes_to_add": ["all:monitor"]
                },
                {
                    "type": "simple",
                    "attributes": [{"name": "sAMAccountName", "value": "Guest"}],
                    "scopes_to_add": ["all:guest"]
                },
            ]
        ),
        [
            LdapSearchResult(
                dn="CN=Guest,CN=Users,DC=tdrygiel,DC=local",
                attributes={"memberOf": ["CN=Guests,CN=Builtin,DC=tdrygiel,DC=local"],
                            "sAMAccountName": ["Guest"]}
            )
        ],
        ["all:monitor", "all:guest"],
        id="active-directory"
    )
])
async def test_retrieve_scopes(
    ldap_provider,
    mocker,
    idp_config: LdapConfig,
    mock_search: list[dict],
    scopes_expected: list[str]
):
    """

    Test `retrieve_scope` from LdapProvider, mock bind & search LDAP request.
    This test check role mapping from mock response entries expect some scopes in return.
    """
    # Mock bind request
    mocker.patch("ateme.um_backend.ldap.LdapClient.bind", return_value=(None, True))
    # Mock search request with `mock_search` data from parametrize.
    mocker.patch("ateme.um_backend.ldap.LdapClient.search", return_value=mock_search)
    scopes = await ldap_provider.retrieve_scopes(
        idp_config, "Guest", "secret", asyncio.get_running_loop()
    )
    assert scopes == scopes_expected

@pytest.mark.parametrize(
    "attribute, username",
    [
        ("uid", "john"),                                # basic case
        ("cn", "admin)(|(cn=*))"),                      # username injection attempt
        ("cn)(", "john"),                               # attribute injection attempt
        ("uid)(", "john)(test"),                        # both need escaping
        ("", "john"),                                   # empty attribute
        ("uid", ""),                                    # empty username
        ("sn", "müller"),                               # unicode input
    ],
)
def test_build_user_search_filter_cases(attribute, username):
    """Test build_user_search_filter against multiple attribute/username combinations."""
    expected_attr = escape_filter_chars(attribute)
    expected_username = escape_filter_chars(username)
    expected = f"({expected_attr}={expected_username})"

    output = build_user_search_filter(attribute, username)

    assert output == expected
