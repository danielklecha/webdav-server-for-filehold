import logging
from typing import Any, Dict, Optional

from .client_factory import ClientFactory
from .library_object_service import LibraryObjectService

logger = logging.getLogger(__name__)


class FolderService(LibraryObjectService):
    """Service for managing FileHold folders."""

    DEFAULT_OWNER_GUID = "00000000-0000-0000-0000-000000000000"

    @staticmethod
    def get_folder_structure(client: Any, folder_id: int) -> Any:
        """Retrieves the structure of a specific folder.

        Args:
            client: The Zeep client instance.
            folder_id: The unique identifier of the folder.

        Returns:
            The folder structure object.
        """
        return client.service.GetFolderStructure(folderId=folder_id)

    @staticmethod
    def add_folder(
        session_id: str,
        base_url: str,
        drawer_id: int,
        folder_name: str,
        category_id: int = 0,
        description: Optional[str] = None,
        owner_guid: Optional[str] = None,
        default_schema_name: Optional[str] = None
    ) -> Any:
        """Adds a new folder to a drawer.

        Args:
            session_id: The user session ID.
            base_url: The base URL of the FileHold server.
            drawer_id: The ID of the parent drawer.
            folder_name: The name of the new folder.
            category_id: The category ID (default: 0).
            description: Optional description of the folder.
            owner_guid: Optional owner GUID (defaults to system default).
            default_schema_name: Optional name of the default schema.

        Returns:
            The response from the AddFolder service call.

        Raises:
            Exception: If the folder cannot be added.
        """
        try:
            default_schema_id = 0
            if default_schema_name:
                found_id = FolderService.get_schema_id_by_name(
                    session_id, base_url, default_schema_name
                )
                if found_id:
                    default_schema_id = found_id
                    logger.info(
                        "Resolved default schema '%s' to Id: %s",
                        default_schema_name, default_schema_id
                    )
                else:
                    logger.warning(
                        "Default schema '%s' not found. Using default.",
                        default_schema_name
                    )

            client = ClientFactory.get_library_structure_manager_client(
                session_id, base_url
            )

            new_folder = FolderService._create_folder_payload(
                folder_name=folder_name,
                drawer_id=drawer_id,
                category_id=category_id,
                description=description,
                owner_guid=owner_guid,
                default_schema_id=default_schema_id
            )

            response = client.service.AddFolder(
                drawerId=drawer_id,
                newFolder=new_folder
            )

            if response:
                return response
            
            raise Exception("AddFolder returned no response")

        except Exception as e:
            raise Exception(f"Failed to add folder '{folder_name}': {e}") from e

    @staticmethod
    def _create_folder_payload(
        folder_name: str,
        drawer_id: int,
        category_id: int,
        description: Optional[str],
        owner_guid: Optional[str],
        default_schema_id: int
    ) -> Dict[str, Any]:
        """Creates the dictionary payload for a new folder.
        
        Args:
            folder_name: Name of the folder.
            drawer_id: ID of the parent drawer.
            category_id: Category ID.
            description: Description of the folder.
            owner_guid: Owner GUID.
            default_schema_id: Default schema ID.

        Returns:
            A dictionary representing the new folder object.
        """
        return {
            'Id': 0,
            'Name': folder_name,
            'Weight': 0,
            'DocumentsCount': 0,
            'IsArchive': False,
            'IsCabinetOwner': False,
            'ParentCabinetId': 0,  # Will be set by server
            'Expanded': False,
            'CanEdit': True,
            'ShowEdit': True,
            'CanChangeOwner': True,
            'CanDelete': True,
            'ShowDelete': True,
            'CanCopy': True,
            'ShowCopy': True,
            'CanClone': True,
            'ShowClone': True,
            'CanArchive': True,
            'ShowArchive': True,
            'IsDeleted': False,
            # Folder fields
            'CategoryId': category_id,
            'OwnerGuid': owner_guid or FolderService.DEFAULT_OWNER_GUID,
            'HasRestrictedRights': False,
            'Description': description or "",
            'Selected': False,
            'CanAddModifyDocument': True,
            'CanEditReadOnlyFields': True,
            'CanMoveDocumentTo': True,
            'CanMove': True,
            'ShowMove': True,
            'AlertMeOfChanges': False,
            'InheritSecurityPermissions': True,
            'IsAutoTagged': False,
            'DefaultSchema': default_schema_id,
            'IsSchemaInherited': (default_schema_id == 0),
            'Color': 'yellow',
            'DrawerId': drawer_id,
            'BlockFolderBrowsing': False
        }

    @staticmethod
    def update_folder(
        session_id: str,
        base_url: str,
        folder_id: int,
        new_name: str,
        folder_obj: Any
    ) -> bool:
        """Updates an existing folder's name.

        Args:
            session_id: The user session ID.
            base_url: The base URL of the FileHold server.
            folder_id: The ID of the folder to update.
            new_name: The new name for the folder.
            folder_obj: The existing folder object.

        Returns:
            True if successful.

        Raises:
            Exception: If permission is denied or update fails.
        """
        if not getattr(folder_obj, 'CanEdit', True):
            raise Exception("Permission denied: Cannot edit this folder")

        original_name = folder_obj.Name
        try:
            client = ClientFactory.get_library_structure_manager_client(
                session_id, base_url
            )
            # Update the name
            folder_obj.Name = new_name

            client.service.UpdateFolder(changedFolder=folder_obj)
            return True
        except Exception as e:
            # Restore original name on failure
            folder_obj.Name = original_name
            raise Exception(
                f"Failed to rename folder {folder_id} to '{new_name}': {e}"
            ) from e

    @staticmethod
    def remove_folder(session_id: str, base_url: str, folder_id: int) -> bool:
        """Removes a folder.

        Args:
            session_id: The user session ID.
            base_url: The base URL of the FileHold server.
            folder_id: The ID of the folder to remove.

        Returns:
            True if successful.

        Raises:
            Exception: If removal fails.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(
                session_id, base_url
            )
            client.service.RemoveFolder(
                folderId=folder_id,
                forceContentRemoval=True
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to remove folder {folder_id}: {e}") from e

    @staticmethod
    def get_schema_id_by_name(
        session_id: str,
        base_url: str,
        schema_name: str
    ) -> Optional[int]:
        """Resolves a schema name to its ID.

        Args:
            session_id: The user session ID.
            base_url: The base URL of the FileHold server.
            schema_name: The name of the schema to look up.

        Returns:
            The schema ID if found, otherwise None.
        """
        try:
            client = ClientFactory.get_document_schema_manager_client(
                session_id, base_url
            )
            schemas = client.service.GetDocumentSchemasInfoList()

            if not schemas:
                return None

            target = schema_name.lower()
            for schema in schemas:
                if getattr(schema, 'Name', '').lower() == target:
                    return getattr(schema, 'DocumentSchemaId', None)

            return None
        except Exception as e:
            logger.error("Failed to lookup schema %s: %s", schema_name, e)
            return None
