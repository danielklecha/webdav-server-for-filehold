import os
from typing import List, Any
from .utils import sanitize_name


class LibraryObjectService:
    """
    Service for handling library objects, including processing and renaming
    to avoid name collisions.
    """

    @staticmethod
    def _insert_suffix(name: str, suffix: str, is_file: bool = False) -> str:
        """
        Inserts a suffix into a name.

        Args:
            name: The original name.
            suffix: The suffix to insert.
            is_file: Whether the name represents a file (to preserve extension).

        Returns:
            The name with the suffix inserted.
        """
        if is_file:
            base, ext = os.path.splitext(name)
            return f"{base} {suffix}{ext}"
        return f"{name} {suffix}"

    @staticmethod
    def process_objects(items: List[Any], is_file: bool = False) -> List[Any]:
        """
        Processes a list of objects, handling duplicate names by appending a suffix.

        Args:
            items: List of objects to process.
            is_file: Whether the objects represent files.

        Returns:
            The processed list of objects with unique names.
        """
        if not items:
            return []

        grouped = {}
        for item in items:
            name = getattr(item, 'Name', 'Unknown')
            key = sanitize_name(name).lower()

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)

        results = []
        for key in grouped:
            group = grouped[key]
            # Sort by ID to ensure stability
            group.sort(key=lambda x: getattr(x, 'Id', 0))

            for i, item in enumerate(group):
                original_name = getattr(item, 'Name', 'Unknown')
                final_name = original_name

                if i > 0:
                    suffix = f"({i + 1})"
                    final_name = LibraryObjectService._insert_suffix(
                        original_name, suffix, is_file=is_file
                    )

                setattr(item, 'Name', final_name)
                results.append(item)

        return results
