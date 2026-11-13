============
xblocks-core
============

*Before Verawood, this repository was known as "xblocks-contrib"*

This repository is the new home for XBlocks which are part of the base openedx-platform
installation.

Project Overview
=======================

XBlocks are modular components that enable rich interactive learning experiences in Open edX courses.
Historically, the XBlock code was tightly coupled with the edx-platform, making it challenging to manage and extend.
By extracting XBlocks into this dedicated repository, we can reduce the complexity of the edx-platform, making it more maintainable and scalable.

XBlocks Being Moved Here
************************

These are the XBlocks being moved here, and each of their statuses:

* ``poll_question`` -- Ready to Use
* ``word_cloud`` -- Ready to Use
* ``annotatable`` -- Ready to Use
* ``lti`` -- Ready to Use
* ``pdf`` -- Done
* ``html`` -- Ready to Use
* ``discussion`` -- Ready to Use
* ``problem`` -- Ready to Use
* ``video`` -- Ready to Use

The possible XBlock statuses are:

* In Development: We're building and testing this block.
* Ready to Use: You can try this on your site using the Waffle flag.
* Done: The built-in block has been removed. The ``pyproject.toml`` entry-point has been removed from edx-platform and added to xblock-contrib.


Additional XBlocks that belong here
***********************************

Over time, more XBlocks may be moved here. An XBlock belongs here if and only if both of the following are true:

1. **It needs to be part of the out-of-the-box Open edX experience, as agreed upon by the
   Product Working Group.** Otherwise, perhaps the block belongs in `xblocks-extra <https://github.com/openedx/xblocks-extra>`_,
   or it belongs in a community repository outside of the openedx GitHub organization.

2. **The maintainers of this repository have capacity to maintain the additional block.**
   Otherwise, perhaps the block belongs in its own repository with a separate dedicated maintainer,
   such as `ora2 <https://github.com/openedx/edx-ora2>`_.


Installation and Development Guide
**********************************

Python Setup
------------

This project uses `uv <https://docs.astral.sh/uv/>`_ for dependency management.

1. `Install uv <https://docs.astral.sh/uv/getting-started/installation/>`_.
2. Install all development dependencies::

    $ make requirements

   This runs ``uv sync --group dev`` and installs the package in editable mode.

3. Run the test suite::

    $ uv run tox

4. To upgrade all dependencies::

    $ make upgrade

Frontend Setup
--------------

Study scripts in the ``package.json`` file to understand the available commands.

1. Install this repository into your runtime (for example ``openedx-platform``) as an editable dependency. For Tutor, you can mount this repository for local development.
2. Run ``npm run build`` to generate production public assets for the XBlocks.
3. Run ``npm run build-dev`` to generate development public assets for the XBlocks.
4. Run ``npm run watch-build-dev`` to watch for relevant file changes and regenerate public assets.
   Recommended during development. Run it in a separate terminal; you will still need to refresh the browser to pick up rebuilt assets.
5. Run ``npm run test`` to run the repository tests.


Translating
*************

Internationalization (i18n) is when a program is made aware of multiple languages.
Localization (l10n) is adapting a program to local language and cultural habits.

For information on how to enable translations, visit the `Open edX XBlock tutorial on Internationalization <https://docs.openedx.org/projects/xblock/en/latest/xblock-tutorial/edx_platform/edx_lms.html#internationalization-support>`_.

The included Makefile contains a target for extracting translatable strings.
Each XBlock in this repository has its own translation configuration under
``src/xblock_<name>/conf/locale/``. The Make target iterates over every XBlock automatically.


The general steps to provide multilingual messages for a Python program (or an XBlock) are:

1. Mark translatable strings.
2. Run i18n tools to create raw message catalogs.
3. Create language specific translations for each message in the catalogs.
4. Use ``gettext`` to translate strings.

Prerequisites
-------------

Install the development requirements, which include `edx-i18n-tools <https://github.com/openedx/i18n-tools>`_
and GNU gettext tools (``msgcat``, ``msgfmt``)::

    $ make requirements

On macOS, install gettext via Homebrew if not already present::

    $ brew install gettext

1. Mark translatable strings
----------------------------

Mark translatable strings in python::

    from django.utils.translation import gettext as _

    # Translators: This comment will appear in the `.po` file.
    message = _("This will be marked.")

See `edx-developer-guide <https://docs.openedx.org/en/latest/developers/references/developer_guide/internationalization/i18n.html#python-source-code>`__
for more information.

You can also use ``gettext`` to mark strings in javascript::

    // Translators: This comment will appear in the `.po` file.
    var message = gettext("Custom message.");

See `edx-developer-guide <https://docs.openedx.org/en/latest/developers/references/developer_guide/internationalization/i18n.html#javascript-files>`__
for more information.

2. Run i18n tools to create raw message catalogs
-------------------------------------------------

After marking strings as translatable we have to create the raw message catalogs.
These catalogs are created in ``.po`` files. For more information see
`GNU PO file documentation <https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html>`_.
These catalogs can be created by running::

    $ make extract_translations

This iterates over every XBlock and:

1. Runs ``i18n_tool extract --no-segment`` to extract Python, HTML and JS strings.
2. Merges ``djangojs.po`` into ``django.po`` (if JS strings exist) using ``msgcat``.
3. Moves the result to ``<module_name>/conf/locale/`` at the repository root.

The output for each XBlock is a single file at::

    xblock_<name>/conf/locale/en/LC_MESSAGES/django.po

These per-XBlock files are used by the
`openedx-translations <https://github.com/openedx/openedx-translations>`_ pipeline (OEP-58)
to sync translations with Transifex. Each XBlock is a separate Transifex resource.

3. Create language specific translations
----------------------------------------

3.1 Add translated strings
~~~~~~~~~~~~~~~~~~~~~~~~~~

After creating the raw message catalogs, all translations should be filled out by the translator.
One or more translators must edit the entries created in the message catalog, i.e. the ``.po`` file(s).
The format of each entry is as follows::

    #  translator-comments
    A. extracted-comments
    #: reference...
    #, flag...
    #| msgid previous-untranslated-string
    msgid 'untranslated message'
    msgstr 'mensaje traducido (translated message)'

For more information see
`GNU PO file documentation <https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html>`_.

3.2 Transifex integration (via openedx-translations)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This project follows `OEP-58 <https://docs.openedx.org/en/latest/developers/concepts/oep58.html>`_
for translation management. Translations are managed centrally through the
`openedx-translations <https://github.com/openedx/openedx-translations>`_ repository:

1. A daily GitHub Actions workflow in openedx-translations clones this repo, runs
   ``make extract_translations``, and commits each XBlock's ``django.po`` source file under
   ``translations/xblocks-core/<module_name>/conf/locale/``.
2. The Transifex GitHub App syncs source strings to the ``openedx-translations`` Transifex project
   under the ``open-edx`` organization.
3. The Open edX translation community translates strings on Transifex.
4. Reviewed translations sync back to the openedx-translations repository.

Since these XBlocks were extracted from edx-platform, many strings already have existing translations
in Transifex. The openedx-translations pipeline preserves these so translators do not need to
re-translate them.

4. Use ``gettext`` to translate strings
---------------------------------------

Open edX pulls the translations from openedx-translations with ``atlas``
(``make pull_xblock_translations`` in openedx-platform), and Django uses ``gettext`` to
translate strings.

Make targets reference
----------------------

..  list-table::
    :widths: 35 65
    :header-rows: 1

    * - Target
      - Description
    * - ``make extract_translations``
      - Extract translatable strings into ``<module_name>/conf/locale/`` for each XBlock

Troubleshooting
~~~~~~~~~~~~~~~

See `django's i18n troubleshooting documentation
<https://docs.djangoproject.com/en/5.2/topics/i18n/translation/#troubleshooting-gettext-incorrectly-detects-python-format-in-strings-with-percent-signs>`_
for more information.

**Common issues:**

- ``i18n_tool: command not found`` -- Run ``make requirements`` to install ``edx-i18n-tools``.
- ``msgcat: command not found`` -- Install GNU gettext (``brew install gettext`` on macOS).
