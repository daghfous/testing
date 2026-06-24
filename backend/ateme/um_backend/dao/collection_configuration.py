"""
collection configuration
"""
from dataclasses import dataclass
from .collections import Collections, CollectionBase


@dataclass(kw_only=True)
class CollectionConfiguration(CollectionBase):
    """ CollectionConfiguration inherits from CollectionBase.
    It manages the collection `configuration`.
    """
    name: str = Collections.configuration.name
