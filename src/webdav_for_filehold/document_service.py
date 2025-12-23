import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

import requests

from .client_factory import ClientFactory
from .columns_with_values import ColumnsWithValues
from .document_data_service import DocumentDataService
from .download_stream import DownloadStream
from .field_definition import FieldDefinition
from .utils import sanitize_name

logger = logging.getLogger(__name__)

ZERO_GUID = "00000000-0000-0000-0000-000000000000"
DEFAULT_CHUNK_SIZE = 50 * 1024 * 1024  # 50MB


class DocumentService:
    @staticmethod
    def get_documents_with_fields(
        session_id: str, base_url: str, folder_id: int
    ) -> Tuple[str, List[ColumnsWithValues]]:
        """
        Retrieves a list of documents in a folder, including selected metadata fields.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            folder_id: The ID of the folder to search.

        Returns:
            A tuple containing the snapshot ID and the result object (List[ColumnsWithValues]).
        """
        try:
            doc_client = ClientFactory.get_document_finder_client(session_id, base_url)

            criteria = DocumentService._build_search_criteria(doc_client, folder_id)
            field_definitions = DocumentService._get_search_columns(doc_client)

            page_size = 200

            initial_result = doc_client.service.GetDocumentsWithFields(
                prevSnapshotId=ZERO_GUID,
                snapshotId=ZERO_GUID,
                viewContainerType="FLD",
                fieldDefinitions=field_definitions,
                searchCriteria=criteria,
                sortOrder=None,
                firstRowIndex=0,
                pageSize=page_size
            )

            result_obj = initial_result.GetDocumentsWithFieldsResult
            snapshot_id = initial_result.snapshotId

            all_document_data = DocumentService._extract_document_data(result_obj)

            total_count = 0
            try:
                total_count = doc_client.service.GetSnapshotDocumentCount(snapshot_id)
            except Exception as e:
                logger.warning(f"Failed to get snapshot document count: {e}")

            if len(all_document_data) < total_count:
                more_data = DocumentService._fetch_document_batch(
                    doc_client,
                    snapshot_id,
                    field_definitions,
                    criteria,
                    page_size,
                    len(all_document_data),
                    total_count
                )
                all_document_data.extend(more_data)

            results_list = []
            if all_document_data:
                # Create list of ColumnsWithValues
                all_columns = result_obj.Columns if result_obj and result_obj.Columns else []
                for doc_data in all_document_data:
                    results_list.append(ColumnsWithValues(all_columns, [doc_data]))

                DocumentService._process_duplicates(results_list)

            return snapshot_id, results_list

        except Exception as e:
            logger.error(f"Error fetching files for folder {folder_id}: {e}")
            raise e

    @staticmethod
    def _fetch_document_batch(
        doc_client: Any,
        snapshot_id: str,
        field_definitions: Any,
        criteria: Any,
        page_size: int,
        start_index: int,
        total_count: int
    ) -> List[Any]:
        """Fetches remaining documents in batches."""
        collected_data = []
        current_index = start_index

        while current_index < total_count:
            next_batch = doc_client.service.GetDocumentsWithFields(
                prevSnapshotId=ZERO_GUID,
                snapshotId=snapshot_id,
                viewContainerType="FLD",
                fieldDefinitions=field_definitions,
                searchCriteria=criteria,
                sortOrder=None,
                firstRowIndex=current_index,
                pageSize=page_size
            )

            batch_data = DocumentService._extract_document_data(next_batch.GetDocumentsWithFieldsResult)
            if not batch_data:
                break

            collected_data.extend(batch_data)
            current_index += len(batch_data)

        return collected_data

    @staticmethod
    def _extract_document_data(result_obj: Any) -> List[Any]:
        """Extracts and normalizes document data from the result object."""
        if not result_obj or not result_obj.DocumentValues:
            return []

        vals = result_obj.DocumentValues
        if hasattr(vals, 'DocumentData') and not isinstance(vals, list):
            vals = vals.DocumentData

        return vals if vals else []

    @staticmethod
    def _build_search_criteria(doc_client: Any, folder_id: int) -> Dict[str, Any]:
        """
        Builds the search criteria for retrieving documents.

        Args:
            doc_client: The Zeep client for document operations.
            folder_id: The ID of the folder to search within.

        Returns:
            A dictionary representing the search criteria.
        """
        
        def create_condition(search_type_val, operator_val, operands_list):
            wrapped_operands = []
            for op in operands_list:
                wrapped_operands.append(ClientFactory.get_any_object(doc_client, op))
            return {
                'SearchType': search_type_val,
                'OperatorType': operator_val,
                'Operands': {'anyType': wrapped_operands}
            }

        return {
            'SearchConditions': {
                'SearchCondition': [
                    create_condition('FolderId', 'Equal', [int(folder_id)]),
                    create_condition('OnlyLastVersion', 'Equal', [True, True]),
                    create_condition('IncludeArchive', 'Equal', [True]),
                    create_condition('DocumentFormat', 'NotEqual', [2]) # OfflineDocument
                ]
            },
            'BooleanSearch': False 
        }

    @staticmethod
    def _get_search_columns(doc_client: Any) -> Any:
        """
        Defines the columns/fields to retrieve from FileHold.

        Args:
            doc_client: The Zeep client for document operations.

        Returns:
            An ArrayOfFieldDefinition containing the columns to retrieve.
        """
        types = doc_client.type_factory('ns0')
        search_columns = [
            FieldDefinition.make_field({'SystemFieldId': -4, 'IsSystem': True, 'MetadataFieldId': 0}),  # DocumentName
            FieldDefinition.make_field({'SystemFieldId': -24, 'IsSystem': True, 'MetadataFieldId': 0}), # FileSize
            FieldDefinition.make_field({'SystemFieldId': -31, 'IsSystem': True, 'MetadataFieldId': 0}), # CreationDate
            FieldDefinition.make_field({'SystemFieldId': -12, 'IsSystem': True, 'MetadataFieldId': 0}), # LastModifiedDate
            FieldDefinition.make_field({'SystemFieldId': -26, 'IsSystem': True, 'MetadataFieldId': 0})  # Owner
        ]
        return types.ArrayOfFieldDefinition(FieldDefinition=search_columns)

    @staticmethod
    def get_large_chunk_size(session_id: str, base_url: str) -> int:
        """
        Retrieves the large chunk size from the RepositoryController.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.

        Returns:
            The configured large chunk size in bytes.

        Raises:
            Exception: If the call fails.
        """
        try:
            client = ClientFactory.get_repository_controller_client(session_id, base_url)
            result = client.service.GetLargeChunkSize()
            return result
        except Exception as e:
            logger.error(f"Error getting large chunk size: {e}")
            raise e

    @staticmethod
    def _insert_suffix(name: str, suffix: str, is_file: bool = True) -> str:
        """
        Inserts a suffix into a filename (before extension) or a string.

        Args:
            name: The original name.
            suffix: The suffix to insert.
            is_file: True if the name is a filename with an extension.

        Returns:
             The modified name with the suffix.
        """
        if is_file:
            base, ext = os.path.splitext(name)
            return f"{base} {suffix}{ext}"
        return f"{name} {suffix}"

    @staticmethod
    def _process_duplicates(results_list: List[ColumnsWithValues]) -> None:
        """
        Detects duplicate document names and appends a suffix (e.g. ' (1)') to disambiguate them.
        This modifies the 'DocumentData' inside ColumnsWithValues in-place.
        """
        grouped = {}
        all_keys = set()
        
        # First pass: Group by name and collect all existing keys
        for item in results_list:
            if not item.DocumentData:
                continue
                
            doc_data = item.DocumentData[0]
            columns = item.Columns.FieldDefinition if item.Columns else []
            
            name = DocumentDataService.get_document_name(doc_data, columns)
            extension = getattr(doc_data, 'Extension', "") or ""
            
            # Ensure name has extension if needed (to match file system view)
            if not name.lower().endswith(extension.lower()):
                name = name + extension
                DocumentDataService.set_document_name(doc_data, columns, name)

            key = sanitize_name(name).lower()
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)
            all_keys.add(key)

        # Second pass: Rename duplicates
        for key, group in grouped.items():
            # Sort by DocumentId to ensure deterministic renaming
            group.sort(key=lambda x: getattr(x.DocumentData[0], 'DocumentId', 0))
            
            for i, item in enumerate(group):
                if i > 0:
                    doc_data = item.DocumentData[0]
                    columns = item.Columns.FieldDefinition if item.Columns else []
                    
                    original_name = DocumentDataService.get_document_name(doc_data, columns)
                    
                    # Search for a unique suffix
                    suffix_index = i
                    while True:
                        suffix = f"({suffix_index})"
                        new_name = DocumentService._insert_suffix(original_name, suffix, is_file=True)
                        new_key = sanitize_name(new_name).lower()
                        
                        if new_key not in all_keys:
                            DocumentDataService.set_document_name(doc_data, columns, new_name)
                            all_keys.add(new_key)
                            break
                        
                        suffix_index += 1

    @staticmethod
    def download_document(
        session_id: str,
        base_url: str,
        metadata_version_id: int,
        file_size: Optional[int] = None
    ) -> Tuple[DownloadStream, int]:
        """
        Prepares a document for download and returns the raw file stream and size.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            metadata_version_id: The metadata version ID of the document.
            file_size: Optional known file size to avoid extra calls.

        Returns:
             A tuple containing the DownloadStream and the file size.

        Raises:
             Exception: If preparation fails.
        """
        try:
            client = ClientFactory.get_document_manager_client(session_id, base_url)
            
            request_body = {
                'metadataVersionId': metadata_version_id,
                'token': ZERO_GUID,
                'fileSize': 0,
                'fileName': None,
                'actionType': 'Downloaded'
            }
            
            response = client.service.PrepareSingleDocumentToDownload(**request_body)
            
            token = response.token
            if file_size is None:
                file_size = response.fileSize
            
            try:
                chunk_size = DocumentService.get_large_chunk_size(session_id, base_url)
            except Exception as e:
                 logger.warning(f"Failed to get large chunk size, using default {DEFAULT_CHUNK_SIZE}: {e}")
                 chunk_size = DEFAULT_CHUNK_SIZE

            return DownloadStream(session_id, base_url, token, file_size, chunk_size), file_size
            
        except Exception as e:
            logger.error(f"Error downloading document version {metadata_version_id}: {e}")
            raise e

    @staticmethod
    def create_upload_token(session_id: str, base_url: str, file_size: int, parent_cabinet_id: int = 0, is_archive: bool = False) -> Tuple[str, int]:
        """Creates an upload token for chunked uploading."""
        repo_client = ClientFactory.get_repository_controller_client(session_id, base_url)
        
        try:
            upload_token_result = repo_client.service.CreateUploadTokenWithChunkSizeForPreferredGroup(
                fileSize=file_size,
                cabinetId=parent_cabinet_id,
                isArchive=is_archive
            )
        except Exception as e:
            logger.error(f"Failed to create upload token Args: fileSize={file_size}, cabinetId={parent_cabinet_id}, isArchive={is_archive}")
            raise Exception(f"Failed to create upload token: {e}")
        
        return upload_token_result.CreateUploadTokenWithChunkSizeForPreferredGroupResult, upload_token_result.chunkSize

    @staticmethod
    def upload_chunk(session_id: str, base_url: str, token: str, chunk: bytes) -> None:
        """
        Uploads a single chunk of data using the provided token.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            token: The upload token.
            chunk: The bytes to upload.

        Raises:
            Exception: If upload fails.
        """
        upload_handler_url = base_url.rstrip('/') + "/DocumentRepository/UploadHandler.ashx"

        files = {'file': ('file', chunk, 'application/octet-stream')}
        params = {'token': token}
        cookies = {'FHLSID': session_id}
        
        try:
             r = requests.post(upload_handler_url, params=params, files=files, cookies=cookies)
             r.raise_for_status()
        except requests.exceptions.RequestException as e:
             error_msg = f"Upload failed. Status: {e.response.status_code if e.response else 'N/A'}. Body: {e.response.text if e.response else 'N/A'}"
             logger.error(f"{error_msg}. URL: {upload_handler_url}")
             raise Exception(error_msg)

    @staticmethod
    def perform_chunked_upload(
        session_id: str,
        base_url: str,
        file_stream: Any,
        file_size: int,
        parent_cabinet_id: int = 0,
        is_archive: bool = False
    ) -> str:
        """
        Uploads a file stream in chunks to the FileHold repository.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            file_stream: The file-like object to read from.
            file_size: Total size of the file.
            parent_cabinet_id: ID of the parent cabinet (optional).
            is_archive: Whether the file is an archive (optional).

        Returns:
            The upload token.
        """
        token, chunk_size = DocumentService.create_upload_token(session_id, base_url, file_size, parent_cabinet_id, is_archive)
        
        file_stream.seek(0)
        uploaded_bytes = 0
        while uploaded_bytes < file_size:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            
            DocumentService.upload_chunk(session_id, base_url, token, chunk)
            uploaded_bytes += len(chunk)
            
        return token

    @staticmethod
    def add_document(
        environ: Dict[str, Any],
        folder_object: Any,
        file_name: str,
        file_size: int,
        upload_token: str
    ) -> Any:
        """
        Adds a new document to a FileHold folder.

        Args:
            environ: WSGI environment containing session/url info.
            folder_object: The target virtual folder/FileHold folder object.
            file_name: The name of the file to add.
            file_size: Size of the file in bytes.
            upload_token: Token from previously uploaded content.

        Returns:
            The result object from AddDocumentInfo.

        Raises:
            Exception: If session is missing/invalid or upload token is missing.
        """
        session_id = environ.get("filehold.session_id")
        base_url = environ.get("filehold.url", "http://localhost/FH/FileHold/")

        if not session_id:
            raise Exception("No session ID found")

        if not upload_token:
            raise Exception("Upload token is required for add_document")

        DocumentService._validate_folder_permissions(folder_object)

        doc_schema_client = ClientFactory.get_document_schema_manager_client(session_id, base_url)
        schema, schema_id = DocumentService._get_and_validate_schema(folder_object, doc_schema_client)

        fields_with_values = DocumentService._prepare_fields_for_add(
            session_id, base_url, folder_object, schema, schema_id, doc_schema_client
        )

        document_info = DocumentService._prepare_document_add_info(
            file_name, upload_token, schema_id, folder_object.Id, fields_with_values
        )

        document_manager_client = ClientFactory.get_document_manager_client(session_id, base_url)
        return document_manager_client.service.AddDocumentInfo(document_info)

    @staticmethod
    def _prepare_document_add_info(
        file_name: str,
        upload_token: str,
        schema_id: int,
        folder_id: int,
        fields_with_values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepares the document info dictionary for adding a document."""
        return {
            'DocumentName': os.path.splitext(file_name)[0],
            'UploadToken': upload_token,
            'DocumentSchemaId': schema_id,
            'OriginalFileName': file_name,
            'FolderId': folder_id,
            'FieldsWithValues': {'FieldWithValue': fields_with_values} if fields_with_values else None,
            'SendEmailToMembers': False,
            'SnapshotId': ZERO_GUID
        }

    @staticmethod
    def _validate_folder_permissions(folder_object: Any) -> None:
        """
        Validates if the user can add documents to the folder.

        Args:
            folder_object: The folder object to check permissions for.

        Raises:
            Exception: If folder is invalid or user lacks permissions.
        """
        if folder_object is None:
             raise Exception("Target directory is not a valid FileHold folder")
        
        can_add = getattr(folder_object, 'CanAddModifyDocument', False)
        if not can_add:
            raise Exception(f"User is not allowed to add document to folder {folder_object.Name} ({folder_object.Id})")

    @staticmethod
    def _get_and_validate_schema(folder_object: Any, doc_schema_client: Any) -> Tuple[Any, int]:
        """
        Retrieves and validates the target schema for the new document.

        Args:
            folder_object: The target folder object.
            doc_schema_client: The Zeep client for schema operations.

        Returns:
            A tuple containing the schema object and the schema ID.

        Raises:
            Exception: If schema cannot be found or is invalid (e.g. Offline type).
        """
        is_auto_tagged = getattr(folder_object, 'IsAutoTagged', False)
        
        if is_auto_tagged and hasattr(folder_object, 'AutoTagging'):
            schema_id = folder_object.AutoTagging.DocumentSchemaId
        else:
            schema_id = getattr(folder_object, 'DefaultSchema', 0)
            
        schema = doc_schema_client.service.GetDocumentSchema(schema_id)
        
        if not schema:
            raise Exception(f"Could not retrieve schema {schema_id}")

        if schema.Type == 'OfflineDocument' or schema.Type == 2:
             raise Exception(f"Cannot add file to folder {folder_object.Name} because default schema is offline type")
             
        # Validate control fields
        if schema.DocumentControlFieldId > 0:
            ctrl_field = doc_schema_client.service.GetDocumentControlField(schema.DocumentControlFieldId)
            if not ctrl_field.IsAutoGenerated:
                 raise Exception("Cannot add file: Document control field is not auto-generated")

        if schema.VersionControlFieldId > 0:
            ver_field = doc_schema_client.service.GetDocumentControlField(schema.VersionControlFieldId)
            if not ver_field.IsAutoGenerated:
                 raise Exception("Cannot add file: Version control field is not auto-generated")
                 
        return schema, schema_id

    @staticmethod
    def _prepare_fields_for_add(
        session_id: str,
        base_url: str,
        folder_object: Any,
        schema: Any,
        schema_id: int,
        doc_schema_client: Any
    ) -> List[Dict[str, Any]]:
        """
        Prepares field values based on autotagging or defaults.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            folder_object: The target folder object.
            schema: The document schema object.
            schema_id: The ID of the schema.
            doc_schema_client: The Zeep client for schema operations.

        Returns:
            A list of field dictionaries for the new document.
        """
        field_definitions = doc_schema_client.service.GetDocumentSchemaFields(schema_id)
        if not field_definitions:
            return []

        is_auto_tagged = getattr(folder_object, 'IsAutoTagged', False)
        auto_tagging_fields = []
        if is_auto_tagged and hasattr(folder_object, 'AutoTagging') and folder_object.AutoTagging:
             at_fields = getattr(folder_object.AutoTagging, 'MetadataFields', None)
             if at_fields and hasattr(at_fields, 'AutoTaggingField'):
                 auto_tagging_fields = at_fields.AutoTaggingField
                 if not isinstance(auto_tagging_fields, list):
                     auto_tagging_fields = [auto_tagging_fields]

        def find_auto_tag(metadata_field_id):
            for at in auto_tagging_fields:
                if at.FieldId == metadata_field_id:
                    return at
            return None

        fields_with_values = []
        doc_manager_client = ClientFactory.get_document_manager_client(session_id, base_url)
        
        # Determine strict timezone
        user_prefs_client = ClientFactory.get_user_preferences_client(session_id, base_url)
        try:
            timezone_id_resp = user_prefs_client.service.GetLocalTimeZoneId()
            timezone_id = getattr(timezone_id_resp, 'GetLocalTimeZoneIdResult', timezone_id_resp)
        except Exception:
            timezone_id = None

        for field_def in field_definitions:
            auto_tag = find_auto_tag(field_def.MetadataFieldId)
            
            if auto_tag:
                 fwv = {
                     'FieldId': auto_tag.FieldId,
                     'FieldValue': ClientFactory.get_any_object(doc_manager_client, auto_tag.Value)
                 }
                 fields_with_values.append(fwv)
            else:
                initial_value = field_def.InitialValue

                if DocumentDataService.is_required(field_def, schema) and DocumentDataService.is_empty(field_def, initial_value):
                     raise Exception(f"Cannot add file because field {field_def.MetadataHeaderText} ({field_def.MetadataFieldId}) is required in default schema and initial value is empty")
                
                # Handle default date formatting logic for 1900-01-01
                if isinstance(initial_value, datetime) and initial_value.year == 1900 and initial_value.month == 1 and initial_value.day == 1:
                     now_utc = datetime.now(timezone.utc)
                     if timezone_id and ZoneInfo:
                         try:
                             tz = ZoneInfo(timezone_id)
                             initial_value = now_utc.astimezone(tz)
                         except Exception as e:
                             logger.warning(f"Could not load timezone {timezone_id}: {e}. using UTC.")
                             initial_value = now_utc
                     else:
                         initial_value = now_utc
                
                fwv = {
                    'FieldId': field_def.MetadataFieldId,
                    'FieldValue': ClientFactory.get_any_object(doc_manager_client, initial_value)
                }
                fields_with_values.append(fwv)
                
        return fields_with_values

    @staticmethod
    def replace_document_content(
        environ: Dict[str, Any],
        document_data: ColumnsWithValues,
        file_name: str,
        file_size: int,
        folder_object: Any,
        upload_token: str,
        snapshot_id: Optional[str] = None
    ) -> bool:
        """
        Checks out an existing document, uploads new content, and checks it in as a new version.

        Args:
            environ: WSGI environment containing session/url info.
            document_data: The existing document's metadata wrapper.
            file_name: The name of the file being uploaded.
            file_size: The size of the file.
            folder_object: The parent folder object.
            upload_token: The upload token.
            snapshot_id: Optional snapshot ID.

        Returns:
            True if successful.

        Raises:
            Exception: If replacement/check-in fails.
        """
        session_id = environ.get("filehold.session_id")
        base_url = environ.get("filehold.url", "http://localhost/FH/FileHold/")
        
        if not session_id:
            raise Exception("No session ID found")
        
        if not upload_token:
             raise Exception("Upload token is required for replace_document_content")
        
        doc_finder = ClientFactory.get_document_finder_client(session_id, base_url)
        document_manager_client = ClientFactory.get_document_manager_client(session_id, base_url)
        
        doc_data = document_data.DocumentData[0] if document_data.DocumentData else None
        fields = document_data.Columns.FieldDefinition if document_data.Columns else []
        
        if not doc_data:
            raise Exception("No document data found in ColumnsWithValues")

        # Checkout if needed
        DocumentService._perform_checkout_logic(doc_finder, document_manager_client, doc_data, snapshot_id)
        
        local_path = DocumentDataService.get_original_file_name_with_extension(doc_data, fields)
        file_name_arg = DocumentDataService.get_original_file_name(doc_data, fields)
        
        try:
            document_manager_client.service.CheckIn(
                uploadToken=upload_token,
                option='CreateNewVersion',
                originalFileName=local_path,
                documentName=file_name_arg,
                metadataVersionId=doc_data.MetadataVersionId,
                sendEmailToMembers=False
            )
        except Exception as e:
            raise Exception(f"Failed to check in document: {e}")
                
        return True

    @staticmethod
    def _perform_checkout_logic(doc_finder: Any, doc_manager: Any, doc_data: Any, snapshot_id: Optional[str] = None) -> None:
        """
        Ensures document is checked out by the current user, performing checkout if needed.

        Args:
            doc_finder: The Zeep client for document finding.
            doc_manager: The Zeep client for document management.
            doc_data: The document data object.
            snapshot_id: Optional snapshot ID.

        Raises:
            Exception: If checkout not possible or owned by another user.
        """
        
        checked_out_by = getattr(doc_data, 'CheckedOutBy', 0) or 0
        can_check_out = getattr(doc_data, 'CanCheckOut', False)
        is_checked_out_by_me = getattr(doc_data, 'IsCheckedOutByMe', False)
        
        # If not checked out, try to check out
        if checked_out_by == 0:
            if not can_check_out:
                raise Exception("Document cannot be checked out (Locked, permissions, or system state)")
            
            try:
                 if snapshot_id is None:
                     snapshot_id = getattr(doc_data, 'SnapshotId', ZERO_GUID)

                 selection_id = DocumentService._create_single_document_selection(doc_manager, doc_data, snapshot_id)
                 doc_manager.service.CheckOutDocuments(selection_id, True)
                 doc_data.CanCheckOut = False
                 doc_data.IsCheckedOutByMe = True
                 doc_data.CheckedOutBy = sys.maxsize
            except Exception as e:
                 raise Exception(f"Failed to checkout document: {e}")
        
        # Verify ownership of checkout
        elif not is_checked_out_by_me:
             raise Exception(f"Document is checked out by another user (Id: {checked_out_by})")

    @staticmethod
    def update_document(session_id: str, base_url: str, dto_object: Any, new_name: str) -> int:
        """
        Updates document metadata, specifically the document name.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            dto_object: The document object to update (e.g. ColumnsWithValues).
            new_name: The new name for the document.

        Returns:
            The new metadata version ID.

        Raises:
            Exception: If update fails or user permission is denied.
        """
        # Unwrap ColumnsWithValues if necessary
        doc_data = dto_object
        if hasattr(dto_object, 'DocumentData') and dto_object.DocumentData:
            doc_data = dto_object.DocumentData[0]

        if not getattr(doc_data, 'CanEdit', True):
            raise Exception(f"User cannot edit document {getattr(doc_data, 'Name', 'Unknown')} ({doc_data.DocumentId})")

        DocumentService._validate_schema_for_update(session_id, base_url, doc_data)

        # Retrieve current details to get all field values
        doc_finder = ClientFactory.get_document_finder_client(session_id, base_url)
        try:
            details = doc_finder.service.GetDocumentDetails(metadataVersionId=doc_data.MetadataVersionId)
        except Exception as e:
            raise Exception(f"Failed to get document details: {e}")

        if not details:
            raise Exception("GetDocumentDetails returned empty response")

        document_manager_client = ClientFactory.get_document_manager_client(session_id, base_url)
        
        fields_with_values = DocumentService._prepare_fields_for_update(details, document_manager_client)

        try:
            extension = getattr(doc_data, 'Extension', '')
            document_name = new_name
            
            if extension and new_name.lower().endswith(extension.lower()):
                document_name = new_name[:-(len(extension))]
                    
            new_metadata_version_id = document_manager_client.service.SetMetadata(
                prevMetadataVersionId=doc_data.MetadataVersionId,
                documentSchemaId=doc_data.DocumentSchemaId,
                documentName=document_name,
                fieldsWithValues={'FieldWithValue': fields_with_values},
                overwritePrevious=False,
                versionNumber=None
            )
            return new_metadata_version_id
        except Exception as e:
            raise Exception(f"Failed to set metadata: {e}")

    @staticmethod
    def _validate_schema_for_update(session_id: str, base_url: str, document_data: Any) -> None:
        """
        Validates schema configuration allows update.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            document_data: The document data object.

        Raises:
            Exception: If schema prevents update (e.g. strict version control).
        """
        version_number = getattr(document_data, 'VersionNumber', None)
        if version_number:
            schema_mgr = ClientFactory.get_document_schema_manager_client(session_id, base_url)
            schema = schema_mgr.service.GetDocumentSchema(document_data.DocumentSchemaId)
            
            if not schema:
                raise Exception(f"Unable to find schema {document_data.DocumentSchemaId}")
                
            if getattr(schema, 'VersionControlFieldId', 0) > 0:
                vc_field = schema_mgr.service.GetVersionControlField(schema.VersionControlFieldId)
                if not vc_field.IsAutoGenerated:
                    raise Exception(f"Version control field {vc_field.Name} ({vc_field.FieldId}) is not auto-generated")

    @staticmethod
    def _prepare_fields_for_update(details: Any, doc_manager_client: Any) -> List[Dict[str, Any]]:
        """
        Maps existing field values to safe transport objects for update.

        Args:
            details: The document details object containing current values.
            doc_manager_client: The Zeep client for document management.

        Returns:
             A list of field dictionaries for the update operation.
        """
        fields_with_values = []
        if details.Columns and details.Columns.FieldDefinition and details.DocumentValues:
            columns = details.Columns.FieldDefinition
            vals = details.DocumentValues
            if hasattr(vals, 'DocumentData') and not isinstance(vals, list):
                vals = vals.DocumentData
            doc_value_data = vals[0]
            
            data_columns = getattr(doc_value_data.DataColumns, 'anyType', []) if doc_value_data.DataColumns else []
            
            for col in columns:
                if col.IsSystem:
                    continue
                    
                idx = col.ColumnIndex
                val = None
                if 0 <= idx < len(data_columns):
                     val = data_columns[idx]
                
                # Handle complex types like Dropdown/Drilldown
                col_type = getattr(col, 'Type', '')
                if col_type == 'DropdownMenu':
                    new_val = []
                    if val and isinstance(val, list):
                        for item in val:
                            item_id = getattr(item, 'Id', None)
                            if item_id is not None:
                                new_val.append(item_id)
                    val = new_val
                elif col_type == 'DrilldownMenu':
                    if val and isinstance(val, list) and len(val) > 0:
                        # Extract the deepest selected child ID
                        current = val[0]
                        while True:
                            children = getattr(current, 'ChildChoices', None)
                            if children and len(children) > 0:
                                current = children[0]
                            else:
                                break
                        val = [getattr(current, 'Id')]
                    else:
                        val = []
                
                fwv = {
                    'FieldId': col.MetadataFieldId,
                    'FieldValue': ClientFactory.get_any_object(doc_manager_client, val)
                }
                fields_with_values.append(fwv)
        return fields_with_values

    @staticmethod
    def _create_single_document_selection(
        doc_manager_client: Any,
        document_data: Any,
        snapshot_id: str
    ) -> str:
        """
        Creates a selection for a single document.

        Args:
            doc_manager_client: The Zeep client.
            document_data: The document data object.
            snapshot_id: Snapshot ID.

        Returns:
            The selection ID string (result of CreateSelection).
        """
        snapshot_selection = {
            'SnapshotId': snapshot_id,
            'MetadataVersionIdList': {'int': [document_data.MetadataVersionId]},
            'DocumentIdList': {'int': [document_data.DocumentId]},
            'ContainsExcluded': False
        }

        selection = {
            'SnapshotSelection': {'SnapshotSelection': [snapshot_selection]}
        }

        create_response = doc_manager_client.service.CreateSelection(selection)
        return create_response

    @staticmethod
    def move_document(
        session_id: str,
        base_url: str,
        document_data: Any,
        target_folder_id: int,
        snapshot_id: Optional[str] = None
    ) -> bool:
        """
        Moves a document to a different folder.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            document_data: The document data object to move.
            target_folder_id: The ID of the destination folder.
            snapshot_id: Optional snapshot ID used for selection.

        Returns:
            True if the move was successful.

        Raises:
            Exception: If the move fails.
        """
        document_manager_client = ClientFactory.get_document_manager_client(session_id, base_url)
        
        # Unwrap ColumnsWithValues if necessary
        doc_data = document_data
        if hasattr(document_data, 'DocumentData') and document_data.DocumentData:
            doc_data = document_data.DocumentData[0]

        try:
            # Create selection for the document to move
            selection_id = DocumentService._create_single_document_selection(
                document_manager_client, 
                doc_data,
                snapshot_id
            )
            
            # Call Move method
            result = document_manager_client.service.Move(selection_id, target_folder_id)
            return result
            
        except Exception as e:
            doc_id = getattr(doc_data, 'DocumentId', 'Unknown')
            logger.error(f"Failed to move document {doc_id} to folder {target_folder_id}: {e}")
            raise Exception(f"Failed to move document: {e}")

    @staticmethod
    def delete_document(session_id: str, base_url: str, document_data: Any, snapshot_id: Optional[str] = None) -> bool:
        """
        Deletes a document (and all its versions) from FileHold.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            document_data: The document data object to delete.
            snapshot_id: Optional snapshot ID.

        Returns:
            True if deletion was successful.

        Raises:
             Exception: If deletion fails or permission denied.
        """
        if not getattr(document_data, 'CanDelete', False):
             raise Exception(f"User cannot delete document {document_data.DocumentId}")

        document_manager_client = ClientFactory.get_document_manager_client(session_id, base_url)
        
        try:
            if snapshot_id is None:
                snapshot_id = getattr(document_data, 'SnapshotId', ZERO_GUID)

            selection_id = DocumentService._create_single_document_selection(document_manager_client, document_data, snapshot_id)
            
            document_manager_client.service.DeleteDocuments(selectionId=selection_id, removeAllVersions=True)
            return True

        except Exception as e:
            raise Exception(f"Failed to delete document {document_data.DocumentId}: {e}")

    @staticmethod
    def parse_document_list(session_id: str, base_url: str, snapshot_id: str, result: Any) -> List[Dict[str, Any]]:
        """
        Parses the result from GetDocumentsWithFields into a list of simplified objects/dicts.

        Args:
            session_id: The user session ID.
            base_url: The FileHold base URL.
            snapshot_id: The snapshot ID associated with the result.
            result: The result object from GetDocumentsWithFields (list of ColumnsWithValues).

        Returns:
             A list of dictionaries representing the documents.
        """

        if not result:
            return []

        # Assuming result is now a List[ColumnsWithValues] or similar structure where we can access Columns
        first_item = result[0] if result else None
        
        name_col_index = -1
        size_col_index = -1
        
        if first_item and first_item.Columns and first_item.Columns.FieldDefinition:
             for col in first_item.Columns.FieldDefinition:
                if col.SystemFieldId == -4:
                    name_col_index = col.ColumnIndex
                elif col.SystemFieldId == -24:
                    size_col_index = col.ColumnIndex

        parsed_docs = []
        for wrapper in result:
            if not wrapper.DocumentData:
                continue
                
            item = wrapper.DocumentData[0]
            # Get name
            doc_name = "Unknown"
            if name_col_index >= 0 and item.DataColumns and len(item.DataColumns.anyType) > name_col_index:
                 doc_name = item.DataColumns.anyType[name_col_index]

            # Get size
            file_size = None
            if size_col_index >= 0 and item.DataColumns and len(item.DataColumns.anyType) > size_col_index:
                try:
                    val = item.DataColumns.anyType[size_col_index]
                    if val is not None:
                        file_size = int(val)
                except ValueError:
                    pass

            doc_info = {
                'name': doc_name,
                'file_size': file_size,
                'dto_object': wrapper,
                'metadata_version_id': getattr(item, 'MetadataVersionId', 0),
                'snapshot_id': snapshot_id or ZERO_GUID
            }
            parsed_docs.append(doc_info)
            
        return parsed_docs

    @staticmethod
    def save_document(
        environ: Dict[str, Any],
        parent_object: Any,
        dto_object: Any,
        name: str,
        file_size: int,
        upload_token: str,
        snapshot_id: Optional[str] = None
    ) -> Any:
        """
        Decides whether to create a new document or update an existing one based on the presence of dto_object.

        Args:
            environ: WSGI environment containing session/url info.
            parent_object: The parent folder object.
            dto_object: Existing document DTO (ColumnsWithValues) for updates, or None for new files.
            name: The name of the file.
            file_size: The size of the file.
            upload_token: The upload token.
            snapshot_id: Optional snapshot ID.

        Returns:
            The result of the add or replace operation.
        """
        if dto_object:
            # Update existing file
            return DocumentService.replace_document_content(
                environ, 
                dto_object, 
                name, 
                file_size, 
                folder_object=parent_object,
                upload_token=upload_token,
                snapshot_id=snapshot_id
            )
        else:
             # Create new file
             return DocumentService.add_document(
                 environ, 
                 parent_object, 
                 name, 
                 file_size, 
                 upload_token=upload_token
             )
