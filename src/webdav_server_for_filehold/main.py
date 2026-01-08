import argparse
import logging
import logging.config
import typing
import json
import os

import sys
import uvicorn
from uvicorn.logging import DefaultFormatter
from wsgidav.wsgidav_app import WsgiDAVApp

# Import from local modules
from .auth import CustomDomainController
from .provider import CustomProvider

_application = None


def _parse_environ(environ: dict) -> dict:
    """
    Parses configuration from environment variables.

    Args:
        environ (dict): The environment dictionary (e.g., os.environ or WSGI environ).

    Returns:
        dict: A dictionary of configuration arguments for _get_wsgi_app.
    """
    kwargs = {}

    filehold_url = environ.get("WEBDAV_FILEHOLD_URL")
    if filehold_url:
        kwargs["filehold_url"] = filehold_url

    host = environ.get("WEBDAV_HOST")
    if host:
        kwargs["host"] = host

    port = environ.get("WEBDAV_PORT")
    if port:
        try:
            kwargs["port"] = int(port)
        except ValueError:
            logging.error(f"Invalid value for WEBDAV_PORT: {port}")

    verbose = environ.get("WEBDAV_VERBOSE")
    if verbose:
        try:
            kwargs["verbose"] = int(verbose)
        except ValueError:
            logging.error(f"Invalid value for WEBDAV_VERBOSE: {verbose}")

    create_category = environ.get("WEBDAV_CREATE_CATEGORY_IN_DRAWER")
    if create_category:
        kwargs["create_category_in_drawer"] = create_category.lower() == "true"

    default_schema = environ.get("WEBDAV_DEFAULT_SCHEMA_NAME")
    if default_schema:
        kwargs["default_schema_name"] = default_schema

    return kwargs


def _parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="WebDAV for FileHold")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging for the application"
    )
    parser.add_argument(
        "-vv", "--very-verbose",
        action="store_true",
        help="Enable debug logging for everything (including libraries)"
    )

    parser.add_argument(
        "--filehold-url",
        default="http://localhost/FH/FileHold/",
        help="Base URL for FileHold (default: http://localhost/FH/FileHold/)"
    )
    parser.add_argument(
        "--ssl-cert",
        help="Path to SSL certificate file (PEM format)"
    )
    parser.add_argument(
        "--ssl-key",
        help="Path to SSL key file (PEM format)"
    )
    parser.add_argument(
        "--create-category-in-drawer",
        action="store_true",
        default=False,
        help="Create Category instead of Folder when creating directory in Drawer"
    )
    parser.add_argument(
        "--default_schema_name",
        help="Default schema name to use when creating Cabinets or Folders"
    )
    return parser.parse_args()


def _configure_logging(verbose: bool, very_verbose: bool) -> None:
    """
    Configures logging based on verbosity flags using standard dictConfig.
    
    Rules:
    - Default: WARNING for everything.
    - verbose (-v): INFO for webdav_server_for_filehold, WARNING for others.
    - very_verbose (-vv): INFO for everything.
    """
    root_level = "WARNING"
    app_level = "NOTSET"

    if very_verbose:
        root_level = "INFO"
    elif verbose:
        app_level = "INFO"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
        },
        "handlers": {
            "console": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "webdav_server_for_filehold": {
                "level": app_level,
            },
            "wsgidav": {
                "level": "NOTSET",
                "propagate": True,
            },
            "uvicorn": {
                "level": "NOTSET",
                "propagate": True,
            },
        },
        "root": {
            "level": root_level,
            "handlers": ["console"],
        },
    }
    
    logging.config.dictConfig(logging_config)

def _get_wsgi_app(
    filehold_url: str = "http://localhost/FH/FileHold/",
    host: str = "0.0.0.0",
    port: int = 8080,
    verbose: int = 2,
    create_category_in_drawer: bool = False,
    default_schema_name: typing.Optional[str] = None
) -> WsgiDAVApp:
    """
    Creates the WsgiDAV application.

    Args:
        filehold_url (str): Base URL for FileHold.
        host (str): Host to bind to.
        port (int): Port to bind to.
        verbose (int): Verbosity level (0-3).
        create_category_in_drawer (bool): Create Category instead of Folder in Drawer.
        default_schema_name (typing.Optional[str]): Default schema name.

    Returns:
        WsgiDAVApp: The WsgiDAV application.
    """
    # Ensure URL ends with slash
    if not filehold_url.endswith("/"):
        filehold_url += "/"

    config = {
        "provider_mapping": {
            "/": CustomProvider(
                filehold_url,
                create_category_in_drawer,
                default_schema_name
            )
        },
        "http_authenticator": {
            "domain_controller": CustomDomainController,
            "accept_basic": True,
            "accept_digest": False,
            "default_to_digest": False,
        },
        "logging": {
            "enable": False,
        },
        "verbose": verbose,
        "host": host,
        "port": port,
        "filehold_url": filehold_url
    }
    return WsgiDAVApp(config)


def get_wsgi_app(environ, start_response):
    """
    WSGI application entry point for IIS/FastCGI.
    
    Configuration is loaded from environment variables (e.g. WEBDAV_FILEHOLD_URL).
    """
    global _application
    if _application is None:
        # Check both process environment (os.environ) and WSGI environment (environ)
        # WSGI environ takes precedence for request-specific config if needed, 
        # but here we're initializing the global app so we check likely sources.
        # We start with os.environ as a base, then update with passed environ if it has our keys.
        
        # Merge sources: os.environ first, then passed environ
        merged_environ = os.environ.copy()
        # Only update with string keys from environ to avoid issues
        for k, v in environ.items():
            if isinstance(k, str) and isinstance(v, str):
                merged_environ[k] = v

        kwargs = _parse_environ(merged_environ)
        _application = _get_wsgi_app(**kwargs)

    return _application(environ, start_response)


def start_server(
    app: typing.Any,
    host: str,
    port: int,
    ssl_cert: typing.Optional[str] = None,
    ssl_key: typing.Optional[str] = None
) -> None:
    """
    Initializes and starts the WSGI server.

    Args:
        app (typing.Any): The WSGI application (e.g. WsgiDAVApp).
        host (str): Host to bind to.
        port (int): Port to bind to.
        ssl_cert (typing.Optional[str]): Path to SSL certificate.
        ssl_key (typing.Optional[str]): Path to SSL key.
    """
    protocol = "http"
    if ssl_cert and ssl_key:
        protocol = "https"

    logger = logging.getLogger("webdav_server_for_filehold")
    logger.info(f"Serving on {protocol}://{host}:{port} ...")
    # Ensure we don't fail if app doesn't have config (generic usage)
    if hasattr(app, "config"):
        logger.info(f"Targeting FileHold at {app.config.get('provider_mapping', {}).get('/', 'UNKNOWN')}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_certfile=ssl_cert,
        ssl_keyfile=ssl_key,
        interface="wsgi",
        log_config=None,
    )


def run() -> None:
    """
    Entry point for the WebDAV server.
    Parses arguments, configures logging, and starts the WsgiDAV app.
    """
    args = _parse_arguments()
    _configure_logging(args.verbose, args.very_verbose)
    
    verbose_level = 3 if args.very_verbose else 2
    
    app = _get_wsgi_app(
        filehold_url=args.filehold_url,
        host=args.host,
        port=args.port,
        verbose=verbose_level,
        create_category_in_drawer=args.create_category_in_drawer,
        default_schema_name=args.default_schema_name
    )
    start_server(app, args.host, args.port, args.ssl_cert, args.ssl_key)


if __name__ == "__main__":
    run()

