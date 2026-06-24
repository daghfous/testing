"""
AuthDataDescriptor class
"""
from dataclasses import dataclass


@dataclass
class AuthDataDescriptor:
    """
    AuthData class
    """
    prefix: str
    url: str
    app_name: str
