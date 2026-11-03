"""
Tests for remote codejail execution.
"""

import json
from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from xblocks_contrib.problem.capa.safe_exec.remote_exec import get_remote_exec


class TestRemoteExec(TestCase):
    """Tests for remote_exec."""

    @override_settings(
        ENABLE_CODEJAIL_REST_SERVICE=True,
        CODE_JAIL_REST_SERVICE_HOST="http://localhost",
        CODE_JAIL_REST_SERVICE_REMOTE_EXEC=(
            "xblocks_contrib.problem.capa.safe_exec.remote_exec.send_safe_exec_request_v0"
        ),
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
