import os
import tempfile
import unittest
from unittest.mock import patch

from slink import crypto


class TestCrypto(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        # Patch module-level paths to use temp dir
        crypto.DEFAULT_CONFIG_DIR = self.tmpdir.name
        crypto.SALT_FILE = os.path.join(self.tmpdir.name, "salt")
        crypto.HOSTS_FILE = os.path.join(self.tmpdir.name, "hosts.enc")
        crypto.AGENT_HOSTS_FILE = os.path.join(self.tmpdir.name, "agent_hosts.enc")
        crypto.AGENT_EXPIRES_FILE = os.path.join(self.tmpdir.name, "agent_expires")
        crypto.AGENT_SALT_FILE = os.path.join(self.tmpdir.name, "agent_salt")
        # Fix salt to avoid intermittent InvalidToken failures in CI
        patcher = patch.object(crypto, "_get_or_create_salt", return_value=b"x" * 16)
        patcher.start()
        self.addCleanup(patcher.stop)
        agent_patcher = patch.object(crypto, "_get_agent_salt", return_value=b"a" * 16)
        agent_patcher.start()
        self.addCleanup(agent_patcher.stop)

    def test_derive_key_consistent(self):
        key1 = crypto._derive_key("password", b"salt" * 4)
        key2 = crypto._derive_key("password", b"salt" * 4)
        self.assertEqual(key1, key2)

    def test_derive_key_different_password(self):
        key1 = crypto._derive_key("password1", b"salt" * 4)
        key2 = crypto._derive_key("password2", b"salt" * 4)
        self.assertNotEqual(key1, key2)

    def test_encrypt_decrypt_text(self):
        token = crypto.encrypt_text("hello world", password="pw")
        plain = crypto.decrypt_text(token, password="pw")
        self.assertEqual(plain, "hello world")

    def test_decrypt_wrong_password(self):
        token = crypto.encrypt_text("secret", password="correct")
        with self.assertRaises(crypto.DecryptError):
            crypto.decrypt_text(token, password="wrong")

    def test_encrypt_decrypt_data(self):
        data = {"hosts": {"web1": {"hostname": "10.0.0.1"}}}
        token = crypto.encrypt_data(data, password="pw")
        result = crypto.decrypt_data(token, password="pw")
        self.assertEqual(result, data)

    def test_decrypt_data_wrong_password(self):
        token = crypto.encrypt_data({"a": 1}, password="correct")
        with self.assertRaises(crypto.DecryptError):
            crypto.decrypt_data(token, password="wrong")

    def test_save_load_hosts(self):
        from unittest.mock import patch
        hosts = {"web1": {"hostname": "10.0.0.1", "port": 22}}
        with patch.object(crypto, "_get_or_create_salt", return_value=b"x" * 16):
            crypto.save_hosts(hosts, password="pw")
            loaded = crypto.load_hosts(password="pw")
        self.assertEqual(loaded, hosts)

    def test_load_hosts_no_file(self):
        loaded = crypto.load_hosts(password="pw")
        self.assertEqual(loaded, {})

    def test_save_hosts_creates_file(self):
        crypto.save_hosts({}, password="pw")
        self.assertTrue(os.path.exists(crypto.HOSTS_FILE))

    def test_agent_hosts_roundtrip(self):
        hosts = {"web1": {"hostname": "10.0.0.1"}}
        crypto.save_agent_hosts(hosts, password="agent_pw", ttl=300)
        loaded = crypto.load_agent_hosts(password="agent_pw")
        self.assertEqual(loaded, hosts)

    def test_agent_hosts_expired(self):
        hosts = {"web1": {"hostname": "10.0.0.1"}}
        crypto.save_agent_hosts(hosts, password="agent_pw", ttl=0)
        with self.assertRaises(crypto.DecryptError):
            crypto.load_agent_hosts(password="agent_pw")


if __name__ == "__main__":
    unittest.main()
