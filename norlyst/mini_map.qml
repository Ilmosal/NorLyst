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
        id:map
        anchors.fill: parent
        plugin: mapPlugin
        center: QtPositioning.coordinate(64.45, 26.59) // Approx Helsinki
        zoomLevel: 8

        MapItemView {
            model: markerModel
            remove: Transition {
                enabled: false
            }
            delegate:MapQuickItem {
                anchorPoint: Qt.point(8, 8)
                coordinate: QtPositioning.coordinate(markerPosition.x, markerPosition.y)
                zoomLevel: 0
                sourceItem: Rectangle {
                    width: 16
                    height: 16
                    radius: 8
                    color: markerColor
                    border.width: 1
                }
            }
        }
        function updateMap(lat, lon) {
            map.center = QtPositioning.coordinate(lat, lon);
            map.zoomLevel = 8;
        }
    }
}
