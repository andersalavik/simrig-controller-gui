import wx
from wx.lib.plot import PolyLine, PlotCanvas, PlotGraphics
import serial
from serial.tools import list_ports
import threading
import numpy as np



class HandbrakeController(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Handbrake Controller", size=(800,600))

        # Serial communication
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.timeout = 1

        # GUI elements
        self.portSelection = wx.ComboBox(self)
        self.updatePortList()

        self.curveTypeChoices = ['LINEAR', 'EXPONENTIAL', 'LOGARITHMIC']
        self.curveType = wx.Choice(self, choices=self.curveTypeChoices)

        # Create the slider and the text
        self.minHandbrake = wx.Slider(self, value=-5200, minValue=-10000, maxValue=900000, style=wx.SL_HORIZONTAL)
        self.minHandbrakeValueText = wx.StaticText(self, label=str(self.minHandbrake.GetValue()))

        
        self.maxHandbrake = wx.Slider(self, value=50000, minValue=-10000, maxValue=900000, style=wx.SL_HORIZONTAL)
        self.maxHandbrakeValueText = wx.StaticText(self, label=str(self.maxHandbrake.GetValue()))
        
        self.curveFactor = wx.Slider(self, value=2, minValue=0, maxValue=10, style=wx.SL_HORIZONTAL)
        self.curveFactorValueText = wx.StaticText(self, label=str(self.curveFactor.GetValue()))
        
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
        self.connectButton = wx.Button(self, label="Connect")
        hbox0.Add(self.connectButton)

        vbox.Add(hbox0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(wx.StaticText(self, label="Curve Type: "), flag=wx.RIGHT, border=8)
        hbox1.Add(self.curveType)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(wx.StaticText(self, label="Min Handbrake: "), flag=wx.RIGHT, border=8)
        hbox2.Add(self.minHandbrake, proportion=1)
        hbox2.Add(self.minHandbrakeValueText)
        
        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(wx.StaticText(self, label="Max Handbrake: "), flag=wx.RIGHT, border=8)
        hbox3.Add(self.maxHandbrake, proportion=1)
        hbox3.Add(self.maxHandbrakeValueText)
        vbox.Add(hbox3, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        hbox4.Add(wx.StaticText(self, label="Curve Factor: "), flag=wx.RIGHT, border=8)
        hbox4.Add(self.curveFactor, proportion=1)
        hbox4.Add(self.curveFactorValueText)
        vbox.Add(hbox4, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        vbox.Add(self.saveButton, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(self.setupModeToggle, flag=wx.EXPAND|wx.ALL, border=10)

        vbox.Add(self.plotCanvas, proportion=1, flag=wx.EXPAND)
        vbox.Add(self.rawHandbrakeValue, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(self.processedHandbrakeValue, flag=wx.EXPAND|wx.ALL, border=10)

        self.SetSizer(vbox)

        # Event bindings
        self.connectButton.Bind(wx.EVT_BUTTON, self.onConnectButton)
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

    def onConnectButton(self, event):
        if self.ser.is_open:
            self.ser.close()
            self.connectButton.SetLabel("Connect")
        else:
            try:
                port = self.portSelection.GetValue()
                self.ser.port = port
                self.ser.open()
                self.readSettings()
                self.connectButton.SetLabel("Disconnect")
            except:
                wx.MessageBox('Failed to open port.', 'Error', wx.OK | wx.ICON_ERROR)

    def onCurveTypeChange(self, event):
        curveType = self.curveTypeChoices.index(self.curveType.GetStringSelection())
        self.ser.write(bytes('c' + str(curveType), 'utf-8'))
        self.plotCurve()  # Update curve

    def onMinHandbrakeChange(self, event):
        minHandbrake = self.minHandbrake.GetValue()
        self.minHandbrakeValueText.SetLabel(str(minHandbrake))
        self.ser.write(bytes('m' + str(minHandbrake), 'utf-8'))
        self.plotCurve()  # Update curve

    def onMaxHandbrakeChange(self, event):
        maxHandbrake = self.maxHandbrake.GetValue()
        self.maxHandbrakeValueText.SetLabel(str(maxHandbrake))
        self.ser.write(bytes('M' + str(maxHandbrake), 'utf-8'))
        self.plotCurve()  # Update curve

    def onCurveFactorChange(self, event):
        curveFactor = self.curveFactor.GetValue()
        self.curveFactorValueText.SetLabel(str(curveFactor))
        self.ser.write(bytes('f' + str(curveFactor), 'utf-8'))
        self.plotCurve()  # Update curve

    def onSaveButton(self, event):
        self.ser.write(bytes('s', 'utf-8'))

    def onSetupModeToggle(self, event):
        self.ser.write(bytes('e', 'utf-8'))
        
    def readSettings(self):
        self.ser.write(bytes('r', 'utf-8'))
        
    def plotCurve(self):
        curveType = self.curveType.GetStringSelection()
        minHandbrake = self.minHandbrake.GetValue()
        maxHandbrake = self.maxHandbrake.GetValue()
        curveFactor = self.curveFactor.GetValue()

        x = np.linspace(minHandbrake, maxHandbrake, 100)  # Generate x values
        if curveType == 'LINEAR':
            y = x * curveFactor
        elif curveType == 'EXPONENTIAL':
            y = np.exp(x * curveFactor)
        elif curveType == 'LOGARITHMIC':
            y = np.log(x * curveFactor)

        # Create new plot
        line = PolyLine(list(zip(x, y)), colour='red', width=1)
        gc = PlotGraphics([line], 'Handbrake Values', 'Raw Value', 'Processed Value')
        # Update plot on the GUI
        wx.CallAfter(self.plotCanvas.Draw, gc)

    def updateHandbrakeValues(self):
        self.data_raw = []  # Initialize data list for raw values
        self.data_processed = []  # Initialize data list for processed values
        counter = 0  # Simple counter to represent time
        while True:
            if self.ser.is_open:  # Ensure the serial port is open before reading
                line = self.ser.readline().decode('utf-8').strip()
                if line.startswith("Raw Handbrake Value: "):
                    raw, processed = line.split("   Processed Handbrake Value: ")
                    raw = float(raw[21:])
                    processed = float(processed)

                    wx.CallAfter(self.rawHandbrakeValue.SetLabel, "Raw Handbrake Value: " + str(raw))
                    wx.CallAfter(self.processedHandbrakeValue.SetLabel, "Processed Handbrake Value: " + str(processed))

                    # Add new data point to list
                    self.data_raw.append((counter, raw))
                    self.data_processed.append((counter, processed))
                    # Remove oldest data point if list is too long
                    if len(self.data_raw) > 100:
                        self.data_raw.pop(0)
                        self.data_processed.pop(0)

                    # Create new plot
                    line_raw = PolyLine(self.data_raw, colour='red', width=1)
                    line_processed = PolyLine(self.data_processed, colour='blue', width=1)
                    gc = PlotGraphics([line_raw, line_processed], 'Handbrake Values', 'Time', 'Value')
                    # Update plot on the GUI
                    wx.CallAfter(self.plotCanvas.Draw, gc)

                    counter += 1  # Increment counter


if __name__ == "__main__":
    app = wx.App(False)
    frame = HandbrakeController()
    frame.Show()
    app.MainLoop()
