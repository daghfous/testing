<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Script generate_um_export_from_pms.py](#script-generate_um_export_from_pmspy)
  - [Overview](#overview)
  - [Usages](#usages)
  - [Execution with 'tox' tool](#execution-with-tox-tool)
  - [Execution with Docker](#execution-with-docker)
  - [Compile script](#compile-script)
  - [Run test on compile version](#run-test-on-compile-version)
    - [Requirements:](#requirements)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Script generate_um_export_from_pms.py

## Overview

This script could be used when you want to generate an export file compatible with User Management Import/Export feature from a PMS backup file.\
It supports the backup files from the following PMS versions: 2.1, 2.2, 2.3, 2.4, 2.5 and 2.6.
The generated export file will have the name: 'export-UM-4.0-<<backup-file-name>>.zip'.
Later, you could import this file in the UserManagement having a version greater than or equal to 4.1.

Since the UM feature [MS-3734: [User Management] Create one scope per deployed app](https://myateme.atlassian.net/wiki/spaces/MSS/pages/4050747963/MS-3734+User+Management+Create+one+scope+per+deployed+app),
scopes may be prefixed with the application name, in addition to the api prefix. In this case, the scope format is: 
"app-name:prefix:scope".
By passing the parameter '--app-name-to-patch-in-scopes <target-app-name>' at the script execution, the scopes in the exported files will be patched with the <target-app-name>. All scopes are patched and the resulting scopes will be: target-app-name:prefix:scope.

Note: You can find details about the UM Import/Export feature [here](https://myateme.atlassian.net/wiki/spaces/MSS/pages/4122673253/MS-2969+UserManagement+Full+service+Backup+Restore).

## Usages

| Name                                                         | Description                                                                                                                                                                      |
|--------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-h`, `--help`                                               | Show the help message                                                                                                                                                           |
| `--backup-file-name backup-file`                             | The name of the backup file to process                                                                                                                                          |
| `--app-name-to-patch-in-scopes target-app-name` (optional)   | The name of the target application that will be used to patch scopes having format 'app-name:prefix:scope' |
| `--relative-output-directory relative-output_dir` (optional) | The directory where the output will be stored |

## Execution with 'tox' tool

Tox is a popular command-line tool used in the Python programming ecosystem for managing and automating testing and virtual environment creation. It primarily serves the purpose of helping developers ensure their Python projects work consistently
across different environments and configurations.\
You can install tox using the Python package manager pip. If you have pip installed (which is often included with Python installations), you can open a terminal or command prompt and run the following command:

```console
pip install tox
```


```console
usage: tox -r -- [-h]
                 [--backup_file_name backup-file]
                 [--app-name-to-patch-in-scopes application-name]
                 [--relative-output-directory relative-output_directory]

required argument:
  --backup-file-name backup-file                          The backup file to process

optional arguments:
  -h, --help                                              Show this help message and exit
  --app-name-to-patch-in-scopes application-name          The new name of the application to patch in the scopes <app-name>:<prefix>:<scope>
  --relative-output-directory relative-output-directory   The directory where the output will be stored

```

Note that you can regenerate the 'requirements.txt' by launching the command:

```console
tox -e reqs
```

## Execution with Docker

Build the docker image:
```console
docker build -t generate_um_export_from_pms .
```

Run the docker image:
```console
docker run generate_um_export_from_pms ...options...
```

Result without options:
```
usage: generate_um_export_from_pms.py [-h] --backup-file-name BACKUP_FILE_NAME
                                      [--app-name-to-patch-in-scopes APP_NAME_TO_PATCH_IN_SCOPES]
                                      [--relative-output-directory RELATIVE_OUTPUT_DIRECTORY]

Generate Export file from PMS backup compatible with UM import/export feature

optional arguments:
  -h, --help                                                    show this help message and exit
  --backup-file-name BACKUP_FILE_NAME                           Database backup file to process
  --app-name-to-patch-in-scopes APP_NAME_TO_PATCH_IN_SCOPES     App Name to use for patching scopes
  --relative-output-directory RELATIVE_OUTPUT_DIRECTORY         The directory where the output will be stored,
                                                                relative to the directory of the backup file
```

Generate an export file from a backup one:

```console
docker run  -v <directory-of-the-backup-file>:/opt/input generate_um_export_from_pms
  --backup-file-name  /opt/input/<name-of-the-backup-file>
  --relative-output-directory /opt/input/<relative-output-directory>

```

Generate an export file from a backup one with the patch of all scopes

```console
docker run  -v <directory-of-the-backup-file>:/opt/input \
 generate_um_export_from_pms \
 --backup-file-name  /opt/input/<name-of-the-backup-file> \
 --app-name-to-patch-in-scopes <new_app-name>       \
 --relative-output-directory /opt/input/<relative-output-directory>

```

## Compile script

If you need to compile this script, we may use the compile task define on tox.ini:

```bash
tox -e compile
```

## Run test on compile version

### Requirements:

* docker
* kind
* kubectl
* helm
* tox

```bash
./run_test.sh
```
