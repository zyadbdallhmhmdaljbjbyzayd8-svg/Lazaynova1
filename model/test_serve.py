import unittest
from serve import encode, decode, STOI, generate

class LocalRuntimeTests(unittest.TestCase):
    def test_known_character_round_trip(self):
        ch = next(iter(STOI))
        self.assertEqual(decode(encode(ch)), ch)
    def test_unknown_characters_are_ignored(self):
        self.assertEqual(encode("\U0001f9ff"), [])
    def test_generation_returns_string(self):
        self.assertIsInstance(generate([{"role":"user","content":"مرحبا"}], 2, .8), str)

if __name__ == "__main__":
    unittest.main()
