class WorkflowError(RuntimeError):
    """A safe, user-actionable workflow failure."""


class ValidationError(WorkflowError):
    """Input or installed state violates the workflow contract."""


class TransactionError(WorkflowError):
    """A filesystem transaction failed and required rollback."""


class InputRequiredError(WorkflowError):
    """A lifecycle operation needs explicit user-provided input to continue."""

    def __init__(self, message: str, *, prompt: str, input_file: str) -> None:
        super().__init__(message)
        self.prompt = prompt
        self.input_file = input_file
