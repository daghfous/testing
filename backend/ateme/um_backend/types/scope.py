"""
Scope class
"""
from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto
import os
from typing import List

from ateme.um_backend.loggers import LOG
from .base import Base, BASE_SCHEMA_PATH


# Default pagination limit for scopes
DEFAULT_SCOPES_PAGE_LIMIT = 100

# Empty scope id pattern
SCOPE_ID_EMPTY_PATTERN = "^"


class DefaultScopes(Enum):
    """
    DefaultScopes
    """
    # pylint: disable=invalid-name
    administrator = auto()
    engineer = auto()
    operator = auto()
    monitoring = auto()
    guest = auto()


class ScopeFilterMode(StrEnum):
    """
    Scope Filter Mode class used for 'get_scopes' function
    Two modes for retrieving the scopes
    """
    EXPERT = auto()
    BASIC = auto()


class ScopeIdSortOrder(StrEnum):
    """
    Scope Id Sort Order class used for 'get_scopes' function
    Two modes for sorting the scopes
    """
    ASCENDING = "id"
    DESCENDING = "-id"

    @property
    def mongo_sort(self) -> tuple[str, int]:
        """Return tuple usable directly in pymongo sort."""
        if self == ScopeIdSortOrder.ASCENDING:
            return "id", 1
        return "id", -1


@dataclass(kw_only=True)
class ScopeFilter:  # pylint: disable=too-many-instance-attributes
    """ ScopeFilter is a data container and filter builder for querying scope objects in a MongoDB database.

    Attributes:
        mode (ScopeFilterMode): The filtering mode, defaults to ScopeFilterMode.EXPERT.
        internal (bool | None): If True, filters on internal scopes; if False, excludes them; None to ignore the field.
        pmf_release_name (str): Release name used for filtering in BASIC mode.
        scope_ids (list[str]): List of scope IDs to filter for.
        prefix (str | None): Optional prefix for scope ID pattern matching.
        app_name (str | None): Optional application name for scope ID pattern matching.
        scope_type (str | None): Optional scope type for scope ID pattern matching.
        label (str | None): Optional label for regex-based filtering.
        default (bool | None): If True, filters on default scopes; if False, excludes them; None to ignore the field.
        additional_filters (dict | None): Optional dictionary of additional custom filters.
    """
    mode: ScopeFilterMode = ScopeFilterMode.EXPERT
    internal: bool | None = False
    pmf_release_name: str = ""
    scope_ids: list[str] = field(default_factory=list)
    prefix: str | None = None
    app_name: str | None = None
    scope_type: str | None = None
    label: str | None = None
    default: bool | None = None
    additional_filters: dict | None = None

    def to_mongo_filter(self) -> dict:
        """
        Generates a MongoDB filter dictionary based on the current state of the ScopeFilter instance.

        Returns:
            dict: A MongoDB filter dictionary combining all applicable criteria.
        """
        # pylint: disable=too-many-branches
        filters = []

        if self.internal is not None:
            if self.internal:
                filters.append({"internal": True})
            else:
                # `internal` is not required field in scope, check internal is False
                # or internal field does not exist.
                filters.append({
                    "$or": [
                        {"internal": False},
                        {"internal": {"$exists": False}}
                    ]
                })

        if self.mode == ScopeFilterMode.BASIC:
            if self.pmf_release_name:
                # Match either:
                # [2 levels] "app_name:scope_type" where app_name != pmf_release_name
                # [3 levels] "pmf_release_name:prefix:scope_type" where app_name == pmf_release_name
                id_basic_regex = f"^((?!{self.pmf_release_name}:)[^:]+:[^:]+$|{self.pmf_release_name}:[^:]+:[^:]+$)"
            else:
                # Handle case without pmf_release_name (TE mode).
                # Return only "all:scope_type" and "usr:scope_type" levels.
                id_basic_regex = r"^(all|usr):[^:]+$"
            filters.append({"id": {"$regex": id_basic_regex}})

        if self.scope_ids:
            filters.append({"id": {"$in": self.scope_ids}})

        id_pattern = SCOPE_ID_EMPTY_PATTERN
        if self.prefix:
            id_pattern = f"^{self.app_name}:{self.prefix}:" if self.app_name else f"^{self.prefix}:"
        elif self.app_name:
            id_pattern = f"^{self.app_name}:"
        if self.scope_type:
            if self.app_name and self.prefix:
                id_pattern += f"{self.scope_type}$"
            else:
                id_pattern += f"(.*:)?{self.scope_type}$"
        if id_pattern != SCOPE_ID_EMPTY_PATTERN:
            filters.append({"id": {"$regex": id_pattern}})

        if self.label:
            filters.append({"label": {"$regex": self.label}})

        if self.default is not None:
            if self.default:
                filters.append({"default": True})
            else:
                # `default` is not required field in scope, check default is False
                # or default field does not exist.
                filters.append({
                    "$or": [
                        {"default": False},
                        {"default": {"$exists": False}}
                    ]
                })

        # Combine filters via $and if multiple
        if len(filters) == 0:
            scope_filter = {}
        elif len(filters) == 1:
            scope_filter = filters[0]
        else:
            scope_filter = {"$and": filters}
        return scope_filter


class AllScopesDescriptions(Enum):
    """
    Enum for all scopes descriptions
    """
    # pylint: disable=invalid-name
    administrator = "Role granting full access to all features and functionalities of the applications."
    engineer = "Role allowing configuration management across all features of the applications."
    operator = "Role permitting control and operational actions across all features of the applications."
    monitoring = "Role providing view-only access across all features of the applications."
    guest = "Role with minimal access, restricted to basic usage and limited features."


class Scope(Base):
    """ class Scope """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "scope.yaml")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fill_title()

    @classmethod
    def from_dict(cls, data: dict):
        # pylint: disable=no-member
        """
        from_dict class method
        :param data:
        :return:
        """
        self = super().from_dict(data)
        self.fill_title()
        return self

    @property
    def id(self) -> str:
        """

        id getter
        :return:
        """
        return self._data.get('id')

    @id.setter
    def id(self, id: str):  # pylint: disable=redefined-builtin
        """

        id setter
        :param id:
        """
        self._data['id'] = id

    @property
    def version(self) -> int:
        """

        version getter
        :return:
        """
        return self._data.get('version', 1)

    @version.setter
    def version(self, version: int):
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
        return self._data.get('title')

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
        return self._data.get('label')

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
        return self._data.get('description')

    @description.setter
    def description(self, description: str):
        """

        description setter
        :param description:
        """
        self._data['description'] = description

    @property
    def default(self) -> bool:
        """

        default getter
        :return:
        """
        return self._data.get('default', False)

    @default.setter
    def default(self, default: bool):
        """

        default setter
        :param default:
        """
        self._data['default'] = default

    @property
    def content(self) -> list:
        """

        content getter
        :return:
        """
        return self._data['content']

    @content.setter
    def content(self, content: list):
        """

        content setter
        :param content:
        """
        self._data['content'] = content

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

    def fill_title(self):
        """[Fill scope title]
        """
        # label and id are required for a creation, but not necessarily provided for an updating
        scope_name = None
        if not self.title and self.label and self.id:
            # title auto-generation
            scope_name = self.id.split(':')[1]
            # pylint: disable=assigning-non-slot
            self.title = f"{self.label} {scope_name}"

@dataclass
class ScopesPaginatedResponse:
    """
    Paginated Scopes Response class
    used to return data from 'get_scopes' function in database
    """
    scopes: list[Scope]
    start: int
    total: int

def load_default_scopes(data: List[dict]) -> List[Scope]:
    """

    :param data:
    :return:
    """
    # Commented => Encryption disabled
    # decrypted_data = json.loads(AESCipher(hash_key=True).decrypt(data).replace("'", '"'))
    default_scopes = []
    if data:
        default_scopes = [Scope.from_dict(item) for item in data]
        for idx, scope in enumerate(default_scopes):
            try:
                scope.validate()
            except Exception as error:
                default_scopes.pop(idx)
                LOG.warning("Default scope %s not taken into account and "
                            "not pushed in the database due to %s", scope.id, error)
    return default_scopes
