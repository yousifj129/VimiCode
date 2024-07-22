import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QTreeView, 
                               QFileSystemModel, QSplitter, QVBoxLayout, QWidget, 
                               QMenuBar, QMenu, QFileDialog, QCompleter
                               , QTabWidget, QMessageBox,QInputDialog)
from PySide6.QtCore import Qt, QDir, QStringListModel,QPoint
from PySide6.QtGui import QAction,QKeySequence
import jedi
from PySide6.QtWidgets import QCompleter
import subprocess
from Terminal import Terminal
from CodeEditor import CodeEditor

class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_file_system()
        self.setup_editor()
        self.setup_terminal()
        self.setup_layouts()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Python Text Editor")
        self.setGeometry(100, 100, 1200, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.create_menu_bar()

    def setup_file_system(self):
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.currentPath()))
        self.tree.setAnimated(False)
        self.tree.setIndentation(20)
        self.tree.setSortingEnabled(True)
        self.tree.setColumnWidth(0, 250)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)

    def setup_editor(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.completer = QCompleter(self)
        self.completer.setModel(QStringListModel())

    def setup_terminal(self):
        self.terminal = Terminal(self)
        self.terminal.output.append("Terminal ready.")
        self.cfont = self.terminal.font()

    def setup_layouts(self):
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # Left pane (file tree)
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.addWidget(self.tree)
        self.main_splitter.addWidget(left_pane)

        # Right pane (editor and terminal)
        self.right_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(self.right_splitter)

        self.right_splitter.addWidget(self.tab_widget)
        self.right_splitter.addWidget(self.terminal)

        # Set initial sizes
        self.main_splitter.setSizes([200, 1000])
        self.right_splitter.setSizes([600, 200])

    def connect_signals(self):
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tree.clicked.connect(self.open_file)
        self.tree.doubleClicked.connect(self.open_file)
        
        

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        open_action = QAction("&Open Folder", self)
        open_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_action)
        

        menu = QMenu()
        new_file_action = QAction("New File", self)
        new_file_action.triggered.connect(lambda: self.create_new_file(0))
        file_menu.addAction(new_file_action)

        save_action = QAction("&Save", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.tree.setRootIndex(self.model.index(folder))
            self.update_terminal_directory(folder)
        self.tab_widget.clear()

    def open_file(self, index):
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            # Check if the file is already open in a tab
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i).file_path == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return

            # If not, open a new tab
            with open(file_path, 'r') as file:
                content = file.read()
                new_tab = CodeEditor(self)
                new_tab.setPlainText(content)
                new_tab.file_path = file_path
                new_tab.setCompleter(self.completer)
                new_tab.blockCountChanged.connect(self.update_completer)
                new_tab.setFont(self.cfont)
                tab_name = os.path.basename(file_path)
                self.tab_widget.addTab(new_tab, tab_name)
                self.tab_widget.setCurrentWidget(new_tab)

            
                self.update_completer()
            
    def update_terminal_directory(self, directory):
        self.terminal.set_working_directory(directory)

    def close_tab(self, index):
        self.tab_widget.removeTab(index)

    def update_completer(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, CodeEditor) and current_tab.file_path.endswith('.py'):
            line, column = current_tab.get_current_line_column()
            script = jedi.Script(path=current_tab.file_path)
            
            completions = script.complete(line=line, column=column)
            words = [c.name for c in completions]
            self.completer.model().setStringList(words)
            self.tab_widget.currentWidget().jscript = script
            self.terminal.jscript = script

    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu()
        new_file_action = QAction("New File", self)
        new_file_action.triggered.connect(lambda: self.create_new_file(index))
        menu.addAction(new_file_action)

        delete_file_action = QAction("Delete", self)
        delete_file_action.triggered.connect(lambda: self.delete_file(index))
        menu.addAction(delete_file_action)

        save_file_action = QAction("Save", self)
        save_file_action.triggered.connect(lambda: self.save_file())
        menu.addAction(save_file_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def create_new_file(self, parent_index):
        if parent_index == 0:
            parent_path = self.terminal.current_directory
        else:
            parent_path = self.model.filePath(parent_index)
        if not os.path.isdir(parent_path):
            parent_path = os.path.dirname(parent_path)

        file_name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and file_name:
            full_path = os.path.join(parent_path, file_name)
            try:
                with open(full_path, 'w') as f:
                    pass  # Create an empty file
                self.open_file(self.model.index(full_path))
            except IOError:
                QMessageBox.critical(self, "Error", f"Unable to create file: {full_path}")

    def delete_file(self, index):
        file_path = self.model.filePath(index)
        reply = QMessageBox.question(self, "Delete File",
                                     f"Are you sure you want to delete {file_path}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                # Close the tab if the file is open
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.widget(i).file_path == file_path:
                        self.tab_widget.removeTab(i)
                        break
            except OSError:
                QMessageBox.critical(self, "Error", f"Unable to delete file: {file_path}")

    def save_file(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, CodeEditor) and hasattr(current_tab, 'file_path'):
            try:
                with open(current_tab.file_path, 'w') as file:
                    file.write(current_tab.toPlainText())
                self.terminal.output.append(f"File saved: {current_tab.file_path}")
            except IOError:
                QMessageBox.critical(self, "Error", f"Unable to save file: {current_tab.file_path}")
        else:
            QMessageBox.warning(self, "Warning", "No file is currently open for saving.")

    def zoom_in(self):
        self.cfont = self.terminal.font()
        self.cfont.setPointSize(self.cfont.pointSize() + 1)
        self.terminal.setFont(self.cfont)
        self.tab_widget.currentWidget().setFont(self.cfont)

    def zoom_out(self):
        self.cfont = self.terminal.font()
        self.cfont.setPointSize(self.cfont.pointSize() - 1)
        self.terminal.setFont(self.cfont)
        self.tab_widget.currentWidget().setFont(self.cfont)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Save):
            self.save_file()
        if event.matches(QKeySequence.ZoomIn):
            print("hello ")
            self.zoom_in()

        if event.matches(QKeySequence.ZoomOut):
            self.zoom_out()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = TextEditor()
    editor.show()
    sys.exit(app.exec())