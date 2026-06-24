"""
Utils for um and its client
"""
import re
from datetime import datetime, UTC
from typing import List, Tuple, Union, Optional

import certifi
from pymongo import AsyncMongoClient
from ateme.openapi import OpenApiDefinition

from ateme.um_backend.types import (
    DefaultScopes,
    Scope,
    Action,
    Request,
    RequestMethod,
    ApiDescriptor,
    AuthDataDescriptor
)
from .loggers import LOG


DEFAULT_API_DESCRIPTORS_KEY = "api_descriptors"
DEFAULT_SCOPES_KEY = "scopes"
DEFAULT_ACTIONS_KEY = "actions"


def build_action_name_from_method_and_uri(method_name: str, uri: str) -> str:
    """
    This function is used to create an "action name" using
    the method_name and the uri from API definition

    Args:
        method_name: String representing a method (example: GET)
        uri: String representing an uri (example: /users/actions)
    Returns:
        a string build from method_name and uri
    Example:
        method_name = "GET"
        uri = "/users/}{id}/actions"
        return result: "get_users_id_actions"
    """
    method = method_name.lower()
    # remove curly braces used for path params
    uri = re.sub(r'[{}]', '', uri)
    # strip leading slash if present
    uri = uri.lstrip('/')
    # prefix with method
    base = f"{method}_{uri}"
    # replace remaining disallowed characters (other / or char like .) with "_",
    # allowed chars are defined in the `api/definitions/action.yaml` definition
    name = re.sub(r'[^a-zA-Z0-9_:]', '_', base)
    # lowercase for consistency
    name = name.lower()
    return name

def fill_scope_description(scope: Scope, definition: OpenApiDefinition):
    """[Fill scope description]

    Args:
        scope (Scope):
        definition (OpenApiDefinition):
    """
    # label and id are required for a creation, but not necessarily provided for an updating
    scope_name = None
    if scope.label and scope.id:
        # title is systematically auto generated
        scope_name = scope.id.split(':')[-1]
        scope.title = f"{scope_name.capitalize()} - {scope.label.lower()}"
        # default description
        if not scope.description:
            scope.description = f"Scope {scope_name} for {scope.label}"
    if definition.auth.scope_descriptions and \
            scope_name in definition.auth.scope_descriptions:
        # replace default description by the one filled in api.yaml
        scope.description = definition.auth.scope_descriptions[scope_name]


def generate_scopes_and_actions(api_definition: Optional[OpenApiDefinition] = None,  # pylint: disable=too-many-locals, too-many-branches
                                mainapp_prefix: str = "",
                                subapp_path: str = "",
                                app_name: str = "") -> Tuple[List[Scope], List[Action]]:
    # pylint: disable=too-many-locals
    """

    Generate scopes and actions from OpenApi definition.

    Disclaimer : mainapp_prefix and subapp_path need to be used both at a time to be able to generate
                 scopes and actions from a subapp definition

    :param api_definition:
    :param mainapp_prefix: corresponding to the main api definition prefix (ex: /usr)
    :param subapp_path: corresponding to the sub api definition prefix (ex: /sub)
    :param app_name: application name used to create scope
    :return:
    """
    if subapp_path and not mainapp_prefix or not subapp_path and mainapp_prefix:
        LOG.warning("Can't generate actions and scopes of a subapp with only %s, %s is needed too",
                    'subapp_path' if subapp_path else 'mainapp_prefix',
                    'mainapp_prefix' if subapp_path else 'subapp_path')
        return [], []
    actions = []
    scopes = {}
    for path_name, path in api_definition.paths.items():
        for method_name, method in path.methods.items():
            # Check if "operation_id" is present or not
            # If its present, we do nothing, else we rebuild it using method and path
            method_operation_id = method.operation_id
            if not method_operation_id:
                method_operation_id = build_action_name_from_method_and_uri(method_name=method_name,
                                                                            uri=path_name)
            # scopes/actions are not necessary if no scopes
            if not method.scopes and method_operation_id not in ['get_def', 'get_doc']:
                continue
            # summary property should be added in OpenAPI method class
            summary = method.method_object.get("summary")
            title = summary if summary else method_operation_id.replace('_', ' ').capitalize()
            prefix = api_definition.auth.prefix
            if app_name:
                prefix = f"{app_name}:{api_definition.auth.prefix}"
            description = method.method_object.get("description")
            if description is None:
                description = summary if summary else "Missing description ..."
            # action with the single scope usr:internal_administrator is flagged 'internal'
            usr_internal_action = (api_definition.auth.prefix == "usr" and len(method.scopes) == 1
                                   and method.scopes[0] == "internal_administrator")
            # get match children scope bool
            x_scope_match_children = method.method_object.get("x-scope-match-children", False)
            action = Action(name=method_operation_id,
                            label=api_definition.auth.label,
                            title=title,
                            request=Request(method=RequestMethod[method_name.upper()], route=path_name),
                            prefix=prefix,
                            description=description,
                            internal=usr_internal_action,
                            x_scope_match_children=x_scope_match_children)
            if subapp_path and mainapp_prefix:
                action.name = f"{api_definition.auth.prefix}:{action.name}"
                action.request.route = \
                    f"{subapp_path}{action.request.route if not action.request.route == '/' else ''}"
                action.prefix = mainapp_prefix
                if app_name:
                    action.prefix = f"{app_name}:{mainapp_prefix}"
            action.validate()
            actions.append(action)
            for scope in method.scopes:
                scope_content = {"action": f"{action.prefix}:{action.name}",
                                 "policy": "allow",
                                 "resource": {}}
                if scope in scopes:
                    scopes[scope].content.append(scope_content)
                else:
                    usr_internal_scope = (api_definition.auth.prefix == "usr" and
                                          scope in ["internal_administrator", "internal"])
                    scope_id = f"{api_definition.auth.prefix}:{scope}"
                    label = api_definition.auth.label
                    if app_name and 'internal' not in scope:
                        # Create a 3 levels scope
                        scope_id = f"{app_name}:{api_definition.auth.prefix}:{scope}"
                        label = f"{app_name} - {label}"

                    scopes[scope] = Scope(id=scope_id,
                                          label=label,
                                          content=[scope_content], default=True,
                                          internal=usr_internal_scope)
                    fill_scope_description(scopes[scope], api_definition)

                if app_name and 'internal' not in scope:
                    # Check the 2 levels scope to extend or create it
                    _scope_id = f"{app_name}:{scope}"
                    scope_content = {"scope": f"{app_name}:{api_definition.auth.prefix}:{scope}"}
                    # Create the 2 levels scope
                    scopes[_scope_id] = Scope(id=_scope_id,
                                              label=app_name,
                                              content=[scope_content], default=True,
                                              internal=usr_internal_scope)
                    fill_scope_description(scopes[_scope_id], api_definition)

    scopes_values = [*scopes.values()]
    for scope in scopes_values:
        scope.validate()
    return scopes_values, actions


def parse_scopes_and_actions(descriptor: ApiDescriptor,  # pylint: disable=too-many-locals
                             definition: OpenApiDefinition,
                             subapp_path: str = "",
                             main_def: Optional[Union[OpenApiDefinition, dict]] = None):
    """
    Parse an OpenApiDefintion to get scopes and actions in order to insert them in the ApiDescription

    :param descriptor:
    :param definition:
    :param subapp_path: optional arg to know if it is a subapp definition (ex: /credentials)
    :param main_def: main api definition
    :return:
    """
    # Generate scopes and actions from api file
    definition_scopes, definition_actions = generate_scopes_and_actions(
        api_definition=definition,
        mainapp_prefix=descriptor.prefix if subapp_path else "",
        subapp_path=subapp_path,
        app_name=descriptor.app_name)

    # Some definitions and scopes can have a subpath
    # The subpath is added to the scopes and definitons
    if subapp_path:
        descriptor.actions.extend(definition_actions)
        default_ids = []
        for scope in DefaultScopes:
            default_ids.append(
                f"{descriptor.app_name}:{definition.auth.prefix}:{scope.name}" if descriptor.app_name
                else f"{definition.auth.prefix}:{scope.name}")
        for definition_scope in definition_scopes:
            if definition_scope.id in default_ids:
                current_scope_processed = False
                for description_scope in descriptor.scopes:
                    desc_scope_name = description_scope.id.split(':')[-1]
                    def_scope_name = definition_scope.id.split(':')[-1]
                    if desc_scope_name == def_scope_name:
                        description_scope.content.extend(definition_scope.content)
                        current_scope_processed = True
                        break
                if current_scope_processed:
                    continue
                # The scope does not exist in the main api and should be added
                label_name = definition.auth.label
                if main_def:
                    if isinstance(main_def, OpenApiDefinition):
                        label_name = main_def.auth.label
                    else:
                        label_name = main_def['info']['x-auth']['label']
                scope_id = f"{descriptor.prefix}:{definition_scope.id.split(':')[-1]}"
                if descriptor.app_name and 'internal' not in def_scope_name:
                    scope_id = f"{descriptor.app_name}:{descriptor.prefix}:{def_scope_name}"
                new_scope = Scope(
                    id=scope_id,
                    label=label_name,
                    default=True,
                    internal=False,
                    content=definition_scope.content,
                    description=f"Scope {definition_scope.id.split(':')[-1]} for {label_name}"
                )
                descriptor.scopes.append(new_scope)
    else:
        descriptor.actions = definition_actions
        descriptor.scopes = definition_scopes


def create_async_pymongo_client(
        database_url: str,
        connect_timeout_ms: int = 1000,
        server_selection_timeout_ms: int = 5000,
        mongo_tls_cert_path: Optional[str] = None) -> AsyncMongoClient:
    """
    Create an asyncio PyMongo client for mongoDB

    Args:
        database_url (str): The database's url
        connect_timeout_ms (int): Connect Timeout..
        server_selection_timeout_ms (int): Server Selection Timeout..
        mongo_tls_cert_path (Optional[str]): Path where tls cert are located (as .pem file). Default to None.

    Returns:
        AsyncMongoClient
    """
    pymongo_async_client_args = {}
    if mongo_tls_cert_path:
        # The user wants to use certificates in order to authenticate,
        # certfile is provided
        pymongo_async_client_args['tls'] = True
        # If not provided, pymongo client will fail to validate certificates
        pymongo_async_client_args['tlsCAFile'] = certifi.where()
        pymongo_async_client_args['tlsCertificateKeyFile'] = mongo_tls_cert_path
    else:
        # The user decides to reach a local database that does not need to authenticate
        pymongo_async_client_args['tlsAllowInvalidCertificates'] = True
    # Create the client and return it
    client = AsyncMongoClient(
        database_url,
        connectTimeoutMS=connect_timeout_ms,
        serverSelectionTimeoutMS=server_selection_timeout_ms,
        **pymongo_async_client_args
    )
    return client


def compute_app_scopes(
    api_descriptors: List[ApiDescriptor|AuthDataDescriptor],
    scopes: List[Scope]
) -> tuple[bool, List[str]]:
    """
    Computes application-specific scope identifiers based on provided API descriptors and scopes.

    The function first checks if any of the API descriptors specify an application name.
    If so, it generates scope identifiers for each default scope associated with the application.
    If no application-specific scopes are found, it examines the provided scopes:
    - If a scope ID has three colon-separated parts, it is considered a level 3 scope.
    - If a scope ID has two colon-separated parts, it is considered an application scope.

    Returns:
        tuple[bool, List[str]]: A tuple where the first element is a boolean indicating
        whether we have to manage application scopes, and the second element is a list of
        the corresponding scope identifiers.
    """
    app_scopes_ids = set()

    # First, iterate over api_descriptors to get the app scopes
    for descriptor in api_descriptors:
        if descriptor.app_name:
            for default_scope in DefaultScopes:
                app_scopes_ids.add(f"{descriptor.app_name}:{default_scope.name}")
    if app_scopes_ids:
        return True, list(app_scopes_ids)

    # Else, iterate over the provided scopes
    lvl3_scopes_present = False
    for scope in scopes:
        id_splitted = scope.id.split(':')
        if len(id_splitted) == 3:
            lvl3_scopes_present = True
        elif len(id_splitted) == 2:
            app_scopes_ids.add(scope.id)
    if lvl3_scopes_present:
        return True, list(app_scopes_ids)

    return False, []


def utcnow() -> datetime:
    """

    As utcnow of `datetime.datetime` is readonly, it will be easier to mock to redefine this function here.

    Returns:
        datetime: UTC datetime
    """
    return datetime.now(UTC)
