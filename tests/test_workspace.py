import os
import tempfile
import unittest

from slink import crypto
from slink import workspace


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        crypto.DEFAULT_CONFIG_DIR = self.tmpdir.name
        workspace.WORKSPACES_DIR = os.path.join(self.tmpdir.name, "workspaces")

    def test_save_load_list_delete(self):
        data = {"name": "prod", "hosts": ["web1", "web2"]}
        workspace.save_workspace(data, "prod")
        self.assertEqual(workspace.list_workspaces(), ["prod"])
        loaded = workspace.load_workspace("prod")
        self.assertEqual(loaded["name"], "prod")
        self.assertEqual(loaded["hosts"], ["web1", "web2"])
        workspace.delete_workspace("prod")
        self.assertEqual(workspace.list_workspaces(), [])

    def test_load_not_found(self):
        with self.assertRaises(ValueError):
            workspace.load_workspace("missing")

    def test_build_workspace(self):
        ws = workspace.build_workspace(
            "test", ["h1", "h2"], blocked=["h1"], focused="h2", mode="focus"
        )
        self.assertEqual(ws["name"], "test")
        self.assertEqual(ws["hosts"], ["h1", "h2"])
        self.assertEqual(ws["blocked"], ["h1"])
        self.assertEqual(ws["focused"], "h2")
        self.assertEqual(ws["mode"], "focus")
        self.assertIn("created_at", ws)

    def test_find_workspace_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, ".sli-workspace.json")
            with open(path, "w") as f:
                f.write("{}")
            found = workspace.find_workspace_file(tmpdir)
            self.assertEqual(found, path)

    def test_find_workspace_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            found = workspace.find_workspace_file(tmpdir)
            self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
