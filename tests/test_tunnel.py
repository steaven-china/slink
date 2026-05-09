import unittest
from unittest.mock import patch

from click.testing import CliRunner

from slink.cli import cli


class TestTunnelCmd(unittest.TestCase):
    @patch("slink.cli.ssh_connect")
    @patch("slink.cli.get_host")
    def test_local_forward(self, mock_get_host, mock_ssh_connect):
        mock_get_host.return_value = {
            "hostname": "bastion",
            "username": "root",
            "port": 22,
        }
        runner = CliRunner()
        result = runner.invoke(cli, ["tunnel", "bastion", "-L", "8080:localhost:80", "--master-password", "pw"])
        self.assertEqual(result.exit_code, 0)
        args = mock_ssh_connect.call_args[0][0]
        self.assertIn("-N", args["extra_args"])
        self.assertIn("-T", args["extra_args"])
        self.assertIn("-L", args["extra_args"])
        self.assertIn("8080:localhost:80", args["extra_args"])

    @patch("slink.cli.ssh_connect")
    @patch("slink.cli.get_host")
    def test_socks5(self, mock_get_host, mock_ssh_connect):
        mock_get_host.return_value = {
            "hostname": "bastion",
            "username": "root",
            "port": 22,
        }
        runner = CliRunner()
        result = runner.invoke(cli, ["tunnel", "bastion", "-D", "1080", "--master-password", "pw"])
        self.assertEqual(result.exit_code, 0)
        args = mock_ssh_connect.call_args[0][0]
        self.assertIn("-D", args["extra_args"])
        self.assertIn("1080", args["extra_args"])

    @patch("slink.cli.ssh_connect")
    @patch("slink.cli.get_host")
    def test_multiple_forwards(self, mock_get_host, mock_ssh_connect):
        mock_get_host.return_value = {
            "hostname": "bastion",
            "username": "root",
            "port": 22,
        }
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "tunnel",
                "bastion",
                "-L",
                "8080:localhost:80",
                "-L",
                "9090:localhost:90",
                "-R",
                "9999:localhost:22",
                "--master-password",
                "pw",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        args = mock_ssh_connect.call_args[0][0]
        extra = args["extra_args"]
        self.assertEqual(extra.count("-L"), 2)
        self.assertEqual(extra.count("-R"), 1)

    @patch("slink.cli.ssh_connect")
    def test_host_file(self, mock_ssh_connect):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"hostname": "filehost", "port": 2222}, f)
            path = f.name
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ["tunnel", path, "-D", "1080"])
            self.assertEqual(result.exit_code, 0)
            args = mock_ssh_connect.call_args[0][0]
            self.assertEqual(args["hostname"], "filehost")
            self.assertIn("-D", args["extra_args"])
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
