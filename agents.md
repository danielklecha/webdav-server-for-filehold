# Project Context: WebDAV Adapter for FileHold

## Overview
This project adapts the **FileHold Document Management System (DMS)** to the **WebDAV** protocol. It allows users to mount FileHold as a network drive (e.g., in Windows Explorer or macOS Finder) and interact with documents and metadata using standard file system operations.

## Architecture
The application is built on top of **WsgiDAV**, a WSGI-based WebDAV server for Python.

1.  **Entry Point (`main.py`)**:
    -   Configures the WsgiDAV server.
    -   Sets up the WSGI application (using `cheroot` for production).
    -   Handles command-line arguments.

2.  **WebDAV Provider (`provider.py`)**:
    -   Implements `CustomProvider`, which inherits from `wsgidav.dav_provider.DAVProvider`.
    -   Translates WebDAV actions (GET, PUT, MKCOL, DELETE, MOVE) into calls to the Virtual File System (VFS).

3.  **Virtual File System (VFS)**:
    -   **Node Classes**: `VirtualFolder` (containers) and `VirtualFile` (documents). They implement the WsgiDAV resource interface but delegate business logic to services.
    -   **Services**: The core logic has been refactored into specialized services to improve maintainability and testability.
    -   **Streaming**: File uploads and downloads are handled by `UploadStream` and `DownloadStream` (wrapping `RepositoryController.asmx` logic) to support large files efficiently.

4.  **Services Layer**:
    -   **`ClientFactory`**: Manages `zeep` SOAP clients and authentication headers.
    -   **`DocumentService`**: Interactions with `LibraryManager.wsdl` for document CRUD operations. Handles chunked uploads/downloads.
    -   **`DocumentDataService`**: Handles metadata retrieval and updates (`DocumentManager.wsdl`).
    -   **`FolderService`, `CabinetService`, `DrawerService`**: Manage specific container types.
    -   **`LibraryObjectService`**: a base service for handling common logic like name sanitization for library objects.
    -   **`CategoryService`**: Manages document schemas (FileHold Categories).

5.  **Authentication (`auth.py`)**:
    -   Implements `CustomDomainController` for WsgiDAV.
    -   authenticates users against FileHold and maintains sessions.

## Dependencies
-   **wsgidav**: The WebDAV server framework.
-   **cheroot**: Production-quality WSGI server.
-   **zeep**: SOAP client for communicating with FileHold wsdl.
-   **requests**: HTTP library (used by zeep).

## Development Guidelines

### Environment Setup
-   **Build**: `hatch build`.
-   **Run**: `hatch run webdav-for-filehold`.

### Testing
Tests are located in `tests/`.
-   **Unit Tests**: `tests/unit/` (Mocked SOAP calls).
-   **Integration/E2E**: `tests/integration/` and `tests/e2e/` (May require a live FileHold instance).
-   **Run Tests**: `hatch test`.

### Code Style
-   Follow PEP 8.
-   Type hinting is encouraged.
-   **Architecture**: Logic should be placed in the appropriate `Service` class. `VirtualFolder` and `VirtualFile` should primarily act as adapters between WsgiDAV and the Service Layer.

### Key Considerations for Agents
-   **SOAP API**: The FileHold API is SOAP-based. All interactions go through `zeep` clients initialized in `ClientFactory`.
-   **State Management**: WebDAV is stateless, but FileHold sessions are stateful. The `auth.py` handles session caching.
-   **Concurrency**: usage of `cheroot` implies multi-threaded execution. Ensure shared resources are thread-safe.
-   **FileHold Schema**: The mapping between FileHold "Documents" (which have metadata/cards) and WebDAV "Files" (which are binary streams) is critical. `DocumentService` and `DocumentDataService` handle this abstraction.
