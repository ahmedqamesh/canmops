# CANMOPS for DCS Controller
This Python package provides a set of functions and GUI to communicate with  the [<abbr title="Detector Control System">DCS</abbr>](https://twiki.cern.ch/twiki/bin/viewauth/Atlas/DetectorControlSystemMainPage "Only accessible with CERN account") ASIC: [Monitoring Of Pixel System (MOPS)](https://edms.cern.ch/ui/file/1909505/3/MOPS-specs-V3_docx_cpdf.pdf). It communicates with a <abbr title="Controller Area Network">CAN</abbr> interface and talks CANopen with connected MOPS. Currently CAN interfaces from [AnaGate](https://www.anagate.de/) (Ethernet), [Kvaser](https://www.kvaser.com/) (USB) and [SocketCAN Kernel](https://www.kernel.org/doc/html/latest/networking/can.html) are supported.

## Installation
This Python package requires a working [Python 3.6](https://www.python.org/ "Official Python Homepage") Installation. I recommend the usage of [Anaconda](https://anaconda.org/ "Official Anaconda Homepage") which is available for all platforms and also easy to install and manage.
```
For more information contact ahmed.qamesh@cern.ch
```
## Dependencies
All third-party Python packages that are needed can be found on the [Twiki](https://gitlab.cern.ch/aqamesh/canmops/-/wikis/home) page. The necessary AnaGate libraries are also included in this repository. For the use of Kvaser CAN interfaces you have to install the [Kvaser drivers](https://www.kvaser.com/downloads-kvaser/ "Kvaser download page") first which are avaiable for [Windows](https://www.kvaser.com/downloads-kvaser/?utm_source=software&utm_ean=7330130980013&utm_status=latest) and [Linux](https://www.kvaser.com/downloads-kvaser/?utm_source=software&utm_ean=7330130980754&utm_status=latest).

### System Requirements:
Operating System: Windows and Linux
### AnaGate interface
If you are using an AnaGate Ethernet CAN interface you will probably need to manually set the IP address of your network card so that the interface is part of its network. The default IP address of an AnaGate CAN interface is *192.168.1.254*, so you should set the IP address of your network card to *192.168.1.1*.
### Kvaser interface
It has happened that the USB port was not correctly reset after the Kvaser interface has been disconnected so that the connection to other USB devices could not be established. As a workaround I recommend rebooting the system.

## Documentation
Documentation can be found under: https://gitlab.cern.ch/aqamesh/canmops/-/wikis/home . </br>
Under development: https://canmops.readthedocs.io/en/latest/installation.html

### Installation and usage
Clone the repository to get a copy of the source code (for developers):
```
git clone ssh://git@gitlab.cern.ch:7999/aqamesh/canmops.git
```
Make sure that the CAN interface is connected and the needed software is installed.
Simply in the home directory run:
```
python CANMOPS_test.py
```
### Scanning the Node Ids connected on the bus:
In order to make sure that all the connected nodes [Mops] on the bus are healthy and ready for communication, the user need to know the exact pre-defined Node Id of the Node-under-test. 
```
python canmops/canWrapper.py -S -b 111111 -sp 0.3 -sjw 4 -tseg1 5 -tseg2 6
```
Users should replace the argument -S according to the used interface [-S for socket, -K for Kvaser and -A for Anagate].