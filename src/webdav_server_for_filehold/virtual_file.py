import logging
import mimetypes
import os
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

from wsgidav.dav_provider import DAVNonCollection

from .document_service import DocumentService
from .document_data_service import DocumentDataService
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
        logger.debug(f"begin_write called for {self.path}, content_type: {content_type}")
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
        logger.debug(f"on_upload_complete called for {self.path}, token: {upload_token}")
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
        logger.debug(f"get_content_length called for {self.path}")
        return self.file_size

    def get_content_type(self) -> str:
        """
        Get the MIME type of the file.

        Returns:
            The MIME type string.
        """
        if self.name:
            logger.debug(f"get_content_type called for {self.path}")
            mime_type, _ = mimetypes.guess_type(self.name)
            if mime_type:
                return mime_type
        return "application/octet-stream"

    def get_creation_date(self) -> Optional[float]:
        """
        Get the creation date of the file.

        Returns:
            The creation timestamp or None.
        """
        logger.debug(f"get_creation_date called for {self.path}")
        if not self.dto_object or not self.dto_object.Columns or not self.dto_object.DocumentData:
            return None

        try:
            fields = self.dto_object.Columns.FieldDefinition
            doc_data = self.dto_object.DocumentData[0]
            
            # SystemFieldId -31 is Creation Date
            val = DocumentDataService.get_field_value(doc_data, fields, -31)
            
            if val and hasattr(val, 'timestamp'):
                return val.timestamp()
                
        except Exception as e:
            logger.error(f"Error getting creation date for {self.path}: {e}")

        return None

    def get_display_name(self) -> str:
        """
        Get the display name of the file.

        Returns:
            The name of the file.
        """
        if self.name:
            logger.debug(f"get_display_name called for {self.path}")
            return self.name
        return os.path.basename(self.path)

    def _get_owner(self) -> Optional[str]:
        """
        Get the owner of the document.

        Returns:
            The name of the owner, or None if not found.
        """
        if not self.dto_object or not self.dto_object.Columns or not self.dto_object.DocumentData:
            return None

        try:
            fields = self.dto_object.Columns.FieldDefinition
            doc_data = self.dto_object.DocumentData[0]

            # SystemFieldId -26 is Owner
            val = DocumentDataService.get_field_value(doc_data, fields, -26)

            if val:
                return str(val)

        except Exception as e:
            logger.error(f"Error getting owner for {self.path}: {e}")

        return None

    def get_property_value(self, name: str) -> Any:
        """
        Get the value of a property.
        
        Args:
            name: The name of the property (e.g. "{DAV:}owner").
            
        Returns:
            The value of the property, or None if not found.
        """
        logger.debug(f"get_property_value called for {self.path}, name: {name}")
        if name == "{DAV:}owner":
            return self._get_owner()
            
        return super().get_property_value(name)

    def get_property_names(self, is_allprop: bool) -> List[str]:
        """
        Get the list of supported property names.
        
        Args:
            is_allprop: True if all properties are requested.
            
        Returns:
            A list of property names.
        """
        prop_names = super().get_property_names(is_allprop=is_allprop)
        if "{DAV:}owner" not in prop_names:
            prop_names.append("{DAV:}owner")
        return prop_names

    def get_etag(self) -> None:
        """
        Get the ETag of the file.

        Returns:
            None (not implemented).
        """
        logger.debug(f"get_etag called for {self.path}")
        return None

    def get_last_modified(self) -> Optional[float]:
        """
        Get the last modified timestamp.

        Returns:
            The last modified timestamp or None.
        """
        logger.debug(f"get_last_modified called for {self.path}")
        if not self.dto_object or not self.dto_object.Columns or not self.dto_object.DocumentData:
            return None

        try:
            fields = self.dto_object.Columns.FieldDefinition
            doc_data = self.dto_object.DocumentData[0]

            # SystemFieldId -12 is Last Modified Date
            val = DocumentDataService.get_field_value(doc_data, fields, -12)

            if val and hasattr(val, 'timestamp'):
                return val.timestamp()

        except Exception as e:
            logger.error(f"Error getting last modified date for {self.path}: {e}")

        return None

    def support_ranges(self) -> bool:
        """
        Check if range requests are supported.

        Returns:
            False.
        """
        logger.debug(f"support_ranges called for {self.path}")
        return False

    def support_etag(self) -> bool:
        """
        Check if ETags are supported.

        Returns:
            False.
        """
        logger.debug(f"support_etag called for {self.path}")
        return False

    def get_content(self) -> Union[BytesIO, Any]:
        """
        Retrieve the content of the file.

        Returns:
            A file-like object containing the file content.
        """
        logger.debug(f"get_content called for {self.path}")
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
        logger.debug(f"delete called for {self.path}")
        if not self.dto_object:
            raise Exception("Cannot delete document: Document data not available")

        session_id, base_url = self._get_session_context()

        DocumentService.delete_document(
            session_id, base_url, self.dto_object, snapshot_id=self.snapshot_id
        )

    def support_recursive_delete(self) -> bool:
        """
        Check if recursive delete is supported.

        Returns:
            True always.
        """
        logger.debug(f"support_recursive_delete called for {self.path}")
        return True

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
        logger.debug(f"handle_move called for {self.path} to {dest_path}")
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
        logger.debug(f"support_recursive_move called for {self.path}")
        return True

    def move_recursive(self, dest_path: str) -> None:
        """
        Move the file to a new location.

        Args:
            dest_path: The destination path.
        """
        logger.debug(f"move_recursive called for {self.path} to {dest_path}")
        self.handle_move(dest_path)
