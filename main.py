"""
main.py

This script runs on a LoPy4 with a Pysense 2 board. It reads temperature,
humidity, and barometric pressure, sends the data to The Things Network (TTN)
via LoRaWAN (OTAA), and then enters deep sleep for 3 hours.

Instructions:
1. Connect the Pysense 2 board to the LoPy4.
2. Replace the placeholder values for `DEV_EUI`, `APP_EUI`, and `APP_KEY`
   with the credentials from your TTN application.
3. Upload the script to your LoPy4 as `main.py`.
4. Ensure the `lib` folder on your device contains the necessary libraries
   for the Pysense 2 sensors (SI7006A20, MPL3115A2). These are typically
   part of the standard Pycom firmware.
"""

import time
import pycom
import ubinascii
import ustruct
from machine import Pin, deepsleep
from network import LoRa
from pysense import Pysense
from SI7006A20 import SI7006A20
from MPL3115A2 import MPL3115A2

# Disable the heartbeat LED to save power
pycom.heartbeat(False)

# --- LoRaWAN Configuration ---
# Replace with your device credentials from TTN
DEV_EUI = ubinascii.unhexlify('0000000000000000')  # Your Device EUI
APP_EUI = ubinascii.unhexlify('0000000000000000')  # Your Application EUI
APP_KEY = ubinascii.unhexlify('00000000000000000000000000000000') # Your Application Key

# LoRaWAN region
# Options: LoRa.AS923, LoRa.AU915, LoRa.EU868, LoRa.US915, etc.
LORA_REGION = LoRa.EU868

# Deep sleep duration in milliseconds (3 hours)
DEEP_SLEEP_DURATION_MS = 3 * 60 * 60 * 1000

# --- Sensor and LoRa Initialization ---
try:
    # Initialize Pysense board and sensors
    py = Pysense()
    si = SI7006A20(py)
    mpl = MPL3115A2(py, mode=MPL3115A2.PRESSURE) # Set to pressure mode

    # Initialize LoRa in LoRaWAN mode
    lora = LoRa(mode=LoRa.LORAWAN, region=LORA_REGION)

    print("--- LoRaWAN/Sensor Setup ---")
    print("DEV EUI: {}".format(ubinascii.hexlify(lora.mac()).decode('ascii').upper()))
    print("APP EUI: {}".format(ubinascii.hexlify(APP_EUI).decode('ascii').upper()))
    print("APP KEY: {}".format(ubinascii.hexlify(APP_KEY).decode('ascii').upper()))

    # Join the network using OTAA (Over the Air Activation)
    lora.join(activation=LoRa.OTAA, auth=(DEV_EUI, APP_EUI, APP_KEY), timeout=0)

    # Wait until the module has joined the network
    while not lora.has_joined():
        time.sleep(2.5)
        print('Not joined yet...')

    print('Network joined!')

    # Create a LoRa socket
    s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
    s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5) # Set data rate
    s.setblocking(True)

    # --- Main Logic ---
    print("Reading sensor data...")
    temperature = si.temperature()
    humidity = si.humidity()
    pressure = mpl.pressure() / 100 # Convert Pa to hPa for easier decoding

    print("Temperature: {:.2f} C".format(temperature))
    print("Humidity: {:.2f} %RH".format(humidity))
    print("Pressure: {:.2f} hPa".format(pressure))

    # Pack the data into a compact byte structure for transmission
    # Format:
    # - Temperature: signed short (2 bytes), value * 100
    # - Humidity: unsigned short (2 bytes), value * 100
    # - Pressure: unsigned short (2 bytes), value * 100
    # Total payload: 6 bytes
    payload = ustruct.pack('>hHH',
                           int(temperature * 100),
                           int(humidity * 100),
                           int(pressure * 100))

    print("Sending packed data ({} bytes): {}".format(len(payload), ubinascii.hexlify(payload)))
    s.send(payload)
    print("Data sent successfully.")

except Exception as e:
    print("An error occurred: {}".format(e))

finally:
    # --- Deep Sleep ---
    print("Entering deep sleep for 3 hours...")
    py.setup_sleep(DEEP_SLEEP_DURATION_MS)
    py.go_to_sleep()
