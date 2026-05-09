import unittest

from slink.ssh_wrapper import _build_chain_config, _escape_config_val


class TestEscapeConfigVal(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_escape_config_val("/home/user/key"), "/home/user/key")

    def test_with_spaces(self):
        self.assertEqual(
            _escape_config_val("C:/Users/My User/key"), '"C:/Users/My User/key"'
        )

    def test_with_quotes(self):
        self.assertEqual(
            _escape_config_val('say "hello"'), '"say \\"hello\\""'
        )


class TestBuildChainConfig(unittest.TestCase):
    def test_single_jump(self):
        jumps = [
            {
                "hostname": "bastion",
                "username": "ops",
                "port": 2222,
                "key_file": "/tmp/jump_key",
            }
        ]
        cfg = _build_chain_config(jumps, {})
        self.assertIn("Host slk_jump_0", cfg)
        self.assertIn("HostName bastion", cfg)
        self.assertIn("User ops", cfg)
        self.assertIn("Port 2222", cfg)
        self.assertIn("IdentityFile /tmp/jump_key", cfg)
        self.assertIn("StrictHostKeyChecking accept-new", cfg)

    def test_temp_key_override(self):
        jumps = [{"hostname": "j1", "key_file": "/old/key"}]
        temp_keys = {"jump_0": "/tmp/new_key"}
        cfg = _build_chain_config(jumps, temp_keys)
        self.assertIn("IdentityFile /tmp/new_key", cfg)
        self.assertNotIn("/old/key", cfg)

    def test_no_key(self):
        jumps = [{"hostname": "j1"}]
        cfg = _build_chain_config(jumps, {})
        self.assertNotIn("IdentityFile", cfg)

    def test_default_port_omitted(self):
        jumps = [{"hostname": "j1", "port": 22}]
        cfg = _build_chain_config(jumps, {})
        self.assertNotIn("Port", cfg)

    def test_windows_path_conversion(self):
        jumps = [{"hostname": "j1", "key_file": "C:\\Users\\key"}]
        cfg = _build_chain_config(jumps, {})
        self.assertIn("IdentityFile C:/Users/key", cfg)

    def test_multiple_jumps(self):
        jumps = [
            {"hostname": "j1", "username": "a"},
            {"hostname": "j2", "username": "b", "port": 2222},
        ]
        cfg = _build_chain_config(jumps, {})
        self.assertIn("Host slk_jump_0", cfg)
        self.assertIn("Host slk_jump_1", cfg)
        self.assertIn("User a", cfg)
        self.assertIn("User b", cfg)
        self.assertIn("Port 2222", cfg)


if __name__ == "__main__":
    unittest.main()
