"""
Django App configuration for the xblocks-core CAPA module.
"""

from django.apps import AppConfig


class CapaAppConfig(AppConfig):
    """
    Configuration for the CAPA problem XBlock Django application.

    Why are we registering this as a Django App?
    --------------------------------------------
    The capa input templates reference assets under ``capa/static/`` (``js/capa/*``, ``images/*``,
    ``applets/*``) with ``{% static %}``. Django's ``AppDirectoriesFinder`` only collects a ``static/``
    directory that belongs to an app in ``INSTALLED_APPS``, so this app exists to get those assets
    picked up by ``collectstatic`` in the LMS and CMS.

    Rather than asking every deployment to add this module to ``INSTALLED_APPS`` by hand, we use the
    Open edX Django App Plugin Framework (``lms.djangoapp``/``cms.djangoapp`` entry points), which
    injects it at runtime.

    References:
    - Open edX Plugin App Framework:
      https://docs.openedx.org/projects/edx-django-utils/en/latest/plugins/how_tos/how_to_create_a_plugin_app.html
    - Django AppDirectoriesFinder:
      https://docs.djangoproject.com/en/stable/ref/contrib/staticfiles/#django.contrib.staticfiles.finders.AppDirectoriesFinder
    """

    name = "xblock_problem.capa"
    label = "xblock_problem_capa"
    verbose_name = "XBlocks Core - CAPA Problem Static Assets"

    # The Open edX plugin dictionary that triggers dynamic injection
    plugin_app = {
        "settings_config": {
            "lms.djangoapp": {
                "default": "",
            },
            "cms.djangoapp": {
                "default": "",
            },
        },
    }
