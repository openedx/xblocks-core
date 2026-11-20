"""Capa's specialized use of codejail.safe_exec."""

import hashlib

from codejail.safe_exec import SafeExecException, json_safe
from django.core.exceptions import ImproperlyConfigured
from edx_django_utils.monitoring import function_trace

from . import lazymod
from .exceptions import CodejailServiceParseError, CodejailServiceStatusError, CodejailServiceUnavailable
from .remote_exec import get_codejail_rest_service_host, get_remote_exec

# Establish the Python environment for Capa.
# Capa assumes float-friendly division always.
# The name "random" is a properly-seeded stand-in for the random module.
CODE_PROLOG = """\
from __future__ import absolute_import, division

import os

# openblas is a math library used by numpy. It will try to allocate multiple
# threads by default, but this may exceed resource limits and cause a segfault.
# Limiting to 1 thread will prevent this in all configurations.
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Any code that uses the tempfile module to create temporary files should use
# the ./tmp directory that codejail creates in each sandbox, rather than trying
# to use a global temp dir (which should be blocked by AppArmor anyhow).
# This is needed for matplotlib among other things.
#
# matplotlib will complain on stderr about the non-standard temp dir if we
# don't explicitly tell it "no really, use this". This pollutes the output
# when codejail returns an error message (which includes stderr). So we also
# set MPLCONFIGDIR as a special case.
os.environ["TMPDIR"] = os.getcwd() + "/tmp"
os.environ["MPLCONFIGDIR"] = os.environ["TMPDIR"]

import random2 as random_module
import sys
from six.moves import xrange

random = random_module.Random(%r)
random.Random = random_module.Random
random.SystemRandom = random_module.SystemRandom
sys.modules['random'] = random
"""

ASSUMED_IMPORTS = [
    ("numpy", "numpy"),
    ("math", "math"),
    ("scipy", "scipy"),
    ("calc", "calc"),
    ("eia", "eia"),
    ("chemcalc", "chem.chemcalc"),
    ("chemtools", "chem.chemtools"),
    ("miller", "chem.miller"),
    ("draganddrop", "verifiers.draganddrop"),
]

# We'll need the code from lazymod.py for use in safe_exec, so read it now.
LAZYMOD_PY_FILE = lazymod.__file__
if LAZYMOD_PY_FILE.endswith("c"):
    LAZYMOD_PY_FILE = LAZYMOD_PY_FILE[:-1]

with open(LAZYMOD_PY_FILE, encoding="utf-8") as f:
    lazymod_py = f.read()

LAZY_IMPORTS = [lazymod_py]
for name, modname in ASSUMED_IMPORTS:
    LAZY_IMPORTS.append(f"{name} = LazyModule('{modname}')\n")

LAZY_IMPORTS = "".join(LAZY_IMPORTS)


def update_hash(hasher, obj):
    """
    Update a `hashlib` hasher with a nested object.

    To properly cache nested structures, we need to compute a hash from the
    entire structure, canonicalizing at every level.

    `hasher`'s `.update()` method is called a number of times, touching all of
    `obj` in the process.  Only primitive JSON-safe types are supported.

    """
    hasher.update(str(type(obj)).encode())
    if isinstance(obj, (tuple, list)):
        for e in obj:
            update_hash(hasher, e)
    elif isinstance(obj, dict):
        for k in sorted(obj):
            update_hash(hasher, k)
            update_hash(hasher, obj[k])
    else:
        hasher.update(repr(obj).encode())


# pylint: disable=too-many-arguments,too-many-branches,too-many-locals,too-many-positional-arguments,too-many-statements
@function_trace("safe_exec")
def safe_exec(
    code,
    globals_dict,
    random_seed=None,
    python_path=None,
    extra_files=None,
    cache=None,
    limit_overrides_context=None,
    slug=None,
    unsafely=False,
    gettext=None,
):
    """
    Execute python code safely.

    `code` is the Python code to execute.  It has access to the globals in `globals_dict`,
    and any changes it makes to those globals are visible in `globals_dict` when this
    function returns.

    `random_seed` will be used to see the `random` module available to the code.

    `python_path` is a list of filenames or directories to add to the Python
    path before execution.  If the name is not in `extra_files`, then it will
    also be copied into the sandbox.

    `extra_files` is a list of (filename, contents) pairs.  These files are
    created in the sandbox.

    `cache` is an object with .get(key) and .set(key, value) methods.  It will be used
    to cache the execution, taking into account the code, the values of the globals,
    and the random seed.

    `limit_overrides_context` is an optional context name used to select
    resource-limit overrides configured with the setting
    CODE_JAIL["limit_overrides"] on the remote Codejail service. Any matching
    overrides are merged into the service's default limits for this execution.
    If the context is omitted or unmatched, the service's defaults apply
    unchanged. Problem blocks pass the course-run key when available, allowing
    deployments to configure different limits for specific course runs.

    `slug` is an arbitrary string, a description that's meaningful to the
    caller, that will be used in log messages.

    `gettext` translates the Codejail service error messages. Problem blocks pass their
    ``i18n`` service's ``gettext`` so the messages come from the block's own catalog.
    If omitted, the messages are left in English.

    `unsafely` is retained as parameter for compatibility but raises
    `ImproperlyConfigured` when set to true, which only happens for
    courses in `COURSES_WITH_UNSAFE_CODE`.
    """
    if unsafely:
        raise ImproperlyConfigured(
            "Unsandboxed code execution is no longer supported. Remove affected courses from "
            "COURSES_WITH_UNSAFE_CODE and configure per-course limits on the Codejail service instead; "
            "see https://github.com/openedx/openedx-platform/issues/36639"
        )

    # Check the cache for a previous result.
    if cache:
        safe_globals = json_safe(globals_dict)
        md5er = hashlib.md5()
        md5er.update(repr(code).encode("utf-8"))
        update_hash(md5er, safe_globals)
        key = f"safe_exec.{random_seed!r}.{md5er.hexdigest()}"
        cached = cache.get(key)
        if cached is not None:
            # We have a cached result.  The result is a pair: the exception
            # message, if any, else None; and the resulting globals dictionary.
            emsg, cleaned_results = cached
            globals_dict.update(cleaned_results)
            if emsg:
                raise SafeExecException(emsg)
            return

    # Create the complete code we'll run.
    code_prolog = CODE_PROLOG % random_seed

    if not get_codejail_rest_service_host():
        raise ImproperlyConfigured(
            "Capa Python execution requires a remote Codejail service. "
            "Configure CODE_JAIL_REST_SERVICE_HOST with the service address."
        )

    data = {
        "code": code_prolog + LAZY_IMPORTS + code,
        "globals_dict": globals_dict,
        "python_path": python_path,
        "limit_overrides_context": limit_overrides_context,
        "slug": slug,
        "extra_files": extra_files,
    }

    try:
        emsg, exception = get_remote_exec(data)
    except (CodejailServiceUnavailable, CodejailServiceStatusError, CodejailServiceParseError) as err:
        if gettext is None or not err.args:
            raise
        # The messages are marked with gettext_noop in remote_exec, so translating a variable is intended.
        raise type(err)(gettext(str(err.args[0]))) from err  # pylint: disable=translation-of-non-string

    # Put the result back in the cache.  This is complicated by the fact that
    # the globals dict might not be entirely serializable.
    if cache:
        cleaned_results = json_safe(globals_dict)
        cache.set(key, (emsg, cleaned_results))

    # If an exception happened, raise it now.
    if exception:
        raise exception
