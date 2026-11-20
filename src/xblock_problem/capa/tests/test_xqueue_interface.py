"""Test the XQueue interface."""

import json
from unittest.mock import Mock, patch

import pytest
from submissions.errors import SubmissionInternalError

from xblock_problem.capa.errors import RuntimeErrorSubmission
from xblock_problem.capa.xqueue_interface import XQueueInterface, make_xheader


@pytest.mark.django_db
@patch("xblock_problem.capa.xqueue_submission.XQueueInterfaceSubmission.send_to_submission")
def test_send_to_queue(mock_send_to_submission):
    """send_to_queue hands the header, body and queue key to edx-submissions."""
    xqueue_interface = XQueueInterface(block=Mock())

    header = make_xheader(lms_key="default", queue_name="testqueue")
    body = json.dumps(
        {
            "student_info": json.dumps({"anonymous_student_id": "student_id"}),
            "student_response": "student_answer",
        }
    )

    mock_send_to_submission.return_value = {"submission": "mock_submission"}
    error, msg = xqueue_interface.send_to_queue(header, body)

    mock_send_to_submission.assert_called_once_with(header, body, "default", {})
    assert error == 0
    assert msg == ""


@pytest.mark.django_db
@patch("xblock_problem.capa.xqueue_submission.XQueueInterfaceSubmission.send_to_submission")
def test_send_to_queue_with_files(mock_send_to_submission):
    """Uploaded files are passed through keyed by file name."""
    xqueue_interface = XQueueInterface(block=Mock())
    header = make_xheader(lms_key="default", queue_name="testqueue")
    body = json.dumps({"student_info": json.dumps({"anonymous_student_id": "student_id"})})
    prog = Mock()
    prog.name = "prog1.py"

    mock_send_to_submission.return_value = {"submission": "mock_submission"}
    error, _ = xqueue_interface.send_to_queue(header, body, files_to_upload=[prog])

    mock_send_to_submission.assert_called_once_with(header, body, "default", {"prog1.py": prog})
    assert not error


@pytest.mark.django_db
@patch("xblock_problem.capa.xqueue_submission.XQueueInterfaceSubmission.send_to_submission")
def test_send_to_queue_reports_submission_service_error(mock_send_to_submission):
    """
    If edx-submissions can't create the submission, send_to_queue returns an error
    so the problem tells the learner, instead of reporting success.
    """
    xqueue_interface = XQueueInterface(block=Mock())
    header = make_xheader(lms_key="default", queue_name="testqueue")
    body = json.dumps({"student_info": json.dumps({"anonymous_student_id": "student_id"})})

    mock_send_to_submission.return_value = {"error": "Validation error: The field 'student_response' does not exist."}
    error, msg = xqueue_interface.send_to_queue(header, body)

    assert error == 1
    assert msg == "Validation error: The field 'student_response' does not exist."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "exception",
    [SubmissionInternalError("database is away"), RuntimeErrorSubmission("Database access not allowed")],
)
@patch("xblock_problem.capa.xqueue_submission.XQueueInterfaceSubmission.send_to_submission")
def test_send_to_queue_reports_exceptions_as_errors(mock_send_to_submission, exception):
    """
    A failure inside edx-submissions comes back as an error code and message, the way a
    connection failure to the XQueue service used to, so the problem can tell the learner
    to try again instead of raising.
    """
    xqueue_interface = XQueueInterface(block=Mock())
    header = make_xheader(lms_key="default", queue_name="testqueue")
    body = json.dumps({"student_info": json.dumps({"anonymous_student_id": "student_id"})})

    mock_send_to_submission.side_effect = exception
    error, msg = xqueue_interface.send_to_queue(header, body)

    assert error == 1
    assert msg == str(exception)
