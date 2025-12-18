import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from webdav_for_filehold.virtual_folder import VirtualFolder


class TestRename(unittest.TestCase):
    """
    Unit tests for renaming logic in VirtualFolder.
    """

    def test_rename_cabinet(self) -> None:
        """
        Test renaming a cabinet via handle_move.
        """
        # Setup
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }

        # Cabinet object
        cabinet_obj = MagicMock()
        cabinet_obj.Name = "Old Name"
        cabinet_obj.Id = 1

        # VirtualFolder for Cabinet (Level 1)
        vf = VirtualFolder("/Old Name", environ, resource_id=1, level=1, soap_object=cabinet_obj)

        # Mock get_library_structure_manager_client
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # Execute renaming to "New Name"
            # wsgidav move_to(dest_parent, new_name)
            # Renaming /Old Name to /New Name
            # dest_parent is "/"

            vf.handle_move("/New Name")

            # Verify UpdateCabinet called
            mock_client.service.UpdateCabinet.assert_called_once()
            call_args = mock_client.service.UpdateCabinet.call_args
            changed_cabinet = call_args[1]['changedCabinet']

            self.assertEqual(changed_cabinet.Name, "New Name")
            self.assertEqual(changed_cabinet.Id, 1)

    def test_rename_not_supported_level(self) -> None:
        """
        Test that renaming fails for unsupported levels.
        """
        environ: Dict[str, Any] = {"wsgidav.provider": MagicMock()}
        vf = VirtualFolder("/Folder", environ, level=3)
        with self.assertRaises(Exception):
            vf.handle_move("/Folder2")


if __name__ == '__main__':
    unittest.main()
