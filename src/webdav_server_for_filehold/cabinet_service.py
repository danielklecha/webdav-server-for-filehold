from typing import Any, Dict, List, Optional

from .client_factory import ClientFactory
from .library_object_service import LibraryObjectService

DEFAULT_OWNER_GUID = "00000000-0000-0000-0000-000000000000"


class CabinetService(LibraryObjectService):
    """
    Service class for managing cabinets in FileHold.
    """

    @staticmethod
    def get_tree_structure(client: Any) -> List[Any]:
        """
        Retrieves the cabinet tree structure.

        Args:
            client (Any): The Zeep client for library structure.

        Returns:
            List[Any]: A list of processed cabinet objects.
        """
        result = client.service.GetTreeStructure()
        cabinets = result if result is not None else []
        return CabinetService.process_objects(cabinets)

    @staticmethod
    def get_cabinet_structure(client: Any, cabinet_id: int) -> Optional[Any]:
        """
        Retrieves the structure of a specific cabinet, including its drawers.

        Args:
            client (Any): The Zeep client for library structure.
            cabinet_id (int): The ID of the cabinet.

        Returns:
            Optional[Any]: The cabinet object with its drawers processed, or None if not found.
        """
        cabinet = client.service.GetCabinetStructure(cabinet_id)
        if cabinet:
            CabinetService._process_drawers(cabinet)
        return cabinet

    @staticmethod
    def add_cabinet(
        session_id: str,
        base_url: str,
        cabinet_name: str,
        cabinet_description: Optional[str] = None,
        owner_guid: Optional[str] = None,
        default_schema_name: Optional[str] = None
    ) -> int:
        """
        Adds a new cabinet to the library.

        Args:
            session_id (str): The current session ID.
            base_url (str): The base URL of the FileHold server.
            cabinet_name (str): The name of the new cabinet.
            cabinet_description (Optional[str]): Description for the cabinet. Defaults to None.
            owner_guid (Optional[str]): The GUID of the owner. Defaults to None.
            default_schema_name (Optional[str]): The name of the default schema. Defaults to None.

        Returns:
            int: The ID of the newly created cabinet.

        Raises:
            Exception: If the cabinet cannot be added or no response is received.
        """
        try:
            default_schema_id = CabinetService._resolve_schema_id(
                session_id, base_url, default_schema_name
            )
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)

            new_cabinet = CabinetService._create_cabinet_dto(
                cabinet_name,
                cabinet_description,
                owner_guid,
                default_schema_id
            )

            response = client.service.AddCabinet(
                isArchive=False,
                newCabinet=new_cabinet
            )

            if response is not None:
                return response
            
            raise Exception("AddCabinet returned no response")

        except Exception as e:
            raise Exception(f"Failed to add cabinet '{cabinet_name}': {str(e)}")

    @staticmethod
    def update_cabinet(
        session_id: str,
        base_url: str,
        cabinet_id: int,
        new_name: str,
        cabinet_obj: Any
    ) -> bool:
        """
        Updates the name of an existing cabinet.

        Args:
            session_id (str): The current session ID.
            base_url (str): The base URL of the FileHold server.
            cabinet_id (int): The ID of the cabinet to update.
            new_name (str): The new name for the cabinet.
            cabinet_obj (Any): The existing cabinet object.

        Returns:
            bool: True if the update was successful.

        Raises:
            Exception: If permission is denied or the update fails.
        """
        if not getattr(cabinet_obj, 'CanEdit', True):
            raise Exception("Permission denied: Cannot edit this cabinet")

        original_name = cabinet_obj.Name
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            cabinet_obj.Name = new_name

            client.service.UpdateCabinet(
                changedCabinet=cabinet_obj
            )
            return True
        except Exception as e:
            cabinet_obj.Name = original_name
            raise Exception(f"Failed to rename cabinet {cabinet_id} to '{new_name}': {str(e)}")

    @staticmethod
    def remove_cabinet(session_id: str, base_url: str, cabinet_id: int) -> bool:
        """
        Removes a cabinet from the library.

        Args:
            session_id (str): The current session ID.
            base_url (str): The base URL of the FileHold server.
            cabinet_id (int): The ID of the cabinet to remove.

        Returns:
            bool: True if the removal was successful.

        Raises:
            Exception: If the removal fails.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            client.service.RemoveCabinet(cabinetId=cabinet_id, forceContentRemoval=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to remove cabinet {cabinet_id}: {str(e)}")

    @staticmethod
    def _resolve_schema_id(
        session_id: str,
        base_url: str,
        default_schema_name: Optional[str]
    ) -> int:
        """
        Resolves the schema ID based on the provided schema name.

        Args:
            session_id (str): The current session ID.
            base_url (str): The base URL of the FileHold server.
            default_schema_name (Optional[str]): The name of the default schema.

        Returns:
            int: The schema ID if found, otherwise 0.
        """
        if default_schema_name:
            # Lazy import to avoid potential circular dependency
            from .folder_service import FolderService
            found_id = FolderService.get_schema_id_by_name(session_id, base_url, default_schema_name)
            if found_id:
                return found_id
        return 0

    @staticmethod
    def _create_cabinet_dto(
        cabinet_name: str,
        cabinet_description: Optional[str],
        owner_guid: Optional[str],
        default_schema_id: int
    ) -> Dict[str, Any]:
        """
        Creates the dictionary representation of a Cabinet object for the API.

        Args:
            cabinet_name (str): The name of the cabinet.
            cabinet_description (Optional[str]): The description of the cabinet.
            owner_guid (Optional[str]): The owner's GUID.
            default_schema_id (int): The default schema ID.

        Returns:
            Dict[str, Any]: A dictionary representing the cabinet DTO.
        """
        return {
            # LibraryStructureObject fields
            'Id': 0,
            'Name': cabinet_name,
            'Weight': 0,
            'DocumentsCount': 0,
            'IsArchive': False,
            'IsCabinetOwner': True,
            'ParentCabinetId': 0,
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

            # Cabinet fields
            'Description': cabinet_description or "",
            'DefaultSchema': default_schema_id,
            'HasChildren': False,
            'CanAddFolderGroup': True,
            'CanChangeFolderOwner': True,
            'CanAddDrawer': True,
            'ShowAddDrawer': True,
            'OwnerGuid': owner_guid or DEFAULT_OWNER_GUID,
            'PopulateSecurityPermissions': False
        }

    @staticmethod
    def _process_drawers(cabinet: Any) -> None:
        """
        Helper to process drawers within a cabinet.

        Args:
            cabinet (Any): The cabinet object to process.
        """
        if hasattr(cabinet, 'Drawers') and cabinet.Drawers:
            drawers = cabinet.Drawers.Drawer if hasattr(cabinet.Drawers, 'Drawer') else cabinet.Drawers
            if not isinstance(drawers, list) and drawers is not None:
                drawers = [drawers]
            if drawers:
                CabinetService.process_objects(drawers)
