import unittest
from unittest.mock import MagicMock, patch
from webdav_for_filehold.folder_service import FolderService


class TestFolderService(unittest.TestCase):
    """
    Unit tests for the FolderService class.
    """

    def test_add_folder_structure(self) -> None:
        """
        Test adding a folder structure (folder within a drawer).
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service
            mock_service.AddFolder.return_value = 100

            result = FolderService.add_folder(
                session_id="sess",
                base_url="http://host",
                drawer_id=10,
                folder_name="New Folder",
                description="Desc"
            )

            self.assertEqual(result, 100)
            _, kwargs = mock_service.AddFolder.call_args
            self.assertEqual(kwargs['drawerId'], 10)
            new_folder = kwargs['newFolder']
            self.assertEqual(new_folder['Name'], "New Folder")
            self.assertEqual(new_folder['Description'], "Desc")
            self.assertEqual(new_folder['OwnerGuid'], FolderService.DEFAULT_OWNER_GUID)

    def test_add_folder_with_default_schema(self) -> None:
        """
        Test adding a folder with a default schema specified.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_lib_client, \
             patch('webdav_for_filehold.folder_service.FolderService.get_schema_id_by_name', return_value=99) as mock_get_schema:

            mock_service = MagicMock()
            mock_lib_client.return_value.service = mock_service
            mock_service.AddFolder.return_value = 101

            FolderService.add_folder(
                session_id="sess",
                base_url="http://host",
                drawer_id=10,
                folder_name="F",
                default_schema_name="MySchema"
            )

            mock_get_schema.assert_called_with("sess", "http://host", "MySchema")
            _, kwargs = mock_service.AddFolder.call_args
            self.assertEqual(kwargs['newFolder']['DefaultSchema'], 99)
            self.assertEqual(kwargs['newFolder']['IsSchemaInherited'], False)

    def test_update_folder(self) -> None:
        """
        Test updating a folder's properties.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            folder_obj = MagicMock()
            folder_obj.Name = "Old Name"
            folder_obj.CanEdit = True

            result = FolderService.update_folder("sess", "http://host", 1, "New Name", folder_obj)

            self.assertTrue(result)
            self.assertEqual(folder_obj.Name, "New Name")
            mock_service.UpdateFolder.assert_called_with(changedFolder=folder_obj)

    def test_remove_folder(self) -> None:
        """
        Test removing a folder.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            result = FolderService.remove_folder("sess", "http://host", 1)

            self.assertTrue(result)
            mock_service.RemoveFolder.assert_called_with(folderId=1, forceContentRemoval=True)

    def test_get_schema_id_by_name(self) -> None:
        """
        Test retrieving schema ID by name.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_document_schema_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            s1 = MagicMock()
            s1.Name = "Schema1"
            s1.DocumentSchemaId = 10
            s2 = MagicMock()
            s2.Name = "Target"
            s2.DocumentSchemaId = 20

            mock_service.GetDocumentSchemasInfoList.return_value = [s1, s2]

            res = FolderService.get_schema_id_by_name("sess", "http://host", "target")
            self.assertEqual(res, 20)

            res_none = FolderService.get_schema_id_by_name("sess", "http://host", "missing")
            self.assertIsNone(res_none)


if __name__ == '__main__':
    unittest.main()
