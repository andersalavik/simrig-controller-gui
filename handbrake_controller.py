import wx
from wx.lib.plot import PolyLine, PlotCanvas, PlotGraphics, PolyMarker
import serial
from serial.tools import list_ports
import threading
import numpy as np
import time

class HandbrakeController(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Handbrake Controller", size=(800,600))
        self.running = True

        # Serial communication
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.timeout = 1

        # GUI elements
        self.portSelection = wx.ComboBox(self)
        self.updatePortList()

        self.autoSetMode = False

        self.curveTypeChoices = ['LINEAR', 'EXPONENTIAL', 'LOGARITHMIC']
        self.curveType = wx.Choice(self, choices=self.curveTypeChoices)

        # Create the slider and the text
        self.minHandbrake = wx.Slider(self, value=-5200, minValue=-10000, maxValue=3000000, style=wx.SL_HORIZONTAL)
        self.minHandbrakeValueInput = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)

        self.maxHandbrake = wx.Slider(self, value=50000, minValue=-10000, maxValue=3000000, style=wx.SL_HORIZONTAL)
        self.maxHandbrakeValueInput = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)

        self.curveFactor = wx.Slider(self, value=20, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        self.curveFactorValueInput = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)

        self.saveButton = wx.Button(self, label="Save Settings")
        self.setupModeToggle = wx.CheckBox(self, label="Toggle Setup Mode")
        self.setupModeToggle.Hide()

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
        self.configButton = wx.Button(self, label="Config")
        hbox0.Add(self.configButton)
        self.configButton.Hide()

        vbox.Add(hbox0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(wx.StaticText(self, label="Curve Type: "), flag=wx.RIGHT, border=8)
        hbox1.Add(self.curveType)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.minHandbrake, proportion=1)
        hbox2.Add(self.minHandbrakeValueInput)
        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.maxHandbrake, proportion=1)
        hbox3.Add(self.maxHandbrakeValueInput)
        vbox.Add(hbox3, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        hbox4.Add(self.curveFactor, proportion=1)
        hbox4.Add(self.curveFactorValueInput)
        vbox.Add(hbox4, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        vbox.Add(self.saveButton, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(self.setupModeToggle, flag=wx.EXPAND|wx.ALL, border=10)

        vbox.Add(self.plotCanvas, proportion=1, flag=wx.EXPAND)
        vbox.Add(self.rawHandbrakeValue, flag=wx.EXPAND|wx.ALL, border=10)
        vbox.Add(self.processedHandbrakeValue, flag=wx.EXPAND|wx.ALL, border=10)

        self.autoSetButton = wx.Button(self, label="Auto Set")
        vbox.Add(self.autoSetButton, flag=wx.EXPAND|wx.ALL, border=10)

        # Bind an event handler to the button's click event
        self.autoSetButton.Bind(wx.EVT_BUTTON, self.onAutoSetButton)

        self.SetSizer(vbox)

        # Event bindings
        self.connectButton.Bind(wx.EVT_BUTTON, self.onConnectButton)
        self.curveType.Bind(wx.EVT_CHOICE, self.onCurveTypeChange)
        self.minHandbrake.Bind(wx.EVT_SLIDER, self.onMinHandbrakeChange)
        self.maxHandbrake.Bind(wx.EVT_SLIDER, self.onMaxHandbrakeChange)
        self.curveFactor.Bind(wx.EVT_SLIDER, self.onCurveFactorChange)
        self.saveButton.Bind(wx.EVT_BUTTON, self.onSaveButton)
        self.setupModeToggle.Bind(wx.EVT_CHECKBOX, self.onSetupModeToggle)
        self.configButton.Bind(wx.EVT_BUTTON, self.onConfigButton)
        self.minHandbrakeValueInput.Bind(wx.EVT_TEXT_ENTER, self.onMinHandbrakeValueInput)
        self.maxHandbrakeValueInput.Bind(wx.EVT_TEXT_ENTER, self.onMaxHandbrakeValueInput)
        self.curveFactorValueInput.Bind(wx.EVT_TEXT_ENTER, self.onCurveFactorValueInput)



        # Start update thread
        self.updateThread = threading.Thread(target=self.updateHandbrakeValues)
        self.updateThread.start()
        
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def updatePortList(self):
        self.portSelection.Clear()
        ports = list_ports.comports()
        for port in ports:
            self.portSelection.Append(port.device)

    def onConnectButton(self, event):
        if self.ser.is_open:
            self.ser.write(bytes('w', 'utf-8'))
            self.setupModeToggle.SetValue(False)
            time.sleep(1)
            self.ser.close()
            self.connectButton.SetLabel("Connect")
        else:
            try:
                port = self.portSelection.GetValue()
                self.ser.port = port
                
                self.ser.open()
                self.readSettings()
                self.setupModeToggle.SetValue(True)
                self.ser.write(bytes('e', 'utf-8'))
                self.connectButton.SetLabel("Disconnect")
            except:
                wx.MessageBox('Failed to open port.', 'Error', wx.OK | wx.ICON_ERROR)

    def onConfigButton(self, event):
        self.readSettings()


    def stop(self):
        self.running = False
        
    def OnClose(self, event):
        self.stop()
        self.Destroy()

    def onCurveTypeChange(self, event):
        curveTypeMapping = {'LINEAR': 0, 'EXPONENTIAL': 1, 'LOGARITHMIC': 2}
        curveType = self.curveType.GetStringSelection()
        curveTypeNumber = curveTypeMapping.get(curveType, 0)  # Default to 'LINEAR' if curveType is not found
        #print(curveTypeNumber)
        self.ser.write(bytes('c' + str(curveTypeNumber), 'utf-8'))
        self.plotCurve()  # Update curve

    def onMinHandbrakeChange(self, event):
        minHandbrake = self.minHandbrake.GetValue()
        self.minHandbrakeValueInput.SetValue(str(minHandbrake))
        self.ser.write(bytes('m' + str(minHandbrake), 'utf-8'))
        self.plotCurve()  # Update curve

    def onMaxHandbrakeChange(self, event):
        maxHandbrake = self.maxHandbrake.GetValue()
        self.maxHandbrakeValueInput.SetValue(str(maxHandbrake))
        #print(maxHandbrake)
        self.ser.write(bytes('t' + str(maxHandbrake), 'utf-8'))
        self.plotCurve()  # Update curve

    def onCurveFactorChange(self, event):
        curveFactor = self.curveFactor.GetValue() 
        self.curveFactorValueInput.SetValue(str(curveFactor / 10))
        print(curveFactor)
        self.ser.write(bytes('f' + str(curveFactor), 'utf-8'))
        self.plotCurve()  # Update curve

    def onSaveButton(self, event):
        self.ser.write(bytes('s', 'utf-8'))

    def onSetupModeToggle(self, event):
        if self.setupModeToggle.Value == True:
            self.ser.write(bytes('e', 'utf-8'))
        else:
            self.ser.write(bytes('w', 'utf-8'))
        
    def readSettings(self):
        self.ser.write(bytes('r', 'utf-8'))
        

    def onAutoSetButton(self, event):
        # Toggle "auto set" mode
        self.autoSetMode = not self.autoSetMode

        if self.autoSetMode:
            self.autoSetButton.SetBackgroundColour('red')
            self.autoSetButton.SetForegroundColour('white')

            # Reset current values on min and max to 0
            self.minHandbrake.SetValue(0)
            self.maxHandbrake.SetValue(0)
            self.minHandbrakeValueInput.SetValue(str(0))
            self.maxHandbrakeValueInput.SetValue(str(0))
        else:
            # Restore original button color
            self.autoSetButton.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
            self.autoSetButton.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT))


            minHandbrake = self.minHandbrake.GetValue()

            self.ser.write(bytes('m' + str(minHandbrake), 'utf-8'))

            maxHandbrake = self.maxHandbrake.GetValue()

            self.ser.write(bytes('t' + str(maxHandbrake), 'utf-8'))



        self.autoSetButton.Refresh()  # Refresh button to apply color changes


    def onMinHandbrakeValueInput(self, event):
        value = int(event.GetString())
        self.minHandbrake.SetValue(value)
        self.minHandbrakeValueInput.SetValue(str(value))
        self.ser.write(bytes('m' + str(value), 'utf-8'))

    def onMaxHandbrakeValueInput(self, event):
        value = int(event.GetString())
        self.maxHandbrake.SetValue(value)
        self.maxHandbrakeValueInput.SetValue(str(value))
        self.ser.write(bytes('t' + str(value), 'utf-8'))

    def onCurveFactorValueInput(self, event):
        value = int(event.GetString())
        self.curveFactor.SetValue(value)
        self.curveFactorValueInput.SetValue(str(value / 10.0))
        self.ser.write(bytes('f' + str(value), 'utf-8'))



    def plotCurve(self):
        curveType = self.curveType.GetStringSelection()
        minHandbrake = self.minHandbrake.GetValue()
        maxHandbrake = self.maxHandbrake.GetValue()
        curveFactor = self.curveFactor.GetValue() / 10
        rawHandbrakeValue = self.data_raw[-1][1] if self.data_raw else None
        processedHandbrakeValue = self.data_processed[-1][1] if self.data_processed else None

        # Define output range
        output_min = 0
        output_max = 100

        # Scale processed data to graph range (0-100)
        if processedHandbrakeValue is not None:
            processedHandbrakeValue = ((processedHandbrakeValue - 0) / (1023 - 0)) * (output_max - output_min) + output_min

        if rawHandbrakeValue is not None and processedHandbrakeValue is not None:
            #print(rawHandbrakeValue, processedHandbrakeValue)
            point = PolyMarker([(rawHandbrakeValue, processedHandbrakeValue)], colour='blue', marker='circle', size=2)
        else:
            point = None

        #print(point)
        x = np.linspace(minHandbrake, maxHandbrake, 100)  + 0.001  # Generate x values

        # Compute curves
        if curveType == 'LINEAR':
            y = maxHandbrake * x + curveFactor 
        elif curveType == 'EXPONENTIAL':
            y = np.where(x > 0, maxHandbrake * np.power(x, curveFactor) + curveFactor, 0)
        elif curveType == 'LOGARITHMIC':
            # Check to avoid log of 0
            y = np.where(x > 0, maxHandbrake * np.log(x) / np.log(curveFactor) + curveFactor, 0)
        else:
            y = x  # Default case: y = x


        # Scale output values to desired range (output_min - output_max)
        y = ((y - np.min(y)) / (np.max(y) - np.min(y))) * (output_max - output_min) + output_min

        # Create new plot
        line = PolyLine(list(zip(x, y)), colour='red', width=1)

        if point is not None:
            gc = PlotGraphics([line, point], 'Handbrake Values', 'Raw Value', 'Processed Value')
        else:
            gc = PlotGraphics([line], 'Handbrake Values', 'Raw Value', 'Processed Value')

        # Update plot on the GUI
        wx.CallAfter(self.plotCanvas.Draw, gc)



    def updateHandbrakeValues(self):
        while self.running:
            self.data_raw = []  # Initialize data list for raw values
            self.data_processed = []  # Initialize data list for processed values
            counter = 0  # Simple counter to represent time
            while True:
                if self.ser.is_open:  # Ensure the serial port is open before reading
                    line = self.ser.readline().decode('utf-8').strip()

                    rawHandbrakeValue = self.data_raw[-1][1] if self.data_raw else None
                    if rawHandbrakeValue is not None:
                        if self.autoSetMode:
                            # Update minimum and maximum values
                            if rawHandbrakeValue < self.minHandbrake.GetValue() and wx.GetApp() is not None:
                                wx.CallAfter(self.minHandbrake.SetValue, rawHandbrakeValue)
                                wx.CallAfter(self.minHandbrakeValueInput.SetValue, str(rawHandbrakeValue))
                            if rawHandbrakeValue > self.maxHandbrake.GetValue() and wx.GetApp() is not None:
                                wx.CallAfter(self.maxHandbrake.SetValue, rawHandbrakeValue)
                                wx.CallAfter(self.maxHandbrakeValueInput.SetValue, str(rawHandbrakeValue))

                    print(line)
                    if line.startswith("Raw Handbrake Value: "):
                        raw, processed = line.split("   Processed Handbrake Value: ")
                        raw = float(raw[21:])
                        processed = float(processed)

                        if wx.GetApp() is not None:
                            wx.CallAfter(self.rawHandbrakeValue.SetLabel, "Raw Handbrake Value: " + str(raw))
                            wx.CallAfter(self.processedHandbrakeValue.SetLabel, "Processed Handbrake Value: " + str(processed))

                        # Add new data point to list
                        self.data_raw.append((counter, raw))
                        self.data_processed.append((counter, processed))
                        # Remove oldest data point if list is too long
                        if len(self.data_raw) > 100:
                            self.data_raw.pop(0)
                            self.data_processed.pop(0)

                    
                        # Plot curve
                        self.plotCurve()
                        
                        counter += 1  # Increment counter


                    ''' Curve type: EXPONENTIAL
                        Min raw handbrake: 10000.00
                        Max raw handbrake: 2095588.00
                        Curve factor: 2.00
                    '''                

                    if line.startswith("Curve type: "):
                        curve_type = line.split(":")[1].strip()
                        selection = self.curveTypeChoices.index(curve_type)
                        if wx.GetApp() is not None:
                            wx.CallAfter(self.curveType.SetSelection, selection) 

                    if line.startswith("Min raw handbrake: "):
                        min_handbrake = float(line.split(":")[1])
                        wx.CallAfter(self.minHandbrakeValueInput.SetValue, str(min_handbrake))
                        if wx.GetApp() is not None:
                            wx.CallAfter(self.minHandbrake.SetValue, min_handbrake)

                    if line.startswith("Max raw handbrake: "):
                        max_handbrake = float(line.split(":")[1])
                        wx.CallAfter(self.maxHandbrakeValueInput.SetValue, str(max_handbrake))
                        if wx.GetApp() is not None:
                            wx.CallAfter(self.maxHandbrake.SetValue, max_handbrake)

                    if line.startswith("Curve factor: "):
                        curve_factor = float(line.split(":")[1])
                        
                        wx.CallAfter(self.curveFactorValueInput.SetValue, str(curve_factor / 10 ))
                        if wx.GetApp() is not None:
                            wx.CallAfter(self.curveFactor.SetValue, curve_factor)

if __name__ == "__main__":
    app = wx.App(False)
    frame = HandbrakeController()
    frame.Show()
    app.MainLoop()
