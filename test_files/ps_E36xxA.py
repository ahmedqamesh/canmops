########################################################
"""
    This file is part of the MOPS-Hub project.
    Author: Ahmed Qamesh (University of Wuppertal)
    email: ahmed.qamesh@cern.ch  
    Date: 01.05.2020
"""
########################################################
#pip install pyvisa
#The script is dedicated for Agilent E364xA  https://www.tme.eu/Document/9f3996689f24777703b84ff64b156944/E3646-90001.pdf
import visa
import time
def control_power():
    # Initialize the PyVISA library
    rm = visa.ResourceManager()
    # List available VISA resources
    resources = rm.list_resources()
    print("Available VISA Resources:")
    for resource in resources:
        print(resource)
        
    # Open a connection to the power supply
    power_supply = rm.open_resource('ASRL/dev/ttyUSB1::INSTR')  # Use the appropriate VISA resource name
    power_supply.timeout = 10000  # Set a longer timeout (in milliseconds)
    # Query the instrument's identification
    identification = power_supply.query('*IDN?')
    print(f"Instrument Identification: {identification}")
    
    output_enabled = power_supply.query('OUTP?')
    print(f"Output 1 Enabled: {output_enabled}")
    
    # Set the voltage and current for Output 1
    power_supply.write('INST OUT1')  # Select Output 1
    power_supply.write('VOLT 5.0')   # Set the voltage for Output 1 to 5.0 V
    power_supply.write('CURR 1.0')   # Set the current for Output 1 to 1.0 A
    time.sleep(5)  # Wait for 5 seconds
    voltage_setting_output_1 = float(power_supply.query('VOLT?'))
    print(f"Voltage Setting for Output 1: {voltage_setting_output_1} V")
    # Read back the current for Output 1
    current_output1 = power_supply.query('CURR?')
    print(f"Current for Output 1: {current_output1} A")
    time.sleep(5)  # Wait for 5 seconds
    # Set the voltage and current for Output 2
    power_supply.write('INST OUT2')  # Select Output 2
    power_supply.write('VOLT 4.0')  # Set the voltage for Output 2 to 12.0 V
    power_supply.write('CURR 2.0')   # Set the current for Output 2 to 2.0 A
    time.sleep(5)  # Wait for 5 seconds
    
    voltage_setting_output_2 = float(power_supply.query('VOLT?'))
    print(f"Voltage Setting for Output 2: {voltage_setting_output_2} V")
    # Read back the current for Output 1
    current_output2 = power_supply.query('CURR?')
    print(f"Current for Output 2: {current_output2} A")
    # Please add your trim function here
    # Disable both outputs after a delay
    time.sleep(5)  # Wait for 5 seconds
    #power_supply.write('OUTP OFF')  # Turn off both outputs
    # Close the connection
    #power_supply.close()

control_power()
