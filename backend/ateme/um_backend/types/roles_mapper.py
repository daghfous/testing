"""
RolesMapper class
"""

from abc import ABC
from enum import Enum, auto
from typing import List

from bson import ObjectId

from .base import Base


class RolesMapperType(Enum):
    """

    RolesMapperType enum, can be direct or simple
    """
    # pylint: disable=invalid-name
    direct = auto()
    simple = auto()


class RolesMapper(Base, ABC):
    """

    RolesMapper abstract class, define shared property of DirectRolesMapper
    and SimpleRolesMapper.
    """

    @property
    def _id(self) -> ObjectId:
        """

        _id getter

        Returns:
            ObjectId: bson.OjectId used has id.

        """
        return self._data['_id']

    @_id.setter
    def _id(self, _id: ObjectId):
        """

        _id setter

        Args:
            _id (ObjectId): bson.OjectId used has id.

        """
        self._data['_id'] = _id

    @property
    def type(self) -> RolesMapperType:
        """

        type getter

        Returns:
            RolesMapperType: Roles mapper type

        """
        return self._data['type']

    @type.setter
    def type(self, _type: RolesMapperType):
        """

        type setter

        Args:
            _type (RolesMapperType): Roles mapper type

        """
        self._data['type'] = _type


class SimpleRolesMapperAttribute(Base):
    """
    SimpleRolesMapperAttribute class type
    """

    @property
    def name(self) -> str:
        """
        name getter

        Returns:
            str: name
        """
        return self._data['name']

    @name.setter
    def name(self, name: str):
        """
        name setter

        Args:
            name (str): name to set
        """
        self._data['name'] = name

    @property
    def value(self) -> str:
        """
        value getter

        Returns:
            str: value
        """
        return self._data['value']

    @value.setter
    def value(self, value: str):
        """
        value setter

        Args:
            value (str): value to set
        """
        self._data['value'] = value


class SimpleRolesMapper(RolesMapper):
    """
    SimpleRolesMapper class type
    """

    @property
    def attributes(self) -> List[SimpleRolesMapperAttribute]:
        """
        attributes getter

        Returns:
            List[SimpleRolesMapperAttribute]: attributes
        """
        return self._data.get('attributes', [])

    @attributes.setter
    def attributes(self, attributes: List[dict]):
        """
        attributes setter, will cast to SimpleRolesMapperAttribute class.

        Args:
            attributes (List[dict]): attributes to set
        """
        self._data["attributes"] = [SimpleRolesMapperAttribute.from_dict(item) for item in attributes]

    @property
    def scopes_to_add(self) -> List[str]:
        """
        scopes_to_add getter

        Returns:
            List[str]: List of ref scopes
        """
        return self._data['scopes_to_add']

    @scopes_to_add.setter
    def scopes_to_add(self, scopes_to_add: List[str]):
        """
        scopes_to_add setter

        Args:
            scopes_to_add (List[str]): scopes to add
        """
        self._data['scopes_to_add'] = scopes_to_add


class DirectRolesMapper(RolesMapper):
    """
    DirectRolesMapper class type
    """

    @property
    def attribute_name(self) -> str:
        """
        attribute_name getter

        Returns:
            str: attribute name

        """
        return self._data['attribute_name']

    @attribute_name.setter
    def attribute_name(self, attribute_name: str):
        """
        attribute_name setter

        Args:
            attribute_name (str): attritube name setter

        """
        self._data['attribute_name'] = attribute_name
