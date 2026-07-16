import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: keypad

    property var keys: []
    property var pressedKeys: []
    property int selectedKey: -1
    property int columns: 3
    property bool interactive: true
    property bool simulateOnClick: false
    property color accent: "#20BFA9"
    property color ink: "#E7EDF1"
    property color muted: "#9AA8B4"
    property color bodyColor: "#64717B"
    property color panelColor: "#172129"

    signal keySelected(int keyIndex)
    signal keyActivated(int keyIndex)

    implicitWidth: 310
    implicitHeight: 308
    Layout.minimumWidth: 170
    Layout.minimumHeight: 168

    Item {
        id: deviceBody
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height * 1.07)
        height: width / 1.07

        Rectangle {
            id: sideProfile
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: topShell.bottom
            width: topShell.width * 0.88
            height: Math.max(14, parent.height * 0.16)
            color: Qt.darker(keypad.bodyColor, 1.32)
            radius: Math.max(3, height * 0.22)
            border.color: Qt.darker(keypad.bodyColor, 1.55)
        }

        Rectangle {
            id: topShell
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: parent.height * 0.88
            radius: Math.max(8, width * 0.075)
            color: keypad.bodyColor
            border.width: 1
            border.color: Qt.darker(keypad.bodyColor, 1.45)

            Rectangle {
                anchors.fill: parent
                anchors.margins: Math.max(9, parent.width * 0.065)
                color: Qt.lighter(keypad.bodyColor, 1.08)
                radius: Math.max(6, width * 0.055)
                border.width: 1
                border.color: Qt.lighter(keypad.bodyColor, 1.18)
            }

            Grid {
                id: keyGrid
                anchors.centerIn: parent
                width: parent.width * 0.78
                height: parent.height * 0.72
                columns: Math.max(1, keypad.columns)
                rows: Math.ceil(keypad.keys.length / Math.max(1, keypad.columns))
                spacing: Math.max(5, width * 0.032)

                Repeater {
                    model: keypad.keys
                    delegate: Button {
                        id: physicalKey
                        required property var modelData
                        readonly property bool isPressed: keypad.pressedKeys.indexOf(modelData.index) !== -1
                        readonly property bool isSelected: keypad.selectedKey === modelData.index
                        readonly property real pressDepth: Math.max(2, height * 0.07)
                        width: (keyGrid.width - keyGrid.spacing * (keyGrid.columns - 1)) / keyGrid.columns
                        height: (keyGrid.height - keyGrid.spacing * (keyGrid.rows - 1)) / keyGrid.rows
                        enabled: keypad.interactive
                        hoverEnabled: keypad.interactive
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: "Physical key " + (modelData.index + 1) + ", " + modelData.label
                        Accessible.description: modelData.physicalLabel
                        ToolTip.visible: hovered
                        ToolTip.text: modelData.physicalLabel + "\n" + modelData.label

                        onClicked: {
                            keypad.keySelected(modelData.index)
                            if (keypad.simulateOnClick)
                                keypad.keyActivated(modelData.index)
                        }

                        background: Item {
                            Rectangle {
                                x: 0
                                y: physicalKey.pressDepth
                                width: parent.width
                                height: parent.height - physicalKey.pressDepth
                                radius: Math.max(4, parent.width * 0.11)
                                color: Qt.darker(keypad.panelColor, 1.4)
                            }
                            Rectangle {
                                id: keyCap
                                x: 0
                                y: physicalKey.isPressed ? physicalKey.pressDepth : 0
                                width: parent.width
                                height: parent.height - physicalKey.pressDepth
                                radius: Math.max(4, parent.width * 0.11)
                                color: physicalKey.isPressed ? Qt.darker(keypad.panelColor, 1.18) : keypad.panelColor
                                border.width: 1
                                border.color: physicalKey.isSelected ? keypad.accent : Qt.lighter(keypad.panelColor, 1.55)
                                Behavior on y { NumberAnimation { duration: 65; easing.type: Easing.OutCubic } }
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: 3
                                    radius: Math.max(3, parent.radius - 2)
                                    visible: !physicalKey.isPressed
                                    color: "transparent"
                                    border.width: physicalKey.isSelected ? 1 : 0
                                    border.color: Qt.lighter(keypad.panelColor, 1.28)
                                }
                            }
                        }

                        contentItem: Item {
                            Column {
                                id: keyLegend
                                x: Math.max(4, parent.width * 0.09)
                                y: Math.max(4, parent.width * 0.09) + (physicalKey.isPressed ? physicalKey.pressDepth : 0)
                                width: parent.width - 2 * x
                                spacing: 1
                                Behavior on y { NumberAnimation { duration: 65; easing.type: Easing.OutCubic } }
                                Label {
                                    width: parent.width
                                    text: "K" + (physicalKey.modelData.index + 1)
                                    color: keypad.muted
                                    font.pixelSize: Math.max(8, physicalKey.width * 0.14)
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                                Label {
                                    width: parent.width
                                    text: physicalKey.modelData.label
                                    color: keypad.ink
                                    font.pixelSize: Math.max(9, physicalKey.width * 0.17)
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    maximumLineCount: 2
                                    wrapMode: Text.Wrap
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
