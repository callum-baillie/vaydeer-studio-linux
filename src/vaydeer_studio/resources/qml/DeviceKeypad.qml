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
    property bool showSyncState: false
    property color accent: "#20BFA9"
    property color pendingColor: "#D99C35"
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
            id: topShell
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: parent.height
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
                    id: keyRepeater
                    // A repeater owns its delegates. Keep the root reference
                    // here so an event handler never has to resolve the outer
                    // keypad ID from the delegate's isolated scope.
                    property var keypadControl: keypad
                    model: keypad.keys
                    delegate: Button {
                        id: physicalKey
                        required property var modelData
                        objectName: "physicalKey-" + modelData.index
                        readonly property var keypadRoot: keyRepeater.keypadControl
                        readonly property bool isPressed: keypadRoot !== null && keypadRoot.pressedKeys.indexOf(modelData.index) !== -1
                        readonly property bool isSelected: keypadRoot !== null && keypadRoot.selectedKey === modelData.index
                        readonly property bool hasPendingChange: modelData.pending === true
                        readonly property real pressDepth: Math.max(2, height * 0.07)
                        width: (keyGrid.width - keyGrid.spacing * (keyGrid.columns - 1)) / keyGrid.columns
                        height: (keyGrid.height - keyGrid.spacing * (keyGrid.rows - 1)) / keyGrid.rows
                        enabled: keypadRoot !== null && keypadRoot.interactive
                        hoverEnabled: keypadRoot !== null && keypadRoot.interactive
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: "Physical key " + (modelData.index + 1) + ", " + modelData.label
                        Accessible.description: modelData.physicalLabel + (physicalKey.hasPendingChange ? ", pending device sync" : ", matches device state")
                        ToolTip.visible: hovered
                        ToolTip.text: modelData.physicalLabel + "\nDraft: " + modelData.label + (physicalKey.hasPendingChange ? "\nDevice: " + modelData.deviceLabel + "\nPending sync" : "\nCurrent on device")

                        onClicked: {
                            if (keypadRoot === null)
                                return
                            keypadRoot.keySelected(modelData.index)
                            if (keypadRoot.simulateOnClick)
                                keypadRoot.keyActivated(modelData.index)
                        }

                        background: Item {
                            Rectangle {
                                x: 0
                                y: physicalKey.pressDepth
                                width: parent.width
                                height: parent.height - physicalKey.pressDepth
                                radius: Math.max(4, parent.width * 0.11)
                                color: Qt.darker(physicalKey.keypadRoot.panelColor, 1.4)
                            }
                            Rectangle {
                                id: keyCap
                                x: 0
                                y: physicalKey.isPressed ? physicalKey.pressDepth : 0
                                width: parent.width
                                height: parent.height - physicalKey.pressDepth
                                radius: Math.max(4, parent.width * 0.11)
                                color: physicalKey.isPressed ? Qt.darker(physicalKey.keypadRoot.panelColor, 1.18) : physicalKey.keypadRoot.panelColor
                                border.width: 1
                                border.color: physicalKey.isSelected ? physicalKey.keypadRoot.accent : (physicalKey.hasPendingChange ? physicalKey.keypadRoot.pendingColor : Qt.lighter(physicalKey.keypadRoot.panelColor, 1.55))
                                Behavior on y { NumberAnimation { duration: 65; easing.type: Easing.OutCubic } }
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: 3
                                    radius: Math.max(3, parent.radius - 2)
                                    visible: !physicalKey.isPressed
                                    color: "transparent"
                                    border.width: physicalKey.isSelected ? 1 : 0
                                    border.color: Qt.lighter(physicalKey.keypadRoot.panelColor, 1.28)
                                }
                                Rectangle {
                                    visible: physicalKey.keypadRoot.showSyncState
                                    width: Math.max(7, parent.width * 0.11)
                                    height: width
                                    radius: width / 2
                                    anchors.top: parent.top
                                    anchors.right: parent.right
                                    anchors.topMargin: Math.max(4, parent.width * 0.07)
                                    anchors.rightMargin: Math.max(4, parent.width * 0.07)
                                    color: physicalKey.hasPendingChange ? physicalKey.keypadRoot.pendingColor : physicalKey.keypadRoot.accent
                                    border.color: Qt.lighter(color, 1.2)
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
                                    color: physicalKey.keypadRoot.muted
                                    font.pixelSize: Math.max(8, physicalKey.width * 0.14)
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                                Label {
                                    width: parent.width
                                    text: physicalKey.modelData.label
                                    color: physicalKey.keypadRoot.ink
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
