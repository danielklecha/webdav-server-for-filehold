import io
import logging
from typing import Dict, Any, Optional, Callable
from .document_service import DocumentService

logger = logging.getLogger(__name__)

class UploadStream(io.BufferedIOBase):
    """
    Handles file upload streaming to FileHold by buffering data and sending it in chunks.
    """

    def __init__(
        self,
        environ: Dict[str, Any],
        parent_cabinet_id: int,
        is_archive: bool,
        file_name: str,
        file_size: int,
        callback: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the upload stream.

        Args:
            environ (Dict[str, Any]): The WSGI environment dictionary.
            parent_cabinet_id (int): ID of the parent cabinet.
            is_archive (bool): Flag indicating if the file is an archive.
            file_name (str): Name of the file being uploaded.
            file_size (int): Total size of the file in bytes.
            callback (Optional[Callable[[str], None]]): Optional callback function to be executed 
                upon successful completion. Receives the upload token as an argument.
        """
        self.environ = environ
        self.file_name = file_name
        self.file_size = file_size
        self.callback = callback
        self.buffer = bytearray()
        
        self.session_id = self.environ.get("filehold.session_id")
        self.base_url = self.environ.get("filehold.url", "http://localhost/FH/FileHold/")
        
        # Initialize upload token immediately
        self.upload_token, self.chunk_size = DocumentService.create_upload_token(
            self.session_id, 
            self.base_url, 
            file_size, 
            parent_cabinet_id, 
            is_archive
        )
        logger.debug(f"Initialized upload for {file_name}. Token: {self.upload_token}, Chunk size: {self.chunk_size}")

    def writable(self) -> bool:
        """
        Return whether the stream supports writing.

        Returns:
            bool: Always True.
        """
        return True

    def write(self, b: bytes) -> int:
        """
        Write bytes to the buffer and upload chunks if buffer size exceeds chunk size.

        Args:
            b (bytes): The data to write.

        Returns:
            int: The number of bytes written.
        """
        self.buffer.extend(b)
        
        while len(self.buffer) >= self.chunk_size:
            chunk = self.buffer[:self.chunk_size]
            self._upload_chunk(chunk)
            self.buffer = self.buffer[self.chunk_size:]
            
        return len(b)

    def _upload_chunk(self, chunk: bytes) -> None:
        """
        Upload a single chunk of data to the service.

        Args:
            chunk (bytes): The data chunk to upload.
        """
        DocumentService.upload_chunk(self.session_id, self.base_url, self.upload_token, chunk)

    def close(self) -> None:
        """
        Flush remaining buffer, execute callback, and close the stream.

        Raises:
            Exception: If the callback execution or upload fails.
        """
        if self.closed:
            return
        
        # Upload remaining data
        if self.buffer:
             self._upload_chunk(self.buffer)
             self.buffer = bytearray()
        
        try:
             if self.callback:
                 self.callback(self.upload_token)
        except Exception as e:
            logger.exception(f"UploadStream close failed for {self.file_name}: {e}")
            raise e
        finally:
            super().close()
