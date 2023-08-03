import wx
from wx.lib.plot import PolyLine, PlotCanvas, PlotGraphics
import serial
from serial.tools import list_ports
import threading

class HandbrakeController(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Handbrake Controller", size=(600,400))

        # Serial communication
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.timeout = 1

        # GUI elements
        self.portSelection = wx.ComboBox(self)
        self.updatePortList()

        self.curveTypeChoices = ['LINEAR', 'EXPONENTIAL', 'LOGARITHMIC']
        self.curveType = wx.Choice(self, choices=self.curveTypeChoices)

        self.minHandbrake = wx.Slider(self, value=0, minValue=0, maxValue=900000, style=wx.SL_HORIZONTAL)
        self.maxHandbrake = wx.Slider(self, value=900000, minValue=0, maxValue=900000, style=wx.SL_HORIZONTAL)
        self.curveFactor = wx.Slider(self, value=2, minValue=0, maxValue=10, style=wx.SL_HORIZONTAL)

        self.saveButton = wx.Button(self, label="Save Settings")
        self.setupModeToggle = wx.CheckBox(self, label="Toggle Setup Mode")

        self.plotCanvas = PlotCanvas(self)
        self.rawHandbrakeValue = wx.StaticText(self, label="Raw Handbrake Value: ")
        self.processedHandbrakeValue = wx.StaticText(self, label="Processed Handbrake Value: ")

        # Layout
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox0 = wx.BoxSizer(wx.HORIZONTAL)
        hbox0.Add(wx.StaticText(self, label="Port: "), flag=wx.RIGHT, border=8)
        hbox0.Add(self.portSelection)
        vbox.Add(hbox0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(wx.StaticText(self, label="Curve Type: "), flag=wx.RIGHT, border=8)
        hbox1.Add(self.curveType)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(wx.StaticText(self, label="Min Handbrake: "), flag=wx.RIGHT, border=8)
        hbox2.Add(self.minHandbrake, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(wx.StaticText(self, label="Max Handbrake: "), flag=wx.RIGHT, border=8)
        hbox3.Add(self.maxHandbrake, proportion=1)
        vbox.Add(hbox3, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        hbox4.Add(wx.StaticText(self, label="Curve Factor: "), flag=wx.RIGHT, border=8)
        hbox4.Add(self.curveFactor, proportion=1)
        vbox.Add(hbox4, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        vbox.Add(self.saveButton, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(self.setupModeToggle, flag=wx.EXPAND|wx.ALL, border=10)

        vbox.Add(self.plotCanvas, proportion=1, flag=wx.EXPAND)
        vbox.Add(self.rawHandbrakeValue, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(self.processedHandbrakeValue, flag=wx.EXPAND|wx.ALL, border=10)

        self.SetSizer(vbox)

        # Event bindings
        self.portSelection.Bind(wx.EVT_COMBOBOX, self.onPortSelection)
        self.curveType.Bind(wx.EVT_CHOICE, self.onCurveTypeChange)
        self.minHandbrake.Bind(wx.EVT_SLIDER, self.onMinHandbrakeChange)
        self.maxHandbrake.Bind(wx.EVT_SLIDER, self.onMaxHandbrakeChange)
        self.curveFactor.Bind(wx.EVT_SLIDER, self.onCurveFactorChange)
        self.saveButton.Bind(wx.EVT_BUTTON, self.onSaveButton)
        self.setupModeToggle.Bind(wx.EVT_CHECKBOX, self.onSetupModeToggle)

        # Start update thread
        self.updateThread = threading.Thread(target=self.updateHandbrakeValues)
        self.updateThread.start()

    def updatePortList(self):
        self.portSelection.Clear()
        ports = list_ports.comports()
        for port in ports:
            self.portSelection.Append(port.device)

    def onPortSelection(self, event):
        port = self.portSelection.GetValue()
        if self.ser.is_open:
            self.ser.close()
        self.ser.port = port
        self.ser.open()

    def onCurveTypeChange(self, event):
        curveType = self.curveTypeChoices.index(self.curveType.GetStringSelection())
        self.ser.write(bytes('c' + str(curveType), 'utf-8'))

    def onMinHandbrakeChange(self, event):
        minHandbrake = self.minHandbrake.GetValue()
        self.ser.write(bytes('m' + str(minHandbrake), 'utf-8'))

    def onMaxHandbrakeChange(self, event):
        maxHandbrake = self.maxHandbrake.GetValue()
        self.ser.write(bytes('M' + str(maxHandbrake), 'utf-8'))

    def onCurveFactorChange(self, event):
        curveFactor = self.curveFactor.GetValue()
        self.ser.write(bytes('f' + str(curveFactor), 'utf-8'))

    def onSaveButton(self, event):
        self.ser.write(bytes('s', 'utf-8'))

    def onSetupModeToggle(self, event):
        self.ser.write(bytes('e', 'utf-8'))

    def updateHandbrakeValues(self):
        while True:
            line = self.ser.readline().decode('utf-8').strip()
            if line.startswith("Raw Handbrake Value: "):
                raw, processed = line.split("   Processed Handbrake Value: ")
                raw = float(raw[21:])
                processed = float(processed)

                wx.CallAfter(self.rawHandbrakeValue.SetLabel, "Raw Handbrake Value: " + str(raw))
                wx.CallAfter(self.processedHandbrakeValue.SetLabel, "Processed Handbrake Value: " + str(processed))

                # Here, you should also add the new data point to your plot and refresh it

if __name__ == "__main__":
    app = wx.App(False)
    frame = HandbrakeController()
    frame.Show()
    app.MainLoop()
