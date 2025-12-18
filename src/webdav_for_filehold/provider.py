from typing import Any, Dict, Optional
import os
from wsgidav.dav_provider import DAVProvider
from .virtual_folder import VirtualFolder

class CustomProvider(DAVProvider):
    """
    Custom WebDAV provider for FileHold.
    
    This provider integrates with the FileHold system to expose its folder
    structure and documents via WebDAV.
    """
    
    def __init__(
        self, 
        filehold_url: str, 
        create_category_in_drawer: bool = False, 
        default_schema_name: Optional[str] = None
    ):
        """
        Initialize the CustomProvider.

        Args:
            filehold_url: The base URL for the FileHold instance.
            create_category_in_drawer: Whether to create categories directly inside drawers.
            default_schema_name: The default schema name to use for new documents.
        """
        super().__init__()
        self.filehold_url = filehold_url
        self.create_category_in_drawer = create_category_in_drawer
        self.default_schema_name = default_schema_name

    def is_readonly(self) -> bool:
        """
        Check if the provider is read-only.

        Returns:
            bool: Always False for this provider.
        """
        return False

    def get_resource_inst(
        self, path: str, environ: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Resolve a DAV resource instance for the given path.

        Args:
            path: The path relative to the share root (e.g., '/foo/bar').
            environ: The WSGI environment dictionary.

        Returns:
            Optional[DAVResource]: The resolved resource instance, or None if not found.
        """
        self._inject_environment_config(environ)

        clean_path = path.strip("/")
        if not clean_path:
            return VirtualFolder("/", environ, level=0)

        return self._resolve_path(clean_path, environ)

    def _inject_environment_config(self, environ: Dict[str, Any]) -> None:
        """
        Inject provider configuration into the WSGI environment.
        
        This allows VirtualFolder instances to access global settings.
        
        Args:
            environ: The WSGI environment dictionary to modify.
        """
        environ["filehold.url"] = self.filehold_url
        environ["filehold.create_category_in_drawer"] = self.create_category_in_drawer
        if self.default_schema_name:
            environ["filehold.default_schema_name"] = self.default_schema_name

    def _resolve_path(
        self, path: str, environ: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Traverse the virtual file system to find the resource at the given path.

        Args:
            path: The clean, non-empty path to resolve (e.g., 'foo/bar').
            environ: The WSGI environment dictionary.

        Returns:
            Optional[DAVResource]: The resolved resource, or None if not found.
        """
        parts = path.split("/")
        current: DAVResource = VirtualFolder("/", environ, level=0)

        for part in parts:
            if not isinstance(current, VirtualFolder):
                # If we hit a leaf (non-folder) but still have path parts, it's a mismatch
                return None
                
            found = False
            # Optimization Note: get_member_list might trigger SOAP calls.
            # Caching is a potential future improvement.
            for member in current.get_member_list():
                # We need to match the exact segment name from the URL.
                if os.path.basename(member.path) == part:
                    current = member
                    found = True
                    break
            
            if not found:
                return None

        return current


