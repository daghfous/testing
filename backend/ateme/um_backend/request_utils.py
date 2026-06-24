"""
Request utils
"""
import re
import base64
import binascii
from typing import Any, Final
from urllib.parse import urlparse
from multidict import MultiMapping, istr
from aiohttp import hdrs
from packaging.version import Version, InvalidVersion

from ateme.openapi import Request

from ateme.um_backend.exceptions import RequestExtractError
from ateme.um_backend.loggers import LOG


class HttpHeaders:  # pylint: disable=too-few-public-methods
    """ HttpHeaders class

    this class defines all required headers
    """
    # pylint: disable=too-few-public-methods
    AUTHORIZATION: Final[istr] = hdrs.AUTHORIZATION
    REFERER: Final[istr] = hdrs.REFERER
    SEC_WEBSOCKET_PROTOCOL: Final[istr] = hdrs.SEC_WEBSOCKET_PROTOCOL
    USER_AGENT: Final[istr] = hdrs.USER_AGENT
    X_ORIGINAL_URI: Final[istr] = istr("X-Original-URI")
    X_ORIGINAL_METHOD: Final[istr] = istr("X-Original-Method")
    X_REAL_IP: Final[istr] = istr("X-Real-IP")
    X_FORWARDED_FOR: Final[istr] = hdrs.X_FORWARDED_FOR
    X_API_URL_1: Final[istr] = istr("x-api-url")
    X_API_URL_2: Final[istr] = istr("X-api-url")
    X_USER: Final[istr] = istr("X-User")
    X_IDP_NAME: Final[istr] = istr("X-IDP-Name")

    @classmethod
    def values(cls) -> list[istr]:
        """ Retrieve only the constants (exclude private items and methods).

        Returns:
            list[istr]: list of constants
        """
        return [v for k, v in vars(cls).items() if not k.startswith("_") and isinstance(v, istr)]


def show_headers(request: Request):
    """ Filter on interesting headers and display them.

    Args:
        request (Request): request to process
    """
    headers = {
        header: value for header in HttpHeaders.values() if (value := request.headers.get(header))
    }
    LOG.debug(headers)


def extract_token(request: Request, introspection: bool=False) -> str:
    """ Extract token from the request.
    By default, the token extraction is only done in the `Authorization` request header.
    But during introspection, the token extraction need to support also:
    - the reverse-proxy UC which provides the token in the request body,
    - the web socket UC which provides the token in the `Sec-WebSocket-Protocol` request header.

    Args:
        request (Request): request to process
        introspection (bool, optional): introspection flag. Defaults to False.

    Raises:
        RequestExtractError, when the token can't be found in the request.
        RequestExtractError, when the token can't be decoded.

    Returns:
        str: token
    """
    headers: MultiMapping[str] = request.headers
    body: Any = request.body
    # basic and introspection UCs
    token_header: str | None = headers.get("Authorization")
    token_prefix: str = "Bearer "
    if token_header and token_header.startswith(token_prefix):
        return token_header.replace(token_prefix, "")
    if introspection:
        # reverse-proxy UC
        if isinstance(body, dict) and 'token' in body:
            return body['token'][0]
        # websocket UC
        ws_protocols_header: str | None = headers.get("Sec-WebSocket-Protocol")
        wb_protocol_token: str = "base64url.bearer.authorization."
        if ws_protocols_header and wb_protocol_token in ws_protocols_header:
            for protocol in ws_protocols_header.split(","):
                if not protocol.startswith(wb_protocol_token):
                    continue
                b64token: str = protocol.replace(wb_protocol_token, "")
                try:
                    return base64.b64decode(b64token).decode("utf-8")
                except (binascii.Error, ValueError, UnicodeError) as error:
                    # `base64.b64decode` may raise [binascii.Error | ValueError]
                    # `decode` may raise [UnicodeError]
                    raise RequestExtractError("Can't decode token") from error
    raise RequestExtractError("Can't find token in request")


def extract_uri_and_method(request: Request) -> tuple[str, str]:
    """ Extract uri and method from the request.

    Args:
        request (Request): request to process

    Returns:
        tuple[str, str]: uri and method
    """
    headers: MultiMapping[str] = request.headers
    body: Any = request.body
    if "X-Original-URI" in headers and "X-Original-Method" in headers:
        uri = headers["X-Original-URI"]
        method = headers["X-Original-Method"]
        return uri, method
    if isinstance(body, dict) and 'uri' in body and 'method' in body:
        # introspection use UC with reverse-proxy
        body_uri: list | str = body["uri"]
        uri = body_uri[0] if isinstance(body_uri, list) else body_uri
        body_method: list | str = body["method"]
        method = body_method[0] if isinstance(body_method, list) else body_method
        return uri, method
    raise RequestExtractError("Can't find uri and method in request")


def extract_api_url(request: Request) -> str:
    """ Extract api url from the request.

    Args:
        request (Request): request to process

    Returns:
        str: Api URL
    """
    headers: MultiMapping[str] = request.headers
    api_url = headers.get("x-api-url", "")
    if not api_url:
        api_url = headers.get("X-api-url", "")
    return api_url


def extract_user_ip(request: Request) -> str | None:
    """ Extract user IP from the request.

    Args:
        request (Request): request to process

    Returns:
        str | None: user IP or empty string or None
    """
    user_ip = request.headers.get("X-Real-IP")
    if not user_ip:
        user_ip = request.headers.get("X-Forwarded-For")
        if user_ip:
            # According https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For,
            # `X-Forwarded-For` is a comma-separated list of IP addresses. The first element in
            # this list is the client IP address and other elements are proxy servers.
            user_ip = user_ip.split(",")[0]
    if not user_ip:
        user_ip = request.remote
    return user_ip


def extract_user_agent_as_string(request: Request) -> str:
    """ Extract user agent from the request as string.

    Args:
        request (Request): request to process

    Returns:
        str: user agent as a raw string
    """
    headers: MultiMapping[str] = request.headers
    return headers.get("User-Agent", "")


def extract_user_agent(request: Request) -> list[tuple[str, Version]]:
    """ Extract user agent from the request as list of products.

    Args:
        request (Request): request to process

    Returns:
        list[tuple[str, Version]]: list of products with their names and versions
    """
    result = []
    # Format: <product>/<product-version> <comment>
    data = re.findall(r"([\w.-]+)/([\w.-]+)", extract_user_agent_as_string(request))
    for _product, _version in data:
        try:
            result.append((_product, Version(_version)))
        except InvalidVersion:
            # skip the data if the version is invalid
            pass
    return result

def extract_username_and_idpname(request: Request) -> tuple[str | None, str | None]:
    """ Extract username and idp_name from the request.

    Args:
        request (Request): request to process

    Returns:
        tuple[str | None, str | None]: Return username and idp_name from headers
    """
    headers: MultiMapping[str] = request.headers
    return headers.get(HttpHeaders.X_USER), headers.get(HttpHeaders.X_IDP_NAME)


def extract_activity_extra_data(request: Request) -> dict:
    """ Extract the activity extra data from request

    Args:
        request (Request): request to process

    Returns:
        dict: activity extra data
    """
    username, idp_name = extract_username_and_idpname(request)
    remote = extract_user_ip(request)
    referer = request.headers.get(HttpHeaders.REFERER)
    extra = {
        "clientip": remote,
        "user": username + ":" + idp_name if username and idp_name else "-",
        "funcname": request.operation_id,
        "url": f"{urlparse(referer).path}{request.url.raw_path}",
        "method": request.method
    }
    return extra
