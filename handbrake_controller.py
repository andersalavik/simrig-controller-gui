import wx
from wx.lib.plot import PolyLine, PlotCanvas, PlotGraphics, PolyMarker
import serial
from serial.tools import list_ports
import threading
import numpy as np
import time

class HandbrakeController(wx.Frame):
    def __init__(self):
        super().__init__(None, wx.ID_ANY, "Handbrake Controller", size=(800,600))
        self.running = True

        # Serial communication setup
        self.ser = serial.Serial(baudrate=9600, timeout=1)

        # GUI elements
        self.initialize_gui_elements()

        # Event bindings
        self.bind_events()

        # Start thread to update handbrake values
        self.updateThread = threading.Thread(target=self.updateHandbrakeValues)
        self.updateThread.start()
        
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def initialize_gui_elements(self):
        # Initialize GUI elements and layout
        self.portSelection = self.create_and_append_ports()
        self.autoSetMode = False
        self.connectButton = wx.Button(self, label="Connect")  
        self.curveTypeChoices = ['LINEAR', 'EXPONENTIAL', 'LOGARITHMIC']
        self.curveType = wx.Choice(self, choices=self.curveTypeChoices)
        self.initialize_sliders_and_texts()
        self.saveButton = wx.Button(self, label="Save Settings")
        self.setupModeToggle = wx.CheckBox(self, label="Toggle Setup Mode")
        self.setupModeToggle.Hide()
        self.plotCanvas = PlotCanvas(self)
        self.rawHandbrakeValue = wx.StaticText(self, label="Raw Handbrake Value: ")
        self.processedHandbrakeValue = wx.StaticText(self, label="Processed Handbrake Value: ")
        self.initialize_layout()


    def initialize_sliders_and_texts(self):
        # Initialize sliders and corresponding text fields
        self.minHandbrake, self.minHandbrakeValueInput = self.create_slider_and_text(-5200, -10000, 3000000)
        self.maxHandbrake, self.maxHandbrakeValueInput = self.create_slider_and_text(50000, -10000, 3000000)
        self.curveFactor, self.curveFactorValueInput = self.create_slider_and_text(20, 0, 100)

    def create_and_append_ports(self):
        # Create port selection combo box and append available ports
        portSelection = wx.ComboBox(self)
        ports = list_ports.comports()
        for port in ports:
            portSelection.Append(port.device)
        return portSelection

    def create_slider_and_text(self, value, minValue, maxValue):
        # Create slider and corresponding text field
        slider = wx.Slider(self, value=value, minValue=minValue, maxValue=maxValue, style=wx.SL_HORIZONTAL)
        text = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        return slider, text

    def initialize_layout(self):
        # Initialize layout for GUI
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Put portSelection and connectButton in the same hbox
        hbox_connect = wx.BoxSizer(wx.HORIZONTAL)
        hbox_connect.Add(self.portSelection, proportion=1, flag=wx.EXPAND)
        hbox_connect.Add(self.connectButton, proportion=0)
        vbox.Add(hbox_connect, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # Other hbox elements
        hbox_list = [self.create_hbox(element) for element in [self.curveType,
                                                            self.minHandbrake, self.maxHandbrake, self.curveFactor,
                                                            self.saveButton, self.setupModeToggle,
                                                            self.rawHandbrakeValue, self.processedHandbrakeValue]]

        # Create a grid sizer with 1 row and 1 column for the PlotCanvas
        grid_sizer = wx.GridSizer(1, 1, 5, 5)
        grid_sizer.Add(self.plotCanvas, 1, wx.EXPAND)

        # Add the grid sizer to the vbox
        vbox.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 5)

        for hbox in hbox_list:
            vbox.Add(hbox, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        self.autoSetButton = wx.Button(self, label="Auto Set")
        vbox.Add(self.autoSetButton, flag=wx.EXPAND|wx.ALL, border=10)

        self.SetSizer(vbox)


    def create_hbox(self, element):
        # Create horizontal box for layout
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(element, proportion=1)
        if isinstance(element, wx.Slider):
            hbox.Add(self.get_corresponding_text(element))
        return hbox

    def get_corresponding_text(self, slider):
        # Get corresponding text field for a given slider
        if slider == self.minHandbrake:
            return self.minHandbrakeValueInput
        elif slider == self.maxHandbrake:
            return self.maxHandbrakeValueInput
        elif slider == self.curveFactor:
            return self.curveFactorValueInput

    def bind_events(self):
        # Bind events to GUI elements
        self.connectButton.Bind(wx.EVT_BUTTON, self.onConnectButton)
        self.curveType.Bind(wx.EVT_CHOICE, self.onCurveTypeChange)
        self.minHandbrake.Bind(wx.EVT_SLIDER, self.onSliderChange)
        self.maxHandbrake.Bind(wx.EVT_SLIDER, self.onSliderChange)
        self.curveFactor.Bind(wx.EVT_SLIDER, self.onSliderChange)
        self.saveButton.Bind(wx.EVT_BUTTON, self.onSaveButton)
        self.setupModeToggle.Bind(wx.EVT_CHECKBOX, self.onSetupModeToggle)
        #self.configButton.Bind(wx.EVT_BUTTON, self.onConfigButton)
        self.minHandbrakeValueInput.Bind(wx.EVT_TEXT_ENTER, self.onTextEnter)
        self.maxHandbrakeValueInput.Bind(wx.EVT_TEXT_ENTER, self.onTextEnter)
        self.curveFactorValueInput.Bind(wx.EVT_TEXT_ENTER, self.onTextEnter)
        self.autoSetButton.Bind(wx.EVT_BUTTON, self.onAutoSetButton)

    def onSliderChange(self, event):
        # Event handler for slider changes
        slider = event.GetEventObject()
        value = slider.GetValue()
        text = self.get_corresponding_text(slider)
        text.SetValue(str(value))
        self.ser.write(bytes(f'{self.get_slider_prefix(slider)}{value}', 'utf-8'))
        self.plotCurve()  # Update curve

    def get_slider_prefix(self, slider):
        # Get corresponding prefix for a given slider
        if slider == self.minHandbrake:
            return 'm'
        elif slider == self.maxHandbrake:
            return 't'
        elif slider == self.curveFactor:
            return 'f'

    def onTextEnter(self, event):
        # Event handler for text enter events
        text = event.GetEventObject()
        value = int(event.GetString())
        slider = self.get_corresponding_slider(text)
        slider.SetValue(value)
        text.SetValue(str(value))
        self.ser.write(bytes(f'{self.get_slider_prefix(slider)}{value}', 'utf-8'))

    def get_corresponding_slider(self, text):
        # Get corresponding slider for a given text field
        if text == self.minHandbrakeValueInput:
            return self.minHandbrake
        elif text == self.maxHandbrakeValueInput:
            return self.maxHandbrake
        elif text == self.curveFactorValueInput:
            return self.curveFactor

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
