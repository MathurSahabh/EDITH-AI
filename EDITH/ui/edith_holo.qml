import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    visible: true
    width: 1480
    height: 900
    title: "EDITH • HOLO INTERFACE V2.1"
    color: "#050b14"

    property color cBg0: "#050a13"
    property color cBg1: "#091526"
    property color cPanel: "#0c1829"
    property color cEdge: "#1f4d74"
    property color cGlow: "#66d1ff"
    property color cText: "#ddf5ff"
    property color cSub: "#82bddd"

    property int cpuVal: 0
    property int netVal: 0
    property int micVal: 0
    property string timeVal: "--:--:--"
    property string statusVal: "BOOTING"

    // NEW V2.1
    property bool wakeOn: false
    property int reminderCount: 0
    property bool listeningPulse: false

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: cBg0 }
            GradientStop { position: 1.0; color: cBg1 }
        }
    }

    Canvas {
        id: scanline
        anchors.fill: parent
        opacity: 0.08
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = "#8fe3ff"
            ctx.lineWidth = 1
            for (var y = 0; y < height; y += 4) {
                ctx.beginPath()
                ctx.moveTo(0, y)
                ctx.lineTo(width, y)
                ctx.stroke()
            }
        }
    }
    Timer { interval: 120; running: true; repeat: true; onTriggered: scanline.requestPaint() }

    GridLayout {
        anchors.fill: parent
        anchors.margins: 12
        columns: 4
        columnSpacing: 10
        rowSpacing: 10

        // LEFT
        Rectangle {
            Layout.row: 0
            Layout.column: 0
            Layout.rowSpan: 2
            Layout.fillHeight: true
            Layout.preferredWidth: 285
            radius: 14
            color: cPanel
            border.width: 1
            border.color: cEdge

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text { text: "EDITH"; color: cGlow; font.pixelSize: 48; font.bold: true }
                Text { text: "HOLOGRAPHIC ASSIST SYSTEM"; color: cSub; font.pixelSize: 12 }

                // wake status chip
                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 9
                    color: wakeOn ? "#123d2a" : "#3a1a1a"
                    border.color: wakeOn ? "#4ce39c" : "#e36b6b"
                    border.width: 1

                    Row {
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle {
                            width: 10; height: 10; radius: 5
                            color: wakeOn ? "#68ffb8" : "#ff8f8f"
                            SequentialAnimation on opacity {
                                running: wakeOn
                                loops: Animation.Infinite
                                NumberAnimation { from: 1.0; to: 0.25; duration: 500 }
                                NumberAnimation { from: 0.25; to: 1.0; duration: 500 }
                            }
                        }
                        Text {
                            text: wakeOn ? "WAKE MODE: ON" : "WAKE MODE: OFF"
                            color: "#e8f6ff"
                            font.bold: true
                            font.pixelSize: 13
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 170
                    radius: 12
                    color: "#081424"
                    border.color: "#2a608a"
                    border.width: 1

                    Canvas {
                        id: miniRadar
                        anchors.fill: parent
                        property real ang: 0
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0,0,width,height)
                            var cx = width/2, cy = height/2
                            var r = Math.min(width,height)*0.34
                            function ring(rr,a,w){ ctx.beginPath(); ctx.strokeStyle="rgba(105,210,255,"+a+")"; ctx.lineWidth=w; ctx.arc(cx,cy,rr,0,Math.PI*2); ctx.stroke(); }
                            ring(r,0.95,2); ring(r-16,0.5,1); ring(r-30,0.35,1)
                            for (var i=0;i<50;i++){
                                var t=i*Math.PI*2/50
                                var x1=cx+(r-6)*Math.cos(t), y1=cy+(r-6)*Math.sin(t)
                                var x2=cx+(r+2)*Math.cos(t), y2=cy+(r+2)*Math.sin(t)
                                ctx.beginPath(); ctx.strokeStyle=(i%5===0)?"rgba(150,240,255,0.9)":"rgba(90,165,210,0.4)"
                                ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke()
                            }
                            var a = miniRadar.ang*Math.PI/180
                            ctx.beginPath(); ctx.strokeStyle="rgba(170,250,255,0.95)"; ctx.lineWidth=2
                            ctx.moveTo(cx,cy); ctx.lineTo(cx+(r-8)*Math.cos(a), cy+(r-8)*Math.sin(a)); ctx.stroke()
                            ctx.beginPath(); ctx.fillStyle="rgba(130,230,255,1)"; ctx.arc(cx,cy,6,0,Math.PI*2); ctx.fill()
                        }
                        Timer { interval: 30; running: true; repeat: true; onTriggered: { miniRadar.ang=(miniRadar.ang+3)%360; miniRadar.requestPaint() } }
                    }
                }

                // buttons
                Rectangle {
                    Layout.fillWidth: true; height: 42; radius: 10
                    color: "#112238"; border.color: "#2f628a"; border.width: 1
                    Text { anchors.centerIn: parent; color: "#e3f4ff"; text: "Clear Chat"; font.pixelSize: 15 }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onEntered: parent.color = "#16314f"
                        onExited: parent.color = "#112238"
                        onClicked: backend.clearChat()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 42; radius: 10
                    color: "#112238"; border.color: "#2f628a"; border.width: 1
                    Text { anchors.centerIn: parent; color: "#e3f4ff"; text: "Voice Toggle"; font.pixelSize: 15 }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onEntered: parent.color = "#16314f"
                        onExited: parent.color = "#112238"
                        onClicked: backend.toggleVoice()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 42; radius: 10
                    color: "#112238"; border.color: "#2f628a"; border.width: 1
                    Text { anchors.centerIn: parent; color: "#e3f4ff"; text: "Mode Toggle"; font.pixelSize: 15 }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onEntered: parent.color = "#16314f"
                        onExited: parent.color = "#112238"
                        onClicked: backend.toggleMode()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 42; radius: 10
                    color: wakeOn ? "#123d2a" : "#112238"
                    border.color: wakeOn ? "#4ce39c" : "#2f628a"
                    border.width: 1
                    Text { anchors.centerIn: parent; color: "#e3f4ff"; text: "Wake Toggle"; font.pixelSize: 15 }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onEntered: parent.color = wakeOn ? "#175538" : "#16314f"
                        onExited: parent.color = wakeOn ? "#123d2a" : "#112238"
                        onClicked: {
                            wakeOn = !wakeOn
                            backend.toggleWake()
                        }
                    }
                }

                Text { text: "Quick Commands"; color: cSub; font.bold: true; font.pixelSize: 13 }

                Repeater {
                    model: ["open youtube", "search carryminati on youtube", "weather in delhi", "latest tech news"]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: 9
                        color: "#0f1d31"
                        border.color: "#2b5c84"
                        border.width: 1
                        Text { anchors.centerIn: parent; text: modelData; color: "#d9efff"; font.pixelSize: 14 }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: backend.sendCommand(modelData)
                            onPressed: parent.color = "#1a3553"
                            onReleased: parent.color = "#0f1d31"
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }

        // CENTER
        Rectangle {
            Layout.row: 0
            Layout.column: 1
            Layout.columnSpan: 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 14
            color: cPanel
            border.width: 1
            border.color: cEdge

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "EDITH // HOLOGRAPHIC CORE"
                        color: cText
                        font.pixelSize: 30
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: statusVal
                        color: cGlow
                        font.pixelSize: 15
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: "#071323"
                    border.color: "#234e70"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 12

                        Rectangle {
                            Layout.preferredWidth: 430
                            Layout.fillHeight: true
                            radius: 12
                            color: "#08172a"
                            border.color: "#2a5d87"
                            border.width: 1

                            Canvas {
                                id: coreRadar
                                anchors.fill: parent
                                property real ang: 0
                                property real pulse: 0
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0,0,width,height)
                                    var cx = width/2, cy = height/2
                                    var r = Math.min(width,height)*0.38
                                    function ring(rr,a,w){ ctx.beginPath(); ctx.strokeStyle="rgba(98,205,255,"+a+")"; ctx.lineWidth=w; ctx.arc(cx,cy,rr,0,Math.PI*2); ctx.stroke(); }
                                    ring(r,0.95,2); ring(r-24,0.60,1); ring(r-48,0.40,1); ring(r-72,0.25,1)
                                    for (var i=0;i<14;i++){
                                        var sa=(i*26+coreRadar.ang)*Math.PI/180
                                        var ea=sa+14*Math.PI/180
                                        ctx.beginPath()
                                        ctx.strokeStyle=(i%3===0)?"rgba(140,240,255,0.95)":"rgba(80,160,210,0.5)"
                                        ctx.lineWidth=3
                                        ctx.arc(cx,cy,r-12,sa,ea)
                                        ctx.stroke()
                                    }
                                    var a=coreRadar.ang*Math.PI/180
                                    ctx.beginPath(); ctx.strokeStyle="rgba(160,248,255,0.95)"; ctx.lineWidth=2.5
                                    ctx.moveTo(cx,cy); ctx.lineTo(cx+(r-8)*Math.cos(a), cy+(r-8)*Math.sin(a)); ctx.stroke()
                                    var pr=30+(coreRadar.pulse%70), pa=Math.max(0,190-coreRadar.pulse*2)
                                    ctx.beginPath(); ctx.strokeStyle="rgba(130,220,255,"+(pa/255)+")"; ctx.lineWidth=2
                                    ctx.arc(cx,cy,pr,0,Math.PI*2); ctx.stroke()
                                    ctx.beginPath(); ctx.fillStyle="rgba(65,150,205,0.7)"; ctx.arc(cx,cy,18,0,Math.PI*2); ctx.fill()
                                }
                                Timer { interval: 30; running: true; repeat: true; onTriggered: { coreRadar.ang=(coreRadar.ang+2.4)%360; coreRadar.pulse=(coreRadar.pulse+1)%95; coreRadar.requestPaint() } }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: "#08172a"
                            border.color: "#2a5d87"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8

                                Text {
                                    text: "NEURAL EVENT STREAM"
                                    color: cSub
                                    font.bold: true
                                    font.pixelSize: 13
                                }

                                ListView {
                                    id: eventList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    spacing: 7
                                    model: ListModel { id: eventModel }

                                    delegate: Rectangle {
                                        width: eventList.width - 10
                                        height: t.paintedHeight + 20
                                        radius: 10
                                        color: "#12263b"
                                        border.color: "#285679"
                                        border.width: 1

                                        Text {
                                            id: t
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: model.text
                                            color: "#dff3ff"
                                            wrapMode: Text.Wrap
                                            font.pixelSize: 14
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // RIGHT
        Rectangle {
            Layout.row: 0
            Layout.column: 3
            Layout.fillHeight: true
            Layout.preferredWidth: 280
            radius: 14
            color: cPanel
            border.width: 1
            border.color: cEdge

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                Text { text: "SYSTEM WIDGETS"; color: cSub; font.bold: true; font.pixelSize: 13 }

                Rectangle {
                    Layout.fillWidth: true; height: 78; radius: 10
                    color: "#0f2136"; border.color: "#2d6289"; border.width: 1
                    Column { anchors.centerIn: parent; spacing: 4
                        Text { text: "CPU LOAD"; color: "#8bc6e8"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; width: 200 }
                        Text { text: cpuVal + "%"; color: "#ddf6ff"; font.pixelSize: 22; font.bold: true; horizontalAlignment: Text.AlignHCenter; width: 200 }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 78; radius: 10
                    color: "#0f2136"; border.color: "#2d6289"; border.width: 1
                    Column { anchors.centerIn: parent; spacing: 4
                        Text { text: "NETWORK"; color: "#8bc6e8"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; width: 200 }
                        Text { text: netVal + "%"; color: "#ddf6ff"; font.pixelSize: 22; font.bold: true; horizontalAlignment: Text.AlignHCenter; width: 200 }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 78; radius: 10
                    color: "#0f2136"; border.color: "#2d6289"; border.width: 1
                    Column { anchors.centerIn: parent; spacing: 4
                        Text { text: "MIC LEVEL"; color: "#8bc6e8"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; width: 200 }
                        Text { text: micVal + "%"; color: "#ddf6ff"; font.pixelSize: 22; font.bold: true; horizontalAlignment: Text.AlignHCenter; width: 200 }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 78; radius: 10
                    color: "#0f2136"; border.color: "#2d6289"; border.width: 1
                    Column { anchors.centerIn: parent; spacing: 4
                        Text { text: "LOCAL TIME"; color: "#8bc6e8"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; width: 200 }
                        Text { text: timeVal; color: "#ddf6ff"; font.pixelSize: 22; font.bold: true; horizontalAlignment: Text.AlignHCenter; width: 200 }
                    }
                }

                // NEW reminder tile
                Rectangle {
                    Layout.fillWidth: true; height: 78; radius: 10
                    color: "#16253a"; border.color: "#4d7aa8"; border.width: 1
                    Column { anchors.centerIn: parent; spacing: 4
                        Text { text: "REMINDERS"; color: "#8bc6e8"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; width: 200 }
                        Text { text: reminderCount.toString(); color: "#e7f8ff"; font.pixelSize: 22; font.bold: true; horizontalAlignment: Text.AlignHCenter; width: 200 }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }

        // BOTTOM
        Rectangle {
            Layout.row: 1
            Layout.column: 1
            Layout.columnSpan: 3
            Layout.fillWidth: true
            Layout.preferredHeight: 128
            radius: 14
            color: cPanel
            border.width: 1
            border.color: cEdge

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                TextArea {
                    id: commandInput
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#e5f6ff"
                    placeholderText: "Type command..."
                    placeholderTextColor: "#7ba4c4"
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 16
                    background: Rectangle {
                        radius: 10
                        color: "#081728"
                        border.color: "#2a5d85"
                        border.width: 1
                    }
                }

                ColumnLayout {
                    Layout.preferredWidth: 130
                    spacing: 8

                    Rectangle {
                        Layout.fillWidth: true; height: 40; radius: 10
                        color: "#1a4f78"; border.color: "#62c8ff"; border.width: 1
                        Text { anchors.centerIn: parent; text: "SEND"; color: "#ecf9ff"; font.bold: true }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                if (commandInput.text.trim().length === 0) return
                                backend.sendCommand(commandInput.text)
                                commandInput.clear()
                            }
                        }
                    }

                    Rectangle {
                        id: micBtn
                        Layout.fillWidth: true; height: 40; radius: 10
                        color: listeningPulse ? "#215f8f" : "#1b3350"
                        border.color: listeningPulse ? "#8fe3ff" : "#4ea8e2"
                        border.width: 1
                        Text { anchors.centerIn: parent; text: "MIC"; color: "#ecf9ff"; font.bold: true }

                        SequentialAnimation on opacity {
                            running: listeningPulse
                            loops: Animation.Infinite
                            NumberAnimation { from: 1.0; to: 0.45; duration: 350 }
                            NumberAnimation { from: 0.45; to: 1.0; duration: 350 }
                        }

                        MouseArea { anchors.fill: parent; onClicked: backend.micOnce() }
                    }

                    Rectangle {
                        Layout.fillWidth: true; height: 40; radius: 10
                        color: "#4b1e2b"; border.color: "#c9667d"; border.width: 1
                        Text { anchors.centerIn: parent; text: "STOP"; color: "#ffe9ef"; font.bold: true }
                        MouseArea { anchors.fill: parent; onClicked: backend.stopSpeech() }
                    }
                }
            }
        }
    }

    // Boot overlay
    Rectangle {
        id: bootOverlay
        anchors.fill: parent
        color: "#000000"
        opacity: 0.92
        visible: true
        z: 999

        Column {
            anchors.centerIn: parent
            spacing: 10

            Text {
                text: "EDITH BOOT SEQUENCE"
                color: "#8fe0ff"
                font.pixelSize: 34
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                width: 600
            }

            Rectangle {
                width: 700
                height: 230
                radius: 12
                color: "#061120"
                border.color: "#2a5e88"
                border.width: 1

                ListView {
                    id: bootList
                    anchors.fill: parent
                    anchors.margins: 10
                    clip: true
                    model: ListModel { id: bootModel }
                    delegate: Text {
                        text: model.text
                        color: "#a6dcff"
                        font.family: "Consolas"
                        font.pixelSize: 15
                    }
                }
            }
        }

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }

    Connections {
        target: backend

        function onPushEvent(msg) {
            if (msg === "##CLEAR##") {
                eventModel.clear()
                reminderCount = 0
                return
            }
            eventModel.append({ "text": msg })
            eventList.positionViewAtEnd()

            // update reminder counter from messages
            if (msg.toLowerCase().indexOf("reminder set") !== -1) reminderCount += 1
            if (msg.toLowerCase().indexOf("edith: reminder:") !== -1 && reminderCount > 0) reminderCount -= 1
        }

        function onStatusChanged(msg) {
            statusVal = msg.toUpperCase()

            // listening pulse state
            listeningPulse = (statusVal === "LISTENING")
        }

        function onTelemetry(cpu, net, mic, timeText) {
            cpuVal = cpu
            netVal = net
            micVal = mic
            timeVal = timeText
        }

        function onBootLine(line) {
            bootModel.append({ "text": line })
            bootList.positionViewAtEnd()
        }

        function onBootDone() {
            bootOverlay.opacity = 0
            bootOverlay.visible = false
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            var d = new Date()
            var hh = ("0"+d.getHours()).slice(-2)
            var mm = ("0"+d.getMinutes()).slice(-2)
            var ss = ("0"+d.getSeconds()).slice(-2)
            backend.pushClock(hh + ":" + mm + ":" + ss)
        }
    }
}