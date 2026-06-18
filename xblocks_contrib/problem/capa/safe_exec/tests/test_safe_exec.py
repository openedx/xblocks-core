"""Test safe_exec.py"""

import hashlib
import io
import textwrap
import unittest
import zipfile

import pytest
import random2 as random
from codejail import jail_code
from codejail.django_integration import ConfigureCodeJailMiddleware
from codejail.safe_exec import SafeExecException
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.test import override_settings
from six import unichr
from six.moves import range

from xblocks_contrib.problem.capa.safe_exec import safe_exec, update_hash
from xblocks_contrib.problem.capa.safe_exec.remote_exec import is_codejail_rest_service_enabled
from xblocks_contrib.problem.capa.tests.test_util import UseUnsafeCodejail


def make_python_library_zip_bytes():
    """
    Make a simple course library ZIP file, returning the bytes.

    Contains one module, `constant.py` with a single constant `THE_CONST`.
    """
    memfile = io.BytesIO()
    with zipfile.ZipFile(memfile, "w") as z:
        z.writestr(
            "constant.py",
            textwrap.dedent("""
                THE_CONST = 23
            """),
        )

    memfile.seek(0)
    return memfile.read()


PYTHON_LIB_BYTES = make_python_library_zip_bytes()


class TestSafeExec(unittest.TestCase):
    """Unit tests for verifying functionality and restrictions of safe_exec."""

    def test_set_values(self):
        """Verify assignment of values in safe_exec."""
        g = {}
        safe_exec("a = 17", g)
        assert g["a"] == 17

    def test_division(self):
        """Verify division operation in safe_exec."""
        g = {}
        # Future division: 1/2 is 0.5.
        safe_exec("a = 1/2", g)
        assert g["a"] == 0.5

    def test_assumed_imports(self):
        """Check assumed standard imports in safe_exec."""
        g = {}
        # Math is always available.
        safe_exec("a = int(math.pi)", g)
        assert g["a"] == 3

    def test_random_seeding(self):
        """Test predictable random results with seeding in safe_exec."""
        g = {}
        r = random.Random(17)
        rnums = [r.randint(0, 999) for _ in range(100)]

        # Without a seed, the results are unpredictable
        safe_exec("rnums = [random.randint(0, 999) for _ in xrange(100)]", g)
        assert g["rnums"] != rnums

        # With a seed, the results are predictable
        safe_exec("rnums = [random.randint(0, 999) for _ in xrange(100)]", g, random_seed=17)
        assert g["rnums"] == rnums

    def test_random_is_still_importable(self):
        """Ensure random module works with seeding in safe_exec."""
        g = {}
        r = random.Random(17)
        rnums = [r.randint(0, 999) for _ in range(100)]

        # With a seed, the results are predictable even from the random module
        safe_exec("import random\nrnums = [random.randint(0, 999) for _ in xrange(100)]\n", g, random_seed=17)
        assert g["rnums"] == rnums

    def test_python_lib(self):
        """Test importing Python library from custom path in safe_exec."""
        g = {}
        safe_exec(
            "import constant; a = constant.THE_CONST",
            g,
            python_path=["python_lib.zip"],
            extra_files={"python_lib.zip": PYTHON_LIB_BYTES},
        )

    def test_raising_exceptions(self):
        """Ensure exceptions are raised correctly in safe_exec."""
        g = {}
        with pytest.raises(SafeExecException) as cm:
            safe_exec("1/0", g)
        assert "ZeroDivisionError" in str(cm.value)


class TestSafeOrNot(unittest.TestCase):
    """Tests to verify safe vs unsafe execution behavior of code jail."""

    def test_cant_do_something_forbidden(self):
        """
        Demonstrates that running unsafe code inside the code jail
        throws SafeExecException, protecting the calling process.

        This test is skipped unless a local or remote CodeJail service is
        properly configured. In xblocks-contrib, the test **will pass**
        when the CodeJail REST service is running and the following setting
        is enabled:

            @override_settings(ENABLE_CODEJAIL_REST_SERVICE=True)

        Developers working on CodeJail integration or advanced CAPA logic
        are encouraged to run this test locally with CodeJail configured.

        See setup instructions:
        * in-platform setup:
        https://github.com/openedx/xblocks-contrib/blob/main/xblocks_contrib/problem/capa/safe_exec/README.rst
        * remote setup (using Tutor):
        https://github.com/eduNEXT/tutor-contrib-codejail
        """
        # If in-platform codejail isn't configured...
        if not jail_code.is_configured("python"):
            # ...AND if remote codejail isn't configured...
            if not is_codejail_rest_service_enabled():
                # ...then skip this test.
                pytest.skip(reason="Local or remote codejail has to be configured and enabled to run this test.")

        g = {}
        with pytest.raises(SafeExecException) as cm:
            safe_exec("import sys; sys.exit(1)", g)
        assert "SystemExit" not in str(cm)
        assert "Couldn't execute jailed code" in str(cm)


class TestLimitConfiguration(unittest.TestCase):
    """
    Test that resource limits can be configured and overriden via Django settings.

    We just test that the limits passed to `codejail` as we expect them to be.
    Actual resource limiting tests are within the `codejail` package itself.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Make a copy of codejail settings just for this test class.
        # Set a global REALTIME limit of 100.
        # Set a REALTIME limit override of 200 for a special course.
        cls.test_codejail_settings = (getattr(settings, "CODE_JAIL", None) or {}).copy()
        cls.test_codejail_settings["limits"] = {
            "REALTIME": 100,
        }
        cls.test_codejail_settings["limit_overrides"] = {
            "course-v1:my+special+course": {"REALTIME": 200, "NPROC": 30},
        }
        cls.configure_codejail(cls.test_codejail_settings)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        # Re-apply original configuration.
        cls.configure_codejail(getattr(settings, "CODE_JAIL", None) or {})

    @staticmethod
    def configure_codejail(codejail_settings):
        """
        Given a `settings.CODE_JAIL` dictionary, apply it to the codejail package.

        We use the `ConfigureCodeJailMiddleware` that comes with codejail.
        """
        with override_settings(CODE_JAIL=codejail_settings):
            # To apply `settings.CODE_JAIL`, we just intialize an instance of the
            # middleware class. We expect it to apply to changes, and then raise
            # "MiddlewareNotUsed" to indicate that its work is done.
            # This is exactly how the settings are applied in production (except the
            # middleware is automatically initialized because it's an element of
            # `settings.MIDDLEWARE`).
            try:
                ConfigureCodeJailMiddleware(get_response=lambda request: None)
            except MiddlewareNotUsed:
                pass

    def test_effective_limits_reflect_configuration(self):
        """
        Test that `get_effective_limits` returns configured limits with overrides
        applied correctly.
        """
        # REALTIME has been configured with a global limit.
        # Check it with no overrides context.
        assert jail_code.get_effective_limits()["REALTIME"] == 100

        # Now check REALTIME with an overrides context that we haven't configured.
        # Should be the same.
        assert jail_code.get_effective_limits("random-context-name")["REALTIME"] == 100

        # Now check REALTIME limit for a special course.
        # It should be overriden.
        assert jail_code.get_effective_limits("course-v1:my+special+course")["REALTIME"] == 200

        # We haven't configured a limit for NPROC.
        # It should use the codejail default.
        assert jail_code.get_effective_limits()["NPROC"] == 15

        # But we have configured an NPROC limit override for a special course.
        assert jail_code.get_effective_limits("course-v1:my+special+course")["NPROC"] == 30


class DictCache:
    """A cache implementation over a simple dict, for testing."""

    def __init__(self, d):
        self.cache = d

    def get(self, key):
        """Get value from cache by key with length check."""
        # Actual cache implementations have limits on key length
        assert len(key) <= 250
        return self.cache.get(key)

    def set(self, key, value):
        """Set value in cache by key with length check."""
        # Actual cache implementations have limits on key length
        assert len(key) <= 250
        self.cache[key] = value


@UseUnsafeCodejail()
class TestSafeExecCaching(unittest.TestCase):
    """Test that caching works on safe_exec."""

    def test_cache_miss_then_hit(self):
        """Test caching works on miss and hit in safe_exec."""
        g = {}
        cache = {}

        # Cache miss
        safe_exec("a = int(math.pi)", g, cache=DictCache(cache))
        assert g["a"] == 3
        # A result has been cached
        assert list(cache.values())[0] == (None, {"a": 3})

        # Fiddle with the cache, then try it again.
        cache[list(cache.keys())[0]] = (None, {"a": 17})

        g = {}
        safe_exec("a = int(math.pi)", g, cache=DictCache(cache))
        assert g["a"] == 17

    def test_cache_large_code_chunk(self):
        """Test caching handles large code chunks."""
        # Caching used to die on memcache with more than 250 bytes of code.
        # Check that it doesn't any more.
        code = "a = 0\n" + ("a += 1\n" * 12345)

        g = {}
        cache = {}
        safe_exec(code, g, cache=DictCache(cache))
        assert g["a"] == 12345

    def test_cache_exceptions(self):
        """Test caching of exceptions in safe_exec."""
        # Used to be that running code that raised an exception didn't cache
        # the result.  Check that now it does.
        code = "1/0"
        g = {}
        cache = {}
        with pytest.raises(SafeExecException):
            safe_exec(code, g, cache=DictCache(cache))

        # The exception should be in the cache now.
        assert len(cache) == 1
        cache_exc_msg, cache_globals = list(cache.values())[0]  # pylint: disable=unused-variable
        assert "ZeroDivisionError" in cache_exc_msg

        # Change the value stored in the cache, the result should change.
        cache[list(cache.keys())[0]] = ("Hey there!", {})

        with pytest.raises(SafeExecException):
            safe_exec(code, g, cache=DictCache(cache))

        assert len(cache) == 1
        cache_exc_msg, cache_globals = list(cache.values())[0]
        assert "Hey there!" == cache_exc_msg

        # Change it again, now no exception!
        cache[list(cache.keys())[0]] = (None, {"a": 17})
        safe_exec(code, g, cache=DictCache(cache))
        assert g["a"] == 17

    def test_unicode_submission(self):
        """Test safe_exec handles non-ASCII unicode."""
        # Check that using non-ASCII unicode does not raise an encoding error.
        # Try several non-ASCII unicode characters.
        for code in [129, 500, 2**8 - 1, 2**16 - 1]:
            code_with_unichr = str("# ") + unichr(code)
            try:
                safe_exec(code_with_unichr, {}, cache=DictCache({}))
            except UnicodeEncodeError:
                self.fail(f"Tried executing code with non-ASCII unicode: {code}")


class TestUpdateHash(unittest.TestCase):
    """Test the safe_exec.update_hash function to be sure it canonicalizes properly."""

    def hash_obj(self, obj):
        """Return the md5 hash that `update_hash` makes us."""
        md5er = hashlib.md5()
        update_hash(md5er, obj)
        return md5er.hexdigest()

    def equal_but_different_dicts(self):
        """
        Make two equal dicts with different key order.

        Simple literals won't do it.  Filling one and then shrinking it will
        make them different.

        """
        d1 = {k: 1 for k in "abcdefghijklmnopqrstuvwxyz"}
        d2 = {k: 1 for k in "bcdefghijklmnopqrstuvwxyza"}

        # Check that our dicts are equal, but with different key order.
        assert d1 == d2
        assert list(d1.keys()) != list(d2.keys())

        return d1, d2

    def test_simple_cases(self):
        """Test hashing of simple objects."""
        h1 = self.hash_obj(1)
        h10 = self.hash_obj(10)
        hs1 = self.hash_obj("1")

        assert h1 != h10
        assert h1 != hs1

    def test_list_ordering(self):
        """Test that list ordering affects hash."""
        h1 = self.hash_obj({"a": [1, 2, 3]})
        h2 = self.hash_obj({"a": [3, 2, 1]})
        assert h1 != h2

    def test_dict_ordering(self):
        """Test that dict ordering does not affect hash."""
        d1, d2 = self.equal_but_different_dicts()
        h1 = self.hash_obj(d1)
        h2 = self.hash_obj(d2)
        assert h1 == h2

    def test_deep_ordering(self):
        """Test that nested structures are hashed consistently."""
        d1, d2 = self.equal_but_different_dicts()
        o1 = {"a": [1, 2, [d1], 3, 4]}
        o2 = {"a": [1, 2, [d2], 3, 4]}
        h1 = self.hash_obj(o1)
        h2 = self.hash_obj(o2)
        assert h1 == h2


@UseUnsafeCodejail()
class TestRealProblems(unittest.TestCase):
    """Unit tests for executing real problem code snippets safely."""

    def test_802x(self):
        "Test execution of real problem code snippet safely."
        code = textwrap.dedent("""\
            import math
            import random
            import numpy
            e=1.602e-19 #C
            me=9.1e-31  #kg
            mp=1.672e-27 #kg
            eps0=8.854e-12 #SI units
            mu0=4e-7*math.pi #SI units

            Rd1=random.randrange(1,30,1)
            Rd2=random.randrange(30,50,1)
            Rd3=random.randrange(50,70,1)
            Rd4=random.randrange(70,100,1)
            Rd5=random.randrange(100,120,1)

            Vd1=random.randrange(1,20,1)
            Vd2=random.randrange(20,40,1)
            Vd3=random.randrange(40,60,1)

            #R=[0,10,30,50,70,100] #Ohm
            #V=[0,12,24,36] # Volt

            R=[0,Rd1,Rd2,Rd3,Rd4,Rd5] #Ohms
            V=[0,Vd1,Vd2,Vd3] #Volts
            #here the currents IL and IR are defined as in figure ps3_p3_fig2
            a=numpy.array([  [  R[1]+R[4]+R[5],R[4] ],[R[4], R[2]+R[3]+R[4] ] ])
            b=numpy.array([V[1]-V[2],-V[3]-V[2]])
            x=numpy.linalg.solve(a,b)
            IL='%.2e' % x[0]
            IR='%.2e' % x[1]
            ILR='%.2e' % (x[0]+x[1])
            def sign(x):
                return abs(x)/x

            RW="Rightwards"
            LW="Leftwards"
            UW="Upwards"
            DW="Downwards"
            I1='%.2e' % abs(x[0])
            I1d=LW if sign(x[0])==1 else RW
            I1not=LW if I1d==RW else RW
            I2='%.2e' % abs(x[1])
            I2d=RW if sign(x[1])==1 else LW
            I2not=LW if I2d==RW else RW
            I3='%.2e' % abs(x[1])
            I3d=DW if sign(x[1])==1 else UW
            I3not=DW if I3d==UW else UW
            I4='%.2e' % abs(x[0]+x[1])
            I4d=UW if sign(x[1]+x[0])==1 else DW
            I4not=DW if I4d==UW else UW
            I5='%.2e' % abs(x[0])
            I5d=RW if sign(x[0])==1 else LW
            I5not=LW if I5d==RW else RW
            VAP=-x[0]*R[1]-(x[0]+x[1])*R[4]
            VPN=-V[2]
            VGD=+V[1]-x[0]*R[1]+V[3]+x[1]*R[2]
            aVAP='%.2e' % VAP
            aVPN='%.2e' % VPN
            aVGD='%.2e' % VGD
            """)
        g = {}
        safe_exec(code, g)
        assert "aVAP" in g
