import unittest
from webdav_server_for_filehold.utils import sanitize_name


class TestUtils(unittest.TestCase):
    """
    Unit tests for utility functions.
    """

    def test_sanitize_name_none(self) -> None:
        """
        Test sanitizing None returns 'Unknown'.
        """
        self.assertEqual(sanitize_name(None), "Unknown")

    def test_sanitize_name_empty(self) -> None:
        """
        Test sanitizing empty string returns 'Unknown'.
        """
        self.assertEqual(sanitize_name(""), "Unknown")

    def test_sanitize_name_valid(self) -> None:
        """
        Test sanitizing a valid name returns the name itself.
        """
        self.assertEqual(sanitize_name("valid_name.txt"), "valid_name.txt")

    def test_sanitize_name_invalid_chars(self) -> None:
        """
        Test sanitizing a name with invalid characters replaces them with underscores.
        """
        self.assertEqual(sanitize_name("invalid*name?.txt"), "invalid_name_.txt")

    def test_sanitize_name_whitespace(self) -> None:
        """
        Test sanitizing a name strips leading/trailing whitespace.
        """
        self.assertEqual(sanitize_name("  trimmed_name.txt  "), "trimmed_name.txt")


if __name__ == '__main__':
    unittest.main()
