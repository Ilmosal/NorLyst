"""
This module contains small helper classes and functions that are not clearly part of an other area of NorLyst
"""
import time

from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject, QMutex

from waveformlocator.waveformLocator import WaveformLocator

from config import CLASSIFICATION_PRIORITY_DICT, WAVEFORM_LOCATOR_CONFIG_FILE, WAVEFORM_OLD_BUFFER_SIZE, WAVEFORM_PREDICTIVE_BUFFER_SIZE


class EventClassification():
    """
    Class for event classifications in the database
    """
    def __init__(self, ec_id, daily_id, priority, event_id, classification, eqex, certainty, username, analysis_id, update_queue):
        self.ec_id = ec_id
        self.event_id = event_id
        self.classification = classification
        self.eqex = eqex
        self.certainty = certainty
        self.update_queue = update_queue

        self._priority = priority
        self._unimportant = True
        self._username = username
        self._analysis_id = analysis_id

        self.analyses = []
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
        if self._priority > -1:
            return self._priority
        else:
            return 0 - self.classification

    def setEvent(self, event):
        self.event = event

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

class UpdateQueue():
    """
    Class containing necessary database updates in a queue
    """
    ANALYSIS_ID_UPDATE_OPERATION = 1
    PRIORITY_UPDATE_OPERATION = 2
    USERNAME_UPDATE_OPERATION = 3
    UNIMPORTANT_UPDATE_OPERATION = 4

    def __init__(self, database_accesser):
        self.queue_buffer = []
        self.database_accesser = database_accesser
        self.timer = QTimer()
        self.timer.timeout.connect(self.processQueue)
        self.timer.start(5000)

        self.DATABASE_OPERATIONS = {
            1: self.database_accesser.analysisIdUpdate,
            2: self.database_accesser.priorityUpdate,
            3: self.database_accesser.usernameUpdate,
            4: self.database_accesser.setEventAsUnimportant
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
        for update_event in self.queue_buffer:
            operation, event_classification_id, value = update_event
            self.DATABASE_OPERATIONS[operation](event_classification_id, value)

class WaveformAccessManager(QObject):
    """
    Class for fetching waveform data and assigning them to the event classifications
    """
    def __init__(self):
        QObject.__init__(self)
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
            self.waveform_access_thread.predictive_event = predictive
            self.waveform_access_thread.event = event
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
            self.waveform_access_thread.predictive_event = predictive
            self.waveform_access_thread.event = event
            self.waveform_access_thread.start()


        print('Active event: {0}'.format(self.active_event_id))
        print('Old events: {0}\n'.format(list(self.old_waveform_cache.keys())))
        print('Predictive events: {0}\n'.format(list(self.predictive_waveform_cache.keys())))

    def insertEventToOld(self, event_id, waveform):
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
        if self.active_waveform is not None:
            self.insertEventFromActiveToOld()

        self.active_waveform = waveform
        self.active_event_id = event_id


    def insertEventFromPredictiveToActive(self, event_id):
        if self.active_waveform is not None:
            self.insertEventFromActiveToOld()

        self.active_waveform = self.predictive_waveform_cache[event_id][1]
        self.active_event_id = event_id

        del self.predictive_waveform_cache[event_id]

    def insertEventFromActiveToOld(self):
        self.insertEventToOld(self.active_event_id, self.active_waveform)
        self.active_waveform = None
        self.active_event_id = -1

    def insertEventFromOldToActive(self, event_id):
        if self.active_waveform is not None:
            self.insertEventFromActiveToOld()

        self.active_waveform = self.old_waveform_cache[event_id][1]
        self.active_event_id = event_id

        del self.old_waveform_cache[event_id]

    def getEventPredictions(self, event):
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
        self.predictive = False
        self.is_fetching = False

    def run(self):
        waveform = None
        if self.event is not None:
            waveform = self.waveform_locator.getEventWaveforms(self.event)

        self.signal.emit(waveform)
