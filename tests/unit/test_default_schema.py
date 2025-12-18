import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Optional

from webdav_for_filehold.folder_service import FolderService
from webdav_for_filehold.virtual_folder import VirtualFolder


class TestDefaultSchema(unittest.TestCase):
    """
    Unit tests for default schema handling in FolderService and VirtualFolder.
    """

    def test_get_schema_id_by_name_found(self) -> None:
        """
        Test getting schema ID by name when the schema exists.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_document_schema_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            # Mock schema objects
            schema1 = MagicMock()
            schema1.Name = "Other Schema"
            schema1.DocumentSchemaId = 100

            schema2 = MagicMock()
            schema2.Name = "Target Schema"
            schema2.DocumentSchemaId = 200

            # Mock return value (list)
            mock_service.GetDocumentSchemasInfoList.return_value = [schema1, schema2]

            # Test exact match
            result = FolderService.get_schema_id_by_name("sid", "url", "Target Schema")
            self.assertEqual(result, 200)

            # Test case insensitive
            result = FolderService.get_schema_id_by_name("sid", "url", "target schema")
            self.assertEqual(result, 200)

    def test_get_schema_id_by_name_not_found(self) -> None:
        """
        Test getting schema ID by name when the schema does not exist.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_document_schema_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service
            mock_service.GetDocumentSchemasInfoList.return_value = []

            result = FolderService.get_schema_id_by_name("sid", "url", "Missing Schema")
            self.assertIsNone(result)

    @patch('webdav_for_filehold.cabinet_service.CabinetService.add_cabinet')
    @patch('webdav_for_filehold.folder_service.FolderService.get_schema_id_by_name')
    def test_create_cabinet_with_default_schema(self, mock_get_schema: MagicMock, mock_add_cabinet: MagicMock) -> None:
        """
        Test creating a cabinet with a default schema.
        """
        environ: Dict[str, Any] = {
            "filehold.session_id": "sid",
            "filehold.url": "url",
            "filehold.user_guid": "uid",
            "filehold.default_schema_name": "MySchema",
            "wsgidav.provider": MagicMock()
        }

        vf = VirtualFolder("/", environ, level=0)

        # Mock schema lookup success
        mock_get_schema.return_value = 999
        mock_add_cabinet.return_value = 123

        vf.create_collection("New Cabinet")

        mock_add_cabinet.assert_called_with(
            "sid",
            "url",
            "New Cabinet",
            owner_guid="uid",
            default_schema_name="MySchema"
        )

    @patch('webdav_for_filehold.cabinet_service.CabinetService.add_cabinet')
    @patch('webdav_for_filehold.folder_service.FolderService.get_schema_id_by_name')
    def test_create_cabinet_schema_not_found(self, mock_get_schema: MagicMock, mock_add_cabinet: MagicMock) -> None:
        """
        Test creating a cabinet when the default schema is not found.
        """
        environ: Dict[str, Any] = {
            "filehold.session_id": "sid",
            "filehold.url": "url",
            "filehold.default_schema_name": "MissingSchema",
            "wsgidav.provider": MagicMock()
        }

        vf = VirtualFolder("/", environ, level=0)
        # VirtualFolder no longer checks validity, it just passes the name.
        # So we should mock the service to raise the exception if we want to test that VF propagates it.
        # But properly testing VF now means checking it passes the name.

        vf.create_collection("New Cabinet")
        mock_add_cabinet.assert_called_with(
            "sid",
            "url",
            "New Cabinet",
            owner_guid=None,  # No user_guid in this test setup
            default_schema_name="MissingSchema"
        )

    @patch('webdav_for_filehold.folder_service.FolderService.add_folder')
    @patch('webdav_for_filehold.folder_service.FolderService.get_schema_id_by_name')
    def test_create_folder_with_default_schema(self, mock_get_schema: MagicMock, mock_add_folder: MagicMock) -> None:
        """
        Test creating a folder with a default schema.
        """
        environ: Dict[str, Any] = {
            "filehold.session_id": "sid",
            "filehold.url": "url",
            "filehold.user_guid": "uid",
            "filehold.default_schema_name": "MySchema",
            "wsgidav.provider": MagicMock()
        }

        # Level 2 (Drawer) -> Creating Folder
        vf = VirtualFolder("/cab/drawer", environ, resource_id=10, level=2)

        mock_get_schema.return_value = 888
        mock_add_folder.return_value = 555

        vf.create_collection("New Folder")

        mock_add_folder.assert_called_with(
            "sid",
            "url",
            10,
            "New Folder",
            category_id=0,
            owner_guid="uid",
            default_schema_name="MySchema"
        )

    def test_add_folder_params(self) -> None:
        """
        Test arguments passed to AddFolder service.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client, \
                patch('webdav_for_filehold.folder_service.FolderService.get_schema_id_by_name') as mock_get_schema:

            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service
            mock_service.AddFolder.return_value = 1

            mock_get_schema.return_value = 777

            FolderService.add_folder("sid", "url", 10, "F", default_schema_name="Schema777")

            _, kwargs = mock_service.AddFolder.call_args
            new_folder = kwargs['newFolder']
            self.assertEqual(new_folder['DefaultSchema'], 777)
            self.assertEqual(new_folder['IsSchemaInherited'], False)


if __name__ == '__main__':
    unittest.main()
