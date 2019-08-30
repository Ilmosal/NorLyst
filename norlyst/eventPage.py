"""
This module contains EventPage class and all relevant objects
"""
from datetime import datetime
import numpy

from PyQt5.QtWidgets import (QWidget, QGridLayout, QTextEdit, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel, QAbstractItemView,
                             QDoubleSpinBox, QPushButton, QFrame, QFileDialog)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt5.QtCore import Qt

from pyqtgraph import PlotWidget, PlotDataItem, PlotItem, TextItem, ErrorBarItem, mkPen, setConfigOption

from obspy import UTCDateTime

from pathlib import Path

from nordb.nordic.nordicComment import NordicComment
from nordb import createNordicEvents

from config import CLASSIFICATION_COLOR_DICT, CLASSIFICATION_STRING_DICT, CLASSIFICATION_PRIORITY_DICT, MAX_PLOT_SIZE, DEFAULT_FILTERS
from eventWindows import SpectrogramWindow, ImportWindow
from misc import FilterStats, FilterWidget, filterTrace

class EventPage(QWidget):
    """
    EventPage contains functionality related to viewing information about a single day
    """
    def __init__(self, parent, database_access):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)

        filter_stats = FilterStats()

        self.waveform_plot_widget = WaveformPlotWidget(self, filter_stats)
        self.button_list = ButtonList(self)
        self.event_list = EventList(self)
        self.event_info = EventInfo(self)
        self.station_list = StationList(self)
        self.filter_widget = FilterWidget(self, filter_stats)
        self.import_buttons = ImportButtons(self, database_access)
        self.event_page_map = EventPageMap(self)

        self.layout.addWidget(self.event_list, 0, 0, 1, 1)
        self.layout.addWidget(self.event_info, 1, 0, 1, 2)
        self.layout.addWidget(self.station_list, 0, 1, 1, 2)
        self.layout.addWidget(self.button_list, 1, 2, 1, 1)
        self.layout.addWidget(self.event_page_map, 2, 0, 2, 3)
        self.layout.addWidget(self.waveform_plot_widget, 0, 3, 3, 12)
        self.layout.addWidget(self.filter_widget, 3, 3, 1, 1)
        self.layout.addWidget(self.import_buttons, 3, 14, 1, 1, Qt.AlignRight)

        self.setLayout(self.layout)

        self.spectrogram_widget = None
        self.nordic_widget = None
        self.comment_widget = None

    def filterChange(self):
        """
        Function for performing a filter change
        """
        self.station_list.plotWaveforms()

    def openSpectrogramWindow(self):
        """
        Function for opening the spectrogram window
        """
        if self.spectrogram_widget is None:
            self.spectrogram_widget = SpectrogramWindow(self.station_list)
        else:
            self.spectrogram_widget.hidden = False
            self.spectrogram_widget.setStationsFromNewEvent()

        self.spectrogram_widget.show()

    def openCommentWindow(self):
        """
        Function for opening the comment window
        """
        pass

    def openNordicWindow(self):
        """
        Function for opening the nordic window
        """
        pass

    def openExportWindow(self):
        """
        Function for opening an export window
        """
        current_event_class = self.getFocusedEventClassification()
        if current_event_class is None:
            return

        nordic_filename = current_event_class.event.waveform_h[0].waveform_info
        filename = QFileDialog.getSaveFileName(self, "Save file", nordic_filename, ".n")[0]

        if filename.strip() == "":
            return

        n_file = open(filename, 'w')
        n_file.write(str(current_event_class.getEvent()))
        n_file.close()

    def importEvent(self):
        """
        Button for importing a solution to this automatic event
        """
        pass

    def setEventClassifications(self, event_classifications, chosen_date):
        """
        Set event classifications to all child objects
        """
        self.import_buttons.checkForDailyLock(chosen_date)
        self.event_list.setEventClassifications(event_classifications)
        self.event_info.updateEventInfo()

    def getFocusedEventClassification(self):
        """
        Get the event classification that has the focus of the program. Returns None if there is no focus
        """
        focus_ec = None

        for ec in self.parent().parent().parent().event_classifications:
            if ec.focus:
                focus_ec = ec

        return focus_ec

class ButtonList(QWidget):
    """
    Class that holds multiple buttons and their functionalities
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignTop)
        self.setFixedWidth(150)

        self.spectrograms_window_btn = QPushButton('Spectrograms', self)
        self.spectrograms_window_btn.pressed.connect(self.parent().openSpectrogramWindow)
        self.comments_window_btn = QPushButton('Comments', self)
        self.comments_window_btn.pressed.connect(self.parent().openCommentWindow)
        self.nordic_window_btn = QPushButton('Nordic', self)
        self.nordic_window_btn.pressed.connect(self.parent().openNordicWindow)
        self.export_window_btn = QPushButton('Export', self)
        self.export_window_btn.pressed.connect(self.parent().openExportWindow)

        self.layout.addWidget(self.nordic_window_btn)
        self.layout.addWidget(self.spectrograms_window_btn)
        self.layout.addWidget(self.comments_window_btn)
        self.layout.addWidget(self.export_window_btn)

        self.setLayout(self.layout)

class StationList(QWidget):
    """
    List of stations that have observed the event
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.station_list_label = QLabel('Station List', self)
        self.station_list = QListWidget(self)
        self.station_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.station_list.itemClicked.connect(self.plotWaveforms)

        self.only_z_checkbox = QCheckBox('Show only z-channels', self)
        self.only_z_checkbox.stateChanged.connect(self.plotWaveforms)

        self.layout.addWidget(self.station_list_label
                             )
        self.layout.addWidget(self.station_list)
        self.layout.addWidget(self.only_z_checkbox)

        self.waveform_traces = None
        self.event = None

    def setCurrentWaveforms(self, waveform_traces, event):
        """
        Function for setting this list of stations
        """
        self.event = event
        self.waveform_traces = waveform_traces

        station_data = []
        for pick in event.data:
            if pick.station_code not in [sd[0] for sd in station_data]:
                station_data.append([pick.station_code, pick.epicenter_distance, pick.epicenter_to_station_azimuth])

        for tr in waveform_traces.values():
            if tr[0].stats['station'] not in [sd[0] for sd in station_data]:
                station_data.append([tr[0].stats['station'], None, None])

        station_data = sorted(station_data, key = lambda x: (x[1] is None, x[1]))

        self.station_list.clear()
        counter = 0

        for st in station_data:
            if st[1] is not None:
                new_item = QListWidgetItem("{0} - {1} km - {2}°".format(*st), self.station_list)
            else:
                new_item = QListWidgetItem("{0}".format(st[0]), self.station_list)

            if counter < 5:
                new_item.setSelected(True)
                counter += 1

            self.station_list.addItem(new_item)

        self.plotWaveforms()

    def getCurrentTraceAndPPickForStation(self, station_name):
        """
        Get trace for certain waveform
        """
        result = None

        if self.waveform_traces is None:
            return [result, None]

        if station_name in self.waveform_traces:
            for tr in self.waveform_traces[station_name]:
                if tr.stats['channel'].lower()[-1] == 'z':
                    result = tr
                    break

        p_pick_start_time = None
        for pick in self.event.data:
            if pick.station_code == station_name and pick.phase_type[0] == 'P':
                p_pick_start_time = pick.observation_time
                break

        return result, p_pick_start_time

    def getOrderedStationList(self):
        """
        Get stations in order
        """
        if not self.station_list:
            return []

        ordered_station_names = []

        for st in self.station_list.selectedItems():
            station_name = st.text().split('-')[0].strip()

            if station_name not in self.waveform_traces:
                continue

            if len(st.text().split('-')) > 1:
                distance = int(st.text().split('-')[1].strip()[:-3])
            else:
                distance = 99999999
            ordered_station_names.append([station_name, distance])

        ordered_station_names.sort(key = lambda x: x[1])

        return ordered_station_names

    def plotWaveforms(self):
        """
        Function for plotting selected waveforms
        """
        if not self.station_list:
            return

        plot_waves = {}

        ordered_station_names = self.getOrderedStationList()

        for station_name in [x[0] for x in ordered_station_names]:
            for tr in self.waveform_traces[station_name]:
                if self.only_z_checkbox.checkState() and tr.stats['channel'][-1].lower() == 'z':
                    if station_name not in plot_waves:
                        plot_waves[station_name] = []

                    plot_waves[station_name].append(tr)
                elif not self.only_z_checkbox.checkState():
                    if station_name not in plot_waves:
                        plot_waves[station_name] = []

                    plot_waves[station_name].append(tr)

        self.parent().waveform_plot_widget.setNewTraces(plot_waves, self.event)

class WaveformPlotWidget(QWidget):
    """
    This widget contains the functionality for a single waveform plot
    """
    def __init__(self, parent, filter_stats):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        setConfigOption('background', 1.0)

        self.filter_stats = filter_stats

        self.plot_widget = PlotWidget(self)
        self.plot_widget.getPlotItem().setLabel('bottom', 'time')

        self.s_pick_pen = mkPen(color = (222, 22, 22), width = 1.0)
        self.p_pick_pen = mkPen(color = (3, 171, 31), width = 1.0)
        self.msg_pick_pen = mkPen(color = (2, 67, 171), width = 1.0)
        self.plot_pen = mkPen(color = (0, 0, 0), width = 1.0)

        self.layout.addWidget(self.plot_widget, 0, 1, 3, 3)

    def setNewTraces(self, waveform_traces, plot_event):
        """
        Function for scaling and plotting waveform traces
        """
        self.plot_widget.getPlotItem().clear()

        offset = 0
        first_event_timestamp = None
        pick_dict = {}

        for pick in plot_event.data:
            if pick.station_code not in pick_dict:
                pick_dict[pick.station_code] = []

            pick_dict[pick.station_code].append(pick)

        for key in waveform_traces.keys():
            for tr in waveform_traces[key]:
                if first_event_timestamp is None:
                    first_event_timestamp = tr.stats['starttime']
                elif first_event_timestamp > tr.stats['starttime']:
                    first_event_timestamp = tr.stats['starttime']

        for key in waveform_traces.keys():
            for tr in waveform_traces[key]:
                tr_filter =  self.filter_stats.getCurrentFilter()
                tr_copy = filterTrace(tr_filter, tr)

                data_array = tr_copy.data
                time_array = tr_copy.times()
                time_offset = tr_copy.stats['starttime'] - first_event_timestamp

                min_value = numpy.amin(data_array)
                max_value = numpy.amax(data_array) - min_value
                data_array = ((data_array - min_value) / max_value) - offset

                time_array += time_offset

                self.plot_widget.getPlotItem().plot(time_array, data_array, pen = self.plot_pen)
                channel_text_item = TextItem("{0} - {1}".format(key, tr.stats['channel']))
                self.plot_widget.getPlotItem().addItem(channel_text_item)
                channel_text_item.setPos(-20, 0.5 - offset)
                offset += 1

            if key in pick_dict:
                for pick in pick_dict[key]:
                    if pick.phase_type[0] not in ['S', 'P', 'M']:
                        continue

                    tr_size = len(waveform_traces[key])
                    time_pos = UTCDateTime(pick.observation_time) - first_event_timestamp

                    if pick.phase_type[0] == 'S':
                        pick_pen = self.s_pick_pen
                    elif pick.phase_type[0] == 'P':
                        pick_pen = self.p_pick_pen
                    else:
                        pick_pen = self.msg_pick_pen

                    pick_bar = ErrorBarItem(
                        x = numpy.array([time_pos]),
                        y = numpy.array([float(tr_size) / 2 - offset + 1]),
                        height = tr_size,
                        pen = pick_pen
                    )

                    pick_text = TextItem(pick.phase_type, color = pick_pen.color())
                    self.plot_widget.getPlotItem().addItem(pick_bar)
                    self.plot_widget.getPlotItem().addItem(pick_text)
                    pick_text.setPos(time_pos, 1.1 + tr_size - offset)

class EventList(QListWidget):
    """
    This class contains functionality related to the Event List
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFixedWidth(150)

        self.ec_icons = {}
        self.ec_icons_finished = {}
        self.ec_icons_unimportant = {}

        for key in CLASSIFICATION_COLOR_DICT.keys():
            icon_pixmap_color = QPixmap(48, 48)
            icon_pixmap_color.fill(QColor(*CLASSIFICATION_COLOR_DICT[key]))
            icon_pixmap_border = QPixmap(48, 48)
            icon_pixmap_border.load('resources/icons/icon_borders.png')

            painter = QPainter(icon_pixmap_color)
            painter.drawPixmap(0, 0, icon_pixmap_border)
            self.ec_icons[key] = QIcon(icon_pixmap_color)
            painter.end()

        for key in CLASSIFICATION_COLOR_DICT.keys():
            icon_pixmap_color = QPixmap(48, 48)
            icon_pixmap_color.fill(QColor(*CLASSIFICATION_COLOR_DICT[key]))
            icon_pixmap_border = QPixmap(48, 48)
            icon_pixmap_border.load('resources/icons/icon_borders_finished.png')

            painter = QPainter(icon_pixmap_color)
            painter.drawPixmap(0, 0, icon_pixmap_border)
            self.ec_icons_finished[key] = QIcon(icon_pixmap_color)
            painter.end()

        for key in CLASSIFICATION_COLOR_DICT.keys():
            icon_pixmap_color = QPixmap(48, 48)
            icon_pixmap_color.fill(QColor(*CLASSIFICATION_COLOR_DICT[key]))
            icon_pixmap_border = QPixmap(48, 48)
            icon_pixmap_border.load('resources/icons/icon_borders_unimportant.png')

            painter = QPainter(icon_pixmap_color)
            painter.drawPixmap(0, 0, icon_pixmap_border)
            self.ec_icons_unimportant[key] = QIcon(icon_pixmap_color)
            painter.end()

        self.itemClicked.connect(self.focusOnEvent)

    def setEventClassifications(self, event_classifications):
        """
        Create all items to EventList
        """
        self.clear()
        for ec in event_classifications:
            list_item_string = "Event {0}"
            try:
                list_item = QListWidgetItem(list_item_string.format(ec.event_id), self)
            except Exception as e:
                list_item = QListWidgetItem(str(e), self)

            if ec.done:
                list_item.setIcon(self.ec_icons_finished[10])
            elif ec.unimportant:
                if ec.priority < 0:
                    list_item.setIcon(self.ec_icons_unimportant[ec.classification])
                elif ec.priority > 9999:
                    list_item.setIcon(self.ec_icons_unimportant[21])
                else:
                    list_item.setIcon(self.ec_icons_unimportant[20])
            elif ec.analysis_id != -1:
                if ec.priority < 0:
                    list_item.setIcon(self.ec_icons_finished[ec.classification])
                elif ec.priority > 9999:
                    list_item.setIcon(self.ec_icons_finished[21])
                else:
                    list_item.setIcon(self.ec_icons_finished[20])
            else:
                if ec.priority < 0:
                    list_item.setIcon(self.ec_icons[ec.classification])
                elif ec.priority > 9999:
                    list_item.setIcon(self.ec_icons[21])
                else:
                    list_item.setIcon(self.ec_icons[20])

            self.addItem(list_item)

            if ec.focus:
                self.setCurrentItem(list_item)

    def focusOnEvent(self):
        """
        Focus on the selected item on the item list
        """
        event_id = int(self.currentItem().text().split(' ')[1])
        self.parent().parent().parent().parent().focusOnEvent(event_id)

class ImportButtons(QWidget):
    """
    This class contains all import buttons of this program
    """
    def __init__(self, parent, database_access):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)

        self.database_access = database_access

        self.import_window_btn = QPushButton('Import Event', self)
        self.mark_day_as_done_btn = QPushButton('Day is done', self)

        self.import_window_btn.pressed.connect(self.openImportWindow)
        self.mark_day_as_done_btn.pressed.connect(self.markDayAsDone)

        self.layout.addWidget(self.import_window_btn, 0, 0)
        self.layout.addWidget(self.mark_day_as_done_btn, 0, 1)

        self.setLayout(self.layout)

        self.import_window = None

    def openImportWindow(self):
        """
        Open import window for the current event
        """
        if self.import_window is not None:
            return

        self.import_window = ImportWindow(self.database_access, self.parent().getFocusedEventClassification())
        self.import_window.show()

    def markDayAsDone(self):
        """
        mark the current day as done
        """
        pass

    def checkForDailyLock(self, current_date):
        """
        Function for locking the buttons whenever the chosen date changes
        """
        if self.database_access.isDateLockedToUser(current_date):
            self.import_window_btn.setEnabled(True)
            self.mark_day_as_done_btn.setEnabled(True)
        else:
            self.import_window_btn.setEnabled(False)
            self.mark_day_as_done_btn.setEnabled(False)

class EventInfo(QWidget):
    """
    This class contains functionality related to the event information
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFixedHeight(250)
        self.event_text = "Event ID: {0}\n"
        self.event_text += "{1}\n"
        self.event_text += "{2} ± {3}\n"
        self.event_text += "{4}, {5}\n"
        self.event_text += "±{6}, ±{7}\n"
        self.event_text += "Mag: {8} ± {9}\n\n"
        self.event_text += "Classification: {10}\n"
        self.event_text += "eqex: {11} certainty: {12}\n"
        self.event_text += "{13}"

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.event_info_text = QTextEdit("No event selected")
        self.event_info_text.setReadOnly(True)

        self.layout.addWidget(self.event_info_text, 0, 0)

        self.setLayout(self.layout)

    def updateEventInfo(self):
        """
        Update the event info box when the focused event changes.
        """
        focused_event_class = self.parent().getFocusedEventClassification()

        if focused_event_class is None:
            self.event_info_text.setText("No event selected")
            return

        focused_event = focused_event_class.getEvent()

        if focused_event.getOriginTime() is None:
            self.event_info_text.setText(self.event_text.format(
                focused_event.event_id,
                focused_event.main_h[0].origin_date,
                " ",
                "0",
                " ",
                " ",
                "0",
                "0",
                " ",
                "0",
                focused_event_class.classification,
                focused_event_class.eqex,
                focused_event_class.certainty,
                focused_event.waveform_h[0].waveform_info
            ))
        elif focused_event.main_h[0].error_h is None:
            self.event_info_text.setText(self.event_text.format(
                focused_event.event_id,
                focused_event.main_h[0].origin_date,
                focused_event.main_h[0].origin_time.strftime("%H:%M:%S.%f")[:-4],
                "0",
                focused_event.main_h[0].epicenter_latitude,
                focused_event.main_h[0].epicenter_longitude,
                "0",
                "0",
                focused_event.main_h[0].magnitude_1,
                "0",
                focused_event_class.classification,
                focused_event_class.eqex,
                focused_event_class.certainty,
                focused_event.waveform_h[0].waveform_info
            ))
        else:
            self.event_info_text.setText(self.event_text.format(
                focused_event.event_id,
                focused_event.main_h[0].origin_date,
                focused_event.main_h[0].origin_time.strftime("%H:%M:%S.%f")[:-4],
                focused_event.main_h[0].error_h.second_error,
                focused_event.main_h[0].epicenter_latitude,
                focused_event.main_h[0].epicenter_longitude,
                focused_event.main_h[0].error_h.epicenter_latitude_error,
                focused_event.main_h[0].error_h.epicenter_longitude_error,
                focused_event.main_h[0].magnitude_1,
                focused_event.main_h[0].error_h.magnitude_error,
                focused_event_class.classification,
                focused_event_class.eqex,
                focused_event_class.certainty,
                focused_event.waveform_h[0].waveform_info

            ))


class EventPageMap(QFrame):
    """
    Small map for visualizing the location of the event
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFixedWidth(400)
        self.setFixedHeight(400)
        self.setFrameStyle(1)
        self.label = QLabel('EventPageMap', self)
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

