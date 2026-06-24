import argparse
import os.path
import re
import zipfile
from typing import Dict, List, Any
from datetime import datetime
import json
import hashlib

from bson import json_util
import semver

from ateme.um_backend.types import (
    User,
    Scope,
    LdapConfig,
    Configuration,
)

USERS = "users"
SCOPES= "scopes"
LDAP_CONFIG = "ldap_config"
CONFIGURATION = "configuration"

SUPPORTED_PMS_VERSIONS = ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"]

PMS_VERSION_UM_VERSION = {
    "2.1": "3.21.0",
    "2.2": "3.21.0",
    "2.3": "3.25.0",
    "2.4": "3.33.0",
    "2.5": "3.33.0",
    "2.6": "3.33.0"
}

COLLECTIONS_TO_PROCESS = [USERS, LDAP_CONFIG, CONFIGURATION, SCOPES]
UM_VERSION = "4.0"
UM_COMPONENT_NAME = "user-management"
UM_PACKAGE_NAME = "user-management"
MIGRATION_SCHEMA = {
    "configuration": {
        "collection": "configuration",
        "import_policy": {"conflict_management": "override", "key_index": []}
    },
    "users": {
        "collection": "users",
        "import_policy": {"conflict_management": "abort", "key_index": [{"username": "ASCENDING"}]}
    },
    "scopes": {
        "collection": "scopes",
        "import_policy": {"conflict_management": "abort", "key_index": [{"id": "ASCENDING"}]}
    },
    "ldap_config": {
        "collection": "ldap_config",
        "import_policy": {"conflict_management": "override", "key_index": [{"domain": "ASCENDING"}]}
    }
}

def read_backup_file(file_name) -> Dict:
    """
    Return the content of the backup file as a json

    Args:
        file_name: the src backup file

    Returns:
        the json content of the backup file
    """
    json_content: Dict = {}
    try:
        with open(file_name, 'r') as file:
            content = file.read()
        json_content = json.loads(content)
    except Exception as exception:
        print(f"Fatal: Error {exception} when trying to read file {file_name}")
        raise exception
    return json_content

def get_pms_version(json_content: Dict) -> str:
    """
    Get the PMS version from the provided JSON content.

    Args:
        json_content (Dict): The JSON content.

    Returns:
        str: The PMS version.

    Raises:
        Exception: If the PMS version is not found in the JSON content.
    """
    version = json_content["amsBackupVersion"]
    parsed_version = semver.parse_version_info(version)
    pms_version: str = f"{parsed_version.major}.{parsed_version.minor}"
    return pms_version

def get_users_data(data: Dict) -> Dict:
    """
    Extracts the users data from the JSON content.

    Args:
        data (Dict): The JSON content to extract the users data from.

    Returns:
        List[Dict]: A list of dictionaries representing the users data.

    Raises:
        Exception: If the users data is not found in the JSON content.
    """

    if "users" in data:
        return data["users"]
    print("Fatal: Users data not found in backup file")
    raise Exception("Fatal: Users data not found in backup file")

def process_collection(name: str, data: List[Dict]) -> Dict:
    """
    Compute the export for a collection

    Args:
        name: the name of te collection
        data: the data to be exported

    Returns:
        the exported collection
    """
    result = {}
    if name == "scopes":
        result = process_scopes_collection(scopes=data,)
    elif name == "ldap_config":
        result = process_ldap_config_collection(ldap_configs=data)
    elif name == "configuration":
        result = process_configuration_collection(configurations=data)
    elif name == "users":
        result = process_users_collection(users=data)
    else:
        print(f"Error: Unexpected collection to process: {name}. Skip it")
    return result

def process_scopes_collection(scopes: List[Dict]) -> Dict:
    """
    Generate the scopes part of the export file from the backup data.

    Changes for scopes collection between the UM versions:
    3.33.0 -> 4.1.0:
        - No changes
    3.25.0 -> 4.1.0:
        - No changes
    3.21.0 -> 4.1.0:
        - No changes

    Args:
        scopes: The scopes to export

    Returns:
        The export part of this collection that will be added in the export file
    """

    exported_scopes: List[Dict] = []
    # Add header in the export content for this collection
    exported_collection: Dict = MIGRATION_SCHEMA["scopes"]
    # Migrate all items to the User struct used for UM 4.0
    for scope in scopes:
        scope_obj = Scope.from_dict(scope)
        if scope_obj.default or scope_obj.internal:
            print(f"Warning: Scope {scope} is an internal or a default scope. Skip it")
            continue
        exported_scopes.append(scope_obj.to_dict())
    exported_collection["data"] = exported_scopes
    return exported_collection

def process_ldap_config_collection(ldap_configs: List[Dict]) -> Dict:
    """
    Generate the ldap_config part of the export file from the backup data.

    Changes for ldap_config collection between the UM versions:

    3.33.0 -> 4.1.0:
        - Add "scopes", default:["all:guest"]
        - Add "automatically_add_user", default: False
    3.25.0 -> 4.1.0:
        - Add "scopes", default: ["all:guest"]
        - Add "automatically_add_user", default: False
    3.21.0 -> 4.1.0:
        - Add "scopes", default: ["all:guest"]
        - Add "automatically_add_user", default: False
    Args:
        ldap_configs:

    Returns:
        The export part of this collection that will be added in the export file
    """
    migrated_ldap_configs: List[Dict] = []
    # Add header in the export content for this collection
    exported_collection: Dict = MIGRATION_SCHEMA["ldap_config"]
    # Migrate all items to the LdapConfig struct used for UM 4.0
    for ldap_config in ldap_configs:
        if "scopes" not in ldap_config:
            ldap_config["scopes"] =  ["all:guest"]
        if "automatically_add_user" not in ldap_config:
            ldap_config["automatically_add_user"] = False
        ldap_config_obj = LdapConfig.from_dict(ldap_config)
        migrated_ldap_configs.append(ldap_config_obj.to_dict())
    exported_collection["data"] = migrated_ldap_configs
    return  exported_collection

def process_configuration_collection(configurations: List[Dict]) -> Dict:
    """
    Generate the configuration part of the export file from the backup data.

    Changes for configuration collection between the UM versions:
    * 3.33.0 -> 4.1.0:
        - No change
    * 3.25.0 -> 4.1.0:
        - Add refresh_token_expiration (default 7200)
    * 3.21.0 -> 4.1.0:
        - Add refresh_token_expiration (default 7200)

    Args:
        configurations:

    Returns:
        The export part of this collection that will be added in the export file
    """

    migrated_configurations: List[Dict] = []
    # Add header in the export content for this collection
    exported_collection: Dict = MIGRATION_SCHEMA["configuration"]
    # Migrate all items to the Configuration struct used for UM 4.0
    for configuration in configurations:
        if "refresh_token_expiration" not in configuration:
            configuration["refresh_token_expiration"] = 7200
        configuration_obj = Configuration.from_dict(configuration)
        migrated_configurations.append(configuration_obj.to_dict())
    exported_collection["data"] = migrated_configurations
    return exported_collection

def process_users_collection(users: List[Dict]) -> Dict:
    """
    Generate the configuration part of the export file from the backup data.

    Changes for configuration collection between the UM versions:
    * 3.33 -> 4.0:
        - Add domain_ldap
    * 3.25.0 -> 4.1.0:
        - Add domain_ldap
        - first_login: str-> bool
    * 3.21.0 -> 4.1.0:
        - Add domain_ldap
        - first_login: str-> bool
    Args:
        users:

    Returns:
        The export part of this collection that will be added in the export file
    """

    migrated_users: List[Dict] = []
    # Add header in the export content for this collection
    exported_collection: Dict = MIGRATION_SCHEMA["users"]
    # Migrate all items to the User struct used for UM 4.0
    for user in users:
        # first_login: Convert str to bool if required
        if "first_login" in user and isinstance(user["first_login"], str):
            user["first_login"] = user["first_login"].lower() == 'true'  # Converting "True" to True
        if "domain_ldap" not in user:
            user["domain_ldap"] = ""
        user_obj = User.from_dict(user)
        migrated_users.append(user_obj.to_dict(with_creation_id=True))

    exported_collection["data"] = migrated_users
    return exported_collection

def create_export_file(exported_collections: List[Dict], export_file_name: str):
    """
    Write the export file with exported collections, the global header and the hash computed on the whole content

    Args:
        exported_collections: the data to write in the export file
        export_file_name: the name of the result export file

    Returns:

    """
    # Add the global header
    export_content: Dict[str, Any] = {
        "component": UM_COMPONENT_NAME,
        "version": UM_VERSION,
        "generation_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "data": {UM_VERSION: []}
    }
    # Add entry "4.0." in the data part with the exported data
    export_content["data"][UM_VERSION] = exported_collections
    # Finally, add the hash for the whole file content
    computed_hash = hashlib.md5(json_util.dumps(export_content, sort_keys=True).encode('utf-8')).hexdigest()
    export_content["hash"] = computed_hash

    # Write the zip file on the disk
    with zipfile.ZipFile(f"{export_file_name}.zip", mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        # Encode the JSON data to bytes and write it to the zipfile
        zip_file.writestr(f"{export_file_name}.json", json_util.dumps(export_content).encode())
        print(f"Export zip file '{export_file_name}.zip' created successfully.")

def post_processing(data: List[Dict], target_app_name: str):
    """
    Post Processing of the export data before writing the export file.
    Required to patch the app-name in the scopes.

    Args:
        data: the data to post-process
        target_app_name: the new application name used for scopes patch

    Returns:
        the data post-processed
    """
    data = patch_scope_app_name(data=data, target_app_name=target_app_name)
    return data

def patch_scope_app_name(data: List[Dict], target_app_name):
    """
    Patch scopes having the format <app-name>:<prefix>:<scope> with new application name in the whole data.
    The patched scopes will be: target_app_name:<prefix>:<scope>.
    This patch is applied on the whole data, not only on the Scopes collection.

    Args:
        data: the data to patch
        target_app_name: the new application name to patch in the scopes

    Returns:
        the data with scopes patched
    """
    data_str = json.dumps(data)
    # Pattern for scope search
    pattern = r"(\w+):(\w+):(\w+)"
    # Replace the <app-name> part of scopes by the new application name
    patched_data = re.sub(pattern, rf"{target_app_name}:\2:\3", data_str)
    # Add <target_app_name> to scope without <app-name>
    pattern = r'"(\w+)(?<!usr|all):(\w+)"'
    patched_data = re.sub(pattern, rf'"{target_app_name}:\1:\2"', patched_data)

    patched_data = json.loads(patched_data)
    return patched_data


def main():

    exported_collections = []
    parser = argparse.ArgumentParser(description='Generate Export file from PMS backup compatible with UM import/export feature')
    parser.add_argument('--backup-file-name', help='Database backup file to process', required=True)
    parser.add_argument('--app-name-to-patch-in-scopes', help='App Name to use for patching scopes', required=True)
    parser.add_argument('--relative-output-directory', help='The directory where the output will be stored', default="")

    args = parser.parse_args()

    output_file_name = f"export-UM-4.0-{os.path.basename(args.backup_file_name).rsplit('.', 1)[0]}"
    if args.relative_output_directory:
        output_file_name = os.path.join(args.relative_output_directory, output_file_name)

    backup_data = read_backup_file(args.backup_file_name)
    app_name_to_patch_in_scopes = args.app_name_to_patch_in_scopes

    pms_version = get_pms_version(backup_data)
    if not pms_version or pms_version not in PMS_VERSION_UM_VERSION.keys():
        raise Exception(f"PMS version not found in backup file "
                        f"or this version '{pms_version}' is not among the supported versions: "
                        f"{list(PMS_VERSION_UM_VERSION.keys())}.")

    # Retrieve the users part in the backup file that will be used to create the export file
    imported_users_data = get_users_data(backup_data)

    # For information purpose only
    for collection in imported_users_data.keys():
        if collection not in COLLECTIONS_TO_PROCESS:
            print(f"Warning: Collection '{collection}' data in backup file won't be used for export file "
                  f"because this collection is not managed by the UM import/export feature")

    # Process the 4 targeted collections: Users, Scopes, Ldap Config and Configurations
    for collection in COLLECTIONS_TO_PROCESS:
        imported_collection_data: List[Dict] = []
        if collection in imported_users_data:
            print(f"Processing backup data of {collection}")
            imported_collection_data = imported_users_data[collection]
        else:
            imported_collection_data = []
            print(f"Warning: '{collection}' data not found in the backup file. Add an empty entry in the export file")
        exported_collection = process_collection(name=collection, data=imported_collection_data)
        exported_collections.append(exported_collection)

    exported_collections = post_processing(data=exported_collections, target_app_name=app_name_to_patch_in_scopes)

    # Write the whole export file with header and hash
    create_export_file(exported_collections=exported_collections, export_file_name=output_file_name)

if __name__ == '__main__':
    main()