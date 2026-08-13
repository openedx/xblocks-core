XBlocks-Core Test Course
########################

A minimal OLX course containing **one example of each XBlock type** defined in
this repository (``src/xblock_*``). It exists so the extracted XBlocks can be
imported into Studio/LMS and exercised by hand.

Layout
======

The course is one section (``chapter``) with one subsection (``sequential``)
per XBlock type. Each subsection currently holds a single example unit
(``vertical``)::

    course/
      course.xml                     # course pointer: org / course / run
      course/examples.xml            # the run; lists the section
      chapter/xblock_examples.xml    # one section, lists all subsections
      sequential/<type>_examples.xml # one subsection per XBlock type
      vertical/<type>_example_1.xml  # one example unit per type
      html/ problem/ video/          # pointer-file component bodies
      policies/examples/             # policy.json + grading_policy.json
      about/                         # overview + short description

XBlock types covered: ``html``, ``problem``, ``video``, ``annotatable``,
``discussion``, ``lti``, ``pdf``, ``poll_question``, ``word_cloud``.

The examples are intentionally as minimal as possible. Detail can be added later.

Adding more examples
====================

Each type's subsection is designed to grow. To add a second example of, say,
``video``:

1. Create ``vertical/video_example_2.xml`` with your component.
2. Add ``<vertical url_name="video_example_2"/>`` to
   ``sequential/video_examples.xml`` (there is a commented placeholder there).

Packaging
=========

From the repo root::

    make test_course

This writes ``test-course/xblocks-core-test-course.tar.gz`` (gitignored), ready
to import via Studio (*Tools → Import*) or ``manage.py cms import``.
