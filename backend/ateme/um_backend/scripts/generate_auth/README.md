# [generate_auth](generate_auth.py)

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [main usages](#main-usages)
- [authloader usages](#authloader-usages)
- [umbackend usages](#umbackend-usages)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## main usages

This script generates the User Management authorizations relative to some OpenAPI definitions.

It is based on 2 sub-commands: `authloader` and `umbackend`.

Usages:
```
usage: generate_auth [-h] {authloader,umbackend} ...

positional arguments:
  {authloader,umbackend}
    authloader          Sub-command to generate auth data for UM Authloader
    umbackend           sub-command to generate auth data for UM Backend

options:
  -h, --help            show this help message and exit
```

## authloader usages

The `authloader` sub-command is **RECOMMENDED** for applications which will be deployed with PILOT FOUNDATION MANAGER (PMF).

In this use-case, the application auth data are based on configmaps with specifics labels/annotations. More details [here](../../../../../docs/load_auth_data.md#load-auth-data-from-configmap).

This sub-command generates the auth data (api_descriptors, actions and scopes) to put in a configmap.

> **CAUTION** it does not generate the full configmap with the required labels/annotations.

The required arguments are:
- the list of OpenApi 3.0 definitions,
- the corresponding list of Kubernetes services for each definition (**definition order must be kept**).

The application name pattern is not required BUT recommended (set your release name template).

Others arguments are optional.

The result is a YAML file or a YAML raw data in stdout.

Usages:
```
usage: generate_auth authloader [-h] --definition-filepath DEFINITION_FILEPATH --upstream-url UPSTREAM_URL [--output-dir OUTPUT_DIR] [--output-filename OUTPUT_FILENAME]
                                [--app-name-pattern APP_NAME_PATTERN] [--add-app-level-scopes]

options:
  -h, --help            show this help message and exit
  --definition-filepath DEFINITION_FILEPATH
                        REQUIRED Path to an OpenAPI definition, repeat this argument for each OpenAPI definition to parse
  --upstream-url UPSTREAM_URL
                        REQUIRED Upstream URL where the OpenAPI definition is located on the application (one per definition)
  --output-dir OUTPUT_DIR
                        OPTIONAL Output directory where the result file will be written (when not set, stdout is used)
  --output-filename OUTPUT_FILENAME
                        OPTIONAL Output filename without the extension (extension depends on --output-format argument)
  --app-name-pattern APP_NAME_PATTERN
                        OPTIONAL Custom Helm pattern to manage the application name
  --add-app-level-scopes
                        OPTIONAL|NOT RECOMMENDED Add the app level scopes only if `--app-name-pattern` is set (`false` by default)
```

Command example:
```
generate_auth authloader \
  --definition-filepath <path>/api_1.yaml \
  --upstream-url 'http://{{ .Release.Name }}-<api_1>.{{ .Release.Namespace }}.svc.cluster.local:<port>' \
  --definition-filepath <path>/api_2.yaml \
  --upstream-url 'http://{{ .Release.Name }}-<api_2>.{{ .Release.Namespace }}.svc.cluster.local:<port>' \
  --app-name-pattern '{{ .Release.Name }}'
```

Result example:
```yaml
api_descriptors.json: |
  [
    {
        # api_descriptor_1 formatted as expected by UM
    },
    ...
    {
        # api_descriptor_N formatted as expected by UM
    }
  ]
scopes.json: |
  [
    {
        # scope_1 formatted as expected by UM
    },
    ...
    {
        # scope_N formatted as expected by UM
    }
  ]
actions.json: |
  [
    {
        # action_1 formatted as expected by UM
    },
    ...
    {
        # action_N formatted as expected by UM
    }
  ]
```

Other examples are available in [here](../../../../tests/scripts/generate_auth/references/).


## umbackend usages

The `umbackend` sub-command is **RECOMMENDED** for applications which won't be deployed with PILOT FOUNDATION MANAGER (PMF).

In this use-case, the User-Management module is integrated in the application. More details [here](../../../../../docs/load_auth_data.md#load-default-scopes-actions-and-admin).

This sub-command generates the auth data (api_descriptors, actions and scopes) to put in a YAML or JSON file.

This file must provided via an argument when the User-Managemet is launched to load these auth data.

The required arguments are:
- the list of OpenApi 3.0 definitions,
- the corresponding list of local services for each definition (**definition order must be kept**).

Others arguments are optional.

The result is a JSON file or a JSON raw data in stdout.

Usages:
```
usage: generate_auth umbackend [-h] --definition-filepath DEFINITION_FILEPATH --upstream-url UPSTREAM_URL [--output-dir OUTPUT_DIR] [--output-filename OUTPUT_FILENAME]

options:
  -h, --help            show this help message and exit
  --definition-filepath DEFINITION_FILEPATH
                        REQUIRED Path to an OpenAPI definition, repeat this argument for each OpenAPI definition to parse
  --upstream-url UPSTREAM_URL
                        REQUIRED Upstream URL where the OpenAPI definition is located on the application (one per definition)
  --output-dir OUTPUT_DIR
                        Output directory where the result file will be written (when not set, stdout is used)
  --output-filename OUTPUT_FILENAME
                        Output filename without the extension (extension depends on --output-format argument)
```

Command example:
```
generate_auth umbackend \
  --definition-filepath <path>/api_1.yaml \
  --upstream-url 'http://localhost:<port_1>' \
  --definition-filepath <path>/api_2.yaml \
  --upstream-url 'http://localhost:<port_2>'
```

Result example:
```yaml
api_descriptors: |
  [
    {
        # api_descriptor_1 formatted as expected by UM
    },
    ...
    {
        # api_descriptor_N formatted as expected by UM
    }
  ]
scopes: |
  [
    {
        # scope_1 formatted as expected by UM
    },
    ...
    {
        # scope_N formatted as expected by UM
    }
  ]
actions: |
  [
    {
        # action_1 formatted as expected by UM
    },
    ...
    {
        # action_N formatted as expected by UM
    }
  ]
```

Other examples are available in [here](../../../../tests/scripts/generate_auth/references/).
