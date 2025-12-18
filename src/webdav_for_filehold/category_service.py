"""
Service for handling Category operations in FileHold.
"""
from typing import Any, Optional, List

from .client_factory import ClientFactory
from .library_object_service import LibraryObjectService


class CategoryService(LibraryObjectService):
    """
    Service for handling Category operations in FileHold.
    """

    @staticmethod
    def get_category_structure(client: Any, drawer_id: int, category_id: int) -> Optional[Any]:
        """
        Retrieves the structure of a specific category, including its folders.

        Args:
            client: The SOAP client to use.
            drawer_id (int): The ID of the drawer containing the category.
            category_id (int): The ID of the category to retrieve.

        Returns:
            Optional[Any]: The category object if found, otherwise None.
        """
        category = client.service.GetCategoryStructure(drawerId=drawer_id, categoryId=category_id)
        if category:
            CategoryService._process_category_folders(category)
        return category

    @staticmethod
    def _process_category_folders(category: Any) -> None:
        """
        Normalizes and processes folders within a category.

        Args:
            category: The category object to process.
        """
        if hasattr(category, 'Folders') and category.Folders:
            folders = category.Folders.Folder if hasattr(category.Folders, 'Folder') else category.Folders

            # Normalize to list
            if not isinstance(folders, list) and folders is not None:
                folders = [folders]  # type: ignore

            if folders:
                CategoryService.process_objects(folders)

    @staticmethod
    def add_category(
        session_id: str,
        base_url: str,
        cabinet_id: int,
        drawer_id: int,  # pylint: disable=unused-argument
        category_name: str
    ) -> Any:
        """
        Adds a new category or finds an existing one.

        Args:
            session_id (str): The session ID for authentication.
            base_url (str): The base URL of the FileHold server.
            cabinet_id (int): The ID of the cabinet.
            drawer_id (int): The ID of the drawer (unused in current SOAP call).
            category_name (str): The name of the category to add.

        Returns:
            Any: The response from the FindOrAddCategory service call.

        Raises:
            Exception: If the category creation fails or no response is received.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            # Note: drawer_id used to be passed to this function but is not used
            # in the FindOrAddCategory call below in the original code.
            # Preserving this behavior.
            response = client.service.FindOrAddCategory(
                cabinetId=cabinet_id,
                categoryName=category_name
            )
            if response:
                return response

            raise Exception("AddCategory returned no response")
        except Exception as e:
            raise Exception(f"Failed to add category '{category_name}' to drawer {drawer_id}: {str(e)}") from e

    @staticmethod
    def remove_category(session_id: str, base_url: str, category_id: int, drawer_id: int) -> bool:
        """
        Removes a category.

        Args:
            session_id (str): The session ID for authentication.
            base_url (str): The base URL of the FileHold server.
            category_id (int): The ID of the category to remove.
            drawer_id (int): The ID of the drawer containing the category.

        Returns:
            bool: True if the removal was successful.

        Raises:
            Exception: If the category removal fails.
        """
        try:
            client = ClientFactory.get_library_structure_manager_client(session_id, base_url)
            client.service.RemoveCategory(
                categoryId=category_id,
                drawerId=drawer_id,
                forceContentRemoval=True
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to remove category {category_id}: {str(e)}") from e
