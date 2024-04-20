# CANMOPS for MOPS Readout

CANMOPS is a free CAN bus monitor and general-purpose diagnostic tool available for Windows and Linux. The software package offers a comprehensive set of functions and a graphical user interface (GUI) to facilitate communication with the [DCS ASIC: Monitoring Of Pixel System (MOPS)](https://edms.cern.ch/ui/file/1909505/3/MOPS-specs-V3_docx_cpdf.pdf), supported by CAN interfaces from [AnaGate (Ethernet)](https://www.anagate.de/), [Kvaser (USB)](https://www.kvaser.com/), and [SocketCAN Kernel](https://www.kernel.org/doc/html/latest/networking/can.html).
![CANMOPS](https://gitlab.cern.ch/mops/canmops/-/wikis/uploads/133057f8a2ba5ebd7f595cd72aa86547/phd_designs__9_.png)

## General Features
- History list for sent messages.
- Time-stamping of incoming and outgoing messages, displayed in both absolute and relative formats.
- CAN bus statistics including number of messages and bus load.
- Traffic generator to simulate heavy bus load conditions.
- Capability to log data to a file.

## Installation and Usage

### System Requirements
- **Operating System:** Windows, Linux

### Required Python Packages
- A [Python 3.9 or higher](https://www.python.org/) installation is necessary. [Anaconda](https://anaconda.org/) is recommended for easy installation and management across all platforms. Detailed installation instructions are available on the [CANMOPS Twiki page](https://gitlab.cern.ch/mops/canmops/-/wikis/CANMOPS-Twiki-page).

### Getting Started
Clone the repository to download the source code:
```
ssh://git@gitlab.cern.ch:7999/mops/canmops.git
```
Ensure the CAN interface is connected and the required software is installed. To test the setup, run the following command in the home directory:

```
python canmops_test.py
```
### Scanning Node IDs on the Bus:
To verify that all nodes connected on the bus are operational and ready for communication, it is important to know the exact pre-defined Node ID for each node under test. Use the following command template to scan the Node IDs:

```
python canmops/can_wrapper_main.py -S -b 111111 -sp 0.3 -sjw 4 -tseg1 5 -tseg2 6 -nodeid 0
```
Replace the -S argument based on the interface used (-S for SocketCAN, -K for Kvaser, -A for AnaGate), and adjust the -nodeid argument according to the specific Node ID of the chip.

## Contributing and Contact Information:
We welcome contributions from the community please contact : `ahmed.qamesh@cern.ch`.
