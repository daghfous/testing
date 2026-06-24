"""

Test roles_mapper.py
"""
from contextlib import ExitStack as does_not_raise
from typing import ContextManager, List

import pytest

from ateme.um_backend.roles_mapper import (
    retrieve_scopes_from_roles_mapper,
    Attributes
)
from ateme.um_backend.types import (
    RolesMapper,
    DirectRolesMapper,
    SimpleRolesMapper
)


@pytest.mark.parametrize(
    "mappers, attributes, scopes_expected",
    [
        pytest.param(
            [DirectRolesMapper(attribute_name="roles")],
            Attributes({"roles": "usr:engineer", "username": "john.doe@evilcorp.org"}),
            ["usr:engineer"],
            id='direct-mapper-str-attribute'
        ),
        pytest.param(
            [DirectRolesMapper(attribute_name="roles")],
            Attributes({"roles": ["usr:engineer", "all:operator"], "username": "john.doe@evilcorp.org"}),
            ["usr:engineer", "all:operator"],
            id='direct-mapper-list-attribute'
        ),
        pytest.param(
            [DirectRolesMapper(attribute_name="scopes")],
            Attributes({"roles": ["usr:engineer", "all:operator"], "username": "john.doe@evilcorp.org"}),
            [],
            id='direct-mapper-not-matching'
        ),
        pytest.param(
            [DirectRolesMapper(attribute_name="roles.test")],
            Attributes({"roles": "test", "username": "john.doe@evilcorp.org"}),
            [],
            id='direct-mapper-not-found'
        ),
        pytest.param(
            [DirectRolesMapper(attribute_name="roles.test")],
            Attributes({"roles": {"test": ["usr:engineer"]}, "username": "john.doe@evilcorp.org"}),
            ["usr:engineer"],
            id='direct-mapper-nested-property'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': 'roles', 'value': 'test'}],
                    scopes_to_add=["all:administrator"]
                )
            ],
            Attributes({"roles": "test123", "username": "john.doe@evilcorp.org"}),
            [],
            id='simple-mapper-value-not-equal'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': 'common_name', 'value': 'admin'}],
                    scopes_to_add=["all:administrator"]
                )
            ],
            Attributes({"username": "john.doe@evilcorp.org", "common_name": "admin"}),
            ["all:administrator"],
            id='simple-mapper-simple-attribute'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': 'common.name', 'value': 'admin'}],
                    scopes_to_add=["all:administrator"]
                ),
                SimpleRolesMapper(
                    attributes=[{'name': 'common.name', 'value': 'user'}],
                    scopes_to_add=["all:usr"]
                )
            ],
            Attributes({"username": "john.doe@evilcorp.org", "common": {"name": "admin"}}),
            ["all:administrator"],
            id='simple-mapper-multiple-nested-attribute'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': r'common.name\.with\.dot', 'value': 'admin'}],
                    scopes_to_add=["all:administrator", "all:operator"])
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name.with.dot": "admin"}}),
            ["all:administrator", "all:operator"],
            id='simple-mapper-nested-attribute-with-dot'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': r'common.name\.with\.dot', 'value': 'admin'}],
                    scopes_to_add=["all:administrator", "all:operator"])
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name": {"with": {"dot": "admin"}}}}),
            [],
            id='simple-mapper-not-matching'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': 'common.name', 'value': 'admin'}],
                    scopes_to_add=["all:administrator"]
                ),
                SimpleRolesMapper(
                    attributes=[{'name': 'common.name', 'value': 'user'}],
                    scopes_to_add=["all:usr"])
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name": ['admin', 'user']}}),
            ["all:administrator", "all:usr"],
            id='simple-mapper-matching-in-list'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[{'name': 'ou', 'value': 'Administrators'}],
                    scopes_to_add=["all:administrator"]
                ),
                SimpleRolesMapper(
                    attributes=[{'name': 'objectclass', 'value': 'organizationalPerson'}],
                    scopes_to_add=["all:usr"])
            ],
            Attributes(
                {
                    "username": "jane.doe@evilcorp.org",
                    "ou": "Administrators",
                    "objectclass": "organizationalPerson",
                }
            ),
            ["all:administrator", "all:usr"],
            id='simple-mapper-matching-in-list-different-attributes'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[
                        {'name': 'common.name', 'value': 'pmf'},
                        {'name': 'common.role', 'value': 'admin'}
                    ],
                    scopes_to_add=["all:administrator"]
                ),
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name": 'pmf', "role": ['admin', 'user']}}),
            ["all:administrator"],
            id='simple-mapper-multiple-attributes-match'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[
                        {'name': 'common.name', 'value': 'pmf'},
                        {'name': 'common.role', 'value': 'admin'}
                    ],
                    scopes_to_add=["all:administrator"]
                ),
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name": 'pmf', "role": ['user']}}),
            [],
            id='simple-mapper-multiple-attributes-not-match'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[
                        {'name': 'common.name', 'value': 'pmf'},
                        {'name': 'common.role', 'value': 'admin'}
                    ],
                    scopes_to_add=["all:administrator"]
                ),
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name": 'mss', "role": ['user']}}),
            [],
            id='simple-mapper-multiple-attributes-none-match'
        ),
        pytest.param(
            [
                SimpleRolesMapper(
                    attributes=[
                        {'name': 'common.name', 'value': 'pmf'},
                        {'name': 'common.role', 'value': 'admin'}
                    ],
                    scopes_to_add=["all:administrator"]
                ),
            ],
            Attributes({"username": "jane.doe@evilcorp.org", "common": {"name": 'pmf', "roles": ['admin', 'user']}}),
            [],
            id='simple-mapper-multiple-attributes-attribute-name-absent'
        ),
    ],
)
def test_retrieve_scopes_from_roles_mapper(
    mappers: List[RolesMapper], attributes: Attributes, scopes_expected: List[str]
):
    """

    test retrieve_scopes_from_roles_mapper:
        * check that we retrive scopes from an 'Attributes' instance and a list of 'RolesMapper'

    Args:
        mappers (List[RolesMapper]): List of mapper to evaluate
        attributes (Attributes): Attribute to test
        scopes_expected (List[str]): List of scope ref expected

    """
    assert sorted(retrieve_scopes_from_roles_mapper(mappers, attributes)) == sorted(scopes_expected)


@pytest.mark.parametrize(
    "path, path_splitted_expected",
    [
        ("user.name", ["user", "name"]),
        (r"user.na\.me", ["user", "na.me"]),
        ("user", ["user"]),
    ],
)
def test__split_path(path: str, path_splitted_expected: List[str]):
    """

    test Attributes.__split_path function

    Args:
        path (str): path to access, can be nested with '.'
        path_splitted_expected (List[str]): List of sub path expected

    """
    assert Attributes.split_path(path) == path_splitted_expected


@pytest.mark.parametrize(
    "attributes, key, contains, getter_expected, getter_exception_expected",
    [
        (Attributes({"user": {"name": "johndoe"}}), "user.name", True, "johndoe", does_not_raise()),
        (
            Attributes({"user": {"name": "johndoe"}}),
            "user.name.full",
            False,
            None,
            pytest.raises(KeyError, match="Can't find path user.name.full in attribute"),
        ),
        (
            Attributes({"user": {"name": "johndoe"}}),
            "user",
            True,
            {"name": "johndoe"},
            does_not_raise()
        ),
        (
            Attributes({"user": {"name": "johndoe"}}),
            "users",
            False,
            None,
            pytest.raises(KeyError, match="'users'"),
        ),
        (
            Attributes({"user": {"na.me": "johndoe"}}),
            r"user.na\.me",
            True,
            "johndoe",
            does_not_raise()
        ),
    ],
)
def test_attributes_contains_and_getter(
    attributes: Attributes,
    key: str,
    contains: bool,
    getter_expected: str,
    getter_exception_expected: ContextManager[object],
):
    """

    Check __contains__ and __getter__ function on Attributes class.

    Args:
        attributes (Attributes): Attributes to test.
        key (str): Path to access.
        contains (bool): Check if we must find the key.
        getter_expected (str): Value of getter expected.
        getter_exception_expected (ContextManager[object]): Exception expcted, direct accessor may raise a 'KeyError'.

    """
    assert (key in attributes) == contains
    with getter_exception_expected:
        assert attributes[key] == getter_expected
    assert attributes.get(key) == getter_expected
