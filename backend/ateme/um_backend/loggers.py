"""
Loggers utils
"""
import os
import logging

from ateme.log import (
    CustomFormatter,
    ActivityFormatter,
    get_activity_log
)
from ateme.openapi import (
    Response,
    HTTPException, Request
)

LOGLEVEL_CHOICES = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

# Logger for the application
LOGGER_NAME = 'um_backend'
LOG = logging.getLogger(LOGGER_NAME)
LOG.setLevel(os.getenv('LOGLEVEL', LOGLEVEL_CHOICES[3]))
formatter = CustomFormatter.build_default()
stderr_handler = logging.StreamHandler()
stderr_handler.setFormatter(formatter)
LOG.addHandler(stderr_handler)

LOG_ACTIVITY = logging.getLogger('user_activity')
LOG_ACTIVITY.setLevel(os.getenv('LOGLEVEL', LOGLEVEL_CHOICES[3]))
formatter = ActivityFormatter.build_default()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
LOG_ACTIVITY.addHandler(handler)


def show_activity_log(level: int, instance: Response | HTTPException, extra: dict):
    """ Show the `activity_msg` property from the instance when available.

    Args:
        level (int): log level
        instance (Response | HTTPException): instance to log
        extra (dict): extra information
    """
    activity_metadata = get_activity_log(instance)
    if activity_metadata:
        _message = activity_metadata.message
        # `instance_extra` MUST override `extra`
        _extra = extra | activity_metadata.extra
        _user = _extra.get("user", "-")
        LOG_ACTIVITY.log(level, "%s %s", _user, _message, extra=_extra)

def generate_audit_log_for_user_update(request: Request) -> dict[str, str]:
    """
    Generate audit log messages from user update request
    Args:
        request: Request
    Returns:
        success_message, failure_message as dict
    """
    username = request.parameters.get('username')
    idp_name = request.parameters.get('idp_name')
    body = request.body
    extra = ""
    extra_list: list = []
    if body:
        if "session_timeout_disabled" in body:
            extra_list.append(f"with disable session timeout set to {body.get('session_timeout_disabled')}")
        if "password_expiration_disabled" in body:
            extra_list.append("with password expiration "
                              f"{'disabled' if body.get('password_expiration_disabled') else 'enabled'}")
        if "scopes" in body:
            extra_list.append(f"adding scopes {', '.join(body['scopes'])}")
        if "password" in body:
            extra_list.append("resetting the password")
        if "first_login" in body and body["first_login"]:
            extra_list.append("forcing to change the password")
    if extra_list:
        extra = ", ".join(extra_list)
    success_message = f"updated user {username}:{idp_name} {extra}".strip()
    failure_message = f"failed to update user {username}:{idp_name}"
    return {"success_message": success_message, "failure_message": failure_message}

def generate_audit_log_for_scope_update(request: Request) -> dict[str, str]:
    """
    Generate audit log messages from scope update request
    Args:
        request: Request
    Returns:
        success_message, failure_message as dict
    """
    scope_id = request.parameters.get('id')
    body = request.body
    scopes_actions: list = []
    extra = ""
    if body and "content" in body:
        for item in body["content"]:
            item_log = ""
            if "action" in item:
                item_log = f"action {item['action']}"
            elif "scope" in item:
                item_log = f"scope {item['scope']}"
            if item_log:
                scopes_actions.append(item_log)
    if scopes_actions:
        extra = f", adding {', '.join(scopes_actions)}"
    success_message = f"updated scope {scope_id}{extra}"
    failure_message = f"failed to update scope {scope_id}"
    return {"success_message": success_message, "failure_message": failure_message}

def generate_audit_log_for_idp_config_update(request: Request) -> dict[str, str]:
    """
    Generate audit log messages from idp config update request
    Args:
        request: Request
    Returns:
        success_message, failure_message as dict
    """
    body = request.body
    idp_name = request.parameters.get('idp_name')
    extra_list: list = []
    extra = ""
    mappers: list = []

    if "scopes" in body and len(body["scopes"]) > 0:
        extra_list.append(f"to add default roles with roles {', '.join(body['scopes'])}")
    if "deny_access" in body:
        extra_list.append(f"to {'deny' if body['deny_access'] else 'allow'} access")
    if "mappers" in body and len(body["mappers"]) > 0:
        for mapper in body["mappers"]:
            id = mapper.get("id", "unknown_id")
            mappers.append(f"{mapper['type']}/{id}")
        extra_list.append(f"with mappers {', '.join(mappers)}")

    if extra_list:
        extra = f", set default behavior {', '.join(extra_list)}"
    success_message = f"updated idp configuration {idp_name}{extra}"
    failure_message = f"failed to update idp configuration {idp_name}"

    return {"success_message": success_message, "failure_message": failure_message}
