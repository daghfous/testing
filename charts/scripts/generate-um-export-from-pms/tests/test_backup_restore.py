import os
import subprocess
import re

import requests
import pytest


@pytest.mark.parametrize("app_name", ["pms", None])
def test_backup_restore(binary_path, api_url, database_client, init, tmp_path, backup_filepath, app_name):
    cmd = [
        binary_path,
        f"--backup-file-name={backup_filepath}",
        f"--relative-output-directory={tmp_path}",
    ]

    if app_name:
        cmd.append(f"--app-name-to-patch-in-scopes={app_name}")

    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
    )
    assert res.returncode == 0
    export_filepath = re.search("Export zip file '(.*)'", res.stdout.decode()).group(1)
    requests.put(
        f"{api_url}/users/fullconfiguration",
        files={"export.json": open(export_filepath, "rb")},
        headers={"Authorization": f"Bearer {init}"},
    )

    scopes = database_client["scopes"].find(
        {"$or": [{"default": False}, {"default": {"$exists": False}}]}, projection={"_id": False}
    )
    print(list(scopes))

    count_scopes = database_client["scopes"].count_documents(
        {"$or": [{"default": False}, {"default": {"$exists": False}}]}
    )
    assert count_scopes

    users = database_client["users"].find(
        {"$or": [{"default": False}, {"default": {"$exists": False}}]}, projection={"_id": False}
    )
    print(list(users))

    count_users = database_client["users"].count_documents(
        {"$or": [{"default": False}, {"default": {"$exists": False}}]}
    )
    assert count_users
