.. _chapter-i18n:

Internationalization
####################
All user-facing text content should be marked for translation. Even if this application is only run in English, our
open source users may choose to use another language. Marking content for translation ensures our users have
this choice.

Follow the `internationalization coding guidelines`_ in the Open edX Developer's Guide when developing new features.

.. _internationalization coding guidelines: https://docs.openedx.org/en/latest/developers/references/developer_guide/internationalization/i18n.html

Project structure
*****************
Each XBlock in this repository manages its own translations independently:

- **Config**: ``src/xblock_<name>/conf/locale/config.yaml`` -- defines supported languages and
  ignored directories.
- **Source strings**: ``xblock_<name>/conf/locale/en/LC_MESSAGES/django.po`` (at the repository
  root) -- extracted English strings (Python, HTML, and JavaScript combined into a single file),
  used by the openedx-translations pipeline (OEP-58).

``make extract_translations`` iterates over every XBlock that has a ``conf/`` directory automatically.

Updating Translations
*********************
This project follows `OEP-58`_ for translation management. Translations are managed centrally through
the `openedx-translations`_ repository rather than directly via Transifex.

.. _OEP-58: https://docs.openedx.org/en/latest/developers/concepts/oep58.html
.. _openedx-translations: https://github.com/openedx/openedx-translations

**How the pipeline works:**

1. A daily GitHub Actions workflow in openedx-translations clones this repo and runs
   ``make extract_translations``.
2. Each XBlock's ``django.po`` file is committed to openedx-translations under
   ``translations/xblocks-core/<module_name>/conf/locale/``.
3. The Transifex GitHub App syncs source strings to the ``openedx-translations`` Transifex project
   under the ``open-edx`` organization.
4. The Open edX translation community translates strings on `Transifex`_.
5. Reviewed translations sync back to the openedx-translations repository.

Since these XBlocks were extracted from edx-platform, many strings already have existing translations
in Transifex. The pipeline preserves these so translators do not need to re-translate them.

.. _Transifex: https://www.transifex.com/

..  list-table::
    :widths: 35 65
    :header-rows: 1

    * - Target
      - Description
    * - ``make extract_translations``
      - Extract translatable strings into ``<module_name>/conf/locale/`` for each XBlock
