from PyQt5 import QtGui, QtCore, QtWidgets
import daq
import sys


class Second(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)


class First(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pushButton = QtWidgets.QPushButton("Click me")
        self.pushButton2 = QtWidgets.QPushButton("DAQ")
        self.setCentralWidget(self.pushButton)
        self.setCentralWidget(self.pushButton2)

        self.pushButton.clicked.connect(self.on_pushButton_clicked)
        self.pushButton2.clicked.connect(self.on_pushButton2_clicked)
        self.dialogs = list()

    def on_pushButton_clicked(self):
        dialog = Second(self)
        self.dialogs.append(dialog)
        dialog.show()
        self.hide()

    def on_pushButton2_clicked(self):
        dialog = daq.DAQ()
        self.dialogs.append(dialog)
        self.hide()


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = First()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()