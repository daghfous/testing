"""
Base class
"""
import inspect
from abc import ABC
from collections import OrderedDict
from enum import Enum, auto
from os import path
from typing import Optional

from bson import ObjectId

from ateme.openapi import InvalidDefinition, schema_validation

BASE_SCHEMA_PATH = path.join(path.dirname(__file__)[:-6], "api", "definitions")


class RequestMethod(Enum):
    """
    RequestMethod class
    """
    POST = auto()
    GET = auto()
    PUT = auto()
    DELETE = auto()
    PATCH = auto()
    HEAD = auto()
    OPTIONS = auto()
    TRACE = auto()
    CONNECT = auto()


class MissingParameterException(Exception):
    """
    MissingParameterException exception
    """


class Base(ABC):
    """

    Base class
    """

    __slots__ = ["_data"]
    SCHEMA_PATH: Optional[str] = None
    STR2ENUM = {
        'method': RequestMethod,
    }
    KEY_OBJECTS = {}

    def __init__(self, **kwargs):
        self._data = OrderedDict()
        self._load(kwargs)

    def _load(self, data: dict):
        for key, value in data.items():
            try:
                # Inspect the class object to see if the required property is defined
                # Raise an AttributeError if the property is not in the class object
                # to avoid creating properties on the fly
                inspect.getattr_static(self, key)
                if key in self.STR2ENUM and not isinstance(value, self.STR2ENUM[key]):
                    setattr(self, key, self.STR2ENUM[key][value])
                elif key in self.KEY_OBJECTS and isinstance(value, (dict, list, str)):
                    setattr(self, key, self.KEY_OBJECTS[key](value))
                else:
                    setattr(self, key, value)
            except AttributeError:
                # don't flood with user_management _load [Unknown parameter: _id]
                pass

    @classmethod
    def from_dict(cls, data: dict):
        """

        from_dict class method
        :param data:
        :return:
        """
        self = cls()

        self._load(data)  # pylint: disable=protected-access

        return self

    def validate(self) -> bool:
        """

        validate data
        :return:
        """
        try:
            schema_validation(self.to_dict(), self.SCHEMA_PATH, self.SCHEMA_PATH)
        except InvalidDefinition as err:
            raise MissingParameterException(err) from err
        return True

    def to_dict(self) -> dict:
        """

        to_dict function
        :return:
        """
        data = self._data.copy()
        for key, value in data.items():
            if isinstance(value, list) and value:
                new_values = [
                    item.to_dict()
                    if hasattr(value[0], "to_dict") and callable(value[0].to_dict)
                    else item
                    for item in value
                ]
                data[key] = new_values
            # Not used but keep in case the need appears
            # elif isinstance(value, dict) and value:
            #     if hasattr(list(value.values())[0], "to_dict"):
            #         data[key] = {k: v.to_dict() for k, v in value.items()}
            #     elif isinstance(list(value.values())[0], list) and \
            #             list(value.values())[0] and \
            #             hasattr(list(value.values())[0][0], "to_dict"):
            #         data[key] = {
            #             k: [item.to_dict() for item in v] for k, v in value.items()
            #         }
            elif hasattr(value, "to_dict") and callable(value.to_dict):
                data[key] = value.to_dict()
            elif key in self.STR2ENUM:
                data[key] = value.name
            elif isinstance(value, ObjectId) and value:
                data[key] = str(value)
        return data

    def __str__(self) -> str:
        return str(self.to_dict())
