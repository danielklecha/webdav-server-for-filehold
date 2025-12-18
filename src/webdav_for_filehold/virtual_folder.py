import logging
import os
from typing import Any, Dict, List, Optional, Union

from wsgidav.dav_provider import DAVCollection
from wsgidav.util import join_uri

from .cabinet_service import CabinetService
from .category_service import CategoryService
from .client_factory import ClientFactory
from .document_service import DocumentService
from .drawer_service import DrawerService
from .folder_service import FolderService
from .utils import sanitize_name
from .virtual_file import VirtualFile

logger = logging.getLogger(__name__)


class VirtualFolder(DAVCollection):
    """
    Represents a folder-like object in the WebDAV hierarchy (e.g., Root, Cabinet, Drawer, Folder, Category).
    """

    LEVEL_ROOT = 0
    LEVEL_CABINET = 1
    LEVEL_DRAWER = 2
    LEVEL_FOLDER = 3
    LEVEL_CATEGORY = 4

    def __init__(
        self,
        path: str,
        environ: Dict[str, Any],
        resource_id: Optional[Union[str, int]] = None,
        level: int = 0,
        soap_object: Optional[Any] = None,
        name: Optional[str] = None,
        parent_resource_id: Optional[Union[str, int]] = None,
    ):
        """
        Initializes a VirtualFolder.

        Args:
            path: The virtual path of the folder.
            environ: WSGI environment.
            resource_id: FileHold ID of the object.
            level: Hierarchy level (0=Root, 1=Cabinet, 2=Drawer, 3=Folder, 4=Category).
            soap_object: The SOAP object representing this folder (optional).
            name: Display name.
            parent_resource_id: resource_id of the parent (used for Categories).
        """
        super().__init__(path, environ)
        self.path = path
        self.resource_id = resource_id
        self.level = level
        self.dto_object = soap_object
        self.name = name
        self.parent_resource_id = parent_resource_id

    def get_display_name(self) -> str:
        """
        Returns the display name of the folder.

        Returns:
            The name of the folder, or an empty string if it is the root.
        """
        if self.name:
            return self.name
        if self.path == "/":
            return ""
        return os.path.basename(self.path)

    def get_member_list(self) -> List[Union["VirtualFolder", VirtualFile]]:
        """
        Returns a list of children (VirtualFolder or VirtualFile) for this collection.
        Fetching depends on the current level in the hierarchy.

        Returns:
            A list of child resources.
        """
        session_id = self.environ.get("filehold.session_id")
        base_url = self.environ.get("filehold.url", "http://localhost/FH/FileHold/")

        if not session_id:
            logger.error("No session ID found in environ")
            return []

        try:
            client = ClientFactory.get_library_structure_manager_client(
                session_id, base_url
            )

            self._refresh(client)

            if self.level == self.LEVEL_FOLDER:
                return self._get_documents(session_id, base_url)

            if self.level == self.LEVEL_ROOT:
                return self._get_cabinets(client)

            elif self.level == self.LEVEL_CABINET:
                return self._get_drawers(client)

            elif self.level == self.LEVEL_DRAWER:
                return self._get_drawer_contents(client)

            elif self.level == self.LEVEL_CATEGORY:
                return self._get_category_contents(client)

        except Exception as e:
            logger.error(f"Error fetching members for {self.path}: {e}")
            return []

        return []

    def delete(self) -> None:
        """
        Deletes the current collection from FileHold.

        Raises:
            Exception: If no session ID is found or if deletion fails.
        """
        session_id = self.environ.get("filehold.session_id")
        base_url = self.environ.get("filehold.url", "http://localhost/FH/FileHold/")

        if not session_id:
            raise Exception("No session ID found")

        if self.level == self.LEVEL_CABINET:
            CabinetService.remove_cabinet(session_id, base_url, self.resource_id)
        elif self.level == self.LEVEL_DRAWER:
            DrawerService.remove_drawer(session_id, base_url, self.resource_id)
        elif self.level == self.LEVEL_FOLDER:
            FolderService.remove_folder(session_id, base_url, self.resource_id)
        elif self.level == self.LEVEL_CATEGORY:
            if not self.parent_resource_id:
                raise Exception("Cannot delete category without parent drawer ID")
            CategoryService.remove_category(
                session_id, base_url, self.resource_id, self.parent_resource_id
            )
        else:
            raise Exception(f"Deletion not supported for level {self.level}")

    def _refresh(self, client: Any) -> None:
        """
        Refreshes the internal FileHold object structure if necessary.

        Args:
            client: The SOAP client instance.
        """
        try:
            if self.level == self.LEVEL_CABINET:
                self._refresh_cabinet(client)
            elif self.level == self.LEVEL_DRAWER:
                self._refresh_drawer(client)
            elif self.level == self.LEVEL_FOLDER:
                self._refresh_folder(client)
            elif self.level == self.LEVEL_CATEGORY:
                self._refresh_category(client)
        except Exception as e:
            logger.error(f"Error refreshing object for {self.path}: {e}")

    def _refresh_cabinet(self, client: Any) -> None:
        """Helper to refresh cabinet structure."""
        current_filehold_object = self.dto_object
        need_fetch = False

        if not current_filehold_object:
            need_fetch = True
        else:
            drawers = getattr(current_filehold_object, "Drawers", None)
            drawers_empty = not drawers
            has_children = getattr(current_filehold_object, "HasChildren", False)

            if not hasattr(current_filehold_object, "Drawers"):
                if has_children:
                    need_fetch = True
            elif drawers_empty and has_children:
                need_fetch = True

        if need_fetch:
            self.dto_object = CabinetService.get_cabinet_structure(
                client, self.resource_id
            )

    def _refresh_drawer(self, client: Any) -> None:
        """Helper to refresh drawer structure."""
        drawer_struct = self.dto_object
        need_fetch = False

        if not drawer_struct:
            need_fetch = True
        else:
            folders = getattr(drawer_struct, "Folders", None)
            categories = getattr(drawer_struct, "Categories", None)
            is_empty = (not folders) and (not categories)
            has_children = getattr(drawer_struct, "HasChildren", False)

            if is_empty and has_children:
                need_fetch = True

        if need_fetch:
            self.dto_object = DrawerService.get_drawer_structure(
                client, self.resource_id
            )

    def _refresh_folder(self, client: Any) -> None:
        """Helper to refresh folder structure."""
        folder_obj = self.dto_object
        need_fetch = False

        if not folder_obj:
            need_fetch = True
        else:
            is_auto_tagged = getattr(folder_obj, "IsAutoTagged", False)
            auto_tagging = getattr(folder_obj, "AutoTagging", None)

            if is_auto_tagged and not auto_tagging:
                need_fetch = True

        if need_fetch:
            self.dto_object = FolderService.get_folder_structure(
                client, self.resource_id
            )

    def _refresh_category(self, client: Any) -> None:
        """Helper to refresh category structure."""
        category_obj = self.dto_object
        need_fetch = False

        if not category_obj:
            need_fetch = True
        else:
            folders = getattr(category_obj, "Folders", None)
            has_children = getattr(category_obj, "HasChildren", False)

            if not folders and has_children:
                need_fetch = True

        if need_fetch and self.parent_resource_id:
            self.dto_object = CategoryService.get_category_structure(
                client, self.parent_resource_id, self.resource_id
            )

    def _get_cabinets(self, client: Any) -> List["VirtualFolder"]:
        """Fetches and returns the list of cabinets."""
        cabinets = CabinetService.get_tree_structure(client)
        if not cabinets:
            return []

        results = []
        for cabinet in cabinets:
            name = cabinet.Name
            new_path = join_uri(self.path, sanitize_name(name))
            results.append(
                VirtualFolder(
                    new_path,
                    self.environ,
                    resource_id=cabinet.Id,
                    level=self.LEVEL_CABINET,
                    soap_object=cabinet,
                    name=name,
                )
            )

        return results

    def _get_drawers(self, client: Any) -> List["VirtualFolder"]:
        """Fetches and returns the list of drawers in the current cabinet."""
        current_filehold_object = self.dto_object

        if (
            current_filehold_object
            and hasattr(current_filehold_object, "Drawers")
            and current_filehold_object.Drawers
        ):
            drawers_list = []
            if hasattr(current_filehold_object.Drawers, "Drawer"):
                drawers_list = current_filehold_object.Drawers.Drawer
            elif isinstance(current_filehold_object.Drawers, list):
                drawers_list = current_filehold_object.Drawers
            if not isinstance(drawers_list, list) and drawers_list is not None:
                drawers_list = [drawers_list]

            results = []
            if drawers_list:
                for drawer in drawers_list:
                    name = drawer.Name
                    new_path = join_uri(self.path, sanitize_name(name))
                    results.append(
                        VirtualFolder(
                            new_path,
                            self.environ,
                            resource_id=drawer.Id,
                            level=self.LEVEL_DRAWER,
                            soap_object=drawer,
                            name=name,
                        )
                    )
            return results
        return []

    def _get_drawer_contents(self, client: Any) -> List["VirtualFolder"]:
        """Fetches and returns folders and categories within the current drawer."""
        drawer_struct = self.dto_object

        results = []

        # Process Folders
        if (
            drawer_struct
            and hasattr(drawer_struct, "Folders")
            and drawer_struct.Folders
        ):
            folders_list = []
            if hasattr(drawer_struct.Folders, "Folder"):
                folders_list = drawer_struct.Folders.Folder
            elif isinstance(drawer_struct.Folders, list):
                folders_list = drawer_struct.Folders

            if not isinstance(folders_list, list) and folders_list is not None:
                folders_list = [folders_list]

            if folders_list:
                for folder in folders_list:
                    name = folder.Name
                    new_path = join_uri(self.path, sanitize_name(name))
                    results.append(
                        VirtualFolder(
                            new_path,
                            self.environ,
                            resource_id=folder.Id,
                            level=self.LEVEL_FOLDER,
                            soap_object=folder,
                            name=name,
                        )
                    )

        # Process Categories
        if (
            drawer_struct
            and hasattr(drawer_struct, "Categories")
            and drawer_struct.Categories
        ):
            categories_list = []
            if hasattr(drawer_struct.Categories, "Category"):
                categories_list = drawer_struct.Categories.Category
            elif isinstance(drawer_struct.Categories, list):
                categories_list = drawer_struct.Categories

            if not isinstance(categories_list, list) and categories_list is not None:
                categories_list = [categories_list]

            if categories_list:
                for category in categories_list:
                    cat_id = (
                        category.CategoryId
                        if hasattr(category, "CategoryId")
                        else category.Id
                    )
                    name = category.Name
                    new_path = join_uri(self.path, sanitize_name(name))
                    results.append(
                        VirtualFolder(
                            new_path,
                            self.environ,
                            resource_id=cat_id,
                            level=self.LEVEL_CATEGORY,
                            soap_object=category,
                            name=name,
                            parent_resource_id=int(self.resource_id),
                        )
                    )

        return results

    def _get_category_contents(self, client: Any) -> List["VirtualFolder"]:
        """Fetches and returns folders within the current category."""
        if (
            self.dto_object
            and hasattr(self.dto_object, "Folders")
            and self.dto_object.Folders
        ):
            folders_list = []
            # Note: The original code used `self.filehold_object` in one branch, assume `self.dto_object` was intended based on context
            if hasattr(self.dto_object.Folders, "Folder"):
                folders_list = self.dto_object.Folders.Folder
            elif isinstance(self.dto_object.Folders, list):
                folders_list = self.dto_object.Folders

            if not isinstance(folders_list, list) and folders_list is not None:
                folders_list = [folders_list]

            results = []
            if folders_list:
                for folder in folders_list:
                    name = folder.Name
                    new_path = join_uri(self.path, sanitize_name(name))
                    results.append(
                        VirtualFolder(
                            new_path,
                            self.environ,
                            resource_id=folder.Id,
                            level=self.LEVEL_FOLDER,
                            soap_object=folder,
                            name=name,
                        )
                    )

            return results
        return []

    def _get_documents(
        self, session_id: str, base_url: str
    ) -> List[VirtualFile]:
        """Fetches and returns files within the current folder."""
        try:
            snapshot_id, result = DocumentService.get_documents_with_fields(
                session_id, base_url, self.resource_id
            )

            if result:
                parsed_list = DocumentService.parse_document_list(
                    session_id, base_url, snapshot_id, result
                )

                results = []
                for doc in parsed_list:
                    new_path = join_uri(self.path, sanitize_name(doc["name"]))
                    v_file = VirtualFile(
                        new_path,
                        self.environ,
                        name=doc["name"],
                        file_size=doc["file_size"],
                        parent_object=self.dto_object,
                        dto_object=doc["dto_object"],
                        snapshot_id=doc["snapshot_id"],
                    )
                    v_file.metadata_version_id = doc["metadata_version_id"]
                    results.append(v_file)

                return results

        except Exception as e:
            logger.error(f"Error fetching files for {self.path}: {e}")
            return []

        return []

    def get_member_names(self) -> List[str]:
        """
        Returns a list of member names.

        Returns:
            List of names of child resources.
        """
        return [r.get_display_name() for r in self.get_member_list()]

    def _create_folder_with_schema(
        self,
        name: str,
        session_id: str,
        base_url: str,
        parent_id: Union[str, int],
        category_id: Union[str, int] = 0,
    ) -> None:
        """
        Helper to create a folder.
        """
        owner_guid = self.environ.get("filehold.user_guid")
        default_schema_name = self.environ.get("filehold.default_schema_name")

        FolderService.add_folder(
            session_id,
            base_url,
            parent_id,
            name,
            category_id=category_id,
            owner_guid=owner_guid,
            default_schema_name=default_schema_name,
        )

    def _create_cabinet(self, name: str, session_id: str, base_url: str) -> bool:
        """
        Creates a new Cabinet.
        """
        try:
            owner_guid = self.environ.get("filehold.user_guid")
            default_schema_name = self.environ.get("filehold.default_schema_name")

            CabinetService.add_cabinet(
                session_id,
                base_url,
                name,
                owner_guid=owner_guid,
                default_schema_name=default_schema_name,
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to create cabinet: {str(e)}")

    def _create_drawer(self, name: str, session_id: str, base_url: str) -> bool:
        """
        Creates a new Drawer in the current Cabinet.
        """
        try:
            DrawerService.add_drawer(session_id, base_url, self.resource_id, name)

            if self.dto_object:
                if hasattr(self.dto_object, "Drawers"):
                    self.dto_object.Drawers = None
                setattr(self.dto_object, "HasChildren", True)

            return True
        except Exception as e:
            raise Exception(f"Failed to create drawer: {str(e)}")

    def _create_in_drawer(self, name: str, session_id: str, base_url: str) -> bool:
        """
        Creates a new Folder (or Category, if configured) in the current Drawer.
        """
        try:
            create_category = self.environ.get(
                "filehold.create_category_in_drawer", False
            )

            if create_category:
                parent_cabinet_id = (
                    self.dto_object.ParentCabinetId
                    if self.dto_object
                    and hasattr(self.dto_object, "ParentCabinetId")
                    else 0
                )
                CategoryService.add_category(
                    session_id, base_url, parent_cabinet_id, self.resource_id, name
                )
            else:
                self._create_folder_with_schema(
                    name, session_id, base_url, self.resource_id
                )

            if self.dto_object:
                if hasattr(self.dto_object, "Categories"):
                    self.dto_object.Categories = None
                if hasattr(self.dto_object, "Folders"):
                    self.dto_object.Folders = None
                setattr(self.dto_object, "HasChildren", True)
            return True
        except Exception as e:
            raise Exception(f"Failed to create directory in drawer: {str(e)}")

    def _create_in_category(self, name: str, session_id: str, base_url: str) -> bool:
        """
        Creates a new Folder in the current Category.
        """
        try:
            if not self.parent_resource_id:
                raise Exception("Cannot create folder: Parent drawer ID is missing")

            self._create_folder_with_schema(
                name,
                session_id,
                base_url,
                self.parent_resource_id,
                category_id=self.resource_id,
            )

            if self.dto_object:
                if hasattr(self.dto_object, "Folders"):
                    self.dto_object.Folders = None
                setattr(self.dto_object, "HasChildren", True)

            return True
        except Exception as e:
            raise Exception(f"Failed to create folder in category: {str(e)}")

    def create_collection(self, name: str) -> bool:
        """
        Creates a new collection (Cabinet, Drawer, Folder, or Category) inside this collection.
        Delegates to specific helper methods based on hierarchy level.

        Args:
            name: Name of the new collection.

        Returns:
            True if creation was successful.

        Raises:
            Exception: If creation fails or is not supported.
        """
        session_id = self.environ.get("filehold.session_id")
        base_url = self.environ.get("filehold.url", "http://localhost/FH/FileHold/")

        if not session_id:
            raise Exception("No session ID found in environ")

        if self.level == self.LEVEL_ROOT:
            return self._create_cabinet(name, session_id, base_url)

        elif self.level == self.LEVEL_CABINET:
            return self._create_drawer(name, session_id, base_url)

        elif self.level == self.LEVEL_DRAWER:
            return self._create_in_drawer(name, session_id, base_url)

        elif self.level == self.LEVEL_CATEGORY:
            return self._create_in_category(name, session_id, base_url)

        else:
            raise Exception(f"Creating collections is not supported at level {self.level}")

    def create_empty_resource(self, name: str) -> VirtualFile:
        """
        Creates an empty resource (file) in the current collection.

        Args:
            name: Name of the file.

        Returns:
            The created VirtualFile object.

        Raises:
            Exception: If the current level allows file creation or if operation fails.
        """
        if self.level != self.LEVEL_FOLDER:
            raise Exception("Files can only be added to Folders")

        content_length = self.environ.get("CONTENT_LENGTH")

        try:
            file_size = int(content_length) if content_length else 0
        except Exception:
            file_size = 0

        new_path = join_uri(self.path, name)
        return VirtualFile(
            new_path,
            self.environ,
            name=name,
            file_size=file_size,
            parent_object=self.dto_object,
        )

    def handle_move(self, dest_path: str) -> bool:
        """
        Handles moving (renaming) of this collection.
        Currently only supports renaming within the same parent (Move to same parent).

        Args:
            dest_path: The destination path.

        Returns:
            True if the move was successful.

        Raises:
            Exception: If the move is invalid or fails.
        """
        new_name = os.path.basename(dest_path.rstrip("/"))
        logger.info(
            f"handle_move called for {self.path}. Dest path: {dest_path}, New name: {new_name}"
        )

        current_parent_path = os.path.dirname(self.path.rstrip("/"))
        if current_parent_path == "/":
            current_parent_path = ""

        dest_parent_check = os.path.dirname(dest_path.rstrip("/"))
        if dest_parent_check == "/":
            dest_parent_check = ""

        is_rename = dest_parent_check == current_parent_path

        if not is_rename:
            logger.warning(
                f"Move rejected: dest_path={dest_path}, current_parent={current_parent_path}"
            )
            raise Exception("Moving objects to different parents is not supported yet.")

        session_id = self.environ.get("filehold.session_id")
        base_url = self.environ.get("filehold.url", "http://localhost/FH/FileHold/")

        if self.level == self.LEVEL_CABINET:
            try:
                logger.info(
                    f"Renaming cabinet {self.resource_id} from {self.name} to {new_name}"
                )
                CabinetService.update_cabinet(
                    session_id,
                    base_url,
                    self.resource_id,
                    new_name,
                    self.dto_object,
                )
                return True
            except Exception as e:
                raise Exception(f"Failed to rename cabinet: {e}")

        elif self.level == self.LEVEL_DRAWER:
            try:
                logger.info(
                    f"Renaming drawer {self.resource_id} from {self.name} to {new_name}"
                )
                DrawerService.update_drawer(
                    session_id,
                    base_url,
                    self.resource_id,
                    new_name,
                    self.dto_object,
                )
                return True
            except Exception as e:
                raise Exception(f"Failed to rename drawer: {e}")

        elif self.level == self.LEVEL_FOLDER:
            try:
                logger.info(
                    f"Renaming folder {self.resource_id} from {self.name} to {new_name}"
                )
                FolderService.update_folder(
                    session_id,
                    base_url,
                    self.resource_id,
                    new_name,
                    self.dto_object,
                )
                return True
            except Exception as e:
                raise Exception(f"Failed to rename folder: {e}")
        else:
            raise Exception(f"Renaming not supported for level {self.level}")

    def support_recursive_move(self, dest_path: str) -> bool:
        """
        Returns whether the provider supports recursive move.

        Returns:
            True always.
        """
        return True

    def is_readonly(self) -> bool:
        """
        Returns whether the resource is read-only.

        Returns:
            False always.
        """
        return False

    def support_etag(self) -> bool:
        """
        Returns whether the provider supports ETags.

        Returns:
            False always.
        """
        return False
