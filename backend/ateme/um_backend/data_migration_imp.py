"""
Updater
"""
import math

from ateme.updater.data_migration import DataMigration
from ateme.updater.updater import (
    find_collection,
    ExportDowngradeException,
    ImportUpgradeException
)
from ateme.um_backend.types import (
    IdpType,
    User,
    DEFAULT_LOCAL_IDP_NAME,
    PasswordPolicy
)

from .loggers import LOG


class DataMigrationImp(DataMigration):  # pylint: disable=too-few-public-methods
    """
    DataMigrationImpl
    This class relates to the Upgrade/downgrade feature in the context of Backup/Restore functionality.
    It allows to provide implementations of upgrade/downgrade methods required for the data migration during the
    Backup/Restore. These methods will be called by the Updater Library.
    Their names should have the following format:
    - downgrade_from_<origin_version>_to_<target_version>
    - upgrade_from_<origin_version>_to_<target_version>.
    with versions expressed with 2 digits separated by '_'.

    Examples

    >>>    def downgrade_from_6_0_to_5_0(self, data):
    >>>       # Downgrade data from version 6.0 to 5.0
    >>>       <Do stuff>

    >>>    def upgrade_from_5_0_to_6_0(self, data):
    >>>       # Upgrade data from version 5.0 to 6.0
    >>>       <Do stuff>

    """

    @staticmethod
    def compute_idp_name_from_domain(domain: str) -> str:
        """
        compute_idp_name_from_domain
        :param domain:
        """
        return f"{IdpType.ldap.name}_{domain}"

    @staticmethod
    def compute_password_policy(password_expiration: int) -> dict:
        """
        compute password_policy from the password_expiration (expressed in month)
        :param password_expiration:
        """
        password_policy = {"regex_pattern": PasswordPolicy.get_password_regex_pattern()}
        if password_expiration != -1:
            password_policy["expiration_delay_in_days"] = password_expiration * 30
        else:
            password_policy["expiration_delay_in_days"] = -1
        return password_policy

    @staticmethod
    def compute_password_expiration(password_policy: dict) -> int:
        """
        compute password_expiration from the password_policy
        We ceil the password_expiration to the nearest month
        :param password_policy:

        """
        if (password_policy and "expiration_delay_in_days" in password_policy
                and password_policy["expiration_delay_in_days"] > 0):
            password_expiration = math.ceil(password_policy["expiration_delay_in_days"] / 30)
        else:
            password_expiration = -1
        return password_expiration

    def downgrade_from_9_0_to_5_0(self, data: list):  # pylint: disable=too-many-branches,too-many-statements
        """
        Downgrade data from version 9.0 to 5.0
        For configuration
        - Remove password_policy
        - Add password_expiration based on password_policy["expiration_delay_in_days"]
            password_expiration (in month) = expiration_delay_in_days * 30

        Args:
            data (list): list of collection to transform from version 9.x to 5.x.
        """
        try:
            configuration_idx = find_collection(data, "configuration")
            if configuration_idx >= 0:
                for doc in data[configuration_idx]["data"]:
                    doc["password_expiration"] = self.compute_password_expiration(doc["password_policy"])
                    del doc["password_policy"]
        except Exception as exception:
            LOG.error("ExportDowngradeException exception: %s", exception)
            raise ExportDowngradeException("Fail to downgrade from higher version") from exception

    def upgrade_from_5_0_to_9_0(self, data: list):
        """
        Upgrade data from version 5.0 to 9.0
        For configuration
        - Remove password_expiration
        - Add password_policy with password_policy["expiration_delay_in_days"] computed from password_expiration

        Args:
            data (list): list of collection to transform from version 5.x to 9.x.
        """
        try:
            configuration_idx = find_collection(data, "configuration")
            if configuration_idx >= 0:
                for doc in data[configuration_idx]["data"]:
                    doc["password_policy"] = self.compute_password_policy(doc["password_expiration"])
                    del doc["password_expiration"]
        except Exception as exception:
            LOG.error("ImportUpgradeException exception: %s", exception)
            raise ImportUpgradeException("Fail to upgrade from previous version") from exception

    def downgrade_from_5_0_to_4_0(self, data: list):  # pylint: disable=too-many-branches,too-many-statements
        """
        Downgrade data from version 5.0 to 4.0
        For idp_config/ldap_config
        - idp_config replace ldap_config in 5.0 with two additional fields: idp_type, idp_name
        For users/admin collection
        - Remove idp_name
        - Replace idp_type by authenticate_mode
        - Add domain for ldap based on idp_name only for users collection.
        - Regenerate user_id

        Args:
            data (list): list of collection
        """
        # pylint: disable=too-many-nested-blocks
        try:
            admin_idx = find_collection(data, "admin")
            if admin_idx >= 0:
                for doc in data[admin_idx]["data"]:
                    doc["user_id"] = User.generate_hash([doc["username"], str(doc["password"])])
                    doc["authenticate_mode"] = "local"
                    del doc["idp_name"]

            users_idx = find_collection(data, "users")
            idp_config_idx = find_collection(data, "idp_config")
            users_to_delete = []
            usernames = []
            if users_idx >= 0:
                for i, doc in enumerate(data[users_idx]["data"]):
                    # Get the user idp type
                    idp_type = ''
                    idp_domain = ''
                    if idp_config_idx >= 0:
                        for idp_doc in data[idp_config_idx]["data"]:
                            if idp_doc["idp_name"] == doc["idp_name"]:
                                idp_type = idp_doc["idp_type"]
                                # No domain for local config
                                idp_domain = idp_doc.get("domain")
                                break
                    if not idp_type:
                        LOG.warning("No idp config for this user %s", doc['username'])
                        users_to_delete.append(i)
                        continue
                    if idp_type == IdpType.ldap.name:
                        # Get domain from the idp_name
                        doc["domain_ldap"] = idp_domain
                        doc["authenticate_mode"] = "ldap"
                    elif idp_type == IdpType.local.name:
                        doc["authenticate_mode"] = "local"
                    else:
                        LOG.warning("Saml login is not managed in version 4")
                    usernames.append(doc['username'])
                    del doc["idp_name"]
                    #  Regenerate user_id only based on the username and password
                    # for this version (idp_name used in 5.0)
                    doc["user_id"] = User.generate_hash([doc["username"], str(doc["password"])])
            # delete users without idp config
            for i in reversed(users_to_delete):
                LOG.warning("Delete user %s", data[users_idx]["data"][i]['username'])
                del data[users_idx]["data"][i]
            # username is uniq in version 4
            users_to_delete = []
            if len(usernames) > len(set(usernames)):
                for i, doc in enumerate(data[users_idx]["data"]):
                    # local users have priority
                    if usernames.count(doc['username']) > 1 and doc['authenticate_mode'] != 'local':
                        users_to_delete.append(i)
            for i in reversed(users_to_delete):
                LOG.warning("Delete user %s", data[users_idx]["data"][i]['username'])
                del data[users_idx]["data"][i]

            # Update import policy
            data[users_idx]["import_policy"]["key_index"] = [{"user_id": "ASCENDING"},
                                                             {"username": "ASCENDING"}]
            # idp_config to ldap_config
            i_local_idp = None
            if idp_config_idx >= 0:
                for i, doc in enumerate(data[idp_config_idx]["data"]):
                    if doc["idp_name"] == DEFAULT_LOCAL_IDP_NAME:
                        i_local_idp = i
                    # remove no more present fields
                    del doc["idp_name"]
                    del doc["idp_type"]
                    doc.pop("idp_label", None)
            # delete local idp config
            if i_local_idp is not None:
                del data[idp_config_idx]["data"][i_local_idp]
            # update collection name and import policy
            data[idp_config_idx]["collection"] = "ldap_config"
            data[idp_config_idx]["import_policy"]["key_index"] = [{"domain": "ASCENDING"}]
        except Exception as exception:
            LOG.error("ExportDowngradeException exception: %s", exception)
            raise ExportDowngradeException("Fail to downgrade from higher version") from exception

    def upgrade_from_4_0_to_5_0(self, data: list):
        """
        Upgrade data from version 4.0 to 5.0
        For idp_config/ldap_config
        - idp_config replace ldap_config in 5.0 with two additional fields: idp_type, idp_name
        For User/admin collection
        - Add idp_name from domain
        - Replace authenticate_mode by idp_type
        - Remove domain only for users collection, no need for admin it's only local users.
        - Regenerate user_id

        Args:
            data (list): list of collection to transform from version 4.x to 5.x.
        """
        try:
            admin_idx = find_collection(data, "admin")
            if admin_idx >= 0:
                for doc in data[admin_idx]["data"]:
                    doc["idp_name"] = DEFAULT_LOCAL_IDP_NAME
                    doc["user_id"] = User.generate_hash([doc["username"], str(doc["password"]), doc["idp_name"]])
                    del doc["authenticate_mode"]

            users_idx = find_collection(data, "users")
            if users_idx >= 0:
                for doc in data[users_idx]["data"]:
                    if doc["authenticate_mode"] == IdpType.ldap.name:
                        # Compute idp_name and idp_label from domain_ldap
                        doc["idp_name"] = self.compute_idp_name_from_domain(doc["domain_ldap"])
                        del doc["domain_ldap"]
                    else:
                        doc["idp_name"] = DEFAULT_LOCAL_IDP_NAME
                    #  Regenerate user_id based on username, password and idp_name
                    doc["user_id"] = User.generate_hash([doc["username"], str(doc["password"]), doc["idp_name"]])
                    del doc["authenticate_mode"]
            # Update import policy
            data[users_idx]["import_policy"]["key_index"] = [{"idp_name": "ASCENDING", "user_id": "ASCENDING"},
                                                             {"idp_name": "ASCENDING", "username": "ASCENDING"}]
            # ldap_config to idp_config
            ldap_config_idx = find_collection(data, "ldap_config")
            if ldap_config_idx >= 0:
                for doc in data[ldap_config_idx]["data"]:
                    # add idp_type and idp_name
                    doc["idp_name"] = self.compute_idp_name_from_domain(doc["domain"])
                    doc["idp_label"] = doc["idp_name"]
                    doc["idp_type"] = IdpType.ldap.name
            # rename collection and update
            data[ldap_config_idx]["collection"] = "idp_config"
            data[ldap_config_idx]["import_policy"]["key_index"] = [{"idp_name": "ASCENDING"}]
        except Exception as exception:
            LOG.error("ImportUpgradeException exception: %s", exception)
            raise ImportUpgradeException("Fail to upgrade from previous version") from exception
