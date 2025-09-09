function Decoder(bytes, port) {
  // Decodes the 7-byte payload from the Lopy4/Pysense raw sensor script.
  //
  // Payload structure:
  // Bytes 0-1: Raw Humidity (from SI7006A20)
  // Bytes 2-3: Raw Temperature (from SI7006A20)
  // Bytes 4-6: Raw Pressure (from MPL3115A2)

  // --- Configuration ---
  // Adjust this value based on your measurements.
  // If your sensor reads 3°C too high, set this to -3.
  var TEMPERATURE_OFFSET = -3.0;

  // --- Decoding Logic ---
  var decoded = {};

  // 1. Decode Humidity (Bytes 0-1)
  // Formula from SI7006A20 datasheet: RH = ((RH_Code * 125) / 65536) - 6
  var rh_code = (bytes[0] << 8) | bytes[1];
  decoded.humidity = ((rh_code * 125) / 65536) - 6;

  // 2. Decode Temperature (Bytes 2-3)
  // Formula from SI7006A20 datasheet: Temp_C = ((Temp_Code * 175.72) / 65536) - 46.85
  var temp_code = (bytes[2] << 8) | bytes[3];
  var raw_temperature = ((temp_code * 175.72) / 65536) - 46.85;

  // Apply the compensation offset
  decoded.temperature_c = raw_temperature + TEMPERATURE_OFFSET;

  // 3. Decode Pressure (Bytes 4-6)
  // The MPL3115A2 returns a 20-bit pressure value in Pascals with 2 fractional bits (Q18.2 format).
  // The 3 bytes represent the 20-bit value, left-justified in a 24-bit field.
  var pressure_raw = (bytes[4] << 16) | (bytes[5] << 8) | bytes[6];

  // To get the actual 20-bit value, we right-shift by 4.
  var pressure_20bit = pressure_raw >> 4;

  // The value has 2 fractional bits, so we divide by 4 to get the value in Pascals.
  var pressure_pascals = pressure_20bit / 4.0;

  // It's common to work with hectopascals (hPa), which is the same as millibars (mbar).
  decoded.pressure_hpa = pressure_pascals / 100;

  // Round values for cleaner output
  decoded.humidity = Math.round(decoded.humidity * 100) / 100;
  decoded.temperature_c = Math.round(decoded.temperature_c * 100) / 100;
  decoded.pressure_hpa = Math.round(decoded.pressure_hpa * 100) / 100;

  return decoded;
}
