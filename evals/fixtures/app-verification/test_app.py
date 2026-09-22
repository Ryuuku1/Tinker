import unittest

from app import greeting


class GreetingTests(unittest.TestCase):
    def test_greets_by_name(self):
        self.assertEqual(greeting("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
