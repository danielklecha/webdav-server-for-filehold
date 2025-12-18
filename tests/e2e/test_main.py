import os
import pytest
import requests
from zeep import Client
from zeep.transports import Transport
from typing import Generator, Any
from webdav_for_filehold.provider import CustomProvider
from webdav_for_filehold.client_factory import ClientFactory
from webdav_for_filehold.cabinet_service import CabinetService

# Configuration from environment variables
FILEHOLD_URL = os.environ.get("FILEHOLD_URL", "http://localhost/FH/FileHold/")
FILEHOLD_USERNAME = os.environ.get("FILEHOLD_USERNAME", "sysadm")
FILEHOLD_PASSWORD = os.environ.get("FILEHOLD_PASSWORD")
SKIP_E2E = os.environ.get("SKIP_E2E", "false").lower() == "true"


@pytest.mark.skipif(SKIP_E2E, reason="Skipping E2E tests")
class TestMainE2E:
    """
    End-to-end tests for the WebDAV adapter.
    """

    @pytest.fixture(scope="class")
    def session_id(self) -> Generator[str, None, None]:
        """
        Authenticate and return session ID.
        """
        if not FILEHOLD_PASSWORD:
            pytest.skip("FILEHOLD_PASSWORD environment variable not set")

        try:
            auth_url = f"{FILEHOLD_URL.rstrip('/')}/UserRoleManager/SessionManager.asmx?WSDL"
            session = requests.Session()
            transport = Transport(session=session)
            auth_client = Client(auth_url, transport=transport)
            # Try "WebClient" as client type
            session_id = auth_client.service.StartSession(FILEHOLD_USERNAME, FILEHOLD_PASSWORD, "WebClient")
            yield session_id
        except Exception as e:
            pytest.fail(f"Authentication failed: {e}")

    @pytest.fixture(scope="class")
    def provider(self) -> CustomProvider:
        """
        Fixture for CustomProvider instance.
        """
        return CustomProvider(FILEHOLD_URL)

    def test_provider_initialization(self, provider: CustomProvider) -> None:
        """
        Test that the provider initializes correctly.
        """
        assert provider is not None

    def test_tree_traversal(self, session_id: str, provider: CustomProvider) -> None:
        """
        Test traversing the tree structure from Root down to Files.
        """
        environ = {"filehold.session_id": session_id, "wsgidav.provider": provider}

        # Test Root
        root = provider.get_resource_inst("/", environ)
        assert root is not None

        members = root.get_member_list()
        assert members is not None
        # We expect at least one cabinet if the system is set up
        if not members:
            pytest.skip("No cabinets found, skipping traversal test")

        # Test Cabinet
        cabinet = members[0]
        print(f"Testing Cabinet: {cabinet.get_display_name()}")
        drawers = cabinet.get_member_list()
        assert drawers is not None

        if drawers:
            # Test Drawer
            drawer = drawers[0]
            print(f"Testing Drawer: {drawer.get_display_name()}")
            folders = drawer.get_member_list()
            assert folders is not None

            if folders:
                # Test Folder
                folder = folders[0]
                print(f"Testing Folder: {folder.get_display_name()}")
                files = folder.get_member_list()
                assert files is not None
                print(f"Folder members: {[m.get_display_name() for m in files]}")

    def test_get_tree_structure_direct(self, session_id: str) -> None:
        """
        Test the underlying get_tree_structure function directly.
        """
        client = ClientFactory.get_library_structure_manager_client(session_id, FILEHOLD_URL)
        cabinets = CabinetService.get_tree_structure(client)
        assert cabinets is not None
        assert isinstance(cabinets, list)
