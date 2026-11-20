"""
Tests for remote codejail execution.
"""

import json
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from requests.exceptions import HTTPError
from simplejson import JSONDecodeError

from xblock_problem.capa.safe_exec.exceptions import CodejailServiceParseError, CodejailServiceStatusError
from xblock_problem.capa.safe_exec.remote_exec import get_remote_exec


class TestRemoteExec(TestCase):
    """Tests for remote_exec."""

    @override_settings(
        CODE_JAIL_REST_SERVICE_HOST="http://localhost",
        CODE_JAIL_REST_SERVICE_REMOTE_EXEC="xblock_problem.capa.safe_exec.remote_exec.send_safe_exec_request_v0",
    )
    @patch("requests.post")
    def test_json_encode(self, mock_post):
        """Verify that get_remote_exec correctly JSON-encodes payload with globals."""
        get_remote_exec(
            {
                "code": "out = 1 + 1",
                "globals_dict": {"some_data": b"bytes", "unusable": object()},
                "extra_files": None,
            }
        )

        mock_post.assert_called_once()
        data_arg = mock_post.call_args_list[0][1]["data"]
        payload = json.loads(data_arg["payload"])
        assert payload["globals_dict"] == {"some_data": "bytes"}

    @override_settings(
        CODE_JAIL_REST_SERVICE_HOST="http://localhost",
        CODE_JAIL_REST_SERVICE_REMOTE_EXEC="xblock_problem.capa.safe_exec.remote_exec.send_safe_exec_request_v0",
    )
    @patch("requests.post")
    def test_status_error(self, mock_post):
        """A non-2xx response raises CodejailServiceStatusError with an untranslated message."""
        mock_post.return_value.raise_for_status.side_effect = HTTPError("500")

        with pytest.raises(CodejailServiceStatusError, match="^Codejail API Service invalid response.$"):
            get_remote_exec({"code": "", "globals_dict": {}, "extra_files": None})

    @override_settings(
        CODE_JAIL_REST_SERVICE_HOST="http://localhost",
        CODE_JAIL_REST_SERVICE_REMOTE_EXEC="xblock_problem.capa.safe_exec.remote_exec.send_safe_exec_request_v0",
    )
    @patch("requests.post")
    def test_parse_error(self, mock_post):
        """An invalid JSON response raises CodejailServiceParseError with an untranslated message."""
        mock_post.return_value = Mock(content=b"not json")
        mock_post.return_value.json.side_effect = JSONDecodeError("bad", "not json", 0)

        with pytest.raises(
            CodejailServiceParseError, match="^Invalid JSON response received from codejail api service.$"
        ):
            get_remote_exec({"code": "", "globals_dict": {}, "extra_files": None})
