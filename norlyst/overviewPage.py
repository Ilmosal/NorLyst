"""
This module contains OverviewPage class and all relevant objects
"""
import os
import datetime

from PyQt5.QtWidgets import (QWidget, QFrame, QGridLayout, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QDateTimeEdit)
from PyQt5.QtCore import Qt, QUrl, QByteArray, QModelIndex, QAbstractListModel, QPointF, pyqtSlot, QPoint
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtQuick import QQuickView

from norlyst.config import CLASSIFICATION_COLOR_DICT, CLASSIFICATION_STRING_DICT, CLASSIFICATION_PRIORITY_DICT, PROJECT_FILE_PATH

class OverviewPage(QWidget):
    """
    OverviewPage contains functionality related to viewing an overview of a single day.
    """
    def __init__(self, parent, database_access):
        super(QWidget, self).__init__(parent)
        self.layout = QGridLayout(self)

        self.overview_map = OverviewMap(self)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(OverviewList(self.scroll_area))
        self.scroll_area.setFixedWidth(900)

        self.title_label = QLabel('<b>EVENT LIST</b>', self)
        self.title_label.setFixedWidth(250)

        self.daily_lock_manager = DailyLockManager(self, database_access)

        self.layout.addWidget(self.daily_lock_manager, 0, 3)
        self.layout.addWidget(self.title_label, 0, 2)
        self.layout.addWidget(self.overview_map, 0, 0, 2, 2)
        self.layout.addWidget(self.scroll_area, 1, 2, 1, 2)

        self.setLayout(self.layout)

    def setEventClassifications(self, event_classifications, chosen_date):
        """
        Function for passing the event_classifications from the norlyst main widget to the overview_map and list of this widget.
        """
        self.daily_lock_manager.setDailyLockForDate(chosen_date)
        self.overview_map.setEventClassifications(event_classifications)
        self.scroll_area.widget().setEventClassifications(event_classifications, self.daily_lock_manager.lock_status)

        if self.scroll_area.widget().getFocusedEventBox():
            self.scroll_area.ensureVisible(0, self.scroll_area.widget().getOffsetToFocusedEventClassification(), 200, 200)

"""
DAILY LOCK IMPLEMENTATION
-------------------------
"""
class DailyLockManager(QWidget):
    """
    This class contains the functionality for locking and unlocking a certain day for the user and protecting the database for simultaneous changes by concurrent users.
    """
    def __init__(self, parent, database_access):
        super(QWidget, self).__init__(parent)
        self.setFixedWidth(650)
        self.layout = QHBoxLayout(self)
        self.layout.setAlignment(Qt.AlignRight)

        self.__database_access = database_access

        self.events_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
        self.lock_status = self.__database_access.isDateLockedToUser(self.events_date)

        self.__lock_label = QLabel("<b>Automatic Event Date:</b>", self)
        self.__lock_button = QPushButton('', self)
        if self.lock_status:
            self.__lock_button.setIcon(QIcon('{0}/resources/icons/unlock.png'.format(PROJECT_FILE_PATH)))
        else:
            self.__lock_button.setIcon(QIcon('{0}/resources/icons/lock.png'.format(PROJECT_FILE_PATH)))
        self.__lock_button.setFixedSize(30, 30)
        self.__lock_button.clicked.connect(self.lockButtonPressed)

        self.__daily_lock_date = QDateTimeEdit(self.events_date)
        self.__daily_lock_date.setCalendarPopup(True)
        self.__daily_lock_date.setDisplayFormat("dd-MM-yyyy")
        self.__daily_lock_date.setFixedWidth(150)
        self.__daily_lock_date.dateTimeChanged.connect(self.setEventDateToDateTimeEditValue)

        self.layout.addWidget(self.__lock_label)
        self.layout.addWidget(self.__daily_lock_date)
        self.layout.addWidget(self.__lock_button)

    def setDailyLockForDate(self, chosen_date):
        """
        Function for setting this lock into the correct position for this date
        """
        if self.__database_access.isDateLockedToUser(chosen_date):
            self.lock_status = True
            self.__lock_button.setIcon(QIcon('{0}/resources/icons/lock.png'.format(PROJECT_FILE_PATH)))
        else:
            self.lock_status = False
            self.__lock_button.setIcon(QIcon('{0}/resources/icons/unlock.png'.format(PROJECT_FILE_PATH)))

    def setEventDateToDateTimeEditValue(self):
        """
        Function that sets a new value to event_date from the DateTimeEdit widget
        """
        self.events_date = self.__daily_lock_date.date().toPyDate()
        self.setNewEventsDate()

    def setNewEventsDate(self):
        """
        Function for setting the date for the tool and spreading the information around the program
        """
        self.parent().parent().parent().parent().setEventsForChosenDate(self.events_date)

    def lockButtonPressed(self):
        """
        Function for locking the chosen date of the daily lock manager
        """
        if self.lock_status:
            self.parent().parent().parent().parent().saveChanges()
            self.__database_access.unlockDayForUser(self.events_date)
        else:
            self.__database_access.lockDayForUser(self.events_date)

        self.parent().parent().parent().parent().setEventsForChosenDate(self.events_date)

"""
OVERVIEW MAP FUNCTIONALITY
--------------------------
"""

class OverviewMap(QQuickWidget):
    """
    This class contains functionality related to the overview Map
    """
    def __init__(self, parent):
        super(QQuickWidget, self).__init__(parent)

        self.model = MarkerModel()
        self.context = self.rootContext()
        self.context.setContextProperty('markerModel', self.model)

        self.setSource(QUrl.fromLocalFile('{0}/map.qml'.format(PROJECT_FILE_PATH)))
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.show()

        self.rootObject().childItems()[0].clicked.connect(self.mapEvent)

    def setEventClassifications(self, event_classifications):
        """
        Function for setting the event classifications for the overviewMap
        """
        self.model.clearAll()
        for ec in event_classifications:
            if ec.unimportant:
                continue

            if ec.getEvent().getLatitude().val is None:
                continue

            if ec.priority > 9999:
                ec_color = QColor(*CLASSIFICATION_COLOR_DICT[21])
            else:
                ec_color = QColor(*CLASSIFICATION_COLOR_DICT[ec.classification])

            self.model.addMarker(MapMarker(
                ec.event_id,
                QPointF(ec.getEvent().getLatitude().val, ec.getEvent().getLongitude().val),
                ec_color,
                ec.focus
            ))

    @pyqtSlot(int)
    def mapEvent(self, event_id):
        """
        Function for focusing on a single event from clicking of a symbol on the map
        """
        self.parent().parent().parent().parent().focusOnEvent(event_id)

class MapMarker(object):
    """
    This class contains the information of a single marker on the map
    """
    def __init__(self, event_id, position, color, highlight):
        self._position = position
        self._color = color
        self._event_id = event_id
        self._highlight = highlight

    def position(self):
        return self._position

    def setPosition(self, position):
        self._position = position

    def color(self):
        return self._color

    def setColor(self, color):
        self._color = color

    def eventId(self):
        return self._event_id

    def setEventId(self, event_id):
        self._event_id = event_id

    def highlight(self):
        return self._highlight

    def setHighlight(self, highlight):
        self._highlight = highlight

class MarkerModel(QAbstractListModel):
    position_role = Qt.UserRole + 1
    color_role = Qt.UserRole + 2
    event_id_role = Qt.UserRole + 3
    highlight_role = Qt.UserRole + 4

    _roles = {
        position_role: QByteArray(b'markerPosition'),
        color_role: QByteArray(b'markerColor'),
        event_id_role: QByteArray(b'markerEventId'),
        highlight_role: QByteArray(b'markerHighlight'),
    }

    def __init__(self, parent = None):
        QAbstractListModel.__init__(self, parent)
        self._markers = []

    def rowCount(self, index = QModelIndex()):
        return len(self._markers)

    def roleNames(self):
        return self._roles

    def data(self, index, role=Qt.DisplayRole):
        if index.row() >= self.rowCount():
            return QVariant()

        marker = self._markers[index.row()]

        if role == MarkerModel.position_role:
            return marker.position()
        elif role == MarkerModel.color_role:
            return marker.color()
        elif role == MarkerModel.event_id_role:
            return marker.eventId()
        elif role == MarkerModel.highlight_role:
            return marker.highlight()

        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid():
            marker = self._markers[index.row()]

            if role == MarkerModel.position_role:
                return marker.setPosition(value)
            elif role == MarkerModel.color_role:
                return marker.setColor(value)
            elif role == MarkerModel.event_id_role:
                return marker.setEventId(value)
            elif role == MarkerModel.highlight_role:
                return marker.setHighlight(value)

            self.dataChanged.emit(index, index)

        return QAbstractListModel.setData(self, index, value, role)

    def removeRows(self, row, count, index):
        if (count == 0 or not self._markers):
            return True

        self.beginRemoveRows(index, row, row + count - 1)

        for i in reversed(range(row, row + count)):
            self._markers.pop(i)

        self.endRemoveRows()

        return True

    def addMarker(self, marker):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._markers.append(marker)
        self.endInsertRows()

    def clearAll(self):
        self.beginResetModel()
        self._markers.clear()
        self.endResetModel()

        return True

"""
OVERVIEW LIST FUNCTIONALITY
---------------------------
"""

class OverviewList(QWidget):
    """
    This class contains functionality related to the overview list
    """
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(8)

        self.classification_boxes = []
        for i in [1,2,3,4,5,6,7,10,20,21]:
            self.classification_boxes.append(ClassificationBox(self, i))

        self.event_boxes = []
        self.event_boxes.extend(self.classification_boxes)
        self.__priority_counter = 0

        self.setLayout(self.layout)

    def getFocusedEventBox(self):
        """
        This function returns the focused EventBox object and None if None are focused
        """
        for e_box in self.event_boxes:
            if e_box.getFocus():
                return e_box
        return None

    def getNewPriorityNumber(self):
        """
        This function advances the priority counter with 1 and returns the new value for the event box
        """
        self.__priority_counter += 1
        return self.__priority_counter

    def setEventClassifications(self, event_classifications, lock_status):
        """
        Function for setting the event classifications for the overviewList
        """
        self.event_boxes = []
        self.event_boxes.extend(self.classification_boxes)

        self.__priority_counter = 0

        for e_class in event_classifications:
            if e_class.unimportant:
                continue

            self.event_boxes.append(EventBox(self, e_class, lock_status))
            if e_class.priority != -1:
                if e_class.priority > 9999 and e_class.priority - 10000 > self.__priority_counter:
                    self.__priority_counter = e_class.priority - 10000
                elif e_class.priority > -1 and e_class.priority > self.__priority_counter:
                    self.__priority_counter = e_class.priority

        self.orderEventBoxes()

    def orderEventBoxes(self):
        """
        Function for ordering EventBoxes
        """
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

        self.event_boxes.sort(key = lambda x: x.getPriority(), reverse=True)

        for e_box in self.event_boxes:
            self.layout.addWidget(e_box)

    def getOffsetToFocusedEventClassification(self):
        """
        Function for getting the offset to the focused Event Classification
        """
        offset = 0

        for ec in self.event_boxes:
            offset += ec.height() + 8
            if ec.getFocus():
                break

        return offset

class ClassificationBox(QFrame):
    """
    This class is the divider box for different event_classifications
    """
    def __init__(self, parent, classification_type):
        super(QFrame, self).__init__(parent)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet('background-color: rgb({0}, {1}, {2})'.format(*CLASSIFICATION_COLOR_DICT[classification_type]))
        self.setFixedWidth(400)
        self.setFixedHeight(40)

        self.priority = CLASSIFICATION_PRIORITY_DICT[classification_type]

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        self.layout.addWidget(QLabel("<b>" + CLASSIFICATION_STRING_DICT[classification_type]+"<b>", self))

        self.setLayout(self.layout)

    def getPriority(self):
        return self.priority

    def getFocus(self):
        return False

    def getEventId(self):
        return -1

    def getHeight(self):
        return 40

class EventBox(QFrame):
    """
    This class contains a single event description for a single day. These objects will be listed in the OverviewList widget.
    """
    def __init__(self, parent, event_classification, lock_status):
        super(QFrame, self).__init__(parent)
        self.setFixedWidth(850)
        self.setFrameStyle(QFrame.Box)
        if event_classification.focus:
            self.setLineWidth(3)

        self.setStyleSheet('background-color: white')

        self.layout = QGridLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.__text_layout = QVBoxLayout()
        self.__text_layout.setSpacing(5)
        self.__text_layout.setContentsMargins(5, 5, 5, 5)
        self.__button_layout = QHBoxLayout()
        self.__button_layout.setSpacing(4)
        self.__button_layout.setContentsMargins(5, 5, 5, 5)

        self.__event_classification = event_classification
        event = self.__event_classification.getEvent()

        self.__id_label = QLabel('ID: {0} - {1}'.format(event.event_id, event.waveform_h[0].getWaveformFileName()))
        self.__id_label.setContentsMargins(5, 5, 5, 5)
        self.__id_label.setStyleSheet('background-color: rgb({0}, {1}, {2}); border-bottom: 1px solid black'.format(*CLASSIFICATION_COLOR_DICT[event_classification.classification]))

        if event.getOriginTime() is None:
            origin_time = "-"
        else:
            origin_time = event.getOriginTime().val.strftime("%H:%M:%S")

        self.__event_values_text = QLabel('Time: {0}    Latitude: {1}    Longitude: {2}    Magnitude: {3}'.format(
            origin_time,
            event.getLatitude().val,
            event.getLongitude().val,
            event.getMagnitude().val,)
            , self)
        self.__event_values_text.setFixedHeight(20)

        category_string = "Event Classification: {0}    ".format(self.__event_classification.classification)
        if self.__event_classification.eqex is not None:
            category_string += 'EQ/EX: {0}    '.format(self.__event_classification.eqex)
        if self.__event_classification.certainty is not None:
            category_string += 'Certainty: {0}'.format(self.__event_classification.certainty)

        self.__event_categorization_text = QLabel(category_string, self)
        self.__event_categorization_text.setFixedHeight(20)

        self.__remove_priority_button = QPushButton('', self)
        self.__remove_priority_button.setIcon(QIcon('{0}/resources/icons/remove.png'.format(PROJECT_FILE_PATH)))
        self.__remove_priority_button.setFixedSize(25, 25)
        self.__remove_priority_button.clicked.connect(self.removePriority)

        if (self.__event_classification.priority < 0 or self.__event_classification.priority > 9999):
            self.__remove_priority_button.hide()

        self.__push_to_top_button = QPushButton('', self)
        self.__push_to_top_button.setIcon(QIcon('{0}/resources/icons/push_to_top.png'.format(PROJECT_FILE_PATH)))
        self.__push_to_top_button.setFixedSize(25, 25)
        self.__push_to_top_button.clicked.connect(self.pushToTopPressed)

        self.__set_as_important_button = QPushButton('', self)
        if self.__event_classification.priority > 9999:
            self.__set_as_important_button.setIcon(QIcon('{0}/resources/icons/set_as_unimportant.png'.format(PROJECT_FILE_PATH)))
        else:
            self.__set_as_important_button.setIcon(QIcon('{0}/resources/icons/set_as_important.png'.format(PROJECT_FILE_PATH)))
        self.__set_as_important_button.setFixedSize(25, 25)
        self.__set_as_important_button.clicked.connect(self.setAsImportantPressed)

        self.__text_layout.addWidget(self.__event_values_text)
        self.__text_layout.addWidget(self.__event_categorization_text)

        self.__button_layout.addWidget(self.__remove_priority_button, 0, Qt.AlignTop)
        self.__button_layout.addWidget(self.__push_to_top_button, 0, Qt.AlignTop)
        self.__button_layout.addWidget(self.__set_as_important_button, 0, Qt.AlignTop)

        self.layout.addWidget(self.__id_label, 0, 0, 1, 2)
        self.layout.addLayout(self.__text_layout, 1, 0)
        self.layout.addLayout(self.__button_layout, 1, 1)

        if lock_status:
            self.unlockEventBox()
        else:
            self.lockEventBox()

    def getHeight(self):
        """
        Function for getting the height of this object
        """
        return 60

    def getEventId(self):
        """
        Function for getting event classification event_id
        """
        return self.__event_classification.event_id

    def getFocus(self):
        """
        Get event focus status
        """
        return self.__event_classification.focus

    def getPriority(self):
        """
        Function for getting the priority of this event box
        """
        if self.__event_classification.done:
            return -10
        elif self.__event_classification.priority == -1:
            return 0 - self.__event_classification.classification
        else:
            return self.__event_classification.priority

    def removePriority(self):
        """
        Function for removing the priority number of this event
        """
        self.__event_classification.priority = -1
        self.parent().parent().parent().parent().parent().parent().parent().setEventClassifications()
        self.__remove_priority_button.setVisible(False)
        self.repaint()

    def setAsImportantPressed(self):
        """
        Function for setting a single event box as important.
        """
        if self.__event_classification.priority > 9999:
            self.__set_as_important_button.setIcon(QIcon('{0}/resources/icons/set_as_important.png'.format(PROJECT_FILE_PATH)))
            self.__event_classification.priority -= 10001
            self.__push_to_top_button.setEnabled(True)
            self.__event_classification.focus = False
            self.parent().parent().parent().parent().parent().parent().parent().setEventClassifications()
        else:
            self.__event_classification.priority += 10001
            self.__set_as_important_button.setIcon(QIcon('{0}/resources/icons/set_as_unimportant.png'.format(PROJECT_FILE_PATH)))
            self.__push_to_top_button.setEnabled(False)
            self.highlightEvent()

    def pushToTopPressed(self):
        """
        Function for pushing a event to the top of the priority list
        """
        self.__event_classification.priority = self.parent().getNewPriorityNumber()

        self.parent().parent().parent().parent().parent().parent().parent().setEventClassifications()
        self.__remove_priority_button.setVisible(True)
        self.__remove_priority_button.repaint()

    def unlockEventBox(self):
        """
        Function for unlocking an event box for interaction
        """
        self.__set_as_important_button.setEnabled(True)
        self.__push_to_top_button.setEnabled(True)
        self.__remove_priority_button.setEnabled(True)


    def lockEventBox(self):
        """
        Function for locking an event box from interaction
        """
        self.__set_as_important_button.setEnabled(False)
        self.__push_to_top_button.setEnabled(False)
        self.__remove_priority_button.setEnabled(False)

    def highlightEvent(self):
        """
        Function for highlighting this event classification
        """
        self.parent().parent().parent().parent().parent().parent().parent().focusOnEvent(self.__event_classification.event_id)

    def mousePressEvent(self, event):
        """
        Highlight the event classification when clicking an event classification box
        """
        self.highlightEvent()
