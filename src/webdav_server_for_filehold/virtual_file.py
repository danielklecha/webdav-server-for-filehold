import logging
import mimetypes
import os
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union

from wsgidav.dav_provider import DAVNonCollection

from .document_service import DocumentService
from .upload_stream import UploadStream

logger = logging.getLogger(__name__)


class VirtualFile(DAVNonCollection):
    """
    Represents a virtual file in the WebDAV interface, mapping to a FileHold document.
    """

    def __init__(
        self,
        path: str,
        environ: Dict[str, Any],
        name: Optional[str] = None,
        file_size: Optional[int] = None,
        parent_object: Optional[Any] = None,
        dto_object: Optional[Any] = None,
        snapshot_id: Optional[str] = None,
    ):
        """
        Initialize the VirtualFile.

        Args:
            path: The active path to this resource.
            environ: The WSGI environment dictionary.
            name: The file name.
            file_size: The size of the file in bytes.
            parent_object: The parent folder object (if available).
            dto_object: The DocumentData object representing the file metadata.
            snapshot_id: The snapshot ID (optional).
        """
        super().__init__(path, environ)
        self.path = path
        self.name = name
        self.metadata_version_id: Optional[int] = None
        self.file_size = file_size
        self.parent_object = parent_object
        self.dto_object = dto_object
        self.snapshot_id = snapshot_id

    def _get_session_context(self) -> Tuple[Optional[str], str]:
        """
        Retrieve session ID and base URL from the environment.

        Returns:
            A tuple containing (session_id, base_url).
        """
        session_id = self.environ.get("filehold.session_id")
        base_url = self.environ.get("filehold.url", "http://localhost/FH/FileHold/")
        return session_id, base_url

    def begin_write(self, content_type: Optional[str] = None) -> UploadStream:
        """
        Start a write operation (upload).

        Args:
            content_type: The content type of the file being uploaded.

        Returns:
            An UploadStream instance to handle the upload.
        """
        parent_cabinet_id = (
            getattr(self.parent_object, "ParentCabinetId", 0)
            if self.parent_object
            else 0
        )
        is_archive = (
            getattr(self.parent_object, "IsArchive", False)
            if self.parent_object
            else False
        )

        return UploadStream(
            self.environ,
            parent_cabinet_id,
            is_archive,
            self.name,
            file_size=self.file_size,
            callback=self.on_upload_complete,
        )

    def on_upload_complete(self, upload_token: str) -> None:
        """
        Callback triggered when an upload is complete.

        Args:
            upload_token: The token identifying the upload.
        """
        DocumentService.save_document(
            self.environ,
            self.parent_object,
            self.dto_object,
            self.name,
            self.file_size,
            upload_token,
            snapshot_id=self.snapshot_id
        )

    def get_content_length(self) -> Optional[int]:
        """
        Get the content length of the file.

        Returns:
            The size of the file in bytes, or None if unknown.
        """
        return self.file_size

    def get_content_type(self) -> str:
        """
        Get the MIME type of the file.

        Returns:
            The MIME type string.
        """
        if self.name:
            mime_type, _ = mimetypes.guess_type(self.name)
            if mime_type:
                return mime_type
        return "application/octet-stream"

    def get_creation_date(self) -> None:
        """
        Get the creation date of the file.

        Returns:
            None (not implemented).
        """
        return None

    def get_display_name(self) -> str:
        """
        Get the display name of the file.

        Returns:
            The name of the file.
        """
        if self.name:
            return self.name
        return os.path.basename(self.path)

    def get_etag(self) -> None:
        """
        Get the ETag of the file.

        Returns:
            None (not implemented).
        """
        return None

    def get_last_modified(self) -> None:
        """
        Get the last modified timestamp.

        Returns:
            None (not implemented).
        """
        return None

    def support_ranges(self) -> bool:
        """
        Check if range requests are supported.

        Returns:
            False.
        """
        return False

    def support_etag(self) -> bool:
        """
        Check if ETags are supported.

        Returns:
            False.
        """
        return False

    def get_content(self) -> Union[BytesIO, Any]:
        """
        Retrieve the content of the file.

        Returns:
            A file-like object containing the file content.
        """
        session_id, base_url = self._get_session_context()

        if not session_id:
            logger.error("No session ID found in environ")
            return BytesIO(b"")

        # Prioritize local metadata_version_id, then fallback to DTO object
        mv_id = (
            self.metadata_version_id
            if self.metadata_version_id
            else (self.dto_object.MetadataVersionId if self.dto_object else None)
        )

        if not mv_id:
            logger.error("No MetadataVersionId found for file")
            return BytesIO(b"")

        try:
            stream, size = DocumentService.download_document(
                session_id, base_url, mv_id, self.file_size
            )
            # Update file size if it was unknown but returned by service
            if self.file_size is None and size is not None:
                self.file_size = size
            return stream
        except Exception as e:
            logger.error(f"Error downloading file {self.name}: {e}")
            return BytesIO(f"Error: {e}".encode("utf-8"))

    def delete(self) -> None:
        """
        Delete the file.

        Raises:
            Exception: If document data is not available.
        """
        logger.info(f"delete called for {self.path}")
        if not self.dto_object:
            raise Exception("Cannot delete document: Document data not available")

        session_id, base_url = self._get_session_context()

        DocumentService.delete_document(
            session_id, base_url, self.dto_object, snapshot_id=self.snapshot_id
        )

    def handle_move(self, dest_path: str) -> bool:
        """
        Handle a move or rename operation.

        Args:
            dest_path: The destination path.

        Returns:
            True if successful.

        Raises:
            Exception: If moving to a different folder or if document data is missing.
        """
        new_name = os.path.basename(dest_path.rstrip("/"))
        logger.info(
            f"handle_move called for file {self.path}. Dest: {dest_path}, New name: {new_name}"
        )

        current_parent_path = os.path.dirname(self.path.rstrip("/"))
        if current_parent_path == "/":
            current_parent_path = ""

        dest_parent_check = os.path.dirname(dest_path.rstrip("/"))
        if dest_parent_check == "/":
            dest_parent_check = ""

        if current_parent_path != dest_parent_check:
            # Move to different folder
            dest_parent_res = self.provider.get_resource_inst(dest_parent_check, self.environ)
            if not dest_parent_res:
                 raise Exception(f"Destination folder not found: {dest_parent_check}")

            # Check if destination is a Folder (Level 3)
            # Avoiding circular import by checking attribute directly, usually level 3 is Folder
            if not getattr(dest_parent_res, 'level', -1) == 3: # 3 is LEVEL_FOLDER
                 raise Exception("Documents can only be moved to Folders.")
            
            target_folder_id = int(dest_parent_res.resource_id)
            session_id, base_url = self._get_session_context()

            # Perform the move
            DocumentService.move_document(
                session_id, 
                base_url, 
                self.dto_object, 
                target_folder_id, 
                snapshot_id=self.snapshot_id
            )
            
            # If we just moved, valid parent object for the file instance is now stale, 
            # but we are likely about to discard this instance or return success.

        if not self.dto_object:
            raise Exception("Cannot update document: Document data not available")

        session_id, base_url = self._get_session_context()

        if new_name != self.name:
            new_metadata_id = DocumentService.update_document(
                session_id, base_url, self.dto_object, new_name
            )

            if new_metadata_id:
                self.metadata_version_id = new_metadata_id
                self.name = new_name

        return True


    def support_recursive_move(self, dest_path: str) -> bool:
        """
        Check if recursive move is supported.

        Args:
            dest_path: The destination path.

        Returns:
            True always.
        """
        return True

    def move_recursive(self, dest_path: str) -> None:
        """
        Move the file to a new location.

        Args:
            dest_path: The destination path.
        """
        self.handle_move(dest_path)
