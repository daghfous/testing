"""
Tests database
"""
# pylint: disable=no-member,too-many-lines,unused-argument

import asyncio
import binascii
from contextlib import nullcontext as does_not_raise
from base64 import b64decode
import copy
from datetime import datetime, timedelta
from typing import List
from unittest import mock

import pymongo
import pytest
from bson import ObjectId

from ateme.encryption_lib import AESCipher  # pylint: disable=no-name-in-module
from ateme.um_backend.database import Collections
from ateme.um_backend.data_migration_imp import DataMigrationImp
from ateme.um_backend.types import (
    Token,
    Configuration,
    User,
    Scope,
    Action,
    Request,
    RequestMethod,
    LdapConfig,
    ApiDescriptor,
    IdpType,
    DEFAULT_LOCAL_IDP_NAME,
    IdpLocalConfig
)

from .utils import (
    NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6,
    ADMIN,
    IDP_LDAP_CONFIG_1,
    IDP_LDAP_CONFIG_2,
    IDP_LOCAL_CONFIG,
    INTERNAL_ADMIN,
    NEW_INTERNAL_USER,
    NEW_USER_LDAP,
)

NEW_USER = User(creation_id=ObjectId(), username="bidule", password="123456", scopes=[])

password = b64decode(AESCipher().encrypt("internal_admin").decode("utf-8"))
password = binascii.hexlify(password).decode("utf-8")

async def test_is_database_available(init_database, mocker):
    """ Test is_database_available """
    _db = init_database
    assert await _db.is_database_available()

    def mock_list_topology_server_descriptions(*args):
        # pylint: disable=protected-access
        server =  pymongo.server_description.ServerDescription(('127.0.0.1', 40961))
        server._is_readable = True
        server._is_writable = False
        return {('127.0.0.1', 40961): server}
    mocker.patch("pymongo.topology_description.TopologyDescription.server_descriptions",
                 mock_list_topology_server_descriptions)
    assert not await _db.is_database_available()

    async def mock_list_run_admin_command(*args):
        raise pymongo.errors.ConnectionFailure
    mocker.patch("ateme.um_backend.database.Database.run_admin_command", mock_list_run_admin_command)
    assert not await _db.is_database_available()
    mocker.stopall()


async def test_update_configuration(init_database):
    """ Test update_configuration """
    _db = init_database
    await _db.insert_configuration(Configuration())
    conf = await _db.get_configuration()
    max_successive_failed_login = 5
    expiration_delay_in_days = 10
    password_min_length = 20
    await _db.update_configuration(max_successive_failed_login=max_successive_failed_login,
                                   expiration_delay_in_days=expiration_delay_in_days,
                                   password_min_length=password_min_length)
    new_conf = await _db.get_configuration()
    assert new_conf.max_successive_failed_login == max_successive_failed_login
    assert new_conf.password_policy.expiration_delay_in_days == expiration_delay_in_days
    assert new_conf.password_policy.password_min_length == password_min_length
    assert conf.logout_timeout == new_conf.logout_timeout

    # Check that configuration in db with unexpected field is properly loaded
    # patch the conf directly in db
    res = await _db.db["configuration"].update_one({}, {"$set": {"password_expiration": 1}})
    assert res.modified_count == 1
    patched_conf = await _db.db["configuration"].find_one({})
    assert "password_expiration" in patched_conf, "configuration not been properly patched"
    # read configuration thanks to Database function
    assert await _db.get_configuration()


async def test_create_user(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(NEW_USER, collection_name=Collections.users.name)
    assert res
    expected_error = None
    try:
        await _db.create_user(None, collection_name=Collections.users.name)
    except Exception as error:
        expected_error = error
    assert expected_error.args[0] == "'NoneType' object has no attribute 'to_dict'"

    res = await _db.create_user(
        NEW_INTERNAL_USER, collection_name=Collections.users.name
    )
    assert res
    res = await _db.create_user(NEW_USER_LDAP, collection_name=Collections.users.name)
    assert res
    res = await _db.create_user(INTERNAL_ADMIN, collection_name=Collections.admin.name)
    assert res


async def test_is_admin(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(NEW_USER, collection_name=Collections.users.name)
    assert res
    res = await _db.create_user(
        NEW_INTERNAL_USER, collection_name=Collections.users.name
    )
    assert res
    res = await _db.create_user(INTERNAL_ADMIN, collection_name=Collections.admin.name)
    assert res

    # use the user internal flag as internal parameter
    user = await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=NEW_USER.internal,
        idp_name=NEW_USER.idp_name,
    )
    assert user
    token = Token(
        token="123456789",
        started_date=datetime.now(),
        expiration_date=datetime.now() + timedelta(hours=1),
        refresh_token="Barthez",
        refresh_token_expiration_date=datetime.now() + timedelta(hours=2),
        user_id=user["user_id"]
    )
    assert await _db.collection_tokens.store(token)
    assert not await _db.is_admin(token.token)

    user = await _db.get_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=NEW_INTERNAL_USER.internal,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    assert user
    token = Token(
        token="987654321",
        started_date=datetime.now(),
        expiration_date=datetime.now() + timedelta(hours=1),
        refresh_token="Blanc",
        refresh_token_expiration_date=datetime.now() + timedelta(hours=2),
        user_id=user["user_id"]
    )
    assert await _db.collection_tokens.store(token)
    assert not await _db.is_admin(token.token)

    user = await _db.get_user_by_name(
        username=INTERNAL_ADMIN.username,
        internal=INTERNAL_ADMIN.internal,
        idp_name=INTERNAL_ADMIN.idp_name,
    )
    assert user
    token = Token(
        token="1234",
        started_date=datetime.now(),
        expiration_date=datetime.now() + timedelta(hours=1),
        refresh_token="Jacquet",
        refresh_token_expiration_date=datetime.now() + timedelta(hours=2),
        user_id=user["user_id"]
    )
    assert await _db.collection_tokens.store(token)
    assert await _db.is_admin(token.token)


async def test_update_user_by_name(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(NEW_USER, collection_name=Collections.users.name)
    assert res
    res = await _db.create_user(
        NEW_INTERNAL_USER, collection_name=Collections.users.name
    )
    assert res
    res = await _db.create_user(NEW_USER_LDAP, collection_name=Collections.users.name)
    assert res
    res = await _db.collection_scopes.store(NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6)
    assert res

    # Update user
    res = await _db.update_user_by_name(
        username=NEW_USER.username,
        internal=NEW_USER.internal,
        scopes=[NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id],
        idp_name=NEW_USER.idp_name,
        first_login=True,
        session_timeout_disabled=True,
        preferences={"favorite_application": "TLCN"}
    )
    assert not res
    assert isinstance(res, set)

    # Update user having an idp_name different from the DEFAULT_LOCAL_IDP_NAME one
    res = await _db.update_user_by_name(
        username=NEW_USER_LDAP.username,
        internal=NEW_USER_LDAP.internal,
        scopes=[NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id],
        idp_name=NEW_USER_LDAP.idp_name,
    )
    assert not res
    assert isinstance(res, set)

    # fail to update an internal user with non internal scope
    res = await _db.update_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=NEW_INTERNAL_USER.internal,
        scopes=[NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id],
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    assert res == {"usr:wheel"}, "internal user could not have a non internal scope"

    # Update admin
    await _db.create_user(ADMIN, Collections.admin.name)
    await _db.update_user_by_name(
        username=ADMIN.username,
        internal=ADMIN.internal,
        enabled=False,
        idp_name=ADMIN.idp_name,
    )
    assert not (await _db.get_admin_user())["enabled"]


async def test_update_user_by_name_fail(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.update_user_by_name(
        username="test",
        internal=False,
        scopes=[NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id],
        idp_name=DEFAULT_LOCAL_IDP_NAME,
    )
    assert not res
    assert isinstance(
        res, list
    ), "update_user_by_name should return a list if unknown user"
    # Fail to update a valid username but with a bad idp_name
    res = await _db.update_user_by_name(
        username=NEW_USER_LDAP.username,
        internal=NEW_USER_LDAP.internal,
        scopes=[NEW_USR_NON_DEFAULT_NON_BASIC_SCOPE_6.id],
        idp_name="invalid_idp_name",
    )
    assert not res
    assert isinstance(
        res, list
    ), "update_user_by_name should return a list if unknown user"


async def test_update_user_id_by_name(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(NEW_USER, collection_name=Collections.users.name)
    assert res
    res = await _db.create_user(
        NEW_INTERNAL_USER, collection_name=Collections.users.name
    )
    assert res
    res = await _db.create_user(NEW_USER_LDAP, collection_name=Collections.users.name)
    assert res
    res = await _db.create_user(ADMIN, Collections.admin.name)
    assert res

    # Update user id
    previous_id = await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=NEW_USER.internal,
        idp_name=NEW_USER.idp_name,
    )
    await _db.update_user_by_name(
        NEW_USER.username, password="password", idp_name=NEW_USER.idp_name
    )
    assert previous_id != await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=NEW_USER.internal,
        idp_name=NEW_USER.idp_name,
    )
    await _db.update_user_by_name(
        NEW_USER.username, password=NEW_USER.password, idp_name=NEW_USER.idp_name
    )

    # Update user id having a idp_name different from the DEFAULT_LOCAL_IDP_NAME one
    previous_id = await _db.get_user_by_name(
        username=NEW_USER_LDAP.username,
        internal=NEW_USER_LDAP.internal,
        idp_name=NEW_USER_LDAP.idp_name,
    )
    await _db.update_user_by_name(
        NEW_USER_LDAP.username, password="password", idp_name=NEW_USER_LDAP.idp_name
    )
    assert previous_id != await _db.get_user_by_name(
        username=NEW_USER_LDAP.username,
        internal=NEW_USER_LDAP.internal,
        idp_name=NEW_USER_LDAP.idp_name,
    )
    await _db.update_user_by_name(
        NEW_USER_LDAP.username,
        password=NEW_USER_LDAP.password,
        idp_name=NEW_USER_LDAP.idp_name,
    )

    # Update internal user id
    previous_id = await _db.get_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=NEW_INTERNAL_USER.internal,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    await _db.update_user_by_name(
        NEW_INTERNAL_USER.username,
        password="password",
        idp_name=NEW_INTERNAL_USER.idp_name,
        internal=True,
    )
    assert previous_id != await _db.get_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=NEW_INTERNAL_USER.internal,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    await _db.update_user_by_name(
        NEW_INTERNAL_USER.username,
        password=NEW_INTERNAL_USER.password,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )

    # Update admin id
    previous_id = (await _db.get_admin_user())["user_id"]
    await _db.update_user_by_name(
        ADMIN.username, password="password", idp_name=ADMIN.idp_name
    )
    assert previous_id != (await _db.get_admin_user())["user_id"]
    await _db.db[Collections.admin.name].delete_one({"username": ADMIN.username})


async def test_store_idp_config(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_1.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_2.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LOCAL_CONFIG.to_dict())
    assert res, "result of insert idp_config should be defined"
    # Fail to insert a duplicate
    with pytest.raises(pymongo.errors.DuplicateKeyError):
        res = await _db.store_idp_config(IDP_LDAP_CONFIG_1.to_dict())


async def test_get_idp_config(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_1.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_2.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LOCAL_CONFIG.to_dict())
    assert res, "result of insert idp_config should be defined"

    idp_configs = await _db.get_idp_configs()
    assert idp_configs, "idp_configs result should be defined"
    assert isinstance(idp_configs, List), "idp_configs should be a List"
    assert len(idp_configs) == 3, "idp_configs should be gt 0"
    assert isinstance(
        idp_configs[0], LdapConfig
    ), "Item 0 in list should type of LdapConfig"
    assert (
        idp_configs[0].to_dict() == IDP_LDAP_CONFIG_1.to_dict()
    ), "Item 0 in list should equal to IDP_LDAP_CONFIG_1"
    assert isinstance(
        idp_configs[1], LdapConfig
    ), "Item 1 in list should type of LdapConfig"
    assert (
        idp_configs[1].to_dict() == IDP_LDAP_CONFIG_2.to_dict()
    ), "Item 1 in list should equal to IDP_LDAP_CONFIG_1"
    assert isinstance(
        idp_configs[2], IdpLocalConfig
    ), "Item 2 in list should type of IdpLocalConfig"
    assert (
        idp_configs[2].to_dict() == IDP_LOCAL_CONFIG.to_dict()
    ), "Item 2 in list should equal to IDP_LOCAL_CONFIG"


async def test_get_idp_config_by_type(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_1.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_2.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LOCAL_CONFIG.to_dict())
    assert res, "result of insert idp_config should be defined"

    ldap_configs = await _db.get_idp_configs_by_type(idp_type=IdpType.ldap.name)
    assert ldap_configs, "ldap_configs result should be defined"
    assert isinstance(ldap_configs, List), "ldap_configs should be a list"
    nb_ldap_configs = len(ldap_configs)
    assert nb_ldap_configs == 2, "ldap_configs list should be gt 0"
    assert isinstance(
        ldap_configs[0], LdapConfig
    ), "Item 1 in list should type of LdapConfig"
    assert (
        ldap_configs[0].to_dict() == IDP_LDAP_CONFIG_1.to_dict()
    ), "Item 1 in list should equal to IDP_LDAP_CONFIG_1"
    assert isinstance(
        ldap_configs[1], LdapConfig
    ), "Item 2 in list should type of LdapConfig"
    assert (
        ldap_configs[1].to_dict() == IDP_LDAP_CONFIG_2.to_dict()
    ), "Item 2 in list should equal to IDP_LDAP_CONFIG_2"

    local_configs = await _db.get_idp_configs_by_type(idp_type=IdpType.local.name)
    assert isinstance(local_configs, List), "local_configs should be a list"
    nb_local_configs = len(local_configs)
    assert nb_local_configs == 1, "local_configs list should not be empty"
    assert isinstance(
        local_configs[0], IdpLocalConfig
    ), "Item in list should type of IdpLocalConfig"
    assert (
        local_configs[0].to_dict() == IDP_LOCAL_CONFIG.to_dict()
    ), "Item in list should type of local_configs"

    all_configs = await _db.get_idp_configs_by_type()
    assert (
        len(all_configs) == nb_local_configs + nb_ldap_configs
    ), "idp_config list should not be empty"
    assert all(
        isinstance(idp_config, (LdapConfig, IdpLocalConfig))
        for idp_config in all_configs
    )


async def test_get_idp_config_by_name(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_1.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_2.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LOCAL_CONFIG.to_dict())
    assert res, "result of insert idp_config should be defined"

    idp_ldap_name = DataMigrationImp.compute_idp_name_from_domain(
        IDP_LDAP_CONFIG_2.domain
    )
    ldap_config = await _db.get_idp_config_by_name(idp_name=idp_ldap_name)
    assert ldap_config, "ldap_config result should be defined"
    assert isinstance(ldap_config, LdapConfig), "ldap_config should be a LdapConfig"
    assert (
        ldap_config.to_dict() == IDP_LDAP_CONFIG_2.to_dict()
    ), "2nd Item in list should equal to IDP_LDAP_CONFIG_2"

    other_config = await _db.get_idp_config_by_name(idp_name="unknown")
    assert not other_config, "other_config result should not be defined"


async def test_update_ip_config(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_1.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LDAP_CONFIG_2.to_dict())
    assert res, "result of insert idp_config should be defined"
    res = await _db.store_idp_config(IDP_LOCAL_CONFIG.to_dict())
    assert res, "result of insert idp_config should be defined"

    domain = IDP_LDAP_CONFIG_1.domain
    idp_name = DataMigrationImp.compute_idp_name_from_domain(domain)
    new_server = "example.com"
    new_scopes = ["usr:guest", "usr:administrator"]
    data = {"server": new_server, "scopes": new_scopes}
    res = await _db.update_idp_config(idp_name=idp_name, data=data)
    assert res, "result from update_ip_config should be defined"

    ldap_config = await _db.get_idp_config_by_name(idp_name)
    assert ldap_config, "ldap_config result should be defined"
    assert ldap_config.server == new_server, "ldap_config should have the new server"
    assert ldap_config.domain == IDP_LDAP_CONFIG_1.domain
    assert ldap_config.search == IDP_LDAP_CONFIG_1.search
    assert ldap_config.group == IDP_LDAP_CONFIG_1.group
    assert ldap_config.use_ssl == IDP_LDAP_CONFIG_1.use_ssl
    assert ldap_config.scopes == new_scopes, "ldap_config should have the new scopes"


@pytest.mark.parametrize(
    "given, expected, scope_presence",
    [
        pytest.param([], [], True, id="empty-list"),
        pytest.param(
            [
                {
                    "_id": "000000000000000000000001",
                    "type": "direct",
                    "attribute_name": "property",
                }
            ],
            [
                {
                    "_id": ObjectId("000000000000000000000001"),
                    "type": "direct",
                    "attribute_name": "property",
                }
            ],
            True,
            id="direct-mapper",
        ),
        pytest.param(
            [
                {
                    "_id": "000000000000000000000002",
                    "type": "simple",
                    "attribute_name": "property",
                    "attribute_value": "value",
                    "scopes_to_add": ["all:guest"],
                }
            ],
            [
                {
                    "_id": ObjectId("000000000000000000000002"),
                    "type": "simple",
                    "attribute_name": "property",
                    "attribute_value": "value",
                    "scopes_to_add": ["all:guest"],
                }
            ],
            True,
            id="simple-mapper",
        ),
        pytest.param(
            [
                {
                    "_id": "000000000000000000000003",
                    "type": "simple",
                    "attribute_name": "property",
                    "attribute_value": "value",
                    "scopes_to_add": ["all:guest", "all:guest"],
                }
            ],
            [
                {
                    "_id": ObjectId("000000000000000000000003"),
                    "type": "simple",
                    "attribute_name": "property",
                    "attribute_value": "value",
                    "scopes_to_add": ["all:guest"],
                }
            ],
            True,
            id="duplicated-scope",
        ),
        pytest.param(
            [
                {
                    "_id": "000000000000000000000004",
                    "type": "simple",
                    "attribute_name": "property",
                    "attribute_value": "value",
                    "scopes_to_add": ["all:guest", "all:guest"],
                }
            ],
            [
                {
                    "_id": ObjectId("000000000000000000000004"),
                    "type": "simple",
                    "attribute_name": "property",
                    "attribute_value": "value",
                    "scopes_to_add": [],
                }
            ],
            False,
            id="no-scope",
        ),
    ],
)
async def test_prepare_idp_mappers(
    init_database, given, expected, scope_presence
):
    """
    Test prepare_idp_mappers method
    """
    _db = init_database
    with mock.patch(
        "ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id", return_value=scope_presence
    ):
        await _db.prepare_idp_mappers(given)
    assert given == expected


async def test_prepare_idp_mappers_no_id(init_database):
    """
    Test prepare_idp_mappers method. Check ID generation for mappers.
    """
    _db = init_database
    given = [
        {"type": "direct", "attribute_name": "property"},
        {
            "type": "simple",
            "attribute_name": "property",
            "attribute_value": "value",
            "scopes_to_add": ["all:guest"],
        },
    ]
    expected = copy.deepcopy(given)
    future = asyncio.Future()
    future.set_result(True)
    with mock.patch("ateme.um_backend.dao.collection_scopes.CollectionScopes.get_by_id", return_value=future):
        await _db.prepare_idp_mappers(given)
    ids = [mapper.pop("_id") for mapper in given]
    assert given == expected
    assert len(ids) == 2
    for id_ in ids:
        assert isinstance(id_, ObjectId)


async def test_remove_idp_config(init_database):
    """

    :return:
    """
    _db = init_database
    domain = IDP_LDAP_CONFIG_1.domain
    idp_name = DataMigrationImp.compute_idp_name_from_domain(domain)
    res = await _db.remove_idp_config(idp_name=idp_name)
    assert res, "result from remove_idp_config should be defined"
    ldap_config = await _db.get_idp_config_by_name(idp_name=idp_name)
    assert not ldap_config, "Should be deleted"


async def test_get_all_users(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(
        NEW_INTERNAL_USER, collection_name=Collections.users.name
    )
    assert res

    # without internal users
    users = await _db.get_all_users()
    assert not users, "users return should be defined"
    assert all(
        user["username"] != NEW_INTERNAL_USER.username for user in users
    ), "internal users should not be returned"
    # with internal users
    users = await _db.get_all_users(internal=True)
    assert users, "users return should be defined"
    assert any(
        user["username"] == NEW_INTERNAL_USER.username for user in users
    ), "internal users should be returned"


async def test_get_user_by_name(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(
        NEW_INTERNAL_USER, collection_name=Collections.users.name
    )
    assert res
    res = await _db.create_user(NEW_USER, collection_name=Collections.users.name)
    assert res

    user = await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=NEW_USER.internal,
        idp_name=NEW_USER.idp_name,
    )
    assert user, "user return should exist"
    assert isinstance(user, dict), "user should type of dict"
    assert user.get("username") == NEW_USER.username

    user = await _db.get_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=NEW_INTERNAL_USER.internal,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    assert user, "internal user return should exist"
    assert isinstance(user, dict), "internal user should type of dict"
    assert user.get("username") == NEW_INTERNAL_USER.username
    assert not user.get("internal"), "internal flag should not be returned"

    user = await _db.get_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=NEW_INTERNAL_USER.internal,
        internal_projection=True,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    assert user, "internal user return should exist"
    assert isinstance(user, dict), "internal user should type of dict"
    assert user.get("username") == NEW_INTERNAL_USER.username
    assert (
        user.get("internal") == NEW_INTERNAL_USER.internal
    ), "internal should be set to TRUE"

    user = await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=INTERNAL_ADMIN.internal,
        idp_name=NEW_USER.idp_name,
    )
    assert not user, "user should not be returned"

    user = await _db.get_user_by_name(
        username=NEW_INTERNAL_USER.username,
        internal=ADMIN.internal,
        idp_name=NEW_INTERNAL_USER.idp_name,
    )
    assert not user, "internal user should not be returned"
    # with all_users param set to True, internal param is not taken into account
    user = await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=INTERNAL_ADMIN.internal,
        all_users=True,
        idp_name=NEW_USER.idp_name,
    )
    assert user, "user return should exist"
    assert isinstance(user, dict), "user should type of dict"
    assert user.get("username") == NEW_USER.username


async def test_update_user_by_id(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(NEW_USER, collection_name=Collections.users.name)
    assert res

    NEW_USER.scopes = ["usr:wheel", "usr:default_users_scope"]
    await _db.update_user_by_id(NEW_USER.user_id, NEW_USER)
    user = await _db.get_user_by_name(
        username=NEW_USER.username,
        internal=NEW_USER.internal,
        idp_name=NEW_USER.idp_name,
    )
    assert user, "user return should be delete"
    assert isinstance(user, dict), "user should type of dict"
    assert user.get("username") == NEW_USER.username
    assert user.get("scopes") == ["usr:wheel", "usr:default_users_scope"]


async def test_count_documents(init_database):
    """

    :return:
    """
    _db = init_database
    res = await _db.create_user(ADMIN, Collections.admin.name)
    assert res

    count = await _db.db[Collections.admin.name].count_documents({})
    assert count == 1

    admin = User(
        creation_id=ObjectId(),
        username="zizou",
        password="numero_10",
        scopes=["administrator"],
    )
    await _db.create_user(admin, Collections.admin.name)

    count = await _db.db[Collections.admin.name].count_documents({})
    assert count == 2

    await _db.db[Collections.admin.name].delete_many({})

    count = await _db.db[Collections.admin.name].count_documents({})
    assert count == 0


async def test_re_initialize_db(init_database, mocker):
    """
    See if the collection are not recreated or if it throws an error
    """
    _db = init_database

    # mock list_collection_names to force the collections re-creation
    async def _mock_list_collection_names(*_):
        """ mock list_collection_names to return an empty list
        """
        return []

    mocker.patch(
        "pymongo.asynchronous.database.AsyncDatabase.list_collection_names",
        _mock_list_collection_names
    )
    with does_not_raise():
        await _db.initialize()


async def test_remove_user_by_domain(init_database):
    """
    remove a user by domain
    """
    _db = init_database
    # Create an user and add it to a domain
    domain_ldap = "ateme.com"
    idp_name = DataMigrationImp.compute_idp_name_from_domain(domain_ldap)
    user = User(
        creation_id=ObjectId(),
        username="testuser",
        password="123456",
        scopes=["usr:guest"],
        idp_name=idp_name,
    )

    res = await _db.create_user(user, collection_name=Collections.users.name)
    assert res

    # Remove user by idp_name
    removed_user_by_idp_name = await _db.delete_users_by_idp_name(idp_name=idp_name)
    assert removed_user_by_idp_name.deleted_count == 1


async def test_update_users_scopes_by_ldap_domain(init_database):
    """
    Update users scope for a given ldap domain
    """
    _db = init_database
    domain = "ateme.com"
    idp_name = DataMigrationImp.compute_idp_name_from_domain(domain)
    new_scopes = ["usr:administrator"]
    # Create two users and add them to a domain
    user = User(
        creation_id=ObjectId(),
        username="testuser",
        password="123456",
        scopes=["usr:guest"],
        idp_name=idp_name,
    )
    res = await _db.create_user(user, collection_name=Collections.users.name)
    assert res
    user_2 = User(
        creation_id=ObjectId(),
        username="testuser_2",
        password="123456",
        scopes=["usr:guest"],
        idp_name=idp_name,
    )
    res = await _db.create_user(user_2, collection_name=Collections.users.name)
    assert res

    # Update users scopes
    res = await _db.update_users_by_idp_scopes(idp_name=idp_name, scopes=new_scopes)
    assert res

    # Get the 2 user info
    user = await _db.get_user_by_name(
        username=user.username, internal=False, idp_name=idp_name
    )
    assert user["scopes"] == new_scopes, "Update was not succesfull"
    user_2 = await _db.get_user_by_name(
        username=user_2.username, internal=False, idp_name=idp_name
    )
    assert user_2["scopes"] == new_scopes, "Update was not succesfull"


@pytest.mark.parametrize(
    "import_policy, data, filter_expected",
    [
        (
            {"conflict_management": "override", "key_index": [{"id": "ASCENDING"}]},
            {"id": "123456"},
            {"$and": [{"id": "123456"}]},
        ),
        (
            {
                "conflict_management": "override",
                "key_index": [
                    {"id": "ASCENDING", "prefix": "ASCENDING"},
                    {"user_id": "ASCENDING"},
                ],
            },
            {"id": "123456", "prefix": "aaa", "data": "aaa", "user_id": "123456"},
            {"$and": [{"id": "123456", "prefix": "aaa"}, {"user_id": "123456"}]},
        ),
        (
            {
                "conflict_management": "override",
                "key_index": [{"id": "ASCENDING", "prefix": "ASCENDING"}],
            },
            {"id": "123456", "prefix": "aaa", "data": "aaa"},
            {"$and": [{"id": "123456", "prefix": "aaa"}]},
        ),
        (
            {"conflict_management": "override", "key_index": []},
            {"id": "123456", "prefix": "aaa", "data": "aaa"},
            {},
        ),
        pytest.param(
            {
                "conflict_management": "override",
                "key_index": [{"id": "ASCENDING", "prefix": "ASCENDING"}],
            },
            {"prefix": "aaa", "data": "aaa"},
            None,
            marks=pytest.mark.xfail(raises=KeyError, strict=True),
        ),
    ],
)
def test_generate_filter_from_import_policy(
    init_database, import_policy, data, filter_expected
):
    """

    Check if we generate the right mongo filter from an import policy
    """
    _db = init_database
    # pylint: disable=protected-access
    _filter = _db._generate_filter_from_import_policy(import_policy, data)
    assert _filter == filter_expected


@pytest.mark.parametrize(
    "import_policy, data, operations_expected",
    [
        (
            {"conflict_management": "override", "key_index": [{"id": "ASCENDING"}]},
            [{"id": "123456"}],
            [pymongo.ReplaceOne({"$and": [{"id": "123456"}]}, {"id": "123456"}, True)],
        ),
        (
            {"conflict_management": "abort", "key_index": [{"id": "ASCENDING"}]},
            [{"id": "123456"}],
            [pymongo.InsertOne({"id": "123456"})],
        ),
    ],
)
def test_generate_bulk_write(
    init_database, import_policy, data, operations_expected
):
    """

    Check if we generate the right bulk write operations
    """
    # pylint: disable=protected-access
    _db = init_database
    operations = _db._generate_bulk_write(import_policy, data, "scopes")
    assert operations == operations_expected


@pytest.mark.parametrize(
    "initial_scope_in_db, actions, scopes, api_descriptors,"
    "scope_filter, expected_scopes_after_update, expected_scopes_after_remove,"
    "expected_hat_scopes_content_after_update, expected_hat_scopes_content_after_remove",
    [
        pytest.param(
            None,
            [
                Action(
                    name="upgrade",
                    description="Upgrade",
                    label="Test - Upgrade",
                    prefix="apm",
                    request=Request(method=RequestMethod.GET, route="/upgrade"),
                ),
                Action(
                    name="get_threshold",
                    description="Get threshold",
                    label="Test - Get threshold",
                    prefix="sysm",
                    request=Request(method=RequestMethod.GET, route="/threshold"),
                ),
            ],
            [
                Scope(
                    id="apm:administrator",
                    label="apm",
                    version=3,
                    content=[
                        {"action": "apm:upgrade", "policy": "allow", "resource": {}}
                    ],
                ),
                Scope(
                    id="sysm:administrator",
                    label="sysm",
                    version=3,
                    content=[
                        {"action": "sysm:threshold", "policy": "allow", "resource": {}}
                    ],
                ),
            ],
            [ApiDescriptor(prefix="test", url="http://alarm-ext.cluster")],
            {"id": {"$regex": "^(apm:administrator|sysm:administrator)$"}},
            [{"id": "apm:administrator"}, {"id": "sysm:administrator"}],
            [],
            {
                "all:administrator": [
                    {"scope": "apm:administrator"},
                    {"scope": "sysm:administrator"},
                ],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            {
                "all:administrator": [],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            id="only-default-scopes",
        ),
        pytest.param(
            None,
            [
                Action(
                    name="upgrade",
                    description="Upgrade",
                    label="Test - Upgrade",
                    prefix="apm",
                    request=Request(method=RequestMethod.GET, route="/upgrade"),
                ),
                Action(
                    name="get_threshold",
                    description="Get threshold",
                    label="Test - Get threshold",
                    prefix="sysm",
                    request=Request(method=RequestMethod.GET, route="/threshold"),
                ),
            ],
            [
                Scope(
                    id="tlcna:apm:administrator",
                    label="apm",
                    version=3,
                    content=[
                        {"action": "apm:upgrade", "policy": "allow", "resource": {}}
                    ],
                ),
                Scope(
                    id="tlcna:sysm:administrator",
                    label="sysm",
                    version=3,
                    content=[
                        {"action": "sysm:threshold", "policy": "allow", "resource": {}}
                    ],
                ),
            ],
            [
                ApiDescriptor(
                    prefix="test", url="http://alarm-ext.cluster", app_name="tlcna"
                )
            ],
            {"id": {"$regex": "^tlcna:"}},
            [
                {"id": "tlcna:apm:administrator"},
                {"id": "tlcna:sysm:administrator"},
                {"id": "tlcna:administrator"},
            ],
            [],
            {
                "all:administrator": [{"scope": "tlcna:administrator"}],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            {
                "all:administrator": [],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            id="only-level3-scopes",
        ),
        pytest.param(
            Scope(
                id="tlcna:guest",
                label="tlcna",
                version=3,
                content=[
                    {"scope": "tlcna:alamext:guest", "policy": "allow", "resource": {}}
                ],
            ),
            [
                Action(
                    name="upgrade",
                    description="Upgrade",
                    label="Test - Upgrade",
                    prefix="apm",
                    request=Request(method=RequestMethod.GET, route="/upgrade"),
                ),
                Action(
                    name="get_threshold",
                    description="Get threshold",
                    label="Test - Get threshold",
                    prefix="sysm",
                    request=Request(method=RequestMethod.GET, route="/threshold"),
                ),
            ],
            [
                Scope(
                    id="tlcna:administrator",
                    label="tlcna - app scope",
                    version=3,
                    content=[
                        {
                            "scope": "tlcna:alamext:admin",
                            "policy": "allow",
                            "resource": {},
                        }
                    ],
                ),
                Scope(
                    id="tlcna:apm:administrator",
                    label="apm",
                    version=3,
                    content=[
                        {"action": "apm:upgrade", "policy": "allow", "resource": {}}
                    ],
                ),
                Scope(
                    id="tlcna:sysm:administrator",
                    label="sysm",
                    version=3,
                    content=[
                        {"action": "sysm:threshold", "policy": "allow", "resource": {}}
                    ],
                ),
            ],
            [
                ApiDescriptor(
                    prefix="test", url="http://alarm-ext.cluster", app_name="tlcna"
                )
            ],
            {"id": {"$regex": "^tlcna:"}},
            [
                {"id": "tlcna:apm:administrator"},
                {"id": "tlcna:sysm:administrator"},
                {"id": "tlcna:administrator"},
                {"id": "tlcna:guest"},
            ],
            [{"id": "tlcna:guest"}],
            {
                "all:administrator": [{"scope": "tlcna:administrator"}],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            {
                "all:administrator": [],
                "all:engineer": [],
                "all:operator": [],
                "all:monitoring": [],
                "all:guest": [],
            },
            id="mixed-app-scope-level3-scopes-with-initial-app-scope",
        ),
    ],
)
async def test_update_auth_data(
    init_database,
    initial_scope_in_db,
    actions,
    scopes,
    api_descriptors,
    scope_filter,
    expected_scopes_after_update,
    expected_scopes_after_remove,
    expected_hat_scopes_content_after_update,
    expected_hat_scopes_content_after_remove,
):
    """

    Test update_auth_data and remove_auth_data function
    """
    # pylint: disable=too-many-arguments,too-many-locals,too-many-positional-arguments
    _db = init_database
    if initial_scope_in_db:
        res = await _db.db[Collections.scopes.name].insert_one(
            initial_scope_in_db.to_dict()
        )
        assert res and res.acknowledged, "The initial scope could not be inserted"
    scopes_in_db = (
        await _db.db[Collections.scopes.name].find(scope_filter).to_list(None)
    )
    if initial_scope_in_db:
        assert len(scopes_in_db) == len(
            [initial_scope_in_db]
        ), "Only the initial scope should be present in database at init"
    else:
        assert not scopes_in_db

    await _db.update_auth_data(actions, scopes, api_descriptors)
    scopes_in_db = (
        await _db.db[Collections.scopes.name]
        .find(scope_filter, projection={"id": 1, "_id": 0})
        .to_list(None)
    )
    assert all(
        scope in scopes_in_db for scope in expected_scopes_after_update
    ), "All expected scopes should be present in database after update"
    assert len(scopes_in_db) == len(
        expected_scopes_after_update
    ), "Scopes nb in database should match expected scopes nb"

    action_count = await _db.db[Collections.actions.name].count_documents(
        {"label": {"$regex": "^Test"}}
    )
    assert action_count == 2

    api_descriptor_count = await _db.db[
        Collections.api_descriptors.name
    ].count_documents({"prefix": "test"})
    assert api_descriptor_count == 1

    hat_scopes_in_db = await (
        _db.db[Collections.scopes.name]
        .find({"id": {"$regex": "^all:"}}, projection={"id": 1, "content": 1, "_id": 0})
        .to_list(None)
    )
    assert all(
        hat_scope_in_db["content"]
        == expected_hat_scopes_content_after_update[hat_scope_in_db["id"]]
        for hat_scope_in_db in hat_scopes_in_db
    )

    # Remove auth data: All scopes, actions and api-descriptor should have been removed except
    # app scopes that are not empty
    await _db.remove_auth_data(actions, scopes, api_descriptors)

    scopes_in_db = (
        await _db.db[Collections.scopes.name]
        .find(scope_filter, projection={"id": 1, "_id": 0})
        .to_list(None)
    )
    assert scopes_in_db == expected_scopes_after_remove
    hat_scopes_in_db = await (
        _db.db[Collections.scopes.name]
        .find({"id": {"$regex": "^all:"}}, projection={"id": 1, "content": 1, "_id": 0})
        .to_list(None)
    )
    assert all(
        hat_scope_in_db["content"]
        == expected_hat_scopes_content_after_remove[hat_scope_in_db["id"]]
        for hat_scope_in_db in hat_scopes_in_db
    )

    action_count = await _db.db[Collections.actions.name].count_documents(
        {"label": {"$regex": "^Test"}}
    )
    assert action_count == 0

    api_descriptor_count = await _db.db[
        Collections.api_descriptors.name
    ].count_documents({"prefix": "test"})
    assert api_descriptor_count == 0


@pytest.mark.parametrize("init_users", [
    pytest.param(
        [
            User(
                creation_id=ObjectId(),
                username="bidule",
                password="123456",
                scopes=[],
                password_expiration_disabled=False),
            User(
                creation_id=ObjectId(),
                username="bidule2",
                password="123456",
                scopes=[],
                password_expiration_disabled=True),
        ],
    ),
])
async def test_force_password_expiration_for_local_users(
        init_database,
        init_users
):
    """
    Test force_password_expiration_for_local_users function
    """
    _db = init_database
    # Insert two users:
    # First user with password_expiration_disabled = True
    # Second user with password_expiration_disabled = False
    for _user in init_users:
        await _db.db[Collections.users.name].insert_one(_user.to_dict())

    # Update users to have password_expired=True
    await _db.force_password_expiration_for_local_users()
    # User 1 should have password_expired set to True
    user_1 = await _db.get_user_by_name(username=init_users[0].username, idp_name=DEFAULT_LOCAL_IDP_NAME)
    assert user_1['password_expired'] is True
    # User 2 should have password_expired set to False
    user_2 = await _db.get_user_by_name(username=init_users[1].username, idp_name=DEFAULT_LOCAL_IDP_NAME)
    assert user_2['password_expired'] is False
