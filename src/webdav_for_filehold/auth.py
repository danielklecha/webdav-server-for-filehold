from wsgidav.dc.base_dc import BaseDomainController
from zeep import Client
from zeep.transports import Transport
import requests
import hashlib
import hmac
import threading
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, List, Dict, Any, Tuple, Union

logger = logging.getLogger(__name__)

class CustomDomainController(BaseDomainController):
    """
    Custom WsgiDAV Domain Controller for FileHold authentication.
    Handles user login, session caching, and domain-based authentication.
    """

    DEFAULT_FILEHOLD_URL = "http://localhost/FH/FileHold/"
    CLIENT_NAME = "CustomClient"
    CACHE_REFRESH_MINUTES = 1
    CACHE_LIFETIME_MINUTES = 60

    def __init__(self, wsgidav_app: Any, config: Dict[str, Any]):
        super().__init__(wsgidav_app, config)
        base_url = config.get("filehold_url", self.DEFAULT_FILEHOLD_URL)
        self.wsdl_url = f"{base_url}UserRoleManager/SessionManager.asmx?WSDL"
        # key: user_name, value: {'password_hash': bytes, 'session_id': str,
        # 'refresh_time': datetime, 'lifetime': datetime}
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_domain_realm(self, input_url: str, environ: Dict[str, Any]) -> str:
        """
        Get the domain realm for the request.

        Args:
            input_url: The URL being requested.
            environ: The WSGI environment.

        Returns:
            The domain realm string.
        """
        return "CustomWebDAV"

    def require_authentication(self, realm: str, environ: Dict[str, Any]) -> bool:
        """
        Check if authentication is required.

        Args:
            realm: The authentication realm.
            environ: The WSGI environment.

        Returns:
            True if authentication is required, False otherwise.
        """
        return True

    def get_permissions(self, realm: str, user_name: str, path: str, environ: Dict[str, Any]) -> List[str]:
        """
        Get permissions for the user on the given path.

        Args:
            realm: The authentication realm.
            user_name: The name of the authenticated user.
            path: The path being accessed.
            environ: The WSGI environment.

        Returns:
            A list of permission strings.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"get_permissions called for user={user_name}, path={path}")
        return ["all"]

    def supports_http_digest_auth(self) -> bool:
        """
        Check if HTTP Digest Authentication is supported.

        Returns:
            False as Digest Auth is not supported.
        """
        return False

    def is_readonly(self) -> bool:
        """
        Check if the provider is read-only.

        Returns:
            False, permitting write operations.
        """
        logger.debug("CustomProvider.is_readonly called")
        return False

    def supports_basic_auth(self) -> bool:
        """
        Check if Basic Authentication is supported.

        Returns:
            True as Basic Auth is supported.
        """
        return True

    def basic_auth_user(self, realm: str, user_name: str, password: str, environ: Dict[str, Any]) -> bool:
        """
        Authenticates a user against FileHold.

        Supports caching of sessions to avoid round-trips for every request.
        Handles both local and domain users.

        Args:
            realm: The authentication realm.
            user_name: The provided username.
            password: The provided password.
            environ: The WSGI environment.

        Returns:
            True if authentication is successful, False otherwise.
        """
        try:
            client = Client(self.wsdl_url)
            now = datetime.now(timezone.utc)
            session_id, session_info_obj = self._resolve_session(client, user_name, password, now)

            if session_id:
                return self._configure_request_env(session_id, session_info_obj, environ, client)
            return False
        except Exception as e:
            logger.error(f"SOAP Authentication failed: {e}")
            return False

    def _is_secret_valid(self, input_secret: Union[str, bytes], stored_hash: bytes) -> bool:
        """
        Securely compares the input secret against the stored hash.
        """
        if not input_secret or not stored_hash:
            return False
        if isinstance(input_secret, str):
            input_secret = input_secret.encode('utf-8')
        input_hash = hashlib.sha256(input_secret).digest()
        return hmac.compare_digest(input_hash, stored_hash)

    def _cleanup_expired_sessions(self, now: datetime) -> None:
        """Removes expired sessions from the cache."""
        to_remove = [
            user for user, data in self._session_cache.items()
            if data.get('lifetime') and data['lifetime'] < now
        ]
        for user in to_remove:
            del self._session_cache[user]

    def _get_cached_session(self, user_name: str, password: str, now: datetime) -> Tuple[Optional[str], bool, Optional[Dict[str, Any]]]:
        """Retrieves a valid session from the cache if credentials match."""
        session_id = None
        should_refresh = False
        cached_entry = self._session_cache.get(user_name)

        if cached_entry:
            pass_valid = self._is_secret_valid(password, cached_entry['password_hash'])
            if pass_valid:
                session_id = cached_entry['session_id']
                if not (cached_entry.get('refresh_time') and now < cached_entry['refresh_time']):
                    should_refresh = True

        return session_id, should_refresh, cached_entry

    def _remove_cached_session(self, user_name: str, session_id: str) -> None:
        """Thread-safe removal of a session from cache if it matches the id."""
        with self._lock:
            if user_name in self._session_cache and self._session_cache[user_name]['session_id'] == session_id:
                del self._session_cache[user_name]

    def _refresh_session(self, client: Client, user_name: str, session_id: str, cached_entry: Dict[str, Any], now: datetime) -> Tuple[Optional[str], Any]:
        """Refreshes the session with FileHold to ensure it's still valid."""
        try:
            session_info_obj = client.service.GetSessionInfo(sessionId=session_id)
            if session_info_obj:
                with self._lock:
                    if user_name in self._session_cache:
                        self._session_cache[user_name]['refresh_time'] = now + timedelta(minutes=self.CACHE_REFRESH_MINUTES)
                        self._session_cache[user_name]['lifetime'] = now + timedelta(minutes=self.CACHE_LIFETIME_MINUTES)
                return session_id, session_info_obj
        except Exception:
            pass  # Fall through to removal

        # If we are here, either session_info_obj was None, or an exception occurred
        self._remove_cached_session(user_name, cached_entry['session_id'])
        return None, None

    def _authenticate_domain_user(self, client: Client, domain: str, login: str, password: str) -> Optional[str]:
        """Authenticates a domain user."""
        try:
            domains = client.service.GetStoredDomains()
            domain_id = None
            if domains:
                # Find the domain ID case-insensitively
                for d in domains:
                    if d.Name and d.Name.lower() == domain:
                        domain_id = d.Id
                        break

            if domain_id:
                return client.service.StartSessionForDomainUser(login, password, domain_id, self.CLIENT_NAME)
            else:
                logger.warning(f"Domain '{domain}' not found.")
                return None
        except Exception as e:
            logger.error(f"Error authenticating domain user: {e}")
            return None

    def _authenticate_local_user(self, client: Client, login: str, password: str) -> str:
        """Authenticates a local user."""
        return client.service.StartSession(login, password, self.CLIENT_NAME)

    def _authenticate_with_credentials(self, client: Client, user_name: str, password: str) -> Optional[str]:
        """Authenticates using credentials against FileHold (Domain or Local)."""
        domain = None
        login = user_name

        # Parse domain\\user format
        if "\\" in user_name:
            parts = user_name.split("\\", 1)
            if len(parts) == 2:
                domain_candidate = parts[0].lower()
                login = parts[1]
                if domain_candidate not in (".", "local"):
                    domain = domain_candidate

        if domain:
            return self._authenticate_domain_user(client, domain, login, password)
        else:
            return self._authenticate_local_user(client, login, password)

    def _update_session_cache(self, user_name: str, password: str, session_id: str, now: datetime) -> None:
        """Updates the session cache with the new session."""
        p_hash = hashlib.sha256(password.encode('utf-8')).digest()
        with self._lock:
            self._session_cache[user_name] = {
                'password_hash': p_hash,
                'session_id': session_id,
                'refresh_time': now + timedelta(minutes=self.CACHE_REFRESH_MINUTES),
                'lifetime': now + timedelta(minutes=self.CACHE_LIFETIME_MINUTES)
            }

    def _resolve_session(self, client: Client, user_name: str, password: str, now: datetime) -> Tuple[Optional[str], Any]:
        """Resolves the session ID, handling cache and refresh."""
        session_id = None
        should_refresh = False
        cached_entry = None
        session_info_obj = None

        with self._lock:
            self._cleanup_expired_sessions(now)
            session_id, should_refresh, cached_entry = self._get_cached_session(user_name, password, now)

        if should_refresh and session_id and cached_entry:
            session_id, session_info_obj = self._refresh_session(client, user_name, session_id, cached_entry, now)

        if not session_id:
            session_id = self._authenticate_with_credentials(client, user_name, password)
            if session_id:
                self._update_session_cache(user_name, password, session_id, now)

        return session_id, session_info_obj

    def _configure_request_env(self, session_id: str, session_info_obj: Any, environ: Dict[str, Any], client: Client) -> bool:
        """Configures the request environment with session details."""
        environ["filehold.session_id"] = session_id
        try:
            if not session_info_obj:
                session_info_obj = client.service.GetSessionInfo(sessionId=session_id)

            if session_info_obj and hasattr(session_info_obj, 'UserGuid'):
                environ["filehold.user_guid"] = session_info_obj.UserGuid
        except Exception as ex:
            logger.error(f"Failed to get session info: {ex}")
            return False

        return True
