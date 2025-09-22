import os.path
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog, QAction, QMessageBox
)
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QKeySequence
from PyQt5.QtCore import QRegularExpression

# ---- HALCON operator list (expandable) ----
HALCON_OPERATORS = {
    "read_image", "write_image", "dev_open_window", "dev_close_window",
    "dev_display", "disp_image", "clear_window", "gen_image_const",
    "threshold", "connection", "select_shape", "union1", "difference",
    "intersection", "fill_up", "dilation1", "erosion1",
    "gen_circle", "gen_rectangle1", "gen_region_points",
    "area_center", "orientation_region", "count_obj",
    "if", "endif", "for", "endfor", "while", "endwhile",
    "stop", "return"
}


# ---- Syntax Highlighter ----
class HalconHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("blue"))
        self.keyword_format.setFontWeight(QFont.Bold)

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("darkgreen"))
        self.comment_format.setFontItalic(True)

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("darkred"))

        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor("red"))
        self.error_format.setFontWeight(QFont.Bold)

    def highlightBlock(self, text: str):
        # Comments (* ...)
        if text.strip().startswith("*"):
            self.setFormat(0, len(text), self.comment_format)
            return

        # Strings "..."
        regex = QRegularExpression(r'"[^"]*"')
        it = regex.globalMatch(text)
        while it.hasNext():
            match = it.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), self.string_format)

        # Split into tokens and check first operator
        tokens = text.strip().split()
        if not tokens:
            return

        first = tokens[0]
        if first in HALCON_OPERATORS:
            self.setFormat(0, len(first), self.keyword_format)
        else:
            self.setFormat(0, len(first), self.error_format)


# ---- Main Window ----
class HalconEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HALCON HDevelop Editor")
        self.resize(900, 600)

        # Text editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.setCentralWidget(self.editor)

        # Syntax highlighter
        self.highlighter = HalconHighlighter(self.editor.document())

        # Menu
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_file)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_file)

        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.save_file_as)

        save_as_action = QAction("Exit", self)
        save_as_action.triggered.connect(self.exit)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)

        self.current_path = None

    # ---- File Handling ----
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open HDevelop File", "", "HDevelop Files (*.hdev)")
        if not path:
            return
        self.current_path = path

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            lines = []
            for child in root.iter():
                if child.tag == "l":
                    lines.append(child.text or "")
                elif child.tag == "c":
                    lines.append(f"{child.text or ''}")
            code = "\n".join(lines)
            self.editor.setPlainText(code)
            self.setWindowTitle(path + " - HALCON HDevelop Editor")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")

    def save_file(self):
        if not self.current_path:
            return self.save_file_as()
        self._write_hdev(self.current_path)

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save HDevelop File As", "", "HDevelop Files (*.hdev)")
        if not path:
            return
        self.current_path = path
        self._write_hdev(self.current_path)

    def exit(self):
        sys.exit(app.exec_())

    # ---- Internal helper to save XML hdev ----
    def _write_hdev(self, path):
        try:
            code = self.editor.toPlainText().splitlines()

            # Root element
            program = ET.Element("hdevelop")
            body = ET.SubElement(program, "body")

            for line in code:
                if line.strip().startswith("*"):  # comment
                    c_elem = ET.SubElement(body, "c")
                    c_elem.text = line.lstrip("*").strip()
                else:  # code line
                    l_elem = ET.SubElement(body, "l")
                    l_elem.text = line

            # Pretty print XML
            xml_str = ET.tostring(program, encoding="utf-8")
            pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

            with open(path, "w", encoding="utf-8") as f:
                f.write(pretty_xml)

            QMessageBox.information(self, "Saved", f"File saved as valid HDevelop XML:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")


# ---- Run the App ----
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HalconEditor()
    window.show()
    sys.exit(app.exec_())
