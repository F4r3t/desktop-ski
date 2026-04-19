from PySide6.QtWidgets import QApplication, QMainWindow
from design import Ui_MainWindow


def main():
    app = QApplication()
    window = QMainWindow()

    ui = Ui_MainWindow()
    ui.setupUi(window)

    window.show()
    app.exec()

if __name__ == "__main__":
    main()