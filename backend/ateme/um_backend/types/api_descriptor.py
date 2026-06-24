"""
ApiDescriptor class
"""
from os import path
from typing import List, Optional

from .action import Action
from .scope import Scope
from .base import Base, BASE_SCHEMA_PATH


class ApiDescriptor(Base):
    """
    Configuration class
    """

    SCHEMA_PATH = path.join(BASE_SCHEMA_PATH, "api_descriptor.yaml")

    # pylint: disable=too-many-arguments,dangerous-default-value,too-many-positional-arguments
    def __init__(self, prefix: Optional[str] = None, url: Optional[str] = None, actions: List[Action] = [],
                 scopes: List[Scope] = [], app_name: Optional[str]= None):
        """
        Initialize

        :param prefix:
        :param url:
        :param actions:
        :param scopes:
        :param app_name:
        """
        super().__init__(prefix=prefix,
                         url=url,
                         actions=actions,
                         scopes=scopes,
                         app_name=app_name)

    @classmethod
    def from_dict(cls, data: dict):
        """

        from_dict class method
        :param data:
        :return:
        """
        self = cls()

        self._load(data)  # pylint: disable=protected-access

        for idx, action in enumerate(self.actions):
            if not isinstance(action, Action):
                self.actions[idx] = Action.from_dict(action)

        for idx, scope in enumerate(self.scopes):
            if not isinstance(scope, Scope):
                self.scopes[idx] = Scope.from_dict(scope)

        return self

    @property
    def prefix(self) -> str:
        """
        Return prefix
        :return
        """
        return self._data["prefix"]

    @prefix.setter
    def prefix(self, prefix):
        """
        prefix setter
        """
        self._data["prefix"] = prefix

    @property
    def url(self) -> str:
        """
        Return url
        :return
        """
        return self._data["url"]

    @url.setter
    def url(self, url):
        """
        url setter
        """
        self._data["url"] = url

    @property
    def actions(self) -> List[Action]:
        """
        Return list of actions
        :return
        """
        return self._data["actions"]

    @actions.setter
    def actions(self, actions):
        """
        actions setter
        """
        self._data["actions"] = actions

    @property
    def scopes(self) -> List[Scope]:
        """
        Return list of scopes
        :return
        """
        return self._data["scopes"]

    @scopes.setter
    def scopes(self, scopes):
        """
        scopes setter
        """
        self._data["scopes"] = scopes

    @property
    def app_name(self) -> str:
        """
        Return app_name
        :return
        """
        return self._data["app_name"]

    @app_name.setter
    def app_name(self, app_name: str):
        """
        app_name setter
        """
        self._data["app_name"] = app_name
