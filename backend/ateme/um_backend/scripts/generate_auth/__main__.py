import os
from enum import Enum, auto
from dataclasses import dataclass

import yaml
import json
import argparse

from yaml.resolver import BaseResolver
from ateme.openapi import OpenApiDefinition
from ateme.um_backend import (
    ApiDescriptor,
    parse_scopes_and_actions,
    Scope,
    DEFAULT_API_DESCRIPTORS_KEY,
    DEFAULT_SCOPES_KEY,
    DEFAULT_ACTIONS_KEY,
    DefaultScopes
)


PATTERN_TO_REPLACE = "patterntoreplace"


# Custom code to manager "|" in YAML file
#
class AsLiteral(str):
    pass


def represent_literal(dumper, data):
    return dumper.represent_scalar(BaseResolver.DEFAULT_SCALAR_TAG, data, style="|")


yaml.add_representer(AsLiteral, represent_literal)


OUTPUT_FORMATTER = {
    "json": [
        (lambda d: d),
        (lambda d: json.dumps(d, indent=2))
    ],
    "yaml": [
        (lambda d: AsLiteral(json.dumps(d, indent=2))),
        (lambda d: yaml.dump(d, indent=2))
    ]
}
OUTPUT_FORMATTER_VALUES = list(OUTPUT_FORMATTER.keys())
OUTPUT_FORMATTER_DEFAULT = OUTPUT_FORMATTER_VALUES[1]


@dataclass
class InputConfig:
    """ InputConfig class
    """
    definition_filepath_list: list
    upstream_url_list: list
    app_name_pattern: str | None
    add_app_level_scopes: bool
    key_api_descriptors: str
    key_actions: str
    key_scopes: str
    output_format: str
    output_dir: str | None
    output_filename: str

    def __post_init__(self):
        """ __post_init__ to check some inputs
        """
        assert len(self.definition_filepath_list) == len(self.upstream_url_list), "definition_list and upstream_list must have the same length"
        if self.add_app_level_scopes:
            assert self.app_name_pattern and self.add_app_level_scopes, "add_app_level_scopes must be set only if app_name_pattern is set"


def compute_authdata(config: InputConfig):
    api_descriptors = []
    actions = []
    scopes = []
    app_scopes = {}

    if config.app_name_pattern:
        # Init app_scopes when required
        for default_scope in DefaultScopes:
            app_scopes[f"{PATTERN_TO_REPLACE}:{default_scope.name}"] = None

    for index, definition_filepath in enumerate(config.definition_filepath_list):
        definition = OpenApiDefinition(definition_filepath)
        base_api_descriptor_args = {
            'prefix': definition.auth.prefix,
            'url': config.upstream_url_list[index]
        }
        additional_api_descriptor_args = {}
        if config.app_name_pattern:
            additional_api_descriptor_args['app_name'] = PATTERN_TO_REPLACE
        api_descriptor_args = {**base_api_descriptor_args, **additional_api_descriptor_args}
        api_descriptor = ApiDescriptor(**api_descriptor_args)
        parse_scopes_and_actions(api_descriptor, definition)

        # Append api_descriptor
        api_descriptors.append(api_descriptor_args)

        # Append actions
        for action in api_descriptor.actions:
            actions.append(dict(action.to_dict()))

        # Append scopes
        for scope in api_descriptor.scopes:
            if not config.add_app_level_scopes:
                # Append scope except if it is a app scope
                if scope.id in app_scopes.keys():
                    continue
                scopes.append(dict(scope.to_dict()))
                continue
            # Manage the app scopes
            if scope.id not in app_scopes.keys():
                # Basic scopes can be directly append
                scopes.append(dict(scope.to_dict()))
                continue
            # App scope must be re-created and mutualize between all definitions
            app_scope: Scope | None = app_scopes[scope.id]
            if app_scope:
                # the scope already exists, update the content
                app_scope.content += scope.content
            else:
                scope_name = scope.id.split(":")[1]
                # the scope does not exists, append it
                # (see function `fill_scope_description` to compute title and description fields)
                app_scopes[scope.id] = Scope(
                    id=scope.id,
                    label=scope.label,
                    title=f"{scope_name.capitalize()} - {scope.label.lower()}",
                    description=f"Scope {scope_name} for {scope.label}",
                    content=scope.content,
                    default=True,
                    internal=False
                )

    # Append the app scopes if exist
    scopes += [dict(app_scope.to_dict()) for app_scope in app_scopes.values() if app_scope]

    output_formatter = OUTPUT_FORMATTER[config.output_format]
    json_data = {
        config.key_api_descriptors: output_formatter[0](api_descriptors),
        config.key_actions: output_formatter[0](actions),
        config.key_scopes: output_formatter[0](scopes),
    }
    output_data = output_formatter[1](json_data)
    if config.app_name_pattern:
        output_data = output_data.replace(PATTERN_TO_REPLACE, config.app_name_pattern)
    file_name = f"{config.output_filename}.{config.output_format}"
    if config.output_dir:
        with open(os.path.join(config.output_dir, file_name), "w") as _file:
            _file.write(output_data)
    else:
        print(output_data)


def do_authloader_data(args: argparse.Namespace):
    """This mode is RECOMMENDED for Micro-Services application to create a file with auth data
    which will be loaded by the UM Authloader.

    Args:
        args (argparse.Namespace): arguments for authloader mode.
    """
    config = InputConfig(
        definition_filepath_list=list(dict.fromkeys(args.definition_filepath)),
        upstream_url_list=list(dict.fromkeys(args.upstream_url)),
        app_name_pattern=args.app_name_pattern,
        add_app_level_scopes=args.add_app_level_scopes,
        key_api_descriptors=DEFAULT_API_DESCRIPTORS_KEY + ".json",
        key_actions=DEFAULT_ACTIONS_KEY + ".json",
        key_scopes=DEFAULT_SCOPES_KEY + ".json",
        output_format="yaml",
        output_dir=args.output_dir,
        output_filename=args.output_filename
    )
    compute_authdata(config)


def do_umbackend_data(args: argparse.Namespace):
    """This mode is RECOMMENDED for appliance mode to create a file with auth data
    which will be loaded by the UM Backend.

    Args:
        args (argparse.Namespace): arguments for umbackend mode.
    """
    config = InputConfig(
        definition_filepath_list=list(dict.fromkeys(args.definition_filepath)),
        upstream_url_list=list(dict.fromkeys(args.upstream_url)),
        app_name_pattern=None,
        add_app_level_scopes=False,
        key_api_descriptors=DEFAULT_API_DESCRIPTORS_KEY,
        key_actions=DEFAULT_ACTIONS_KEY,
        key_scopes=DEFAULT_SCOPES_KEY,
        output_format="json",
        output_dir=args.output_dir,
        output_filename=args.output_filename
    )
    compute_authdata(config)


def main(input_args=None):
    """
    Main function
    """

    # Create a parent parser for all common arguments required for subparsers
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--definition-filepath",
        action='append',
        required=True,
        help="REQUIRED Path to an OpenAPI definition, repeat this argument for each OpenAPI definition to parse"
    )
    common_parser.add_argument(
        "--upstream-url",
        action='append',
        required=True,
        help="REQUIRED Upstream URL where the OpenAPI definition is located on the application (one per definition)"
    )
    common_parser.add_argument(
        "--output-dir",
        default="",
        help="OPTIONAL Output directory where the result file will be written (when not set, stdout is used)"
    )
    common_parser.add_argument(
        "--output-filename",
        default="result",
        help="OPTIONAL Output filename without the extension (extension depends on --output-format argument)"
    )

    # Create the main parser with its subparsers based on `parent_parser`
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers(required=True)
    authloader_subparser = subparsers.add_parser(
        "authloader",
        parents = [common_parser],
        help="Sub-command to generate auth data for UM Authloader"
    )
    authloader_subparser.add_argument(
        "--app-name-pattern",
        help="OPTIONAL Custom Helm pattern to manage the application name"
    )
    authloader_subparser.add_argument(
        "--add-app-level-scopes",
        action="store_true",
        help="OPTIONAL|NOT RECOMMENDED Add the app level scopes only if `--app-name-pattern` is set (`false` by default)"
    )
    authloader_subparser.set_defaults(function=do_authloader_data)

    umbackend_subparser = subparsers.add_parser(
        "umbackend",
        parents = [common_parser],
        help="sub-command to generate auth data for UM Backend"
    )
    umbackend_subparser.set_defaults(function=do_umbackend_data)

    args = main_parser.parse_args(input_args)
    args.function(args)


if __name__ == "__main__":
    main()
