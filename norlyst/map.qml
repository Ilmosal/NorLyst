import QtQuick 2.12
import QtQuick.Window 2.12
import QtLocation 5.12
import QtPositioning 5.12

Canvas {
    Plugin {
        id: mapPlugin
        name: "esri"
        // specify plugin parameters if necessary
    }

    Map {
        anchors.fill: parent
        plugin: mapPlugin
        center: QtPositioning.coordinate(64.45, 26.59) // Approx Helsinki
        zoomLevel: 5
        signal clicked(int event_id) 

        MapItemView {
            model: markerModel
            remove: Transition {
                enabled: false
            }
            delegate:MapQuickItem{
                anchorPoint: Qt.point(((markerHighlight) ? 12 : 8), ((markerHighlight) ? 12 : 8))
                coordinate: QtPositioning.coordinate(markerPosition.x, markerPosition.y)
                zoomLevel: 0
                sourceItem: Rectangle {
                    width: (markerHighlight) ? 24 : 16
                    height: (markerHighlight) ? 24 : 16
                    radius: (markerHighlight) ? 12 : 8
                    border.color: (markerHighlight) ? "black" : "black"
                    color: markerColor
                    border.width: (markerHighlight) ? 3 : 1
                     
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            parent.parent.parent.parent.parent.clicked(markerEventId)
                        }
                    }
                }
            }
        }
    }
}
