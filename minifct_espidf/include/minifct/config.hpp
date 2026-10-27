#pragma once
#include <cstdint>

namespace minifct::config {
inline constexpr char kDeviceName[] = "MiniFCT";
inline constexpr char kFirmwareVersion[] = "0.1.0";
inline constexpr char kProtocolVersion[] = "1";
inline constexpr uint32_t kSerialBaud = 115200;

// ESP32-WROOM-32 / generic ESP32 DevKit example pin assignment.
// GPIO25 -> jumper -> GPIO26 for the loopback test.
inline constexpr int kLoopOutPin = 25;
inline constexpr int kLoopInPin = 26;

// ADC measurement is deliberately not enabled in this scaffold. The final
// product should use a calibrated ADC / current-sense front end and validated
// input protection rather than treating the ESP32 ADC as a precision meter.
}
