import unittest
from unittest.mock import MagicMock, patch, call
from webdav_server_for_filehold.document_service import DocumentService

class TestReplaceLogic(unittest.TestCase):
    def test_perform_checkout_logic_success(self):
        # Setup
        doc_client = MagicMock()
        doc_manager = MagicMock()
        soap_object = MagicMock()
        
        # Mock soap_object properties
        soap_object.MetadataVersionId = 123
        soap_object.CheckedOutBy = 0
        soap_object.CanCheckOut = True
        soap_object.IsCheckedOutByMe = False
        
        # Mock _get_search_columns
        mock_fields_wrapper = MagicMock()
        field_def = MagicMock()
        field_def.SystemFieldId = -4
        mock_fields_wrapper.FieldDefinition = [field_def]
        
        with patch.object(DocumentService, '_get_search_columns', return_value=mock_fields_wrapper), \
             patch('webdav_server_for_filehold.document_service.DocumentService._create_single_document_selection', return_value='sel1') as mock_create_selection:
             # Act
             DocumentService._perform_checkout_logic(doc_client, doc_manager, soap_object, snapshot_id="snap1")
             
             # Assert
             # Verify check out happened
             doc_manager.service.CheckOutDocuments.assert_called_with('sel1', True)
             # Verify in-place update
             self.assertEqual(soap_object.CanCheckOut, False)
             self.assertEqual(soap_object.IsCheckedOutByMe, True)
             # Verify snapshot_id passed to selection creation
             mock_create_selection.assert_called_with(doc_manager, soap_object, "snap1")

    def test_perform_checkout_logic_already_checked_out(self):
        # Setup - doc data that is already checked out? 
        # Actually current method takes separate client/manager/soap_object arguments, 
        # but the test logic checks properties on soap_object.
        
        # WE NEED TO BE CAREFUL: DocumentService._perform_checkout_logic logic:
        # if not document_data.IsCheckedOutByMe: ...
        
        doc_client = MagicMock()
        doc_manager = MagicMock()
        soap_object = MagicMock()
        soap_object.IsCheckedOutByMe = True
        
        # Should do nothing
        DocumentService._perform_checkout_logic(doc_client, doc_manager, soap_object)
        
        doc_manager.service.CheckOutDocuments.assert_not_called()

    def test_replace_document_content_flow(self):
        # Setup
        environ = {"filehold.session_id": "sid", "filehold.url": "url"}
        document_data = MagicMock()
        document_data.MetadataVersionId = 999
        document_data.CheckedOutBy = 0
        document_data.CanCheckOut = True
        
        # Wrap doc data
        doc_wrapper = MagicMock()
        doc_wrapper.DocumentData = [document_data]
        doc_wrapper.Columns = MagicMock()

        file_name = "test.txt"
        file_size = 100
        folder_object = MagicMock()
        upload_token = "token"
        
        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_finder_client') as mock_finder_fac, \
             patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_manager_client') as mock_manager_fac, \
             patch.object(DocumentService, '_perform_checkout_logic') as mock_perform_checkout, \
             patch('webdav_server_for_filehold.document_service.DocumentDataService') as mock_dds:
            
            mock_finder = mock_finder_fac.return_value
            mock_manager = mock_manager_fac.return_value
            
            # _perform_checkout_logic returns None
            mock_perform_checkout.return_value = None
            
            # mock DDS
            mock_dds.get_original_file_name_with_extension.return_value = "test.txt"
            mock_dds.get_original_file_name.return_value = "test"
            
            # Act
            result = DocumentService.replace_document_content(
                environ, doc_wrapper, file_name, file_size, folder_object, upload_token, snapshot_id="snap2"
            )
            
            # Assert
            self.assertTrue(result)
            
            # Verify _perform_checkout_logic called with document_data and snapshot_id
            mock_perform_checkout.assert_called_with(mock_finder, mock_manager, document_data, "snap2")
            
            # Verify CheckIn
            mock_manager.service.CheckIn.assert_called()

if __name__ == '__main__':
    unittest.main()
