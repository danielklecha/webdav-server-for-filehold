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


## Installation

To install the application, you need the provided `.whl` file.

* **[uv](https://docs.astral.sh/uv/) (recommended)**: `uv pip install webdav_server_for_filehold-*.whl`
* **pip**: `python -m pip install webdav_server_for_filehold-*.whl`

## Quick start

To start the server, run:

```bash
uv run webdav-server-for-filehold --filehold-url http://localhost/FH/FileHold/
```

### Logging in

When connecting via a WebDAV client (like WinSCP), use your FileHold credentials:

- **Local User**: `sysadm`, `.\sysadm`, or `local\sysadm`
- **Domain User**: `domainName\sysadm`

## Configuration

You can configure the server using the following command-line arguments:

| Argument                      | Environment Variable               | Description                                                         | Default                         |
| :---------------------------- | :--------------------------------- | :------------------------------------------------------------------ | :------------------------------ |
| `--host`                      | `WEBDAV_HOST`                      | Host to bind to                                                     | `0.0.0.0`                       |
| `--port`                      | `WEBDAV_PORT`                      | Port to bind to                                                     | `8080`                          |
| `--filehold-url`              | `WEBDAV_FILEHOLD_URL`              | Base URL for FileHold                                               | `http://localhost/FH/FileHold/` |
| `--default_schema_name`       | `WEBDAV_DEFAULT_SCHEMA_NAME`       | Default schema name to use when creating Cabinets or Folders        | `None`                          |
| `--create-category-in-drawer` | `WEBDAV_CREATE_CATEGORY_IN_DRAWER` | Create Category instead of Folder when creating directory in Drawer | `False`                         |
| `-v`, `--verbose`             | `WEBDAV_VERBOSE`                   | Enable debug logging for the application                            | `False`                         |
| `-vv`, `--very-verbose`       | `WEBDAV_VERY_VERBOSE`              | Enable debug logging for everything (including libraries)           | `False`                         |
| `--ssl-cert`                  | `WEBDAV_SSL_CERT`                  | Path to SSL certificate file (PEM format)                           | `None`                          |
| `--ssl-key`                   | `WEBDAV_SSL_KEY`                   | Path to SSL key file (PEM format)                                   | `None`                          |

**Example:**
```bash
webdav-server-for-filehold --port 9090 --filehold-url http://filehold.example.com/FH/FileHold/ --default_schema_name "Document"
```

## Contributing

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for development and testing instructions.

## License

`webdav-server-for-filehold` is provided as-is under the MIT license.
