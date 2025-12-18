import unittest
from unittest.mock import MagicMock, patch

from webdav_for_filehold.document_service import DocumentService


class TestUpdateDocument(unittest.TestCase):
    """
    Unit tests for DocumentService.update_document method, focusing on complex field types like DrilldownMenu.
    """

    def test_update_document_drilldown_menu(self) -> None:
        """
        Test updating a document with a DrilldownMenu field.
        """
        # Mock inputs
        session_id = "sess1"
        base_url = "http://host"

        doc_data = MagicMock()
        doc_data.CanEdit = True
        doc_data.DocumentId = 100
        doc_data.DocumentSchemaId = 10
        doc_data.MetadataVersionId = 200
        doc_data.VersionNumber = 1
        doc_data.Extension = ""

        new_name = "MyDoc_Renamed"

        # Mocks for clients
        with patch('webdav_for_filehold.client_factory.ClientFactory.get_document_schema_manager_client') as mock_schema_mgr, \
             patch('webdav_for_filehold.client_factory.ClientFactory.get_document_finder_client') as mock_finder, \
             patch('webdav_for_filehold.client_factory.ClientFactory.get_document_manager_client') as mock_doc_mgr:

            # 1. Schema Manager mocks
            mock_schema_service = mock_schema_mgr.return_value.service
            mock_schema = MagicMock()
            mock_schema.VersionControlFieldId = 0  # Simple case
            mock_schema_service.GetDocumentSchema.return_value = mock_schema

            # 2. Document Finder mocks (GetDocumentDetails)
            mock_finder_service = mock_finder.return_value.service
            mock_details = MagicMock()

            # Fields: System, Name, Drilldown
            f1 = MagicMock(IsSystem=True)
            f2 = MagicMock(IsSystem=False, ColumnIndex=0, MetadataFieldId=11, Type='Text')
            f3 = MagicMock(IsSystem=False, ColumnIndex=1, MetadataFieldId=22, Type='DrilldownMenu')

            mock_details.Columns.FieldDefinition = [f1, f2, f3]

            # Values
            # Column 0: Text "Hello"
            # Column 1: Drilldown list
            # Structure of Drilldown item: {Id, Value, ChildChoices}
            # Deep structure: Root(1) -> Child(2) -> Leaf(3)

            leaf = MagicMock()
            leaf.Id = 333
            leaf.Value = "Leaf"
            leaf.ChildChoices = []

            child = MagicMock()
            child.Id = 222
            child.Value = "Child"
            child.ChildChoices = [leaf]

            root = MagicMock()
            root.Id = 111
            root.Value = "Root"
            root.ChildChoices = [child]

            # Value in DataColumns is a list of choices (usually starting from one root)
            val_drilldown = [root]

            doc_value = MagicMock()
            doc_value.DataColumns.anyType = ["Hello", val_drilldown]

            mock_details.DocumentValues.DocumentData = [doc_value]

            # Make sure response returns details directly (as per logic in model.py lines 475)
            mock_finder_service.GetDocumentDetails.return_value = mock_details

            # 3. Document Manager mocks (SetMetadata)
            mock_doc_mgr_service = mock_doc_mgr.return_value.service
            mock_doc_mgr_service.SetMetadata.return_value = 201  # New version ID

            # Configure type_factory
            mock_factory = MagicMock()
            mock_type = MagicMock(side_effect=lambda x: x)
            mock_factory.ArrayOfInt = mock_type
            mock_doc_mgr.return_value.type_factory.return_value = mock_factory

            # Run
            DocumentService.update_document(session_id, base_url, doc_data, new_name)

            # Verify SetMetadata call
            _, kwargs = mock_doc_mgr_service.SetMetadata.call_args

            self.assertIn('fieldsWithValues', kwargs)
            fwv_wrapper = kwargs['fieldsWithValues']
            self.assertIn('FieldWithValue', fwv_wrapper)
            fields = fwv_wrapper['FieldWithValue']

            # Expecting 2 fields
            # Field 1: Text "Hello". ID 11.
            # Field 2: Drilldown ID 333 (Leaf). ID 22.

            self.assertEqual(len(fields), 2, "Should match 2 non-system fields")

            f_text = next((f for f in fields if f['FieldId'] == 11), None)
            self.assertIsNotNone(f_text)
            self.assertEqual(f_text['FieldValue'].value, "Hello")

            f_drill = next((f for f in fields if f['FieldId'] == 22), None)
            self.assertIsNotNone(f_drill)

            # CRITICAL CHECK: The value should be the INT 333, not a list, not ArrayOfInt object
            # Note: get_any_object wraps int in AnyObject(xsd.Int(), value)
            print(f"Drilldown Value: {f_drill['FieldValue']}")
            self.assertEqual(f_drill['FieldValue'].value, [333])
            self.assertIsInstance(f_drill['FieldValue'].value, list)
