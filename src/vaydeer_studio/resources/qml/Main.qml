import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1320
    height: 820
    minimumWidth: 980
    minimumHeight: 660
    visible: true
    title: "Vaydeer Studio"
    property bool darkMode: true
    property int navIndex: 0
    property color canvas: darkMode ? "#15191E" : "#F4F6F8"
    property color panel: darkMode ? "#20262D" : "#FFFFFF"
    property color panelRaised: darkMode ? "#29313A" : "#EEF2F5"
    property color ink: darkMode ? "#EEF3F6" : "#162029"
    property color muted: darkMode ? "#AAB7C2" : "#52616E"
    property color accent: "#12A594"
    property color amber: "#E9A528"
    property color danger: "#D85B62"

    Material.theme: darkMode ? Material.Dark : Material.Light
    Material.accent: accent

    Component.onCompleted: vaydeerBridge.refreshDiagnostics()

    background: Rectangle { color: window.canvas }

    Dialog {
        id: diffDialog
        modal: true
        focus: true
        title: "Review device changes"
        width: Math.min(window.width - 120, 760)
        height: Math.min(window.height - 100, 600)
        anchors.centerIn: parent
        background: Rectangle { color: window.panel; radius: 6; border.color: window.darkMode ? "#3B4651" : "#D8E0E6" }
        contentItem: ColumnLayout {
            spacing: 14
            Label {
                text: vaydeerBridge.previewLines.length > 0 ? "The current device will be backed up before these changes are applied." : vaydeerBridge.statusMessage
                color: window.muted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: window.panelRaised
                radius: 4
                ListView {
                    anchors.fill: parent
                    anchors.margins: 10
                    model: vaydeerBridge.previewLines
                    clip: true
                    delegate: Label {
                        width: ListView.view.width
                        text: modelData
                        color: window.ink
                        padding: 6
                        wrapMode: Text.WordWrap
                    }
                    footer: Label {
                        visible: vaydeerBridge.previewLines.length === 0
                        text: "No pending changes."
                        color: window.muted
                        padding: 6
                    }
                }
            }
            Label {
                visible: vaydeerBridge.backupPath.length > 0
                text: "Backup: " + vaydeerBridge.backupPath
                color: window.muted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }
        footer: RowLayout {
            spacing: 8
            Item { Layout.fillWidth: true }
            Button { text: "Cancel"; onClicked: diffDialog.close() }
            Button {
                text: "Apply mock changes"
                enabled: vaydeerBridge.device.writable && vaydeerBridge.previewLines.length > 0
                onClicked: { vaydeerBridge.applyPreview(); diffDialog.close() }
                Accessible.name: "Apply reviewed mock configuration"
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: rail
            Layout.fillHeight: true
            Layout.preferredWidth: 222
            color: darkMode ? "#10161B" : "#17222B"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        radius: 6
                        color: window.accent
                        Label { anchors.centerIn: parent; text: "V"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 17 }
                    }
                    ColumnLayout {
                        spacing: 0
                        Label { text: "Vaydeer Studio"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 16 }
                        Label { text: vaydeerBridge.device.usb; color: "#AAB7C2"; font.pixelSize: 11 }
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#33414C"; Layout.topMargin: 14; Layout.bottomMargin: 8 }
                Repeater {
                    model: ["Devices", "On-device mappings", "Linux bindings", "Profiles", "Live key tester", "Diagnostics", "Research"]
                    delegate: ItemDelegate {
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true
                        height: 42
                        text: modelData
                        highlighted: index === window.navIndex
                        Accessible.name: modelData
                        contentItem: Label {
                            text: parent.text
                            color: parent.highlighted ? "#FFFFFF" : "#C4D0D8"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 10
                            font.pixelSize: 14
                        }
                        background: Rectangle { radius: 5; color: parent.highlighted ? "#24554F" : "transparent" }
                        onClicked: {
                            window.navIndex = index
                            vaydeerBridge.setTesterOpen(index === 4)
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    color: "#17222B"
                    radius: 5
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 3
                        Label { text: vaydeerBridge.device.model; color: "#EDF4F7"; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        Label { text: "FW " + vaydeerBridge.device.firmware + "  •  " + vaydeerBridge.device.keyCount + " keys"; color: "#AAB7C2"; font.pixelSize: 11 }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                color: window.panel
                border.color: window.darkMode ? "#303A43" : "#D8E0E6"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 20
                    spacing: 12
                    Label {
                        text: ["Devices", "On-device mappings", "Linux bindings", "Profiles", "Live key tester", "Diagnostics", "Research"][window.navIndex]
                        color: window.ink
                        font.pixelSize: 18
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Label { text: vaydeerBridge.dirty ? "Unsaved profile changes" : "Profile in sync"; color: vaydeerBridge.dirty ? window.amber : window.accent; font.pixelSize: 12 }
                    Button {
                        text: darkMode ? "Light" : "Dark"
                        onClicked: darkMode = !darkMode
                        Accessible.name: "Switch color theme"
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                color: window.darkMode ? "#182128" : "#E9EEF2"
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 24
                    anchors.right: parent.right
                    anchors.rightMargin: 24
                    text: vaydeerBridge.statusMessage
                    color: window.muted
                    elide: Text.ElideRight
                    font.pixelSize: 12
                }
            }

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.navIndex
                onCurrentIndexChanged: {
                    if (currentIndex === 5)
                        vaydeerBridge.refreshDiagnostics()
                }

                // Devices
                Item {
                    ScrollView {
                        id: devicesScroll
                        anchors.fill: parent
                        contentWidth: availableWidth
                        contentHeight: devicesContent.implicitHeight + 48
                        ColumnLayout {
                            id: devicesContent
                            x: 24
                            y: 24
                            width: Math.max(0, devicesScroll.availableWidth - 48)
                            spacing: 18
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 148
                                color: window.panel
                                radius: 6
                                border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 22
                                    Rectangle { Layout.preferredWidth: 12; Layout.preferredHeight: 12; radius: 6; color: vaydeerBridge.connection.connected ? window.accent : window.danger }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Label { text: vaydeerBridge.connection.title; color: window.ink; font.bold: true; font.pixelSize: 18; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        Label { text: vaydeerBridge.connection.message; color: window.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        Label { visible: vaydeerBridge.connection.recovery.length > 0; text: vaydeerBridge.connection.recovery; color: window.amber; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                    Button { text: "Retry detection"; onClicked: vaydeerBridge.reconnectDevice(); Accessible.name: "Retry Vaydeer device detection" }
                                    Button { text: "Setup"; onClicked: vaydeerBridge.showSetupCommand(); Accessible.name: "Show hardware setup command" }
                                    Button { text: "Export diagnostics"; onClicked: vaydeerBridge.exportDiagnostics(); Accessible.name: "Export sanitized diagnostics" }
                                }
                            }
                            GridLayout {
                                id: deviceFacts
                                Layout.fillWidth: true
                                Layout.preferredHeight: columns === 3 ? 188 : 288
                                columns: width > 940 ? 3 : 2
                                rowSpacing: 12
                                columnSpacing: 12
                                Repeater {
                                    model: [
                                        ["Firmware", vaydeerBridge.device.firmware], ["Bootloader", vaydeerBridge.device.bootloader], ["Physical keys", vaydeerBridge.device.keyCount],
                                        ["Active layer", vaydeerBridge.device.activeLayer + 1], ["Layers", vaydeerBridge.device.layerCount + " / 6"], ["Permissions", vaydeerBridge.device.permissions]
                                    ]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.preferredWidth: (
                                            deviceFacts.width - (deviceFacts.columns - 1) * deviceFacts.columnSpacing
                                        ) / deviceFacts.columns
                                        Layout.preferredHeight: 88
                                        color: window.panel
                                        radius: 6
                                        border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 14
                                            Label { text: parent.parent.modelData[0]; color: window.muted; font.pixelSize: 12 }
                                            Label { text: parent.parent.modelData[1]; color: window.ink; font.pixelSize: 20; font.bold: true }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                visible: vaydeerBridge.device.warning.length > 0
                                Layout.fillWidth: true
                                Layout.preferredHeight: warningText.implicitHeight + 26
                                color: window.darkMode ? "#3C3220" : "#FFF4D6"
                                radius: 5
                                Label {
                                    id: warningText
                                    anchors.fill: parent
                                    anchors.margins: 13
                                    text: vaydeerBridge.device.warning
                                    wrapMode: Text.WordWrap
                                    color: window.darkMode ? "#FFE4A3" : "#73510A"
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 168
                                color: window.panel
                                radius: 6
                                border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Hardware setup"; color: window.ink; font.bold: true; Layout.fillWidth: true }
                                        Button { text: "Reload service"; onClicked: vaydeerBridge.reloadService(); Accessible.name: "Reload Vaydeer keepalive service" }
                                        Button { text: "Copy summary"; onClicked: vaydeerBridge.copyDiagnosticSummary(); Accessible.name: "Copy sanitized diagnostic summary" }
                                    }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: devicesContent.width > 860 ? 4 : 2
                                        rowSpacing: 8
                                        columnSpacing: 16
                                        Repeater {
                                            model: vaydeerBridge.setupChecks
                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: 6
                                                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: modelData.status === "pass" ? window.accent : modelData.status === "warn" ? window.amber : window.danger }
                                                Label { text: modelData.label; color: window.muted; font.pixelSize: 12 }
                                            }
                                        }
                                    }
                                    Label { text: "Run ./scripts/install.sh to install or repair udev and the user service. The application never invokes sudo itself."; color: window.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }

                // Mapping editor
                Item {
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 18
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 14
                            RowLayout {
                                Layout.fillWidth: true
                                Repeater {
                                    model: vaydeerBridge.layers
                                    delegate: Button {
                                        required property var modelData
                                        text: "Layer " + (modelData.index + 1) + "  " + modelData.name
                                        checked: modelData.selected
                                        checkable: true
                                        onClicked: vaydeerBridge.selectLayer(modelData.index)
                                        Accessible.name: text
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                Button { text: "Read"; onClicked: vaydeerBridge.readFromDevice(); Accessible.name: "Read configuration from device" }
                                Button {
                                    text: "Restore latest"
                                    onClicked: { vaydeerBridge.restoreLatestBackup(); diffDialog.open() }
                                    Accessible.name: "Stage latest backup restore"
                                }
                                Button { text: "Discard"; enabled: vaydeerBridge.dirty; onClicked: vaydeerBridge.discardChanges(); Accessible.name: "Discard profile changes" }
                                Button {
                                    text: "Review changes"
                                    enabled: vaydeerBridge.dirty
                                    onClicked: { vaydeerBridge.previewApply(); diffDialog.open() }
                                    Accessible.name: "Review mapping diff before applying"
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: window.panel
                                radius: 6
                                border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                GridLayout {
                                    id: keypadGrid
                                    anchors.centerIn: parent
                                    columns: vaydeerBridge.layoutColumns
                                    rowSpacing: 14
                                    columnSpacing: 14
                                    Repeater {
                                        model: vaydeerBridge.keys
                                        delegate: Button {
                                            required property var modelData
                                            Layout.preferredWidth: 146
                                            Layout.preferredHeight: 124
                                            checkable: true
                                            checked: modelData.selected
                                            text: "K" + (modelData.index + 1) + "\n" + modelData.label
                                            Accessible.name: modelData.physicalLabel + ", " + modelData.label
                                            onClicked: vaydeerBridge.selectKey(modelData.index)
                                            contentItem: ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 10
                                                spacing: 6
                                                Label { text: "K" + (modelData.index + 1); color: window.muted; font.pixelSize: 11; font.bold: true }
                                                Label { text: modelData.label; color: window.ink; Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; font.pixelSize: 14; font.bold: true }
                                                Label { text: modelData.support === "on_device" ? "On device" : "Experimental"; color: modelData.support === "on_device" ? window.accent : window.amber; font.pixelSize: 10 }
                                            }
                                            background: Rectangle {
                                                radius: 6
                                                color: parent.checked ? (window.darkMode ? "#24554F" : "#D7F1ED") : window.panelRaised
                                                border.width: parent.checked ? 2 : 1
                                                border.color: parent.checked ? window.accent : (window.darkMode ? "#45525E" : "#D3DCE2")
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        Rectangle {
                            Layout.preferredWidth: 310
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12
                                Label { text: "Key " + (vaydeerBridge.selectedKey.index + 1); color: window.ink; font.pixelSize: 17; font.bold: true }
                                Label { text: vaydeerBridge.selectedKey.support === "on_device" ? "Stored on the keypad" : "Experimental or service-only"; color: vaydeerBridge.selectedKey.support === "on_device" ? window.accent : window.amber; font.pixelSize: 12 }
                                Label { text: "Action"; color: window.muted; font.pixelSize: 12 }
                                ComboBox {
                                    id: categoryBox
                                    Layout.fillWidth: true
                                    model: ["Keyboard key", "Modifier", "Key combination", "Media", "System control", "Mouse", "Macro", "Text", "Layer action", "Vaydeer action", "Linux host action", "Disabled"]
                                    Component.onCompleted: currentIndex = Math.max(0, model.indexOf("Keyboard key"))
                                }
                                Label { text: "Label"; color: window.muted; font.pixelSize: 12 }
                                TextField { id: labelField; Layout.fillWidth: true; text: vaydeerBridge.selectedKey.label; Accessible.name: "Key label" }
                                Label { text: "Key code or names"; color: window.muted; font.pixelSize: 12 }
                                TextField { id: codeField; Layout.fillWidth: true; text: vaydeerBridge.selectedKey.codes; placeholderText: "A, F13, CTRL+ALT+P"; Accessible.name: "Key codes" }
                                Label { text: "Mouse, macro, text, layer, Vaydeer, and Linux host actions are retained as experimental and are never sent to hardware."; visible: categoryBox.currentText !== "Keyboard key" && categoryBox.currentText !== "Modifier" && categoryBox.currentText !== "Key combination" && categoryBox.currentText !== "Media" && categoryBox.currentText !== "System control" && categoryBox.currentText !== "Disabled"; color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
                                Item { Layout.fillHeight: true }
                                Button { Layout.fillWidth: true; text: "Save key"; onClicked: vaydeerBridge.saveKey(categoryBox.currentText, labelField.text, codeField.text); Accessible.name: "Save key assignment" }
                            }
                        }
                    }
                }

                // Linux bindings
                Item {
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 18
                        ColumnLayout {
                            Layout.preferredWidth: 360
                            Layout.fillHeight: true
                            spacing: 12
                            Label { text: "New Linux-side binding"; color: window.ink; font.pixelSize: 17; font.bold: true }
                            Label { text: "Runs only while vaydeer-studiod is active. Commands use an argv array unless shell execution is explicitly enabled outside this UI."; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            ComboBox { id: bindAction; Layout.fillWidth: true; model: ["application", "url", "file", "directory", "command", "notification", "script", "text"] }
                            TextField { id: bindTarget; Layout.fillWidth: true; placeholderText: "Application, URL, path, or program"; Accessible.name: "Linux binding target" }
                            TextField { id: bindArgs; Layout.fillWidth: true; placeholderText: "Arguments, separated by spaces"; Accessible.name: "Linux binding arguments" }
                            Button { text: "Add for selected key"; Layout.fillWidth: true; onClicked: vaydeerBridge.addBinding(bindAction.currentText, bindTarget.text, bindArgs.text); Accessible.name: "Add Linux binding" }
                            Item { Layout.fillHeight: true }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.darkMode ? "#33414C" : "#D8E0E6" }
                            Label { text: "Selected key: K" + (vaydeerBridge.selectedKey.index + 1); color: window.accent; font.bold: true }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            ListView {
                                anchors.fill: parent
                                anchors.margins: 12
                                clip: true
                                model: vaydeerBridge.bindings
                                spacing: 8
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: ListView.view.width
                                    height: 76
                                    radius: 5
                                    color: window.panelRaised
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Label { text: "K" + (modelData.key_index + 1) + " • " + modelData.action; color: window.ink; font.bold: true }
                                            Label { text: modelData.target + (modelData.arguments.length ? "  " + modelData.arguments.join(" ") : ""); color: window.muted; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                        Button { text: "Run mock"; onClicked: vaydeerBridge.runBinding(index); Accessible.name: "Run this binding in mock mode" }
                                    }
                                }
                                footer: Label { visible: vaydeerBridge.bindings.length === 0; text: "No Linux-side bindings in this profile."; color: window.muted; padding: 12 }
                            }
                        }
                    }
                }

                // Profiles
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 118
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 14
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Active profile"; color: window.muted; font.pixelSize: 12 }
                                    TextField { id: profileName; text: vaydeerBridge.profileName; Layout.fillWidth: true; onEditingFinished: vaydeerBridge.renameProfile(text); Accessible.name: "Profile name" }
                                }
                                Button { text: "Save library"; onClicked: vaydeerBridge.saveProfile(); Accessible.name: "Save profile to library" }
                                Button { text: "Duplicate"; onClicked: vaydeerBridge.duplicateProfile(); Accessible.name: "Duplicate profile" }
                                Button { text: "Export JSON"; onClicked: vaydeerBridge.exportProfile(); Accessible.name: "Export profile" }
                                Button { text: "Delete"; onClicked: vaydeerBridge.deleteProfile(); Accessible.name: "Clear current profile" }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            TextField { id: importProfilePath; Layout.fillWidth: true; placeholderText: "Profile JSON or YAML path"; Accessible.name: "Profile import path" }
                            Button { text: "Import"; onClicked: vaydeerBridge.importProfile(importProfilePath.text); Accessible.name: "Import profile" }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            rowSpacing: 12
                            columnSpacing: 12
                            Repeater {
                                model: [["Portable profile", "JSON or YAML schema version 1"], ["On-device mappings", "Validated device actions"], ["Linux bindings", vaydeerBridge.bindings.length + " service actions"]]
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 96
                                    color: window.panel
                                    radius: 6
                                    border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        Label { text: parent.parent.modelData[0]; color: window.ink; font.bold: true }
                                        Label { text: parent.parent.modelData[1]; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 136
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                Label { text: "Saved profiles"; color: window.ink; font.bold: true }
                                ListView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: vaydeerBridge.savedProfiles
                                    spacing: 6
                                    delegate: Button {
                                        required property var modelData
                                        width: ListView.view.width
                                        text: modelData.name
                                        onClicked: vaydeerBridge.loadSavedProfile(modelData.id)
                                        Accessible.name: "Load saved profile " + modelData.name
                                    }
                                    footer: Label { visible: vaydeerBridge.savedProfiles.length === 0; text: "No saved profiles yet."; color: window.muted; padding: 4 }
                                }
                            }
                        }
                    }
                }

                // Live tester
                Item {
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 18
                        Rectangle {
                            Layout.preferredWidth: 350
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12
                                Label { text: "Live key tester"; color: window.ink; font.pixelSize: 17; font.bold: true }
                                Label { text: "Events are shown only while this screen is open. In mock mode, click a key to generate its press and release reports."; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: vaydeerBridge.layoutColumns
                                    Repeater {
                                        model: vaydeerBridge.keys
                                        delegate: Button { required property var modelData; text: "K" + (modelData.index + 1); Layout.fillWidth: true; Layout.preferredHeight: 52; onClicked: vaydeerBridge.simulateKey(modelData.index); Accessible.name: "Simulate key " + (modelData.index + 1) }
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Label { text: "Vendor event format: fb 03 layer key state xor"; color: window.muted; font.pixelSize: 11 }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            ListView {
                                anchors.fill: parent
                                anchors.margins: 12
                                model: vaydeerBridge.testerEvents
                                clip: true
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: ListView.view.width
                                    height: 38
                                    color: index % 2 ? "transparent" : window.panelRaised
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        Label { text: modelData.timestamp; color: window.muted; Layout.preferredWidth: 110 }
                                        Label { text: "K" + modelData.key; color: window.ink; Layout.preferredWidth: 52 }
                                        Label { text: modelData.event; color: modelData.event === "Press" ? window.accent : window.muted; Layout.preferredWidth: 64 }
                                        Label { text: "Layer " + (modelData.layer + 1); color: window.muted; Layout.preferredWidth: 65 }
                                        Label { text: modelData.raw; color: window.muted; font.family: "monospace" }
                                    }
                                }
                                footer: Label { visible: vaydeerBridge.testerEvents.length === 0; text: "No key events yet."; color: window.muted; padding: 12 }
                            }
                        }
                    }
                }

                // Diagnostics
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 14
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Diagnostics are sanitized: no serial numbers, home paths, or vendor binaries are exported."; color: window.muted; Layout.fillWidth: true }
                            Button { text: "Refresh"; onClicked: vaydeerBridge.refreshDiagnostics(); Accessible.name: "Refresh diagnostics" }
                            Button { text: "Copy summary"; onClicked: vaydeerBridge.copyDiagnosticSummary(); Accessible.name: "Copy sanitized diagnostics summary" }
                            Button { text: "Export diagnostics"; onClicked: vaydeerBridge.exportDiagnostics(); Accessible.name: "Export diagnostics bundle" }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 12
                            Repeater {
                                model: [["Command interface", "Interface 0 • 0xFF00 / 0x0001"], ["Keepalive interface", "Interface 2 • read-only • no fixed hidraw path"], ["Keepalive status", vaydeerBridge.device.keepalive], ["Permission status", vaydeerBridge.device.permissions]]
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 92
                                    color: window.panel
                                    radius: 6
                                    border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        Label { text: parent.parent.modelData[0]; color: window.muted; font.pixelSize: 12 }
                                        Label { text: parent.parent.modelData[1]; color: window.ink; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.bold: true }
                                    }
                                }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                            Label { anchors.fill: parent; anchors.margins: 16; text: vaydeerBridge.diagnosticSummary; color: window.muted; wrapMode: Text.WordWrap; verticalAlignment: Text.AlignTop }
                        }
                    }
                }

                // Research
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 24
                            spacing: 14
                            Label { text: "Research and safety"; color: window.ink; font.pixelSize: 21; font.bold: true }
                            Repeater {
                                model: [
                                    ["Linux activation", "Opening the JP-1011 vendor async interface (USB interface 2) read-only is sufficient for normal Linux keyboard traffic. Reads and writes are not required for the keepalive."],
                                    ["Vendor HID protocol", "Configuration uses checksummed command reports. Vaydeer Studio allowlists documented configuration IDs and rejects unknown IDs."],
                                    ["Firmware boundary", "Firmware update command 0xFC is blocked by the protocol core. There is no firmware updater, raw packet console, or command scanner."],
                                    ["QMK status", "The APM32F103CBT6 is capable in principle, but no JP-1011 port, verified bootloader path, or recovery workflow exists. Firmware replacement is outside this application."]
                                ]
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: researchBody.implicitHeight + 54
                                    color: window.panel
                                    radius: 6
                                    border.color: window.darkMode ? "#33414C" : "#D8E0E6"
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 7
                                        Label { text: parent.parent.modelData[0]; color: window.ink; font.bold: true; font.pixelSize: 15 }
                                        Label { id: researchBody; text: parent.parent.modelData[1]; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                }
                            }
                            Item { Layout.preferredHeight: 4 }
                        }
                    }
                }
            }
        }
    }
}
