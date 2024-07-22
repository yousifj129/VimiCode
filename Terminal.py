import shutil
import os
import shlex
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PySide6.QtCore import Qt, QProcess, Signal
from PySide6.QtGui import QTextCursor
import jedi

class InteractiveProcess(QProcess):
    output_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.readyReadStandardOutput.connect(self.handle_stdout)
        self.readyReadStandardError.connect(self.handle_stderr)

    def start_command(self, command):
        if not command.strip():
            return  # Don't try to execute empty commands

        command_list = shlex.split(command)
        if command_list:
            program = command_list[0]
            args = command_list[1:]

            # Check if the program exists
            if not self.is_command_valid(program):
                self.error_occurred.emit(f"Error: Command '{program}' not found.\n")
                return

            super().start(program, args)

    def is_command_valid(self, command):
        """ Check if the command exists in the system's PATH. """
        return shutil.which(command) is not None

    def handle_stdout(self):
        data = self.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.output_ready.emit(stdout)

    def handle_stderr(self):
        data = self.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.output_ready.emit(stderr)


class Terminal(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output)
        
        self.input = QLineEdit(self)
        self.layout.addWidget(self.input)
        
        self.input.returnPressed.connect(self.run_command)
        
        self.current_directory = os.getcwd()
        self.update_prompt()
        
        self.command_history = []
        self.history_index = 0
        
        self.process = None

    def run_command(self):
        command = self.input.text()
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        self.output.moveCursor(QTextCursor.End)
        self.output.insertPlainText(f"\n{self.current_directory}$ {command}\n")
        self.input.clear()

        if command.startswith("cd "):
            self.change_directory(command[3:])
        else:
            self.process = InteractiveProcess(self)
            self.process.output_ready.connect(self.handle_output)
            self.process.error_occurred.connect(self.handle_error)
            self.process.finished.connect(self.process_finished)
            self.process.setWorkingDirectory(self.current_directory)
            self.process.start_command(command)

    def handle_output(self, output):
        self.output.moveCursor(QTextCursor.End)
        self.output.insertPlainText(output)

    def handle_error(self, error_message):
        self.output.moveCursor(QTextCursor.End)
        self.output.insertPlainText(error_message)

    def process_finished(self):
        self.process = None
        self.update_prompt()
        
    def keyPressEvent(self, event):
        if self.process and self.process.state() == QProcess.Running:
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self.process.write(b'\n')
            else:
                self.process.write(event.text().encode())
        else:
            if event.key() == Qt.Key_Up:
                self.show_previous_command()
            elif event.key() == Qt.Key_Down:
                self.show_next_command()
            elif event.key() == Qt.Key_Tab:
                self.input.setText(self.input.text() + "    ")
            elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self.run_command()
            else:
                super().keyPressEvent(event)
    
    def show_previous_command(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.input.setText(self.command_history[self.history_index])
    
    def show_next_command(self):
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input.setText(self.command_history[self.history_index])
        elif self.history_index == len(self.command_history) - 1:
            self.history_index += 1
            self.input.clear()
    
    def change_directory(self, new_dir):
        try:
            os.chdir(os.path.join(self.current_directory, new_dir))
            self.current_directory = os.getcwd()
            self.output.moveCursor(QTextCursor.End)
            self.output.insertPlainText(f"Changed directory to: {self.current_directory}\n")
        except FileNotFoundError:
            self.output.moveCursor(QTextCursor.End)
            self.output.insertPlainText(f"Directory not found: {new_dir}\n")
        except PermissionError:
            self.output.moveCursor(QTextCursor.End)
            self.output.insertPlainText(f"Permission denied: {new_dir}\n")
        self.update_prompt()
    
    def update_prompt(self):
        self.output.moveCursor(QTextCursor.End)
