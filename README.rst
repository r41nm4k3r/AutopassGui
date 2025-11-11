Autopass GUI
============

A cross-platform desktop application for controlling Arduino Pro Micro (Leonardo) based automatic password entry systems.

Features
--------

* **Serial Communication**: Connect to Arduino devices via USB serial ports
* **Configurable Passwords**: Set up to 4 different password sequences
* **Custom Commands**: Send custom commands to the Arduino
* **Dark/Light Theme**: Toggle between dark and light UI themes
* **Cross-Platform**: Works on Windows, macOS, and Linux

Installation
------------

**Linux (Debian/Ubuntu)**::

    sudo dpkg -i autopassgui_1.0.0-1~debian-trixie_amd64.deb

**Linux (Universal - AppImage)**::

    chmod +x Autopass_GUI-1.0.0-x86_64.AppImage
    ./Autopass_GUI-1.0.0-x86_64.AppImage

**Windows**::

    Run the .msi installer

Usage
-----

1. Launch the application
2. Select your Arduino's serial port from the dropdown
3. Click "Connect" to establish connection
4. Use the password buttons to send commands
5. Customize button labels by clicking the pencil icon
6. Toggle dark/light theme using the moon/sun button

Building from Source
--------------------

Install dependencies::

    pip install briefcase

Build for your platform::

    briefcase dev         # Run in development mode
    briefcase build       # Build the app
    briefcase package     # Create installer package

License
-------

See LICENSE file for details

.. _`Briefcase`: https://briefcase.readthedocs.io/
.. _`The BeeWare Project`: https://beeware.org/
.. _`becoming a financial member of BeeWare`: https://beeware.org/contributing/membership
