import os
import tempfile
import unittest

from slink.ssh_config_parser import parse_ssh_config


class TestSSHConfigParser(unittest.TestCase):
    def _write_config(self, text: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".config")
        try:
            os.write(fd, text.encode("utf-8"))
        finally:
            os.close(fd)
        self.addCleanup(lambda: os.remove(path))
        return path

    def test_basic_parse(self):
        path = self._write_config(
            "Host bastion\n"
            "    HostName bastion.example.com\n"
            "    User ops\n"
            "    Port 2222\n"
            "    IdentityFile ~/.ssh/bastion_key\n"
        )
        hosts = parse_ssh_config(path)
        self.assertIn("bastion", hosts)
        self.assertEqual(hosts["bastion"]["hostname"], "bastion.example.com")
        self.assertEqual(hosts["bastion"]["username"], "ops")
        self.assertEqual(hosts["bastion"]["port"], 2222)
        self.assertEqual(
            hosts["bastion"]["key_file"], os.path.expanduser("~/.ssh/bastion_key")
        )

    def test_multi_alias(self):
        path = self._write_config(
            "Host web1 www\n"
            "    HostName 10.0.0.5\n"
            "    User root\n"
        )
        hosts = parse_ssh_config(path)
        self.assertIn("web1", hosts)
        self.assertIn("www", hosts)
        self.assertEqual(hosts["web1"]["hostname"], "10.0.0.5")
        self.assertEqual(hosts["www"]["hostname"], "10.0.0.5")
        self.assertEqual(hosts["web1"]["username"], "root")

    def test_wildcard_skipped(self):
        path = self._write_config(
            "Host *\n"
            "    ForwardAgent yes\n"
            "Host bastion\n"
            "    HostName bastion.example.com\n"
        )
        hosts = parse_ssh_config(path)
        self.assertNotIn("*", hosts)
        self.assertIn("bastion", hosts)

    def test_file_not_exists(self):
        self.assertEqual(parse_ssh_config("/nonexistent/path"), {})

    def test_comments_and_blank_lines(self):
        path = self._write_config(
            "# comment\n"
            "\n"
            "Host server\n"
            "    HostName 192.168.1.1\n"
        )
        hosts = parse_ssh_config(path)
        self.assertIn("server", hosts)
        self.assertEqual(hosts["server"]["hostname"], "192.168.1.1")


if __name__ == "__main__":
    unittest.main()
