# Handbrake Controller GUI

This project provides a graphical user interface (GUI) for controlling an Arduino-based handbrake. The GUI is implemented in Python using the wxPython library.

## Features

- Selection of curve type (LINEAR, EXPONENTIAL, LOGARITHMIC)
- Adjustment of min/max handbrake values
- Adjustment of curve factor
- Saving settings to EEPROM
- Toggling setup mode
- Displaying raw and processed handbrake values
- Selection of serial port

## Requirements

- Python 3.6 or higher
- wxPython 4.1.1 or higher
- pySerial 3.5 or higher

## Installation

1. Clone this repository or download the source code.
2. Install the required Python libraries using pip:

    ```bash
    pip install -r requirements.txt
    ```

3. Run `handbrake_controller.py`:

    ```bash
    python handbrake_controller.py
    ```

## Usage

1. Select the serial port connected to your Arduino.
2. Adjust the handbrake settings as needed.
3. Click 'Save Settings' to save the current settings to EEPROM.
4. Check 'Toggle Setup Mode' to toggle setup mode.

