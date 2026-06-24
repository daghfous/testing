"""
Updater module
"""
from typing import List, Any, Set
import json

from importlib import resources
from bson import json_util

from ateme.updater import Updater, find_collection

from .data_migration_imp import DataMigrationImp
from .database import Database, Collections


class UserUpdater(Updater):
    """

    User implementation of Updater.
    """
    PACKAGE_NAME = "ateme.um_backend"
    json_dumps = staticmethod(json_util.dumps)

    def __init__(self, db: Database, migration_file: str):
        self.db = db
        self.data_migration_imp = DataMigrationImp()
        super().__init__(migration_file=resources.files(self.PACKAGE_NAME) / migration_file,
                         data_migration_imp=self.data_migration_imp)

    def consolidate_data(self, data: list, actions: list, scopes: list):
        """

        Consolidate data, remove unexist action and scope ref in users and scopes data.
        Even if we don't find any scopes and actions ref we have to persist scope or user.

        Args:
            data (list): List of collection to import
            actions (list): Actions ref list
            scopes (list): Scopes ref list
        """
        scopes_id = {item.id for item in scopes}
        actions_id = [item.name for item in actions]
        # iterate over scopes
        scopes_idx = find_collection(data, Collections.scopes.name)
        if scopes_idx >= 0:
            # We have to make an union between scopes from db and scopes from backup file
            scopes_id |= {item["id"] for item in data[scopes_idx]["data"]}
            for item in data[scopes_idx]["data"]:
                item["content"] = [ref for ref in item["content"] if self._check_ref(ref, actions_id, scopes_id)]
        # iterate over users
        users_idx = find_collection(data, Collections.users.name)
        if users_idx >= 0:
            for item in data[users_idx]["data"]:
                item["scopes"] = [ref for ref in item.get("scopes", []) if ref in scopes_id]

    @staticmethod
    def _check_ref(data: dict, actions: List[str], scopes: Set[str]) -> bool:
        """

        check if ref present in actions and scopes list

        Args:
            data (dict): data may be a scope content or an action
            actions (list): actions ref
            scopes (list): scopes ref

        Returns:
            bool: If we find ref
        """
        if "action" in data:
            return data["action"] in actions
        if "scope" in data:
            return data["scope"] in scopes
        return False

    async def export_collection(self, collection_name: str, filters: dict, fields_projection: dict) -> List[Any]:
        """
        Extract from the db the data of a collection, based on the collection file
        Raise an exception in case of file validation error or incoherency
        Args:
            collection_name:
            filters:
            fields_projection:

        Returns:
            exported data and the update_policy
        """
        # Get the data from the db
        if not fields_projection:
            # Export all fields of the filtered data
            export_result = await self.db.get_generic_data(collection_name=collection_name, filters=filters)
        else:
            # Export only the fields specified in the export_policy/fields (expressed as a mongo projection)
            # for filtered data
            export_result = await self.db.get_generic_data(collection_name=collection_name,
                                                           filters=filters,
                                                           projection=fields_projection)
        # Explicit BSON conversion to json to deal with ObjectId from mongo
        export_result = json.loads(json_util.dumps(export_result))

        return export_result

    async def import_collections(self, data: dict):
        """

        Import collections implementation: we first consolidate scope and action references and
        pass to database layer in order to update data.

        Args:
            data (dict): backup data to import
        """
        actions = await self.db.collection_actions.get_list()
        scopes = await self.db.collection_scopes.get_list()
        self.consolidate_data(data, actions, scopes)
        await self.db.import_full_configuration(data)
