import os.path
import toml
import typing

__project_data = None


def __get_project_data() -> None | dict[str, typing.Any]:
    global __project_data
    if __project_data is None:
        pyproject_toml_file = os.path.join(
            os.path.dirname(__file__), "..", "pyproject.toml"
        )
        if os.path.exists(pyproject_toml_file) and os.path.isfile(pyproject_toml_file):
            try:
                data = toml.load(pyproject_toml_file)
                if "project" in data:
                    __project_data = data["project"]
            except TypeError, toml.TomlDecodeError, FileNotFoundError:
                pass
    return __project_data


def __get_str_value(key: str) -> str:
    project_data = __get_project_data()
    if project_data is not None and key in project_data:
        return project_data[key]
    return "unknown"


def get_version() -> str:
    return __get_str_value("version")


def get_name() -> str:
    return __get_str_value("name")


def get_description() -> str:
    return __get_str_value("description")
