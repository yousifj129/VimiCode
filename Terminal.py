import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PySide6.QtCore import Qt, QProcess, Signal
from PySide6.QtGui import QTextCursor
import shlex
import jedi

class InteractiveProcess(QProcess):
    output_ready = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.readyReadStandardOutput.connect(self.handle_stdout)
        self.readyReadStandardError.connect(self.handle_stderr)

    def start_command(self, command):
        if not command.strip():
            return  # Don't try to execute empty commands
        if isinstance(command, str):
            command = shlex.split(command)
        if command:
            program = command[0]
            args = command[1:]
            super().start(program, args)
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
        self.jscript : jedi.Script = None
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        print("Terminal widget initialized")

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
        self.output.append(f"{self.current_directory}$ {command}")
        self.output.append("\n")
        self.input.clear()
        
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        if command.startswith("cd "):
            self.change_directory(command[3:])
        else:
            self.process = InteractiveProcess(self)
            self.process.output_ready.connect(self.handle_output)
            self.process.finished.connect(self.process_finished)
            self.process.setWorkingDirectory(self.current_directory)
            self.process.start_command(command)
        
    def handle_output(self, output):
        self.output.moveCursor(QTextCursor.End)
        self.output.insertPlainText(output)
        self.output.moveCursor(QTextCursor.End)
        
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
            self.output.append(f"Changed directory to: {self.current_directory}")
        except FileNotFoundError:
            self.output.append(f"Directory not found: {new_dir}")
        except PermissionError:
            self.output.append(f"Permission denied: {new_dir}")
        self.update_prompt()
    
    def update_prompt(self):
        self.output.append(f"\n{self.current_directory}$ ")
    
    def set_working_directory(self, directory):
        self.current_directory = directory
        os.chdir(self.current_directory)
        self.update_prompt()