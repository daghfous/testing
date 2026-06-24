import os

import pytest
import pymongo
import requests


def pytest_addoption(parser):
    parser.addoption(
        "--binary-path",
        action="store",
        default=os.path.join(os.path.dirname(__file__), "..", "generate_um_export_from_pms.bin"),
    )
    parser.addoption(
        "--mongodb-url",
        action="store",
        default="mongodb://127.0.0.1:27017/?directConnection=true"
    )
    parser.addoption(
        "--user-url",
        action="store",
        default="http://127.0.0.1:3080/user"
    )


@pytest.fixture(scope="session")
def binary_path(pytestconfig):
    return pytestconfig.getoption("--binary-path")


@pytest.fixture
def admin_credentials():
    yield "admin", "adminA!0"


@pytest.fixture
def mongo_url(pytestconfig):
    yield pytestconfig.getoption("--mongodb-url")


@pytest.fixture
def api_url(pytestconfig):
    yield pytestconfig.getoption("--user-url")


@pytest.fixture
def mongo_client(mongo_url):
    yield pymongo.MongoClient(mongo_url)


@pytest.fixture
def database_client(mongo_client):
    db = [item for item in mongo_client.list_databases() if item["name"].endswith("user-management")]
    assert db
    database_client = mongo_client[db[0]["name"]]

    yield database_client

    database_client["scopes"].delete_many({"$or": [{"default": False}, {"default": {"$exists": False}}]})
    database_client["users"].delete_many({"$or": [{"default": False}, {"default": {"$exists": False}}]})


@pytest.fixture
def init(api_url, admin_credentials):
    resp = requests.post(
        f"{api_url}/users/admin", json={"username": admin_credentials[0], "password": admin_credentials[1]}
    )
    resp = requests.post(
        f"{api_url}/users/token", json={"username": admin_credentials[0], "password": admin_credentials[1]}
    )
    data = resp.json()
    yield data["access_token"]
    # cleanup


def pytest_generate_tests(metafunc):
    metafunc.parametrize(
        "backup_filepath",
        [
            f"{os.path.dirname(__file__)}/data/{item}"
            for item in os.listdir(os.path.join(os.path.dirname(__file__), "data"))
        ],
    )
