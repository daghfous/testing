"""

Roles mapper module, expose an Attributes class and a utils fonction 'retrieve_scopes_from_roles_mapper'.
"""
import re
from typing import Any, List
from collections import UserDict


from ateme.um_backend.types import (
    RolesMapper,
    DirectRolesMapper,
    SimpleRolesMapper
)


class Attributes(UserDict):
    # pylint: disable=anomalous-backslash-in-string,too-many-ancestors
    """
    Attributes class override 'UserDict' in order to handle nested key
    with standard of dict. Can use "in" and getter function.

    We implement a very simple "JsonPath" we split with dot "." and escape with "\.", that it.
    """

    # This regex use negative lookbehind, that is the way to match on dot
    # if before we don't match the escape character "\".
    SPLIT_PATH_PATTERN = r"(?<!\\)\."

    @staticmethod
    def split_path(path: str) -> List[str]:
        """
        Split path by dot and escpe with backslash dot.

        Args:
            path (str): path as a string.

        Returns:
            List[str]: List of sub path
        """
        return [item.replace("\\", "") for item in re.split(Attributes.SPLIT_PATH_PATTERN, path)]

    def __getitem__(self, key: str) -> Any:
        """
        Attributes getter override from 'UserDict' to handle nested attributes.

        Args:
            key (str): key to find

        Raises:
          KeyError: raise a KeyError if we don't find property or nested property

        Returns:
            Any: value of the nested property in the current dict
        """
        _path = Attributes.split_path(key)
        if len(_path) == 1:
            return super().__getitem__(_path[0])
        _data = self
        for _key in _path:
            if _key not in _data:
                raise KeyError(f"Can't find path {'.'.join(_path)} in attribute")
            _data = _data[_key]
        return _data

    def __contains__(self, key) -> bool:
        """
        Override __contains__ function

        Args:
            key: check if the nested or simple path exists in the current dict, no typing because 'UserDict' doesn't
                 define type for key.

        Returns:
            bool: True if we find the key in dict
        """
        _sub_path = Attributes.split_path(key)
        if len(_sub_path) == 1:
            return super().__contains__(_sub_path[0])
        _item = self
        for path in _sub_path:
            if not isinstance(_item, (dict, UserDict)):
                return False
            try:
                _item = _item[path]
            except KeyError:
                return False
        return True


def retrieve_scopes_from_roles_mapper(
    mappers: List[RolesMapper],
    attributes: Attributes
) -> List[str]:
    """

    Retrieve scopes to add from a list of 'RolesMappers', 'RolesMapper' can be a
    'DirectRolesMapper' or a 'SimpleRolesMapper'.  In case of 'DirectRolesMapper' we
    retrieve directly the list of scopes ref in the attributes. Else in case of
    'SimpleRolesMapper' we check that attribute value match mapper value defined.

    Args:
        mappers (List[RolesMapper]): List of mappers to evaluate
        attributes (Attributes): Attribute loaded

    Returns:
        List[str]: List of scopes reference.
    """
    # Define scopes as a set, we don't want duplicate scope ref
    scopes = set()
    # Iterate on mappers of saml config
    for mapper in mappers:
        if isinstance(mapper, DirectRolesMapper):
            if mapper.attribute_name in attributes:
                if isinstance(attributes[mapper.attribute_name], list):
                    scopes |= set(attributes[mapper.attribute_name])
                elif isinstance(attributes[mapper.attribute_name], str):
                    scopes.add(attributes[mapper.attribute_name])
        elif isinstance(mapper, SimpleRolesMapper):
            matching = True
            for attribute in mapper.attributes:
                if attribute.name not in attributes:
                    matching = False
                    break
                _attribute_value = attributes[attribute.name]
                if (isinstance(_attribute_value, list) and attribute.value not in _attribute_value) or (
                    # Strict equal in case of type of string but SAML attribute value is always list, is this useful?
                    isinstance(_attribute_value, str) and _attribute_value != attribute.value
                ):
                    matching = False
                    break
            if matching:
                scopes |= set(mapper.scopes_to_add)

    return list(scopes)
