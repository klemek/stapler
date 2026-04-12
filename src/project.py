import pathlib
import typing

import toml


def __get_project_data() -> None | dict[str, typing.Any]:
    pyproject_toml_file = pathlib.Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_toml_file.is_file():
        try:
            data = toml.load(pyproject_toml_file)
            if "project" in data:
                return data["project"]
        except TypeError, toml.TomlDecodeError, FileNotFoundError:
            pass
    return None


__project_data = __get_project_data()


def __get_str_value(key: str) -> str:
    project_data = __project_data
    if project_data is not None and key in project_data:
        return project_data[key]
    return "unknown"


def get_version() -> str:
    return __get_str_value("version")


def get_name() -> str:
    return __get_str_value("name")


def get_description() -> str:
    return __get_str_value("description")
