"""
Custom parser args
"""
import os
import argparse
from typing import Any


def int_checker(min_value: int, max_value: int) -> int:
    """
    Return function handle of an argument type function for
    ArgumentParser checking a float range: min_value <= arg <= max_value
        min_value - minimum acceptable argument
        max_value - maximum acceptable argument
    """
    def range_limited_checker(arg: str) -> int:
        """ Type function for argparse - a int within predefined bounds
        to use for arguments
        """
        arg = int(arg)
        if arg < min_value or arg > max_value:
            raise argparse.ArgumentTypeError("Argument must be between " + str(min_value) +
                                             " and " + str(max_value))
        return arg

    return range_limited_checker


def boolean_checker(arg: str) -> bool | None:
    """Check which boolean to return if specified
    """
    if arg in ("false", "False"):
        return False
    if arg in ("true", "True"):
        return True
    return None


class CustomArgsParser(argparse.ArgumentParser):
    """ CustomArgsParser
    """

    def add_custom_argument(
        self,
        name: str,
        env_name: str | None = None,
        **kwargs
    ):
        """ Overload `ArgumentParser.add_argument` to manage help message, required flag
        and default value according to env settings.

        Args:
            name (str): argument name
            env_name (str | None, optional): env name to drive the default value. Defaults to None.
        """
        arg_opts = {}
        env_value: Any = None
        default_set: bool = "default" in kwargs
        default_value: Any = kwargs.get("default")

        # Retrieve and cast the env value to the expected type
        if env_name and env_name in os.environ:
            _type = kwargs.get("type", str)
            env_value = _type(os.environ[env_name])

        # Compute default value (first from env then default)
        if env_value is not None or default_set:
            arg_opts["default"] = env_value if env_value is not None else default_value

        # Adjust the required flag because when a env_name is used or default set,
        # cli argument can be empty and no more required.
        if (env_value or default_set) and "required" in kwargs:
            arg_opts["required"] = False

        # Compute the help message
        help_message = ""
        if "required" in kwargs and kwargs["required"]:
            help_message += "REQUIRED. "
        help_message += kwargs["help"]
        if default_set:
            help_message += f" Default to `{default_value}`."
        if env_name:
            _value = env_value if env_value is not None else "undefined"
            help_message += f" Otherwise use the env `{env_name} ({_value})`."
        arg_opts["help"] = help_message

        # Overload kwargs with arg_opts
        kwargs |= arg_opts

        # Finally, call `add_argument` method
        self.add_argument(name, **kwargs)
