# main.py  — LoPy4 + Pysense 2.0 X → LoRaWAN (TTN/TTS v3)
# Reads all Pysense sensors and sends a compact 20-byte payload.
import time, struct, binascii
import pycom
from network import LoRa
import socket

# ---- Pysense sensor drivers ----
from pysense import Pysense
from LIS2HH12 import LIS2HH12        # accelerometer (g)  [3](https://docs.pycom.io/firmwareapi/pycom/expansionboards/lis2hh12/)
from LTR329ALS01 import LTR329ALS01  # light, two channels (0..65535)  [4](https://docs.pycom.io/firmwareapi/pycom/expansionboards/ltr329als01/)
from MPL3115A2 import MPL3115A2, ALTITUDE, PRESSURE  # pressure (Pa) / altitude (m)  [2](https://docs.pycom.io/tutorials/expansionboards/pysense2/)
from SI7006A20 import SI7006A20      # temperature (°C), humidity (%RH)  [11](https://github.com/brocaar/pycom-examples/blob/master/pysense-example/lib/SI7006A20.py)

# ------------- USER CONFIG -------------
LORA_REGION = LoRa.EU868      # change if needed (AS923, US915, AU915, IN865, CN470)  [5](https://docs.pycom.io/firmwareapi/pycom/network/lora/)
UPLINK_FPORT = 1              # application fPort on TTN
SEND_PERIOD_S = 300           # send every 5 minutes

# TTN/TTS OTAA credentials (copy from the console; MSB/hex)
APP_EUI = binascii.unhexlify('70B3D57ED0XXXXXX')  # JoinEUI/AppEUI
APP_KEY = binascii.unhexlify('00112233445566778899AABBCCDDEEFF')

# ------------- SETUP -------------
pycom.heartbeat(False)

# Initialize LoRa (LoRaWAN 1.0.2 stack on LoPy4)  [5](https://docs.pycom.io/firmwareapi/pycom/network/lora/)
lora = LoRa(mode=LoRa.LORAWAN, region=LORA_REGION)

# Optional: print DevEUI (use this in TTS if you prefer)
print("DevEUI:", binascii.hexlify(lora.mac()).upper())

# EU868 best-practice: make sure the 3 default channels are TTN-compatible (before OTAA join)  [7](https://github.com/pycom/pycom-libraries/blob/master/examples/lorawan-regional-examples/main_EU868.py)
if LORA_REGION == LoRa.EU868:
    lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
    lora.add_channel(1, frequency=868300000, dr_min=0, dr_max=5)
    lora.add_channel(2, frequency=868500000, dr_min=0, dr_max=5)

    # Remove others to be conservative (TTN will reconfigure after join if needed)
    for i in range(3, 16):
        try:
            lora.remove_channel(i)
        except Exception:
            pass

# Join OTAA (Two-parameter form uses DevEUI = LoRa MAC by default)  [6](https://docs.pycom.io/tutorials/networks/lora/lorawan-otaa/)
print("Joining LoRaWAN (OTAA)...")
lora.join(activation=LoRa.OTAA, auth=(APP_EUI, APP_KEY), timeout=0)

while not lora.has_joined():
    time.sleep(2.5)
    print("  …not joined yet")

print("Joined!")

# Create LoRaWAN socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# Set data rate (EU868 DR5 = SF7BW125; adjust for your region/policy)  [7](https://github.com/pycom/pycom-libraries/blob/master/examples/lorawan-regional-examples/main_EU868.py)
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)

# Use a specific FPort
try:
    s.bind(UPLINK_FPORT)  # sets LoRaWAN FPort on Pycom  [8](https://forum.pycom.io/topic/2735/changing-port-for-sending-data-via-lora)
except Exception:
    pass

s.setblocking(True)

# ------------- SENSOR INIT -------------
py = Pysense()
acc = LIS2HH12(py)
light = LTR329ALS01(py)
mp_alt = MPL3115A2(py, mode=ALTITUDE)   # altitude (m)
mp_prs = MPL3115A2(py, mode=PRESSURE)   # pressure (Pa)
si = SI7006A20(py)

def clamp16(v):  # signed 16-bit clamp
    return max(-32768, min(32767, int(v)))

def u16(v):      # unsigned 16-bit clamp
    return max(0, min(65535, int(v)))

def read_scaled():
    """Read sensors and scale to compact ints (20 bytes total)."""
    # Temperature & humidity
    t_c = si.temperature()             # °C (float)
    rh = si.humidity()                 # %RH (float)

    # Pressure & altitude
    p_pa = mp_prs.pressure()           # Pascals (float)
    alt_m = mp_alt.altitude()          # meters (float)

    # Light: two raw channels (blue, red), each 0..65535 counts  [4](https://docs.pycom.io/firmwareapi/pycom/expansionboards/ltr329als01/)
    ch_blue, ch_red = light.light()

    # Acceleration in g (x,y,z); convert to milli-g (mg)  [3](https://docs.pycom.io/firmwareapi/pycom/expansionboards/lis2hh12/)
    ax_g, ay_g, az_g = acc.acceleration()

    # Battery voltage (if LiPo attached)
    try:
        vbat = py.read_battery_voltage()  # volts
    except Exception:
        vbat = 0.0

    # ---- Scale & pack-friendly integers ----
    t_x100 = clamp16(round(t_c * 100))               # int16, 0.01 °C
    rh_x100 = u16(round(rh * 100))                   # uint16, 0.01 %RH
    p_hpa_x10 = u16(round(p_pa / 10.0))              # uint16, 0.1 hPa (Pa/10)
    alt_i16 = clamp16(round(alt_m))                  # int16, meters
    blue_u16 = u16(ch_blue)                          # uint16
    red_u16 = u16(ch_red)                            # uint16
    ax_mg = clamp16(round(ax_g * 1000))              # int16, mg
    ay_mg = clamp16(round(ay_g * 1000))              # int16, mg
    az_mg = clamp16(round(az_g * 1000))              # int16, mg
    vbat_mV = u16(round(vbat * 1000))                # uint16, millivolts

    return (t_x100, rh_x100, p_hpa_x10, alt_i16,
            blue_u16, red_u16, ax_mg, ay_mg, az_mg, vbat_mV)

def build_payload(fields):
    # >  = big-endian; 10 x 16-bit values = 20 bytes
    fmt = '>h H H h H H h h h H'
    return struct.pack(fmt, *fields)

while True:
    try:
        data_fields = read_scaled()
        payload = build_payload(data_fields)
        print("Sending bytes:", binascii.hexlify(payload))
        s.send(payload)
    except Exception as e:
        print("Send error:", e)

    # non-deepsleep loop; adjust period to meet your fair-use/airtime policy
    time.sleep(SEND_PERIOD_S)