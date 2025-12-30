import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from webdav_server_for_filehold.virtual_folder import VirtualFolder
from webdav_server_for_filehold.virtual_file import VirtualFile
from webdav_server_for_filehold.document_service import DocumentService
from webdav_server_for_filehold.cabinet_service import CabinetService
from webdav_server_for_filehold.drawer_service import DrawerService
from webdav_server_for_filehold.folder_service import FolderService
from webdav_server_for_filehold.category_service import CategoryService
from webdav_server_for_filehold.provider import CustomProvider


class TestVirtualFolder(unittest.TestCase):
    """
    Unit tests for VirtualFolder and related components like VirtualFile and CustomProvider integration.
    """

    def test_member_names(self) -> None:
        """
        Test that member names are correctly processed and sanitized.
        """
        # Mock the SOAP objects
        mock_cabinet = MagicMock()
        mock_cabinet.Name = "Cabinet One"
        mock_cabinet.Id = 1

        # Mock environ
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }

        # Create a VirtualFolder for Root
        vf = VirtualFolder("/", environ, level=0)

        # Mock get_tree_structure
        with patch('webdav_server_for_filehold.cabinet_service.CabinetService.get_tree_structure') as mock_get_tree:
            mock_get_tree.return_value = [mock_cabinet]

            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf.get_member_list()

                self.assertEqual(len(members), 1)
                member = members[0]

                print(f"Path: {member.path}")
                print(f"Display Name: {member.get_display_name()}")

                # Verify new behavior
                # Name: Cabinet One -> Sanitized: Cabinet One
                # Format: {sanitized} -> Cabinet One
                self.assertTrue(member.path.endswith("/Cabinet One"))
                self.assertEqual(member.get_display_name(), "Cabinet One")

    def test_resolve_path(self) -> None:
        """
        Test that CustomProvider can resolve paths correctly.
        """
        # Test that CustomProvider can resolve the new path format
        provider = CustomProvider("http://localhost/FH/FileHold/")
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": provider
        }

        # We want to resolve "/Cabinet One"
        # This requires get_member_list to return a member with that path

        mock_cabinet = MagicMock()
        mock_cabinet.Name = "Cabinet One"
        mock_cabinet.Id = 1

        with patch('webdav_server_for_filehold.cabinet_service.CabinetService.get_tree_structure') as mock_get_tree:
            mock_get_tree.return_value = [mock_cabinet]
            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                resource = provider.get_resource_inst("/Cabinet One", environ)

                self.assertIsNotNone(resource)
                self.assertEqual(resource.path, "/Cabinet One")
                self.assertEqual(resource.resource_id, 1)

    def test_file_names(self) -> None:
        """
        Test VirtualFile naming conventions.
        """
        # Test VirtualFile naming
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }
        # Level 3 = Folder
        vf = VirtualFolder("/Cabinet_One/Drawer_One/Folder_One", environ, resource_id=1, level=3)

        # Mock DocumentFinder client and response
        mock_doc_client = MagicMock()
        mock_result = MagicMock()

        # Columns
        col_name = MagicMock()
        col_name.SystemFieldId = -4
        col_name.ColumnIndex = 0

        col_size = MagicMock()
        col_size.SystemFieldId = -24
        col_size.ColumnIndex = 1

        mock_result.Columns.FieldDefinition = [col_name, col_size]

        # Mock DocumentValues
        doc_data = MagicMock()
        doc_data.DocumentId = 123
        doc_data.MetadataVersionId = 456
        doc_data.Extension = ".txt"
        doc_data.DataColumns.anyType = ["My Document", "1024"]

        mock_result.DocumentValues.DocumentData = [doc_data]

        mock_doc_client.service.GetDocumentsWithFields.return_value.GetDocumentsWithFieldsResult = mock_result
        mock_doc_client.service.GetSnapshotDocumentCount.return_value = 1

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_finder_client') as mock_get_client:
            mock_get_client.return_value = mock_doc_client

            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf.get_member_list()

            self.assertEqual(len(members), 1)
            member = members[0]

            print(f"File Path: {member.path}")
            print(f"File Display Name: {member.get_display_name()}")

            # Expected: {sanitized_base}{extension}
            # Name: "My Document" -> Sanitized Base: "My Document"
            # ID: 123
            # Ext: .txt
            # Result: .../My Document.txt

            self.assertTrue(member.path.endswith("/My Document.txt"))
            self.assertEqual(member.get_display_name(), "My Document.txt")

    def test_create_cabinet_with_owner(self) -> None:
        """
        Test creating a cabinet with an owner GUID specified.
        """
        # Test that create_collection passes user_guid to add_cabinet
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "filehold.user_guid": "11111111-2222-3333-4444-555555555555",
            "wsgidav.provider": MagicMock()
        }

        vf = VirtualFolder("/", environ, level=0)

        with patch('webdav_server_for_filehold.cabinet_service.CabinetService.add_cabinet') as mock_add_cabinet:
            mock_add_cabinet.return_value = 123

            vf.create_collection("New Cabinet")

            mock_add_cabinet.assert_called_with(
                "test_session",
                "http://localhost/FH/FileHold/",
                "New Cabinet",
                owner_guid="11111111-2222-3333-4444-555555555555",
                default_schema_name=None
            )

    def test_lazy_loading_structure(self) -> None:
        """
        Test lazy loading logic for structure optimized fetching.
        """
        # Test smart fetching logic
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }

        # 1. Level 1 (Cabinet): Empty drawers but HasChildren=True -> Should Call
        mock_cabinet_1 = MagicMock()
        mock_cabinet_1.Name = "Cab 1"
        mock_cabinet_1.Id = 1
        mock_cabinet_1.Drawers = None
        mock_cabinet_1.HasChildren = True

        vf_cab_1 = VirtualFolder("/Cab_1", environ, resource_id=1, level=1, soap_object=mock_cabinet_1)

        with patch('webdav_server_for_filehold.cabinet_service.CabinetService.get_cabinet_structure') as mock_get_cab:
            mock_full_cabinet = MagicMock()
            mock_full_cabinet.Drawers.Drawer = [MagicMock(Name="D1", Id=10)]
            mock_get_cab.return_value = mock_full_cabinet

            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf_cab_1.get_member_list()
                mock_get_cab.assert_called_once()
                self.assertEqual(len(members), 1)

        # 2. Level 1 (Cabinet): Empty drawers and HasChildren=False -> Should NOT Call
        mock_cabinet_2 = MagicMock()
        mock_cabinet_2.Name = "Cab 2"
        mock_cabinet_2.Id = 2
        mock_cabinet_2.Drawers = []
        mock_cabinet_2.HasChildren = False

        vf_cab_2 = VirtualFolder("/Cab_2", environ, resource_id=2, level=1, soap_object=mock_cabinet_2)

        with patch('webdav_server_for_filehold.cabinet_service.CabinetService.get_cabinet_structure') as mock_get_cab:
            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf_cab_2.get_member_list()
                mock_get_cab.assert_not_called()
                self.assertEqual(len(members), 0)

        # 3. Level 2 (Drawer): Empty folders/categories but HasChildren=True -> Should Call
        mock_drawer_3 = MagicMock()
        mock_drawer_3.Name = "Drawer 3"
        mock_drawer_3.Id = 3
        # Use del to ensure attributes missing or set to None/Empty
        mock_drawer_3.Folders = None
        mock_drawer_3.Categories = []
        mock_drawer_3.HasChildren = True

        vf_drawer_3 = VirtualFolder("/...,Drawer_3", environ, resource_id=3, level=2, soap_object=mock_drawer_3)

        with patch('webdav_server_for_filehold.drawer_service.DrawerService.get_drawer_structure') as mock_get_drawer:
            mock_struct = MagicMock()
            mock_struct.Folders.Folder = [MagicMock(Name="F1", Id=30)]
            mock_struct.Categories = None
            mock_get_drawer.return_value = mock_struct

            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf_drawer_3.get_member_list()
                mock_get_drawer.assert_called_once()
                self.assertEqual(len(members), 1)

        # 4. Level 2 (Drawer): Empty folders/categories and HasChildren=False -> Should NOT Call
        mock_drawer_4 = MagicMock()
        mock_drawer_4.Name = "Drawer 4"
        mock_drawer_4.Id = 4
        mock_drawer_4.Folders = []
        mock_drawer_4.Categories = None
        mock_drawer_4.HasChildren = False

        vf_drawer_4 = VirtualFolder("/...,Drawer_4", environ, resource_id=4, level=2, soap_object=mock_drawer_4)

        with patch('webdav_server_for_filehold.drawer_service.DrawerService.get_drawer_structure') as mock_get_drawer:
            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf_drawer_4.get_member_list()
                mock_get_drawer.assert_not_called()
                self.assertEqual(len(members), 0)

    def test_duplicates(self) -> None:
        """
        Test handling of duplicate resource names.
        """
        # Create a VirtualFolder for Root
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }
        vf = VirtualFolder("/", environ, level=0)

        # Mock Cabinets with duplicates
        # Cab A (id 10), Cab A (id 5), Cab B (id 20)
        c1 = MagicMock(Name="Cab A", Id=10)
        c2 = MagicMock(Name="Cab A", Id=5)
        c3 = MagicMock(Name="Cab B", Id=20)

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.service.GetTreeStructure.return_value = [c1, c2, c3]

            members = vf.get_member_list()

            self.assertEqual(len(members), 3)

            # Sort by path to be sure of order? Or expected order from logic?
            # Process members sorts by ID:
            # Group "Cab A": [id 5, id 10]
            #   Id 5 -> "Cab A"
            #   Id 10 -> "Cab A (2)"
            # Group "Cab B": [id 20]
            #   Id 20 -> "Cab B"

            # Check mapping
            names_map = {m.resource_id: m.get_display_name() for m in members}
            paths_map = {m.resource_id: m.path for m in members}

            self.assertEqual(names_map[5], "Cab A")
            self.assertTrue(paths_map[5].endswith("/Cab A"))

            self.assertEqual(names_map[10], "Cab A (2)")
            self.assertTrue(paths_map[10].endswith("/Cab A (2)"))

            self.assertEqual(names_map[20], "Cab B")
            self.assertTrue(paths_map[20].endswith("/Cab B"))

    def test_file_duplicates(self) -> None:
        """
        Test handling of duplicate file names.
        """
        # Test VirtualFile duplicate naming (suffixes and extensions)
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }
        vf = VirtualFolder("/Folder", environ, resource_id=1, level=3)

        # Mock DocumentFinder client
        mock_doc_client = MagicMock()
        mock_result = MagicMock()

        # Columns
        col_name = MagicMock(SystemFieldId=-4, ColumnIndex=0)
        col_size = MagicMock(SystemFieldId=-24, ColumnIndex=1)
        mock_result.Columns.FieldDefinition = [col_name, col_size]

        # Documents:
        # Doc.txt (id 100)
        # Doc.txt (id 200)
        # Doc (id 300) -> Doc.txt if extension added logic works? No, name usually includes ext or logic adds it.
        # Let's assume names come with extension or logic appends it.

        d1 = MagicMock()
        d1.DocumentId = 200
        d1.MetadataVersionId = 1
        d1.Extension = ".txt"
        d1.DataColumns.anyType = ["Doc.txt", "10"]

        d2 = MagicMock()
        d2.DocumentId = 100
        d2.MetadataVersionId = 2
        d2.Extension = ".txt"
        d2.DataColumns.anyType = ["Doc", "20"]  # Logic should add .txt

        mock_result.DocumentValues.DocumentData = [d1, d2]

        mock_doc_client.service.GetDocumentsWithFields.return_value.GetDocumentsWithFieldsResult = mock_result
        mock_doc_client.service.GetSnapshotDocumentCount.return_value = 2

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_finder_client') as mock_get_client:
            mock_get_client.return_value = mock_doc_client
            with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client'):
                members = vf.get_member_list()

                self.assertEqual(len(members), 2)

                # Sorted by ID:
                # d2 (id 100) -> "Doc.txt" (Name "Doc" + ".txt")
                # d1 (id 200) -> "Doc (2).txt"

                # Paths should be used as keys to check uniqueness
                for m in members:
                    print(f"Path: {m.path}")

                # .../Doc.txt
                # .../Doc (2).txt

                found_clean = False
                found_suffix = False

                for m in members:
                    if m.path.endswith("/Doc.txt"):
                        self.assertEqual(m.get_display_name(), "Doc.txt")
                        found_clean = True
                    elif m.path.endswith("/Doc (1).txt"):
                        self.assertEqual(m.get_display_name(), "Doc (1).txt")
                        found_suffix = True

                self.assertTrue(found_clean)
                self.assertTrue(found_suffix)

    def test_delete_document(self) -> None:
        """
        Test deleting a document via VirtualFile.delete().
        """
        # Test VirtualFile.delete()
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }

        # Mock filehold object
        mock_doc = MagicMock()
        mock_doc.DocumentId = 1001
        mock_doc.MetadataVersionId = 2002
        mock_doc.CanDelete = True

        # Test 1: With explicit snapshot_id
        vf = VirtualFile("/Doc.txt", environ, name="Doc.txt", dto_object=mock_doc, snapshot_id="guid-snapshot-123")

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_manager_client') as mock_get_dm:
            mock_dm = MagicMock()
            mock_get_dm.return_value = mock_dm
            mock_dm.service.CreateSelection.return_value.CreateSelectionResult = 555

            vf.delete()

            args, _ = mock_dm.service.CreateSelection.call_args
            selection_arg = args[0] if args else _['selection']
            snap_sel = selection_arg['SnapshotSelection']['SnapshotSelection'][0]

            self.assertEqual(snap_sel['SnapshotId'], "guid-snapshot-123")
            self.assertEqual(snap_sel['MetadataVersionIdList']['int'][0], 2002)

        # Test 2: Without explicit snapshot_id (should default/fallback)
        # Note: getattr(mock_doc, 'SnapshotId') will return the mock object unless we set it or use spec.
        # delete_document uses getattr(doc, 'SnapshotId', default_zero_guid)
        # If we pass a mock_doc without 'SnapshotId' property set, default is used.
        del mock_doc.SnapshotId

        vf2 = VirtualFile("/Doc2.txt", environ, name="Doc2.txt", dto_object=mock_doc)

        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_manager_client') as mock_get_dm:
            mock_dm = MagicMock()
            mock_get_dm.return_value = mock_dm
            mock_dm.service.CreateSelection.return_value.CreateSelectionResult = 666

            vf2.delete()

            args, _ = mock_dm.service.CreateSelection.call_args
            selection_arg = args[0] if args else _['selection']
            snap_sel = selection_arg['SnapshotSelection']['SnapshotSelection'][0]

            self.assertEqual(snap_sel['SnapshotId'], "00000000-0000-0000-0000-000000000000")

    def test_remove_operations(self) -> None:
        """
        Test helper functions for removing different types of library objects.
        """
        # Test usage of remove_cabinet, remove_drawer, remove_folder, remove_category
        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_library_structure_manager_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # Cabinet
            CabinetService.remove_cabinet("sess", "url", 100)
            mock_client.service.RemoveCabinet.assert_called_with(cabinetId=100, forceContentRemoval=True)

            # Drawer
            DrawerService.remove_drawer("sess", "url", 200)
            mock_client.service.RemoveDrawer.assert_called_with(drawerId=200, forceContentRemoval=True)

            # Folder
            FolderService.remove_folder("sess", "url", 300)
            mock_client.service.RemoveFolder.assert_called_with(folderId=300, forceContentRemoval=True)

            # Category
            CategoryService.remove_category("sess", "url", 400, 200)
            mock_client.service.RemoveCategory.assert_called_with(categoryId=400, drawerId=200, forceContentRemoval=True)

    def test_virtual_folder_delete_dispatch(self) -> None:
        """
        Test correct delete dispatch logic in VirtualFolder.delete().
        """
        environ: Dict[str, Any] = {
            "filehold.session_id": "test_session",
            "wsgidav.provider": MagicMock()
        }

        # 1. Level 1 (Cabinet)
        vf_cab = VirtualFolder("/Cab", environ, resource_id=10, level=1)
        with patch('webdav_server_for_filehold.cabinet_service.CabinetService.remove_cabinet') as mock_rm:
            vf_cab.delete()
            mock_rm.assert_called_with("test_session", "http://localhost/FH/FileHold/", 10)

        # 2. Level 2 (Drawer)
        vf_drawer = VirtualFolder("/Cab/Drawer", environ, resource_id=20, level=2)
        with patch('webdav_server_for_filehold.drawer_service.DrawerService.remove_drawer') as mock_rm:
            vf_drawer.delete()
            mock_rm.assert_called_with("test_session", "http://localhost/FH/FileHold/", 20)

        # 3. Level 3 (Folder)
        vf_folder = VirtualFolder("/Cab/Drawer/Folder", environ, resource_id=30, level=3)
        with patch('webdav_server_for_filehold.folder_service.FolderService.remove_folder') as mock_rm:
            vf_folder.delete()
            mock_rm.assert_called_with("test_session", "http://localhost/FH/FileHold/", 30)

        # 4. Level 4 (Category)
        # Needs parent_resource_id
        vf_cat = VirtualFolder("/Cab/Drawer/Cat", environ, resource_id=40, level=4, parent_resource_id=20)
        with patch('webdav_server_for_filehold.category_service.CategoryService.remove_category') as mock_rm:
            vf_cat.delete()
            mock_rm.assert_called_with("test_session", "http://localhost/FH/FileHold/", 40, 20)

        # 5. Missing parent ID for Category
        vf_cat_bad = VirtualFolder("/Cab/Drawer/CatBad", environ, resource_id=41, level=4, parent_resource_id=None)
        with self.assertRaises(Exception):
            vf_cat_bad.delete()


class TestDocumentUpdates(unittest.TestCase):
    """
    Unit tests for updating documents.
    """

    def test_update_document_naming(self) -> None:
        """
        Test document renaming logic under various conditions.
        """
        doc_data = MagicMock()
        del doc_data.DocumentData
        doc_data.DocumentId = 1
        doc_data.MetadataVersionId = 100
        doc_data.DocumentSchemaId = 5
        doc_data.Extension = ".txt"
        doc_data.CanEdit = True

        # Mocks for dependencies
        with patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_manager_client') as mock_get_dm, \
             patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_finder_client') as mock_get_finder, \
             patch('webdav_server_for_filehold.client_factory.ClientFactory.get_document_schema_manager_client') as mock_get_schema:

            # Setup Schemas Mock
            mock_schema_mgr = MagicMock()
            mock_get_schema.return_value = mock_schema_mgr

            mock_schema = MagicMock()
            # Ensure integer attributes are integers to avoid TypeError during comparisons
            mock_schema.VersionControlFieldId = 0
            mock_schema_mgr.service.GetDocumentSchema.return_value = mock_schema

            # Setup Document Manager Mock
            mock_dm = MagicMock()
            mock_get_dm.return_value = mock_dm

            # Setup Document Finder Mock (GetDocumentDetails)
            mock_finder = MagicMock()
            mock_get_finder.return_value = mock_finder

            # Mock details response structure
            mock_details = MagicMock()
            mock_details.Columns.FieldDefinition = []
            mock_details.DocumentValues.DocumentData = [doc_data]  # Return self as data for simplicity or strict mock
            mock_finder.service.GetDocumentDetails.return_value = mock_details

            # Helper to run test case
            def run_case(new_name: str, expected_doc_name: str) -> None:
                DocumentService.update_document("sess", "url", doc_data, new_name)
                # Check call to SetMetadata
                args, kwargs = mock_dm.service.SetMetadata.call_args
                # args: [prevMetadataVersionId, documentSchemaId, documentName, ...]
                # or kwargs: documentName=...
                if 'documentName' in kwargs:
                    actual_name = kwargs['documentName']
                else:
                    # Arg positions:
                    # SetMetadata(prevMetadataVersionId, documentSchemaId, documentName, fieldsWithValues, overwritePrevious, versionNumber)
                    # 0, 1, 2
                    actual_name = args[2] if len(args) > 2 else None

                self.assertEqual(actual_name, expected_doc_name, f"Failed for input '{new_name}'")

            # Case 1: Standard renaming with extension
            run_case("MyFile.txt", "MyFile")

            # Case 2: Renaming without extension
            run_case("MyFile", "MyFile")

            # Case 3: Name with dots
            run_case("My.Complex.File.txt", "My.Complex.File")

            # Case 4: Name with dots without extension
            run_case("My.Complex.File", "My.Complex.File")

            # Case 5: Version like name
            run_case("Report v1.2.txt", "Report v1.2")

            # Case 6: Version like name without extension
            run_case("Report v1.2", "Report v1.2")

            # Case 7: Mismatched extension (should keep)
            run_case("MyFile.pdf", "MyFile.pdf")

            # Case 8: Case insensitivity
            run_case("MyFile.TXT", "MyFile")


if __name__ == '__main__':
    unittest.main()
