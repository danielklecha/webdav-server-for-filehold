from unittest.mock import patch
from io import IOBase
from typing import Any, Optional, Generator
from webdav_for_filehold.download_stream import DownloadStream


class MockResponse:
    """
    Mock response object for requests.get.
    """
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code != 200:
            raise Exception("Mock error")


def test_chunked_read_small_file() -> None:
    """
    Test reading a small file in chunks.
    """
    session_id = "test_session"
    base_url = "http://test/"
    download_token = "token"
    total_size = 100
    chunk_size = 50

    # Mock data source
    full_data = b"x" * 100

    stream = DownloadStream(session_id, base_url, download_token, total_size, chunk_size)

    # Check inheritance
    assert isinstance(stream, IOBase)

    with patch("requests.get") as mock_get:
        # Side effect to return chunks based on params
        def get_side_effect(url: str, params: Optional[dict] = None, **kwargs: Any) -> MockResponse:
            if params and 'offset' in params and 'size' in params:
                offset = int(params['offset'])
                size = int(params['size'])
                end = offset + size
                chunk_data = full_data[offset:end]
                return MockResponse(chunk_data)
            return MockResponse(b"")

        mock_get.side_effect = get_side_effect

        # Test reading all
        result = stream.read()
        assert len(result) == 100
        assert result == full_data

        assert mock_get.call_count == 2  # 0-50, 50-100 (size 50 each)


def test_chunked_read_partial() -> None:
    """
    Test partial reads that may cross chunk boundaries.
    """
    session_id = "test_session"
    base_url = "http://test/"
    download_token = "token"
    total_size = 20
    chunk_size = 10

    full_data = b"01234567890123456789"

    stream = DownloadStream(session_id, base_url, download_token, total_size, chunk_size)

    with patch("requests.get") as mock_get:
        def get_side_effect(url: str, params: Optional[dict] = None, **kwargs: Any) -> MockResponse:
            if params and 'offset' in params and 'size' in params:
                offset = int(params['offset'])
                size = int(params['size'])
                end = offset + size
                chunk_data = full_data[offset:end]
                return MockResponse(chunk_data)
            return MockResponse(b"")
        mock_get.side_effect = get_side_effect

        # Read 5 bytes
        result = stream.read(5)
        assert result == b"01234"
        assert mock_get.call_count == 1

        # Read another 10 bytes (crossing chunk boundary)
        result = stream.read(10)
        assert result == b"5678901234"
        assert mock_get.call_count == 2

        # Read remaining
        result = stream.read()
        assert result == b"56789"


def test_chunked_seek() -> None:
    """
    Test seeking within the stream.
    """
    session_id = "test_session"
    base_url = "http://test/"
    download_token = "token"
    total_size = 100
    chunk_size = 10

    stream = DownloadStream(session_id, base_url, download_token, total_size, chunk_size)

    # Assert initial position
    assert stream.position == 0
    assert stream.tell() == 0

    # Seek to 20
    pos = stream.seek(20)
    assert pos == 20
    assert stream.position == 20
    assert stream.tell() == 20
