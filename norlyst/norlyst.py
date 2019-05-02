from PyQt5.QtWidgets import (   QMainWindow, QAction, QWidget, QGridLayout,
                                qApp)
from PyQt5.QtGui import QIcon

"""
This module contains the MainWindow class of the NorLyst program.
The NorLystMain class will have all the functionality of the program inside of
it and it will pass all the messages between different parts of the program.
"""

class NorLystMain(QMainWindow):
    """
    The NorLystMain class. Defines the basic parameters of the whole program.
    """
    def __init__(self, screen_size):
        super().__init__()
        self.title = 'NorLyst'
        self.left = 0
        self.top = 0
        self.width = screen_size.width()
        self.height = screen_size.height()

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.initMenuBarItems()

        self.norlyst_widget = NorLystWidget(self)
        self.setCentralWidget(self.norlyst_widget)

        self.show()

    def initMenuBarItems(self):
        """
        Function for initialising basic menu bar items.
        """
        exit_act = QAction(QIcon('exit.png'), '&Exit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.triggered.connect(qApp.quit)

        self.file_menu = self.menuBar().addMenu('&File')
        self.file_menu.addAction(exit_act)

class NorLystWidget(QWidget):
    """
    NorLystWidget contains the core functionality of the NorLyst program.
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)

        self.setLayout(self.layout)


