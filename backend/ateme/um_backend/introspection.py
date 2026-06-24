"""
Introspection module
"""

import re
from typing import List
from yarl import URL
from aiohttp.web_urldispatcher import DynamicResource

from ateme.um_backend.exceptions import IntrospectionError
from ateme.um_backend.database import Database
from ateme.um_backend.types import Action


class UserDynamicResource(DynamicResource):
    """
    UserDynamicResource inherit from DynamicResource of aiohttp in order
    to re-use aiohttp pattern without load all definition routes.
    """

    def build_from_url(self, url: str) -> dict:
        """ Build parameter dict from url.
        we have to parse url first in order to fetch query string
        and then retrieve path parameter.

        Args:
            url (str): url to parse

        Returns:
            dict: parameter dict
        """
        _parsed_url = URL(url)
        _match_info: dict = {}
        _match_info.update(_parsed_url.query)
        _match_info.update(self._match(_parsed_url.path) or {})
        return _match_info


def _generate_url_pattern(uri: str, x_scope_match_children: bool = False) -> str:
    """Generate url pattern from uri.
    When uri is root, return pattern to handle root endpoint `/`.
    When uri is not root and x_scope_match_children disabled, return pattern to handle `/{uri}`.
    When uri is not root and x_scope_match_children enabled, return pattern to handle `/{uri}` and `/{uri}/*`.

    Args:
        uri (str): uri to use in pattern
        x_scope_match_children (bool, optional): flag to take account the children matching. Defaults to False.

    Returns:
        str: URL pattern
    """
    if uri == "/":
        # to handle root endpoint on user request "/"
        url_pattern = r"/*(\?.*)?$"
    else:
        # If we need to match the children of the parent endpoint then
        # the regex needs to be able to detect the parent and also his children
        # else we use the usual regex
        url_pattern = rf"{uri}([/?].*)?$" if x_scope_match_children else rf"{uri}(\?.*)?$"
    return url_pattern


def _is_scope_to_process(scope_id: str, prefix: str, app_name: str | None, non_default_scope_ids: List[str]) -> bool:
    """Check if the scope_id is relative to the couple (prefix, app_name, non_default_scope_ids).
    REMINDER:
    - Level 1. [all]:<scope_name>
    - Level 2. [app_name|prefix]:<scope_name>
    - Level 3. [app_name]:[prefix]:<scope_name>

    Args:
        scope_id (str): scope id to check against prefix and app_name
        prefix (str): prefix
        app_name (str | None): app name
        non_default_scope_ids (List[str]): list of non default scope ids

    Returns:
        bool: False if the scope must be skipped, else True.
    """
    scope_id_splitted = scope_id.split(":")
    if scope_id_splitted[0] == "all":
        # hat default scope
        return True
    if scope_id_splitted[0] == prefix and len(scope_id_splitted) == 2:
        # base default scope
        return True
    if scope_id_splitted[0] == app_name:
        # hat default application scope
        if len(scope_id_splitted) == 2:
            return True
        if scope_id_splitted[1] == prefix:
            # base default application scope
            return True
    if scope_id in non_default_scope_ids:
        # CAUTION: custom scopes can be created by user and their scope id are not prefixed as expected.
        # So, we need to process them without filtering.
        return True
    # Skip the scope
    return False


def _is_action_allowed(scope_action: str, requested_action: Action) -> bool:
    """
    Check if the requested action is allowed by scope.

    Args:
        scope_action (str): action authorized by the scope
        requested_action (Action): action requested by user
    Returns:
        bool: `True` whether the action is allowed, else `False`
    """
    if scope_action == f"{requested_action.prefix}:{requested_action.name}":
        return True
    if scope_action == f"{requested_action.prefix}:*":
        return True
    if scope_action == f"*:{requested_action.name}":
        return True
    # Handle case for products that includes their prefix in action
    # For example, lcs:import_full_configuration
    splitted_action = requested_action.name.split(":")
    if len(splitted_action) > 1 and scope_action == f"*:{splitted_action[-1]}":
        return True
    return False


class Introspector:
    """Introspector class"""

    # pylint: disable=too-few-public-methods
    def __init__(self, database: Database):
        """Init

        Args:
            database (Database): database instance
        """
        self._db = database
        self._param_regex = re.compile(r"{(\w+)}")

    async def check_introspection(self, user_dict: dict, uri: str, method: str, api_url: str):
        """Check whether a user is allowed to access an endpoint defined by (`uri`, `method`, `api_url`).
        Based on `user_id`, retrieve the user scopes from database.
        Based on `api_url`, retrieve the couple (prefix, app_name) from api descriptors.
        Based on (`uri`, `method`, `prefix`, `app_name`), identify the action if it exists.
        Based on (`prefix`, `app_name`), computes the allowed user actions from the concerned user scopes.
        Then, check if the action is one of user actions.

        Args:
            user_id (str): user id
            uri (str): action uri
            method (str): action method
            api_url (str): api url relative to the action

        Raises:
            IntrospectionError:
                - if user has no scopes
                - if action is not found
                - if user has no action
                - if action is not allowed

        Returns:
            str: username
        """
        # Get the user scopes
        user_scopes: List[str] | None = user_dict.get("scopes")
        if not user_scopes:
            raise IntrospectionError("Operation not authorized")

        # Identify the api descriptor concerned by the request.
        # CAUTION: `api_url` header is present when the introspection request comes from a reverse-proxy or ingress.
        # However, some applications (like PMS) can call the introspection endpoint (without `api_url` headers).
        # TODO add api_descriptor for UM
        app_name: str | None = None
        prefix: str = "usr"
        if api_url:
            api_desc = await self._db.collection_api_descriptors.get_by_url(api_url)
            if api_desc:
                app_name = api_desc.app_name
                prefix = api_desc.prefix

        # Identify the action relative to (uri, method, prefix, app_name)
        action: Action | None = await self._resolve_action(uri, method, prefix, app_name)
        if not action:
            raise IntrospectionError(
                f"Can't find action uri: {uri}, method: {method}, prefix: {prefix}, app_name: {app_name}"
            )

        # Compute the user actions relative to its scopes by filtering on (app_name, prefix)
        content_actions: List[dict] = await self._get_content_actions_from_scopes(user_scopes, prefix, app_name)
        if len(content_actions) == 0:
            raise IntrospectionError(f"No action for user: {user_dict['username']}")

        # Check action according to the content_actions computed from user scopes
        result = self._check_action(action, content_actions, uri)
        if not result:
            raise IntrospectionError("action not allowed according to user scopes")

    async def _resolve_action(self, uri: str, method: str, prefix: str, app_name: str | None) -> Action | None:
        """Resolve action from request

        Args:
            uri (str): request uri
            method (str): request method
            prefix (str): api prefix
            app_name (str | None): product name if it exists.

        Returns:
            Action | None: return the matched action, or None.
        """
        # For action, when `app_name` is present, `action.prefix` is computed as `app_name:prefix` else `prefix`.
        action_prefix = f"{app_name}:{prefix}" if app_name else prefix
        uri_param = re.compile(r"{\w*}")
        actions = await self._db.collection_actions.get_list({"prefix": action_prefix, "request.method": method})
        for action in actions:
            # Replace {param} to valid uri regex
            # Param must match to any character except /, # and ?
            url_pattern = uri_param.sub("[^/#?]*", action.request.route)
            # In case of nginx reverse proxy, auth server receive uri with location uri,
            # url isn't rewrite before (ex: /api/ping)
            route_reg = re.compile(_generate_url_pattern(url_pattern, action.x_scope_match_children))
            # We must search instead of match because we need
            # to be more flexible on begin of url
            match = route_reg.search(uri)
            if match:
                return action
        # no action found
        return None

    async def _get_content_actions_from_scopes(
        self, scopes: List[str], prefix: str, app_name: str | None
    ) -> List[dict]:
        """Compute the content with all user actions from the concerned user scopes.
        Parse all user scopes, filter them according to the couple (prefix, app_name),
        then retrieve the actions to compute the content.

        Args:
            scopes (List[str]): list if user scope ids
            prefix (str): api prefix
            app_name (str | None): product name if it exists.

        Returns:
            List[dict]: _description_
        """

        async def _parse_scope(scope_id: str) -> List[dict]:
            """Recursive function to filter scopes according the couple (prefix, app_name)
            and retrieve the actions to fill the content.

            Args:
                scope_id (str): scope id to process

            Returns:
                List[dict]: content (list of actions)
            """
            content_actions: List[dict] = []
            # Check if scope_id has been already processed
            if scope_id in scopes_processed:
                return content_actions
            # Append scope_id to the processed scope list
            scopes_processed.append(scope_id)
            # Check if this scope must be analyzed, else skip it
            if not _is_scope_to_process(scope_id, prefix, app_name, non_default_scope_ids):
                return content_actions
            scope_dict = await self._db.collection_scopes.get_by_id(_id=scope_id, all_scopes=True)
            if not scope_dict:
                # CAUTION: AuthData management remove the default scopes BUT
                # don't clean the user scopes. So, it is possible to have
                # an obsolete `scope_id` in this list.
                return content_actions
            content: List[dict] = scope_dict.get("content", [])
            # Analyze the `db_scope` to
            for item in content:
                if "scope" in item and item["scope"]:
                    # item is a scope
                    _scope_id = item["scope"]
                    actions = await _parse_scope(_scope_id)
                    content_actions.extend(actions)
                else:
                    # item is an action
                    content_actions.append(item)
            return content_actions

        non_default_scope_ids = await self._db.collection_scopes.get_list_non_default_ids()
        scopes_processed: List[str] = []
        _content_actions: List[dict] = []
        for scope_id in scopes:
            actions = await _parse_scope(scope_id)
            _content_actions.extend(actions)
        return _content_actions

    # pylint: disable=too-many-locals
    def _check_action(self, action: Action, content_actions: List[dict], uri: str) -> bool:
        """
        Check if action is one of user content actions.

        Args:
            user_object: db user_object
            method: requested method
            uri: requested URI

        Returns:
            bool: `True` if action is found, else `False`.
        """
        # Token introspection case, we have to build parameters
        # Remove from url part that aren't define in endpoint url definition
        # For example /api/ping /api reverse proxy location, we have to
        # remove this part, because aiohttp DynamicResource use fullmatch
        first_param = self._param_regex.search(action.request.route)
        start_idx = uri.index(action.request.route[: first_param.start()] if first_param else action.request.route)
        uri_prefix = None
        if start_idx >= 0:
            uri_prefix = uri[:start_idx]
        # Init UserDynamicResource with route pattern
        # and build parameters dict from url
        udr = UserDynamicResource(action.request.route)
        if uri_prefix:
            udr.add_prefix(uri_prefix)
        parameters = udr.build_from_url(uri)
        # Extract parameters available sorted
        # assign value to parameter
        authorize_operation = False
        for item in content_actions:
            item_action: str | None = item.get("action")
            if item_action and _is_action_allowed(item_action, action):
                authorize_operation = True
                # Check the resource access according to the first uri parameter
                # Resource can be a string or an array
                item_resource = item.get("resource")
                if not item_resource:
                    # resource is not required
                    break
                for key, value in item_resource.items():
                    value = [value] if isinstance(value, str) else value
                    item_policy = item["policy"]
                    if item_policy == "allow" and "*" in value:
                        # every resource are allowed
                        break
                    if (item_policy == "deny" and (parameters.get(key) in value or "*" in value)) or (
                        item_policy == "allow" and parameters.get(key) not in value
                    ):
                        authorize_operation = False
                        break
        return authorize_operation
