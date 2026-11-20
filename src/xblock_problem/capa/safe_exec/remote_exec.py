"""
Helper methods related to safe exec.
"""

import json
import logging
from importlib import import_module

import requests
from codejail.safe_exec import SafeExecException, json_safe
from django.conf import settings
from django.utils.translation import gettext_noop
from requests.exceptions import HTTPError, RequestException
from simplejson import JSONDecodeError

from .exceptions import CodejailServiceParseError, CodejailServiceStatusError, CodejailServiceUnavailable

log = logging.getLogger(__name__)


def get_codejail_rest_service_host():
    """Return the configured Codejail service host, if any."""
    return getattr(settings, "CODE_JAIL_REST_SERVICE_HOST", None)


def get_remote_exec(*args, **kwargs):
    """Get remote exec function based on setting and executes it."""
    remote_exec_function_name = settings.CODE_JAIL_REST_SERVICE_REMOTE_EXEC
    try:
        mod_name, func_name = remote_exec_function_name.rsplit(".", 1)
        remote_exec_module = import_module(mod_name)
        remote_exec_function = getattr(remote_exec_module, func_name)
        if not remote_exec_function:
            remote_exec_function = send_safe_exec_request_v0
    except ModuleNotFoundError:
        return send_safe_exec_request_v0(*args, **kwargs)
    return remote_exec_function(*args, **kwargs)


def get_codejail_rest_service_endpoint():
    """Return the endpoint URL for the codejail REST service."""
    return f"{get_codejail_rest_service_host()}/api/v0/code-exec"


def send_safe_exec_request_v0(data):
    """
    Sends a request to a codejail api service forwarding required code and files.

    Error messages are marked with ``gettext_noop`` and left untranslated here, because this function
    has no block (and so no translation catalog). ``safe_exec`` translates them with the caller's ``gettext``.
    Arguments:
        data: Dict containing code and other parameters required for jailed code execution.
        It also includes extra_files (python_lib.zip) required by the codejail execution.
    Returns:
        Response received from codejail api service
    """
    globals_dict = data["globals_dict"]
    extra_files = data.pop("extra_files")

    codejail_service_endpoint = get_codejail_rest_service_endpoint()

    # In rare cases an XBlock might introduce `bytes` objects (or other
    # non-JSON-serializable objects) into the globals dict. The codejail service
    # (via the codejail library) will call `json_safe` on the globals before
    # JSON-encoding for the sandbox input, but here we need to call it earlier
    # in the process so we can even transport the globals *to* the codejail
    # service. Otherwise, we may get a TypeError when constructing the payload.
    #
    # This is a lossy operation (non-serializable objects will be dropped, and
    # bytes converted to strings) but it is the same lossy operation that
    # codejail will perform anyhow -- and it should be idempotent.
    data_send = {**data}
    data_send["globals_dict"] = json_safe(data_send["globals_dict"])

    payload = json.dumps(data_send)

    try:
        response = requests.post(
            codejail_service_endpoint,
            files=extra_files,
            data={"payload": payload},
            timeout=(settings.CODE_JAIL_REST_SERVICE_CONNECT_TIMEOUT, settings.CODE_JAIL_REST_SERVICE_READ_TIMEOUT),
        )

    except RequestException as err:
        log.error(
            "Failed to connect to codejail api service: url=%s, params=%s", codejail_service_endpoint, str(payload)
        )
        raise CodejailServiceUnavailable(
            gettext_noop("Codejail API Service is unavailable. Please try again in a few minutes.")
        ) from err

    try:
        response.raise_for_status()
    except HTTPError as err:
        raise CodejailServiceStatusError(gettext_noop("Codejail API Service invalid response.")) from err

    try:
        response_json = response.json()
    except JSONDecodeError as err:
        log.error("Invalid JSON response received from codejail api service: Response_Content=%s", response.content)
        raise CodejailServiceParseError(
            gettext_noop("Invalid JSON response received from codejail api service.")
        ) from err

    emsg = response_json.get("emsg")
    exception = None

    if emsg:
        exception_msg = f"{emsg}. For more information check Codejail Service logs."
        exception = SafeExecException(exception_msg)

    globals_dict.update(response_json.get("globals_dict"))

    return emsg, exception
