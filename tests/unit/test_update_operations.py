import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from webdav_for_filehold.virtual_folder import VirtualFolder
from webdav_for_filehold.cabinet_service import CabinetService
from webdav_for_filehold.drawer_service import DrawerService
from webdav_for_filehold.folder_service import FolderService


class TestUpdateOperations(unittest.TestCase):
    """
    Unit tests for update operations (renaming) on Cabinets, Drawers, and Folders.
    """

    def test_update_cabinet_permission_granted(self) -> None:
        """
        Test successful cabinet update when permission is granted.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        cabinet_id = 1
        new_name = "New Name"

        mock_cabinet = MagicMock()
        mock_cabinet.CanEdit = True
        mock_cabinet.Name = "Old Name"

        mock_client = MagicMock()

        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client', return_value=mock_client):
            result = CabinetService.update_cabinet(session_id, base_url, cabinet_id, new_name, mock_cabinet)

            self.assertTrue(result)
            self.assertEqual(mock_cabinet.Name, new_name)
            mock_client.service.UpdateCabinet.assert_called_once()

    def test_update_cabinet_permission_denied(self) -> None:
        """
        Test cabinet update failure when permission is denied.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        cabinet_id = 1
        new_name = "New Name"

        mock_cabinet = MagicMock()
        mock_cabinet.CanEdit = False
        mock_cabinet.Name = "Old Name"

        # Test
        with self.assertRaises(Exception) as cm:
            CabinetService.update_cabinet(session_id, base_url, cabinet_id, new_name, mock_cabinet)

        self.assertIn("Permission denied", str(cm.exception))

    def test_update_drawer_permission_granted(self) -> None:
        """
        Test successful drawer update when permission is granted.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        drawer_id = 1
        new_name = "New Drawer Name"

        mock_drawer = MagicMock()
        mock_drawer.CanEdit = True
        mock_drawer.Name = "Old Drawer Name"

        mock_client = MagicMock()

        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client', return_value=mock_client):
            result = DrawerService.update_drawer(session_id, base_url, drawer_id, new_name, mock_drawer)

            self.assertTrue(result)
            self.assertEqual(mock_drawer.Name, new_name)
            mock_client.service.UpdateDrawer.assert_called_once()

    def test_update_drawer_permission_denied(self) -> None:
        """
        Test drawer update failure when permission is denied.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        drawer_id = 1
        new_name = "New Drawer Name"

        mock_drawer = MagicMock()
        mock_drawer.CanEdit = False

        # Test
        with self.assertRaises(Exception) as cm:
            DrawerService.update_drawer(session_id, base_url, drawer_id, new_name, mock_drawer)

        self.assertIn("Permission denied", str(cm.exception))

    def test_handle_move_drawer(self) -> None:
        """
        Test handle_move logic for a VirtualFolder representing a Drawer.
        """
        # Setup VirtualFolder for a Drawer
        environ: Dict[str, Any] = {"filehold.session_id": "sid", "filehold.url": "http://url", "wsgidav.provider": MagicMock()}
        mock_drawer = MagicMock()
        mock_drawer.CanEdit = True
        mock_drawer.Name = "Drawer 1"
        mock_drawer.Id = 10

        vf = VirtualFolder("/Cab/Drawer_1", environ, resource_id=10, level=2, soap_object=mock_drawer, name="Drawer 1")

        destination = "/Cab/Drawer Renamed"

        with patch('webdav_for_filehold.drawer_service.DrawerService.update_drawer') as mock_update:
            vf.handle_move(destination)

            mock_update.assert_called_once()
            args, _ = mock_update.call_args
            # Args: session_id, base_url, drawer_id, new_name, drawer_obj
            self.assertEqual(args[2], 10)
            self.assertEqual(args[3], "Drawer Renamed")

    def test_update_folder_permission_granted(self) -> None:
        """
        Test successful folder update when permission is granted.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        folder_id = 1
        new_name = "New Folder Name"

        mock_folder = MagicMock()
        mock_folder.CanEdit = True
        mock_folder.Name = "Old Folder Name"

        mock_client = MagicMock()

        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client', return_value=mock_client):
            result = FolderService.update_folder(session_id, base_url, folder_id, new_name, mock_folder)

            self.assertTrue(result)
            self.assertEqual(mock_folder.Name, new_name)
            mock_client.service.UpdateFolder.assert_called_once()

    def test_update_folder_permission_denied(self) -> None:
        """
        Test folder update failure when permission is denied.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        folder_id = 1
        new_name = "New Folder Name"

        mock_folder = MagicMock()
        mock_folder.CanEdit = False

        # Test
        with self.assertRaises(Exception) as cm:
            FolderService.update_folder(session_id, base_url, folder_id, new_name, mock_folder)

        self.assertIn("Permission denied", str(cm.exception))

    def test_handle_move_folder(self) -> None:
        """
        Test handle_move logic for a VirtualFolder representing a Folder.
        """
        # Setup VirtualFolder for a Folder
        environ: Dict[str, Any] = {"filehold.session_id": "sid", "filehold.url": "http://url", "wsgidav.provider": MagicMock()}
        mock_folder = MagicMock()
        mock_folder.CanEdit = True
        mock_folder.Name = "Folder 1"
        mock_folder.Id = 20

        vf = VirtualFolder("/Cab/Drawer/Folder_1", environ, resource_id=20, level=3, soap_object=mock_folder, name="Folder 1")

        destination = "/Cab/Drawer/Folder Renamed"

        with patch('webdav_for_filehold.folder_service.FolderService.update_folder') as mock_update:
            vf.handle_move(destination)

            mock_update.assert_called_once()
            args, _ = mock_update.call_args
            # Args: session_id, base_url, folder_id, new_name, folder_obj
            self.assertEqual(args[2], 20)
            self.assertEqual(args[3], "Folder Renamed")

    def test_update_cabinet_rollback_on_failure(self) -> None:
        """
        Test that cabinet name is restored if update fails.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        cabinet_id = 99
        new_name = "New Name"

        mock_cabinet = MagicMock()
        mock_cabinet.CanEdit = True
        mock_cabinet.Name = "Original Name"

        mock_client = MagicMock()
        # Mock UpdateCabinet to raise Exception
        mock_client.service.UpdateCabinet.side_effect = Exception("SOAP Error")

        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client', return_value=mock_client):
            with self.assertRaises(Exception):
                CabinetService.update_cabinet(session_id, base_url, cabinet_id, new_name, mock_cabinet)

            # Verify name was restored
            self.assertEqual(mock_cabinet.Name, "Original Name")

    def test_update_drawer_rollback_on_failure(self) -> None:
        """
        Test that drawer name is restored if update fails.
        """
        # Setup
        session_id = "test_session"
        base_url = "http://test.com"
        drawer_id = 101
        new_name = "New Drawer Name"

        mock_drawer = MagicMock()
        mock_drawer.CanEdit = True
        mock_drawer.Name = "Original Drawer Name"

        mock_client = MagicMock()
        # Mock UpdateDrawer to raise Exception
        mock_client.service.UpdateDrawer.side_effect = Exception("SOAP Error")

        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client', return_value=mock_client):
            with self.assertRaises(Exception):
                DrawerService.update_drawer(session_id, base_url, drawer_id, new_name, mock_drawer)

            # Verify name was restored
            self.assertEqual(mock_drawer.Name, "Original Drawer Name")


if __name__ == '__main__':
    unittest.main()
