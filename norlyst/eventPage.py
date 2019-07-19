"""
This module contains EventPage class and all relevant objects
"""
from PyQt5.QtWidgets import (QWidget, QGridLayout, QTextEdit, QListWidget, QListWidgetItem)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QFont

from config import CLASSIFICATION_COLOR_DICT, CLASSIFICATION_STRING_DICT, CLASSIFICATION_PRIORITY_DICT

class EventPage(QWidget):
    """
    EventPage contains functionality related to viewing information about a single day
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)
        self.waveform_plotter = WaveformPlotter(self)
        self.spectrogram_plotter = SpectrogramPlotter(self)
        self.event_list = EventList(self)
        self.event_info = EventInfo(self)

        self.layout.addWidget(self.event_list, 0, 0, 3, 1)
        self.layout.addWidget(self.waveform_plotter, 0, 1, 2, 2)
        self.layout.addWidget(self.spectrogram_plotter, 0, 4, 1, 1)
        self.layout.addWidget(self.event_info, 1, 4, 1, 1)

        self.setLayout(self.layout)

    def setEventClassifications(self, event_classifications):
        """
        Set event classifications to all child objects
        """
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

class WaveformPlotter(QWidget):
    """
    This class contains functionality related to Waveform plots
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFixedWidth(900)

        self.layout = QGridLayout(self)

        self.layout.addWidget(QTextEdit('Waveform Plotter', self), 0, 0)

        self.setLayout(self.layout)

class SpectrogramPlotter(QWidget):
    """
    This class contains functionality related to the Spectrogram plots
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)

        self.layout.addWidget(QTextEdit('Spectrogram Plot', self), 0, 0)

        self.setLayout(self.layout)

class EventList(QListWidget):
    """
    This class contains functionality related to the Event List
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFixedWidth(400)
        self.ec_icons = {}

        for key in CLASSIFICATION_COLOR_DICT.keys():
            icon_pixmap_color = QPixmap(48, 48)
            icon_pixmap_color.fill(QColor(*CLASSIFICATION_COLOR_DICT[key]))
            icon_pixmap_border = QPixmap(48, 48)
            icon_pixmap_border.load('resources/icons/icon_borders.png')

            painter = QPainter(icon_pixmap_color)
            painter.drawPixmap(0, 0, icon_pixmap_border)
            self.ec_icons[key] = QIcon(icon_pixmap_color)
            painter.end()

        self.itemClicked.connect(self.focusOnEvent)

    def setEventClassifications(self, event_classifications):
        """
        Create all items to EventList
        """
        self.clear()
        for ec in event_classifications:
            list_item_string = "Event {0} - {1} - {2:2.3f}, {3:2.3f} - {4}"
            try:
                list_item = QListWidgetItem(list_item_string.format(*ec.listItemStringArray()), self)
            except Exception as e:
                list_item = QListWidgetItem(str(e), self)

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

class EventInfo(QWidget):
    """
    This class contains functionality related to the event information
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)

        self.event_info_text = QTextEdit('', self)
        monospace = QFont('Monospace', 7)
        monospace.setStyleHint(QFont.TypeWriter)
        self.event_info_text.setFont(monospace)

        self.layout.addWidget(self.event_info_text, 0, 0)

        self.setLayout(self.layout)

    def updateEventInfo(self):
        """
        Update the event info box when the focused event changes.
        """
        focused_event_class = self.parent().getFocusedEventClassification()

        if focused_event_class is None:
            self.event_info_text.setText("")
            return

        self.event_info_text.setText(str(focused_event_class.event))

