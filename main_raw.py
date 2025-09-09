"""
main_raw.py

A minimal script for a LoPy4 with a Pysense 2 board that reads raw byte
data directly from the I2C sensors and sends it over LoRaWAN. This method
avoids using the `ustruct` library and floating-point conversions on the
device.

NOTE: The raw sensor data must be decoded on the server-side (e.g., using
a TTN payload decoder) to be interpreted as meaningful values.
"""

import pycom
import ubinascii
import socket
import time
from machine import deepsleep
from network import LoRa
from pysense import Pysense

# --- Configuration ---
pycom.heartbeat(False)

# LoRaWAN Credentials (replace with your actual values)
DEV_EUI = ubinascii.unhexlify('0000000000000000')
APP_EUI = ubinascii.unhexlify('0000000000000000')
APP_KEY = ubinascii.unhexlify('00000000000000000000000000000000')

# LoRaWAN Region
LORA_REGION = LoRa.EU868

# Deep sleep duration (3 hours in milliseconds)
DEEP_SLEEP_DURATION_MS = 10800000

# I2C Sensor Addresses
SI7006A20_ADDR = 0x40
MPL3115A2_ADDR = 0x60

# --- Main Execution ---
try:
    # --- Initialization ---
    py = Pysense()
    i2c = py.i2c

    # --- MPL3115A2 (Pressure) Sensor Setup ---
    # This sensor must be configured before it can be read.
    # 1. Write 0x38 to CTRL_REG1 (0x26): Sets OSR=128, Barometer mode.
    # 2. Write 0x07 to PT_DATA_CFG (0x13): Enables data ready event flags.
    # 3. Write 0x39 to CTRL_REG1 (0x26): Sets the device to active.
    i2c.writeto_mem(MPL3115A2_ADDR, 0x26, b'\x38')
    i2c.writeto_mem(MPL3115A2_ADDR, 0x13, b'\x07')
    i2c.writeto_mem(MPL3115A2_ADDR, 0x26, b'\x39')

    # --- LoRaWAN Setup ---
    lora = LoRa(mode=LoRa.LORAWAN, region=LORA_REGION)
    lora.join(activation=LoRa.OTAA, auth=(DEV_EUI, APP_EUI, APP_KEY), timeout=0)
    while not lora.has_joined():
        time.sleep_ms(100) # Conserve power while waiting

    s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
    s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
    s.setblocking(True)

    # --- Read Raw Sensor Bytes ---

    # 1. Read Humidity from SI7006A20
    i2c.writeto(SI7006A20_ADDR, b'\xF5') # Trigger humidity measurement
    time.sleep_ms(30) # Wait for measurement
    hum_bytes = i2c.readfrom(SI7006A20_ADDR, 2)

    # 2. Read Temperature from SI7006A20
    i2c.writeto(SI7006A20_ADDR, b'\xF3') # Trigger temperature measurement
    time.sleep_ms(30) # Wait for measurement
    temp_bytes = i2c.readfrom(SI7006A20_ADDR, 2)

    # 3. Read Pressure from MPL3115A2
    # Wait for the 'Pressure Data Ready' flag in the STATUS register (0x00)
    while not (i2c.readfrom_mem(MPL3115A2_ADDR, 0x00, 1)[0] & 0x08):
        time.sleep_ms(10)
    # Read the 3 pressure bytes from OUT_P_MSB (0x01)
    pressure_bytes = i2c.readfrom_mem(MPL3115A2_ADDR, 0x01, 3)

    # --- Transmit Payload ---
    # Concatenate all sensor bytes into a single 7-byte payload
    payload = hum_bytes + temp_bytes + pressure_bytes
    s.send(payload)

finally:
    # --- Deep Sleep ---
    py.setup_sleep(DEEP_SLEEP_DURATION_MS)
    py.go_to_sleep()
