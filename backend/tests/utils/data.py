"""

Test data structure

Initialize UM types object with common data.
"""
import binascii
from base64 import b64decode

from bson import ObjectId

from ateme.encryption_lib import AESCipher  # pylint: disable=no-name-in-module
from ateme.um_backend.types import (
    User,
    Scope,
    Action,
    Request,
    RequestMethod,
    LdapConfig,
    IdpLocalConfig,
    IdpType,
    ApiDescriptor
)


NEW_USER = User(creation_id=ObjectId(), username="bidule", password="Annkfez@88!", scopes=[])
NEW_USER_LDAP = User(
    creation_id=ObjectId(),
    username="bidule",
    password="123456",
    scopes=[],
    idp_name=f"{IdpType.ldap.name}_domain.com",
)

ADMIN = User(
    creation_id=ObjectId(),
    username="admin",
    password="123456",
    scopes=["ala:administrator"],
)

password = b64decode(AESCipher().encrypt("internal_admin").decode("utf-8"))
password = binascii.hexlify(password).decode("utf-8")

NEW_INTERNAL_USER = User(
    creation_id=ObjectId(),
    username="internal_user_test_db",
    password="123456",
    scopes=[],
    internal=True,
)
INTERNAL_ADMIN = User(
    creation_id=ObjectId(),
    username="internal_administrator",
    password=password,
    scopes=["ala:administrator"],
    internal=True,
)
INTERNAL_ADMIN_SCOPE = Scope(
    id="usr:internal_administrator",
    content=[
        {"action": "usr:get_internal_users_test_db", "policy": "allow", "resource": {}},
        {"action": "usr:add_internal_users_test_db", "policy": "allow", "resource": {}},
    ],
    internal=True,
)
NEW_SCOPE = Scope(
    id="usr:wheel",
    label="wheel",
    version=3,
    content=[
        {"action": "usr:change_password", "policy": "allow", "resource": {}},
        {"action": "usr:logout", "policy": "allow", "resource": {}},
    ],
    description="Wheel scope"
)
OLD_SCOPE = {
    "id": "usr:oldwheel",
    "label": "oldWheel",
    "content": [
        {"action": "usr:change_password", "policy": "allow", "resource": {}},
        {"action": "usr:logout", "policy": "allow", "resource": {}},
    ],
}

PMF_DEFAULT_BASIC_SCOPE_0 = Scope(
    id="pmf:apm:administrator",
    label="pmf_default_basic_scope_0",
    content=[{"scope": "pmf:apm:administrator"}, {"scope": "pmf:apmon:administrator"}],
    default=True,
    internal=False,
    title="Administrator - pmf",
    description="Scope with full permissions to manage applications, upgrade and uninstall.",
)
APP_SM_NON_DEFAULT_NON_BASIC_SCOPE_1 = Scope(
    id="sm:custom",
    version=0,
    title="Custom - sm",
    label="app_sm_non_default_non_basic_scope_1",
    description="Scope Custom",
    default=False,
    content=[{"action": "sm:pmnotif:get_version", "policy": "allow", "resource": {}}],
    internal=False,
)
APP_SM_DEFAULT_BASIC_SCOPE_2 = Scope(
    id="sm:guest",
    label="app_sm_default_basic_scope_2",
    content=[{"scope": "sm:pmnotif:guest"}],
    title="Guest - sm",
    description="Scope guest for sm",
    default=True,
    internal=False,
)
APP_SM_DEFAULT_NON_BASIC_SCOPE_3 = Scope(
    id="sm:pmnotif:administrator",
    version=0,
    title="Administrator - sm - pilot manager notifier",
    label="app_sm_default_non_basic_scope_3",
    description="Scope for all-access users on all notifier functions",
    default=True,
    content=[{"action": "sm:pmnotif:get_version", "policy": "allow", "resource": {}}],
    internal=False,
)
USR_DEFAULT_BASIC_SCOPE_4 = Scope(
    id="usr:administrator",
    label="usr_default_basic_scope_4",
    content=[{"action": "usr:disable_session", "policy": "allow", "resource": {}}],
    default=True,
    internal=False,
    title="Administrator - users",
    description="Role granting full access to all users, roles, and identity management functionalities."
)
OLD_USR_NON_DEFAULT_NON_BASIC_SCOPE_5 = Scope(
    id="usr:oldwheel",
    label="old_usr_non_default_non_basic_scope_5",
    content=[
        {"action": "usr:change_password", "policy": "allow", "resource": {}},
        {"action": "usr:logout", "policy": "allow", "resource": {}},
    ]
)
NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6 = Scope(
    id="usr:wheel",
    label="new_usr_non_default_non_basic_scope_6",
    version=3,
    content=[
        {"action": "usr:change_password", "policy": "allow", "resource": {}},
        {"action": "usr:logout", "policy": "allow", "resource": {}},
    ],
)
TEST_SCOPE = Scope(id='usr:test_scope',
                   label='usr',
                   description='description',
                   content=[{"action": "usr:get_ping",
                             "policy": "allow",
                             "resource": {}}])
MIX_SCOPE = Scope(id='usr:mix_scope', label='usr', description='description',
                  content=[{"scope": "usr:test_scope"}])

# Idp configs
IDP_LDAP_CONFIG_1 = LdapConfig(
    idp_type=IdpType.ldap.name,
    idp_name="ldap_ateme.com",
    domain="ateme.com",
    server="atm-infra.corp.ateme.com",
    search="CN=Users,DC=corp,DC=ateme,DC=com",
    group="S_SUPPORT",
    scopes=["all:administrator"],
)
IDP_LDAP_CONFIG_2 = LdapConfig(
    idp_type=IdpType.ldap.name,
    idp_name="ldap_ateme-velizy.com",
    domain="ateme-velizy.com",
    server="atm-infra.corp.ateme-velizy.com",
    search="CN=Users,DC=corp,DC=ateme,DC=com",
    group="S_SUPPORT",
)
# Other IDP config with type different from LDAP
IDP_LOCAL_CONFIG = IdpLocalConfig()

LDAP_CONFIG = LdapConfig(domain='ateme.com',
                         server='atm-infra.corp.ateme.com',
                         search='CN=Users,DC=corp,DC=ateme,DC=com',
                         group='S_SUPPORT')

# Api descriptors
PMF_API_DESCRIPTOR = ApiDescriptor(
    prefix="apm",
    app_name="pmf",
    url="http://pmf-demo-ci-application-manager-backend.pmf-demo-ci.svc.cluster.local:8080"
)
SM_API_DESCRIPTOR = ApiDescriptor(
  app_name="sm",
  prefix="pmnotif",
  url="http://sm-notifier.pmf-demo-ci.svc.cluster.local:8080"
)

# Actions
ACTION = Action(
    name="get_ping",
    prefix="usr",
    request=Request(method=RequestMethod.GET, route="/ping"),
)
INTERNAL_ACTION = Action(
    name="get_internal_users_test_db",
    prefix="usr",
    request=Request(method=RequestMethod.GET, route="/internal_users_test_db"),
    internal=True,
)
