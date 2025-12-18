from datetime import datetime
from decimal import Decimal
from typing import Any, Union

import requests
from zeep import Client, xsd
from zeep.transports import Transport


class ClientFactory:
    """
    Factory class to create and configure Zeep clients for FileHold Web Services.
    """

    @staticmethod
    def get_library_structure_manager_client(session_id: str, base_url: str) -> Client:
        """
        Get the LibraryStructureManager service client.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.

        Returns:
            A configured Zeep Client instance for LibraryStructureManager.
        """
        wsdl_url = f"{base_url}LibraryManager/LibraryStructureManager.asmx?WSDL"
        return ClientFactory._get_client(session_id, wsdl_url)

    @staticmethod
    def get_document_finder_client(session_id: str, base_url: str) -> Client:
        """
        Get the DocumentFinder service client.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.

        Returns:
            A configured Zeep Client instance for DocumentFinder.
        """
        wsdl_url = f"{base_url}LibraryManager/DocumentFinder.asmx?WSDL"
        return ClientFactory._get_client(session_id, wsdl_url)

    @staticmethod
    def get_document_manager_client(session_id: str, base_url: str) -> Client:
        """
        Get the DocumentManager service client.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.

        Returns:
            A configured Zeep Client instance for DocumentManager.
        """
        wsdl_url = f"{base_url}LibraryManager/DocumentManager.asmx?WSDL"
        return ClientFactory._get_client(session_id, wsdl_url)

    @staticmethod
    def get_document_schema_manager_client(session_id: str, base_url: str) -> Client:
        """
        Get the DocumentSchemaManager service client.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.

        Returns:
            A configured Zeep Client instance for DocumentSchemaManager.
        """
        wsdl_url = f"{base_url}LibraryManager/DocumentSchemaManager.asmx?WSDL"
        return ClientFactory._get_client(session_id, wsdl_url)

    @staticmethod
    def get_user_preferences_client(session_id: str, base_url: str) -> Client:
        """
        Get the UserPreferences service client.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.

        Returns:
            A configured Zeep Client instance for UserPreferences.
        """
        wsdl_url = f"{base_url}LibraryManager/UserPreferences.asmx?WSDL"
        return ClientFactory._get_client(session_id, wsdl_url)

    @staticmethod
    def get_repository_controller_client(session_id: str, base_url: str) -> Client:
        """
        Get the RepositoryController service client.

        Args:
            session_id: The session ID for authentication.
            base_url: The base URL of the FileHold server.

        Returns:
            A configured Zeep Client instance for RepositoryController.
        """
        wsdl_url = f"{base_url}DocumentRepository/RepositoryController.asmx?WSDL"
        return ClientFactory._get_client(session_id, wsdl_url)

    @staticmethod
    def _get_client(session_id: str, wsdl_url: str) -> Client:
        """
        Helper method to create a Zeep client with the necessary session cookies.

        Args:
            session_id: The session ID for authentication.
            wsdl_url: The full URL to the WSDL.

        Returns:
            A configured Zeep Client instance.
        """
        session = requests.Session()
        session.cookies.set('FHLSID', session_id)
        transport = Transport(session=session)
        return Client(wsdl_url, transport=transport)

    @staticmethod
    def get_python_object(value: Any) -> Any:
        """
        Convert xsd.AnyObject or Zeep types to a native Python object.

        Args:
            value: The object to convert, potentially an xsd.AnyObject or a Zeep complex type.

        Returns:
            The converted Python object, or the original value if no conversion was needed.
        """
        if isinstance(value, xsd.AnyObject):
            return value.value

        if type(value).__name__ == 'ArrayOfInt':
            value = getattr(value, 'int', [])
            if value is None:
                value = []
        return value

    @staticmethod
    def get_any_object(client: Client, value: Any) -> Union[xsd.AnyObject, Any]:
        """
        Wrap value in xsd.AnyObject with the correct XML type for SOAP requests.

        Args:
            client: The Zeep client (used for type factories).
            value: The value to wrap.

        Returns:
            An xsd.AnyObject wrapping the value with the appropriate type, or the original value.
        """
        value = ClientFactory.get_python_object(value)

        if isinstance(value, list):
            factory = client.type_factory('ns0')
            array_of_int_type = factory.ArrayOfInt
            return xsd.AnyObject(array_of_int_type, array_of_int_type(value))
        
        if isinstance(value, bool):
            return xsd.AnyObject(xsd.Boolean(), value)
        if isinstance(value, int):
            return xsd.AnyObject(xsd.Int(), value)
        if isinstance(value, str):
            return xsd.AnyObject(xsd.String(), value)
        if isinstance(value, datetime):
            return xsd.AnyObject(xsd.DateTime(), value)
        if isinstance(value, Decimal):
            return xsd.AnyObject(xsd.Decimal(), value)
            
        return value
