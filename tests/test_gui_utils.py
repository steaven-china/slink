import unittest

from slink.gui import SlinkGUI


class TestParseJumpSpec(unittest.TestCase):
    def test_simple_hostname(self):
        self.assertEqual(
            SlinkGUI._parse_jump_spec("bastion"),
            {"hostname": "bastion", "username": None, "port": 22},
        )

    def test_user_at_host(self):
        self.assertEqual(
            SlinkGUI._parse_jump_spec("ops@bastion"),
            {"hostname": "bastion", "username": "ops", "port": 22},
        )

    def test_host_with_port(self):
        self.assertEqual(
            SlinkGUI._parse_jump_spec("bastion:2222"),
            {"hostname": "bastion", "username": None, "port": 2222},
        )

    def test_full_spec(self):
        self.assertEqual(
            SlinkGUI._parse_jump_spec("ops@bastion:2222"),
            {"hostname": "bastion", "username": "ops", "port": 2222},
        )

    def test_invalid_port(self):
        self.assertEqual(
            SlinkGUI._parse_jump_spec("host:abc"),
            {"hostname": "host", "username": None, "port": 22},
        )


if __name__ == "__main__":
    unittest.main()
