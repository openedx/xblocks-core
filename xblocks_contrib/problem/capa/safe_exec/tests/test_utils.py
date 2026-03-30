"""
Test utilities for CodeJail safe execution.

This module a small wrapper around not_safe_exec in order to mock a remote
CodeJail REST service call. It is intended to be wired using
`CODE_JAIL_REST_SERVICE_REMOTE_EXEC` setting for test runs.
"""

import sys
from typing import Any

from codejail.safe_exec import SafeExecException, not_safe_exec


def send_safe_exec_request_locally(data: dict[str, Any]) -> tuple[str | None, Exception | None]:
    """
    Execute a Codejail payload locally using CodeJail's `not_safe_exec`.

    `not_safe_exec` does not properly clean up the environment after running,
    causing a stale cache between runs that triggers test failures when loading
    a Python library. We run a cleanup routine that restores the loaded modules
    and clear the zipimporter cache.

    Arguments:
        data (dict): Payload with the same shape as the remote service request:
            code, globals_dict, python_path, extra_files,
            limit_overrides_context, slug, unsafely.

    Returns:
        tuple: ``(emsg, exception)``. ``emsg`` is the error message string if
        the executed code raised, otherwise ``None``. ``exception`` is a
        ``SafeExecException`` when the code raised, otherwise ``None``.
    """
    code = data["code"]
    globals_dict = data["globals_dict"]
    python_path = data.get("python_path") or []
    extra_files = data.get("extra_files") or []
    slug = data.get("slug")
    limit_overrides_context = data.get("limit_overrides_context")

    original_path = list(sys.path)
    original_modules = set(sys.modules.keys())

    try:
        not_safe_exec(
            code,
            globals_dict,
            python_path=python_path,
            extra_files=extra_files,
            slug=slug,
            limit_overrides_context=limit_overrides_context,
        )
    except SafeExecException as exc:
        return str(exc), exc
    finally:
        sys.path = original_path
        for mod_name in list(sys.modules.keys()):
            if mod_name not in original_modules:
                del sys.modules[mod_name]
        for archive_path in python_path:
            if importer := sys.path_importer_cache[archive_path]:
                importer.invalidate_caches()
        sys.path_importer_cache.clear()
    return None, None
