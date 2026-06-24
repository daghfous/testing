"""

Request class
"""
import os

from .base import Base, BASE_SCHEMA_PATH, RequestMethod


class Request(Base):
    """ class Request """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "request.yaml")

    @property
    def method(self) -> RequestMethod:
        """

        method getter
        :return:
        """
        return self._data["method"]

    @method.setter
    def method(self, method: RequestMethod):
        """

        method setter
        :param method:
        """
        self._data["method"] = method

    @property
    def route(self) -> str:
        """

        route getter
        :return:
        """
        return self._data["route"]

    @route.setter
    def route(self, route: str):
        """

        route setter
        :param route:
        """
        self._data["route"] = route
