import argparse
import logging
import typing

from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp

# Import from local modules
from .auth import CustomDomainController
from .provider import CustomProvider


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
        "--verbose",
        type=int,
        choices=[0, 1, 2, 3],
        default=3,
        help="Logging verbosity (0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG)"
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


def _configure_logging(verbose: int) -> None:
    """
    Configures logging based on verbosity level.

    Args:
        verbose (int): The verbosity level (0-3).
    """
    log_level_map = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG
    }
    log_level = log_level_map.get(verbose, logging.DEBUG)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s.%(msecs)03d - %(levelname)-8s: %(message)s',
        datefmt='%H:%M:%S'
    )


def _create_app_config(args: argparse.Namespace) -> typing.Dict[str, typing.Any]:
    """
    Creates the WsgiDAV app configuration dictionary.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Returns:
        typing.Dict[str, typing.Any]: The WsgiDAV configuration dictionary.
    """
    # Ensure URL ends with slash
    filehold_url: str = args.filehold_url
    if not filehold_url.endswith("/"):
        filehold_url += "/"

    return {
        "provider_mapping": {
            "/": CustomProvider(
                filehold_url,
                args.create_category_in_drawer,
                args.default_schema_name
            )
        },
        "http_authenticator": {
            "domain_controller": CustomDomainController,
            "accept_basic": True,
            "accept_digest": False,
            "default_to_digest": False,
        },
        "verbose": args.verbose,
        "host": args.host,
        "port": args.port,
        "filehold_url": filehold_url  # Pass to DC via config
    }


def _start_server(config: typing.Dict[str, typing.Any], ssl_cert: typing.Optional[str], ssl_key: typing.Optional[str]) -> None:
    """
    Initializes and starts the WSGI server.

    Args:
        config (typing.Dict[str, typing.Any]): The WsgiDAV configuration.
        ssl_cert (typing.Optional[str]): Path to SSL certificate.
        ssl_key (typing.Optional[str]): Path to SSL key.
    """
    app = WsgiDAVApp(config)

    server = wsgi.Server(
        bind_addr=(config["host"], config["port"]),
        wsgi_app=app,
    )

    protocol = "http"
    if ssl_cert and ssl_key:
        from cheroot.ssl.builtin import BuiltinSSLAdapter
        server.ssl_adapter = BuiltinSSLAdapter(ssl_cert, ssl_key)
        protocol = "https"

    try:
        logging.info(f"Serving on {protocol}://{config['host']}:{config['port']} ...")
        logging.info(f"Targeting FileHold at {config['filehold_url']}")
        server.start()
    except KeyboardInterrupt:
        logging.info("Stopping...")
        server.stop()


def run() -> None:
    """
    Entry point for the WebDAV server.
    Parses arguments, configures logging, and starts the WsgiDAV app.
    """
    args = _parse_arguments()
    _configure_logging(args.verbose)
    config = _create_app_config(args)
    _start_server(config, args.ssl_cert, args.ssl_key)


if __name__ == "__main__":
    run()

