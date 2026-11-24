"""
A fake XBlock "i18n" service for tests of block-catalog translation.
"""

from django.utils.translation import get_language, trans_real


def reset_django_translations():
    """
    Drop Django's cached translation objects so a test starts from a clean global catalog.

    ``xblock.utils.templatetags.i18n`` merges a block's i18n service into Django's translation for
    the active language while rendering and then puts back a copy it took before the first render.
    From the second render of the same (cached) template node on, that copy *is* the live object,
    so the merge leaks into the global catalog for the rest of the process. Tests that assert on
    untranslated output must not inherit that.
    """
    trans_real._translations = {}  # pylint: disable=protected-access
    trans_real.activate(get_language())


class FakeI18nService:
    """
    Translate from a fixed ``{msgid: msgstr}`` catalog.

    Looks like the platform's ``XBlockI18nService`` wrapping a ``gettext.GNUTranslations``: it exposes
    ``gettext``/``ugettext``/``ngettext`` and the ``_catalog``/``_info``/``_fallback``/``plural``
    attributes that ``django.utils.translation.trans_real.DjangoTranslation.merge`` reads when the
    XBlock ``{% trans %}`` tags merge the service into the active translation.
    """

    def __init__(self, catalog):
        self._catalog = dict(catalog)
        self._info = {}
        self._fallback = None

    @staticmethod
    def plural(n):
        """Two plural forms, like English."""
        return int(n != 1)

    def gettext(self, message):
        return self._catalog.get(message, message)

    ugettext = gettext

    def ngettext(self, singular, plural, n):
        return self._catalog.get((singular, self.plural(n)), singular if n == 1 else plural)

    ungettext = ngettext
