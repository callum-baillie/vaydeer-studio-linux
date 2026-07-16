import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1440
    height: 900
    minimumWidth: 1040
    minimumHeight: 680
    title: "Vaydeer Studio"
    color: darkMode ? "#10171D" : "#F3F6F7"

    property bool darkMode: true
    property int navIndex: 0
    property color ink: darkMode ? "#E8EEF2" : "#18242D"
    property color muted: darkMode ? "#9BAAB5" : "#657681"
    property color accent: "#1DB9A2"
    property color amber: "#D99C35"
    property color danger: "#D25B5B"
    property color panel: darkMode ? "#172129" : "#FFFFFF"
    property color panelRaised: darkMode ? "#202D36" : "#EEF3F5"
    property color line: darkMode ? "#33414C" : "#D8E0E6"
    property var pagesModel: ["Devices", "On-device mappings", "Linux bindings", "Profiles", "Live key tester", "Diagnostics"]

    function layerIndexForSelected() {
        for (let index = 0; index < vaydeerBridge.layers.length; index++) {
            if (vaydeerBridge.layers[index].selected)
                return index
        }
        return 0
    }

    function selectedLayerName() {
        const index = layerIndexForSelected()
        return vaydeerBridge.layers.length > index ? vaydeerBridge.layers[index].name : "Layer"
    }

    function actionDataLabel(category) {
        if (category === "Macro")
            return "Manual macro steps"
        if (category === "Text")
            return "Text to send through the Linux service"
        if (category === "Layer action")
            return "Target layer or layer behavior"
        if (category === "Linux host action")
            return "Service action label"
        if (category === "Mouse")
            return "Mouse action"
        if (category === "Vaydeer action")
            return "Vaydeer action detail"
        return "Action detail"
    }

    function actionState(category) {
        if (["Keyboard key", "Modifier", "Key combination", "Media", "System control", "Disabled"].indexOf(category) !== -1)
            return "Stored on device"
        if (["Text", "Linux host action"].indexOf(category) !== -1)
            return "Linux service only"
        return "Experimental profile data"
    }

    function bindingTargetHint(action) {
        if (action === "url") return "https://example.com"
        if (action === "application") return "/usr/bin/application"
        if (action === "file" || action === "directory") return "/home/user/path"
        if (action === "notification") return "Notification body"
        if (action === "text") return "Text to type"
        if (action === "script") return "/path/to/script"
        return "/usr/bin/program"
    }

    component HintButton: ToolButton {
        id: hint
        text: "?"
        hoverEnabled: true
        implicitWidth: 22
        implicitHeight: 22
        Accessible.name: "Help"
        contentItem: Label {
            text: hint.text
            color: window.muted
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.bold: true
        }
        background: Rectangle {
            radius: 11
            color: hint.hovered ? window.panelRaised : "transparent"
            border.color: window.line
            border.width: 1
        }
        ToolTip.visible: hovered
    }

    component SectionTitle: RowLayout {
        property string text: ""
        property string hint: ""
        Layout.fillWidth: true
        spacing: 6
        Label { text: parent.text; color: window.ink; font.pixelSize: 17; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
        HintButton { visible: parent.hint.length > 0; ToolTip.text: parent.hint }
    }

    component StatusPill: Rectangle {
        property string label: ""
        property color statusColor: window.accent
        implicitWidth: statusLabel.implicitWidth + 22
        implicitHeight: 26
        radius: 5
        color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, window.darkMode ? 0.16 : 0.12)
        border.color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, 0.45)
        Label {
            id: statusLabel
            anchors.centerIn: parent
            text: parent.label
            color: parent.statusColor
            font.pixelSize: 11
            font.bold: true
        }
    }

    Dialog {
        id: diffDialog
        title: "Review proposed device changes"
        modal: true
        width: Math.min(window.width - 72, 760)
        height: Math.min(window.height - 110, 580)
        anchors.centerIn: parent
        background: Rectangle { color: window.panel; radius: 6; border.color: window.line }
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: vaydeerBridge.previewLines.length === 0 ? "No on-device mapping changes are staged." : "A timestamped backup is created before every write."
                color: window.muted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                visible: vaydeerBridge.backupPath.length > 0
                text: "Backup: " + vaydeerBridge.backupPath
                color: window.muted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: vaydeerBridge.previewLines
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width
                    height: diffText.implicitHeight + 16
                    color: index % 2 === 0 ? window.panelRaised : "transparent"
                    Label {
                        id: diffText
                        anchors.fill: parent
                        anchors.margins: 8
                        text: modelData
                        color: window.ink
                        wrapMode: Text.WordWrap
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button { text: "Close"; onClicked: diffDialog.close() }
                Button {
                    text: vaydeerBridge.mockMode ? "Apply in mock" : "Apply from terminal"
                    enabled: vaydeerBridge.previewLines.length > 0
                    onClicked: vaydeerBridge.applyPreview()
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: window.panel
            border.color: window.line
            border.width: 1
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 12
                Label { text: "Vaydeer Studio"; color: window.ink; font.pixelSize: 20; font.bold: true }
                Label { text: "Linux keypad configuration"; color: window.muted; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                StatusPill {
                    label: vaydeerBridge.connection.connected ? "Connected" : "Offline"
                    statusColor: vaydeerBridge.connection.connected ? window.accent : window.danger
                }
                Button {
                    text: window.darkMode ? "Light" : "Dark"
                    onClicked: window.darkMode = !window.darkMode
                    Accessible.name: "Switch application color theme"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 218
                Layout.fillHeight: true
                color: window.darkMode ? "#131C23" : "#EAF0F2"
                border.color: window.line
                border.width: 1
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 5
                    Repeater {
                        model: window.pagesModel
                        delegate: Button {
                            required property string modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            text: modelData
                            checkable: true
                            checked: window.navIndex === index
                            Accessible.name: modelData
                            onClicked: {
                                window.navIndex = index
                                vaydeerBridge.setActivePage(index)
                            }
                            contentItem: Label {
                                text: parent.text
                                color: parent.checked ? window.ink : window.muted
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 12
                                font.bold: parent.checked
                            }
                            background: Rectangle {
                                radius: 5
                                color: parent.checked ? (window.darkMode ? "#203A3B" : "#D9EEEA") : "transparent"
                                border.color: parent.checked ? window.accent : "transparent"
                                border.width: parent.checked ? 1 : 0
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        color: window.panel
                        radius: 5
                        border.color: window.line
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 2
                            Label { text: "Active profile"; color: window.muted; font.pixelSize: 11 }
                            Label { text: vaydeerBridge.profileName; color: window.ink; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                            Label { text: vaydeerBridge.dirty ? "Unsaved mapping edits" : "Saved or read from device"; color: vaydeerBridge.dirty ? window.amber : window.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
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
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 48)
                            x: 24
                            y: 24
                            spacing: 16
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 224
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 20
                                    DeviceKeypad {
                                        Layout.preferredWidth: 188
                                        Layout.preferredHeight: 186
                                        keys: vaydeerBridge.keys
                                        selectedKey: vaydeerBridge.selectedKey.index
                                        columns: vaydeerBridge.layoutColumns
                                        interactive: false
                                        accent: window.accent
                                        ink: window.ink
                                        muted: window.muted
                                        bodyColor: window.darkMode ? "#63717C" : "#9AA7AF"
                                        panelColor: window.darkMode ? "#111920" : "#E3EAED"
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 7
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Rectangle { Layout.preferredWidth: 10; Layout.preferredHeight: 10; radius: 5; color: vaydeerBridge.connection.connected ? window.accent : window.danger }
                                            Label { text: vaydeerBridge.connection.title; color: window.ink; font.bold: true; font.pixelSize: 20; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        }
                                        Label { text: vaydeerBridge.connection.message; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        Label { visible: vaydeerBridge.connection.recovery.length > 0; text: vaydeerBridge.connection.recovery; color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
                                        Item { Layout.fillHeight: true }
                                        RowLayout {
                                            Button { text: "Reconnect"; onClicked: vaydeerBridge.reconnectDevice(); Accessible.name: "Reconnect to Vaydeer device" }
                                            Button { text: "Setup"; onClicked: vaydeerBridge.showSetupCommand(); Accessible.name: "Show Linux setup command" }
                                            Button { text: "Export diagnostics"; onClicked: vaydeerBridge.exportDiagnostics(); Accessible.name: "Export sanitized diagnostics" }
                                        }
                                    }
                                }
                            }
                            GridLayout {
                                id: deviceFacts
                                Layout.fillWidth: true
                                columns: width > 920 ? 3 : 2
                                rowSpacing: 12
                                columnSpacing: 12
                                Repeater {
                                    model: [
                                        ["Firmware", vaydeerBridge.device.firmware], ["Bootloader", vaydeerBridge.device.bootloader], ["Physical keys", vaydeerBridge.device.keyCount],
                                        ["Selected layer", vaydeerBridge.device.activeLayer + 1], ["Profile layers", vaydeerBridge.device.layerCount + " / 6"], ["Permissions", vaydeerBridge.device.permissions]
                                    ]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 84
                                        color: window.panel
                                        radius: 6
                                        border.color: window.line
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 13
                                            Label { text: modelData[0]; color: window.muted; font.pixelSize: 12 }
                                            Label { text: modelData[1]; color: window.ink; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
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
                                Label { id: warningText; anchors.fill: parent; anchors.margins: 13; text: vaydeerBridge.device.warning; color: window.darkMode ? "#FFE4A3" : "#73510A"; wrapMode: Text.WordWrap }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 224
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { text: "Local Vaydeer service"; hint: "This status is for vaydeer-studiod on the host running this application. The service keeps the vendor event interface open read-only so normal keyboard traffic remains active." }
                                        Button { text: "Refresh"; onClicked: vaydeerBridge.refreshServiceStatus(); Accessible.name: "Refresh local Vaydeer service status" }
                                        Button { text: "Reload service"; onClicked: vaydeerBridge.reloadService() }
                                        Button { visible: !vaydeerBridge.service.installed; text: "Install user service"; onClicked: vaydeerBridge.installUserService(); Accessible.name: "Install and enable local Vaydeer user service" }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Host"; color: window.muted; font.pixelSize: 12; Layout.preferredWidth: 48 }
                                        Label { text: vaydeerBridge.service.host; color: window.ink; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        StatusPill { label: vaydeerBridge.service.installed ? "Installed" : "Not installed"; statusColor: vaydeerBridge.service.installed ? window.accent : window.amber }
                                        StatusPill { label: vaydeerBridge.service.running ? "Running" : "Stopped"; statusColor: vaydeerBridge.service.running ? window.accent : window.danger }
                                        StatusPill { label: vaydeerBridge.service.startup ? "Starts at login" : "Not enabled"; statusColor: vaydeerBridge.service.startup ? window.accent : window.amber }
                                    }
                                    Label { text: vaydeerBridge.service.detail; color: vaydeerBridge.service.running ? window.muted : window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: width > 800 ? 4 : 2
                                        rowSpacing: 8
                                        columnSpacing: 12
                                        Repeater {
                                            model: vaydeerBridge.setupChecks
                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: modelData.status === "pass" ? window.accent : modelData.status === "warn" ? window.amber : window.danger }
                                                Label { text: modelData.label; color: window.muted; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // On-device mappings
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 48)
                            x: 24
                            y: 20
                            spacing: 14
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "On-device mappings"; hint: "Only documented keyboard, modifier, combination, media, system, and disabled actions can be written to a JP-1011." }
                                Label { text: "Profile: " + vaydeerBridge.profileName; color: window.muted; font.pixelSize: 12 }
                                StatusPill { label: vaydeerBridge.profileTargetPlatformLabel; statusColor: window.muted }
                                StatusPill {
                                    label: vaydeerBridge.dirty ? vaydeerBridge.pendingMappingCount + " pending" : "Matches device"
                                    statusColor: vaydeerBridge.dirty ? window.amber : window.accent
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 104
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 9
                                        Label { text: "Layer"; color: window.muted; font.pixelSize: 12 }
                                        ComboBox {
                                            id: mappingLayerCombo
                                            Layout.preferredWidth: 185
                                            model: vaydeerBridge.layers
                                            textRole: "displayName"
                                            currentIndex: window.layerIndexForSelected()
                                            onActivated: vaydeerBridge.selectLayer(vaydeerBridge.layers[currentIndex].index)
                                            Accessible.name: "Select profile layer"
                                        }
                                        TextField {
                                            id: mappingLayerName
                                            Layout.preferredWidth: 146
                                            text: window.selectedLayerName()
                                            selectByMouse: true
                                            onEditingFinished: vaydeerBridge.renameLayer(text)
                                            Accessible.name: "Current layer name"
                                        }
                                        HintButton { ToolTip.text: "Layer names are stored with the profile and can be included in a verified device write." }
                                        Item { Layout.fillWidth: true }
                                        Button { text: "Add layer"; onClicked: vaydeerBridge.addLayer(); Accessible.name: "Add profile layer" }
                                        Button { text: "Duplicate"; onClicked: vaydeerBridge.duplicateLayer(); Accessible.name: "Duplicate current layer" }
                                        Button { text: "Remove"; enabled: vaydeerBridge.layers.length > 1; onClicked: vaydeerBridge.deleteLayer(); Accessible.name: "Remove current layer" }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 9
                                        Label {
                                            Layout.fillWidth: true
                                            text: vaydeerBridge.mappingKeySelectionStatus + "  |  " + vaydeerBridge.deviceBaseline + (vaydeerBridge.dirty ? "  |  Refresh keeps the draft until you discard or apply it." : "  |  The workspace shows the device state.")
                                            color: vaydeerBridge.dirty ? window.amber : window.muted
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                        Button {
                                            text: vaydeerBridge.dirty ? "Refresh baseline" : "Read device"
                                            onClicked: vaydeerBridge.readFromDevice()
                                            Accessible.name: "Read current device mappings without replacing pending changes"
                                        }
                                        Button { text: "Restore latest"; onClicked: { vaydeerBridge.restoreLatestBackup(); diffDialog.open() } }
                                        Button { text: "Discard"; enabled: vaydeerBridge.dirty; onClicked: vaydeerBridge.discardChanges() }
                                        Button { text: "Review changes"; enabled: vaydeerBridge.dirty; onClicked: { vaydeerBridge.previewApply(); diffDialog.open() } }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 500
                                spacing: 14
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true
                                            SectionTitle { text: "JP-1011 physical layout"; hint: "Vendor indexes follow reading order: top-left is key 1, bottom-right is key 9." }
                                            RowLayout {
                                                spacing: 9
                                                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: window.accent }
                                                Label { text: "Current on device"; color: window.muted; font.pixelSize: 11 }
                                                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: window.amber }
                                                Label { text: "Pending sync"; color: window.muted; font.pixelSize: 11 }
                                            }
                                        }
                                        DeviceKeypad {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            Layout.margins: 8
                                            keys: vaydeerBridge.keys
                                            selectedKey: vaydeerBridge.selectedKey.index
                                            columns: vaydeerBridge.layoutColumns
                                            interactive: true
                                            accent: window.accent
                                            pendingColor: window.amber
                                            showSyncState: true
                                            ink: window.ink
                                            muted: window.muted
                                            bodyColor: window.darkMode ? "#63717C" : "#9AA7AF"
                                            panelColor: window.darkMode ? "#111920" : "#E3EAED"
                                            onKeySelected: vaydeerBridge.selectKey(keyIndex)
                                        }
                                    }
                                }
                                Rectangle {
                                    Layout.preferredWidth: Math.max(330, Math.min(400, parent.width * 0.37))
                                    Layout.fillHeight: true
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        id: editorColumn
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 8
                                        property var actionModel: ["Keyboard key", "Key combination", "Modifier", "Media", "System control", "Disabled", "Mouse", "Macro", "Text", "Layer action", "Vaydeer action", "Linux host action"]
                                        function loadSelectedKey() {
                                            const current = vaydeerBridge.selectedKey
                                            categoryBox.currentIndex = Math.max(0, actionModel.indexOf(current.category))
                                            labelField.text = current.label
                                            codeField.text = current.codes
                                            shortcutCtrl.checked = current.codes.indexOf("Ctrl") !== -1
                                            shortcutShift.checked = current.codes.indexOf("Shift") !== -1
                                            shortcutAlt.checked = current.codes.indexOf("Alt") !== -1
                                            shortcutMeta.checked = current.codes.indexOf("Meta") !== -1
                                            detailField.text = current.actionData
                                            macroField.text = current.actionData
                                        }
                                        function updateShortcutModifiers() {
                                            if (categoryBox.currentText !== "Key combination")
                                                return
                                            let values = codeField.text.split("+").map(function(item) { return item.trim() }).filter(function(item) {
                                                return ["Ctrl", "Shift", "Alt", "Meta", ""].indexOf(item) === -1
                                            })
                                            let modifiers = []
                                            if (shortcutCtrl.checked) modifiers.push("Ctrl")
                                            if (shortcutShift.checked) modifiers.push("Shift")
                                            if (shortcutAlt.checked) modifiers.push("Alt")
                                            if (shortcutMeta.checked) modifiers.push("Meta")
                                            codeField.text = modifiers.concat(values).join(" + ")
                                        }
                                        Component.onCompleted: loadSelectedKey()
                                        Connections {
                                            target: vaydeerBridge
                                            function onSelectedKeyChanged() { editorColumn.loadSelectedKey() }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            SectionTitle { text: "Key " + (vaydeerBridge.selectedKey.index + 1); hint: "A key label is only a visual name. Its key value controls the actual on-device keyboard behavior." }
                                            StatusPill {
                                                label: vaydeerBridge.selectedKey.syncState
                                                statusColor: vaydeerBridge.selectedKey.pending ? window.amber : window.accent
                                            }
                                        }
                                        Label { text: "Action"; color: window.muted; font.pixelSize: 12 }
                                        ComboBox {
                                            id: categoryBox
                                            Layout.fillWidth: true
                                            model: editorColumn.actionModel
                                            Accessible.name: "Assignment action category"
                                        }
                                        Label { text: "Keypad label"; color: window.muted; font.pixelSize: 12 }
                                        TextField { id: labelField; Layout.fillWidth: true; placeholderText: "Optional label shown on the keypad"; selectByMouse: true; Accessible.name: "Selected key label" }
                                        Label { visible: ["Keyboard key", "Modifier", "Key combination", "Media", "System control"].indexOf(categoryBox.currentText) !== -1; text: categoryBox.currentText === "Key combination" ? "Shortcut values" : "Key value"; color: window.muted; font.pixelSize: 12 }
                                        RowLayout {
                                            visible: ["Keyboard key", "Modifier", "Key combination", "Media", "System control"].indexOf(categoryBox.currentText) !== -1
                                            Layout.fillWidth: true
                                            spacing: 7
                                            TextField {
                                                id: codeField
                                                Layout.fillWidth: true
                                                placeholderText: categoryBox.currentText === "Key combination" ? "Ctrl + Alt + P" : "Choose a value or capture a key"
                                                selectByMouse: true
                                                Accessible.name: "Explicit JP-1011 key value"
                                            }
                                            ComboBox {
                                                id: valuePicker
                                                Layout.preferredWidth: 132
                                                visible: vaydeerBridge.keyChoices(categoryBox.currentText).length > 0
                                                model: vaydeerBridge.keyChoices(categoryBox.currentText)
                                                displayText: "Choose value"
                                                currentIndex: -1
                                                onActivated: {
                                                    if (categoryBox.currentText === "Key combination") {
                                                        let modifiers = []
                                                        if (shortcutCtrl.checked) modifiers.push("Ctrl")
                                                        if (shortcutShift.checked) modifiers.push("Shift")
                                                        if (shortcutAlt.checked) modifiers.push("Alt")
                                                        if (shortcutMeta.checked) modifiers.push("Meta")
                                                        codeField.text = modifiers.concat([currentText]).join(" + ")
                                                    } else {
                                                        codeField.text = currentText
                                                    }
                                                }
                                                Accessible.name: "Choose a standard key value"
                                            }
                                            Button {
                                                text: vaydeerBridge.keyCaptureActive ? "Cancel capture" : "Capture a key"
                                                onClicked: {
                                                    if (vaydeerBridge.keyCaptureActive)
                                                        vaydeerBridge.cancelKeyCapture()
                                                    else {
                                                        vaydeerBridge.beginKeyCapture()
                                                        keyCaptureArea.forceActiveFocus()
                                                    }
                                                }
                                                Accessible.name: vaydeerBridge.keyCaptureActive ? "Cancel keyboard capture" : "Capture a value from the physical keyboard"
                                            }
                                        }
                                        Rectangle {
                                            id: keyCaptureArea
                                            visible: ["Keyboard key", "Modifier", "Key combination", "Media", "System control"].indexOf(categoryBox.currentText) !== -1
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: vaydeerBridge.keyCaptureActive ? 48 : 30
                                            focus: vaydeerBridge.keyCaptureActive
                                            color: vaydeerBridge.keyCaptureActive ? (window.darkMode ? "#203A3B" : "#D9EEEA") : window.panelRaised
                                            radius: 4
                                            border.width: 1
                                            border.color: vaydeerBridge.keyCaptureActive ? window.accent : window.line
                                            Keys.onPressed: function(event) {
                                                if (!vaydeerBridge.keyCaptureActive)
                                                    return
                                                vaydeerBridge.captureKeyInput(event.key, event.modifiers)
                                                codeField.text = vaydeerBridge.keyCaptureValue
                                                event.accepted = true
                                            }
                                            Column {
                                                anchors.fill: parent
                                                anchors.margins: 7
                                                spacing: 2
                                                Label {
                                                    width: parent.width
                                                    text: vaydeerBridge.keyCaptureActive ? "Capturing next keyboard key" : "Key capture"
                                                    color: vaydeerBridge.keyCaptureActive ? window.ink : window.muted
                                                    font.bold: vaydeerBridge.keyCaptureActive
                                                    font.pixelSize: 11
                                                }
                                                Label {
                                                    width: parent.width
                                                    text: vaydeerBridge.keyCaptureHint
                                                    color: window.muted
                                                    font.pixelSize: 10
                                                    elide: Text.ElideRight
                                                }
                                            }
                                            Accessible.name: "Keyboard capture status"
                                            Accessible.description: vaydeerBridge.keyCaptureHint
                                        }
                                        RowLayout {
                                            visible: categoryBox.currentText === "Key combination"
                                            Layout.fillWidth: true
                                            spacing: 8
                                            Label { text: "Modifiers"; color: window.muted; font.pixelSize: 11 }
                                            CheckBox { id: shortcutCtrl; text: "Ctrl"; onToggled: editorColumn.updateShortcutModifiers() }
                                            CheckBox { id: shortcutShift; text: "Shift"; onToggled: editorColumn.updateShortcutModifiers() }
                                            CheckBox { id: shortcutAlt; text: "Alt"; onToggled: editorColumn.updateShortcutModifiers() }
                                            CheckBox { id: shortcutMeta; text: "Meta"; onToggled: editorColumn.updateShortcutModifiers() }
                                        }
                                        Label {
                                            visible: vaydeerBridge.selectedKey.deviceLabel.length > 0
                                            text: vaydeerBridge.selectedKey.pending ? "On device: " + vaydeerBridge.selectedKey.deviceLabel + "  |  Draft: " + vaydeerBridge.selectedKey.value : "On device: " + vaydeerBridge.selectedKey.deviceLabel
                                            color: vaydeerBridge.selectedKey.pending ? window.amber : window.muted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                        ColumnLayout {
                                            visible: categoryBox.currentText === "Macro"
                                            Layout.fillWidth: true
                                            spacing: 6
                                            Label { text: window.actionDataLabel(categoryBox.currentText); color: window.muted; font.pixelSize: 12 }
                                            Label {
                                                Layout.fillWidth: true
                                                text: "Recorded macros are kept in this portable profile. Their on-device payload is not verified, so they are never sent to the keypad."
                                                color: window.amber
                                                wrapMode: Text.WordWrap
                                                font.pixelSize: 11
                                            }
                                            TextArea {
                                                id: macroField
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 64
                                                placeholderText: "Ctrl+C; Wait 120; Ctrl+V"
                                                wrapMode: TextEdit.Wrap
                                                selectByMouse: true
                                                Accessible.name: "Manual macro steps"
                                            }
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Button { text: vaydeerBridge.macroRecording ? "Recording keyboard" : "Record keyboard"; enabled: !vaydeerBridge.macroRecording; onClicked: { vaydeerBridge.startMacroRecording(); macroCapture.forceActiveFocus() } Accessible.name: "Start macro recording from the computer keyboard" }
                                                Button { text: "Stop"; enabled: vaydeerBridge.macroRecording; onClicked: vaydeerBridge.stopMacroRecording(); Accessible.name: "Stop macro recording" }
                                                Button { text: "Clear"; onClicked: vaydeerBridge.clearMacroRecording(); Accessible.name: "Clear captured macro steps" }
                                                Item { Layout.fillWidth: true }
                                            }
                                            Rectangle {
                                                id: macroCapture
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: vaydeerBridge.macroRecording ? 52 : 34
                                                focus: vaydeerBridge.macroRecording
                                                color: vaydeerBridge.macroRecording ? (window.darkMode ? "#203A3B" : "#D9EEEA") : window.panelRaised
                                                radius: 4
                                                border.color: vaydeerBridge.macroRecording ? window.accent : window.line
                                                Keys.onPressed: function(event) { vaydeerBridge.recordMacroInput(event.key, event.modifiers, true); event.accepted = true }
                                                Keys.onReleased: function(event) { vaydeerBridge.recordMacroInput(event.key, event.modifiers, false); event.accepted = true }
                                                Column {
                                                    anchors.fill: parent
                                                    anchors.margins: 7
                                                    spacing: 2
                                                    Label { width: parent.width; text: vaydeerBridge.macroRecording ? "Recording computer keyboard input" : "Macro recorder"; color: vaydeerBridge.macroRecording ? window.ink : window.muted; font.bold: vaydeerBridge.macroRecording; font.pixelSize: 11 }
                                                    Label { width: parent.width; text: vaydeerBridge.macroRecording ? "Type the sequence now. Delays of 50 ms or more are preserved." : (vaydeerBridge.macroSteps.length ? vaydeerBridge.macroSteps.length + " captured steps. You can save or clear them." : "Record a keyboard sequence, then save it into the profile."); color: window.muted; font.pixelSize: 10; elide: Text.ElideRight }
                                                }
                                            }
                                            Label {
                                                visible: vaydeerBridge.macroSteps.length > 0
                                                Layout.fillWidth: true
                                                text: "Recorded sequence: " + vaydeerBridge.macroSteps.map(function(step) { return step.label }).join(" -> ")
                                                color: window.muted
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }
                                        TextField {
                                            id: detailField
                                            visible: categoryBox.currentText !== "Macro" && ["Keyboard key", "Modifier", "Key combination", "Media", "System control", "Disabled"].indexOf(categoryBox.currentText) === -1
                                            Layout.fillWidth: true
                                            placeholderText: window.actionDataLabel(categoryBox.currentText)
                                            selectByMouse: true
                                            Accessible.name: window.actionDataLabel(categoryBox.currentText)
                                        }
                                        Label {
                                            visible: categoryBox.currentText !== "Disabled"
                                            Layout.fillWidth: true
                                            text: vaydeerBridge.selectedKey.notes.length > 0 && categoryBox.currentText === vaydeerBridge.selectedKey.category ? vaydeerBridge.selectedKey.notes : window.actionState(categoryBox.currentText)
                                            color: window.actionState(categoryBox.currentText) === "Stored on device" ? window.muted : window.amber
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 11
                                        }
                                        Item { Layout.fillHeight: true }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Button { text: "Open bindings"; visible: categoryBox.currentText === "Linux host action"; onClicked: { window.navIndex = 2; vaydeerBridge.setActivePage(2) } }
                                            Item { Layout.fillWidth: true }
                                            Button { text: "Save to draft"; onClicked: vaydeerBridge.saveKey(categoryBox.currentText, labelField.text, codeField.text, categoryBox.currentText === "Macro" ? macroField.text : detailField.text); Accessible.name: "Save selected key to the on-device mapping draft" }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Linux bindings
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 48)
                            x: 24
                            y: 20
                            spacing: 14
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "Linux bindings"; hint: "These actions need the Vaydeer Studio user service. They are intentionally separate from onboard mappings." }
                                Label { text: "Profile: " + vaydeerBridge.profileName; color: window.muted; font.pixelSize: 12 }
                                StatusPill { label: vaydeerBridge.profileTargetPlatformLabel; statusColor: vaydeerBridge.profileSupportsLinuxBindings ? window.accent : window.amber }
                                StatusPill { label: vaydeerBridge.service.running ? "Service running" : "Service stopped"; statusColor: vaydeerBridge.service.running ? window.accent : window.danger }
                                StatusPill { label: vaydeerBridge.service.startup ? "Starts at login" : "Manual start"; statusColor: vaydeerBridge.service.startup ? window.accent : window.amber }
                            }
                            Label {
                                visible: !vaydeerBridge.profileSupportsLinuxBindings
                                Layout.fillWidth: true
                                text: "This profile targets " + vaydeerBridge.profileTargetPlatformLabel + ". It can contain portable on-device mappings, but Linux-side bindings are not loaded into vaydeer-studiod. Select Linux on the Profiles page to edit or run host actions."
                                color: window.amber
                                wrapMode: Text.WordWrap
                                font.pixelSize: 11
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 360
                                spacing: 14
                                Rectangle {
                                    Layout.preferredWidth: Math.max(290, parent.width * 0.33)
                                    Layout.fillHeight: true
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        spacing: 8
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: "Binding target"; color: window.ink; font.bold: true; Layout.fillWidth: true }
                                            ComboBox {
                                                id: bindingLayerCombo
                                                Layout.preferredWidth: 142
                                                model: vaydeerBridge.layers
                                                textRole: "displayName"
                                                currentIndex: window.layerIndexForSelected()
                                                onActivated: vaydeerBridge.selectLayer(vaydeerBridge.layers[currentIndex].index)
                                                enabled: !vaydeerBridge.bindingEditor.editing
                                                Accessible.name: "Select binding layer"
                                            }
                                        }
                                        DeviceKeypad {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            keys: vaydeerBridge.keys
                                            selectedKey: vaydeerBridge.selectedKey.index
                                            columns: vaydeerBridge.layoutColumns
                                            interactive: !vaydeerBridge.bindingEditor.editing
                                            accent: window.accent
                                            pendingColor: window.amber
                                            ink: window.ink
                                            muted: window.muted
                                            bodyColor: window.darkMode ? "#63717C" : "#9AA7AF"
                                            panelColor: window.darkMode ? "#111920" : "#E3EAED"
                                            onKeySelected: vaydeerBridge.selectKey(keyIndex)
                                        }
                                        Label { text: "Key " + (vaydeerBridge.selectedKey.index + 1) + " on " + bindingLayerCombo.currentText; color: window.muted; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; font.pixelSize: 12 }
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 8
                                        id: bindingForm
                                        enabled: vaydeerBridge.profileSupportsLinuxBindings
                                        function loadEditor() {
                                            const editor = vaydeerBridge.bindingEditor
                                            bindingAction.currentIndex = Math.max(0, bindingAction.model.indexOf(editor.action))
                                            bindingTarget.text = editor.target
                                            bindingArguments.text = editor.arguments
                                            bindingTrigger.currentIndex = Math.max(0, bindingTrigger.model.indexOf(editor.trigger))
                                            allowShell.checked = editor.allowShell
                                            bindingWindow.text = editor.activeWindowPattern
                                        }
                                        Component.onCompleted: loadEditor()
                                        Connections {
                                            target: vaydeerBridge
                                            function onChanged() { bindingForm.loadEditor() }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            SectionTitle { text: vaydeerBridge.bindingEditor.editing ? "Edit binding" : "New binding"; hint: "Commands use a program plus parsed argument array. Shell interpretation stays disabled unless explicitly enabled." }
                                            Button { text: "New"; onClicked: vaydeerBridge.newBinding(); Accessible.name: "Create a new Linux binding for the selected key" }
                                        }
                                        Label {
                                            Layout.fillWidth: true
                                            text: "K" + (vaydeerBridge.bindingEditor.keyIndex + 1) + " on layer " + (vaydeerBridge.bindingEditor.layerIndex + 1) + (!vaydeerBridge.bindingEditor.supported ? "  |  This trigger is retained but not executed; saving converts it to the selected trigger." : (vaydeerBridge.bindingEditor.editing ? "  |  Target is fixed while editing." : "  |  Only press and release are currently executed by the service."))
                                            color: vaydeerBridge.bindingEditor.supported ? window.muted : window.amber
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 11
                                        }
                                        GridLayout {
                                            Layout.fillWidth: true
                                            columns: 2
                                            rowSpacing: 8
                                            columnSpacing: 10
                                            Label { text: "Action"; color: window.muted; font.pixelSize: 12 }
                                            ComboBox { id: bindingAction; Layout.fillWidth: true; model: ["application", "url", "file", "directory", "command", "notification", "script", "text"]; Accessible.name: "Linux binding action" }
                                            Label { text: "Target"; color: window.muted; font.pixelSize: 12 }
                                            TextField { id: bindingTarget; Layout.fillWidth: true; placeholderText: window.bindingTargetHint(bindingAction.currentText); selectByMouse: true; Accessible.name: "Linux binding target" }
                                            Label { text: "Arguments"; color: window.muted; font.pixelSize: 12 }
                                            TextField { id: bindingArguments; Layout.fillWidth: true; placeholderText: "--option \"quoted value\""; selectByMouse: true; Accessible.name: "Linux binding argument array" }
                                            Label { text: "Trigger"; color: window.muted; font.pixelSize: 12 }
                                            ComboBox { id: bindingTrigger; Layout.fillWidth: true; model: ["press", "release"]; Accessible.name: "Linux binding trigger" }
                                            Label { text: "Active window"; color: window.muted; font.pixelSize: 12 }
                                            TextField { id: bindingWindow; Layout.fillWidth: true; placeholderText: "Optional title or app pattern"; selectByMouse: true; Accessible.name: "Active window pattern" }
                                        }
                                        CheckBox { id: allowShell; visible: bindingAction.currentText === "command"; text: "Allow shell execution"; Accessible.name: "Allow shell execution for this binding" }
                                        Label { visible: bindingAction.currentText === "text"; text: "Text injection is retained in the profile and can be tested in mock mode; a desktop text backend is required for real execution."; color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
                                        Item { Layout.fillHeight: true }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Item { Layout.fillWidth: true }
                                            Button {
                                                text: vaydeerBridge.bindingEditor.editing ? "Save binding" : "Add binding"
                                                onClicked: vaydeerBridge.saveBinding(bindingAction.currentText, bindingTarget.text, bindingArguments.text, bindingTrigger.currentText, allowShell.checked, bindingWindow.text)
                                                Accessible.name: "Save Linux-side binding for selected key"
                                            }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.max(130, bindingsList.contentHeight + 58)
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { text: "Bindings in this profile"; hint: "Bindings are synchronized to the user service when it is reachable." }
                                        Label { text: vaydeerBridge.service.reachable ? "Synced to local service" : "Saved in profile; service unavailable"; color: vaydeerBridge.service.reachable ? window.muted : window.amber; font.pixelSize: 11 }
                                    }
                                    ListView {
                                        id: bindingsList
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        clip: true
                                        model: vaydeerBridge.bindings
                                        spacing: 5
                                        delegate: Rectangle {
                                            required property var modelData
                                            required property int index
                                            width: ListView.view.width
                                            height: 46
                                            color: index % 2 ? "transparent" : window.panelRaised
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 10
                                                anchors.rightMargin: 8
                                                spacing: 10
                                                CheckBox { checked: modelData.enabled; onToggled: vaydeerBridge.setBindingEnabled(index, checked); Accessible.name: "Enable binding " + (index + 1) }
                                                Label { text: "K" + (modelData.key_index + 1); color: window.ink; font.bold: true; Layout.preferredWidth: 28 }
                                                Label { text: "Layer " + (modelData.layer_index + 1); color: window.muted; Layout.preferredWidth: 58; font.pixelSize: 12 }
                                                Label { text: modelData.trigger + " " + modelData.action; color: modelData.supported ? window.ink : window.amber; Layout.preferredWidth: 132; elide: Text.ElideRight }
                                                Label { text: modelData.target; color: window.muted; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                                Label { visible: !modelData.supported; text: "Not executed"; color: window.amber; font.pixelSize: 11 }
                                                Button { text: "Run"; enabled: vaydeerBridge.mockMode; onClicked: vaydeerBridge.runBinding(index); Accessible.name: "Run mock binding " + (index + 1) }
                                                Button { text: "Edit"; onClicked: vaydeerBridge.editBinding(index); Accessible.name: "Edit binding " + (index + 1) }
                                                Button { text: "Remove"; onClicked: vaydeerBridge.removeBinding(index); Accessible.name: "Remove binding " + (index + 1) }
                                            }
                                        }
                                        footer: Label { visible: vaydeerBridge.bindings.length === 0; text: "No Linux-side bindings in this profile."; color: window.muted; padding: 8 }
                                    }
                                }
                            }
                        }
                    }
                }

                // Profiles
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 48)
                            x: 24
                            y: 20
                            spacing: 14
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "Profiles"; hint: "Profiles hold portable on-device mapping drafts, layers, and Linux-side bindings." }
                                StatusPill { label: vaydeerBridge.dirty ? vaydeerBridge.pendingMappingCount + " mapping changes" : "Matches device"; statusColor: vaydeerBridge.dirty ? window.amber : window.accent }
                                StatusPill { label: vaydeerBridge.profileDirty ? "Local save needed" : "Saved locally"; statusColor: vaydeerBridge.profileDirty ? window.amber : window.accent }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 218
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 9
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Profile name"; color: window.muted; font.pixelSize: 12 }
                                        TextField { id: profileNameField; Layout.fillWidth: true; text: vaydeerBridge.profileName; selectByMouse: true; onEditingFinished: vaydeerBridge.renameProfile(text); Accessible.name: "Current profile name" }
                                        Label { text: "Target"; color: window.muted; font.pixelSize: 12 }
                                        ComboBox {
                                            id: profileTargetPlatform
                                            Layout.preferredWidth: 110
                                            model: vaydeerBridge.profilePlatforms
                                            textRole: "label"
                                            valueRole: "id"
                                            currentIndex: {
                                                for (let i = 0; i < model.length; ++i) {
                                                    if (model[i].id === vaydeerBridge.profileTargetPlatform)
                                                        return i
                                                }
                                                return 0
                                            }
                                            onActivated: vaydeerBridge.setProfileTargetPlatform(currentValue)
                                            Accessible.name: "Profile target operating system"
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Button { text: "Save local"; onClicked: vaydeerBridge.saveProfile(); Accessible.name: "Save current profile locally" }
                                        Button { text: "New"; onClicked: vaydeerBridge.createProfile(); Accessible.name: "Create new profile" }
                                        Button { text: "Duplicate"; onClicked: vaydeerBridge.duplicateProfile(); Accessible.name: "Duplicate current profile" }
                                        ComboBox { id: profileExportFormat; Layout.preferredWidth: 78; model: ["JSON", "YAML"]; Accessible.name: "Profile export format" }
                                        Button { text: "Export"; onClicked: vaydeerBridge.exportProfile(profileExportFormat.currentText.toLowerCase()); Accessible.name: "Export current profile" }
                                        Button { text: "Delete"; onClicked: vaydeerBridge.deleteProfile(); Accessible.name: "Delete current profile" }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Start from preset"; color: window.muted; font.pixelSize: 12 }
                                        ComboBox {
                                            id: profilePreset
                                            Layout.fillWidth: true
                                            model: vaydeerBridge.profileTemplates
                                            textRole: "name"
                                            valueRole: "id"
                                            Accessible.name: "Application profile preset"
                                        }
                                        Label {
                                            visible: window.width > 1180
                                            Layout.preferredWidth: 260
                                            text: profilePreset.currentIndex >= 0 ? vaydeerBridge.profileTemplates[profilePreset.currentIndex].summary : ""
                                            color: window.muted
                                            font.pixelSize: 10
                                            elide: Text.ElideRight
                                        }
                                        Button {
                                            text: "Create preset"
                                            enabled: profilePreset.currentIndex >= 0
                                            onClicked: vaydeerBridge.createProfileFromTemplate(profilePreset.currentValue, profileTargetPlatform.currentValue)
                                            Accessible.name: "Create profile from application preset"
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextField { id: importProfilePath; Layout.fillWidth: true; placeholderText: "Profile JSON or YAML path"; selectByMouse: true; Accessible.name: "Profile import path" }
                                        Button { text: "Import"; onClicked: vaydeerBridge.importProfile(importProfilePath.text); Accessible.name: "Import profile" }
                                        Button { text: vaydeerBridge.dirty ? "Refresh device baseline" : "Read device"; onClicked: vaydeerBridge.readFromDevice(); Accessible.name: "Read device profile without overwriting pending mappings" }
                                        Button { text: "Use device state"; enabled: vaydeerBridge.dirty; onClicked: vaydeerBridge.discardChanges(); Accessible.name: "Discard pending mappings and use device state" }
                                    }
                                    Label { text: vaydeerBridge.profileOrigin + "  |  Target: " + vaydeerBridge.profileTargetPlatformLabel + "  |  App: " + vaydeerBridge.profileTargetApplication + "  |  " + vaydeerBridge.deviceBaseline + (vaydeerBridge.dirty ? "  |  Device refresh preserves pending changes." : ""); color: vaydeerBridge.dirty ? window.amber : window.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: width > 920 ? 3 : 1
                                rowSpacing: 12
                                columnSpacing: 12
                                Repeater {
                                    model: [["Device baseline", "JP-1011 / " + vaydeerBridge.keys.length + " keys"], ["Layers", vaydeerBridge.layers.length + " configured"], ["Target", vaydeerBridge.profileTargetPlatformLabel + " / " + vaydeerBridge.profileTargetApplication]]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 86
                                        color: window.panel
                                        radius: 6
                                        border.color: window.line
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 13
                                            Label { text: modelData[0]; color: window.muted; font.pixelSize: 12 }
                                            Label { text: modelData[1]; color: window.ink; font.bold: true; font.pixelSize: 17 }
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 300
                                spacing: 14
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        spacing: 8
                                        SectionTitle { text: "Profile layers"; hint: "Use On-device mappings to edit assignments and manage layers." }
                                        ListView {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            clip: true
                                            model: vaydeerBridge.layers
                                            delegate: Button {
                                                required property var modelData
                                                width: ListView.view.width
                                                height: 42
                                                text: modelData.displayName
                                                checkable: true
                                                checked: modelData.selected
                                                onClicked: vaydeerBridge.selectLayer(modelData.index)
                                                Accessible.name: "Select " + text
                                            }
                                        }
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        spacing: 8
                                        SectionTitle { text: "Saved profiles"; hint: "Saved profiles are local and use the versioned portable profile schema." }
                                        ListView {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            clip: true
                                            model: vaydeerBridge.savedProfiles
                                            spacing: 5
                                            delegate: Button {
                                                required property var modelData
                                                width: ListView.view.width
                                                height: 52
                                                onClicked: vaydeerBridge.loadSavedProfile(modelData.id)
                                                Accessible.name: "Load saved profile " + modelData.name
                                                background: Rectangle {
                                                    radius: 4
                                                    color: modelData.active ? (window.darkMode ? "#203A3B" : "#D9EEEA") : (index % 2 ? "transparent" : window.panelRaised)
                                                    border.color: modelData.active ? window.accent : "transparent"
                                                    border.width: modelData.active ? 1 : 0
                                                }
                                                contentItem: RowLayout {
                                                    anchors.fill: parent
                                                    anchors.margins: 8
                                                    spacing: 8
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 1
                                                        Label { text: modelData.name; color: window.ink; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                                        Label { text: modelData.platform + " / " + modelData.application + "  |  " + modelData.layers + " layers  |  " + modelData.bindings + " bindings  |  " + modelData.updated; color: window.muted; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                                    }
                                                    StatusPill { visible: modelData.active; label: "Current"; statusColor: window.accent }
                                                }
                                            }
                                            footer: Label { visible: vaydeerBridge.savedProfiles.length === 0; text: "No saved profiles yet."; color: window.muted; padding: 5 }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Live key tester
                Item {
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 14
                        Rectangle {
                            Layout.preferredWidth: Math.max(335, parent.width * 0.34)
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.line
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 9
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "Live key tester"; hint: "The service listens through the same read-only vendor event interface used for Linux activation. It does not record key events while this screen is closed." }
                                    StatusPill { label: vaydeerBridge.mockMode ? "Mock" : "Listening"; statusColor: window.accent }
                                }
                                Label { text: vaydeerBridge.mockMode ? "Click a physical key to generate a press and release." : vaydeerBridge.testerStatus; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                DeviceKeypad {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.margins: 6
                                    keys: vaydeerBridge.keys
                                    pressedKeys: vaydeerBridge.testerPressedKeys
                                    selectedKey: vaydeerBridge.selectedKey.index
                                    columns: vaydeerBridge.layoutColumns
                                    interactive: vaydeerBridge.mockMode
                                    simulateOnClick: vaydeerBridge.mockMode
                                    accent: window.accent
                                    ink: window.ink
                                    muted: window.muted
                                    bodyColor: window.darkMode ? "#63717C" : "#9AA7AF"
                                    panelColor: window.darkMode ? "#111920" : "#E3EAED"
                                    onKeySelected: vaydeerBridge.selectKey(keyIndex)
                                    onKeyActivated: vaydeerBridge.simulateKey(keyIndex)
                                }
                                Label { text: "Vendor reports: fb 03 layer key state xor"; color: window.muted; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.line
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Vendor event reports"; color: window.ink; font.bold: true; font.pixelSize: 17; Layout.fillWidth: true }
                                    Label { text: vaydeerBridge.testerEvents.length + " events"; color: window.muted; font.pixelSize: 12 }
                                }
                                ListView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: vaydeerBridge.testerEvents
                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        width: ListView.view.width
                                        height: 40
                                        color: index % 2 ? "transparent" : window.panelRaised
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            spacing: 8
                                            Label { text: modelData.timestamp; color: window.muted; Layout.preferredWidth: 110; font.pixelSize: 12 }
                                            Label { text: modelData.key ? "K" + modelData.key : "Unknown"; color: window.ink; Layout.preferredWidth: 54; font.bold: true }
                                            Label { text: modelData.event; color: modelData.event === "Press" ? window.accent : window.muted; Layout.preferredWidth: 58 }
                                            Label { text: modelData.layer ? "Layer " + modelData.layer : "Unknown layer"; color: window.muted; Layout.preferredWidth: 82; font.pixelSize: 12 }
                                            Label { text: modelData.raw; color: window.muted; font.family: "monospace"; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                    }
                                    footer: Label { visible: vaydeerBridge.testerEvents.length === 0; text: "No key events yet."; color: window.muted; padding: 10 }
                                }
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
                            SectionTitle { text: "Diagnostics"; hint: "Exports omit serial numbers, home paths, vendor binaries, and raw installers." }
                            Button { text: "Refresh"; onClicked: vaydeerBridge.refreshDiagnostics() }
                            Button { text: "Copy summary"; onClicked: vaydeerBridge.copyDiagnosticSummary() }
                            Button { text: "Export diagnostics"; onClicked: vaydeerBridge.exportDiagnostics() }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 12
                            Repeater {
                                model: [["Command interface", "Interface 0 / vendor configuration"], ["Keepalive interface", "Interface 2 / read-only"], ["Keepalive status", vaydeerBridge.device.keepalive], ["Permission status", vaydeerBridge.device.permissions]]
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 82
                                    color: window.panel
                                    radius: 6
                                    border.color: window.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 13
                                        Label { text: modelData[0]; color: window.muted; font.pixelSize: 12 }
                                        Label { text: modelData[1]; color: window.ink; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: window.panel
                            radius: 6
                            border.color: window.line
                            Label { anchors.fill: parent; anchors.margins: 16; text: vaydeerBridge.diagnosticSummary; color: window.muted; wrapMode: Text.WordWrap; verticalAlignment: Text.AlignTop; font.family: "monospace" }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            color: window.panel
            border.color: window.line
            border.width: 1
            Label { anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16; text: vaydeerBridge.statusMessage; color: window.muted; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; font.pixelSize: 11 }
        }
    }
}
