import unittest
from unittest.mock import MagicMock, patch, ANY
from typing import Dict, Any
from webdav_server_for_filehold.upload_stream import UploadStream


class TestUploadStream(unittest.TestCase):
    """
    Unit tests for the UploadStream class used for chunked file uploads.
    """

    def setUp(self) -> None:
        """
        Set up test environment and mocks.
        """
        self.environ: Dict[str, Any] = {
            "filehold.session_id": "sess_id",
            "filehold.url": "http://localhost/FH/FileHold/"
        }
        self.folder_object = MagicMock()
        self.folder_object.ParentCabinetId = 10
        self.folder_object.IsArchive = False

        self.file_name = "test_file.txt"
        self.file_size = 5000  # 5KB

        # Patch DocumentService methods
        self.create_token_patcher = patch('webdav_server_for_filehold.document_service.DocumentService.create_upload_token')
        self.upload_chunk_patcher = patch('webdav_server_for_filehold.document_service.DocumentService.upload_chunk')
        self.add_document_patcher = patch('webdav_server_for_filehold.document_service.DocumentService.add_document')
        self.replace_doc_patcher = patch('webdav_server_for_filehold.document_service.DocumentService.replace_document_content')

        self.mock_create_token = self.create_token_patcher.start()
        self.mock_upload_chunk = self.upload_chunk_patcher.start()
        self.mock_add_document = self.add_document_patcher.start()
        self.mock_replace_doc = self.replace_doc_patcher.start()

        # Defaults
        self.mock_create_token.return_value = ("token_123", 2000)  # 2KB chunk size

    def tearDown(self) -> None:
        """
        Clean up patches.
        """
        self.create_token_patcher.stop()
        self.upload_chunk_patcher.stop()
        self.add_document_patcher.stop()
        self.replace_doc_patcher.stop()

    def test_init_creates_token(self) -> None:
        """
        Test that initialization creates an upload token.
        """
        buf = UploadStream(self.environ, 10, False, self.file_name, self.file_size)

        self.mock_create_token.assert_called_with(
            "sess_id",
            "http://localhost/FH/FileHold/",
            self.file_size,
            10,
            False
        )
        self.assertEqual(buf.upload_token, "token_123")
        self.assertEqual(buf.chunk_size, 2000)

    def test_write_and_flush_chunks(self) -> None:
        """
        Test writing data and auto-flushing chunks when buffer size is exceeded.
        """
        # Chunk size is 2000
        buf = UploadStream(self.environ, 10, False, self.file_name, self.file_size)

        # Write 1500 bytes (no upload yet)
        data1 = b'A' * 1500
        buf.write(data1)
        self.mock_upload_chunk.assert_not_called()
        self.assertEqual(len(buf.buffer), 1500)

        # Write 1000 bytes -> total 2500 -> should upload 2000, keep 500
        data2 = b'B' * 1000
        buf.write(data2)

        self.mock_upload_chunk.assert_called_once()
        args, _ = self.mock_upload_chunk.call_args
        # args: session_id, base_url, token, chunk
        self.assertEqual(args[2], "token_123")
        self.assertEqual(len(args[3]), 2000)

        self.assertEqual(len(buf.buffer), 500)
        self.assertEqual(buf.buffer, b'B' * 500)

        uploaded_chunk = args[3]
        self.assertEqual(uploaded_chunk, b'A' * 1500 + b'B' * 500)

    def test_close_uploads_remaining_and_calls_callback(self) -> None:
        """
        Test closing the stream uploads remaining buffer and calls callback.
        """
        mock_callback = MagicMock()
        buf = UploadStream(self.environ, 10, False, self.file_name, self.file_size, callback=mock_callback)

        buf.write(b'X' * 500)
        buf.close()

        # Should upload the remaining 500 bytes
        self.mock_upload_chunk.assert_called_with(ANY, ANY, "token_123", b'X' * 500)

        # Should call callback with token
        mock_callback.assert_called_with("token_123")

        # Should NOT call add_document directly
        self.mock_add_document.assert_not_called()

    def test_close_calls_callback_if_buffer_empty(self) -> None:
        """
        Test closing stream calls callback even if buffer is empty.
        """
        mock_callback = MagicMock()
        buf = UploadStream(self.environ, 10, False, self.file_name, self.file_size, callback=mock_callback)

        buf.close()

        mock_callback.assert_called_with("token_123")
