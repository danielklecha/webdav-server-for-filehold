# WebDAV Adapter for FileHold

> **Disclaimer:** This is an unofficial WebDAV server for FileHold.

## Features

This adapter allows you to access your FileHold documents via the WebDAV protocol.

1. **Browsing:** Navigate through Cabinets, Drawers, Folder Groups, and Folders.
2. **Downloading:** Download documents.
3. **Adding:** Add Cabinets, Drawers, Folder Groups, Folders and documents.
4. **Overriding:** Override existing documents.
5. **Structure Modification:** Create Cabinets, Drawers, Folder Groups, and Folders.
6. **Renaming:** Rename Cabinets, Drawers, Folder Groups, Folders and documents.

## Configuration

You can configure the server using the following command-line arguments:

- `--host`: The interface to bind to (default: `0.0.0.0`).
- `--port`: The port to listen on (default: `8080`).
- `--filehold-url`: The base URL for the FileHold instance (default: `http://localhost/FH/FileHold/`).
- `--default_schema_name`: Default schema name to use when creating new documents (e.g. `Document`).
- `--create-category-in-drawer`: If set, creating a directory in a Drawer creates a Category instead of a Folder.
- `--verbose`: Logging verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG).
- `--ssl-cert`: Path to SSL certificate file (PEM format).
- `--ssl-key`: Path to SSL key file (PEM format).

**Example:**
```bash
webdav-for-filehold --port 9090 --filehold-url http://filehold.example.com/FH/FileHold/ --default_schema_name "Document"
```

## Deployment

1. `pip install webdav_for_filehold-*.whl`: Install the package.
2. `webdav-for-filehold --help`: Run the application.

## Development

- `hatch env create`: Create virtual environment.
- `hatch shell`: Enter the environment.
- `hatch run webdav-for-filehold`: Run the server.
- `hatch build`: Build the package.
- `hatch publish`: Publish the package.
- `hatch clean`: Clean up the environment.

## Testing

### Unit Tests

To run the unit tests, use the following command:

```bash
hatch test tests/unit
```

### End-to-End (E2E) Tests

E2E tests require a running instance of FileHold and a valid user account.

```powershell
$env:FILEHOLD_PASSWORD="your_password"
hatch test tests/e2e
```

**Environment Variables:**

- `FILEHOLD_URL`: URL to the FileHold instance (default: `http://localhost/FH/FileHold/`).
- `FILEHOLD_USERNAME`: Username (default: `sysadm`).
- `FILEHOLD_PASSWORD`: Password (REQUIRED).
