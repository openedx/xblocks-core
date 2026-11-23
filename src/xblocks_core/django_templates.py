"""
Render Django templates through an XBlock's own i18n service.

``xblock.utils.resources.ResourceLoader.render_django_template`` does this for a template file
that ships inside the block's package, but it builds a bare template engine with no loaders, so
``{% include %}`` and friends do not work. Some blocks here (Problem, Discussion) have template
trees that use ``{% include %}`` and that Django finds through its configured template loaders
(their ``templates/`` directories are exposed to the platform as Django apps).

``render_django_template`` below renders such a template with the configured loaders, while
routing ``{% trans %}`` and ``{% blocktrans %}`` (in the template and in anything it includes)
through the block's i18n service rather than Django's global catalog. The global catalog only
holds strings that the platform extracts from its own source; the block's strings live in the
block's own catalog, which the platform pulls with ``atlas`` and exposes via the i18n service.

This is a candidate for upstreaming into the ``xblock`` package alongside
``ResourceLoader.render_django_template``.
"""

import functools

from django.template import Context, Engine

XBLOCK_I18N_TEMPLATE_LIBRARY = "xblock.utils.templatetags.i18n"


@functools.cache
def _engine_for(default_engine):
    """
    Return a copy of ``default_engine`` whose ``{% load i18n %}`` loads the XBlock tag library.

    The XBlock library's ``trans``/``blocktrans`` tags merge the ``_i18n_service`` found in the
    template context into the active translation for the duration of the render.

    Keyed on the default engine object so that a test's ``override_settings(TEMPLATES=...)``,
    which rebuilds the default engine, also rebuilds this one.
    """
    extra_builtins = [lib for lib in default_engine.builtins if lib not in Engine.default_builtins]
    return Engine(
        dirs=default_engine.dirs,
        # ``loaders`` already accounts for ``app_dirs``, and Engine rejects passing both.
        app_dirs=False,
        context_processors=default_engine.context_processors,
        debug=default_engine.debug,
        loaders=default_engine.loaders,
        string_if_invalid=default_engine.string_if_invalid,
        file_charset=default_engine.file_charset,
        libraries={**default_engine.libraries, "i18n": XBLOCK_I18N_TEMPLATE_LIBRARY},
        builtins=extra_builtins,
        autoescape=default_engine.autoescape,
    )


def render_django_template(template_name, context=None, i18n_service=None):
    """
    Render the Django template ``template_name`` (found via the configured loaders) with ``context``.

    ``{% trans %}`` and ``{% blocktrans %}`` in the template, and in any template it includes,
    translate through ``i18n_service`` (the block's runtime ``"i18n"`` service) when one is given.
    """
    context = dict(context or {})
    context["_i18n_service"] = i18n_service
    engine = _engine_for(Engine.get_default())
    return engine.get_template(template_name).render(Context(context))
