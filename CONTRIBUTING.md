# Contributing

## Development

- `hatch env create`: Create virtual environment.
- `hatch shell`: Enter the environment.
- `hatch run webdav-server-for-filehold`: Run the server.
- `hatch build`: Build the package.
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
