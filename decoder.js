function Decoder(bytes, port) {
  // Decodes the 6-byte payload from the Pysense sensor script (main.py).
  //
  // Payload structure:
  // Bytes 0-1: Temperature (signed short, big-endian), value * 100
  // Bytes 2-3: Humidity (unsigned short, big-endian), value * 100
  // Bytes 4-5: Pressure (unsigned short, big-endian), value * 100

  if (bytes.length !== 6) {
    return {
      error: "Invalid payload length. Expected 6 bytes, got " + bytes.length
    };
  }

  var TEMPERATURE_OFFSET = -3.0;

  // --- Decoding Logic ---
  var decoded = {};

  // 1. Decode Temperature (Bytes 0-1)
  // Signed short (16-bit), big-endian
  var temperature_raw = (bytes[0] << 8) | bytes[1];
  // Handle negative values for signed short
  if (temperature_raw & 0x8000) {
    temperature_raw = temperature_raw - 0x10000;
  }
  // Apply the compensation offset
  decoded.temperature_c = temperature_raw / 100.0 + TEMPERATURE_OFFSET;

  // 2. Decode Humidity (Bytes 2-3)
  // Unsigned short (16-bit), big-endian
  var humidity_raw = (bytes[2] << 8) | bytes[3];
  decoded.humidity = humidity_raw / 100.0;

  // 3. Decode Pressure (Bytes 4-5)
  // Unsigned short (16-bit), big-endian
  var pressure_raw = (bytes[4] << 8) | bytes[5];
  decoded.pressure_hpa = pressure_raw / 100.0;

  // Round values for cleaner output
  decoded.temperature_c = Math.round(decoded.temperature_c * 100) / 100;
  decoded.humidity = Math.round(decoded.humidity * 100) / 100;
  decoded.pressure_hpa = Math.round(decoded.pressure_hpa * 100) / 100;


  return decoded;
}
