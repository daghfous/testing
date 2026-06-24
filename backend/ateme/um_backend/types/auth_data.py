"""
AuthData class
"""
from typing import List
from dataclasses import dataclass, field
from .action import Action
from .scope import Scope
from .auth_data_descriptor import AuthDataDescriptor


@dataclass
class AuthData:
    """
    AuthData class
    """
    auth_data_descriptors: List[AuthDataDescriptor] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    scopes: List[Scope] = field(default_factory=list)
