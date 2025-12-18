import unittest
from unittest.mock import MagicMock, patch
from webdav_for_filehold.document_service import DocumentService

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
        
        with patch.object(DocumentService, '_get_search_columns', return_value=mock_fields_wrapper):
             # Act
             result_soap, result_fields = DocumentService._perform_checkout_logic(doc_client, doc_manager, soap_object)
             
             # Assert
             self.assertEqual(result_soap, soap_object)
             self.assertEqual(result_fields, mock_fields_wrapper.FieldDefinition)
             doc_manager.service.CheckOutDocument.assert_called_with(123)

    def test_replace_document_content_flow(self):
        # Setup
        environ = {"filehold.session_id": "sid", "filehold.url": "url"}
        document_data = MagicMock()
        document_data.MetadataVersionId = 999
        document_data.CheckedOutBy = 0
        document_data.CanCheckOut = True
        
        file_name = "test.txt"
        file_size = 100
        folder_object = MagicMock()
        upload_token = "token"
        
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_document_finder_client') as mock_finder_fac, \
             patch('webdav_for_filehold.client_factory.ClientFactory.get_document_manager_client') as mock_manager_fac, \
             patch.object(DocumentService, '_perform_checkout_logic') as mock_perform_checkout, \
             patch('webdav_for_filehold.document_service.DocumentDataService') as mock_dds:
            
            mock_finder = mock_finder_fac.return_value
            mock_manager = mock_manager_fac.return_value
            
            # _perform_checkout_logic returns (soap_object, fields)
            mock_perform_checkout.return_value = (document_data, [])
            
            # mock DDS
            mock_dds.get_original_file_name_with_extension.return_value = "test.txt"
            mock_dds.get_original_file_name.return_value = "test"
            
            # Act
            result = DocumentService.replace_document_content(environ, document_data, file_name, file_size, folder_object, upload_token)
            
            # Assert
            self.assertTrue(result)
            
            # Verify _perform_checkout_logic called with document_data
            mock_perform_checkout.assert_called_with(mock_finder, mock_manager, document_data)
            
            # Verify CheckIn
            mock_manager.service.CheckIn.assert_called()

if __name__ == '__main__':
    unittest.main()
