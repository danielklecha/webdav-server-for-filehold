import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from webdav_server_for_filehold.virtual_folder import VirtualFolder


class TestRename(unittest.TestCase):
    """
    Unit tests for renaming collections via VirtualFolder (and indirectly services).
    """

    def setUp(self) -> None:
        self.session_id = "test_session"
        self.base_url = "http://localhost/FH/FileHold/"
        self.mock_provider = MagicMock()
        self.environ: Dict[str, Any] = {
            "filehold.session_id": self.session_id,
            "filehold.url": self.base_url,
            "wsgidav.provider": self.mock_provider
        }

    def test_rename_cabinet(self) -> None:
        """
        Test renaming a cabinet.
        """
        vf = VirtualFolder("/Cab", self.environ, resource_id=1, level=1, name="Cab")
        vf.provider = self.mock_provider  # Must be set
        # Setup soap object
        vf.dto_object = MagicMock()
        vf.dto_object.Name = "Cab"

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value.service = mock_client

            vf.delete = MagicMock() # Should NOT be called for rename

            # Execute: This is done by 'support_recursive_move' + 'handle_move' in CustomProvider typically,
            # but usually rename is move to same parent with new name.
            # VirtualFolder doesn't have a 'rename' method exposed to DAV directly, usage is via move.
            # But let's check underlying service update.

            # We can test handle_move(new_path) where parent is same.
            parent = MagicMock()
            parent.level = 0
            self.mock_provider.get_resource_inst.return_value = parent

            vf.handle_move("/NewCab")

            mock_client.UpdateCabinet.assert_called()
            # Verify args
            # UpdateCabinet(changedCabinet=...)
            # The object literal is modified?
            self.assertEqual(vf.dto_object.Name, "NewCab")

    def test_rename_drawer(self) -> None:
        """
        Test renaming a drawer.
        """
        vf = VirtualFolder("/Cab/Drawer", self.environ, resource_id=10, level=2, name="Drawer")
        vf.provider = self.mock_provider
        vf.dto_object = MagicMock()
        vf.dto_object.Name = "Drawer"

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value.service = mock_client

            parent = MagicMock()
            parent.level = 1
            parent.resource_id = 1
            self.mock_provider.get_resource_inst.return_value = parent

            vf.handle_move("/Cab/NewDrawer")

            mock_client.UpdateDrawer.assert_called()
            self.assertEqual(vf.dto_object.Name, "NewDrawer")

    def test_rename_folder(self) -> None:
        """
        Test renaming a folder.
        """
        vf = VirtualFolder("/Cab/Drawer/Folder", self.environ, resource_id=100, level=3, name="Folder")
        vf.provider = self.mock_provider
        vf.dto_object = MagicMock()
        vf.dto_object.Name = "Folder"

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value.service = mock_client

            parent = MagicMock()
            parent.level = 2
            parent.resource_id = 10
            self.mock_provider.get_resource_inst.return_value = parent

            vf.handle_move("/Cab/Drawer/NewFolder")

            mock_client.UpdateFolder.assert_called()
            self.assertEqual(vf.dto_object.Name, "NewFolder")


if __name__ == '__main__':
    unittest.main()
