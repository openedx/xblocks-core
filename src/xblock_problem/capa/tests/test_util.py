"""
Tests capa util
"""

import unittest

import ddt
import pytest
from lxml import etree

from xblock_problem.capa.tests.helpers import mock_capa_system
from xblock_problem.capa.util import (
    compare_with_tolerance,
    contextualize_text,
    get_inner_html_from_xpath,
    is_inside_convex_hull,
    remove_markup,
    sanitize_html,
)


@ddt.ddt
class UtilTest(unittest.TestCase):
    """Tests for util"""

    def setUp(self):
        super().setUp()
        self.system = mock_capa_system()

    def test_compare_with_tolerance(self):  # pylint: disable=too-many-statements
        """Test numeric comparison with relative and absolute tolerances."""
        # Test default tolerance '0.001%' (it is relative)
        result = compare_with_tolerance(100.0, 100.0)
        assert result
        result = compare_with_tolerance(100.001, 100.0)
        assert result
        result = compare_with_tolerance(101.0, 100.0)
        assert not result
        # Test absolute percentage tolerance
        result = compare_with_tolerance(109.9, 100.0, "10%", False)
        assert result
        result = compare_with_tolerance(110.1, 100.0, "10%", False)
        assert not result
        # Test relative percentage tolerance
        result = compare_with_tolerance(111.0, 100.0, "10%", True)
        assert result
        result = compare_with_tolerance(112.0, 100.0, "10%", True)
        assert not result
        # Test absolute tolerance (string)
        result = compare_with_tolerance(109.9, 100.0, "10.0", False)
        assert result
        result = compare_with_tolerance(110.1, 100.0, "10.0", False)
        assert not result
        # Test relative tolerance (string)
        result = compare_with_tolerance(111.0, 100.0, "0.1", True)
        assert result
        result = compare_with_tolerance(112.0, 100.0, "0.1", True)
        assert not result
        # Test absolute tolerance (float)
        result = compare_with_tolerance(109.9, 100.0, 10.0, False)
        assert result
        result = compare_with_tolerance(110.1, 100.0, 10.0, False)
        assert not result
        # Test relative tolerance (float)
        result = compare_with_tolerance(111.0, 100.0, 0.1, True)
        assert result
        result = compare_with_tolerance(112.0, 100.0, 0.1, True)
        assert not result
        # Infinite values #
        infinity = float("Inf")
        # Test relative tolerance (float)
        result = compare_with_tolerance(infinity, 100.0, 1.0, True)
        assert not result
        result = compare_with_tolerance(100.0, infinity, 1.0, True)
        assert not result
        result = compare_with_tolerance(infinity, infinity, 1.0, True)
        assert result
        # Test absolute tolerance (float)
        result = compare_with_tolerance(infinity, 100.0, 1.0, False)
        assert not result
        result = compare_with_tolerance(100.0, infinity, 1.0, False)
        assert not result
        result = compare_with_tolerance(infinity, infinity, 1.0, False)
        assert result
        # Test relative tolerance (string)
        result = compare_with_tolerance(infinity, 100.0, "1.0", True)
        assert not result
        result = compare_with_tolerance(100.0, infinity, "1.0", True)
        assert not result
        result = compare_with_tolerance(infinity, infinity, "1.0", True)
        assert result
        # Test absolute tolerance (string)
        result = compare_with_tolerance(infinity, 100.0, "1.0", False)
        assert not result
        result = compare_with_tolerance(100.0, infinity, "1.0", False)
        assert not result
        result = compare_with_tolerance(infinity, infinity, "1.0", False)
        assert result
        # Test absolute tolerance for smaller values
        result = compare_with_tolerance(100.01, 100.0, 0.01, False)
        assert result
        result = compare_with_tolerance(100.001, 100.0, 0.001, False)
        assert result
        result = compare_with_tolerance(100.01, 100.0, "0.01%", False)
        assert result
        result = compare_with_tolerance(100.002, 100.0, 0.001, False)
        assert not result
        result = compare_with_tolerance(0.4, 0.44, 0.01, False)
        assert not result
        result = compare_with_tolerance(100.01, 100.0, 0.010, False)
        assert result

        # Test complex_number instructor_complex
        result = compare_with_tolerance(0.4, complex(0.44, 0), 0.01, False)
        assert not result
        result = compare_with_tolerance(100.01, complex(100.0, 0), 0.010, False)
        assert result
        result = compare_with_tolerance(110.1, complex(100.0, 0), "10.0", False)
        assert not result
        result = compare_with_tolerance(111.0, complex(100.0, 0), "10%", True)
        assert result

    def test_sanitize_html(self):
        """
        Test for html sanitization with nh3.
        """
        allowed_tags = ["div", "p", "audio", "pre", "span"]
        for tag in allowed_tags:
            queue_msg = f"<{tag}>Test message</{tag}>"
            assert sanitize_html(queue_msg) == queue_msg

        not_allowed_tag = "script"
        queue_msg = f"<{not_allowed_tag}>Test message</{not_allowed_tag}>"
        expected = ""
        assert sanitize_html(queue_msg) == expected

    def test_get_inner_html_from_xpath(self):
        """
        Test for getting inner html as string from xpath node.
        """
        xpath_node = etree.XML('<hint style="smtng">aa<a href="#">bb</a>cc</hint>')
        assert get_inner_html_from_xpath(xpath_node) == 'aa<a href="#">bb</a>cc'

    def test_remove_markup(self):
        """
        Test for markup removal with nh3.
        """
        assert (
            remove_markup("The <mark>Truth</mark> is <em>Out There</em> & you need to <strong>find</strong> it")
            == "The Truth is Out There &amp; you need to find it"
        )

    @ddt.data("When the root level failš the whole hierarchy won’t work anymore.", "あなたあなたあなた")
    def test_contextualize_text(self, context_value):
        """Verify that variable substitution works as intended with non-ascii characters."""
        key = "answer0"
        text = "$answer0"
        context = {key: context_value}
        contextual_text = contextualize_text(text, context)
        assert context_value == contextual_text

    def test_contextualize_text_with_non_ascii_context(self):
        """Verify that variable substitution works as intended with non-ascii characters."""
        key = "あなた$a $b"
        text = "$" + key
        context = {"a": "あなたあなたあなた", "b": "あなたhi"}
        expected_text = "$あなたあなたあなたあなた あなたhi"
        contextual_text = contextualize_text(text, context)
        assert expected_text == contextual_text

    @ddt.data(
        # A triangle: only points strictly inside it count.
        ([[0, 0], [10, 0], [0, 10]], 2, 2, True),
        ([[0, 0], [10, 0], [0, 10]], 6, 6, False),
        ([[0, 0], [10, 0], [0, 10]], 5, 0, False),  # on an edge
        ([[0, 0], [10, 0], [0, 10]], 5, 5, False),  # on the diagonal edge
        ([[0, 0], [10, 0], [0, 10]], 0, 0, False),  # on a corner
        # The order of the points doesn't matter.
        ([[0, 10], [10, 0], [0, 0]], 2, 2, True),
        ([[0, 0], [10, 10], [10, 0], [0, 10]], 5, 2, True),
        ([[0, 0], [10, 10], [10, 0], [0, 10]], 2, 5, True),
        # Points that aren't corners of the hull don't change it.
        ([[0, 0], [10, 0], [10, 10], [5, 1], [0, 10]], 5, 1, True),
        ([[0, 0], [10, 0], [10, 10], [5, 1], [0, 10]], 5, 5, True),
        ([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10]], 5, 0, False),
        ([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10]], 5, 1, True),
        ([[0, 0], [0, 0], [10, 0], [10, 0], [0, 10]], 2, 2, True),
        # Negative and fractional coordinates.
        ([[-5, -5], [10, 0], [0, 10]], 0, 0, True),
        ([[0.5, 0.5], [10.5, 0.5], [0.5, 10.5]], 1, 1, True),
        ([[0.5, 0.5], [10.5, 0.5], [0.5, 10.5]], 5, 6, False),  # on an edge
        # A z coordinate is ignored.
        ([[0, 0, 7], [10, 0, 8], [0, 10]], 2, 2, True),
        # Numeric strings are accepted.
        ([["0", "0"], ["10", "0"], ["0", "1e1"]], 2, 2, True),
        # Hulls with no area don't contain anything.
        ([], 0, 0, False),
        ([[1, 1]], 1, 1, False),
        ([[1, 1], [3, 3]], 2, 2, False),
        ([[0, 0], [5, 5], [10, 10]], 5, 5, False),
        ([[1, 1], [1, 1], [1, 1]], 1, 1, False),
    )
    @ddt.unpack
    def test_is_inside_convex_hull(self, points, x, y, expected):
        """Test which points are strictly inside the convex hull of a set of points."""
        assert is_inside_convex_hull(points, x, y) is expected

    @ddt.data(
        ([[0, 0], [1.1, 5.5], [0, 9]], True),
        ([[0, 0], [1.1, 5.5], [9, 0]], False),
    )
    @ddt.unpack
    def test_is_inside_convex_hull_is_exact(self, points, expected):
        """
        Test that a point right next to an edge is put on the correct side of it.

        (1, 5) would be on the line from (0, 0) to (1.1, 5.5), except that the
        closest float to 1.1 is a tiny bit more than 1.1. Float arithmetic
        rounds that difference away and gets these wrong.
        """
        assert is_inside_convex_hull(points, 1, 5) is expected

    @ddt.data(
        [[0], [10, 0], [0, 10]],
        [[0, 0, 0, 0], [10, 0, 0, 0], [0, 10, 0, 0]],
        [[], [10, 0], [0, 10]],
        ["12", [10, 0], [0, 10]],
        [{"x": 0, "y": 0}, [10, 0], [0, 10]],
        [[[0, 0], [1, 1]], [[2, 2], [3, 3]]],
        [["a", 0], [10, 0], [0, 10]],
        [[None, 0], [10, 0], [0, 10]],
        [[float("nan"), 0], [10, 0], [0, 10]],
        [[float("inf"), 0], [10, 0], [0, 10]],
        [[10**400, 0], [10, 0], [0, 10]],
    )
    def test_is_inside_convex_hull_bad_points(self, points):
        """Test that points which aren't finite [x, y] coordinates are an error."""
        with pytest.raises((ValueError, TypeError, OverflowError)):
            is_inside_convex_hull(points, 2, 2)
