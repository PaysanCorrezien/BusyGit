from textual.widgets import Input, Pretty, Static
from textual.validation import Validator, ValidationResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.widgets import DataTable
import os

class PathValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        """Validate if path exists and is a directory."""
        path = os.path.expanduser(value.strip())
        if not value.strip():
            return self.failure("Path cannot be empty")
        if not os.path.exists(path):
            return self.failure("Path does not exist")
        if not os.path.isdir(path):
            return self.failure("Path is not a directory")
        return self.success()

class PathInputDialog(Container):
    DEFAULT_CSS = """
    PathInputDialog {
        layout: vertical;
        background: $surface;
        padding: 1;
        width: 60;
        height: auto;
        border: thick $primary;
        
        /* Center the dialog */
        align: center middle;
        
        /* Add some space from the top */
        margin-top: -10;
    }

    PathInputDialog > Input {
        width: 100%;
        margin-bottom: 1;
    }

    PathInputDialog > .validation-message {
        color: $error;
        height: auto;
        margin-top: 1;
        text-align: center;
    }

    PathInputDialog > .bindings {
        text-align: center;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "submit", "Submit", show=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input = Input(
            placeholder="Enter path to track...",
            validators=[PathValidator()],
        )
        self.validation_message = Static(classes="validation-message")
        self.bindings_display = Static("ESC to cancel • ENTER to submit", classes="bindings")

    def compose(self):
        yield self.input
        yield self.validation_message
        yield self.bindings_display

    def on_mount(self) -> None:
        self.input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if not event.validation_result.is_valid:
            self.validation_message.update("\n".join(event.validation_result.failure_descriptions))
        else:
            self.validation_message.update("")

    def action_submit(self) -> None:
        if self.input.value and self.input.is_valid:
            self.post_message(self.AddPath(self.input.value))
            self.remove()
            self.app.query_one(DataTable).focus()

    def action_cancel(self) -> None:
        self.remove()
        self.app.query_one(DataTable).focus()

    def action_remove_path(self) -> None:
        """Remove the currently selected path from the list."""
        if self.input.value:  # Assuming the input value is the selected path
            self.post_message(self.RemovePath(self.input.value))
            self.remove()
            self.app.query_one(DataTable).focus()

    class AddPath(Message):
        """Message sent when a valid path is submitted."""
        def __init__(self, path: str) -> None:
            self.path = path
            super().__init__() 

    class RemovePath(Message):
        """Message sent when a path is removed."""
        def __init__(self, path: str) -> None:
            self.path = path
            super().__init__() 