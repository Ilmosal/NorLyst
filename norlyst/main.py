"""
Main script of the NorLysti. Starts the program and does nothing else.
"""
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QGuiApplication

from norlyst.norlyst import NorLystMain

def run():
    app = QApplication(sys.argv)
    screen_size = QApplication.desktop().screenGeometry()
    ex = NorLystMain(screen_size)
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()
