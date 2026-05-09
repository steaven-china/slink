import unittest

from slink.parser import dump_config, parse_config


class TestParseConfig(unittest.TestCase):
    def test_basic_key_value(self):
        text = "hostname: 10.0.0.5\nport: 22\nusername: root\n"
        result = parse_config(text)
        self.assertEqual(result["hostname"], "10.0.0.5")
        self.assertEqual(result["port"], 22)
        self.assertEqual(result["username"], "root")

    def test_equals_syntax(self):
        text = "hostname = 10.0.0.5\nport=2222\n"
        result = parse_config(text)
        self.assertEqual(result["hostname"], "10.0.0.5")
        self.assertEqual(result["port"], 2222)

    def test_comments_and_blank_lines(self):
        text = "\n# comment\nhostname: host\n\n"
        result = parse_config(text)
        self.assertEqual(result["hostname"], "host")

    def test_multiline_block(self):
        text = "key: |\nline1\nline2\n|end\n"
        result = parse_config(text)
        self.assertEqual(result["key"], "line1\nline2")

    def test_list_key(self):
        text = "extra_args: -A -o StrictHostKeyChecking=no\n"
        result = parse_config(text)
        self.assertEqual(result["extra_args"], ["-A", "-o", "StrictHostKeyChecking=no"])

    def test_unclosed_multiline_raises(self):
        text = "key: |\nline1\n"
        with self.assertRaises(ValueError):
            parse_config(text)

    def test_roundtrip(self):
        config = {
            "hostname": "10.0.0.5",
            "port": 22,
            "username": "root",
            "extra_args": ["-A"],
        }
        text = dump_config(config)
        result = parse_config(text)
        self.assertEqual(result, config)

    def test_multiline_roundtrip(self):
        config = {"key": "line1\nline2"}
        text = dump_config(config)
        result = parse_config(text)
        self.assertEqual(result, config)


if __name__ == "__main__":
    unittest.main()
