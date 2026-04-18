from src.page import Page

from . import BaseTestCase


class TestPage(BaseTestCase):
    def test_repr(self) -> None:
        self.assertEqual(str(Page("test_1", with_index=True)), "/test_1/")

    def test_repr_no_index(self) -> None:
        self.assertEqual(str(Page("test_1", with_index=False)), "/test_1/ (no index)")

    def test_repr_with_host(self) -> None:
        self.assertEqual(
            str(Page("test_1", with_index=True, host="example.com")),
            "/test_1/ [example.com]",
        )
