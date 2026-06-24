"""

Test probe endpoints
"""
import pymongo


async def test_ping(init_backend):
    """

    :param init_backend:
    :return:
    """
    _api, _ = init_backend
    ping_resp = await _api.get("/ping")
    assert ping_resp.status == 200
    assert await ping_resp.text() == "OK"

async def test_get_readiness(init_backend, mocker):
    """

    :param init_backend:
    :param mocker:
    :return:
    """
    _api, _ = init_backend
    readiness_resp = await _api.get("/readiness")
    assert readiness_resp.status == 200
    assert await readiness_resp.text() == "OK"

    async def mock_list_run_admin_command(*args):
        raise pymongo.errors.ConnectionFailure
    mocker.patch("ateme.um_backend.database.Database.run_admin_command", mock_list_run_admin_command)
    readiness_resp = await _api.get("/readiness")
    assert readiness_resp.status == 503
    assert await readiness_resp.text() == "Database not available"
    mocker.stopall()
