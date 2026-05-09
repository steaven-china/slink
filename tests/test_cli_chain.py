import unittest

from slink.api import unpack_chain


class TestUnpackChain(unittest.TestCase):
    def test_plain_chain(self):
        data = {
            "jumps": [{"hostname": "bastion", "username": "ops"}],
            "endpoint": {"hostname": "target", "username": "root"},
        }
        result = unpack_chain(data)
        self.assertIn("_chain", result)
        self.assertEqual(len(result["_chain"]["jumps"]), 1)
        self.assertEqual(result["_chain"]["endpoint"]["hostname"], "target")

    def test_legacy_target(self):
        data = {"jumps": [], "target": {"hostname": "old", "username": "u"}}
        result = unpack_chain(data)
        self.assertEqual(result["_chain"]["endpoint"]["hostname"], "old")

    def test_secrets_merged(self):
        data = {
            "topology": {
                "jumps": [{"hostname": "j1"}],
                "endpoint": {"hostname": "e1"},
            },
            "secrets": {
                "jumps": [{"password": "pw1", "key_file": "~/.ssh/j1"}],
                "endpoint": {"password": "pw2", "key": "KEYDATA"},
            },
        }
        result = unpack_chain(data)
        jumps = result["_chain"]["jumps"]
        endpoint = result["_chain"]["endpoint"]
        self.assertEqual(jumps[0]["password"], "pw1")
        import os
        self.assertEqual(jumps[0]["key_file"], os.path.expanduser("~/.ssh/j1"))
        self.assertEqual(endpoint["password"], "pw2")
        self.assertEqual(endpoint["key"], "KEYDATA")

    def test_topology_secrets_dict(self):
        data = {
            "topology": {
                "jumps": [
                    {"hostname": "hop1", "port": 2222, "username": "ops"}
                ],
                "endpoint": {"hostname": "dest", "username": "admin"},
            },
            "secrets": {"jumps": [], "endpoint": {}},
        }
        result = unpack_chain(data)
        self.assertEqual(result["_chain"]["jumps"][0]["hostname"], "hop1")
        self.assertEqual(result["_chain"]["jumps"][0]["port"], 2222)
        self.assertEqual(result["_chain"]["endpoint"]["username"], "admin")


if __name__ == "__main__":
    unittest.main()
