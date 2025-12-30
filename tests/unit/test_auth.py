import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any
from webdav_server_for_filehold.auth import CustomDomainController


class TestCustomDomainController(unittest.TestCase):
    """
    Unit tests for the CustomDomainController class.
    """

    def setUp(self) -> None:
        """
        Set up the test environment.
        """
        self.config: Dict[str, str] = {"filehold_url": "http://test/CH/FileHold/"}
        self.auth = CustomDomainController(MagicMock(), self.config)
        self.environ: Dict[str, Any] = {}

    @patch('webdav_server_for_filehold.auth.Client')
    def test_basic_auth_user_success_no_cache(self, MockClient: MagicMock) -> None:
        """
        Test basic authentication success when user is not in cache.
        """
        # Setup
        mock_client = MockClient.return_value
        mock_client.service.StartSession.return_value = "session_123"
        mock_client.service.GetSessionInfo.return_value.UserGuid = "guid_123"

        # Execute
        result = self.auth.basic_auth_user("realm", "user", "pass", self.environ)

        # Verify
        self.assertTrue(result)
        self.assertEqual(self.environ["filehold.session_id"], "session_123")
        self.assertEqual(self.environ["filehold.user_guid"], "guid_123")
        mock_client.service.StartSession.assert_called_with("user", "pass", "CustomClient")

        # Verify cache update
        self.assertIn("user", self.auth._session_cache)
        self.assertEqual(self.auth._session_cache["user"]["session_id"], "session_123")
        # Check hash exists and is bytes
        self.assertIsInstance(self.auth._session_cache["user"]["password_hash"], bytes)
        # Verify it matches hash of "pass"
        import hashlib
        expected_hash = hashlib.sha256(b"pass").digest()
        self.assertEqual(self.auth._session_cache["user"]["password_hash"], expected_hash)

    @patch('webdav_server_for_filehold.auth.Client')
    def test_basic_auth_user_success_cache_hit(self, MockClient: MagicMock) -> None:
        """
        Test basic authentication success when user is in cache.
        """
        # Setup cache
        import hashlib
        p_hash = hashlib.sha256(b"pass").digest()
        self.auth._session_cache["user"] = {"password_hash": p_hash, "session_id": "session_old"}

        mock_client = MockClient.return_value
        # GetSessionInfo returns valid object (truthy)
        mock_client.service.GetSessionInfo.return_value.UserGuid = "guid_old"

        # Execute
        result = self.auth.basic_auth_user("realm", "user", "pass", self.environ)

        # Verify
        self.assertTrue(result)
        self.assertEqual(self.environ["filehold.session_id"], "session_old")
        # StartSession should NOT be called
        mock_client.service.StartSession.assert_not_called()
        # GetSessionInfo called to verify
        mock_client.service.GetSessionInfo.assert_any_call(sessionId="session_old")

    @patch('webdav_server_for_filehold.auth.Client')
    def test_basic_auth_user_cache_invalid_password(self, MockClient: MagicMock) -> None:
        """
        Test basic authentication failure when user is in cache but password is invalid.
        """
        # Setup cache
        import hashlib
        p_hash = hashlib.sha256(b"pass").digest()
        self.auth._session_cache["user"] = {"password_hash": p_hash, "session_id": "session_old"}

        mock_client = MockClient.return_value
        mock_client.service.StartSession.return_value = "session_new"
        mock_client.service.GetSessionInfo.return_value.UserGuid = "guid_new"

        # Execute with WRONG password
        result = self.auth.basic_auth_user("realm", "user", "wrong_pass", self.environ)

        # Verify
        self.assertTrue(result)
        self.assertEqual(self.environ["filehold.session_id"], "session_new")
        # StartSession SHOULD be called because cache password didn't match
        mock_client.service.StartSession.assert_called_with("user", "wrong_pass", "CustomClient")

    @patch('webdav_server_for_filehold.auth.Client')
    def test_basic_auth_user_cache_expired_session(self, MockClient: MagicMock) -> None:
        """
        Test basic authentication when user is in cache but session is expired.
        """
        # Setup cache
        import hashlib
        p_hash = hashlib.sha256(b"pass").digest()
        self.auth._session_cache["user"] = {"password_hash": p_hash, "session_id": "session_expired"}

        mock_client = MockClient.return_value
        # GetSessionInfo throws or returns None for expired session
        # Let's say it raises Exception
        mock_client.service.GetSessionInfo.side_effect = [Exception("Session expired"), MagicMock(UserGuid="guid_new")]
        mock_client.service.StartSession.return_value = "session_new"

        # Execute
        result = self.auth.basic_auth_user("realm", "user", "pass", self.environ)

        # Verify
        self.assertTrue(result)
        self.assertEqual(self.environ["filehold.session_id"], "session_new")
        # StartSession SHOULD be called
        mock_client.service.StartSession.assert_called_with("user", "pass", "CustomClient")

        # Cache should be updated
        self.assertEqual(self.auth._session_cache["user"]["session_id"], "session_new")

    def test_is_secret_valid(self) -> None:
        """
        Test the _is_secret_valid helper method.
        """
        import hashlib
        secret = "secret"
        stored_hash = hashlib.sha256(secret.encode('utf-8')).digest()

        self.assertTrue(self.auth._is_secret_valid("secret", stored_hash))
        self.assertFalse(self.auth._is_secret_valid("wrong", stored_hash))
        self.assertFalse(self.auth._is_secret_valid(None, stored_hash))
        self.assertFalse(self.auth._is_secret_valid("secret", None))

    @patch('webdav_server_for_filehold.auth.Client')
    def test_basic_auth_domain_user(self, MockClient: MagicMock) -> None:
        """
        Test basic authentication for a domain user.
        """
        # Setup
        mock_client = MockClient.return_value

        # Mock GetStoredDomains
        mock_domain = MagicMock()
        mock_domain.Name = "MyDomain"
        mock_domain.Id = 123
        mock_client.service.GetStoredDomains.return_value = [mock_domain]

        mock_client.service.StartSessionForDomainUser.return_value = "session_domain"
        mock_client.service.GetSessionInfo.return_value.UserGuid = "guid_domain"

        # Execute
        result = self.auth.basic_auth_user("realm", "MyDomain\\user", "pass", self.environ)

        # Verify
        self.assertTrue(result)
        self.assertEqual(self.environ["filehold.session_id"], "session_domain")
        mock_client.service.GetStoredDomains.assert_called_once()
        mock_client.service.StartSessionForDomainUser.assert_called_with("user", "pass", 123, "CustomClient")

    @patch('webdav_server_for_filehold.auth.Client')
    def test_basic_auth_local_domain_user(self, MockClient: MagicMock) -> None:
        """
        Test basic authentication for a local domain user.
        """
        # Setup
        mock_client = MockClient.return_value
        mock_client.service.StartSession.return_value = "session_local"
        mock_client.service.GetSessionInfo.return_value.UserGuid = "guid_local"

        # Execute for .\user
        result = self.auth.basic_auth_user("realm", ".\\user", "pass", self.environ)
        self.assertTrue(result)
        self.assertEqual(self.environ["filehold.session_id"], "session_local")
        mock_client.service.StartSession.assert_called_with("user", "pass", "CustomClient")

        # Reset mocks
        mock_client.reset_mock()
        mock_client.service.StartSession.return_value = "session_local_2"
        mock_client.service.GetSessionInfo.return_value.UserGuid = "guid_local_2"

        # Execute for local\user
        result2 = self.auth.basic_auth_user("realm", "local\\user2", "pass", self.environ)
        self.assertTrue(result2)
        mock_client.service.StartSession.assert_called_with("user2", "pass", "CustomClient")


if __name__ == '__main__':
    unittest.main()
