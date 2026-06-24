"""
test_main.py
"""
import os
import pytest
from ateme.um_backend.scripts.generate_auth.__main__ import main as app_main, OUTPUT_FORMATTER


CURRENT_DIR = os.path.join(os.path.dirname(__file__))


def test_main_missing_sub_command():
    """test_main_missing_sub_command"""
    arguments = []
    with pytest.raises(SystemExit) as pytest_wrapped_err:
        app_main(arguments)
    assert pytest_wrapped_err.type == SystemExit
    assert pytest_wrapped_err.value.code == 2


@pytest.mark.parametrize("output_dir", [None, os.path.join(CURRENT_DIR, "outputs")])
@pytest.mark.parametrize("add_app_level_scopes", [True, False])
@pytest.mark.parametrize("arguments", [
    (
        [
            "--definition-filepath", os.path.join(CURRENT_DIR, "inputs", "api_one.yaml"),
            "--upstream-url", "http://fake_url:8081",
            "--definition-filepath", os.path.join(CURRENT_DIR, "inputs", "api_two.yaml"),
            "--upstream-url", "http://fake_url:8082",
            "--app-name-pattern", "my_app_pattern",
        ]
    )
])
def test_main_sub_command_authloader(capsys, arguments: list, output_dir: str, add_app_level_scopes: bool):
    """test_main_sub_command_authloader"""

    expected_filename = "auth_reference"
    if add_app_level_scopes:
        expected_filename += "_with_app_scopes"
    expected_file = os.path.join(CURRENT_DIR, "references", expected_filename + ".yaml")

    output_file = None
    if output_dir:
        output_filename = "auth_result"
        if add_app_level_scopes:
            output_filename += "_with_app_scopes"
        output_file = os.path.join(output_dir, output_filename + ".yaml")

    args = ["authloader"] + arguments
    if add_app_level_scopes:
        args += ["--add-app-level-scopes"]
    if output_dir:
        args += ["--output-dir", output_dir, "--output-filename", output_filename]
    app_main(args)

    with open(expected_file) as expected_fd:
        expected = expected_fd.read()
        if output_file:
            assert os.path.exists(output_file)
            with open(output_file) as output_fd:
                result = output_fd.read()
                assert expected == result
        else:
            result = capsys.readouterr().out
            assert expected in result


@pytest.mark.parametrize("output_dir", [None, os.path.join(CURRENT_DIR, "outputs")])
@pytest.mark.parametrize("arguments", [
    (
        [
            "--definition-filepath", os.path.join(CURRENT_DIR, "inputs", "api_one.yaml"),
            "--upstream-url", "http://fake_url:8081",
            "--definition-filepath", os.path.join(CURRENT_DIR, "inputs", "api_two.yaml"),
            "--upstream-url", "http://fake_url:8082",
        ]
    )
])
def test_main_sub_command_umbackend(capsys, arguments: list, output_dir: str):
    """test_main_sub_command_umbackend"""

    expected_file = os.path.join(CURRENT_DIR, "references", "umb_reference.json")

    output_file = None
    if output_dir:
        output_filename = "umb_result"
        output_file = os.path.join(output_dir, output_filename + ".json")

    args = ["umbackend"] + arguments
    if output_dir:
        args += ["--output-dir", output_dir, "--output-filename", output_filename]
    app_main(args)

    with open(expected_file) as expected_fd:
        expected = expected_fd.read()
        if output_file:
            assert os.path.exists(output_file)
            with open(output_file) as output_fd:
                result = output_fd.read()
                assert expected == result
        else:
            result = capsys.readouterr().out
            assert expected in result

