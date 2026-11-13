"""
This module provides an interface for submitting student responses
to an external grading system through XQueue.
"""

import json
import logging

from xblock_problem.capa.errors import (
    GetSubmissionParamsError,
    JSONParsingError,
    RuntimeErrorSubmission,
    TypeErrorSubmission,
    ValidationError,
)

log = logging.getLogger(__name__)

# edx-submissions stores the grader_payload "lang" in a 32-character field.
MAX_GRADER_LANG_LENGTH = 32


class XQueueInterfaceSubmission:
    """Interface to the external grading system."""

    def __init__(self, block):
        self.block = block

    def _parse_json(self, data, name):
        """
        Helper function to safely parse data that may or may not be a JSON string.
        This is necessary because some callers may already provide parsed Python dicts
        (e.g., during internal calls or test cases), while other sources may send raw JSON strings.
        This helper ensures consistent behavior regardless of input format.
        Args:
            data: The input to parse, either a JSON string or a Python dict.
            name: Name of the field (used for error reporting).
        Returns:
            Parsed Python object or original data if already parsed.
        Raises:
            JSONParsingError: If `data` is a string and cannot be parsed as JSON.
        """
        try:
            return json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as e:
            raise JSONParsingError(name, str(e)) from e

    def get_submission_params(self, header, payload):
        """
        Extracts student submission data from the given header and payload.
        """
        header = self._parse_json(header, "header")
        payload = self._parse_json(payload, "payload")

        queue_name = header.get("queue_name", "default")

        if not self.block:
            raise GetSubmissionParamsError()

        course_id = str(self.block.context_key)
        item_type = self.block.scope_ids.block_type
        points_possible = self.block.max_score()

        item_id = str(self.block.usage_key)

        grader_payload = self._parse_grader_payload(payload)
        grader_file_name = grader_payload.get("grader", "")
        grader_options = self._get_grader_options(grader_payload)

        student_info = self._parse_json(payload["student_info"], "student_info")
        student_id = student_info.get("anonymous_student_id")

        if not student_id:
            raise ValidationError("The field 'anonymous_student_id' is missing from student_info.")

        student_answer = payload.get("student_response")
        if student_answer is None:
            raise ValidationError("The field 'student_response' does not exist.")

        student_dict = {"item_id": item_id, "item_type": item_type, "course_id": course_id, "student_id": student_id}

        return student_dict, student_answer, queue_name, grader_file_name, points_possible, grader_options

    @staticmethod
    def _parse_grader_payload(payload):
        """
        Return the payload's grader_payload as a dict, or {} if it isn't a JSON object.

        The grader_payload is whatever text the course author put in the problem's
        <grader_payload> tag, and legacy XQueue passed it to graders without looking
        at it. It's usually a JSON object with a "grader" key, but it can also be
        empty (no <grader_payload> tag), not JSON, or JSON that isn't an object.
        None of these should keep the submission from being queued.

        See: https://github.com/openedx/edx-submissions/issues/390
        """
        grader_payload = payload.get("grader_payload")
        if isinstance(grader_payload, str):
            try:
                grader_payload = json.loads(grader_payload)
            except json.JSONDecodeError:
                return {}
        if isinstance(grader_payload, dict):
            return grader_payload
        return {}

    def _get_grader_options(self, grader_payload):
        """
        Return the lang, hide_output, and skip_grader options from grader_payload.

        Besides "grader", these are the only grader_payload keys that xqueue-watcher's
        built-in graders read, and edx-submissions sends them back to the grader.

        xqueue-watcher only checks whether hide_output and skip_grader are truthy, so
        we do the same. That means the string "false" counts as true, as it does in
        xqueue-watcher. A lang that isn't a string can break the grader, and one longer
        than MAX_GRADER_LANG_LENGTH isn't a real language code, so we drop those and
        the grader uses its default language.

        See: https://github.com/openedx/edx-submissions/issues/390
        """
        lang = grader_payload.get("lang", "")
        if not isinstance(lang, str) or len(lang) > MAX_GRADER_LANG_LENGTH:
            log.warning("Ignoring invalid grader_payload lang %r for %s", lang, self.block.usage_key)
            lang = ""
        return {
            "lang": lang,
            "hide_output": bool(grader_payload.get("hide_output", False)),
            "skip_grader": bool(grader_payload.get("skip_grader", False)),
        }

    def send_to_submission(self, header, body, queue_key, files_to_upload=None):
        """
        Submits the extracted student data to the edx-submissions system.
        """
        try:
            from submissions.api import create_external_grader_detail  # pylint: disable=import-outside-toplevel

            student_item, answer, queue_name, grader_file_name, points_possible, grader_options = (
                self.get_submission_params(header, body)
            )
            return create_external_grader_detail(
                student_item,
                answer,
                queue_name=queue_name,
                queue_key=queue_key,
                grader_file_name=grader_file_name,
                points_possible=points_possible,
                lang=grader_options["lang"],
                hide_output=grader_options["hide_output"],
                skip_grader=grader_options["skip_grader"],
                files=files_to_upload,
            )
        except (JSONParsingError, ValidationError) as e:
            log.error("%s", e)
            return {"error": str(e)}
        except TypeError as e:
            log.error("%s", e)
            raise TypeErrorSubmission(str(e)) from e
        except RuntimeError as e:
            log.error("%s", e)
            raise RuntimeErrorSubmission(str(e)) from e
