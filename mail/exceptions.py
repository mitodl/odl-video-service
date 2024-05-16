"""Exceptions for mail"""


class SendBatchException(Exception):  # noqa: N818
    """
    An exception which occurs when batch processing of email fails. This contains a list of other exceptions and
    the emails which caused the failure.
    """  # noqa: E501

    def __init__(self, exception_pairs):
        """
        Creates a SendBatchException

        Args:
            exception_pairs (list): A list of (list of recipients, exception)
        """  # noqa: D401
        super().__init__(exception_pairs)
        self.exception_pairs = exception_pairs

    @property
    def failed_recipient_emails(self):
        """
        Yields a list of recipient emails that we failed to send to
        """
        for recipients, _ in self.exception_pairs:
            yield from recipients
