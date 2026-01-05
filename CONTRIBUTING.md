# Contributing

## Development

- `uv sync`: Create virtual environment and install dependencies.
- `uv run webdav-server-for-filehold`: Run the server.
- `uv build`: Build the package.
- `uv run cov`: Run tests with coverage reporting.

## Testing

### Unit Tests

To run the unit tests, use the following command:

```bash
uv run pytest tests/unit
```

### End-to-End (E2E) Tests

E2E tests require a running instance of FileHold and a valid user account.

```powershell
$env:FILEHOLD_PASSWORD="your_password"
uv run pytest tests/e2e
```

**Environment Variables:**

- `FILEHOLD_URL`: URL to the FileHold instance (default: `http://localhost/FH/FileHold/`).
- `FILEHOLD_USERNAME`: Username (default: `sysadm`).
- `FILEHOLD_PASSWORD`: Password (REQUIRED).

### Coverage

To run tests with coverage reporting:

```bash
uv run pytest --cov=webdav_server_for_filehold --cov-report=term-missing
```

## Code Style

This project uses `ruff` and `black` for code style.
