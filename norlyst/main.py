"""
Main script of the NorLysti. Starts the program and does nothing else.
"""
import sys

from PyQt5.QtWidgets import QApplication

from norlyst import NorLystMain

if __name__ == '__main__':
    app = QApplication(sys.argv)
    screen_size = QApplication.desktop().availableGeometry()
    ex = NorLystMain(screen_size)
    sys.exit(app.exec_())
