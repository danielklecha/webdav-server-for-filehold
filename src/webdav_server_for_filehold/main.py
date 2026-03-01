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


def _str_to_bool(value: typing.Union[str, bool, int, None]) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in ("true", "1", "yes", "on")


def _parse_arguments(
    args: typing.Optional[typing.List[str]] = None,
    environ: typing.Dict[str, str] = os.environ
) -> argparse.Namespace:
    """
    Parses command-line arguments, using environment variables as defaults.

    Args:
        args (list): Optional argument list to parse (overrides sys.argv).
        environ (dict): Environment dictionary to look up defaults (default: os.environ).

    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="WebDAV for FileHold (Community Tool)")

    # Helper to get env var with default
    def env(key, default=None):
        return environ.get(key, default)

    parser.add_argument(
        "--host",
        default=env("WEBDAV_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(env("WEBDAV_PORT", 8080)),
        help="Port to bind to (default: 8080)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=_str_to_bool(env("WEBDAV_VERBOSE", False)),
        help="Enable debug logging for the application"
    )
    parser.add_argument(
        "-vv", "--very-verbose",
        action="store_true",
        default=_str_to_bool(env("WEBDAV_VERY_VERBOSE", False)),
        help="Enable debug logging for everything (including libraries)"
    )

    parser.add_argument(
        "--filehold-url",
        default=env("WEBDAV_FILEHOLD_URL", "http://localhost/FH/FileHold/"),
        help="Base URL for FileHold (default: http://localhost/FH/FileHold/)"
    )
    parser.add_argument(
        "--ssl-cert",
        default=env("WEBDAV_SSL_CERT"),
        help="Path to SSL certificate file (PEM format)"
    )
    parser.add_argument(
        "--ssl-key",
        default=env("WEBDAV_SSL_KEY"),
        help="Path to SSL key file (PEM format)"
    )
    parser.add_argument(
        "--create-category-in-drawer",
        action="store_true",
        default=_str_to_bool(env("WEBDAV_CREATE_CATEGORY_IN_DRAWER", False)),
        help="Create Category instead of Folder when creating directory in Drawer"
    )
    parser.add_argument(
        "--default_schema_name",
        default=env("WEBDAV_DEFAULT_SCHEMA_NAME"),
        help="Default schema name to use when creating Cabinets or Folders"
    )
    parser.add_argument(
        "--mount-path",
        default=env("WEBDAV_MOUNT_PATH"),
        help="Mount path for WebDAV (e.g. /webdav)"
    )

    # If args is None, argparse uses sys.argv
    return parser.parse_args(args)


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
    
    # Suppress specific WsgiDAV warning about lack of SSL
    # This is intended behavior when running behind an SSL-terminating proxy (like IIS)
    # or in a controlled internal environment.
    class WsgiDavSslFilter(logging.Filter):
        def filter(self, record):
            if "wsgidav" in record.name:
                if "Basic authentication is enabled: It is highly recommended to enable SSL" in record.getMessage():
                    return False
            return True

    # Attach to root handlers so it applies to wsgidav propagated logs
    for handler in logging.getLogger().handlers:
        handler.addFilter(WsgiDavSslFilter())

def _get_wsgi_app(
    filehold_url: str = "http://localhost/FH/FileHold/",
    host: str = "0.0.0.0",
    port: int = 8080,
    verbose: int = 2,
    create_category_in_drawer: bool = False,
    default_schema_name: typing.Optional[str] = None,
    mount_path: typing.Optional[str] = None
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
        "cors": {
            "enable": True,
            "allow_origin": "*",
        },
        "verbose": verbose,
        "host": host,
        "port": port,
        "filehold_url": filehold_url,
        "mount_path": mount_path
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

        # Parse configuration from environment using argument defaults
        # We pass args=[] to ignore sys.argv when running under WSGI
        args = _parse_arguments(args=[], environ=merged_environ)
        
        _configure_logging(args.verbose, args.very_verbose)
        
        verbose_level = 3 if args.very_verbose else 2

        _application = _get_wsgi_app(
            filehold_url=args.filehold_url,
            host=args.host,
            port=args.port,
            verbose=verbose_level,
            create_category_in_drawer=args.create_category_in_drawer,
            default_schema_name=args.default_schema_name,
            mount_path=args.mount_path
        )

    script_name_override = os.environ.get("SCRIPT_NAME")
    if script_name_override:
         script_name = script_name_override.rstrip("/")
         environ["SCRIPT_NAME"] = script_name
         
         path_info = environ.get("PATH_INFO", "")
         
         # 1. Strip script_name from PATH_INFO if present (handling proxy/uvicorn overlap)
         if path_info.startswith(script_name):
             new_path_info = path_info[len(script_name):]
             environ["PATH_INFO"] = new_path_info
             
             # 2. Redirect /webdav -> /webdav/ to ensure relative links work in WsgiDAV
             if new_path_info == "" and not path_info.endswith("/"):
                 target_url = script_name + "/"
                 qs = environ.get("QUERY_STRING")
                 if qs:
                     target_url += "?" + qs
                 
                 start_response("301 Moved Permanently", [
                     ("Location", target_url),
                     ("Content-Length", "0")
                 ])
                 return [b""]
    
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
    logger.info("WebDAV server for FileHold (Community Tool)")
    logger.info(f"Serving on {protocol}://{host}:{port} ...")

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
        default_schema_name=args.default_schema_name,
        mount_path=args.mount_path
    )
    start_server(app, args.host, args.port, args.ssl_cert, args.ssl_key)


if __name__ == "__main__":
    run()

