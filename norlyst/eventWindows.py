"""
This module contains all new windows that are openable from eventPage
"""
import time
from copy import deepcopy

from scipy import signal

import numpy

from matplotlib import cm as colormap

from PyQt5.QtWidgets import QWidget, QGridLayout, QComboBox, QLabel, QPushButton, QLineEdit, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal

from pyqtgraph import PlotWidget, ImageItem

from obspy import UTCDateTime

from nordb import createNordicEvents
from nordb.nordic.nordicComment import NordicComment

from misc import FilterWidget, FilterStats, filterTrace

from config import *

"""
Import window functionality
---------------------------
"""

class ImportWindow(QWidget):
    """
    This is the class for the import event window
    """
    def __init__(self, database_accesser, ec):
        super(QWidget, self).__init__()
        self.layout = QGridLayout(self)
        self.database_accesser = database_accesser
        self.event_classification = ec

        self.analysis_label = QLabel('Type', self)
        self.analysis_label.setFixedWidth(50)
        self.analysis_type = QComboBox(self)
        self.analysis_type.setFixedWidth(150)
        self.analysis_type.addItem('AR LE')
        self.analysis_type.addItem('AR LP')
        self.analysis_type.addItem('RE LE')
        self.analysis_type.addItem('RE LP')
        self.analysis_type.addItem('From file')
        self.analysis_type.addItem('Not an event')
        self.analysis_type.activated.connect(self.changeAnalysisType)

        self.file_dialog_label = QLabel('Select a file', self)
        self.file_dialog_label.setStyleSheet('background-color: rgb(255, 255, 255); border: 1px solid gray')
        self.file_dialog_label.setVisible(False)
        self.file_dialog_btn = QPushButton('Browse', self)
        self.file_dialog_btn.pressed.connect(self.openFileDialog)
        self.file_dialog_btn.setVisible(False)

        self.comments_label = QLabel('Additional Comments', self)
        self.comment_1 = QLineEdit(self)
        self.comment_1.setMaxLength(78)
        self.comment_1.setFixedWidth(450)
        self.comment_2 = QLineEdit(self)
        self.comment_2.setMaxLength(78)
        self.comment_2.setFixedWidth(450)

        self.submit_btn = QPushButton('Submit', self)
        self.submit_btn.pressed.connect(self.submitEvent)

        self.layout.addWidget(self.analysis_label, 0, 0)
        self.layout.addWidget(self.analysis_type, 0, 1)
        self.layout.addWidget(self.file_dialog_label, 0, 2)
        self.layout.addWidget(self.file_dialog_btn, 0, 3)
        self.layout.addWidget(self.comments_label, 1, 0, 1, 2)
        self.layout.addWidget(self.comment_1, 2, 0, 1, 3)
        self.layout.addWidget(self.comment_2, 3, 0, 1, 3)
        self.layout.addWidget(self.submit_btn, 3, 3)

        self.event = None

        self.setLayout(self.layout)

    def changeAnalysisType(self):
        """
        Function which will be called when the analysis_type QComboBox is activated for hiding file_dialog elements
        """
        if self.analysis_type.currentText() == 'From file':
            self.file_dialog_label.setVisible(True)
            self.file_dialog_btn.setVisible(True)
        else:
            self.file_dialog_label.setVisible(False)
            self.file_dialog_btn.setVisible(False)

    def openFileDialog(self):
        """
        Open file dialog for picking a nordic file
        """
        filename = QFileDialog.getOpenFileName(self, 'Open a Nordic File')[0]

        try:
            nordic_event = createNordicEvents(open(filename, 'r'))[0][0]
        except Exception as e:
            print(e)
            return

        self.file_dialog_label.setText(filename.split('/')[-1])

        self.event = nordic_event

    def submitEvent(self):
        """
        Submit this event
        """

        comments = []

        if self.comment_1.text().strip() != "":
            comments.append(
                NordicComment([self.comment_1.text().strip().upper(), -1, -1])
            )

        if self.comment_2.text().strip() != "":
            comments.append(
                NordicComment([self.comment_2.text().strip().upper(), -1, -1])
            )

        if self.analysis_type.currentText() == "AR LE":
            self.categorizeThisEvent("LE", False, comments)

        elif self.analysis_type.currentText() == "AR LP":
            self.categorizeThisEvent("LP", False, comments)

        elif self.analysis_type.currentText() == "RE LE":
            self.categorizeThisEvent("LE", True, comments)

        elif self.analysis_type.currentText() == "RE LP":
            self.categorizeThisEvent("LP", True, comments)

        elif self.analysis_type.currentText() == "From file":
            if self.event is None:
                return

            self.event.insert2DB(solution_type = 'REV', e_id = self.event_classification.event.event_id)
            self.event_classification.analysis_id = self.event.event_id
            self.event_classification.analysis = self.event
            self.event_classification.done = True

        elif self.analysis_type.currentText() == "Not an event":
            self.event_classification.unimportant = True
            self.event_classification.done = True

    def categorizeThisEvent(self, cat_type, reviewed, comments):
        """
        Function for categorizing an event, storing it to the database and making necessary modifications to the event_classification 
        """
        current_event = deepcopy(self.event_classification.getEvent())

        current_event.main_h[0].distance_indicator = 'L'

        if cat_type == 'LE':
            current_event.main_h[0].event_desc_id = 'E'
        elif cat_type == 'LP':
            current_event.main_h[0].event_desc_id = 'P'
        else:
            return

        if reviewed:
            for comment in current_event.comment_h:
                if comment.h_comment.strip() == "FULLY AUTOMATIC LOCATION":
                    comment.h_comment = "FULLY AUTOMATIC, EVENT TYPE & LOCATION & MAGNITUDE CHECKED ({0})".format(self.database_accesser.getCurrentUser()[:3].upper())

            current_event.comment_h.extend(comments)

        else:
            current_event.comment_h.clear()

            for main in current_event.main_h:
                main.error_h = None

            current_event.main_h[0].origin_time = None
            current_event.main_h[0].epicenter_latitude = None
            current_event.main_h[0].epicenter_longitude = None
            current_event.main_h[0].magnitude_1 = None
            current_event.main_h[0].type_of_magnitude_1 = None
            current_event.main_h[0].magnitude_reporting_agency_1 = None
            current_event.main_h[0].magnitude_2 = None
            current_event.main_h[0].type_of_magnitude_2 = None
            current_event.main_h[0].magnitude_reporting_agency_2 = None
            current_event.main_h[0].magnitude_3 = None
            current_event.main_h[0].type_of_magnitude_3 = None
            current_event.main_h[0].magnitude_reporting_agency_3 = None
            current_event.main_h[0].epicenter_depth = 0.0
            current_event.main_h[0].stations_used = None
            current_event.main_h[0].rms_time_residuals = None

            current_event.comment_h.append(
                NordicComment(
                    ["FULLY AUTOMATIC READINGS, EVENT TYPE CHECKED ({0})".format(self.database_accesser.getCurrentUser()[:3].upper()),
                     -1,
                     -1]
                )
            )
            current_event.comment_h.extend(comments)

            indices_to_remove = []

            for pick_id in range(len(current_event.data)):
                if current_event.data[pick_id].phase_type == 'MSG':
                    indices_to_remove.append(pick_id)
                else:
                    current_event.data[pick_id].signal_duration = None
                    current_event.data[pick_id].max_amplitude = None
                    current_event.data[pick_id].max_amplitude_period = None
                    current_event.data[pick_id].back_azimuth = None
                    current_event.data[pick_id].apparent_velocity = None
                    current_event.data[pick_id].signal_to_noise = None
                    current_event.data[pick_id].azimuth_residual = None
                    current_event.data[pick_id].travel_time_residual = None
                    current_event.data[pick_id].location_weight = None
                    current_event.data[pick_id].epicenter_distance = None
                    current_event.data[pick_id].epicenter_to_station_azimuth = None

            indices_to_remove.sort(reverse = True)

            for i in indices_to_remove:
                del current_event.data[i]

        current_event.insert2DB(solution_type = 'REV', e_id = current_event.event_id)
        self.event_classification.analysis_id = current_event.event_id
        self.event_classification.analysis = current_event
        self.event_classification.done = True


class CommentBars(QWidget):
    """
    This class handles the comment managment in the import window
    """
    def __init__(self):
        super(QWidget, self).__init__()
        self.layout = QGridLayout(self)

        self.comment_texts = []

    def addCommentBar(self):
        """
        Function for adding a new comment bar to this widget
        """

    def removeCommentBar(self):
        """
        Function for removing a single comment bar from CommentBars widget
        """

"""
Spectrogram window functionality
--------------------------------
"""

class SpectrogramWindow(QWidget):
    """
    This is the class for the spectrogram window
    """
    def __init__(self, station_list):
        super(QWidget, self).__init__()
        self.layout = QGridLayout(self)
        self.station_list = station_list
        self.hidden = False

        self.spectrogram_1 = PlotWidget(self)
        self.spectrogram_1.setFixedWidth(400)
        self.spectrogram_1.setFixedHeight(550)
        self.spectrogram_2 = PlotWidget(self)
        self.spectrogram_2.setFixedWidth(400)

        self.station_box_1 = QComboBox(self)
        self.station_box_2 = QComboBox(self)

        self.waiting_traces = [None, None]
        self.waiting_p_picks = [None, None]
        self.filter_stats = FilterStats(True)

        self.spectrogram_threads = [None, None]
        self.spectrogram_threads[0] = SpectrogramCalculatorThread(self.filter_stats, 0)
        self.spectrogram_threads[0].signal.connect(self.plotSpectrogram)
        self.spectrogram_threads[1] = SpectrogramCalculatorThread(self.filter_stats, 1)
        self.spectrogram_threads[1].signal.connect(self.plotSpectrogram)

        self.filter_widget = FilterWidget(self, self.filter_stats)

        self.layout.addWidget(self.spectrogram_1, 0, 0, 1, 2)
        self.layout.addWidget(self.spectrogram_2, 0, 2, 1, 2)
        self.layout.addWidget(self.station_box_1, 1, 0)
        self.layout.addWidget(self.station_box_2, 1, 2)
        self.layout.addWidget(self.filter_widget, 2, 0)

        self.station_box_1.activated.connect(self.replotSpectrogram1)
        self.station_box_2.activated.connect(self.replotSpectrogram2)
        self.setStationsFromNewEvent()

    def closeEvent(self, event):
        """
        This function will be called when the spectrogramWindow Closes
        """
        self.hidden = True

    def replotSpectrogram1(self):
        """
        This function is to be used only by station_box_1
        """
        self.getTraceForSpectrogramThread(0)

    def replotSpectrogram2(self):
        """
        This function is to be used only by station_box_2
        """
        self.getTraceForSpectrogramThread(1)

    def getTraceForSpectrogramThread(self, spectrogram_id):
        """
        Fetch correct trace for the spectrogram_thread. Choose this from the value from station_box_1 or station_box_2
        """
        station_name = None
        if spectrogram_id == 0:
            station_name = self.station_box_1.currentText()
        elif spectrogram_id == 1:
            station_name = self.station_box_2.currentText()

        trace, p_pick = self.station_list.getCurrentTraceAndPPickForStation(station_name)

        if trace is None:
            return

        self.calculateSpectrogram(trace, p_pick, spectrogram_id)

    def setStationsFromNewEvent(self):
        """
        Set the focused event to spectrogram window
        """
        stations = [x[0] for x in self.station_list.getOrderedStationList()]

        if len(stations) < 2:
            return

        self.station_box_1.clear()
        self.station_box_2.clear()

        for stat in stations:
            self.station_box_1.addItem(stat)
            self.station_box_2.addItem(stat)

        self.station_box_1.setCurrentIndex(0)
        self.station_box_2.setCurrentIndex(1)

        self.getTraceForSpectrogramThread(0)
        self.getTraceForSpectrogramThread(1)

    def filterChange(self):
        """
        Function that is called when the filters have been changed
        """
        self.getTraceForSpectrogramThread(0)
        self.getTraceForSpectrogramThread(1)

    def calculateSpectrogram(self, waveform_trace, p_pick, spectrogram_id):
        """
        Function for calculating a spectrogram
        """
        if self.spectrogram_threads[spectrogram_id].running:
            self.waiting_traces[spectrogram_id] = waveform_trace
            self.waiting_p_picks[spectrogram_id] = p_pick
            self.spectrogram_threads[spectrogram_id].interrupt = True
        else:
            self.spectrogram_threads[spectrogram_id].waveform_trace = waveform_trace
            self.spectrogram_threads[spectrogram_id].p_pick = p_pick
            self.spectrogram_threads[spectrogram_id].running = True
            self.spectrogram_threads[spectrogram_id].start()

    def plotSpectrogram(self, return_values):
        """
        Function for plotting a spectrogram
        """
        spectrogram_id, spectrogram, sample_frequencies, sample_times = return_values
        self.spectrogram_threads[spectrogram_id].running = False
        self.spectrogram_threads[spectrogram_id].interrupt = False

        if self.waiting_traces[spectrogram_id] is not None:
            self.calculateSpectrogram(self.waiting_traces[spectrogram_id], self.waiting_p_picks[spectrogram_id], spectrogram_id)
            self.waiting_traces[spectrogram_id] = None
            self.waiting_p_picks[spectrogram_id] = None

        if spectrogram is None:
            return

        if spectrogram_id == 0:
            self.spectrogram_1.clear()
            self.spectrogram_1.addItem(spectrogram)
        elif spectrogram_id == 1:
            self.spectrogram_2.clear()
            self.spectrogram_2.addItem(spectrogram)

class SpectrogramCalculatorThread(QThread):
    """
    This object calculates spectrograms in a background thread and returns them to the spectrogram widget.
    """
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self, filter_stats, spectrogram_id):
        QThread.__init__(self)

        self.waveform_trace = None
        self.p_pick = None
        self.interrupt = False
        self.running = False
        self.filter_stats = filter_stats
        self.spectrogram_id = spectrogram_id

    def run(self):
        """
        Calculate spectrogram from trace
        """
        if self.p_pick is None:
            self.signal.emit([self.spectrogram_id, None, None, None])
            return
        start_time = self.p_pick - SPECTRO_WINDOW_OFFSET
        end_time = start_time + SPECTRO_WINDOW_SIZE

        filtered_trace = filterTrace(self.filter_stats.getCurrentFilter(), self.waveform_trace)
        filtered_trace.trim(UTCDateTime(start_time), UTCDateTime(end_time))

        if self.interrupt:
            self.signal.emit([self.spectrogram_id, None, None, None])
            return

        segment_length = int(len(filtered_trace.data) * SPECTRO_SEGMENT_LENGTH)
        segment_overlap = int(segment_length * SPECTRO_SEGMENT_OVERLAP)
        window = signal.hamming(segment_length)
        sample_frequencies, segment_times, spectrogram = signal.spectrogram(
            filtered_trace.data,
            filtered_trace.stats.sampling_rate,
            window = window,
            noverlap = segment_overlap
        )

        if self.interrupt:
            self.signal.emit([self.spectrogram_id, None, None, None])
            return

        log_spectrogram = numpy.log10(spectrogram.T)
        max_val = numpy.max(log_spectrogram)
        min_val = numpy.min(log_spectrogram)
        value_delta = max_val - min_val
        color_map = colormap.get_cmap('hsv')

        result = ImageItem(numpy.array([[color_map((x - min_val) / value_delta) for x in y] for y in log_spectrogram]))

        if self.interrupt:
            self.signal.emit([self.spectrogram_id, None, None, None])
            return

        self.signal.emit([self.spectrogram_id, result, sample_frequencies, segment_times])

