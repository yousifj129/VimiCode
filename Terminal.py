import os
import shlex
import subprocess
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, QProcess, Signal
from PySide6.QtGui import QTextCursor

class Terminal(QTextEdit):
    command_executed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.process = None
        self.current_input = ""
        self.cursor_position = 0
        self.command_history = []
        self.history_index = -1
        self.current_directory = os.getcwd()

        self.prompt = f"{self.current_directory}$ "
        self.insertPlainText(self.prompt)
        self.prompt_position = self.textCursor().position()

    def keyPressEvent(self, event):
        if self.process and self.process.state() == QProcess.Running:
            if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
                self.interrupt_process()
            return

        if event.key() == Qt.Key_Return:
            self.execute_command()
        elif event.key() == Qt.Key_Backspace:
            self.handle_backspace()
        elif event.key() == Qt.Key_Left:
            self.move_cursor_left()
        elif event.key() == Qt.Key_Right:
            self.move_cursor_right()
        elif event.key() == Qt.Key_Up:
            self.show_previous_command()
        elif event.key() == Qt.Key_Down:
            self.show_next_command()
        elif event.text():
            self.insert_text(event.text())

    def insert_text(self, text):
        self.current_input = (
            self.current_input[:self.cursor_position] +
            text +
            self.current_input[self.cursor_position:]
        )
        self.cursor_position += len(text)
        self.update_display()

    def handle_backspace(self):
        if self.cursor_position > 0:
            self.current_input = (
                self.current_input[:self.cursor_position - 1] +
                self.current_input[self.cursor_position:]
            )
            self.cursor_position -= 1
            self.update_display()

    def move_cursor_left(self):
        if self.cursor_position > 0:
            self.cursor_position -= 1
            self.update_display()

    def move_cursor_right(self):
        if self.cursor_position < len(self.current_input):
            self.cursor_position += 1
            self.update_display()

    def show_previous_command(self):
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.current_input = self.command_history[-1 - self.history_index]
            self.cursor_position = len(self.current_input)
            self.update_display()

    def show_next_command(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_input = self.command_history[-1 - self.history_index]
        elif self.history_index == 0:
            self.history_index -= 1
            self.current_input = ""
        self.cursor_position = len(self.current_input)
        self.update_display()

    def update_display(self):
        cursor = self.textCursor()
        cursor.setPosition(self.prompt_position)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(self.current_input)
        cursor.setPosition(self.prompt_position + self.cursor_position)
        self.setTextCursor(cursor)

    def execute_command(self):
        command = self.current_input.strip()
        self.appendPlainText("\n")
        
        if command:
            self.command_history.append(command)
            self.history_index = -1

            if command.startswith("cd "):
                self.change_directory(command[3:])
            else:
                self.run_process(command)
        else:
            # If no command is entered, just print a new prompt
            self.appendPlainText(self.prompt)

        self.current_input = ""
        self.cursor_position = 0
        self.prompt_position = self.textCursor().position()

    def change_directory(self, path):
        try:
            os.chdir(path)
            self.current_directory = os.getcwd()
            self.prompt = f"{self.current_directory}$ "
        except FileNotFoundError:
            self.appendPlainText(f"cd: no such file or directory: {path}")
        except PermissionError:
            self.appendPlainText(f"cd: permission denied: {path}")
        finally:
            self.appendPlainText(self.prompt)

    def run_process(self, command):
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        try:
            self.process.start(command)
        except Exception as e:
            self.appendPlainText(f"Error: {str(e)}")
            self.appendPlainText(self.prompt)
            self.command_executed.emit()

    def process_finished(self):
        self.process = None
        self.appendPlainText(self.prompt)
        self.command_executed.emit()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.appendPlainText(stdout)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.appendPlainText(stderr)


    def interrupt_process(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.appendPlainText("^C")
            self.command_executed.emit()