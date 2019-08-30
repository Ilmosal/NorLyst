"""
This module contains small helper classes and functions that are not clearly part of an other area of NorLyst
"""
import time

from PyQt5.QtWidgets import QFrame, QPushButton, QCheckBox, QDoubleSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject

from waveformlocator.waveformLocator import WaveformLocator

from config import *

class EventClassification():
    """
    Class for event classifications in the database
    """
    def __init__(self, ec_id, daily_id, priority, event_id, classification, eqex, certainty, username, analysis_id, unimportant, done, update_queue):
        self.ec_id = ec_id
        self.event_id = event_id
        self.classification = classification
        self.eqex = eqex
        self.certainty = certainty
        self.update_queue = update_queue

        self._priority = priority
        self._unimportant = unimportant
        self._done = done
        self._username = username
        self._analysis_id = analysis_id

        self.analysis = None
        self.event = None
        self.focus = False

    def listItemStringArray(self):
        """
        Return list of values needed by the EventList for the list string
        """
        if self.event is None:
            return None

        values = [
            self.event.event_id,
            self.event.getOriginTime().val.strftime('%H:%M:%S'),
            self.event.getLatitude().val,
            self.event.getLongitude().val,
            self.event.getMagnitude().val
        ]
        return values

    def getSortPriority(self):
        if self._done:
            return -10
        if self._unimportant:
            return -999
        if self._priority > -1:
            return self._priority
        else:
            return 0 - self.classification

    def getEvent(self):
        """
        Function for getting the automatic event if there is no analysis and the analysis event if there is one.
        """
        if self.analysis is None:
            return self.event
        else:
            return self.analysis

    def setEvent(self, event):
        self.event = event

    def setAnalysis(self, event):
        self.analysis = event

    @property
    def analysis_id(self):
        return self._analysis_id

    @property
    def priority(self):
        return self._priority

    @property
    def username(self):
        return self._username

    @property
    def unimportant(self):
        return self._unimportant

    @property
    def done(self):
        return self._done

    @analysis_id.setter
    def analysis_id(self, value):
        self.update_queue.addUpdateEvent(UpdateQueue.ANALYSIS_ID_UPDATE_OPERATION, self.ec_id, value)
        self._analysis_id = value

    @priority.setter
    def priority(self, value):
        self.update_queue.addUpdateEvent(UpdateQueue.PRIORITY_UPDATE_OPERATION, self.ec_id, value)
        self._priority = value

    @username.setter
    def username(self, value):
        self.update_queue.addUpdateEvent(UpdateQueue.USERNAME_UPDATE_OPERATION, self.ec_id, value)
        self._username = value

    @unimportant.setter
    def unimportant(self, value):
        self.update_queue.addUpdateEvent(UpdateQueue.UNIMPORTANT_UPDATE_OPERATION, self.ec_id, value)
        self._unimportant = value

    @done.setter
    def done(self, value):
        self.update_queue.addUpdateEvent(UpdateQueue.DONE_UPDATE_OPERATION, self.ec_id, value)
        self._done = value

class UpdateQueue():
    """
    Class containing necessary database updates in a queue
    """
    ANALYSIS_ID_UPDATE_OPERATION = 1
    PRIORITY_UPDATE_OPERATION = 2
    USERNAME_UPDATE_OPERATION = 3
    UNIMPORTANT_UPDATE_OPERATION = 4
    DONE_UPDATE_OPERATION = 5

    def __init__(self, database_accesser):
        self.queue_buffer = []
        self.database_accesser = database_accesser

        self.DATABASE_OPERATIONS = {
            1: self.database_accesser.analysisIdUpdate,
            2: self.database_accesser.priorityUpdate,
            3: self.database_accesser.usernameUpdate,
            4: self.database_accesser.setEventAsUnimportant,
            5: self.database_accesser.setEventAsDone
        }

    def addUpdateEvent(self, operation, event_classification_id, value):
        """
        Function for adding an update event
        """
        self.queue_buffer.append([operation, event_classification_id, value])

    def processQueue(self):
        """
        Function for processing the updateQueue
        """
        if not self.queue_buffer:
            return False

        for update_event in self.queue_buffer:
            operation, event_classification_id, value = update_event
            self.DATABASE_OPERATIONS[operation](event_classification_id, value)

        self.queue_buffer.clear()

        return True

class WaveformAccessManager(QObject):
    """
    Class for fetching waveform data and assigning them to the event classifications
    """
    def __init__(self, parent):
        QObject.__init__(self, parent)
        self.active_event_id = -1
        self.next_active_id = -1
        self.active_waveform = None

        self.old_waveform_cache = {}
        self.predictive_waveform_cache = {}
        self.old_waveform_counter = 0
        self.predictive_waveform_counter = 0

        self.fetch_command_buffer = []

        self.waveform_access_thread = WaveformAccessThread()
        self.waveform_access_thread.signal.connect(self.setWaveform)

    def setActiveEvent(self, event):
        """
        Set this event as the new active event
        """
        if self.active_event_id == event.event_id:
            return

        if event.event_id in list(self.old_waveform_cache.keys()):
            self.insertEventFromOldToActive(event.event_id)
            return
        elif event.event_id in list(self.predictive_waveform_cache.keys()):
            self.insertEventFromPredictiveToActive(event.event_id)
            return

        self.next_active_id = event.event_id

        for i in range(len(self.fetch_command_buffer)):
            if self.fetch_command_buffer[i][0].event_id == event.event_id:
                if i > 1:
                    self.fetch_command_buffer.insert(1, self.fetch_command_buffer.pop(i))
                return

        self.getWaveform(event)

    def getWaveform(self, event, predictive = False):
        """
        Function for starting the fetching operation on waveform access thread or buffering the fetching operation
        """
        if self.waveform_access_thread.is_fetching:
            self.fetch_command_buffer.append([event, predictive])
        else:
            self.fetch_command_buffer.append([event, predictive])
            self.waveform_access_thread.is_fetching = True
            self.waveform_access_thread.predictive_event = self.fetch_command_buffer[0][1]
            self.waveform_access_thread.event = self.fetch_command_buffer[0][0]
            self.waveform_access_thread.start()

        if not predictive:
            for e in self.getEventPredictions(event):
                self.getWaveform(e, True)

    def setWaveform(self, waveform):
        """
        Function for setting the fetched waveform from the access thread and removing the event from the buffer. THIS FUNCTION IS ONLY CALLED FROM THE WAVEFORMACCESSTHREAD
        """
        if self.next_active_id == self.waveform_access_thread.event.event_id:
            self.insertEventToActive(self.waveform_access_thread.event.event_id, waveform)
        elif self.waveform_access_thread.predictive_event:
            self.insertEventToPredictive(self.waveform_access_thread.event.event_id, waveform)
        else:
            self.insertEventToOld(self.waveform_access_thread.event.event_id, waveform)

        self.fetch_command_buffer.pop(0)
        self.waveform_access_thread.is_fetching = False

        if self.fetch_command_buffer:
            self.waveform_access_thread.is_fetching = True
            self.waveform_access_thread.predictive_event = self.fetch_command_buffer[0][1]
            self.waveform_access_thread.event = self.fetch_command_buffer[0][0]
            self.waveform_access_thread.start()

    def insertEventToOld(self, event_id, waveform):
        """
        Insert given event_id and waveform pair into the old_waveform_cache and if the buffer is old then remove the oldest pair from the buffer
        """
        if len(self.old_waveform_cache.keys()) < WAVEFORM_OLD_BUFFER_SIZE:
            self.old_waveform_cache[event_id] = [self.old_waveform_counter, waveform]
        else:
            smallest = next(iter(self.old_waveform_cache))

            for key in self.old_waveform_cache.keys():
                if self.old_waveform_cache[smallest] > self.old_waveform_cache[key]:
                    smallest = key

            del self.old_waveform_cache[smallest]

            self.old_waveform_cache[event_id] = [self.old_waveform_counter, waveform]

        self.old_waveform_counter += 1

    def insertEventToPredictive(self, event_id, waveform):
        """
        Inset given event_id and waveform pair into the predictive_waveform_cache and remove the oldest value if the buffer is full
        """
        if len(self.predictive_waveform_cache.keys()) < WAVEFORM_PREDICTIVE_BUFFER_SIZE:
            self.predictive_waveform_cache[event_id] = [self.predictive_waveform_counter, waveform]
        else:
            smallest = next(iter(self.predictive_waveform_cache))

            for key in self.predictive_waveform_cache.keys():
                if self.predictive_waveform_cache[smallest] > self.predictive_waveform_cache[key]:
                    smallest = key

            del self.predictive_waveform_cache[smallest]

            self.predictive_waveform_cache[event_id] = [self.predictive_waveform_counter, waveform]

        self.predictive_waveform_counter += 1

    def insertEventToActive(self, event_id, waveform):
        """
        Set the event as the active event and if there is an event before inserting, then insert the old event to the old_waveform_cache.
        """
        if self.active_waveform is not None:
            self.insertEventFromActiveToOld()
        self.active_waveform = waveform
        self.active_event_id = event_id
        self.parent().setActiveEventToEventPage(self.active_waveform)

    def insertEventFromPredictiveToActive(self, event_id):
        """
        Insert the event from predictive cache as the active event.
        """
        waveform = self.predictive_waveform_cache[event_id][1]
        del self.predictive_waveform_cache[event_id]
        self.insertEventToActive(event_id, waveform)

    def insertEventFromActiveToOld(self):
        """
        Insert the active event into the old events cache and null the active event.
        """
        self.insertEventToOld(self.active_event_id, self.active_waveform)
        self.active_waveform = None
        self.active_event_id = -1

    def insertEventFromOldToActive(self, event_id):
        """
        Insert an event from the old_waveform_cache as the active event.
        """
        waveform = self.old_waveform_cache[event_id][1]
        del self.old_waveform_cache[event_id]
        self.insertEventToActive(event_id, waveform)

    def getEventPredictions(self, event):
        """
        Get prective events for a single event.
        """

        return []

class WaveformAccessThread(QThread):
    """
    This class describes the object that handles the waveform requests on the background of the program.
    """
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)

        self.waveform_locator = WaveformLocator(WAVEFORM_LOCATOR_CONFIG_FILE)
        self.event = None
        self.predictive_event = False
        self.is_fetching = False

    def run(self):
        ordered_waveforms = {}
        if self.event is not None:
            for tr in self.waveform_locator.getEventWaveforms(self.event):
                if tr.stats['station'] not in ordered_waveforms.keys():
                    ordered_waveforms[tr.stats['station']] = []
                ordered_waveforms[tr.stats['station']].append(tr)

        self.signal.emit(ordered_waveforms)

class FilterStats():
    """
    This is a container widget for filter values
    """

    def __init__(self, spectro_filter = False):
        if spectro_filter:
            self.default_filters = []
            self.default_filters.extend(DEFAULT_SPECTROGRAM_FILTERS)
            self.default_filters.append(['Custom filter', 'HP', 1.0, 2.0, True])
        else:
            self.default_filters = [["No filter", None, None, None, None]]
            self.default_filters.extend(DEFAULT_FILTERS)
            self.default_filters.append(['Custom Filter', 'BP', 1.0, 4.0, False])

        self.filter_types = ["BP", "HP", "LP"]

        self.current_filter = 0

    def getCurrentFilter(self):
        """
        Get current filter values
        """
        return self.default_filters[self.current_filter]

    def setCustomType(self, filter_type):
        """
        Set value to the custom filter type
        """
        self.default_filters[-1][1] = filter_type

    def setCustomLow(self, low):
        """
        Set value to the custom filter low
        """
        self.default_filters[-1][2] = low

    def setCustomHigh(self, high):
        """
        Set value to the custom filter high
        """
        self.default_filters[-1][3] = high

    def setCustomZeroPhase(self, zp):
        """
        Set value to the custom filter zerophase
        """
        self.default_filters[-1][4] = bool(zp)

class FilterWidget(QFrame):
    """
    This widget controls the filter parameters of the program
    """
    def __init__(self, parent, filter_stats):
        super(QFrame, self).__init__(parent)
        self.setFixedWidth(400)
        self.setFixedHeight(80)

        self.filter_stats = filter_stats

        self.main_layout = QVBoxLayout(self)
        self.top_layout = QHBoxLayout(self)
        self.bottom_layout = QHBoxLayout(self)

        self.filter_label = QLabel('Current Filter:')
        self.filter_choice = QComboBox()
        self.filter_choice.activated.connect(self.chooseFilter)

        self.filter_type_label = QLabel('Type')
        self.filter_low_label = QLabel('Low')
        self.filter_high_label = QLabel('High')

        self.apply_filter_btn = QPushButton('Plot')
        self.apply_filter_btn.pressed.connect(self.parent().filterChange)

        self.filter_type = QComboBox()
        self.filter_type.activated.connect(self.chooseFilterType)

        for f_type in self.filter_stats.filter_types:
            self.filter_type.addItem(f_type)

        self.filter_low = QDoubleSpinBox()
        self.filter_low.valueChanged.connect(self.filter_stats.setCustomLow)
        self.filter_high = QDoubleSpinBox()
        self.filter_high.valueChanged.connect(self.filter_stats.setCustomHigh)
        self.filter_zero_phase = QCheckBox('Zero Phase')
        self.filter_zero_phase.stateChanged.connect(self.filter_stats.setCustomZeroPhase)

        for fil in self.filter_stats.default_filters:
            self.filter_choice.addItem(fil[0])

        self.top_layout.addWidget(self.filter_label)
        self.top_layout.addWidget(self.filter_choice)

        self.bottom_layout.addWidget(self.filter_type_label)
        self.bottom_layout.addWidget(self.filter_type)
        self.bottom_layout.addWidget(self.filter_low_label)
        self.bottom_layout.addWidget(self.filter_low)
        self.bottom_layout.addWidget(self.filter_high_label)
        self.bottom_layout.addWidget(self.filter_high)
        self.bottom_layout.addWidget(self.filter_zero_phase)
        self.bottom_layout.addWidget(self.apply_filter_btn)

        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addLayout(self.bottom_layout)

        self.setLayout(self.main_layout)

        self.chooseFilter(self.filter_stats.current_filter)

    def chooseFilter(self, filter_index):
        """
        Function that will be called when the filter selection is changed
        """
        self.filter_stats.current_filter = filter_index

        if self.filter_stats.getCurrentFilter()[0] == "No filter":
            self.filter_type_label.setVisible(False)
            self.filter_low_label.setVisible(False)
            self.filter_high_label.setVisible(False)
            self.filter_type.setVisible(False)
            self.filter_low.setVisible(False)
            self.filter_high.setVisible(False)
            self.filter_zero_phase.setVisible(False)
        else:
            self.filter_type_label.setVisible(True)
            self.filter_type.setVisible(True)
            self.filter_zero_phase.setVisible(True)

            if self.filter_stats.getCurrentFilter()[1] == "BP":
                self.chooseFilterType(0)
                self.filter_type.setCurrentIndex(0)
                self.filter_low.setValue(self.filter_stats.getCurrentFilter()[2])
                self.filter_high.setValue(self.filter_stats.getCurrentFilter()[3])

            elif self.filter_stats.getCurrentFilter()[1] == "HP":
                self.chooseFilterType(1)
                self.filter_type.setCurrentIndex(1)
                self.filter_high.setValue(self.filter_stats.getCurrentFilter()[3])

            elif self.filter_stats.getCurrentFilter()[1] == "LP":
                self.chooseFilterType(2)
                self.filter_type.setCurrentIndex(2)
                self.filter_low.setValue(self.filter_stats.getCurrentFilter()[2])

            self.filter_zero_phase.setChecked(self.filter_stats.getCurrentFilter()[4])

        if self.filter_stats.getCurrentFilter()[0] == "Custom Filter":
            self.apply_filter_btn.setVisible(True)
            self.filter_type.setEnabled(True)
            self.filter_low.setEnabled(True)
            self.filter_high.setEnabled(True)
            self.filter_zero_phase.setEnabled(True)
        else:
            self.apply_filter_btn.setVisible(False)
            self.filter_type.setEnabled(False)
            self.filter_low.setEnabled(False)
            self.filter_high.setEnabled(False)
            self.filter_zero_phase.setEnabled(False)

            self.parent().filterChange()

    def chooseFilterType(self, filter_type_id):
        """
        Function for choosing the filter type
        """
        if filter_type_id == 0:
            self.filter_low_label.setVisible(True)
            self.filter_low.setVisible(True)

            self.filter_high_label.setVisible(True)
            self.filter_high.setVisible(True)
            self.filter_stats.setCustomType("BP")

        elif filter_type_id == 1:
            self.filter_low_label.setVisible(False)
            self.filter_low.setVisible(False)

            self.filter_high_label.setVisible(True)
            self.filter_high.setVisible(True)
            self.filter_stats.setCustomType("HP")

        elif filter_type_id == 2:
            self.filter_low_label.setVisible(True)
            self.filter_low.setVisible(True)

            self.filter_high_label.setVisible(False)
            self.filter_high.setVisible(False)

            self.filter_stats.setCustomType("LP")

def filterTrace(tr_filter, trace):
    """
    Function for filtering a trace
    """
    tr_copy = trace.copy()

    if tr_filter[0] != "No filter":
        tr_copy.detrend('linear')
        tr_copy.taper(FILTER_TAPER_VALUE)
        if tr_filter[1] == "BP":
            tr_copy.filter('bandpass', freqmin = tr_filter[2], freqmax = tr_filter[3])
        elif tr_filter[1] == "LP":
            tr_copy.filter('lowpass', freq = tr_filter[2])
        elif tr_filter[1] == "HP":
            tr_copy.filter('highpass', freq = tr_filter[3])

    return tr_copy
