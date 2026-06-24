"""
User class
"""
import hashlib
import os
from base64 import b64encode
from typing import List, Callable

from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import bcrypt
from Crypto.Util.Padding import pad
from bson import ObjectId

from ateme.um_backend.loggers import LOG
from .base import Base, BASE_SCHEMA_PATH
from .idp_local_config import DEFAULT_LOCAL_IDP_NAME


class UserBadPasswordException(Exception):
    """ Exception raised when user has an invalid password """


class User(Base):
    """ class User """
    SCHEMA_PATH = os.path.join(BASE_SCHEMA_PATH, "user.yaml")

    @property
    def creation_id(self) -> ObjectId:
        """

        _id getter
        :return:
        """
        # Manage import from previous version where _id field was used to salt user password
        if "creation_id" not in self._data and "_id" in self._data:
            return self._data["_id"]
        return self._data["creation_id"]

    @creation_id.setter
    def creation_id(self, creation_id: ObjectId):
        """

        creation_id setter
        :param creation_id:
        """
        self._data["creation_id"] = creation_id

    @property
    def username(self) -> str:
        """

        username getter
        :return:
        """
        return self._data["username"]

    @username.setter
    def username(self, username: str):
        """

        username setter
        :param username:
        """
        self._data["username"] = username

    @property
    def password(self) -> str:
        """

        password getter
        :return:
        """
        return self._data["password"]

    @password.setter
    def password(self, password: str):
        """

        password setter
        :param password:
        """
        self._data["password"] = password

    @property
    def enabled(self) -> bool:
        """
        enabled getter
        :return:
        """
        return self._data.get("enabled", True)

    @enabled.setter
    def enabled(self, enabled: bool):
        """
        enabled setter
        :param enabled:
        """
        self._data["enabled"] = enabled

    @property
    def scopes(self) -> list:
        """

        scopes getter
        :return:
        """
        return self._data["scopes"]

    @scopes.setter
    def scopes(self, scopes: list):
        """

        scopes setter
        :param scopes:
        """
        self._data["scopes"] = scopes

    @property
    def idp_name(self) -> str:
        """

        idp_name getter
        :return:
        """
        return self._data.get("idp_name", DEFAULT_LOCAL_IDP_NAME)

    @idp_name.setter
    def idp_name(self, idp_name: str):
        """

        idp_name setter
        :param idp_name:
        """
        self._data["idp_name"] = idp_name

    @property
    def level(self) -> str:
        """

        level getter
        :return:
        """
        return self._data.get("level")

    @level.setter
    def level(self, level: str):
        """

        level setter
        :param level:
        """
        self._data["level"] = level

    @property
    def first_login(self) -> bool:
        """

        first_login getter
        :return:
        """
        if self.idp_name != DEFAULT_LOCAL_IDP_NAME:
            # first_login set to False for ldap users
            self.first_login = False
        return self._data.get("first_login", False)

    @first_login.setter
    def first_login(self, first_login: bool):
        """

        first_login setter
        :param first_login:
        """
        self._data["first_login"] = first_login

    @property
    def password_last_update(self) -> int:
        """
        password_last_update getter
        :return:
        """
        return self._data.get("password_last_update", False)

    @password_last_update.setter
    def password_last_update(self, password_last_update: int):
        """
        password_last_update setter
        :param password_last_update:
        """
        self._data["password_last_update"] = password_last_update

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
    def default(self) -> bool:
        """ default getter """
        return self._data.get('default', False)

    @default.setter
    def default(self, default: bool):
        """ default setter """
        self._data['default'] = default

    @staticmethod
    def generate_hash(str_list: list):
        """

        :param str_list:
        :return:
        """
        return hashlib.sha1('_'.join(str_list).encode('utf-8')).hexdigest()

    @property
    def user_id(self):
        """

        :return:
        """
        return self.generate_hash([self.username, str(self.password), self.idp_name])

    @property
    def session_timeout_disabled(self) -> bool:
        """
        session_timeout_disabled getter
        :return:
        """
        return self._data.get("session_timeout_disabled", False)

    @session_timeout_disabled.setter
    def session_timeout_disabled(self, session_timeout_disabled: bool):
        """
        session_timeout_disabled setter
        :param session_timeout_disabled:
        """
        self._data["session_timeout_disabled"] = session_timeout_disabled


    @property
    def password_expiration_disabled(self) -> bool:
        """
        password_expiration_disabled getter
        :return:
        """
        return self._data.get("password_expiration_disabled", False)

    @password_expiration_disabled.setter
    def password_expiration_disabled(self, password_expiration_disabled: bool):
        """
        password_expiration_disabled setter
        :param password_expiration_disabled:
        """
        self._data["password_expiration_disabled"] = password_expiration_disabled

    @property
    def password_expired(self) -> bool:
        """

        password_expired getter
        :return:
        """
        return self._data.get("password_expired", False)

    @password_expired.setter
    def password_expired(self, password_expired: bool):
        """

        password_expired setter
        :param password_expired:
        """
        self._data["password_expired"] = password_expired

    def to_dict(self, with_creation_id: bool = False):  # pylint: disable=arguments-differ
        """

        :param:
        :return:
        """
        data = {"creation_id": self.creation_id,
                "user_id": self.user_id,
                "username": self.username,
                "password": self.password,
                "enabled": self.enabled,
                "password_last_update": self.password_last_update,
                "level": self.level,
                "scopes": list(self.scopes),
                "idp_name": self.idp_name,
                "first_login": self.first_login,
                "internal": self.internal,
                "default": self.default,
                "session_timeout_disabled": self.session_timeout_disabled,
                "password_expiration_disabled": self.password_expiration_disabled,
                "password_expired": self.password_expired}

        if not with_creation_id:
            del data['creation_id']
        if not data['level']:
            del data['level']
        return data

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return (self.username == other.username and self.idp_name == other.idp_name and self.scopes == other.scopes
                and self.first_login == other.first_login)

    @staticmethod
    def generate_salted_encrypted_password(password: str, creation_id: bytes, encrypt) -> str:
        """ Generate an encrypted salted password """
        salted = pad(creation_id, 16)  # Add bytes to creation_id to have a length of 16
        return encrypt(str(bcrypt(b64encode(SHA256.new(password.encode('utf-8')).digest()),
                                  12,
                                  salt=salted))).decode('utf-8')

def load_default_users(data: List[dict], encryption_method: Callable) -> List[User]:
    """
    Load and validate default users from the given list
    Args:
        data: list of users
        encryption_method: encryption method to use for password

    Returns:
        List[User]: The list of validated users
    """
    if not data:
        return []

    default_users = []
    for tmp_user in data:
        try:
            user = _load_default_user(input_user=tmp_user, encryption_method=encryption_method)
            if user:
                default_users.append(user)
        except Exception as error:
            LOG.warning("Default user '%s' not taken into account and not pushed in the database due to: %s",
                        tmp_user.get('username'), error)
    return default_users


def load_default_admin(input_admin: dict, encryption_method: Callable) -> User | None:
    """
    Load and validate a default admin
    Args:
        input_admin: an admin
        encryption_method: encryption method to use for password

    Returns:
        User: A validated admin user
    """
    default_admin = None
    try:
        input_admin["scopes"] = ["all:administrator"]
        default_admin = _load_default_user(input_user=input_admin, encryption_method=encryption_method,
                                           is_default=False)
    except Exception as error:
        LOG.warning("Default admin '%s' not taken into account and not pushed in the database due to: %s",
                    input_admin.get('username'), error)
    return default_admin


def _load_default_user(input_user: dict, encryption_method: Callable,
                       is_default = True) -> User:
    """
    Load and validate default user from the given user/admin
    Args:
        input_user: user
        encryption_method: encryption method to use for password
        is_default: if default user
    Returns:
        User: The validated user/admin
    """
    password = input_user.pop('password')
    creation_id = ObjectId()
    input_user['creation_id'] = creation_id
    salted_password = User.generate_salted_encrypted_password(password=password,
                                                              creation_id=creation_id.binary,
                                                              encrypt=encryption_method)
    input_user['password'] = salted_password
    input_user['default'] = is_default
    default_user = User.from_dict(input_user)
    default_user.validate()
    return default_user
