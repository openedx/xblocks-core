"""Tests for DiscussionXBLock"""

import itertools
import random
import string
from collections import namedtuple
from unittest import TestCase, mock

import ddt
from django.test import override_settings
from lxml import etree
from xblock.field_data import DictFieldData
from xblock.fields import NO_CACHE_VALUE, UNIQUE_ID, ScopeIds
from xblock.runtime import Runtime

from xblock_discussion import DiscussionXBlock
from xblocks_core.tests.i18n import FakeI18nService


def attribute_pair_repr(self):
    """
    Custom string representation for the AttributePair namedtuple which is
    consistent between test runs.
    """
    return f"<AttributePair name={self.name}>"


AttributePair = namedtuple("AttributePair", ["name", "value"])
AttributePair.__repr__ = attribute_pair_repr


ID_ATTR_NAMES = ("discussion_id",)
CATEGORY_ATTR_NAMES = ("discussion_category",)
TARGET_ATTR_NAMES = ("discussion_target",)


def _random_string():
    """
    Generates random string
    """
    return "".join(
        random.choice(
            string.ascii_lowercase,
        )
        for _ in range(12)
    )


def _make_attribute_test_cases():
    """
    Builds test cases for attribute-dependent tests
    """
    attribute_names = itertools.product(ID_ATTR_NAMES, CATEGORY_ATTR_NAMES, TARGET_ATTR_NAMES)
    for id_attr, category_attr, target_attr in attribute_names:
        yield (
            AttributePair(id_attr, _random_string()),
            AttributePair(category_attr, _random_string()),
            AttributePair(target_attr, _random_string()),
        )


@ddt.ddt
class DiscussionXBlockImportExportTests(TestCase):
    """
    Import and export tests
    """

    DISCUSSION_XBLOCK_LOCATION = "xblock_discussion.DiscussionXBlock"

    def setUp(self):
        """
        Set up method
        """
        super().setUp()
        self.keys = ScopeIds("any_user", "discussion", "def_id", "usage_id")
        self.runtime_mock = mock.Mock(spec=Runtime)
        self.runtime_mock.construct_xblock_from_class = mock.Mock(side_effect=self._construct_xblock_mock)
        self.runtime_mock.get_policy = mock.Mock(return_value={})

    def _construct_xblock_mock(self, cls, keys):  # pylint: disable=unused-argument
        """
        Builds target xblock instance (DiscussionXBlock)

        Signature-compatible with runtime.construct_xblock_from_class - can be used as a mock side-effect
        """
        return DiscussionXBlock(self.runtime_mock, scope_ids=keys, field_data=DictFieldData({}))

    @mock.patch(DISCUSSION_XBLOCK_LOCATION + ".load_definition_xml")
    @ddt.unpack
    @ddt.data(*list(_make_attribute_test_cases()))
    def test_xblock_export_format(self, id_pair, category_pair, target_pair, patched_load_definition_xml):
        """
        Test that xblock export XML format can be parsed preserving field values
        """
        xblock_xml = f"""
        <discussion
            url_name="82bb87a2d22240b1adac2dfcc1e7e5e4" xblock-family="xblock.v1"
            {id_pair.name}="{id_pair.value}"
            {category_pair.name}="{category_pair.value}"
            {target_pair.name}="{target_pair.value}"
        />
        """
        node = etree.fromstring(xblock_xml)

        patched_load_definition_xml.side_effect = Exception("Irrelevant")

        block = DiscussionXBlock.parse_xml(node, self.runtime_mock, self.keys)
        try:
            assert block.discussion_id == id_pair.value
            assert block.discussion_category == category_pair.value
            assert block.discussion_target == target_pair.value
        except AssertionError:
            print(xblock_xml)
            raise

    @mock.patch(DISCUSSION_XBLOCK_LOCATION + ".load_definition_xml")
    @ddt.unpack
    @ddt.data(*(_make_attribute_test_cases()))
    def test_legacy_export_format(self, id_pair, category_pair, target_pair, patched_load_definition_xml):
        """
        Test that legacy export XML format can be parsed preserving field values
        """
        xblock_xml = """<discussion url_name="82bb87a2d22240b1adac2dfcc1e7e5e4"/>"""
        xblock_definition_xml = f"""
        <discussion
            {id_pair.name}="{id_pair.value}"
            {category_pair.name}="{category_pair.value}"
            {target_pair.name}="{target_pair.value}"
        />"""
        node = etree.fromstring(xblock_xml)
        definition_node = etree.fromstring(xblock_definition_xml)

        patched_load_definition_xml.return_value = (definition_node, "irrelevant")

        block = DiscussionXBlock.parse_xml(node, self.runtime_mock, self.keys)
        try:
            assert block.discussion_id == id_pair.value
            assert block.discussion_category == category_pair.value
            assert block.discussion_target == target_pair.value
        except AssertionError:
            print(xblock_xml, xblock_definition_xml)
            raise

    def test_export_default_discussion_id(self):
        """
        Test that default discussion_id values are not exported.

        Historically, the OLX format allowed omitting discussion ID values; in such case, the IDs are generated
        deterministically based on the course ID and the usage ID. Moreover, Studio does not allow course authors
        to edit discussion_id, so all courses authored in Studio have discussion_id omitted in OLX.

        Forcing Studio to always export discussion_id can cause data loss when switching between an older and newer
        export,  in a course with a course ID different from the one from which the export was created - because the
        discussion ID would be different.
        """
        target_node = etree.Element("dummy")

        block = DiscussionXBlock(self.runtime_mock, scope_ids=self.keys, field_data=DictFieldData({}))
        discussion_id_field = block.fields["discussion_id"]  # pylint: disable=unsubscriptable-object

        # precondition checks - discussion_id does not have a value and uses UNIQUE_ID
        assert discussion_id_field._get_cached_value(block) == NO_CACHE_VALUE  # pylint: disable=W0212
        assert discussion_id_field.default == UNIQUE_ID

        block.add_xml_to_node(target_node)
        assert target_node.tag == "discussion"
        assert "discussion_id" not in target_node.attrib

    @ddt.data("jediwannabe", "iddqd", "itisagooddaytodie")
    def test_export_custom_discussion_id(self, discussion_id):
        """
        Test that custom discussion_id values are exported
        """
        target_node = etree.Element("dummy")

        block = DiscussionXBlock(self.runtime_mock, scope_ids=self.keys, field_data=DictFieldData({}))
        block.discussion_id = discussion_id

        # precondition check
        assert block.discussion_id == discussion_id

        block.add_xml_to_node(target_node)
        assert target_node.tag == "discussion"
        assert target_node.attrib["discussion_id"], discussion_id


class DiscussionXBlockI18nTests(TestCase):
    """
    The block's views translate through its own i18n service, not Django's global catalog.
    """

    def setUp(self):
        super().setUp()
        self.i18n_service = FakeI18nService(
            {
                "Show Discussion": "MOSTRAR DISCUSION",
                "Discussion": "DISCUSION",
                "sign in": "INICIAR SESION",
                "Show all posts": "MOSTRAR TODO",
                "To view live discussions, click Preview or View Live in Unit Settings.": "VISTA PREVIA",
            }
        )
        self.discussion_config = mock.Mock()
        self.discussion_config.is_discussion_visible.return_value = True
        self.discussion_config.is_discussion_enabled = True
        self.discussion_config.has_permission.return_value = True
        self.user = mock.Mock(is_authenticated=False)
        services = {
            "i18n": self.i18n_service,
            "discussion_config_service": self.discussion_config,
            "user": mock.Mock(_django_user=self.user),
        }
        self.runtime = mock.Mock(spec=Runtime)
        self.runtime.service = mock.Mock(side_effect=lambda _block, name: services.get(name))
        self.runtime.local_resource_url = mock.Mock(return_value="/static/resource")
        keys = ScopeIds("any_user", "discussion", "def_id", "usage_id")
        self.block = DiscussionXBlock(self.runtime, scope_ids=keys, field_data=DictFieldData({}))

    @override_settings(PLATFORM_NAME="Test", FEATURES={})
    @mock.patch("xblock_discussion.block.reverse", return_value="/login")
    def test_student_view_uses_block_catalog(self, _reverse):
        """The inline template, its partials, and the sign-in message use the block catalog."""
        html = self.block.student_view().content

        assert "MOSTRAR DISCUSION" in html
        assert "Show Discussion" not in html
        assert "DISCUSION" in html  # the default display name, via _()
        assert "INICIAR SESION" in html
        assert ">sign in<" not in html
        assert "MOSTRAR TODO" in html  # from _thread_list_template.html
        assert 'id="thread-list-template"' in html
        assert "window.PLATFORM_NAME" in html  # from _underscore_templates.html
        assert 'type="text/template"' in html  # from templates.underscore

    def test_author_view_uses_block_catalog(self):
        """The studio template is rendered with the block's i18n service."""
        html = self.block.author_view().content

        assert "VISTA PREVIA" in html
        assert "click Preview" not in html
