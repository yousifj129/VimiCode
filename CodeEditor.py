from PySide6.QtWidgets import ( QPlainTextEdit, QCompleter, QTextEdit, QToolTip
                               )
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import  QTextCharFormat, QFont, QSyntaxHighlighter, QTextCursor,QKeySequence, QColor
from PySide6.QtCore import QRegularExpression
import jedi
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.darkBlue)
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ["and", "as", "assert", "break", "class", "continue", "def",
                    "del", "elif", "else", "except", "False", "finally", "for",
                    "from", "global", "if", "import", "in", "is", "lambda",
                    "None", "nonlocal", "not", "or", "pass", "raise", "return",
                    "True", "try", "while", "with", "yield", "self"]
        
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, keyword_format))
        
        class_format = QTextCharFormat()
        class_format.setFontWeight(QFont.Bold)
        class_format.setForeground(Qt.darkMagenta)
        self.highlighting_rules.append((
            QRegularExpression(r'(?<=class\s)([A-Za-z_][A-Za-z0-9_]*)'),
            class_format
        ))

        function_format = QTextCharFormat()
        function_format.setFontItalic(True)
        function_format.setForeground(QColor("#FFD700"))
        self.highlighting_rules.append((
            QRegularExpression(r"(?<=def\s)([A-Za-z_][A-Za-z0-9_]*)"),
            function_format
        ))

        comment_format = QTextCharFormat()
        comment_format.setForeground(Qt.darkGreen)
        self.highlighting_rules.append((
            QRegularExpression(r'#.*'),
            comment_format
        ))

        string_format = QTextCharFormat()
        string_format.setForeground(Qt.darkYellow)
        self.highlighting_rules.extend([
            (QRegularExpression(r'".*?"'), string_format),
            (QRegularExpression(r"'.*?'"), string_format),
        ])
        
    def newRules(self, words, keyword_format):
        for word in words:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, keyword_format))
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None
        self.highlighter = PythonHighlighter(self.document())
        self.setFont(QFont("Courier", 10))
        self.jscript : jedi.Script = jedi.Script(code=self.document().toPlainText())
        self.words : list[str] = []
        self.setTabStopDistance(self.font().pointSize()*3)
        # self.blockCountChanged.connect(self.onBlockCountChanged)

    def setCompleter(self, completer):
        if self.completer:
            self.completer.disconnect(self)
        self.completer = completer
        if not self.completer:
            return

        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        if self.completer.widget() != self:
            return
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        super().focusInEvent(event)

    def get_current_line_column(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber()
        return line, column

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Save):
            return
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                self.completer.popup().hide()
                return

        isShortcut = (event.modifiers() == Qt.KeyboardModifier.ControlModifier and
                      event.key() == Qt.Key.Key_Space)

        if not self.completer or not isShortcut:
            super().keyPressEvent(event)

        ctrlOrShift = event.modifiers() in (Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier)
        if ctrlOrShift and not event.text():
            return

        eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        hasModifier = (event.modifiers() != Qt.KeyboardModifier.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        if not isShortcut and (hasModifier or not event.text() or
                               len(completionPrefix) < 1 or
                               event.text()[-1] in eow):
            self.completer.popup().hide()
            return

        if completionPrefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completionPrefix)
            self.completer.popup().setCurrentIndex(
                self.completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.completer.popup().sizeHintForColumn(0) +
                    self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(cr)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.showJediInfoForSelection()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.showJediInfoForSelection()

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.showJediInfoForSelection()
    def showJediInfoForSelection(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        # Get the line and column for the start of the selection
        cursor.setPosition(start)
        start_line = cursor.blockNumber() + 1
        start_column = cursor.columnNumber()
        # Get the line and column for the end of the selection
        cursor.setPosition(end)        
        try:
            inferred = self.jscript.infer(line=start_line, column=start_column)
            context = self.jscript.get_context(line=start_line, column=start_column).docstring()
            if inferred:
                info = "\n".join([f"{i.name}: {i.description}" for i in inferred]) + context
                if info:
                    cursor_rect = self.cursorRect(cursor)
                    global_pos = self.mapToGlobal(cursor_rect.bottomRight())
                    QToolTip.showText(global_pos, info, self)
                else:
                    QToolTip.hideText()
            else:
                QToolTip.hideText()
        except Exception as e:
            print(f"Jedi inference error: {e}")
            QToolTip.hideText()
    # def onBlockCountChanged(self):
    #     names = self.jscript.get_names()
    #     for word in names:
    #         if not self.words.__contains__(word.name):
    #             self.words.append(word.name)

        
    #     keyword_format = QTextCharFormat()
    #     keyword_format.setForeground(Qt.red)
    #     keyword_format.setFontWeight(QFont.Bold)
    #     self.highlighter.newRules(words=self.words, keyword_format=keyword_format)
    def leaveEvent(self, event):
        super().leaveEvent(event)
        QToolTip.hideText()