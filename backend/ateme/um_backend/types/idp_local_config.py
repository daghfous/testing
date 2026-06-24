"""

LdapConfig class
"""
from .idp_config import (
    IdpConfig,
    IdpType
)

DEFAULT_LOCAL_IDP_NAME = "local"
DEFAULT_LOCAL_IDP_LABEL = "Local"


class IdpLocalConfig(IdpConfig):
    """ class IdpLocalConfig """

    def __init__(self):
        super().__init__()
        self.idp_name = DEFAULT_LOCAL_IDP_NAME
        self.idp_type = IdpType.local.name
        self.idp_label = DEFAULT_LOCAL_IDP_LABEL
