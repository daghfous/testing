# pylint: disable=no-member
"""

test types
"""
from datetime import timedelta
import pytest

from bson import ObjectId

from ateme.um_backend.data_migration_imp import DataMigrationImp
from ateme.um_backend import (
    Request,
    RequestMethod,
    Action,
    Scope,
    ScopeFilterMode,
    ScopeFilter,
    User,
    LdapConfig,
    IdpType,
    Configuration,
    ApiDescriptor,
    DEFAULT_LOCAL_IDP_NAME,
    PasswordPolicy,
    PublicConfiguration,
    Session,
    Token
)


@pytest.mark.parametrize("req, data", [
    pytest.param(
        Request(method=RequestMethod.GET, route="/alarm/{id}"),
        {"method": "GET", "route": "/alarm/{id}"}
    ),
    pytest.param(
        Request(method=RequestMethod.GET),
        {},
        marks=pytest.mark.xfail
    ),
    pytest.param(
        Request(method=RequestMethod.GET, route="alarm/{id}"),
        {"method": "GET", "route": "/alarm/{id}"},
        marks=pytest.mark.xfail
    ),
])
def test_types_request(req, data):
    """

    test request type
    :param req:
    :param data:
    """
    assert req.to_dict() == data
    req.validate()


@pytest.mark.parametrize("action, data",
                         [pytest.param(
                             Action(
                                 name="delete_alarm", label="usr",
                                 request=Request(method=RequestMethod.GET, route="/alarm/{id}"),
                                 prefix="ala", version=1, description="Missing description ..."),
                             {"name": "delete_alarm", "label": "usr",
                              "request": {"method": "GET", "route": "/alarm/{id}"},
                              "prefix": "ala", "version": 1, "description": "Missing description ..."}),
                          pytest.param(
                              Action(
                                  name="deleteAlarm", request=Request(
                                      method=RequestMethod.GET, route="/alarm/{id}"),
                                  label="usr", description="Missing description ..."),
                              {},
                              marks=pytest.mark.xfail),
                          pytest.param(
                              Action(
                                  name="delete_alarm", label="usr",
                                  request=Request(method=RequestMethod.GET, route="/alarm/{id}"),
                                  prefix="prefixbiggerthan10", version=1, description="Missing description ..."),
                              {"name": "delete_alarm", "label": "usr",
                               "request": {"method": "GET", "route": "/alarm/{id}"},
                               "prefix": "ala", "version": 1, "description": "Missing description ..."},
                              marks=pytest.mark.xfail),
                          pytest.param(
                              Action(
                                  name="delete_alarm", label="usr",
                                  request=Request(method=RequestMethod.GET, route="/alarm/{id}"),
                                  prefix="alarm", version=1, description="Another desc"),
                              {"name": "delete_alarm", "label": "usr",
                               "request": {"method": "GET", "route": "/alarm/{id}"},
                               "prefix": "alarm", "version": 1, "description": "Another desc"}), ])
def test_types_action(action, data):
    """

    test action type
    :param action:
    :param data:
    """
    action.validate()
    assert action.version == data.get('version', 1)
    assert action.to_dict() == data


@pytest.mark.parametrize("scope, data", [
    pytest.param(
        Scope(id="ala:test", label="usr", content=[], version=1, description="TADA", default=True),
        {"id": "ala:test", "label": "usr", "content": [], "version": 1, "description": "TADA",
         "default": True, 'title': 'usr test'}
    ),
    pytest.param(
        Scope(id="ala:test", label="usr", content=[{"scope": "ala:sub_test"},
                                                   {"action": "ala:*", "policy": "allow", "resource": {}}],
              version=1, default=True, description="TADA"),
        {"id": "ala:test", "label": "usr", "content": [{"scope": "ala:sub_test"},
                                                       {'action': 'ala:*', 'policy': 'allow', 'resource': {}}],
         "description": "TADA", "version": 1, "default": True, 'title': 'usr test'}
    ),
    pytest.param(
        Scope(id="test:t", label="usr", content=[]),
        {},
        marks=pytest.mark.xfail
    ),
    pytest.param(
        Scope(id="ala:test", label="usr", content=["ala:get_test", {"action": "ala:*"}]),
        {"id": "ala:test", "label": "usr", "content": ["ala:get_test", {'action': 'ala:*'}]},
        marks=pytest.mark.xfail
    ),
])
def test_types_scope(scope, data):
    """

    test scope type
    :param scope:
    :param data:
    """
    scope.validate()
    assert scope.version
    assert scope.description
    assert scope.default
    assert scope.to_dict() == data


_ID = ObjectId()
USERNAME = 'bidule'
PASSWORD = '5btr5tnrnr@A'
IDP_LOCAL_NAME = DEFAULT_LOCAL_IDP_NAME
IDP_LOCAL_TYPE = IdpType.local.name
IDP_LDAP_NAME = 'ldap_ateme.com'
IDP_LDAP_TYPE = IdpType.ldap.name


@pytest.mark.parametrize("user, data", [
    pytest.param(
        User(creation_id=_ID, username=USERNAME, password=PASSWORD, scopes=[]),
        {'creation_id': _ID,
         'user_id': User.generate_hash([USERNAME, str(PASSWORD), IDP_LOCAL_NAME]),
         'username': USERNAME,
         'password': PASSWORD,
         'idp_name': IDP_LOCAL_NAME,
         'password_last_update': False,
         'scopes': [],
         'first_login': False,
         'password_expired': False,
         'enabled': True,
         'session_timeout_disabled': False,
         'password_expiration_disabled': False}
    ),
    pytest.param(
        User(creation_id=_ID, username=USERNAME, password=PASSWORD, scopes=['usr:admin'],
             idp_name=IDP_LDAP_NAME, password_expiration_disabled=True),
        {'creation_id': _ID,
         'user_id': User.generate_hash([USERNAME, str(PASSWORD), IDP_LDAP_NAME]),
         'username': USERNAME,
         'password': PASSWORD,
         'idp_name': IDP_LDAP_NAME,
         'password_last_update': False,
         'scopes': ['usr:admin'],
         'first_login': False,
         'password_expired': False,
         'enabled': True,
         'session_timeout_disabled': False,
         'password_expiration_disabled': True}
    ),
    pytest.param(
        User(creation_id=_ID, username=USERNAME, password=PASSWORD, scopes=['admin']),
        {'creation_id': _ID,
         'user_id': User.generate_hash([USERNAME, str(PASSWORD), IDP_LOCAL_NAME]),
         'username': USERNAME,
         'password': PASSWORD,
         'idp_name': IDP_LOCAL_NAME,
         'password_last_update': False,
         'scopes': ['usr:admin'],
         'first_login': False,
         'enabled': True,
         'session_timeout_disabled': False,
         'password_expiration_disabled': False},
        marks=pytest.mark.xfail
    ),
    pytest.param(
        User(password="test"),
        {},
        marks=pytest.mark.xfail
    ),
])
def test_types_user(user: User, data: dict):
    """

    test user type
    :param user:
    :param data:
    """
    # pylint: disable=unnecessary-dunder-call
    user.validate()
    data.setdefault("internal", False)
    data.setdefault("default", False)
    assert user.to_dict(with_creation_id=True) == data
    assert user.__eq__(user)
    assert user.__eq__({"nul": None}) == NotImplemented


@pytest.mark.parametrize("ldap_config, data", [
    pytest.param(
        LdapConfig(
            idp_type=IdpType.ldap.name,
            idp_name=DataMigrationImp.compute_idp_name_from_domain("ateme.com"),
            idp_label="Ldap ateme.com",
            domain='ateme.com',
            server='atm-infra.corp.ateme.com',
            search='CN=Users,DC=corp,DC=ateme,DC=com',
            group='S_SUPPORT',
            tls_config={"private_key_file": "private_key_file",
                        "certificate_file": "certificate_file",
                        "ca_certs_file": "ca_certs_file"}),
        {"idp_type": IdpType.ldap.name,
         "idp_name": DataMigrationImp.compute_idp_name_from_domain("ateme.com"),
         "idp_label": "Ldap ateme.com",
         "domain": "ateme.com",
         "server": "atm-infra.corp.ateme.com",
         "search": "CN=Users,DC=corp,DC=ateme,DC=com",
         "group": "S_SUPPORT",
         "tls_config": {"private_key_file": "private_key_file",
                        "certificate_file": "certificate_file",
                        "ca_certs_file": "ca_certs_file"}}
    ),
    pytest.param(
        LdapConfig(
            idp_name=DataMigrationImp.compute_idp_name_from_domain("ateme.com"),
            idp_type=IdpType.ldap.name,
            idp_label="Ldap ateme.com",
            domain='ateme.com',
            server='atm-infra.corp.ateme.com',
            search='CN=Users,DC=corp,DC=ateme,DC=com',
            group='S_SUPPORT'),
        {"idp_type": IdpType.ldap.name,
         "idp_name": DataMigrationImp.compute_idp_name_from_domain("ateme.com"),
         "idp_label": "Ldap ateme.com",
         "domain": "ateme.com",
         "server": "atm-infra.corp.ateme.com",
         "search": "CN=Users,DC=corp,DC=ateme,DC=com",
         "group": "S_SUPPORT"}
    ),
    pytest.param(
        LdapConfig(),
        {},
        marks=pytest.mark.xfail
    ),
])
def test_types_ldap_config(ldap_config, data):
    """

    test ldap_config type
    :param ldap_config:
    :param data:
    """
    # pylint: disable=unnecessary-dunder-call
    assert ldap_config.use_ssl
    if "tls_config" in data:
        assert ldap_config.tls_config.private_key_file
        assert ldap_config.tls_config.certificate_file
        assert ldap_config.tls_config.ca_certs_file
    ldap_config.validate()
    data['deny_access'] = True
    assert ldap_config.to_dict() == data
    assert ldap_config.__eq__({"nul": None}) == NotImplemented


@pytest.mark.parametrize("config, data", [
    pytest.param(
        Configuration(
            max_successive_failed_login=10,
            user_deactivation_period=500,
            token_expiration=100,
            refresh_token_expiration=200,
            token_cleaning_period=300,
            logout_timeout=100,
            password_policy=PasswordPolicy(expiration_delay_in_days=365)),
        {"max_successive_failed_login": 10,
         "user_deactivation_period": 500,
         "token_expiration": 100,
         "refresh_token_expiration": 200,
         "token_cleaning_period": 300,
         "logout_timeout":  100,
         "password_policy": {"expiration_delay_in_days": 365,
                             "regex_pattern": PasswordPolicy.get_password_regex_pattern(),
                             "password_min_length": 10}
         }
    ),
    pytest.param(
        Configuration(),
        {},
        marks=pytest.mark.xfail
    ),
])
def test_types_configuration(config, data):
    """

    test configuration type
    :param config:
    :param data:
    """
    config.validate()
    assert config.user_deactivation_period
    assert config.max_successive_failed_login
    assert config.password_policy.expiration_delay_in_days == 365
    assert config.to_dict() == data


@pytest.mark.parametrize("public_config, data", [
    pytest.param(
        PublicConfiguration(
            Configuration(
                max_successive_failed_login=10,
                user_deactivation_period=500,
                token_expiration=100,
                refresh_token_expiration=200,
                token_cleaning_period=300,
                logout_timeout=100,
                password_policy=PasswordPolicy(expiration_delay_in_days=365))),
        {"logout_timeout":  100,
         "password_policy": {"expiration_delay_in_days": 365,
                             "regex_pattern": PasswordPolicy.get_password_regex_pattern(),
                             "password_min_length": 10}
         }
    ),
    pytest.param(
        PublicConfiguration(Configuration()),
        {},
        marks=pytest.mark.xfail
    ),
])
def test_types_public_configuration(public_config, data):
    """

    test public_configuration type
    :param public_config:
    :param data:
    """
    public_config.validate()
    assert public_config.logout_timeout
    assert public_config.password_policy.expiration_delay_in_days
    assert public_config.password_policy.regex_pattern == PasswordPolicy.get_password_regex_pattern()
    assert public_config.to_dict() == data


@pytest.mark.parametrize("data", [
    pytest.param(
        {"name": "delete_alarm", "request": {"method": "GET", "route": "/alarm/{id}"}, "prefix": "ala", "unknown": 1}
    )
])
def test_types_base_from_dict(data):
    """

    test action type
    :param data:
    """
    # pylint: disable=unnecessary-dunder-call
    result = Action.from_dict(data)
    with pytest.raises(AttributeError, match=r".* 'unknown'"):
        result.__getattribute__("unknown")


@pytest.mark.parametrize("api_descriptor, data", [
    (ApiDescriptor("test",
                   "test:8080",
                   [Action(name="test", prefix='test', request=Request(method=RequestMethod.GET, route="/alarm/{id}"),
                           description="Missing description ...", label="usr",)],
                   [Scope(id="ala:test", label="usr", content=[{"scope": "ala:sub_test"},
                                                               {"action": "ala:*", "policy": "allow", "resource": {}}],
                          version=1, default=True, description="TADA", title="usr test")]), None),
    pytest.param(
        ApiDescriptor(prefix="alaext", url="http://example.com"),
        {"prefix": "alaext", "url": "http://example.com", "actions": [], "scopes": []}
    ),
    pytest.param(
        ApiDescriptor(prefix="alaext"),
        {},
        marks=pytest.mark.xfail
    ),
    pytest.param(
        ApiDescriptor(prefix=5, url="http://example.com"),
        {"prefix": "alaext", "url": "http://example.com", "actions": [], "scopes": []},
        marks=pytest.mark.xfail
    ),
])
def test_type_api_descriptor(api_descriptor, data):
    """
    Test type api_descriptor
    """
    if data:
        descr = api_descriptor.to_dict()
        assert descr['prefix'] == data['prefix']
        assert descr['url'] == data['url']
        assert descr['scopes'] == data['scopes']
    api_descriptor.validate()
    assert api_descriptor.to_dict() == ApiDescriptor.from_dict(api_descriptor.to_dict()).to_dict()


@pytest.mark.parametrize("session, data", [
    pytest.param(Session.from_dict({
        'idp_name': 'test',
        'user_ip': '0.0.0.0',
        'token_id': 'None',
        'user_id': 'test',
        'username': 'test',
    }),
        {
        'idp_name': 'test',
        'user_ip': '0.0.0.0',
        'token_id': 'None',
        'user_id': 'test',
        'username': 'test',
    }),
    pytest.param(Session.generate(
        user={"username": "test", "idp_name": "test"},
        token=Token.generate(
            user_id="test",
            token_expiration=timedelta(days=1),
            refresh_token_expiration=timedelta(days=1),
            session_timeout_disabled=False,
            user_ip="0.0.0.0"
        )),
        {
        'idp_name': 'test',
        'user_ip': '0.0.0.0',
        'token_id': 'None',
        'user_id': 'test',
        'username': 'test',
    }),
    pytest.param(
        Session(username="test", idp_name="test", user_id="test", token_id="test"),
        {},
        marks=pytest.mark.xfail
    ),
])
def test_types_session(session, data):
    """
    test session type
    :param session:
    :param data:
    """
    assert session.username
    session_dict = session.as_dict()
    session_dict.pop('started_date')
    session_dict.pop('expiration_date')
    assert session_dict == data


@pytest.mark.parametrize(
    "input_args, expected_filter", [
        pytest.param(
            {},
            {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
            id="default filter"
        ),
        pytest.param(
            {"internal": False},
            {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
            id="internal False"
        ),
        pytest.param(
            {"internal": True},
            {"internal": True},
            id="internal True"
        ),
        pytest.param(
            {"internal": None},
            {},
            id="internal None"
        ),
        pytest.param(
            {"scope_ids": ["myid"]},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$in": ["myid"]}}
            ]},
            id="scope_id"
        ),
        pytest.param(
            {"prefix": "prefix"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^prefix:"}}
            ]},
            id="prefix filter"
        ),
        pytest.param(
            {"app_name": "myapp"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^myapp:"}}
            ]},
            id="app_name filter"
        ),
        pytest.param(
            {"scope_type": "operator"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^(.*:)?operator$"}}
            ]},
            id="scope_type filter"
        ),
        pytest.param(
            {"label": "admin"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"label": {"$regex": "admin"}}
            ]},
            id="label filter"
        ),
        pytest.param(
            {"default": True},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"default": True}
            ]},
            id="default True"
        ),
        pytest.param(
            {"default": False},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"$or": [{"default": False}, {"default": {"$exists": False}}]}
            ]},
            id="default False"
        ),
        pytest.param(
            {"app_name": "myapp", "prefix": "prefix"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^myapp:prefix:"}}
            ]},
            id="app_name and prefix"
        ),
        pytest.param(
            {"prefix": "prefix", "scope_type": "engineer"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^prefix:(.*:)?engineer$"}}
            ]},
            id="prefix and scope_type"
        ),
        pytest.param(
            {"app_name": "myapp", "scope_type": "administrator"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^myapp:(.*:)?administrator$"}}
            ]},
            id="app_name and scope_type"
        ),
        pytest.param(
            {"app_name": "myapp", "prefix": "prefix", "scope_type": "guest"},
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {"id": {"$regex": "^myapp:prefix:guest$"}}
            ]},
            id="app_name, prefix and scope_type"
        ),
        pytest.param(
            {
                "mode": ScopeFilterMode.BASIC
            },
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {'id': {'$regex': '^(all|usr):[^:]+$'}}
            ]},
            id="basic mode"
        ),
        pytest.param(
            {
                "pmf_release_name": "pmf",
                "mode": ScopeFilterMode.BASIC
            },
            {"$and": [
                {"$or": [{"internal": False}, {"internal": {"$exists": False}}]},
                {'id': {'$regex': '^((?!pmf:)[^:]+:[^:]+$|pmf:[^:]+:[^:]+$)'}}
            ]},
            id="basic mode with pmf release name"
        ),
    ]
)
@pytest.mark.asyncio
async def test_scope_filter_to_mongo_filter(
    input_args: dict,
    expected_filter: dict
):
    """ Test ScopeFilter.to_filter method with various parameters.
    Args:
        mocker: pytest-mock fixture
        input_args (dict): arguments to pass to ScopeFilter
        expected_filter (dict): expected filter output from to_filter
    """
    scope_filter = ScopeFilter(**input_args)
    assert expected_filter == scope_filter.to_mongo_filter()
