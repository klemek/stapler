import pathlib
import typing

import toml


def __get_project_data() -> dict[str, typing.Any]:
    pyproject_toml_file = pathlib.Path(__file__).parent.parent / "pyproject.toml"
    data = toml.load(pyproject_toml_file)
    return data["project"]


__project_data = __get_project_data()


def get_version() -> str:
    return __project_data["version"]


def get_name() -> str:
    return __project_data["name"]


def get_description() -> str:
    return __project_data["description"]
