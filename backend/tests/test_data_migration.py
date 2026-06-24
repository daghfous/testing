"""

Test migration transformation
"""
from contextlib import nullcontext as does_not_raise
from bson import ObjectId
import pytest

from ateme.updater import (
    ExportDowngradeException,
    ImportUpgradeException,
)

from ateme.um_backend.data_migration_imp import DataMigrationImp
from ateme.um_backend.types import (
    IdpType,
    DEFAULT_LOCAL_IDP_NAME
)


@pytest.mark.parametrize(
    "data, expected_downgraded_data, exception_raised",
    [
        # Ok: Downgrade from 5.0 to 4.0
        ([
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'idp_name': 'ASCENDING', 'user_id': 'ASCENDING'},
                                              {'idp_name': 'ASCENDING', 'username': 'ASCENDING'}]},
              "data": [
                  # local user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': '809c6f5139df17d4481fffc36183f4d66648a2cf',
                   'username': 'Jim',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False,
                   'idp_name': DEFAULT_LOCAL_IDP_NAME
                   },
                   # ldap user with same username as local user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': '809c6f5139df17d4481fffc36183f4d66648a2cg',
                   'username': 'Jim',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False,
                   'idp_name': "LDAP_ateme.com"
                   },
                  # ldap user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'b286fc8e2ba8ded33693981e75d39425f54844a9',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False,
                   'idp_name': "LDAP_ateme.com"
                   }
              ]},
             {"collection": "idp_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"idp_name": "ASCENDING"}]},
              "data": [{
                  'idp_type': 'ldap',
                  'idp_name': 'LDAP_ateme.com',
                  'domain': 'ateme.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
                  },
                  {
                  'idp_type': 'local',
                  'idp_name': DEFAULT_LOCAL_IDP_NAME,
                  'label': 'Local'
                  }
              ]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         [
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'user_id': 'ASCENDING'}, {'username': 'ASCENDING'}]},
              "data": [
                  # local user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                   'username': 'Jim',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'authenticate_mode': 'local',
                   'first_login': False,
                   'internal': False
                   },
                  # ldap user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'ba2f02d6a8c9a4bfc1e0bb90741c8c617c987295',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'authenticate_mode': 'ldap',
                   'first_login': False,
                   'internal': False,
                   'domain_ldap': 'ateme.com'
                   }
              ]},
             {"collection": "ldap_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"domain": "ASCENDING"}]},
              "data": [{
                  'domain': 'ateme.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }
              ]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         does_not_raise()
        ),
        # Missing idp_name
        ([
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'idp_name': 'ASCENDING', 'user_id': 'ASCENDING'},
                                              {'idp_name': 'ASCENDING', 'username': 'ASCENDING'}]},
              "data": [
                  # user without idp_name
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'fe97666064e76f0bb9d715268e2e99b5f37e1cc7',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False
                   }
              ]},
             {"collection": "idp_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"idp_name": "ASCENDING"}]},
              "data": [{
                  'idp_type': 'ldap',
                  'idp_name': 'ldap_ateme-velizy.guest.com',
                  'idp_label': 'Ldap  ateme-velizy.guest.com',
                  'domain': 'ateme-velizy.guest.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         [
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'user_id': 'ASCENDING'}, {'username': 'ASCENDING'}]},
              "data": [
                  # ldap user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': '809c6f5139df17d4481fffc36183f4d66648a2cf',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'authenticate_mode': 'ldap',
                   'first_login': False,
                   'internal': False,
                   'domain': 'ateme.com'
                   }
              ]},
             {"collection": "ldap_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"domain": "ASCENDING"}]},
              "data": [{
                  'domain': 'ateme-velizy.guest.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }
              ]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         pytest.raises(ExportDowngradeException)
        )
    ]
)
def test_downgrade_data(updater,
                        data, expected_downgraded_data, exception_raised):
    # pylint: disable=too-many-arguments,unused-argument
    """

    Test downgrade_data
    Call this method with multiple base_version/target_version and check that:
    - in case of success that "operations applied" has been added in the downgraded data with the downgraded
    operations applied on the data
    - in case of error that the expected exception has been raised
    """
    data_migration = DataMigrationImp()

    with exception_raised:
        data_migration.downgrade_from_5_0_to_4_0(data)
        assert data == expected_downgraded_data

@pytest.mark.parametrize(
    "data, expected_upgraded_data, exception_raised",
    [
        # Ok: Upgrade from 4.0 to 5.0
        ([
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'user_id': 'ASCENDING'},
                                              {'username': 'ASCENDING'}]},
              "data": [
                  # local user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'fe97666064e76f0bb9d795168e2e99b5f37e1cc7',
                   'username': 'Jim',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'authenticate_mode': 'local',
                   'first_login': False,
                   'internal': False
                   },
                  # ldap user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'b286fc8e2ba8ded33693981e75d39425f54844a9',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'authenticate_mode': 'ldap',
                   'first_login': False,
                   'internal': False,
                   'domain_ldap': "ateme.com"
                   }
              ]},
             {"collection": "ldap_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"domain": "ASCENDING"}]},
              "data": [{
                  'domain': 'ateme-velizy.guest.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         [
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'idp_name': 'ASCENDING', 'user_id': 'ASCENDING'},
                                              {'idp_name': 'ASCENDING', 'username': 'ASCENDING'}]},
              "data": [
                  # local user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': '809c6f5139df17d4481fffc36183f4d66648a2cf',
                   'username': 'Jim',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False,
                   'idp_name': DEFAULT_LOCAL_IDP_NAME
                   },
                  # ldap user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'b286fc8e2ba8ded33693981e75d39425f54844a9',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False,
                   'idp_name': 'ldap_ateme.com'
                   }
              ]},
             {"collection": "idp_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"idp_name": "ASCENDING"}]},
              "data": [{
                  'idp_type': 'ldap',
                  'idp_name': 'ldap_ateme-velizy.guest.com',
                  'idp_label': 'ldap_ateme-velizy.guest.com',
                  'domain': 'ateme-velizy.guest.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }
              ]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         does_not_raise()
        ),
        # Missing domain for ldap user
        ([
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'user_id': 'ASCENDING'},
                                              {'username': 'ASCENDING'}]},
              "data": [
                  # ldap user without domain
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'fe97666064e76f0bb9d715268e2e99b5f37e1cc7',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'authenticate_mode': 'ldap',
                   'first_login': False,
                   'internal': False
                   }
              ]},
             {"collection": "ldap_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"domain": "ASCENDING"}]},
              "data": [{
                  'domain': 'ateme-velizy.guest.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         [
             {"collection": "users",
              "import_policy": {"conflict_management": "abort",
                                'key_index': [{'idp_name': 'ASCENDING', 'user_id': 'ASCENDING'},
                                              {'idp_name': 'ASCENDING', 'username': 'ASCENDING'}]},
              "data": [
                  # ldap user
                  {'creation_id': ObjectId('63f8826a2b015ac6ae26ff1e'),
                   'user_id': 'fe97666064e76f0bb9d715268e2e99b5f37e1cc7',
                   'username': 'John',
                   'password': '123456',
                   'enabled': True,
                   'password_last_update': False,
                   'scopes': ['usr:engineer'],
                   'first_login': False,
                   'internal': False,
                   'idp_name': 'ldap_ateme.com'
                   }
              ]},
             {"collection": "idp_config",
              "import_policy": {"conflict_management": "override",
                                "key_index": [{"idp_name": "ASCENDING"}]},
              "data": [{
                  'idp_type': IdpType.ldap.name,
                  'idp_name': 'ldap_ateme.com',
                  'idp_label': 'ldap_ateme.com',
                  'domain': 'ateme-velizy.guest.com',
                  'group': 'S_GUEST',
                  'search': 'CN=Guest,DC=corp,DC=ateme,DC=com',
                  'server': 'atm-extra.guest.corp.ateme.com'
              }
              ]},
             {'collection': 'scopes',
              'import_policy': {'conflict_management': 'abort', 'key_index': [{'id': 'ASCENDING'}]},
              'data': [{
                  '_id': ObjectId('63f882712b015ac6ae26ff80'),
                  'id': 'usr:actor',
                  'label': 'Actor',
                  'version': 3,
                  'content': [
                      {'scope': 'usr:engineer'},
                      {'action': 'get_current_user'},
                      {'scope': 'usr:unexist'},
                      {'action': 'unexist'}
                  ],
                  'title': 'Actor actor'
              }]}
         ],
         pytest.raises(ImportUpgradeException)
        )
    ]
)
def test_upgrade_data(updater,
                      data, expected_upgraded_data, exception_raised):
    # pylint: disable=unused-argument
    """

    Test upgrade_data
    """
    data_migration = DataMigrationImp()

    with exception_raised:
        data_migration.upgrade_from_4_0_to_5_0(data)
        assert data == expected_upgraded_data
