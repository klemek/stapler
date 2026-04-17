from src.project import get_description, get_name, get_version

from . import BaseTestCase


class TestProject(BaseTestCase):
    def test_get_version(self) -> None:
        self.assertRegex(get_version(), r"\d+\.\d+\.\d+")

    def test_get_name(self) -> None:
        assert get_name() is not None

    def test_get_description(self) -> None:
        assert get_description() is not None
