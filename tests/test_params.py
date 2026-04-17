from src.params import Parameters, parse_parameters

from . import BaseTestCase


class TestParams(BaseTestCase):
    ENV_COUNT = 10

    def test_parse_parameters(self) -> None:
        with self.patch("os.getenv", return_value=None, count=self.ENV_COUNT):
            params = parse_parameters(["run"])
            self.assertEqual(params, Parameters())

    def test_parse_parameters_with_implied_certificates(self) -> None:
        with self.patch("os.getenv", return_value=None, count=self.ENV_COUNT):
            params = parse_parameters(["--no-certificates", "--https", "run"])
            assert params.with_certificates

    def test_parse_parameters_without_implied_certificates(self) -> None:
        with self.patch("os.getenv", return_value=None, count=self.ENV_COUNT):
            params = parse_parameters(["--no-certificates", "--no-https", "run"])
            assert not params.with_certificates

    def test_parse_parameters_with_env_var(self) -> None:
        with self.patch("os.getenv", return_value="127.0.0.1", count=self.ENV_COUNT):
            params = parse_parameters(["run"])
            self.assertEqual(params.bind, "127.0.0.1")

    def test_parse_parameters_with_env_var_int(self) -> None:
        with self.patch("os.getenv", return_value="127", count=self.ENV_COUNT):
            params = parse_parameters(["run"])
            self.assertEqual(params.http_port, 127)

    def test_parse_parameters_with_invalid_env_var_int(self) -> None:
        with self.patch("os.getenv", return_value="aaa", count=self.ENV_COUNT):
            params = parse_parameters(["run"])
            self.assertEqual(params.http_port, 80)
