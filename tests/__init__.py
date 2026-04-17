import contextlib
import pathlib
import tempfile
import typing
import unittest
import unittest.mock


class BaseTestCase(unittest.TestCase):
    @typing.override
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.mocks: list[unittest.mock.Mock] = []
        self.tmp_dir: tempfile.TemporaryDirectory | None = None
        self.tmp_path = pathlib.Path()
        super().__init__(*args, **kwargs)

    @typing.override
    def tearDown(self) -> None:
        if self.tmp_dir is not None:
            self.tmp_dir.cleanup()
            self.tmp_dir = None
        super().tearDown()

    def get_tmp_dir(self) -> str:
        self.tmp_dir = tempfile.TemporaryDirectory(delete=False)
        self.tmp_path = pathlib.Path(self.tmp_dir.name)
        return self.tmp_dir.name

    def mock(self, spec: type | None = None) -> unittest.mock.Mock:
        mock = unittest.mock.Mock(spec)
        self.mocks += [mock]
        return mock

    @contextlib.contextmanager
    def patch(
        self, target: str, return_value: typing.Any = None, count: int = 1
    ) -> typing.Iterator[unittest.mock.Mock]:
        with unittest.mock.patch(
            target, return_value=return_value, create=True
        ) as mock:
            yield mock
            self.assertEqual(mock.call_count, count, mock)

    @contextlib.contextmanager
    def patch_calls(
        self,
        target: str,
        args: list[typing.Iterable[typing.Any]] | None = None,
        return_values: list[typing.Any] | None = None,
    ) -> typing.Iterator[unittest.mock.Mock]:
        if args is None:
            args = [[]]
        if return_values is None:
            return_values = [None] * len(args)
        with unittest.mock.patch(
            target, side_effect=return_values, create=True
        ) as mock:
            yield mock
            self.__check_calls(mock, args)

    @contextlib.contextmanager
    def patch_call(
        self,
        target: str,
        args: typing.Iterable[typing.Any] | None = None,
        return_value: typing.Any = None,
    ) -> typing.Iterator[unittest.mock.Mock]:
        if args is None:
            args = []
        with self.patch_calls(target, [args], [return_value]) as mock:
            yield mock

    @contextlib.contextmanager
    def seal_mocks(self, *extra_mocks: unittest.mock.Mock) -> typing.Iterator[None]:
        for mock in self.mocks:
            unittest.mock.seal(mock)
        for mock in extra_mocks:
            unittest.mock.seal(mock)
        yield

    @contextlib.contextmanager
    def mock_calls(
        self,
        mock: unittest.mock.Mock,
        args: list[typing.Iterable[typing.Any]] | None = None,
        return_values: list[typing.Any] | None = None,
    ) -> typing.Iterator[None]:
        if args is None:
            args = [[]]
        if return_values is None:
            return_values = [None] * len(args)
        mock.side_effect = return_values
        mock.reset_mock()
        yield
        self.__check_calls(mock, args)

    @contextlib.contextmanager
    def mock_call(
        self,
        mock: unittest.mock.Mock,
        args: typing.Iterable[typing.Any] | None = None,
        return_value: typing.Any = None,
    ) -> typing.Iterator[None]:
        if args is None:
            args = []
        with self.mock_calls(mock, [args], [return_value]):
            yield

    @contextlib.contextmanager
    def mock_calls_unchecked(
        self,
        mock: unittest.mock.Mock,
        count: int = 1,
        return_values: list[typing.Any] | None = None,
    ) -> typing.Iterator[None]:
        if return_values is None:
            return_values = [None] * count
        mock.side_effect = return_values
        mock.reset_mock()
        yield
        self.assertEqual(mock.call_count, count, mock)

    @contextlib.contextmanager
    def mock_call_unchecked(
        self,
        mock: unittest.mock.Mock,
        return_value: typing.Any = None,
    ) -> typing.Iterator[None]:
        with self.mock_calls_unchecked(mock, 1, [return_value]):
            yield

    def assert_file_content(self, file: pathlib.Path, *expected_content: str) -> None:
        assert file.parent.is_dir(), file
        assert file.exists(), file
        assert file.is_file(), file
        with file.open() as file_content:
            self.assertEqual(file_content.read(), "\n".join(expected_content))

    def __check_calls(
        self,
        mock: unittest.mock.Mock,
        args: list[typing.Iterable[typing.Any]],
    ) -> None:
        for i, values in enumerate(
            zip(
                mock.mock_calls
                + [None]
                * (max(len(args), len(mock.method_calls)) - len(mock.mock_calls)),
                args + [[]] * (max(len(args), len(mock.method_calls)) - len(args)),
                strict=False,
            )
        ):
            real_call, expected_args = values
            self.assertEqual(
                real_call, unittest.mock.call(*expected_args), f"{i + 1}: {mock}"
            )
