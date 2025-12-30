
import unittest
from unittest.mock import MagicMock, patch
from webdav_server_for_filehold.document_service import DocumentService
from webdav_server_for_filehold.virtual_file import VirtualFile
from webdav_server_for_filehold.virtual_folder import VirtualFolder

class TestDocumentMove(unittest.TestCase):

    def setUp(self):
        self.session_id = "test_session"
        self.base_url = "http://localhost/FH/FileHold/"
        self.mock_provider = MagicMock()
        self.environ = {
            "filehold.session_id": self.session_id,
            "filehold.url": self.base_url,
            "wsgidav.provider": self.mock_provider
        }
        self.document_data = MagicMock()
        self.document_data.DocumentId = 123
        self.document_data.MetadataVersionId = 456
        self.document_data.SnapshotId = "snapshot_guid"

    @patch("webdav_server_for_filehold.document_service.ClientFactory")
    def test_move_document_success(self, MockClientFactory):
        # Setup mock
        mock_client = MagicMock()
        MockClientFactory.get_document_manager_client.return_value = mock_client
        mock_client.service.Move.return_value = True
        
        # Ensure it doesn't look like a ColumnsWithValues wrapper
        self.document_data.DocumentData = None
        
        # Setup create selection mock (internal method)
        with patch.object(DocumentService, "_create_single_document_selection", return_value="selection_guid") as mock_selection:
            # Call method
            result = DocumentService.move_document(
                self.session_id, self.base_url, self.document_data, target_folder_id=10, snapshot_id="snap123"
            )

            # Verify
            self.assertTrue(result)
            mock_selection.assert_called_once_with(mock_client, self.document_data, "snap123")
            mock_client.service.Move.assert_called_once_with("selection_guid", 10)

    @patch("webdav_server_for_filehold.virtual_file.DocumentService")
    def test_virtual_file_info_moved(self, MockDocumentService):
        # Setup VirtualFile
        v_file = VirtualFile(
            path="/Cabinet/Drawer/Folder/doc.txt",
            environ=self.environ,
            name="doc.txt",
            dto_object=self.document_data,
            snapshot_id="snap_guid"
        )
        v_file.provider = self.mock_provider
        
        # Setup Move Destination
        dest_folder = MagicMock()
        dest_folder.level = 3 # LEVEL_FOLDER
        dest_folder.resource_id = 999
        self.mock_provider.get_resource_inst.return_value = dest_folder
        
        MockDocumentService.move_document.return_value = True

        # Perform logic
        # Moving to a different folder
        result = v_file.handle_move("/Cabinet/Drawer/OtherFolder/doc.txt")

        # Verify
        self.assertTrue(result)
        # Check that get_resource_inst was called for parent path
        self.mock_provider.get_resource_inst.assert_called_with("/Cabinet/Drawer/OtherFolder", self.environ)
        
        # Check that move_document was called
        MockDocumentService.move_document.assert_called_once_with(
            self.session_id, self.base_url, self.document_data, 999, snapshot_id="snap_guid"
        )
        # Verify no rename happened
        MockDocumentService.update_document.assert_not_called()

    @patch("webdav_server_for_filehold.virtual_file.DocumentService")
    def test_virtual_file_move_and_rename(self, MockDocumentService):
        # Setup VirtualFile
        v_file = VirtualFile(
            path="/Cabinet/Drawer/Folder/doc.txt",
            environ=self.environ,
            name="doc.txt",
            dto_object=self.document_data,
            snapshot_id="snap_guid"
        )
        v_file.provider = self.mock_provider
        
        # Setup Move Destination
        dest_folder = MagicMock()
        dest_folder.level = 3 # LEVEL_FOLDER
        dest_folder.resource_id = 999
        self.mock_provider.get_resource_inst.return_value = dest_folder
        
        MockDocumentService.move_document.return_value = True
        MockDocumentService.update_document.return_value = 1001 # New MetadataVersionId

        # Perform logic
        # Moving to a different folder AND renaming
        result = v_file.handle_move("/Cabinet/Drawer/OtherFolder/new_doc.txt")

        # Verify
        self.assertTrue(result)
        MockDocumentService.move_document.assert_called_once_with(
            self.session_id, self.base_url, self.document_data, 999, snapshot_id="snap_guid"
        )
        MockDocumentService.update_document.assert_called_once_with(
            self.session_id, self.base_url, self.document_data, "new_doc.txt"
        )
        self.assertEqual(v_file.name, "new_doc.txt")
        self.assertEqual(v_file.metadata_version_id, 1001)

    @patch("webdav_server_for_filehold.virtual_file.DocumentService")
    def test_virtual_file_move_invalid_destination(self, MockDocumentService):
        # Setup VirtualFile
        v_file = VirtualFile(
            path="/Cabinet/Drawer/Folder/doc.txt",
            environ=self.environ,
            name="doc.txt",
            dto_object=self.document_data
        )
        v_file.provider = self.mock_provider
        
        # Setup Destination that is NOT a folder (e.g. Drawer, level 2)
        dest_drawer = MagicMock()
        dest_drawer.level = 2 # LEVEL_DRAWER
        dest_drawer.resource_id = 888
        self.mock_provider.get_resource_inst.return_value = dest_drawer

        # Perform logic - expect exception
        with self.assertRaises(Exception) as context:
            v_file.handle_move("/Cabinet/DifferentDrawer/doc.txt")
        
        self.assertIn("Documents can only be moved to Folders", str(context.exception))
        MockDocumentService.move_document.assert_not_called()

    def test_support_recursive_move(self):
        v_file = VirtualFile(
            path="/Cabinet/Drawer/Folder/doc.txt",
            environ=self.environ,
            name="doc.txt",
            dto_object=self.document_data
        )
        self.assertTrue(v_file.support_recursive_move("/some/dest"))
        
        # Test move_recursive calls handle_move
        with patch.object(v_file, 'handle_move') as mock_handle:
            v_file.move_recursive("/some/dest")
            mock_handle.assert_called_once_with("/some/dest")


if __name__ == '__main__':
    unittest.main()
