import pytest
from unittest.mock import MagicMock, patch
from webdav_server_for_filehold.document_service import DocumentService

class MockDocumentData:
    def __init__(self, document_id, name, extension=""):
        self.DocumentId = document_id
        self.Name = name # Simplified internal storage
        self.Extension = extension

class MockColumnsWithValues:
    def __init__(self, doc_data_list):
        self.DocumentData = doc_data_list
        self.Columns = MagicMock()
        self.Columns.FieldDefinition = []

@pytest.fixture
def mock_doc_data_service():
    with patch('webdav_server_for_filehold.document_service.DocumentDataService') as mock:
        def get_name(doc_data, columns):
            return doc_data.Name
            
        def set_name(doc_data, columns, new_name):
            doc_data.Name = new_name
            
        mock.get_document_name.side_effect = get_name
        mock.set_document_name.side_effect = set_name
        yield mock

def test_process_duplicates_basic(mock_doc_data_service):
    # Setup: "test.txt", "test.txt"
    docs_data = [
        MockDocumentData(1, "test.txt", ".txt"),
        MockDocumentData(2, "test.txt", ".txt"),
    ]
    items = [MockColumnsWithValues([d]) for d in docs_data]
    
    DocumentService._process_duplicates(items)
    
    assert docs_data[0].Name == "test.txt"
    assert docs_data[1].Name == "test (1).txt"

def test_process_duplicates_collision_with_existing(mock_doc_data_service):
    # Setup: "test.txt", "test.txt", "test (1).txt"
    # Expected: "test.txt", "test (2).txt", "test (1).txt"
    docs_data = [
        MockDocumentData(1, "test.txt", ".txt"),
        MockDocumentData(2, "test.txt", ".txt"),
        MockDocumentData(3, "test (1).txt", ".txt"),
    ]
    items = [MockColumnsWithValues([d]) for d in docs_data]
    
    DocumentService._process_duplicates(items)
    
    names = {d.DocumentId: d.Name for d in docs_data}
    assert names[1] == "test.txt"
    assert names[2] == "test (2).txt"
    assert names[3] == "test (1).txt"

def test_process_duplicates_triple_collision(mock_doc_data_service):
    # Setup: "test.txt", "test.txt", "test (1).txt", "test (2).txt"
    # Expected: ID 2 should become "test (3).txt"
    docs_data = [
        MockDocumentData(1, "test.txt", ".txt"),
        MockDocumentData(2, "test.txt", ".txt"),
        MockDocumentData(3, "test (1).txt", ".txt"),
        MockDocumentData(4, "test (2).txt", ".txt"),
    ]
    items = [MockColumnsWithValues([d]) for d in docs_data]
    
    DocumentService._process_duplicates(items)
    
    names = {d.DocumentId: d.Name for d in docs_data}
    assert names[1] == "test.txt"
    assert names[2] == "test (3).txt"
    assert names[3] == "test (1).txt"
    assert names[4] == "test (2).txt"

def test_process_duplicates_case_insensitive(mock_doc_data_service):
    # Setup: "test.txt", "TEST.txt"
    # Expected: Grouped as duplicates.
    docs_data = [
        MockDocumentData(1, "test.txt", ".txt"),
        MockDocumentData(2, "TEST.txt", ".txt"),
    ]
    items = [MockColumnsWithValues([d]) for d in docs_data]
    
    DocumentService._process_duplicates(items)
    
    names = {d.DocumentId: d.Name for d in docs_data}
    assert names[1] == "test.txt"
    assert names[2] == "TEST (1).txt" 

def test_multiple_groups(mock_doc_data_service):
    # Setup: "a.txt", "a.txt", "b.txt", "b.txt"
    docs_data = [
        MockDocumentData(1, "a.txt", ".txt"),
        MockDocumentData(2, "a.txt", ".txt"),
        MockDocumentData(3, "b.txt", ".txt"),
        MockDocumentData(4, "b.txt", ".txt"),
    ]
    items = [MockColumnsWithValues([d]) for d in docs_data]
    
    DocumentService._process_duplicates(items)
    
    names = {d.DocumentId: d.Name for d in docs_data}
    assert names[1] == "a.txt"
    assert names[2] == "a (1).txt"
    assert names[3] == "b.txt"
    assert names[4] == "b (1).txt"
