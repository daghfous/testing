"""
Action class
"""
import os
from typing import List

from ateme.um_backend.loggers import LOG
from .request import Request
from .base import Base, BASE_SCHEMA_PATH


class Action(Base):
    """ class Action """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "action.yaml")

    @property
    def name(self) -> str:
        """

        name getter
        :return:
        """
        return self._data['name']

    @name.setter
    def name(self, name: str):
        """

        name setter
        :param name:
        """
        self._data['name'] = name

    @property
    def request(self) -> Request:
        """

        request getter
        :return:
        """
        return self._data['request']

    @request.setter
    def request(self, request: Request):
        """

        request setter
        :param request:
        """
        self._data['request'] = request

    @property
    def prefix(self) -> str:
        """

        prefix getter
        :return:
        """
        return self._data['prefix']

    @prefix.setter
    def prefix(self, prefix: str):
        """

        prefix setter
        :param prefix:
        """
        self._data['prefix'] = prefix

    @property
    def version(self) -> str:
        """

        version getter
        :return:
        """
        return self._data.get('version', 1)

    @version.setter
    def version(self, version: str):
        """

        version setter
        :param version:
        """
        self._data['version'] = version

    @property
    def title(self) -> str:
        """

        title getter
        :return:
        """
        return self._data['title']

    @title.setter
    def title(self, title: str):
        """

        title setter
        :param title:
        """
        self._data['title'] = title

    @property
    def label(self) -> str:
        """

        label getter
        :return:
        """
        return self._data['label']

    @label.setter
    def label(self, label: str):
        """

        label setter
        :param label:
        """
        self._data['label'] = label

    @property
    def description(self) -> str:
        """

        description getter
        :return:
        """
        return self._data['description']

    @description.setter
    def description(self, description: str):
        """

        description setter
        :param description:
        """
        self._data['description'] = description

    @property
    def internal(self) -> bool:
        """

        internal getter
        :return:
        """
        return self._data.get('internal', False)

    @internal.setter
    def internal(self, internal: bool):
        """

        internal setter
        :param internal:
        """
        self._data['internal'] = internal

    @property
    def x_scope_match_children(self) -> bool:
        """
        x_scope_match_children getter

        Args: None

        Returns:
            bool: The return value of x_scope_match_children (default False)
        """
        return self._data.get('x_scope_match_children', False)

    @x_scope_match_children.setter
    def x_scope_match_children(self, x_scope_match_children: bool):
        """
        x_scope_match_children setter

        Args:
            x_scope_match_children (bool): The value to set.

        Returns: None
        """
        self._data['x_scope_match_children'] = x_scope_match_children

    @classmethod
    def from_dict(cls, data: dict):
        """

        from_dict class method
        :param data:
        :return:
        """
        self = super().from_dict(data)
        # pylint: disable=no-member
        self._data['request'] = Request.from_dict(self.request)  # pylint: disable=protected-access
        return self


def load_default_actions(data: list) -> List[Action]:
    """
    :param data:
    :return:
    """
    default_actions = []
    if data:
        try:
            default_actions = [Action.from_dict(item) for item in data]
        except Exception as error:
            LOG.error("Default actions not taken into account and not pushed in the database due to %s", error)
        for idx, action in enumerate(default_actions):
            try:
                action.validate()
            except Exception as error:
                default_actions.pop(idx)
                LOG.warning("Default action %s not taken into account and "
                            "not pushed in the database due to %s", action.name, error)
    return default_actions
