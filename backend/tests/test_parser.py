"""
Test file for CustomArgsParser
"""
import os
import argparse
from contextlib import nullcontext as does_not_raise
import pytest

from ateme.um_backend.parser import CustomArgsParser, boolean_checker


@pytest.mark.parametrize("required, arg_value, env, default_value, type_value, context, expected_result", [
    # UC: NON-REQUIRED argument with all empty, return None without CLI error
    (False, None, {}, None, None, does_not_raise(), None),
    # UC: REQUIRED argument with all empty, CLI error MUST occur
    (True, None, {}, None, None, pytest.raises(SystemExit), None),
    # UC: NON-REQUIRED argument with a known env but empty, return None without CLI error
    (False, None, {"name": "FAKE_ENV"}, None, None,does_not_raise(), None),
    # UC: REQUIRED argument with a known env but empty, CLI error MUST occur
    (True, None, {"name": "FAKE_ENV"}, None, None, pytest.raises(SystemExit), None),
    # UC: NON-REQUIRED argument with a env fully set, env value MUST be returned
    (False, None, {"name": "FAKE_ENV", "value": "10"}, None, int, does_not_raise(), 10),
    # UC: REQUIRED argument with a env fully set, env value MUST be returned
    (True, None, {"name": "FAKE_ENV", "value": "10"}, None, int, does_not_raise(), 10),
    # UC: NON-REQUIRED argument with default set, default value MUST be returned
    (False, None, {}, 0.5, int, does_not_raise(), 0.5),
    # UC: REQUIRED argument with default set, default value MUST be returned
    (True, None, {}, 0.5, int, does_not_raise(), 0.5),
    # UC: NON-REQUIRED argument with env and default, env is more important than default, so env value MUST be returned
    (False, None, {"name": "FAKE_ENV", "value": "10"}, 0.5, int, does_not_raise(), 10),
    # UC: REQUIRED argument with env and default, env is more important than default, so env value MUST be returned
    (True, None, {"name": "FAKE_ENV", "value": "10"}, 0.5, int, does_not_raise(), 10),
    # UC: NON-REQUIRED argument with arg provided, arg is the most important, so arg value MUST be returned
    (False, "arg_value", {"name": "FAKE_ENV", "value": "10"}, 0.5, str,  does_not_raise(), "arg_value"),
    # UC: REQUIRED argument with arg provided, arg is the most important, so arg value MUST be returned
    (True, "arg_value", {"name": "FAKE_ENV", "value": "10"}, 0.5, str, does_not_raise(), "arg_value"),
    # UC: if bool type, then bool should be casted and returned
    (True, None, {"name": "FAKE_ENV", "value": "false"}, True, bool, does_not_raise(), False),
    # UC: if bool type, then bool should be casted and returned
    (True, None, {"name": "FAKE_ENV", "value": "true"}, False, bool, does_not_raise(), True)
])
def test_parser_argument(mocker, required, arg_value, env, default_value, type_value, context, expected_result): # pylint: disable=too-many-arguments, too-many-locals
    """ test_parser_argument
    """
    # pylint: disable=too-many-positional-arguments
    arg_name = "--argument"
    arg_help = "Help message."
    expected_help_message = ""
    opts = {"required": required, "type": type_value}
    if type_value is bool:
        opts["type"] = boolean_checker

    if required:
        expected_help_message = "REQUIRED. " + arg_help
    else:
        expected_help_message = arg_help

    if default_value is not None:
        opts["default"] = default_value
        expected_help_message += f" Default to `{default_value}`."

    if "name" in env:
        env_name = env["name"]
        opts["env_name"] = env_name
        expected_help_message += f" Otherwise use the env `{env_name} (undefined)`."

        if "value" in env:
            assert env["value"] is not None
            env_value = env["value"]

            mocker.patch.dict(os.environ, {env_name: str(env_value)})
            if opts["type"] is boolean_checker and env_value is not None:
                env_value = str(env_value).capitalize()
            expected_help_message = expected_help_message.replace("(undefined)", f"({env_value})")

    parser = CustomArgsParser(prog="test", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_custom_argument(arg_name, help=arg_help, **opts)
    assert expected_help_message in parser.format_help()
    with context:
        args = parser.parse_args([arg_name, arg_value] if arg_value else [])
        assert args.argument == expected_result
