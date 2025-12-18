import logging
from typing import Any, List, Optional, Union

logger = logging.getLogger(__name__)

class DocumentDataService:
    DOCUMENT_NAME_FIELD_ID = -4

    @staticmethod
    def is_empty(field_def: Any, value: Any) -> bool:
        """
        Checks if a field value is effectively empty based on its type.

        Args:
            field_def: The definition of the field (contains 'Type').
            value: The value to check.

        Returns:
            bool: True if the value is considered empty, False otherwise.
        """
        if value is None:
            return True
        
        field_type = getattr(field_def, 'Type', '')
        
        # Combined check for menu types
        if field_type in ('DropdownMenu', 'DrilldownMenu'):
            if isinstance(value, list):
                return len(value) == 0
            return True
            
        return False

    @staticmethod
    def is_required(field_def: Any, schema: Any) -> bool:
        """
        Determines if a field is required within a specific schema.

        Args:
            field_def: The definition of the field/metadata.
            schema: The schema object to check against.

        Returns:
            bool: True if the field is required in the given schema.
        """
        if not schema:
            return False
            
        required_in = getattr(field_def, 'RequiredInSchemas', None)
        if not required_in:
            return False
            
        schema_ids: List[int] = []
        if isinstance(required_in, list):
            schema_ids = required_in
        elif hasattr(required_in, 'int'):
            # Handle cases where it might be a complex object with an 'int' attribute
            schema_ids = getattr(required_in, 'int', [])
        
        if schema_ids is None:
            schema_ids = []

        return schema.Id in schema_ids

    @staticmethod
    def _get_column_index(fields: List[Any], system_field_id: int) -> int:
        """
        Helper to find the column index for a given system field ID.

        Args:
            fields: List of field definitions.
            system_field_id: The system field ID to look for.

        Returns:
            int: The column index if found, otherwise -1.
        """
        for col in fields:
            if col.SystemFieldId == system_field_id:
                return col.ColumnIndex
        return -1

    @staticmethod
    def get_field_value(document_data: Any, fields: List[Any], system_field_id: int) -> Any:
        """
        Extract a value from document_data based on a system field ID.

        Args:
            document_data: The document data object containing DataColumns.
            fields: List of field definitions.
            system_field_id: The ID of the system field to retrieve.

        Returns:
            Any: The value at the found column index, or None if not found/out of bounds.
        """
        col_index = DocumentDataService._get_column_index(fields, system_field_id)
        
        if col_index >= 0 and document_data.DataColumns and len(document_data.DataColumns.anyType) > col_index:
            return document_data.DataColumns.anyType[col_index]
        return None

    @staticmethod
    def get_document_name(document_data: Any, fields: List[Any]) -> str:
        """
        Retrieves the document name using the system field ID -4.

        Args:
            document_data: The document data object.
            fields: List of field definitions.

        Returns:
            str: The document name, or empty string if not found.
        """
        val = DocumentDataService.get_field_value(
            document_data, fields, DocumentDataService.DOCUMENT_NAME_FIELD_ID
        )
        return str(val) if val else ""

    @staticmethod
    def get_original_file_name(document_data: Any, fields: List[Any]) -> str:
        """
        Retrieves the original file name. Falls back to document name if not found.

        Args:
            document_data: The document data object.
            fields: List of field definitions.

        Returns:
            str: The original file name or document name.
        """
        original_name = getattr(document_data, 'OriginalFileName', None)
        return original_name if original_name else DocumentDataService.get_document_name(document_data, fields)

    @staticmethod
    def get_original_file_name_with_extension(document_data: Any, fields: List[Any]) -> str:
        """
        Retrieves the original file name with the correct extension appended (if missing).

        Args:
            document_data: The document data object.
            fields: List of field definitions.

        Returns:
            str: Filename with extension.
        """
        original_name = DocumentDataService.get_original_file_name(document_data, fields)
        extension = getattr(document_data, 'Extension', "")
        if extension and not original_name.endswith(extension):
            return f"{original_name}{extension}"
        return original_name

    @staticmethod
    def set_field_value(document_data: Any, fields: List[Any], system_field_id: int, new_value: Any) -> bool:
        """
        Set a value in document_data based on a system field ID.

        Args:
            document_data: The document data object.
            fields: List of field definitions.
            system_field_id: The system field ID to target.
            new_value: The value to set.

        Returns:
            bool: True if successful, False if column not found or out of bounds.
        """
        col_index = DocumentDataService._get_column_index(fields, system_field_id)
        
        col_index = DocumentDataService._get_column_index(fields, system_field_id)
                
        if col_index >= 0 and document_data.DataColumns and len(document_data.DataColumns.anyType) > col_index:
            document_data.DataColumns.anyType[col_index] = new_value
            return True
        return False

    @staticmethod
    def set_document_name(document_data: Any, fields: List[Any], new_name: str) -> bool:
        """
        Sets the document name using the system field ID -4.

        Args:
            document_data: The document data object.
            fields: List of field definitions.
            new_name: The new name to set.

        Returns:
            bool: True if successful, False otherwise.
        """
        return DocumentDataService.set_field_value(
            document_data, fields, DocumentDataService.DOCUMENT_NAME_FIELD_ID, new_name
        )
