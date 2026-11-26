"""
Tests for WordCloudBlock
"""

from unittest.mock import Mock, patch

from django.test import TestCase
from web_fragments.fragment import Fragment
from xblock.fields import ScopeIds
from xblock.test.toy_runtime import ToyRuntime

from xblock_word_cloud import WordCloudBlock


class TestWordCloudBlock(TestCase):
    """Tests for WordCloudBlock"""

    def setUp(self):
        super().setUp()
        scope_ids = ScopeIds("1", "2", "3", "4")
        self.block = WordCloudBlock(ToyRuntime(), scope_ids=scope_ids)

    def test_my_student_view(self):
        """Test the basic view loads."""
        frag = self.block.student_view()
        as_dict = frag.to_dict()
        content = as_dict["content"]
        self.assertIn(
            "Word cloud",
            content,
            "XBlock did not render correct student view",
        )
        self.assertIn(
            "Your words were:",
            content,
            "XBlock did not render correct student view",
        )

    def test_student_view_supports_multi_device(self):
        """
        student_view supports multi_device, so mobile apps render the block inline.

        The built-in openedx-platform block declared this (``xmodule/word_cloud_block.py``),
        and the mobile course blocks API reports it as ``student_view_multi_device``.
        """
        self.assertTrue(self.block.has_support(self.block.student_view, "multi_device"))

    def test_good_word(self):
        self.assertEqual(self.block.good_word("  Test  "), "test")
        self.assertEqual(self.block.good_word("Hello"), "hello")
        self.assertEqual(self.block.good_word("  WORLD "), "world")

    def test_top_dict(self):
        words = {"hello": 3, "world": 5, "python": 2}
        top_words = self.block.top_dict(words, 2)
        self.assertEqual(top_words, {"world": 5, "hello": 3})

    def test_get_state_not_submitted(self):
        self.block.submitted = False
        state = self.block.get_state()
        self.assertFalse(state["submitted"])
        self.assertEqual(state["top_words"], {})

    def test_get_state_submitted(self):
        self.block.submitted = True
        self.block.student_words = ["Mango", "Strawberry", "Banana"]
        self.block.all_words = {"Mango": 11, "Apple": 13, "Banana": 21, "Strawberry": 28}
        self.block.top_words = {"Strawberry": 28, "Banana": 21}
        state = self.block.get_state()
        self.assertTrue(state["submitted"])
        self.assertEqual(
            state["top_words"],
            [{"text": "Banana", "size": 21, "percent": 29}, {"text": "Strawberry", "size": 28, "percent": 71}],
        )
        self.assertEqual(state["total_count"], 73)

    def test_submit_state_first_time(self):
        self.block.submitted = False
        data = {"student_words": ["hello", "world", "hello"]}
        response = self.block.submit_state(data)
        self.assertEqual(response["status"], "success")
        self.assertTrue(self.block.submitted)
        self.assertEqual(self.block.student_words, ["hello", "world", "hello"])
        self.assertEqual(self.block.all_words["hello"], 2)
        self.assertEqual(self.block.all_words["world"], 1)

    def test_submit_state_already_submitted(self):
        self.block.submitted = True
        data = {"student_words": ["new"]}
        response = self.block.submit_state(data)
        self.assertEqual(response["status"], "fail")
        self.assertEqual(response["error"], "You have already posted your data.")

    def test_prepare_words(self):
        top_words = {"hello": 3, "world": 2}
        result = self.block.prepare_words(top_words, 5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "hello")
        self.assertEqual(result[0]["size"], 3)
        self.assertEqual(result[0]["percent"], 60)
        self.assertEqual(result[1]["text"], "world")
        self.assertEqual(result[1]["size"], 2)
        self.assertEqual(result[1]["percent"], 40)


class TestWordCloudBlockI18nJsCatalog(TestCase):
    """Tests for loading the block's namespaced JavaScript translation catalog."""

    def test_namespace(self):
        assert WordCloudBlock.i18n_js_namespace == "XBlockWordCloudI18N"
        assert WordCloudBlock.get_i18n_js_namespace() == "XBlockWordCloudI18N"

    def test_no_catalog_without_url(self):
        """No script is added when there is no catalog or the i18n service can't provide one."""
        no_catalog = Mock()
        no_catalog.get_javascript_i18n_catalog_url.return_value = None
        for i18n_service in (no_catalog, Mock(spec=[])):
            with self.subTest(i18n_service=i18n_service):
                block = Mock()
                block.runtime.service.return_value = i18n_service
                fragment = Fragment()

                WordCloudBlock._add_i18n_js_catalog(block, fragment)  # pylint: disable=protected-access

                assert not fragment.resources

    def test_student_view_loads_catalog_before_block_js(self):
        block = WordCloudBlock(ToyRuntime(), scope_ids=ScopeIds("1", "2", "3", "4"))
        with patch("xblock.runtime.NullI18nService.get_javascript_i18n_catalog_url", return_value="/static/catalog.js"):
            fragment = block.student_view()

        js = [r for r in fragment.resources if r.mimetype == "application/javascript"]
        assert js[0].kind == "url"
        assert js[0].data == "/static/catalog.js"
        assert "function WordCloudBlock(" in js[1].data
