"""
Script Python for Upgrading the database of UM from version 4.X or [5.X, 8.X] to 9.X
"""
import argparse
import os
import logging
import sys

from pymongo import MongoClient, ASCENDING, errors as mongo_errors
from pymongo.results import DeleteResult, UpdateResult

from ateme.um_backend.types import User, PasswordPolicy

# Add Logger Config
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv('UM_DATABASE_URL', 'mongodb://localhost:27017'))
    parser.add_argument("--database-name", default=os.getenv('UM_DATABASE_NAME', 'users'))
    return parser.parse_args()

def check_upgrade():
    """
    Main function of check upgrade script of UM
    We check if we are in version 4.X, in [5.X, 8.X] or in 9.X

    If we are not in 9.X -> exits with 0 code (we upgrade)
    If not -> we do nothing
    """
    args = parse_args()
    db_url = args.database_url
    db_name = args.database_name
    client = MongoClient(db_url)
    # Check if "idp_config" collection exists and "idp_name" index exists in the DB
    idp_config_exists = "idp_config" in client[db_name].list_collection_names()
    idp_name_exists = False
    for _, val in client[db_name].users.index_information().items():
        for key_l in val['key']:
            if 'idp_name' in key_l:
                idp_name_exists = True
    # If the collections does not exists, it means we are in version 4.X
    if not idp_config_exists and not idp_name_exists:
         sys.exit(0)

    # Determine if we are in version < 9.X or >= 9.X (password_policy added in 9.0 configuration)
    configuration = client[db_name].configuration.find_one({})
    if "password_policy" not in configuration:
        logging.info("Password_policy missing in configuration. Upgrade required.")
        sys.exit(0)
    logging.info("Upgrade not need it.")
    sys.exit(1)


def upgrade():
    """
    Main function of an upgrade script of UM
    from version 4.X or [5.X, 8X] to 9.X
    """
    args = parse_args()
    db_url = args.database_url
    db_name = args.database_name
    client = MongoClient(db_url)

    idp_config_exists = "idp_config" in client[db_name].list_collection_names()
    if not idp_config_exists:
        # Drop existing indexes on users collection created by UM v4.0
        logging.info("Drop users collection indexes: user_id and username")
        try:
            client[db_name].users.drop_index('user_id_1')
        except mongo_errors.OperationFailure:
            pass  # index doesn't exist (anymore)

        try:
            client[db_name].users.drop_index('username_1')
        except mongo_errors.OperationFailure:
            pass  # index doesn't exist (anymore)

        logging.info("Drop ldap_config collection indexes: domain")
        try:
            client[db_name].ldap_config.drop_index('domain_1')
        except mongo_errors.OperationFailure:
            pass  # index doesn't exist (anymore)

        # Create the new indexes v5.0
        logging.info("Create users collection indexes: user_id and username with idp_name")
        client[db_name].users.create_index([('user_id', ASCENDING), ('idp_name', ASCENDING)],
                                            unique=True)
        client[db_name].users.create_index([('username', ASCENDING), ('idp_name', ASCENDING)],
                                            unique=True)

        # Create a transaction to process all write operations
        with client.start_session() as session:
            with session.start_transaction():

                # Delete users which do not have a domain_ldap
                # Those users will be recreated on next login
                delete_result: DeleteResult = client[db_name].users.delete_many(
                    {
                        '$and': [
                            {'authenticate_mode': 'ldap'},
                            {'domain_ldap': {'$exists': False}}
                        ]
                    },
                    session=session
                )
                logging.info("delete_many operation (users): remove LDAP users without a domain -> "
                             "deleted count: %d", delete_result.deleted_count)

                # Migrate data for collections "users" and "admin"
                result: UpdateResult = client[db_name].users.update_many(
                    {'authenticate_mode': 'ldap'},
                    [
                        {"$addFields": {'idp_new_name': {"$concat": ['ldap_', '$domain_ldap']}}},
                        {"$set": {'idp_name': '$idp_new_name'}},
                        {"$unset": ['domain_ldap', 'idp_new_name']}
                    ],
                    session=session
                )
                logging.info("update_many operation (users): add idp_name from domain -> "
                             "matched count: %d, modified count: %d", result.matched_count, result.modified_count)

                for col_name in ["users", "admin"]:

                    result = client[db_name][col_name].update_many(
                        {"authenticate_mode": {"$ne": "ldap"}},
                        {"$set": {'idp_name': 'local'}},
                        session=session
                    )
                    logging.info(f"update_many operation ({col_name}): set idp_name to local if auth mode not ldap -> "
                                 "matched count: %d, modified count: %d", result.matched_count, result.modified_count)

                    for user in client[db_name][col_name].find(
                        {},
                        session=session
                    ):
                        new_user_id = User.generate_hash([user['username'], user['password'] or "", user['idp_name']])
                        client[db_name][col_name].update_one({'_id': {'$eq': user['_id']}},
                                                             {"$set": {'user_id': new_user_id}},
                                                             session=session)
                    logging.info(f"user_id updated ({col_name})")

                    result = client[db_name][col_name].update_many(
                        {},
                        {"$unset": {'authenticate_mode': ""}},
                        session=session
                    )
                    logging.info(f"update_many operation ({col_name}): unset authenticate mode -> "
                                 "matched count: %d, modified count: %d", result.matched_count, result.modified_count)

                # Migrate data Third Part "collection ldap_config"
                logging.info("Start migrating data for ldap_config collection.")
                result = client[db_name].ldap_config.update_many(
                    {},
                    [
                        {"$addFields": {'idp_new_name': {"$concat": ['ldap_', '$domain'] } }},
                        {"$set": {'idp_name': '$idp_new_name', 'idp_label': '$idp_new_name', 'idp_type': 'ldap'}},
                        {"$unset": ['idp_new_name']}
                    ],
                    session=session
                )
                logging.info("update_many operation (ldap_config/idp_config): set idp_name, idp_label and idp_type -> "
                             "matched count: %d, modified count: %d", result.matched_count, result.modified_count)

        if "idp_config" not in client[db_name].list_collection_names() and "ldap_config" in client[db_name].list_collection_names():
            client[db_name].ldap_config.rename("idp_config")
            logging.info("Finish migrating data: ldap_config collection updated and renamed to idp_config")
        else:
            logging.info("Idp config collection already exist")
    else:
        logging.info("No upgrade required for idp_config collection")

    logging.info("Drop clients collection indexes: remote and username")
    try:
        client[db_name].clients.drop_index('remote_1_username_1')
    except mongo_errors.OperationFailure:
        pass  # index doesn't exist (anymore)

    configuration = client[db_name].configuration.find_one({})
    if "password_policy" not in configuration:
        logging.info("Upgrade configuration in db by adding default password_policy")
        client[db_name].configuration.update_one(
            {},
            {"$set": {'password_policy': {'expiration_delay_in_days': -1, 'regex_pattern': PasswordPolicy.get_password_regex_pattern()}},
             "$unset": {'password_expiration': ''}},
            upsert=True
        )
        logging.info("Configuration upgraded")
    else:
        logging.info("No upgrade required for Configuration")
