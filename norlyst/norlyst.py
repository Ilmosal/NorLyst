"""
This module contains the MainWindow class of the NorLyst program.
The NorLystMain class will have all the functionality of the program inside of
it and it will pass all the messages between different parts of the program.
"""

import datetime

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (   QMainWindow, QAction, QWidget, QGridLayout,
                                qApp, QTabWidget)
from PyQt5.QtGui import QIcon

from overviewPage import OverviewPage
from eventPage import EventPage
from databaseAccess import DatabaseAccesser
from misc import UpdateQueue, WaveformAccessManager

class NorLystMain(QMainWindow):
    """
    The NorLystMain class. Defines the basic parameters of the whole program.
    """
    def __init__(self, screen_size):
        super(NorLystMain, self).__init__()
        self.title = 'NorLyst'
        self.left = 0
        self.top = 0
        self.width = screen_size.width()
        self.height = screen_size.height()

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.norlyst_widget = NorLystWidget(self)
        self.setCentralWidget(self.norlyst_widget)

        self.initMenuBarItems()

        self.show()

    def closeEvent(self, event):
        """
        Overloading function for saving all changes if the program exits
        """
        self.norlyst_widget.saveChanges()

    def initMenuBarItems(self):
        """
        Function for initialising basic menu bar items.
        """
        exit_act = QAction(QIcon('exit.png'), '&Exit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.triggered.connect(qApp.quit)

        clear_act = QAction(QIcon('clear.png'), '&Clear', self)
        clear_act.setShortcut('Ctrl+C')
        clear_act.triggered.connect(self.norlyst_widget.clearEventFocus)

        self.file_menu = self.menuBar().addMenu('&File')
        self.file_menu.addAction(exit_act)

        self.edit_menu = self.menuBar().addMenu('&Edit')
        self.edit_menu.addAction(clear_act)

class NorLystWidget(QWidget):
    """
    NorLystWidget contains the core functionality of the NorLyst program.
    """
    def __init__(self, parent):
        super(NorLystWidget, self).__init__(parent)
        self.tabs = QTabWidget()

        self.waveform_access_manager = WaveformAccessManager(self)
        self.database_accesser = DatabaseAccesser()
        self.update_queue = UpdateQueue(self.database_accesser)
        self.overview_page = OverviewPage(self, self.database_accesser)
        self.event_page = EventPage(self, self.database_accesser)
        self.event_classifications = []

        self.tabs.addTab(self.overview_page, 'Overview')
        self.tabs.addTab(self.event_page, 'Event')

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.tabs, 0, 0)

        self.setLayout(self.layout)

        self.overview_page.daily_lock_manager.setNewEventsDate()
        self.chosen_date = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.saveChanges)
        self.timer.start(500)

    def saveChanges(self):
        """
        Force update queue to update the rest of the changes.
        """
        if self.update_queue.processQueue():
            self.setEventClassifications()

    def setEventsForChosenDate(self, chosen_date):
        """
        Get current selected event_classifications. Returns a list of NordicEvent Objects
        """
        self.chosen_date = chosen_date
        self.event_classifications = self.database_accesser.getEventClassifications(chosen_date, self.update_queue)
        self.setEventClassifications()

    def setEventClassifications(self):
        """
        Function for setting the event classification for the program
        """
        self.event_classifications.sort(key = lambda x: x.getSortPriority(), reverse=True)

        self.overview_page.setEventClassifications(self.event_classifications, self.chosen_date)
        self.event_page.setEventClassifications(self.event_classifications, self.chosen_date)

    def focusOnEvent(self, event_id):
        """
        Function for focusing on a single event and passing the information to the rest of the program
        """
        for ec in self.event_classifications:
            if ec.event_id == event_id:
                ec.focus = True
            else:
                ec.focus = False

        for ec in self.event_classifications:
            if ec.focus:
                self.waveform_access_manager.setActiveEvent(ec.getEvent())

        if self.event_classifications:
            self.setEventClassifications()

    def getFocusedEvent(self):
        """
        Function for returning the focused event
        """
        for ec in self.event_classifications:
            if ec.focus:
                return ec.getEvent()

    def setActiveEventToEventPage(self, waveform_traces):
        """
        Pass waveform data from station_list alongside with the new active event for plotting the current waveform
        """
        self.event_page.station_list.setCurrentWaveforms(waveform_traces, self.getFocusedEvent())

        if self.event_page.spectrogram_widget is not None and not self.event_page.spectrogram_widget.hidden:
            self.event_page.spectrogram_widget.setStationsFromNewEvent()

    def clearEventFocus(self):
        """
        Clear focus on all events and pass information forwards
        """
        for ec in self.event_classifications:
            ec.focus = False

        if self.event_classifications:
            self.overview_page.setEventClassifications(self.event_classifications)

