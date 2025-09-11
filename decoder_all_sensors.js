// TTN / The Things Stack v3 (JavaScript)
// Matches the 20-byte payload from main.py
function decodeUplink(input) {
  const bytes = input.bytes;
  if (!bytes || bytes.length !== 20) {
    return {
      errors: [`Invalid payload length ${bytes ? bytes.length : 0}, expected 20 bytes`],
    };
  }

  let i = 0;
  const rU16 = () => ((bytes[i++] << 8) | bytes[i++]) >>> 0;
  const rI16 = () => {
    const v = (bytes[i++] << 8) | bytes[i++];
    return (v & 0x8000) ? v - 0x10000 : v;

  };

  const data = {
    temperature_c: rI16() / 100.0,
    humidity_rh: rU16() / 100.0,
    pressure_hpa: rU16() / 10.0,
    altitude_m: rI16(),
    light_blue: rU16(),        // raw channel (0..65535)
    light_red: rU16(),         // raw channel (0..65535)
    accel_mg: {
      x: rI16(),
      y: rI16(),
      z: rI16(),
    },
    vbat_mV: rU16(),
  };
  return { data };
}