import logging
from io import BytesIO, IOBase
from typing import Optional

import requests
from requests import RequestException

logger = logging.getLogger(__name__)

class DownloadStream(IOBase):
    """
    A read-only stream that fetches file content in chunks from FileHold.

    This class implements the io.IOBase interface for compatibility with
    standard Python file-like object consumers.
    """

    def __init__(
        self,
        session_id: str,
        base_url: str,
        download_token: str,
        total_size: int,
        chunk_size: int
    ):
        """
        Initialize the DownloadStream.

        Args:
            session_id (str): The FileHold session ID.
            base_url (str): The base URL of the FileHold server.
            download_token (str): The download token.
            total_size (int): The total size of the file in bytes.
            chunk_size (int): The size of chunks to request.
        """
        self.session_id: str = session_id
        self.base_url: str = base_url
        self.download_token: str = download_token
        self.total_size: int = total_size
        self.chunk_size: int = chunk_size
        
        # Position refers to the offset of the next byte to be fetched from the server.
        # It represents the end of the data currently held in the buffer.
        self.position: int = 0
        self.buffer: BytesIO = BytesIO()
        self.download_url: str = f"{base_url}DocumentRepository/DownloadHandler.ashx"

    def readable(self) -> bool:
        """Return True if the stream supports reading."""
        return True

    def seekable(self) -> bool:
        """Return True if the stream supports random access."""
        return True

    def read(self, size: int = -1) -> bytes:
        """
        Read up to size bytes from the stream.

        Args:
            size (int): The number of bytes to read. If -1, read all remaining bytes.

        Returns:
            bytes: The read bytes.
        """
        if self.position >= self.total_size:
            # Check if buffer is also exhausted
            if self.buffer.tell() == len(self.buffer.getvalue()):
                return b""

        if size == -1:
            while self.position < self.total_size:
                self._fetch_next_chunk()
            return self.buffer.read()

        current_buffer_pos = self.buffer.tell()
        buffer_len = len(self.buffer.getbuffer())
        available_in_buffer = buffer_len - current_buffer_pos

        while available_in_buffer < size and self.position < self.total_size:
            self._fetch_next_chunk()
            current_buffer_pos = self.buffer.tell()
            buffer_len = len(self.buffer.getbuffer())
            available_in_buffer = buffer_len - current_buffer_pos

        return self.buffer.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Change the stream position.

        Args:
            offset (int): The offset to move to.
            whence (int): The reference point (0=start, 1=current, 2=end).

        Returns:
            int: The new absolute position.
        """
        if whence == 0:
            new_pos = offset
        elif whence == 1:
            buffer_len = len(self.buffer.getvalue())
            buffer_start = self.position - buffer_len
            current_abs_pos = buffer_start + self.buffer.tell()
            new_pos = current_abs_pos + offset
        elif whence == 2:
            new_pos = self.total_size + offset
        else:
            raise ValueError(f"Invalid whence: {whence}")

        new_pos = max(0, min(new_pos, self.total_size))

        # Check if new_pos is within the current buffer window
        buffer_len = len(self.buffer.getvalue())
        buffer_start = self.position - buffer_len

        if buffer_start <= new_pos <= self.position:
            self.buffer.seek(new_pos - buffer_start)
        else:
            # Target is outside buffer; reset buffer and move download pointer
            self.position = new_pos
            self.buffer = BytesIO()
        
        return new_pos

    def _fetch_next_chunk(self) -> None:
        """
        Fetch the next chunk of data from the server and append it to the buffer.
        """
        if self.position >= self.total_size:
            return

        end_pos = min(self.position + self.chunk_size, self.total_size)
        current_chunk_size = end_pos - self.position

        params = {
            'token': self.download_token,
            'offset': self.position,
            'size': current_chunk_size
        }
        cookies = {'FHLSID': self.session_id}

        try:
            response = requests.get(self.download_url, params=params, cookies=cookies)
            response.raise_for_status()
            
            chunk_data = response.content
            
            # Preserve unread data from current buffer
            unread_data = self.buffer.read()

            self.buffer = BytesIO()
            self.buffer.write(unread_data)
            self.buffer.write(chunk_data)
            self.buffer.seek(0)

            self.position = end_pos

        except RequestException as e:
            logger.error(f"Error fetching chunk {self.position}-{end_pos}: {e}")
            raise

    def close(self) -> None:
        """Close the stream and release resources."""
        self.buffer.close()
        super().close()
