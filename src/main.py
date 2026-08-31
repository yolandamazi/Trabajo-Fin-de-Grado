import sys
from PyQt5.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.utils.helpers import ensure_directories_exist

def main():
    ensure_directories_exist()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()