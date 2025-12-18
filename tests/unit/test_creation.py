import unittest
from unittest.mock import MagicMock, patch

from webdav_for_filehold.cabinet_service import CabinetService
from webdav_for_filehold.drawer_service import DrawerService


class TestCreation(unittest.TestCase):
    """
    Unit tests for creation of Cabinets and Drawers.
    """

    def test_add_cabinet_success(self) -> None:
        """
        Test successful addition of a cabinet.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            # Setup successful response
            mock_service.AddCabinet.return_value = 123  # Return ID

            result = CabinetService.add_cabinet(
                "session_id",
                "http://base.url/",
                "My Cabinet",
                "Description",
                owner_guid="11111111-2222-3333-4444-555555555555"
            )

            self.assertEqual(result, 123)
            # Verify called with isArchive and newCabinet object
            _, kwargs = mock_service.AddCabinet.call_args
            self.assertFalse(kwargs['isArchive'])
            self.assertEqual(kwargs['newCabinet']['Name'], "My Cabinet")
            self.assertEqual(kwargs['newCabinet']['Description'], "Description")
            self.assertEqual(kwargs['newCabinet']['IsCabinetOwner'], True)
            self.assertEqual(kwargs['newCabinet']['CanClone'], True)
            self.assertEqual(kwargs['newCabinet']['OwnerGuid'], "11111111-2222-3333-4444-555555555555")

    def test_add_cabinet_fail_no_response(self) -> None:
        """
        Test failure when AddCabinet returns no response.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            # Setup None response
            mock_service.AddCabinet.return_value = None

            with self.assertRaises(Exception) as cm:
                CabinetService.add_cabinet("session_id", "http://base.url/", "My Cabinet")

            self.assertIn("AddCabinet returned no response", str(cm.exception))

    def test_add_drawer_success(self) -> None:
        """
        Test successful addition of a drawer.
        """
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_service = MagicMock()
            mock_get_client.return_value.service = mock_service

            # Setup successful response
            mock_service.AddDrawer.return_value = 456  # Return ID

            result = DrawerService.add_drawer("session_id", "http://base.url/", 123, "My Drawer", "Description")

            self.assertEqual(result, 456)

            # Check arguments
            _, kwargs = mock_service.AddDrawer.call_args
            self.assertEqual(kwargs['cabinetId'], 123)
            self.assertEqual(kwargs['newDrawer']['Name'], "My Drawer")
            self.assertEqual(kwargs['newDrawer']['ParentCabinetId'], 123)
            # Verify new fields
            self.assertEqual(kwargs['newDrawer']['CanClone'], False)
            self.assertEqual(kwargs['newDrawer']['IsDeleted'], False)


if __name__ == '__main__':
    unittest.main()
