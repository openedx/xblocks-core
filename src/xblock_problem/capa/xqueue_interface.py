"""
Interface for queueing external grader submissions.

Submissions go to edx-submissions, which stores them in the LMS and serves
them to graders such as xqueue-watcher through its XQueue-compatible API.
The header built here is an internal envelope: edx-submissions reads the
queue name and the queue key out of it and builds its own header for the
grader. The queue key format is the one the retired XQueue service used,
since the problem's correct map still stores it.
"""

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from xblock_problem.capa.errors import XQueueSubmissionError
from xblock_problem.capa.xqueue_submission import XQueueInterfaceSubmission

if TYPE_CHECKING:
    from xblock_problem.block import ProblemBlock

log = logging.getLogger(__name__)
DATEFORMAT = "%Y%m%d%H%M%S"


def make_hashkey(seed):
    """
    Generate a string key by hashing
    """
    h = hashlib.md5()
    h.update(str(seed).encode("latin-1"))
    return h.hexdigest()


def make_xheader(lms_key, queue_name):
    """
    Generate the header that accompanies a queue request.

    The header is a JSON-serialized dict::

        { 'lms_key': secret key used by LMS to match the grader's reply to the request (string),
          'queue_name': the queue the grader polls, e.g. 'MITx-6.00x' (string)
        }
    """
    return json.dumps({"lms_key": lms_key, "queue_name": queue_name})


class XQueueInterface:
    """Queues external grader submissions through edx-submissions."""

    def __init__(self, block: "ProblemBlock"):
        """
        Args:
            block (ProblemBlock): The problem the submissions belong to. edx-submissions
                records the course, the problem and its maximum score with each one.
        """
        self.block = block
        self.submission = XQueueInterfaceSubmission(block)

    def send_to_queue(self, header, body, files_to_upload=None):
        """
        Queue a submission for an external grader.

        header: JSON-serialized dict in the format described in 'xqueue_interface.make_xheader'

        body: Serialized data for the recipient behind the queueing service. The operation of
              the queue is agnostic to the contents of 'body'

        files_to_upload: List of file objects to be stored along with the queue request

        Returns (error_code, msg) where error_code != 0 indicates an error
        """
        from submissions.errors import SubmissionError  # pylint: disable=import-outside-toplevel

        files = {f.name: f for f in files_to_upload or []}

        header_info = json.loads(header)
        queue_key = header_info["lms_key"]

        # Report anything that keeps the submission from being queued as an error, so the
        # learner is told to try again rather than waiting on a submission that doesn't exist.
        # send_to_submission returns {"error": msg} for a bad request body and raises for the
        # rest; edx-submissions raises SubmissionError for its own failures.
        try:
            result = self.submission.send_to_submission(header, body, queue_key, files)
        except (SubmissionError, XQueueSubmissionError) as err:
            log.error("Could not queue submission for %s: %s", self.block.usage_key, err)
            return 1, str(err)
        if isinstance(result, dict) and "error" in result:
            return 1, result["error"]
        return 0, ""
