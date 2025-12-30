import unittest
from unittest.mock import MagicMock
from webdav_server_for_filehold.library_object_service import LibraryObjectService


class TestLibraryObjectService(unittest.TestCase):
    """
    Unit tests for the LibraryObjectService class.
    """

    def test_insert_suffix_file(self) -> None:
        """
        Test suffix insertion for files.
        """
        name = "document.txt"
        suffix = "(1)"
        expected = "document (1).txt"
        result = LibraryObjectService._insert_suffix(name, suffix, is_file=True)
        self.assertEqual(result, expected)

    def test_insert_suffix_folder(self) -> None:
        """
        Test suffix insertion for folders.
        """
        name = "Folder"
        suffix = "(1)"
        expected = "Folder (1)"
        result = LibraryObjectService._insert_suffix(name, suffix, is_file=False)
        self.assertEqual(result, expected)

    def test_process_objects_empty(self) -> None:
        """
        Test processing an empty list of objects.
        """
        result = LibraryObjectService.process_objects([])
        self.assertEqual(result, [])

    def test_process_objects_no_duplicates(self) -> None:
        """
        Test processing objects with unique names.
        """
        item1 = MagicMock()
        item1.Name = "Item1"
        item1.Id = 1

        item2 = MagicMock()
        item2.Name = "Item2"
        item2.Id = 2

        items = [item1, item2]
        results = LibraryObjectService.process_objects(items)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].Name, "Item1")
        self.assertEqual(results[1].Name, "Item2")

    def test_process_objects_duplicates(self) -> None:
        """
        Test processing objects with duplicate names.
        """
        item1 = MagicMock()
        item1.Name = "Item"
        item1.Id = 1

        item2 = MagicMock()
        item2.Name = "Item"
        item2.Id = 2

        items = [item1, item2]
        results = LibraryObjectService.process_objects(items)

        self.assertEqual(len(results), 2)
        # Sort order is deterministic by ID, so Item with ID 1 should correspond to the first one
        self.assertEqual(results[0].Name, "Item")
        self.assertEqual(results[1].Name, "Item (2)")

    def test_process_objects_case_insensitive_duplicates(self) -> None:
        """
        Test processing objects with case-insensitive duplicate names.
        """
        item1 = MagicMock()
        item1.Name = "Item"
        item1.Id = 1

        item2 = MagicMock()
        item2.Name = "item"
        item2.Id = 2

        items = [item1, item2]
        results = LibraryObjectService.process_objects(items)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].Name, "Item")
        self.assertEqual(results[1].Name, "item (2)")


if __name__ == '__main__':
    unittest.main()
