import os
import tempfile
import unittest
from unittest.mock import patch

from slink import crypto, store


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        # Patch crypto paths
        crypto.DEFAULT_CONFIG_DIR = self.tmpdir.name
        crypto.SALT_FILE = os.path.join(self.tmpdir.name, "salt")
        crypto.HOSTS_FILE = os.path.join(self.tmpdir.name, "hosts.enc")
        crypto.AGENT_HOSTS_FILE = os.path.join(self.tmpdir.name, "agent_hosts.enc")
        crypto.AGENT_EXPIRES_FILE = os.path.join(self.tmpdir.name, "agent_expires")
        crypto.AGENT_SALT_FILE = os.path.join(self.tmpdir.name, "agent_salt")
        # Patch store paths
        store._LOCK_FILE = os.path.join(self.tmpdir.name, ".lock")
        store.SHOW_DIRECT_FILE = os.path.join(self.tmpdir.name, ".show_direct")
        # Fix salt to avoid intermittent InvalidToken failures in CI
        patcher = patch.object(crypto, "_get_or_create_salt", return_value=b"x" * 16)
        patcher.start()
        self.addCleanup(patcher.stop)
        agent_patcher = patch.object(crypto, "_get_agent_salt", return_value=b"a" * 16)
        agent_patcher.start()
        self.addCleanup(agent_patcher.stop)

    def test_add_and_get_host(self):
        store.add_host("web1", {"hostname": "10.0.0.1", "port": 22}, password="pw")
        info = store.get_host("web1", password="pw")
        self.assertEqual(info["hostname"], "10.0.0.1")

    def test_alias_resolution(self):
        store.add_host("web1", {"hostname": "10.0.0.1", "aliases": ["www"]}, password="pw")
        info = store.get_host("www", password="pw")
        self.assertEqual(info["hostname"], "10.0.0.1")

    def test_duplicate_name_raises(self):
        store.add_host("web1", {"hostname": "10.0.0.1"}, password="pw")
        with self.assertRaises(ValueError):
            store.add_host("web1", {"hostname": "10.0.0.2"}, password="pw")

    def test_alias_conflict_raises(self):
        store.add_host("web1", {"hostname": "10.0.0.1", "aliases": ["www"]}, password="pw")
        with self.assertRaises(ValueError):
            store.add_host("web2", {"hostname": "10.0.0.2", "aliases": ["www"]}, password="pw")

    def test_remove_host(self):
        store.add_host("web1", {"hostname": "10.0.0.1"}, password="pw")
        store.remove_host("web1", password="pw")
        self.assertIsNone(store.get_host("web1", password="pw"))

    def test_upsert_host(self):
        store.upsert_host("web1", {"hostname": "10.0.0.1"}, password="pw")
        store.upsert_host("web1", {"hostname": "10.0.0.2"}, password="pw")
        info = store.get_host("web1", password="pw")
        self.assertEqual(info["hostname"], "10.0.0.2")

    def test_list_hosts(self):
        store.add_host("web1", {"hostname": "10.0.0.1"}, password="pw")
        store.add_host("web2", {"hostname": "10.0.0.2"}, password="pw")
        hosts = store.list_hosts(password="pw")
        self.assertEqual(sorted(hosts.keys()), ["web1", "web2"])

    def test_rotate_password(self):
        store.add_host("web1", {"hostname": "10.0.0.1"}, password="old")
        store.rotate_password("old", "new")
        info = store.get_host("web1", password="new")
        self.assertEqual(info["hostname"], "10.0.0.1")

    def test_show_direct_names(self):
        store.add_host("web1", {"hostname": "10.0.0.1"}, password="pw")
        names = store.get_show_direct_names()
        self.assertIn("web1", names)


if __name__ == "__main__":
    unittest.main()
