"""
Test request utils
"""
import base64
import logging
from contextlib import ExitStack as DoesNotRaise
import pytest
from packaging.version import Version

from ateme.openapi import Request
from ateme.um_backend.loggers import LOGGER_NAME
from ateme.um_backend.exceptions import RequestExtractError
from ateme.um_backend.request_utils import (
    show_headers,
    extract_token,
    extract_uri_and_method,
    extract_api_url,
    extract_user_ip,
    extract_user_agent
)


@pytest.mark.parametrize("_request, expected_result",[
    pytest.param(
        Request(
            headers={
                "X-api-url": "test_api_url_1",
                "x-api-url": "test_api_url_2",
                "unknown_header": "coucou",
            },
            parameters={}, body={}, url="", method="", remote=""
        ),
        {"x-api-url": "test_api_url_2", "X-api-url": "test_api_url_1"},
        id="extract api url from x-api-url"
    ),
])
def test_show_headers(caplog, _request: Request, expected_result: dict):
    """
    Test function extract_api_url
    """
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        show_headers(_request)
        assert len(caplog.records) == 1
        assert caplog.records[0].msg == expected_result


def create_ws_token(token: str) -> str:
    """
    Create a WS token
    """
    return "base64url.bearer.authorization." + base64.b64encode(token.encode("utf-8")).decode("utf-8")


@pytest.mark.parametrize("_request, introspection, context, expected_result",[
    pytest.param(
        Request(
            headers={
                "Authorization": "Bearer tokenauth123456",
                "Sec-WebSocket-Protocol": create_ws_token("tokenws123456")
            },
            parameters={},
            body={"token": ["tokenbody123456"]},
            url="",
            method="",
            remote=""
        ),
        False,
        DoesNotRaise(),
        "tokenauth123456",
        id="basic extract token from Authorization header only succeed"
    ),
    pytest.param(
        Request(
            headers={
                "Authorization": "Bearer tokenauth123456",
                "Sec-WebSocket-Protocol": create_ws_token("tokenws123456")
            },
            parameters={},
            body={"token": ["tokenbody123456"]},
            url="",
            method="",
            remote=""
        ),
        False,
        DoesNotRaise(),
        "tokenauth123456",
        id="basic extract token from Authorization header only failed"
    ),
    pytest.param(
        Request(
            headers={},
            parameters={},
            body={},
            url="",
            method="",
            remote=""
        ),
        True,
        pytest.raises(RequestExtractError, match="Can't find token in request"),
        "",
        id="introspection extract token failed"
    ),
    pytest.param(
        Request(
            headers={
                "Authorization": "Bearer tokenauth123456",
                "Sec-WebSocket-Protocol": create_ws_token("tokenws123456")
            },
            parameters={},
            body={"token": ["tokenbody123456"]},
            url="",
            method="",
            remote=""
        ),
        True,
        DoesNotRaise(),
        "tokenauth123456",
        id="introspection extract token from Authorization header"
    ),
    pytest.param(
        Request(
            headers={
                "Sec-WebSocket-Protocol": create_ws_token("tokenws123456")
            },
            parameters={},
            body={"token": ["tokenbody123456"]},
            url="",
            method="",
            remote=""
        ),
        True,
        DoesNotRaise(),
        "tokenbody123456",
        id="introspection extract token from body"
    ),
    pytest.param(
        Request(
            headers={
                "Sec-WebSocket-Protocol": ",".join([
                    "another.protocol.grizoureviens",
                    create_ws_token("tokenws123456"),
                ])
            },
            parameters={},
            body={},
            url="",
            method="",
            remote=""
        ),
        True,
        DoesNotRaise(),
        "tokenws123456",
        id="introspection extract token from Sec-WebSocket-Protocol header"
    ),
    pytest.param(
        Request(
            headers={
                "Sec-WebSocket-Protocol": "base64url.bearer.authorization.badtoken" + ",another.protocol.gryzoureviens",
            },
            parameters={},
            body={},
            url="",
            method="",
            remote=""
        ),
        True,
        pytest.raises(RequestExtractError, match="Can't decode token"),
        "",
        id="introspection extract token error from Sec-WebSocket-Protocol header"
    ),
])
def test_extract_token(_request: Request, introspection: bool, context, expected_result: str):
    """
    Test function extract_token
    """
    with context:
        assert expected_result == extract_token(_request, introspection)


FAKE_HEADER_URI = "/header/uri"
FAKE_HEADERS_METHOD = "HeaderMethod"
FAKE_BODY_URI = "/body/uri"
FAKE_BODY_METHOD = "BodyMethod"

@pytest.mark.parametrize("_request, context, expected_result",[
    pytest.param(
        Request(
            headers={"X-Original-URI": FAKE_HEADER_URI, "X-Original-Method": FAKE_HEADERS_METHOD},
            parameters={},
            body={"uri": [FAKE_BODY_URI], "method": [FAKE_BODY_METHOD]},
            url="", method="", remote=""
        ),
        DoesNotRaise(),
        (FAKE_HEADER_URI, FAKE_HEADERS_METHOD),
        id="extract uri and method from headers"
    ),
    pytest.param(
        Request(
            headers={"X-Original-URI": FAKE_HEADER_URI},
            parameters={},
            body={"uri": [FAKE_BODY_URI], "method": [FAKE_BODY_METHOD]},
            url="", method="", remote=""
        ),
        DoesNotRaise(),
        (FAKE_BODY_URI, FAKE_BODY_METHOD),
        id="extract uri and method from body 1"
    ),
    pytest.param(
        Request(
            headers={"X-Original-Method": FAKE_HEADERS_METHOD},
            parameters={},
            body={"uri": [FAKE_BODY_URI], "method": [FAKE_BODY_METHOD]},
            url="", method="", remote=""
        ),
        DoesNotRaise(),
        (FAKE_BODY_URI, FAKE_BODY_METHOD),
        id="extract uri and method from body 2"
    ),
    pytest.param(
        Request(
            headers={},
            parameters={},
            body={"uri": FAKE_BODY_URI, "method": FAKE_BODY_METHOD},
            url="", method="", remote=""
        ),
        DoesNotRaise(),
        (FAKE_BODY_URI, FAKE_BODY_METHOD),
        id="extract uri and method from body 3"
    ),
    pytest.param(
        Request(headers={}, parameters={}, body={}, url="", method="", remote=""),
        pytest.raises(RequestExtractError),
        ("", ""),
        id="extract uri and method failed"
    ),
])
def test_extract_uri_and_method(_request: Request, context, expected_result: tuple[str, str]) -> str:
    """
    Test function extract_uri_and_method
    """
    with context:
        assert expected_result == extract_uri_and_method(_request)


FAKE_BIG_X_API_URL = "Xapiurl"
FAKE_LITTLE_X_API_URL = "xapiurl"

@pytest.mark.parametrize("_request, expected_result",[
    pytest.param(
        Request(
            headers={"X-api-url": FAKE_BIG_X_API_URL, "x-api-url": FAKE_LITTLE_X_API_URL},
            parameters={}, body={}, url="", method="", remote=""
        ),
        FAKE_LITTLE_X_API_URL,
        id="extract api url from x-api-url"
    ),
    pytest.param(
        Request(
            headers={"X-api-url": FAKE_BIG_X_API_URL},
            parameters={}, body={}, url="", method="", remote=""
        ),
        FAKE_BIG_X_API_URL,
        id="extract api url from X-api-url"
    ),
    pytest.param(
        Request(headers={}, parameters={}, body={}, url="", method="", remote=""),
        "",
        id="extract api url empty"
    ),
])
def test_extract_api_url(_request: Request, expected_result: str) -> str:
    """
    Test function extract_api_url
    """
    assert expected_result == extract_api_url(_request)


FAKE_X_REAL_IP = "X-Real-IP"
FAKE_X_FORWARDED_FOR = "X-Forwarded-For"
FAKE_REMOTE = "Remote"

@pytest.mark.parametrize(
    "_request, expected_result", [
        pytest.param(
            Request(
                headers={"X-Real-IP": FAKE_X_REAL_IP, "X-Forwarded-For": FAKE_X_FORWARDED_FOR},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            FAKE_X_REAL_IP,
            id="extract user IP from X-Real-IP"
        ),
        pytest.param(
            Request(
                headers={"X-Forwarded-For": FAKE_X_FORWARDED_FOR},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            FAKE_X_FORWARDED_FOR,
            id="extract user IP from X-Forwarded-For"
        ),
        pytest.param(
            Request(headers={}, parameters={}, body={}, url="", method="", remote=FAKE_REMOTE),
            FAKE_REMOTE,
            id="extract user IP from remote"
        ),
        pytest.param(
            Request(headers={}, parameters={}, body={}, url="", method="", remote=""),
            "",
            id="empty string for user IP"
        ),
        pytest.param(
            Request(headers={}, parameters={}, body={}, url="", method="", remote=None),
            None,
            id="none type for user IP"
        ),
    ]
)
def test_extract_user_ip(_request: Request, expected_result: str):
    """
    Test function extract_user_ip
    """
    assert expected_result == extract_user_ip(_request)


@pytest.mark.parametrize(
    "_request, expected_result", [
        pytest.param(
            Request(
                headers={"User-Agent": "axios/1.6.5"},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            [
                ('axios', Version('1.6.5')),
            ],
            id="extract simple user agent"
        ),
        pytest.param(
            Request(
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            [
                ('Mozilla', Version('5.0')),
                ('AppleWebKit', Version('537.36')),
                ('Chrome', Version('91.0.4472.124')),
                ('Safari', Version('537.36'))
            ],
            id="extract real complex user agent"
        ),
        pytest.param(
            Request(
                headers={
                    "User-Agent": "product/version prod_uct/5.0 (comment) prod.uct/537.36 "
                                  "(comment) prod-uct/91.0.4472.124 (comment) prod_.-uct/1.2 (comment)"},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            [
                # product/version is not expected because processing version will raise InvalidVersion
                ('prod_uct', Version('5.0')),
                ('prod.uct', Version('537.36')),
                ('prod-uct', Version('91.0.4472.124')),
                ('prod_.-uct', Version('1.2 '))
            ],
            id="extract fake complex user agent"
        ),
        pytest.param(
            Request(
                headers={"User-Agent": ""},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            [],
            id="extract empty user agent"
        ),
        pytest.param(
            Request(
                headers={"User-Agent": "Mozilla/5.truc"},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            [],
            id="extract user agent failed, invalid version"
        ),
        pytest.param(
            Request(
                headers={},
                parameters={}, body={}, url="", method="", remote=FAKE_REMOTE
            ),
            [],
            id="extract user agent failed, header missing"
        ),
    ]
)
def test_extract_user_agent(_request: Request, expected_result: list):
    """
    Test function extract_user_agent
    """
    assert expected_result == extract_user_agent(_request)
