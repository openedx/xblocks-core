"""
Tests for xblocks_core.django_templates.
"""

import tempfile
import unittest
from pathlib import Path

from django.template import TemplateDoesNotExist
from django.test import override_settings

from xblocks_core.django_templates import render_django_template
from xblocks_core.tests.i18n import FakeI18nService, reset_django_translations

MAIN_TEMPLATE = """{% load i18n %}{% trans "Hello" as greeting %}{{ greeting }}, {% include "inc.html" %}"""
INCLUDED_TEMPLATE = (
    "{% load i18n %}{% blocktrans count n=count %}{{ n }} world{% plural %}{{ n }} worlds{% endblocktrans %}"
)


class RenderDjangoTemplateTest(unittest.TestCase):
    """
    The helper renders through Django's configured loaders, with the block's i18n service.
    """

    def setUp(self):
        super().setUp()
        reset_django_translations()
        self.templates_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.templates_dir.cleanup)
        templates = Path(self.templates_dir.name)
        (templates / "main.html").write_text(MAIN_TEMPLATE, encoding="utf-8")
        (templates / "inc.html").write_text(INCLUDED_TEMPLATE, encoding="utf-8")
        self.settings = override_settings(
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [self.templates_dir.name],
                }
            ]
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.i18n_service = FakeI18nService(
            {
                "Hello": "Hola",
                ("%(n)s world", 0): "%(n)s mundo",
                ("%(n)s world", 1): "%(n)s mundos",
            }
        )

    def test_translates_with_block_catalog_through_includes(self):
        """``{% trans %}`` and ``{% blocktrans %}``, in the template and in what it includes, use the service."""
        assert render_django_template("main.html", {"count": 1}, i18n_service=self.i18n_service) == "Hola, 1 mundo"
        assert render_django_template("main.html", {"count": 2}, i18n_service=self.i18n_service) == "Hola, 2 mundos"

    def test_without_service_falls_back_to_django(self):
        """With no service, the strings are whatever Django's own catalog has: English here."""
        assert render_django_template("main.html", {"count": 2}) == "Hello, 2 worlds"

    def test_uses_configured_loaders(self):
        """Templates are found the way ``django.template.loader`` finds them, so missing ones raise the usual error."""
        with self.assertRaises(TemplateDoesNotExist):
            render_django_template("missing.html", {}, i18n_service=self.i18n_service)

    def test_engine_follows_settings(self):
        """A new default engine (as after ``override_settings``) gets a matching new engine here."""
        with override_settings(TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates"}]):
            with self.assertRaises(TemplateDoesNotExist):
                render_django_template("main.html", {"count": 1}, i18n_service=self.i18n_service)
        assert render_django_template("main.html", {"count": 1}, i18n_service=self.i18n_service) == "Hola, 1 mundo"
