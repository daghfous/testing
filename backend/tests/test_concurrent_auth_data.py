""" test_concurrent_auth_data.py
"""
import os
import pytest

from ateme.openapi import OpenApiDefinition
from ateme.um_backend.types import Scope


CURRENT_DIR = os.path.join(os.path.dirname(__file__))
APP_NAME = "pms"
APP_SCOPE_ID = f"{APP_NAME}:administrator"
E2E_SCOPE_ID = f"{APP_NAME}:e2e:administrator"


# reproduce MS-11380
@pytest.mark.parametrize(
    "auth_data_content", [
        pytest.param(
            {
                "api_descriptors": [],
                "actions": [],
                "scopes": [
                    Scope(
                        id=APP_SCOPE_ID,
                        label="pma",
                        version=3,
                        content=[
                            {"scope": f"{APP_NAME}:pma:administrator"},
                            {"scope": E2E_SCOPE_ID}
                        ],
                    ).to_dict(),
                    Scope(
                        id=f"{APP_NAME}:pma:administrator",
                        label="pma",
                        version=3,
                        content=[],
                    ).to_dict(),
                ]
            },
            id="workaround-pms-auth-data",
        ),
        pytest.param(
            {
                "api_descriptors": [],
                "actions": [],
                "scopes": [
                    Scope(
                        id=APP_SCOPE_ID,
                        label="pma",
                        version=3,
                        content=[
                            {"scope": f"{APP_NAME}:pma:administrator"}
                        ],
                    ).to_dict(),
                    Scope(
                        id=f"{APP_NAME}:pma:administrator",
                        label="pma",
                        version=3,
                        content=[],
                    ).to_dict(),
                ],
            },
            id="expected-pms-auth-data",
        ),
    ],
)
@pytest.mark.asyncio
async def test_concurrent_auth_data(init_backend, auth_data_content):
    """
    @Goals: Test concurrent posting auth data between E2E definition and PMS configmap @End
    @Type: Functional @End
    @Priority: Critical @End
    @Automating Status: Automated @End
    @Reference: MS-11380 @End

    @Preconditions: Start user-management web application @End
    @Step: Post E2E definition (as ingress controller mode) @End
    @Expected: E2E scopes are present, app scopes created and hat scopes updated @End
    @Step: Post PMS auth data (as configmap controller mode) @End
    @Expected: PMS scopes are present, app scopes and hat scopes updated. E2E scopes must be preserved @End
    @Step: Delete PMS auth data (as configmap controller mode) @End
    @Expected: PMS scopes are deleted, app scopes and hat scopes updated. E2E scopes must be preserved @End
    """
    client, init_api = init_backend

    async def _check_scope_coherency():
        """ _check_scope_coherency
        """
        scope_dict = await init_api.db.collection_scopes.get_by_id("all:administrator")
        scope_ids = [scope["scope"] for scope in scope_dict["content"]]
        assert APP_SCOPE_ID in scope_ids
        scope_dict = await init_api.db.collection_scopes.get_by_id(APP_SCOPE_ID)
        scope_ids = [scope["scope"] for scope in scope_dict["content"]]
        assert scope_ids.count(E2E_SCOPE_ID) == 1

    # First publish the API definition
    definition = OpenApiDefinition(
        definition_file=os.path.join(CURRENT_DIR, "definitions", "e2e.yaml")
    )
    resp = await client.post(
        "/api_definition",
        json={
            "base_url": "api.example.com",
            "main_api": definition.definition,
            "app_name": APP_NAME,
        }
    )
    assert resp.status == 201
    await _check_scope_coherency()

    # Then, post the auth data
    resp = await client.post(
        "/auth_data",
        json={
            "type": "ADDED",
            "content": auth_data_content
        },
    )
    assert resp.status == 200
    await _check_scope_coherency()

    # Then, remove the auth data
    resp = await client.post(
        "/auth_data",
        json={
            "type": "DELETED",
            "content": auth_data_content
        },
    )
    assert resp.status == 200
    await _check_scope_coherency()
