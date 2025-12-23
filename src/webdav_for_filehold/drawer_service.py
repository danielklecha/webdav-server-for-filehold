from typing import Any, List, Optional
from .client_factory import ClientFactory
from .library_object_service import LibraryObjectService

class DrawerService(LibraryObjectService):
    """
    Service for managing Drawer operations in FileHold.
    """

    @staticmethod
    def get_drawer_structure(client: Any, drawer_id: int) -> Optional[Any]:
        """
        Retrieves the structure of a specific drawer, including its folders and categories.

        Args:
            client: The SoapClient instance.
            drawer_id: The ID of the drawer to retrieve.

        Returns:
            The Drawer object if found, otherwise None.
        """
        drawer = client.service.GetDrawerStructure(drawer_id)
        if not drawer:
            return None

        # Process Folders
        if hasattr(drawer, 'Folders') and drawer.Folders:
            folders = DrawerService._get_items_from_collection(drawer.Folders, 'Folder')
            if folders:
                DrawerService.process_objects(folders)

        # Process Categories
        if hasattr(drawer, 'Categories') and drawer.Categories:
            categories = DrawerService._get_items_from_collection(drawer.Categories, 'Category')
            if categories:
                DrawerService.process_objects(categories)

        return drawer

    @staticmethod
    def add_drawer(
        session_id: str,
        base_url: str,
        cabinet_id: int,
        drawer_name: str,
        drawer_description: Optional[str] = None
    ) -> Any:
        """
        Adds a new drawer to a specific cabinet.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.
            cabinet_id: The ID of the parent cabinet.
            drawer_name: The name of the new drawer.
            drawer_description: Optional description for the drawer (currently unused).

        Returns:
            The created Drawer object.

        Raises:
            Exception: If the drawer cannot be added.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)

            new_drawer = {
                # LibraryStructureObject fields
                'Id': 0,
                'Name': drawer_name,
                'Weight': 0,
                'DocumentsCount': 0,
                'IsArchive': False,
                'IsCabinetOwner': False,
                'ParentCabinetId': cabinet_id,
                'Expanded': False,
                'CanEdit': True,
                'ShowEdit': True,
                'CanChangeOwner': False,
                'CanDelete': True,
                'ShowDelete': True,
                'CanCopy': False,
                'ShowCopy': False,
                'CanMove': True,
                'ShowMove': True,
                'CanClone': False,
                'ShowClone': False,
                'CanArchive': False,
                'ShowArchive': False,
                'IsDeleted': False,

                # Drawer fields
                'HasChildren': False,
                'CanAddFolder': True,
                'ShowAddFolder': True,
                'BlockFolderBrowsing': False
            }

            response = client.service.AddDrawer(
                cabinetId=cabinet_id,
                newDrawer=new_drawer
            )

            if response is not None:
                return response
            else:
                raise Exception("AddDrawer returned no response")

        except Exception as e:
            raise Exception(f"Failed to add drawer '{drawer_name}' to cabinet {cabinet_id}: {str(e)}")

    @staticmethod
    def update_drawer(
        session_id: str,
        base_url: str,
        drawer_id: int,
        new_name: str,
        drawer_obj: Any
    ) -> bool:
        """
        Updates the name of an existing drawer.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.
            drawer_id: The ID of the drawer to update.
            new_name: The new name for the drawer.
            drawer_obj: The existing drawer object.

        Returns:
            True if the update was successful.

        Raises:
            Exception: If permission is denied or the update fails.
        """
        if not getattr(drawer_obj, 'CanEdit', True):
            raise Exception("Permission denied: Cannot edit this drawer")

        original_name = drawer_obj.Name
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            # Update the name
            drawer_obj.Name = new_name

            client.service.UpdateDrawer(
                changedDrawer=drawer_obj
            )
            return True
        except Exception as e:
            # Restore original name on failure
            drawer_obj.Name = original_name
            raise Exception(f"Failed to rename drawer {drawer_id} to '{new_name}': {str(e)}")

    @staticmethod
    def remove_drawer(session_id: str, base_url: str, drawer_id: int) -> bool:
        """
        Removes a drawer from the library.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.
            drawer_id: The ID of the drawer to remove.

        Returns:
            True if the removal was successful.

        Raises:
            Exception: If the drawer cannot be removed.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            client.service.RemoveDrawer(drawerId=drawer_id, forceContentRemoval=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to remove drawer {drawer_id}: {str(e)}")

    @staticmethod
    def move_drawer(
        session_id: str,
        base_url: str,
        drawer_id: int,
        dest_cabinet_id: int
    ) -> bool:
        """
        Moves a drawer to a different cabinet.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.
            drawer_id: The ID of the drawer to move.
            dest_cabinet_id: The ID of the destination cabinet.

        Returns:
            True if the move was successful.

        Raises:
            Exception: If the drawer cannot be moved.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            client.service.MoveDrawer(
                drawerId=drawer_id,
                destCabinetId=dest_cabinet_id
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to move drawer {drawer_id} to cabinet {dest_cabinet_id}: {str(e)}")

    @staticmethod
    def _get_items_from_collection(collection_wrapper: Any, item_name: str) -> List[Any]:
        """
        Helper method to extract a list of items from a Zeep array wrapper.

        Args:
            collection_wrapper: The wrapper object (e.g., drawer.Folders).
            item_name: The name of the item property (e.g., 'Folder').

        Returns:
            A list of items.
        """
        if collection_wrapper is None:
            return []

        items = getattr(collection_wrapper, item_name, None) if hasattr(collection_wrapper, item_name) else collection_wrapper

        if items is None:
            return []

        if not isinstance(items, list):
            return [items]

        return items
