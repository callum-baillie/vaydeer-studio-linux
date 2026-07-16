import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    id: window
    visible: true
    width: 1440
    height: 900
    minimumWidth: 1024
    minimumHeight: 680
    title: "Vaydeer Studio"
    color: appBackground

    Settings {
        id: appPreferences
        objectName: "appPreferences"
        category: "ui"
        property bool darkMode: true
        property bool advancedMode: false
        property int page: 0
    }

    // Small design-token set used by the shell and all new surfaces.
    property bool darkMode: appPreferences.darkMode
    property bool advancedMode: appPreferences.advancedMode
    property int navIndex: appPreferences.page
    property color appBackground: darkMode ? "#10171D" : "#F4F7F8"
    property color surface: darkMode ? "#172129" : "#FFFFFF"
    property color raisedSurface: darkMode ? "#202D36" : "#EAF0F2"
    property color primaryText: darkMode ? "#E8EEF2" : "#18242D"
    property color secondaryText: darkMode ? "#A9B8C2" : "#5C6E79"
    property color disabledText: darkMode ? "#6E7E89" : "#8A9AA4"
    property color border: darkMode ? "#33414C" : "#D3DEE3"
    property color accent: "#1AAE99"
    property color info: "#4D91D0"
    property color amber: "#C98B2C"
    property color danger: "#C64F57"
    property color ink: primaryText
    property color muted: secondaryText
    property color panel: surface
    property color panelRaised: raisedSurface
    property color line: border
    property int space4: 4
    property int space8: 8
    property int space12: 12
    property int space16: 16
    property int controlHeight: 36
    property int panelRadius: 6
    property var primaryPagesModel: ["Overview", "On-device keys", "Linux actions", "Profiles", "Live tester", "Diagnostics", "Setup"]
    property int setupPageIndex: 6
    property int helpPageIndex: 7

    palette.button: raisedSurface
    palette.buttonText: primaryText
    palette.base: surface
    palette.text: primaryText
    palette.window: appBackground
    palette.windowText: primaryText
    palette.highlight: accent
    palette.highlightedText: "#FFFFFF"

    Shortcut {
        sequence: "Ctrl+S"
        onActivated: vaydeerBridge.saveProfile()
    }
    Shortcut {
        sequence: "Ctrl+R"
        onActivated: vaydeerBridge.readFromDevice()
    }

    function navigate(index) {
        const safeIndex = Math.max(0, Math.min(index, helpPageIndex))
        appPreferences.page = safeIndex
        navIndex = safeIndex
        vaydeerBridge.setActivePage(safeIndex)
    }

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

    function bindingTargetLabel(action) {
        if (action === "application") return "Application"
        if (action === "url") return "URL"
        if (action === "file") return "File"
        if (action === "directory") return "Folder"
        if (action === "command") return "Executable"
        if (action === "notification") return "Message"
        if (action === "script") return "Script"
        if (action === "text") return "Text"
        return "Target"
    }

    function setupLabel(label) {
        const labels = {
            "Mock keypad": "Keypad detected",
            "Vaydeer device": "Keypad detected",
            "Command interface": "Keypad command access",
            "Command interface 0": "Keypad command access",
            "Keepalive interface": "Linux activation interface",
            "Keepalive interface 2": "Linux activation interface",
            "Command access": "Permission to configure the keypad",
            "Command interface access": "Permission to configure the keypad",
            "Keepalive access": "Permission for Linux activation",
            "Keepalive interface access": "Permission for Linux activation",
            "udev rule": "Device permissions rule",
            "Vaydeer udev rule": "Device permissions rule",
            "User service": "Background service",
            "Protocol read": "Device information read",
            "Device information": "Device information read"
        }
        return labels[label] || label
    }

    function setupDetail(label, status) {
        if (status === "pass")
            return "Ready"
        if (label === "udev rule")
            return "Install or refresh the Vaydeer permissions rule, then reconnect the keypad."
        if (label === "User service")
            return "Install and start the Background service to enable Linux actions."
        return "Needs attention. Run diagnostics or follow Setup guidance."
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
        Label { text: parent.text; color: window.ink; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
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

    component PageHeader: ColumnLayout {
        property string title: ""
        property string subtitle: ""
        property string status: ""
        Layout.fillWidth: true
        spacing: 3
        RowLayout {
            Layout.fillWidth: true
            Label { text: parent.parent.title; color: window.primaryText; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
            Label { visible: parent.parent.status.length > 0; text: parent.parent.status; color: window.secondaryText; font.pixelSize: 12; elide: Text.ElideRight }
        }
        Label { visible: parent.subtitle.length > 0; text: parent.subtitle; color: window.secondaryText; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }

    component InfoBanner: Rectangle {
        property string title: ""
        property string body: ""
        property color bannerColor: window.info
        Layout.fillWidth: true
        implicitHeight: bannerContent.implicitHeight + 24
        color: Qt.rgba(bannerColor.r, bannerColor.g, bannerColor.b, window.darkMode ? 0.12 : 0.09)
        radius: window.panelRadius
        border.width: 1
        border.color: Qt.rgba(bannerColor.r, bannerColor.g, bannerColor.b, 0.42)
        ColumnLayout {
            id: bannerContent
            anchors.fill: parent
            anchors.margins: 12
            spacing: 3
            Label { text: parent.parent.title; color: parent.parent.bannerColor; font.bold: true; font.pixelSize: 13 }
            Label { text: parent.parent.body; color: window.primaryText; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
        }
    }

    component HealthStatusRow: RowLayout {
        property string title: ""
        property string detail: ""
        property string state: "ready"
        Layout.fillWidth: true
        spacing: 10
        Rectangle {
            Layout.preferredWidth: 8
            Layout.preferredHeight: 8
            radius: 4
            color: parent.state === "error" ? window.danger : parent.state === "warning" ? window.amber : parent.state === "info" ? window.info : window.accent
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            Label { text: parent.parent.title; color: window.primaryText; font.bold: true; font.pixelSize: 13 }
            Label { text: parent.parent.detail; color: window.secondaryText; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }

    component EmptyState: ColumnLayout {
        property string title: ""
        property string body: ""
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
        spacing: 6
        Label { text: parent.title; color: window.primaryText; font.pixelSize: 16; font.bold: true; Layout.alignment: Qt.AlignHCenter }
        Label { text: parent.body; color: window.secondaryText; font.pixelSize: 13; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.alignment: Qt.AlignHCenter; Layout.maximumWidth: 420 }
    }

    component PrimaryButton: Button {
        property color buttonColor: window.accent
        implicitHeight: window.controlHeight
        font.bold: true
        Accessible.name: text
        contentItem: Label {
            text: parent.text
            color: "#FFFFFF"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.bold: true
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 5
            color: parent.enabled ? (parent.down ? Qt.darker(parent.buttonColor, 1.12) : parent.buttonColor) : window.disabledText
            border.color: parent.activeFocus ? "#FFFFFF" : "transparent"
            border.width: parent.activeFocus ? 1 : 0
        }
    }

    component SecondaryButton: Button {
        implicitHeight: window.controlHeight
        Accessible.name: text
        contentItem: Label {
            text: parent.text
            color: parent.enabled ? window.primaryText : window.disabledText
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 5
            color: parent.down ? Qt.darker(window.raisedSurface, 1.08) : window.raisedSurface
            border.color: parent.activeFocus ? window.accent : window.border
            border.width: 1
        }
    }

    component ScopeExplainer: Rectangle {
        id: scopeExplainer
        property string deviceText: ""
        property string hostText: ""
        property string note: ""
        Layout.fillWidth: true
        implicitHeight: scopeContent.implicitHeight + 28
        color: window.darkMode ? "#14292C" : "#E7F3F1"
        radius: 6
        border.width: 1
        border.color: window.darkMode ? "#2C5A59" : "#B8DCD6"

        ColumnLayout {
            id: scopeContent
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: "Where this works"
                    color: window.ink
                    font.bold: true
                    font.pixelSize: 13
                }
                Label {
                    visible: scopeExplainer.note.length > 0
                    text: scopeExplainer.note
                    color: window.muted
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 14
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Label { text: "On the macro keypad"; color: window.accent; font.bold: true; font.pixelSize: 12 }
                    Label {
                        text: scopeExplainer.deviceText
                        color: window.ink
                        wrapMode: Text.WordWrap
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 50
                    color: window.line
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Label { text: "On this Linux computer"; color: window.info; font.bold: true; font.pixelSize: 12 }
                    Label {
                        text: scopeExplainer.hostText
                        color: window.ink
                        wrapMode: Text.WordWrap
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }

    Dialog {
        id: diffDialog
        objectName: "diffDialog"
        title: "Review keypad write"
        modal: true
        width: Math.min(window.width - 72, 760)
        height: Math.min(window.height - 110, 580)
        anchors.centerIn: parent
        padding: 14
        header: Rectangle {
            implicitHeight: 48
            color: window.panelRaised
            border.width: 1
            border.color: window.line
            Label {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                text: diffDialog.title
                color: window.ink
                font.pixelSize: 15
                font.bold: true
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
        background: Rectangle {
            color: window.panel
            radius: 6
            border.width: 1
            border.color: window.line
        }
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: vaydeerBridge.previewLines.length === 0 ? "No keypad mapping changes are staged." : "These changes will be stored on the physical keypad. A timestamped backup is created first, then Studio reads the keypad back to verify the write."
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
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: window.darkMode ? "#111920" : "#F7F9FA"
                radius: 4
                border.width: 1
                border.color: window.line
                ListView {
                    anchors.fill: parent
                    anchors.margins: 1
                    clip: true
                    model: vaydeerBridge.previewLines
                    ScrollBar.vertical: ScrollBar { }
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
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
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Close"; onClicked: diffDialog.close() }
                PrimaryButton {
                    text: vaydeerBridge.mockMode ? "Write to mock keypad" : "Continue to confirmation"
                    enabled: vaydeerBridge.previewLines.length > 0
                    onClicked: {
                        if (vaydeerBridge.mockMode) {
                            vaydeerBridge.applyConfirmedPreview()
                            diffDialog.close()
                        } else {
                            diffDialog.close()
                            hardwareWriteDialog.open()
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: hardwareWriteDialog
        objectName: "hardwareWriteDialog"
        title: "Confirm write to keypad"
        modal: true
        width: Math.min(window.width - 72, 600)
        anchors.centerIn: parent
        padding: 14
        closePolicy: Popup.CloseOnEscape
        onOpened: {
            hardwareWritePhrase.text = ""
            hardwareWritePhrase.forceActiveFocus()
        }
        header: Rectangle {
            implicitHeight: 48
            color: window.panelRaised
            border.width: 1
            border.color: window.line
            Label {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                text: hardwareWriteDialog.title
                color: window.ink
                font.pixelSize: 15
                font.bold: true
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
        background: Rectangle {
            color: window.panel
            radius: 6
            border.width: 1
            border.color: window.line
        }
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: "This stores the reviewed mappings in the connected keypad's memory, then reads them back for verification."
                color: window.ink
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                text: "Backup retained at: " + vaydeerBridge.backupPath
                color: window.muted
                wrapMode: Text.WrapAnywhere
                Layout.fillWidth: true
            }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: confirmationCopy.implicitHeight + 20
                color: Qt.rgba(window.amber.r, window.amber.g, window.amber.b, window.darkMode ? 0.13 : 0.1)
                border.width: 1
                border.color: Qt.rgba(window.amber.r, window.amber.g, window.amber.b, 0.5)
                radius: 4
                Label {
                    id: confirmationCopy
                    anchors.fill: parent
                    anchors.margins: 10
                    text: "Type APPLY to confirm this hardware write. Firmware, bootloader, and unknown commands are never sent."
                    color: window.ink
                    wrapMode: Text.WordWrap
                }
            }
            TextField {
                id: hardwareWritePhrase
                Layout.fillWidth: true
                placeholderText: "Type APPLY"
                selectByMouse: true
                Accessible.name: "Type APPLY to confirm the device write"
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: hardwareWriteDialog.close() }
                PrimaryButton {
                    text: "Write to keypad"
                    enabled: hardwareWritePhrase.text.trim() === "APPLY"
                    Accessible.name: "Confirm and write reviewed mappings to the keypad"
                    onClicked: {
                        hardwareWriteDialog.close()
                        vaydeerBridge.applyConfirmedPreview()
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        if (navIndex < 0 || navIndex > helpPageIndex)
            navigate(0)
        else
            vaydeerBridge.setActivePage(navIndex)
    }

    Item {
        anchors.fill: parent

        Rectangle {
            id: appBar
            objectName: "appBar"
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 64
            z: 100
            color: window.panel
            border.color: window.line
            border.width: 1
            Item {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                Label {
                    id: appTitle
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Vaydeer Studio"
                    color: window.primaryText
                    font.pixelSize: 20
                    font.bold: true
                }
                Label {
                    anchors.left: appTitle.right
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Keypad configuration"
                    color: window.secondaryText
                    font.pixelSize: 13
                }
                RowLayout {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    height: parent.height
                    spacing: 12
                    StatusPill {
                        label: vaydeerBridge.connection.connected ? "Keypad ready" : "Keypad offline"
                        statusColor: vaydeerBridge.connection.connected ? window.accent : window.danger
                    }
                    StatusPill {
                        label: vaydeerBridge.service.running && vaydeerBridge.service.reachable ? "Service ready" : "Service needs attention"
                        statusColor: vaydeerBridge.service.running && vaydeerBridge.service.reachable ? window.info : window.amber
                    }
                    SecondaryButton {
                        text: window.advancedMode ? "Advanced" : "Basic"
                        onClicked: appPreferences.advancedMode = !appPreferences.advancedMode
                        Accessible.name: window.advancedMode ? "Switch to Basic mode" : "Switch to Advanced mode"
                        ToolTip.visible: hovered
                        ToolTip.text: "Basic hides low-level device details. Advanced shows them."
                    }
                    SecondaryButton {
                        text: window.darkMode ? "Light" : "Dark"
                        onClicked: appPreferences.darkMode = !window.darkMode
                        Accessible.name: "Switch application color theme"
                    }
                }
            }
        }

        RowLayout {
            anchors.top: appBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 218
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                color: window.darkMode ? "#131C23" : "#EAF0F2"
                border.color: window.line
                border.width: 1
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    Repeater {
                        model: window.primaryPagesModel
                        delegate: Button {
                            required property string modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: window.controlHeight
                            text: modelData
                            checkable: true
                            checked: window.navIndex === index
                            Accessible.name: modelData
                            onClicked: window.navigate(index)
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
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: window.controlHeight
                        text: "Help"
                        checkable: true
                        checked: window.navIndex === window.helpPageIndex
                        Accessible.name: "Help"
                        onClicked: window.navigate(window.helpPageIndex)
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
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label { text: "Active profile"; color: window.secondaryText; font.pixelSize: 11 }
                        Label { text: vaydeerBridge.profileName; color: window.primaryText; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        Label { text: vaydeerBridge.dirty ? "Keypad draft has changes" : "Matches current keypad state"; color: vaydeerBridge.dirty ? window.amber : window.secondaryText; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                }
            }

            StackLayout {
                id: pages
                objectName: "mainPages"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                Layout.alignment: Qt.AlignTop
                currentIndex: window.navIndex
                onCurrentIndexChanged: {
                    if (currentIndex === 5)
                        vaydeerBridge.refreshDiagnostics()
                }

                // Overview
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 56)
                            x: 28
                            y: 24
                            spacing: window.space16
                            PageHeader {
                                title: "Overview"
                                subtitle: "Choose whether you want to change keypad memory or Linux-only actions."
                                status: "Profile: " + vaydeerBridge.profileName
                            }
                            InfoBanner {
                                visible: !vaydeerBridge.connection.connected
                                title: vaydeerBridge.connection.title
                                body: vaydeerBridge.connection.message + " " + vaydeerBridge.connection.recovery
                                bannerColor: window.danger
                            }
                            InfoBanner {
                                visible: vaydeerBridge.connection.connected && (!vaydeerBridge.service.running || !vaydeerBridge.service.reachable)
                                title: "Background service needs attention"
                                body: "The keypad can still keep its stored mappings, but Linux actions and reliable Linux keyboard activation need the Background service running."
                                bannerColor: window.amber
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 172
                                spacing: window.space12
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: window.surface
                                    radius: window.panelRadius
                                    border.color: Qt.rgba(window.accent.r, window.accent.g, window.accent.b, 0.55)
                                    border.width: 1
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: window.space16
                                        spacing: window.space8
                                        Label { text: "Configure keypad memory"; color: window.accent; font.pixelSize: 17; font.bold: true }
                                        Label { text: "Stored on the keypad. Works on any compatible computer after writing. The Background service is not required."; color: window.primaryText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        Item { Layout.fillHeight: true }
                                        PrimaryButton { text: "Open on-device keys"; onClicked: window.navigate(1); Layout.preferredWidth: 190 }
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: window.surface
                                    radius: window.panelRadius
                                    border.color: Qt.rgba(window.info.r, window.info.g, window.info.b, 0.55)
                                    border.width: 1
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: window.space16
                                        spacing: window.space8
                                        Label { text: "Configure Linux actions"; color: window.info; font.pixelSize: 17; font.bold: true }
                                        Label { text: "Stored on this Linux computer. The Background service runs these actions and keeps the keypad active on Linux."; color: window.primaryText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        Item { Layout.fillHeight: true }
                                        PrimaryButton { text: "Open Linux actions"; buttonColor: window.info; onClicked: window.navigate(2); Layout.preferredWidth: 184 }
                                    }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 216
                                color: window.surface
                                radius: window.panelRadius
                                border.color: window.border
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: window.space16
                                    spacing: 20
                                    DeviceKeypad {
                                        objectName: "deviceOverviewKeypad"
                                        Layout.preferredWidth: 176
                                        Layout.preferredHeight: 176
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
                                        spacing: 10
                                        HealthStatusRow {
                                            title: vaydeerBridge.connection.connected ? "Keypad connected" : "Keypad not detected"
                                            detail: vaydeerBridge.connection.connected ? vaydeerBridge.device.model + " with " + vaydeerBridge.device.keyCount + " keys." : vaydeerBridge.connection.message
                                            state: vaydeerBridge.connection.connected ? "ready" : "error"
                                        }
                                        HealthStatusRow {
                                            title: "Background service"
                                            detail: vaydeerBridge.service.detail
                                            state: vaydeerBridge.service.running && vaydeerBridge.service.reachable ? "info" : "warning"
                                        }
                                        HealthStatusRow {
                                            title: "Active profile"
                                            detail: vaydeerBridge.profileName + (vaydeerBridge.dirty ? " has keypad changes waiting to be written." : " matches the current keypad state.")
                                            state: vaydeerBridge.dirty ? "warning" : "ready"
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Item { Layout.fillWidth: true }
                                            SecondaryButton { text: "Setup"; onClicked: window.navigate(window.setupPageIndex) }
                                            SecondaryButton { text: "Run diagnostics"; onClicked: window.navigate(5) }
                                            PrimaryButton {
                                                visible: !vaydeerBridge.connection.connected
                                                text: "Reconnect keypad"
                                                onClicked: vaydeerBridge.reconnectDevice()
                                            }
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 18
                                Label { text: "Firmware " + vaydeerBridge.device.firmware; color: window.secondaryText; font.pixelSize: 12 }
                                Label { text: "Bootloader " + vaydeerBridge.device.bootloader; color: window.secondaryText; font.pixelSize: 12 }
                                Label { text: vaydeerBridge.device.layerCount + " layer" + (vaydeerBridge.device.layerCount === 1 ? "" : "s") + " in profile"; color: window.secondaryText; font.pixelSize: 12 }
                                Label { text: "Host: " + vaydeerBridge.service.host; color: window.secondaryText; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
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
                            PageHeader {
                                title: "On-device keys"
                                subtitle: "Read the keypad, edit a draft, review changes, then write the draft to keypad memory."
                                status: vaydeerBridge.dirty ? vaydeerBridge.pendingMappingCount + " changes waiting to be written" : "Matches keypad"
                            }
                            ScopeExplainer {
                                deviceText: "Supported keys, layers, and layer names are stored in keypad memory after a reviewed, confirmed write. They work on any compatible computer."
                                hostText: "Vaydeer Studio holds edits as a local draft until you write them. The Background service is not needed once these mappings are stored."
                                note: "Profile: " + vaydeerBridge.profileName
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 96
                                color: window.panel
                                radius: window.panelRadius
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
                                        HintButton { ToolTip.text: "Layer names are included when you write the reviewed draft to the keypad." }
                                        Item { Layout.fillWidth: true }
                                        SecondaryButton { text: "Add layer"; onClicked: vaydeerBridge.addLayer(); Accessible.name: "Add profile layer" }
                                        SecondaryButton { text: "Duplicate"; onClicked: vaydeerBridge.duplicateLayer(); Accessible.name: "Duplicate current layer" }
                                        SecondaryButton { text: "Remove"; enabled: vaydeerBridge.layers.length > 1; onClicked: vaydeerBridge.deleteLayer(); Accessible.name: "Remove current layer" }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 9
                                        Label {
                                            Layout.fillWidth: true
                                            text: vaydeerBridge.mappingKeySelectionStatus + " " + (vaydeerBridge.dirty ? "Draft changes are safe until you write them." : vaydeerBridge.deviceBaseline)
                                            color: vaydeerBridge.dirty ? window.amber : window.muted
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                        SecondaryButton { text: "Review changes"; enabled: vaydeerBridge.dirty; onClicked: { vaydeerBridge.previewApply(); diffDialog.open() } }
                                        PrimaryButton { text: "Write to keypad"; enabled: vaydeerBridge.dirty; onClicked: { vaydeerBridge.previewApply(); diffDialog.open() } }
                                        SecondaryButton { text: "More actions"; onClicked: mappingActionsMenu.open() }
                                    }
                                }
                                Menu {
                                    id: mappingActionsMenu
                                    MenuItem {
                                        text: vaydeerBridge.dirty ? "Refresh keypad baseline" : "Read from keypad"
                                        onTriggered: vaydeerBridge.readFromDevice()
                                    }
                                    MenuItem {
                                        text: "Restore latest backup"
                                        onTriggered: { vaydeerBridge.restoreLatestBackup(); diffDialog.open() }
                                    }
                                    MenuSeparator { }
                                    MenuItem {
                                        text: "Discard keypad draft"
                                        enabled: vaydeerBridge.dirty
                                        onTriggered: vaydeerBridge.discardChanges()
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
                                            objectName: "mappingKeypad"
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
                                            onKeySelected: function(keyIndex) { vaydeerBridge.selectKey(keyIndex) }
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
                                        property var basicActionModel: ["Keyboard key", "Key combination", "Modifier", "Media", "System control", "Disabled"]
                                        property var advancedActionModel: ["Mouse", "Macro", "Text", "Layer action", "Vaydeer action", "Linux host action"]
                                        property var actionModel: window.advancedMode ? basicActionModel.concat(advancedActionModel) : basicActionModel
                                        function loadSelectedKey() {
                                            const current = vaydeerBridge.selectedKey
                                            const categoryIndex = actionModel.indexOf(current.category)
                                            categoryBox.currentIndex = categoryIndex >= 0 ? categoryIndex : 0
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
                                            SectionTitle { text: "Key " + (vaydeerBridge.selectedKey.index + 1); hint: "Edit the draft for this physical key. Nothing is written until you review and confirm a keypad write." }
                                            StatusPill {
                                                label: vaydeerBridge.selectedKey.syncState
                                                statusColor: vaydeerBridge.selectedKey.pending ? window.amber : window.accent
                                            }
                                        }
                                        Label { text: "Action type"; color: window.muted; font.pixelSize: 12 }
                                        ComboBox {
                                            id: categoryBox
                                            Layout.fillWidth: true
                                            model: editorColumn.actionModel
                                            Accessible.name: "Assignment action category"
                                        }
                                        Label { text: "Keypad label"; color: window.muted; font.pixelSize: 12 }
                                        TextField { id: labelField; Layout.fillWidth: true; placeholderText: "Optional label shown in Studio"; selectByMouse: true; Accessible.name: "Selected key label" }
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
                                            PrimaryButton {
                                                text: vaydeerBridge.keyCaptureActive ? "Cancel" : "Capture key"
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
                                            Layout.preferredHeight: 46
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
                                                    text: vaydeerBridge.keyCaptureActive ? "Press a key on your computer" : "Capture from computer keyboard"
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
                                            text: vaydeerBridge.selectedKey.pending ? "Keypad now: " + vaydeerBridge.selectedKey.deviceLabel + "   Draft: " + vaydeerBridge.selectedKey.value : "Stored on keypad: " + vaydeerBridge.selectedKey.deviceLabel
                                            color: vaydeerBridge.selectedKey.pending ? window.amber : window.muted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                        ColumnLayout {
                                            visible: window.advancedMode && categoryBox.currentText === "Macro"
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
                                            visible: window.advancedMode && categoryBox.currentText !== "Macro" && ["Keyboard key", "Modifier", "Key combination", "Media", "System control", "Disabled"].indexOf(categoryBox.currentText) === -1
                                            Layout.fillWidth: true
                                            placeholderText: window.actionDataLabel(categoryBox.currentText)
                                            selectByMouse: true
                                            Accessible.name: window.actionDataLabel(categoryBox.currentText)
                                        }
                                        Label {
                                            visible: categoryBox.currentText !== "Disabled" && (window.advancedMode || ["Keyboard key", "Modifier", "Key combination", "Media", "System control"].indexOf(categoryBox.currentText) !== -1)
                                            Layout.fillWidth: true
                                            text: vaydeerBridge.selectedKey.notes.length > 0 && categoryBox.currentText === vaydeerBridge.selectedKey.category ? vaydeerBridge.selectedKey.notes : window.actionState(categoryBox.currentText)
                                            color: window.actionState(categoryBox.currentText) === "Stored on device" ? window.muted : window.amber
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 11
                                        }
                                        Item { Layout.fillHeight: true }
                                        Label {
                                            visible: window.advancedMode
                                            Layout.fillWidth: true
                                            text: "Advanced: documented value " + (codeField.text.length > 0 ? codeField.text : "none") + "  |  category " + categoryBox.currentText
                                            color: window.secondaryText
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            SecondaryButton { text: "Open Linux actions"; visible: window.advancedMode && categoryBox.currentText === "Linux host action"; onClicked: window.navigate(2) }
                                            Item { Layout.fillWidth: true }
                                            PrimaryButton { text: "Save to draft"; onClicked: vaydeerBridge.saveKey(categoryBox.currentText, labelField.text, codeField.text, categoryBox.currentText === "Macro" ? macroField.text : detailField.text); Accessible.name: "Save selected key to the on-device mapping draft" }
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
                            PageHeader {
                                title: "Linux actions"
                                subtitle: "Create actions for this Linux computer without changing keypad memory."
                                status: vaydeerBridge.service.running && vaydeerBridge.service.reachable ? "Background service ready" : "Background service unavailable"
                            }
                            InfoBanner {
                                title: "Runs on this Linux computer"
                                body: "Linux actions are saved in the profile, then synchronized to the Background service. They run only while that service is available and are never written to the keypad."
                                bannerColor: window.info
                            }
                            InfoBanner {
                                visible: !vaydeerBridge.profileSupportsLinuxBindings
                                title: "This profile does not target Linux"
                                body: "The profile targets " + vaydeerBridge.profileTargetPlatformLabel + ". Its portable keypad mappings are still available, but Linux actions are not loaded on this computer. Change the profile target to Linux to edit actions."
                                bannerColor: window.amber
                            }
                            InfoBanner {
                                visible: vaydeerBridge.profileSupportsLinuxBindings && (!vaydeerBridge.service.running || !vaydeerBridge.service.reachable)
                                title: "Background service is not ready"
                                body: "You can edit and save actions, but they will not run until the Background service is started in Setup."
                                bannerColor: window.amber
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
                                        Label { text: "Choose key and layer"; color: window.ink; font.bold: true; Layout.fillWidth: true }
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
                                            objectName: "bindingKeypad"
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
                                            onKeySelected: function(keyIndex) { vaydeerBridge.selectKey(keyIndex) }
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
                                            for (let index = 0; index < bindingAction.model.length; index++) {
                                                if (bindingAction.model[index].id === editor.action) {
                                                    bindingAction.currentIndex = index
                                                    break
                                                }
                                            }
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
                                            SectionTitle { text: vaydeerBridge.bindingEditor.editing ? "Edit Linux action" : "New Linux action"; hint: "Commands use a program plus parsed argument array. Shell interpretation stays disabled unless explicitly enabled." }
                                            SecondaryButton { text: "New action"; onClicked: vaydeerBridge.newBinding(); Accessible.name: "Create a new Linux action for the selected key" }
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
                                            ComboBox {
                                                id: bindingAction
                                                Layout.fillWidth: true
                                                model: [
                                                    { "label": "Launch application", "id": "application" },
                                                    { "label": "Open URL", "id": "url" },
                                                    { "label": "Open file", "id": "file" },
                                                    { "label": "Open folder", "id": "directory" },
                                                    { "label": "Run command", "id": "command" },
                                                    { "label": "Show notification", "id": "notification" },
                                                    { "label": "Run script", "id": "script" },
                                                    { "label": "Type text", "id": "text" }
                                                ]
                                                textRole: "label"
                                                valueRole: "id"
                                                Accessible.name: "Linux action type"
                                            }
                                            Label { text: window.bindingTargetLabel(bindingAction.currentValue); color: window.muted; font.pixelSize: 12 }
                                            TextField { id: bindingTarget; Layout.fillWidth: true; placeholderText: window.bindingTargetHint(bindingAction.currentValue); selectByMouse: true; Accessible.name: "Linux action target" }
                                            Label { visible: ["application", "command", "script"].indexOf(bindingAction.currentValue) !== -1 || window.advancedMode; text: "Arguments"; color: window.muted; font.pixelSize: 12 }
                                            TextField { visible: ["application", "command", "script"].indexOf(bindingAction.currentValue) !== -1 || window.advancedMode; id: bindingArguments; Layout.fillWidth: true; placeholderText: "--option \"quoted value\""; selectByMouse: true; Accessible.name: "Linux action argument array" }
                                            Label { text: "Trigger"; color: window.muted; font.pixelSize: 12 }
                                            ComboBox { id: bindingTrigger; Layout.fillWidth: true; model: ["press", "release"]; Accessible.name: "Linux binding trigger" }
                                            Label { visible: window.advancedMode; text: "Active window"; color: window.muted; font.pixelSize: 12 }
                                            TextField { visible: window.advancedMode; id: bindingWindow; Layout.fillWidth: true; placeholderText: "Optional title or app pattern"; selectByMouse: true; Accessible.name: "Active window pattern" }
                                        }
                                        CheckBox { id: allowShell; visible: window.advancedMode && bindingAction.currentValue === "command"; text: "Allow shell execution"; Accessible.name: "Allow shell execution for this action" }
                                        InfoBanner { visible: window.advancedMode && bindingAction.currentValue === "command" && allowShell.checked; title: "Shell execution enabled"; body: "The Background service will run this command through a shell. Prefer a direct executable with separate arguments when possible."; bannerColor: window.amber }
                                        Label { visible: bindingAction.currentValue === "text"; text: "Software text is kept in the profile. Its real execution needs a desktop text backend; mock mode can test the action safely."; color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
                                        Item { Layout.fillHeight: true }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Item { Layout.fillWidth: true }
                                            PrimaryButton {
                                                text: "Save action"
                                                buttonColor: window.info
                                                onClicked: vaydeerBridge.saveBinding(bindingAction.currentValue, bindingTarget.text, bindingArguments.text, bindingTrigger.currentText, allowShell.checked, bindingWindow.text)
                                                Accessible.name: "Save Linux action for selected key"
                                            }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.max(176, bindingsList.contentHeight + 58)
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { text: "Linux actions in this profile"; hint: "Saving an action synchronizes it to the Background service when that service is reachable." }
                                        Label { text: vaydeerBridge.service.reachable ? "Saved and synchronized" : "Saved locally; service unavailable"; color: vaydeerBridge.service.reachable ? window.secondaryText : window.amber; font.pixelSize: 12 }
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
                                                Label { text: modelData.trigger + " · " + modelData.action; color: modelData.supported ? window.ink : window.amber; Layout.preferredWidth: 132; elide: Text.ElideRight }
                                                Label { text: modelData.target; color: window.muted; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                                Label { visible: !modelData.supported; text: "Not executed"; color: window.amber; font.pixelSize: 11 }
                                                SecondaryButton { text: "Test"; visible: vaydeerBridge.mockMode; onClicked: vaydeerBridge.runBinding(index); Accessible.name: "Test mock Linux action " + (index + 1) }
                                                SecondaryButton { text: "Edit"; onClicked: vaydeerBridge.editBinding(index); Accessible.name: "Edit Linux action " + (index + 1) }
                                                SecondaryButton { text: "Remove"; onClicked: vaydeerBridge.removeBinding(index); Accessible.name: "Remove Linux action " + (index + 1) }
                                            }
                                        }
                                        footer: Item {
                                            visible: vaydeerBridge.bindings.length === 0
                                            width: bindingsList.width
                                            height: 118
                                            EmptyState { anchors.centerIn: parent; title: "No Linux actions yet"; body: "Choose a keypad key, select an action type, then save it for this Linux computer." }
                                        }
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
                            PageHeader {
                                title: "Profiles"
                                subtitle: "Profiles are local, portable configuration files. Selecting one never writes it to the keypad automatically."
                                status: vaydeerBridge.profileDirty ? "Local save needed" : "Saved locally"
                            }
                            ScopeExplainer {
                                deviceText: "A profile can contain keypad mappings and layers. Saving a profile keeps a draft; writing its mappings to keypad memory remains a separate confirmed action."
                                hostText: "A Linux-targeted profile can also carry Linux actions for the Background service. macOS and Windows profiles remain portable configuration files."
                                note: vaydeerBridge.dirty ? vaydeerBridge.pendingMappingCount + " keypad changes waiting to be written" : "Matches keypad baseline"
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
                                        PrimaryButton { text: "Save profile"; onClicked: vaydeerBridge.saveProfile(); Accessible.name: "Save current profile locally" }
                                        SecondaryButton { text: "New profile"; onClicked: vaydeerBridge.createProfile(); Accessible.name: "Create new profile" }
                                        SecondaryButton { text: "Duplicate"; onClicked: vaydeerBridge.duplicateProfile(); Accessible.name: "Duplicate current profile" }
                                        ComboBox { visible: window.advancedMode; id: profileExportFormat; Layout.preferredWidth: 78; model: ["JSON", "YAML"]; Accessible.name: "Profile export format" }
                                        SecondaryButton { text: "Export"; onClicked: vaydeerBridge.exportProfile(window.advancedMode ? profileExportFormat.currentText.toLowerCase() : "json"); Accessible.name: "Export current profile" }
                                        SecondaryButton { text: "Delete"; onClicked: vaydeerBridge.deleteProfile(); Accessible.name: "Delete current profile" }
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
                                        PrimaryButton {
                                            text: "Create preset"
                                            enabled: profilePreset.currentIndex >= 0
                                            onClicked: vaydeerBridge.createProfileFromTemplate(profilePreset.currentValue, profileTargetPlatform.currentValue)
                                            Accessible.name: "Create profile from application preset"
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextField { id: importProfilePath; Layout.fillWidth: true; placeholderText: "Profile JSON or YAML path"; selectByMouse: true; Accessible.name: "Profile import path" }
                                        SecondaryButton { text: "Import"; onClicked: vaydeerBridge.importProfile(importProfilePath.text); Accessible.name: "Import profile" }
                                        SecondaryButton { text: vaydeerBridge.dirty ? "Refresh keypad baseline" : "Read from keypad"; onClicked: vaydeerBridge.readFromDevice(); Accessible.name: "Read device profile without overwriting pending mappings" }
                                        SecondaryButton { text: "Use keypad state"; enabled: vaydeerBridge.dirty; onClicked: vaydeerBridge.discardChanges(); Accessible.name: "Discard pending mappings and use keypad state" }
                                    }
                                    Label { text: vaydeerBridge.profileOrigin + "  |  Target: " + vaydeerBridge.profileTargetPlatformLabel + "  |  App: " + vaydeerBridge.profileTargetApplication + "  |  " + vaydeerBridge.deviceBaseline + (vaydeerBridge.dirty ? "  |  Device refresh preserves pending changes." : ""); color: vaydeerBridge.dirty ? window.amber : window.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 86
                                color: window.panel
                                radius: window.panelRadius
                                border.color: window.line
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: window.space16
                                    spacing: 18
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Label { text: "On-device content"; color: window.accent; font.bold: true; font.pixelSize: 13 }
                                        Label { text: vaydeerBridge.keys.length + " keys · " + vaydeerBridge.layers.length + " layers · " + (vaydeerBridge.dirty ? "draft differs from keypad" : "matches keypad"); color: window.primaryText; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }
                                    Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 46; color: window.line }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Label { text: "Linux-only content"; color: window.info; font.bold: true; font.pixelSize: 13 }
                                        Label { text: vaydeerBridge.bindings.length + " actions · target " + vaydeerBridge.profileTargetPlatformLabel + " · " + (vaydeerBridge.profileSupportsLinuxBindings ? "available on this host" : "not active on this host"); color: window.primaryText; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
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
                                        SectionTitle { text: "On-device layers"; hint: "Use On-device keys to edit assignments and manage layers." }
                                        ListView {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            clip: true
                                            model: vaydeerBridge.layers
                                            delegate: Button {
                                                required property var modelData
                                                required property int index
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
                                        SectionTitle { text: "Saved profiles"; hint: "Saved profiles are local portable files. Loading one does not write it to the keypad." }
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
                    id: testerPage
                    property bool paused: false
                    property int selectedEventIndex: -1
                    onVisibleChanged: {
                        if (visible)
                            paused = false
                    }
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 14
                        PageHeader {
                            title: "Live tester"
                            subtitle: "Read-only event testing. This screen never changes keypad settings."
                            status: testerPage.paused ? "Listening paused" : (vaydeerBridge.mockMode ? "Mock keypad" : "Listening")
                        }
                        ScopeExplainer {
                            deviceText: "The keypad sends physical press and release events. Testing is read-only and does not change stored mappings, layers, or profiles."
                            hostText: "The Background service provides the read-only event stream on Linux. Existing Linux actions need the service, but not the Studio window."
                            note: "Press a keypad key to begin testing."
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
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
                                    SectionTitle { text: "Keypad"; hint: "The Background service listens through the same read-only vendor event interface used for Linux activation. It does not record events after you leave this screen." }
                                    StatusPill { label: testerPage.paused ? "Paused" : (vaydeerBridge.mockMode ? "Mock" : "Listening"); statusColor: testerPage.paused ? window.amber : window.accent }
                                }
                                Label { text: testerPage.paused ? "Listening is paused. Start listening to resume event capture." : (vaydeerBridge.mockMode ? "Click a key to generate a mock press and release." : vaydeerBridge.testerStatus); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                DeviceKeypad {
                                    objectName: "testerKeypad"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.margins: 6
                                    keys: vaydeerBridge.keys
                                    pressedKeys: vaydeerBridge.testerPressedKeys
                                    selectedKey: vaydeerBridge.selectedKey.index
                                    columns: vaydeerBridge.layoutColumns
                                    interactive: vaydeerBridge.mockMode && !testerPage.paused
                                    simulateOnClick: vaydeerBridge.mockMode && !testerPage.paused
                                    accent: window.accent
                                    ink: window.ink
                                    muted: window.muted
                                    bodyColor: window.darkMode ? "#63717C" : "#9AA7AF"
                                    panelColor: window.darkMode ? "#111920" : "#E3EAED"
                                    onKeySelected: function(keyIndex) { vaydeerBridge.selectKey(keyIndex) }
                                    onKeyActivated: function(keyIndex) { vaydeerBridge.simulateKey(keyIndex) }
                                }
                                Label { visible: window.advancedMode; text: "Vendor reports: fb 03 layer key state xor"; color: window.muted; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
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
                                    Label { text: "Event history"; color: window.ink; font.bold: true; font.pixelSize: 17; Layout.fillWidth: true }
                                    Label { text: vaydeerBridge.testerEvents.length + " events"; color: window.muted; font.pixelSize: 12 }
                                    SecondaryButton {
                                        text: testerPage.paused ? "Start listening" : "Pause"
                                        onClicked: {
                                            testerPage.paused = !testerPage.paused
                                            vaydeerBridge.setTesterOpen(!testerPage.paused)
                                        }
                                    }
                                    SecondaryButton { text: "Clear"; enabled: vaydeerBridge.testerEvents.length > 0; onClicked: { testerPage.selectedEventIndex = -1; vaydeerBridge.clearTesterEvents() } }
                                    SecondaryButton { text: "Copy"; enabled: testerPage.selectedEventIndex >= 0; onClicked: vaydeerBridge.copyTesterEvent(testerPage.selectedEventIndex) }
                                    SecondaryButton { text: "Export"; enabled: vaydeerBridge.testerEvents.length > 0; onClicked: vaydeerBridge.exportTesterSession() }
                                }
                                ListView {
                                    id: testerEventList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: vaydeerBridge.testerEvents
                                    delegate: Button {
                                        required property var modelData
                                        required property int index
                                        width: ListView.view.width
                                        height: 40
                                        checkable: true
                                        checked: testerPage.selectedEventIndex === index
                                        onClicked: testerPage.selectedEventIndex = index
                                        Accessible.name: modelData.timestamp + ", " + (modelData.key ? "key " + modelData.key : "unknown key") + ", " + modelData.event
                                        background: Rectangle {
                                            color: parent.checked ? Qt.rgba(window.info.r, window.info.g, window.info.b, window.darkMode ? 0.18 : 0.12) : (index % 2 ? "transparent" : window.panelRaised)
                                            border.color: parent.activeFocus || parent.checked ? window.info : "transparent"
                                            border.width: parent.activeFocus || parent.checked ? 1 : 0
                                        }
                                        contentItem: RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            spacing: 8
                                            Label { text: modelData.timestamp; color: window.muted; Layout.preferredWidth: 110; font.pixelSize: 12 }
                                            Label { text: modelData.key ? "K" + modelData.key : "Unknown"; color: window.ink; Layout.preferredWidth: 54; font.bold: true }
                                            Label { text: modelData.event; color: modelData.event === "Press" ? window.accent : window.muted; Layout.preferredWidth: 58 }
                                            Label { text: modelData.layer ? "Layer " + modelData.layer : "Unknown layer"; color: window.muted; Layout.preferredWidth: 82; font.pixelSize: 12 }
                                            Label { text: modelData.source; color: window.muted; Layout.fillWidth: true; font.pixelSize: 12; elide: Text.ElideRight }
                                            Label { visible: window.advancedMode; text: modelData.raw; color: window.muted; font.family: "monospace"; Layout.preferredWidth: 192; elide: Text.ElideRight }
                                        }
                                    }
                                    footer: Item {
                                        visible: vaydeerBridge.testerEvents.length === 0
                                        width: testerEventList.width
                                        height: 150
                                        EmptyState { anchors.centerIn: parent; title: "Press a keypad key to begin testing"; body: testerPage.paused ? "Start listening to see physical keypad events." : "Press and release events will appear here. Select an event to copy a readable summary." }
                                    }
                                }
                            }
                            }
                        }
                    }
                }

                // Diagnostics
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 56)
                            x: 28
                            y: 24
                            spacing: window.space16
                            PageHeader {
                                title: "Diagnostics"
                                subtitle: "Check keypad connection, permissions, and the Background service. Exports are sanitized."
                                status: vaydeerBridge.connection.connected && vaydeerBridge.service.running && vaydeerBridge.service.reachable ? "Healthy" : "Needs attention"
                            }
                            InfoBanner {
                                visible: !vaydeerBridge.connection.connected
                                title: "Keypad not detected"
                                body: "Reconnect the USB cable or try another port, then run diagnostics again."
                                bannerColor: window.danger
                            }
                            InfoBanner {
                                visible: vaydeerBridge.connection.connected && (!vaydeerBridge.service.running || !vaydeerBridge.service.reachable)
                                title: "Background service stopped or unavailable"
                                body: "Start the service in Setup to enable Linux actions and keepalive support."
                                bannerColor: window.amber
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                PrimaryButton { text: "Run diagnostics"; onClicked: vaydeerBridge.refreshDiagnostics() }
                                SecondaryButton { text: "Copy summary"; onClicked: vaydeerBridge.copyDiagnosticSummary() }
                                SecondaryButton { text: "Export diagnostics"; onClicked: vaydeerBridge.exportDiagnostics() }
                                Item { Layout.fillWidth: true }
                                SecondaryButton { text: "Setup"; onClicked: window.navigate(window.setupPageIndex) }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: diagnosticRows.implicitHeight + 32
                                color: window.panel
                                radius: window.panelRadius
                                border.color: window.line
                                ColumnLayout {
                                    id: diagnosticRows
                                    anchors.fill: parent
                                    anchors.margins: window.space16
                                    spacing: 12
                                    SectionTitle { text: "Health summary"; hint: "Use Setup for guided repair steps. Advanced mode includes technical detail below." }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: width > 820 ? 2 : 1
                                        rowSpacing: 12
                                        columnSpacing: 24
                                        HealthStatusRow {
                                            title: "Keypad connection"
                                            detail: vaydeerBridge.connection.connected ? vaydeerBridge.device.model + " is connected and readable." : vaydeerBridge.connection.message
                                            state: vaydeerBridge.connection.connected ? "ready" : "error"
                                        }
                                        HealthStatusRow {
                                            title: "Background service"
                                            detail: vaydeerBridge.service.detail
                                            state: vaydeerBridge.service.running && vaydeerBridge.service.reachable ? "info" : "warning"
                                        }
                                        Repeater {
                                            model: vaydeerBridge.setupChecks.filter(function(item) { return item.label !== "User service" })
                                            delegate: HealthStatusRow {
                                                required property var modelData
                                                title: window.setupLabel(modelData.label)
                                                detail: window.setupDetail(modelData.label, modelData.status)
                                                state: modelData.status === "pass" ? "ready" : modelData.status === "warn" ? "warning" : "error"
                                            }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                objectName: "advancedDiagnosticsPanel"
                                visible: window.advancedMode
                                Layout.fillWidth: true
                                implicitHeight: advancedDiagnostics.implicitHeight + 32
                                color: window.panel
                                radius: window.panelRadius
                                border.color: window.line
                                ColumnLayout {
                                    id: advancedDiagnostics
                                    anchors.fill: parent
                                    anchors.margins: window.space16
                                    spacing: window.space8
                                    SectionTitle { text: "Technical details"; hint: "Raw information is shown only in Advanced mode." }
                                    Label { text: vaydeerBridge.diagnosticSummary; color: window.secondaryText; wrapMode: Text.WrapAnywhere; font.family: "monospace"; font.pixelSize: 11; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }

                // Setup
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 56)
                            x: 28
                            y: 24
                            spacing: window.space16
                            PageHeader {
                                title: "Setup"
                                subtitle: "Prepare this Linux computer to keep the keypad active and run Linux actions."
                                status: vaydeerBridge.service.running ? "Background service running" : "Setup needed"
                            }
                            InfoBanner {
                                title: "What Setup changes"
                                body: "Setup verifies the keypad, permissions, and Background service. It never changes keypad mappings or firmware."
                                bannerColor: window.info
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: setupRows.implicitHeight + 32
                                color: window.surface
                                radius: window.panelRadius
                                border.color: window.border
                                ColumnLayout {
                                    id: setupRows
                                    anchors.fill: parent
                                    anchors.margins: window.space16
                                    spacing: 12
                                    SectionTitle { text: "Setup checklist"; hint: "Each step is safe to repeat. Permissions changes require reconnecting the keypad." }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: width > 820 ? 2 : 1
                                        rowSpacing: 12
                                        columnSpacing: 24
                                        HealthStatusRow {
                                            title: "Keypad"
                                            detail: vaydeerBridge.connection.connected ? vaydeerBridge.device.model + " is available." : vaydeerBridge.connection.message
                                            state: vaydeerBridge.connection.connected ? "ready" : "error"
                                        }
                                        Repeater {
                                            model: vaydeerBridge.setupChecks.filter(function(item) { return item.label !== "User service" })
                                            delegate: HealthStatusRow {
                                                required property var modelData
                                                title: window.setupLabel(modelData.label)
                                                detail: window.setupDetail(modelData.label, modelData.status)
                                                state: modelData.status === "pass" ? "ready" : modelData.status === "warn" ? "warning" : "error"
                                            }
                                        }
                                        HealthStatusRow {
                                            title: "Background service"
                                            detail: vaydeerBridge.service.detail
                                            state: vaydeerBridge.service.running && vaydeerBridge.service.reachable ? "info" : "warning"
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: window.space8
                                PrimaryButton {
                                    visible: !vaydeerBridge.service.installed
                                    text: "Install Background service"
                                    buttonColor: window.info
                                    onClicked: vaydeerBridge.installUserService()
                                    Accessible.name: "Install and start the Vaydeer Studio Background service"
                                }
                                PrimaryButton {
                                    visible: vaydeerBridge.service.installed && !vaydeerBridge.service.running
                                    text: "Start Background service"
                                    buttonColor: window.info
                                    onClicked: vaydeerBridge.reloadService()
                                }
                                SecondaryButton { text: "Check setup"; onClicked: vaydeerBridge.refreshDiagnostics() }
                                SecondaryButton { text: "Reconnect keypad"; onClicked: vaydeerBridge.reconnectDevice() }
                                Item { Layout.fillWidth: true }
                                SecondaryButton { text: "Permissions help"; onClicked: vaydeerBridge.showSetupCommand() }
                            }
                            Label {
                                visible: window.advancedMode
                                text: "Technical name: vaydeer-studiod. It is a per-user systemd service and keeps only the verified vendor event interface open read-only."
                                color: window.secondaryText
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                // Help
                Item {
                    ScrollView {
                        anchors.fill: parent
                        contentWidth: availableWidth
                        clip: true
                        ColumnLayout {
                            width: Math.max(0, parent.width - 56)
                            x: 28
                            y: 24
                            spacing: window.space16
                            PageHeader {
                                title: "Help"
                                subtitle: "A short guide to Vaydeer Studio, keypad memory, and Linux-only actions."
                            }
                            ScopeExplainer {
                                deviceText: "The keypad stores supported keyboard-style mappings, its layers, and layer names. Those assignments keep working when it is connected to another computer."
                                hostText: "The Background service maintains Linux activation and runs Linux actions after Studio is closed. The Studio app is needed only to configure and inspect the keypad."
                                note: "Use Setup to install or repair the Background service."
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: quickStart.implicitHeight + 28
                                color: window.panel
                                radius: 6
                                border.color: window.line
                                ColumnLayout {
                                    id: quickStart
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8
                                    Label { text: "Start here"; color: window.ink; font.pixelSize: 16; font.bold: true }
                                    Label {
                                        text: "1. Open Overview to check the keypad and Background service.  2. Read the keypad on On-device keys.  3. Edit a draft, review it, and write only when ready.  4. Save or export the profile to keep your configuration."
                                        color: window.muted
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                            GridLayout {
                                id: helpGrid
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 12
                                columnSpacing: 12
                                Repeater {
                                    model: [
                                        {
                                            "title": "Overview",
                                            "body": "See whether the keypad and Background service are ready, then choose keypad memory or Linux actions."
                                        },
                                        {
                                            "title": "On-device keys",
                                            "body": "Select a layer and physical key, choose a supported keyboard-style action, then save it to the draft. Review and write to keypad only when ready."
                                        },
                                        {
                                            "title": "Linux actions",
                                            "body": "Create actions such as launching an app, opening a URL, or running a command. These run only on Linux while the Background service is available."
                                        },
                                        {
                                            "title": "Profiles",
                                            "body": "Use profiles to save, duplicate, import, export, and organize keypad drafts and Linux actions. Only Linux-targeted actions run on this host."
                                        },
                                        {
                                            "title": "Live tester",
                                            "body": "See physical press and release events without changing any settings. You can pause, clear, copy, or export the current event session."
                                        },
                                        {
                                            "title": "Diagnostics",
                                            "body": "Check connection, permissions, and service health. Copy or export the sanitized summary when reporting an issue."
                                        },
                                        {
                                            "title": "Setup",
                                            "body": "Follow the short checklist to install or repair permissions and the Background service. Setup never changes keypad mappings."
                                        },
                                        {
                                            "title": "Basic and Advanced",
                                            "body": "Basic mode keeps everyday configuration simple. Advanced mode reveals technical values, raw reports, and optional command controls without changing your data."
                                        }
                                    ]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.preferredWidth: (helpGrid.width - helpGrid.columnSpacing) / 2
                                        Layout.fillWidth: true
                                        implicitHeight: helpCardContent.implicitHeight + 26
                                        color: window.panel
                                        radius: 6
                                        border.color: window.line
                                        ColumnLayout {
                                            id: helpCardContent
                                            anchors.fill: parent
                                            anchors.margins: 13
                                            spacing: 5
                                            Label { text: modelData.title; color: window.ink; font.bold: true; font.pixelSize: 14 }
                                            Label { text: modelData.body; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
                                        }
                                    }
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "Safety: Studio never flashes firmware or offers raw packet sending. A keypad write always requires a reviewed diff, a timestamped backup, and a typed confirmation."
                                color: window.muted
                                wrapMode: Text.WordWrap
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }
        }

    }

    Rectangle {
        id: statusToast
        property string message: ""
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 24
        anchors.bottomMargin: 24
        width: Math.min(460, toastLabel.implicitWidth + 40)
        height: Math.max(42, toastLabel.implicitHeight + 20)
        visible: opacity > 0
        opacity: 0
        z: 20
        color: window.raisedSurface
        radius: window.panelRadius
        border.color: window.border
        border.width: 1
        Behavior on opacity { NumberAnimation { duration: 140 } }
        function showMessage(text) {
            message = text
            opacity = 1
            hideTimer.restart()
        }
        Label {
            id: toastLabel
            anchors.fill: parent
            anchors.margins: 10
            text: statusToast.message
            color: window.primaryText
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 12
        }
        Timer {
            id: hideTimer
            interval: 4200
            onTriggered: statusToast.opacity = 0
        }
    }

    Connections {
        target: vaydeerBridge
        function onStatusChanged() {
            statusToast.showMessage(vaydeerBridge.statusMessage)
        }
    }
}
