import os
import tempfile
import unittest

from slink import crypto
from slink import group


class TestGroup(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        crypto.DEFAULT_CONFIG_DIR = self.tmpdir.name
        group.GROUPS_FILE = os.path.join(self.tmpdir.name, "groups.yml")

    def test_load_save_groups(self):
        groups = {"web": {"hosts": ["web1", "web2"]}}
        group.save_groups(groups)
        loaded = group.load_groups()
        self.assertEqual(loaded["web"]["hosts"], ["web1", "web2"])

    def test_normalize_group_list(self):
        self.assertEqual(
            group._normalize_group(["h1", "h2"]),
            {"hosts": ["h1", "h2"], "groups": []},
        )

    def test_normalize_group_dict(self):
        self.assertEqual(
            group._normalize_group({"hosts": ["h1"], "groups": ["g2"]}),
            {"hosts": ["h1"], "groups": ["g2"]},
        )

    def test_resolve_group(self):
        groups = {
            "web": {"hosts": ["web1"], "groups": ["db"]},
            "db": {"hosts": ["db1"], "groups": []},
        }
        result = group.resolve_group("web", groups)
        self.assertEqual(result, ["web1", "db1"])

    def test_resolve_group_deduplication(self):
        groups = {
            "all": {"hosts": ["web1"], "groups": ["web"]},
            "web": {"hosts": ["web1", "web2"], "groups": []},
        }
        result = group.resolve_group("all", groups)
        self.assertEqual(result, ["web1", "web2"])

    def test_circular_reference(self):
        groups = {
            "a": {"hosts": [], "groups": ["b"]},
            "b": {"hosts": [], "groups": ["a"]},
        }
        with self.assertRaises(ValueError) as ctx:
            group.resolve_group("a", groups)
        self.assertIn("Circular", str(ctx.exception))

    def test_expand_targets(self):
        groups = {"web": {"hosts": ["web1"], "groups": []}}
        all_hosts = {"web1": {}, "db1": {}}
        result = group.expand_targets(["@web", "db1"], groups, all_hosts)
        self.assertEqual(result, ["web1", "db1"])

    def test_expand_targets_unknown_host(self):
        with self.assertRaises(ValueError):
            group.expand_targets(["missing"], {}, {})


if __name__ == "__main__":
    unittest.main()
