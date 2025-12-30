import unittest
from unittest.mock import MagicMock, patch
from webdav_server_for_filehold.drawer_service import DrawerService
from webdav_server_for_filehold.folder_service import FolderService
from webdav_server_for_filehold.virtual_folder import VirtualFolder

class TestMoveOperations(unittest.TestCase):

    def setUp(self):
        self.session_id = "test_session"
        self.base_url = "http://localhost/FH/FileHold/"
        self.session_id = "test_session"
        self.base_url = "http://localhost/FH/FileHold/"
        self.mock_provider = MagicMock()
        self.environ = {
            "filehold.session_id": self.session_id,
            "filehold.url": self.base_url,
            "wsgidav.provider": self.mock_provider
        }

    @patch("webdav_server_for_filehold.drawer_service.ClientFactory")
    def test_move_drawer_success(self, MockClientFactory):
        # Setup mock
        mock_client = MagicMock()
        MockClientFactory.get_library_structure_manager_client.return_value = mock_client
        
        # Call method
        result = DrawerService.move_drawer(
            self.session_id, self.base_url, drawer_id=10, dest_cabinet_id=5
        )

        # Verify
        self.assertTrue(result)
        mock_client.service.MoveDrawer.assert_called_once_with(
            drawerId=10, destCabinetId=5
        )

    @patch("webdav_server_for_filehold.folder_service.ClientFactory")
    def test_move_folder_success(self, MockClientFactory):
        # Setup mock
        mock_client = MagicMock()
        MockClientFactory.get_library_structure_manager_client.return_value = mock_client
        
        # Call method
        result = FolderService.move_folder(
            self.session_id, self.base_url, folder_id=100,
            dest_drawer_id=10, dest_category_id=0
        )

        # Verify
        self.assertTrue(result)
        mock_client.service.MoveFolder.assert_called_once_with(
            folderId=100, destDrawerId=10, destCategoryId=0
        )

    @patch("webdav_server_for_filehold.virtual_folder.DrawerService")
    @patch("webdav_server_for_filehold.virtual_folder.VirtualFolder._refresh")
    def test_virtual_folder_move_drawer(self, mock_refresh, MockDrawerService):
        # Setup VirtualFolder for Drawer
        drawer_vf = VirtualFolder(
            path="/Cabinet/Drawer",
            environ=self.environ,
            resource_id=10,
            level=VirtualFolder.LEVEL_DRAWER,
            name="Drawer"
        )
        # Mock provider (already in environ, but we need to configure return values)
        drawer_vf.provider = self.mock_provider
        
        # Destination parent (Cabinet)
        dest_cabinet = MagicMock()
        dest_cabinet.level = VirtualFolder.LEVEL_CABINET
        dest_cabinet.resource_id = 5
        
        dest_cabinet.resource_id = 5
        
        self.mock_provider.get_resource_inst.return_value = dest_cabinet
        MockDrawerService.move_drawer.return_value = True

        # Call handle_move with a path in a different cabinet
        result = drawer_vf.handle_move("/OtherCabinet/Drawer")

        # Verify
        self.assertTrue(result)
        MockDrawerService.move_drawer.assert_called_once_with(
            self.session_id, self.base_url, 10, 5
        )

    @patch("webdav_server_for_filehold.virtual_folder.FolderService")
    @patch("webdav_server_for_filehold.virtual_folder.VirtualFolder._refresh")
    def test_virtual_folder_move_folder(self, mock_refresh, MockFolderService):
        # Setup VirtualFolder for Folder
        folder_vf = VirtualFolder(
            path="/Cabinet/Drawer/Folder",
            environ=self.environ,
            resource_id=100,
            level=VirtualFolder.LEVEL_FOLDER,
            name="Folder"
        )
        # Mock provider
        folder_vf.provider = self.mock_provider
        
        # Destination parent (Category)
        dest_category = MagicMock()
        dest_category.level = VirtualFolder.LEVEL_CATEGORY
        dest_category.resource_id = 20
        dest_category.parent_resource_id = 10 # Drawer ID
        
        dest_category.parent_resource_id = 10 # Drawer ID
        
        self.mock_provider.get_resource_inst.return_value = dest_category
        MockFolderService.move_folder.return_value = True

        # Call handle_move with a path in a category
        result = folder_vf.handle_move("/Cabinet/Drawer/Category/Folder")

        # Verify
        self.assertTrue(result)
        MockFolderService.move_folder.assert_called_once_with(
            self.session_id, self.base_url, 100, 10, 20
        )

    @patch("webdav_server_for_filehold.virtual_folder.DrawerService")
    @patch("webdav_server_for_filehold.virtual_folder.VirtualFolder._refresh")
    def test_virtual_folder_move_drawer_with_rename(self, mock_refresh, MockDrawerService):
        # Setup VirtualFolder for Drawer
        drawer_vf = VirtualFolder(
            path="/Cabinet/Drawer",
            environ=self.environ,
            resource_id=10,
            level=VirtualFolder.LEVEL_DRAWER,
            name="Drawer"
        )
        # Mock provider
        drawer_vf.provider = self.mock_provider
        
        # Destination parent (Cabinet)
        dest_cabinet = MagicMock()
        dest_cabinet.level = VirtualFolder.LEVEL_CABINET
        dest_cabinet.resource_id = 5
        
        self.mock_provider.get_resource_inst.return_value = dest_cabinet
        MockDrawerService.move_drawer.return_value = True
        MockDrawerService.update_drawer.return_value = True

        # Call handle_move with a path in a different cabinet AND a different name
        result = drawer_vf.handle_move("/OtherCabinet/RenamedDrawer")

        # Verify
        self.assertTrue(result)
        MockDrawerService.move_drawer.assert_called_once_with(
            self.session_id, self.base_url, 10, 5
        )
        # This assertion expects the rename logic to be present
        MockDrawerService.update_drawer.assert_called_once_with(
            self.session_id, self.base_url, 10, "RenamedDrawer", drawer_vf.dto_object
        )

    @patch("webdav_server_for_filehold.virtual_folder.FolderService")
    @patch("webdav_server_for_filehold.virtual_folder.VirtualFolder._refresh")
    def test_virtual_folder_move_folder_with_rename(self, mock_refresh, MockFolderService):
        # Setup VirtualFolder for Folder
        folder_vf = VirtualFolder(
            path="/Cabinet/Drawer/Folder",
            environ=self.environ,
            resource_id=100,
            level=VirtualFolder.LEVEL_FOLDER,
            name="Folder"
        )
        # Mock provider
        folder_vf.provider = self.mock_provider
        
        # Destination parent (Drawer)
        dest_drawer = MagicMock()
        dest_drawer.level = VirtualFolder.LEVEL_DRAWER
        dest_drawer.resource_id = 10
        
        self.mock_provider.get_resource_inst.return_value = dest_drawer
        MockFolderService.move_folder.return_value = True
        MockFolderService.update_folder.return_value = True

        # Call handle_move with a path in a different location AND a different name
        result = folder_vf.handle_move("/Cabinet/OtherDrawer/RenamedFolder")

        # Verify
        self.assertTrue(result)
        MockFolderService.move_folder.assert_called_once_with(
            self.session_id, self.base_url, 100, 10, 0
        )
        # This assertion expects the rename logic to be present
        MockFolderService.update_folder.assert_called_once_with(
            self.session_id, self.base_url, 100, "RenamedFolder", folder_vf.dto_object
        )

if __name__ == '__main__':
    unittest.main()
