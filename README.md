# WebDAV for FileHold

## Disclaimer

**Unofficial Implementation**
This project is an independent open-source software project. It is **not** affiliated with, endorsed by, sponsored by, or associated with **FileHold Systems Inc.**

**Trademarks**
"FileHold" and the FileHold logo are trademarks or registered trademarks of FileHold Systems Inc. in the United States, Canada, and/or other countries. All other trademarks cited herein are the property of their respective owners. Use of these names is for descriptive purposes only (nominative fair use) to indicate compatibility.

## Features

This server allows you to access your FileHold documents via the WebDAV protocol.

1. **Browsing:** Navigate through cabinets, drawers, folder groups, and folders.
2. **Downloading:** Download documents.
3. **Adding:** Add cabinets, drawers, folder groups, folders and documents.
4. **Overriding:** Override existing documents.
5. **Structure Modification:** Create cabinets, drawers, folder groups, and folders.
6. **Renaming:** Rename cabinets, drawers, folder groups, folders and documents.

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
webdav-server-for-filehold --port 9090 --filehold-url http://filehold.example.com/FH/FileHold/ --default_schema_name "Document"
```

## Deployment

1. `pip install webdav_server_for_filehold-*.whl`: Install the package.
2. `webdav-server-for-filehold --help`: Run the application.

## Contributing

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for development and testing instructions.

