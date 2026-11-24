"""
``{% load xblock_i18n %}``: ``trans`` and ``blocktrans`` that translate through the XBlock i18n service.

This is the XBlock library ``xblock.utils.templatetags.i18n``, made loadable by name. Django only finds
tag libraries inside installed apps' ``templatetags`` packages, and the ``xblock`` package is not an app.

The tags look for the block's i18n service under the ``_i18n_service`` key of the template context.
"""

from xblock.utils.templatetags.i18n import register  # noqa: F401
