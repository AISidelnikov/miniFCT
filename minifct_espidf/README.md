# MiniFCT ESP-IDF scaffold (PlatformIO)

Modular firmware starter for a MiniFCT functional tester. This is a development scaffold, not production-ready measurement equipment.

## Requirements

- VS Code
- PlatformIO IDE extension
- ESP32 DevKit based on ESP32-WROOM-32 (the `esp32dev` PlatformIO board)
- USB data cable

## Build and flash

1. Open this folder in VS Code.
2. Let PlatformIO install the Espressif32 platform and ESP-IDF toolchain.
3. Connect the ESP32 board.
4. In PlatformIO, run **Build**, then **Upload**, then **Monitor**.
5. Monitor baud rate is 115200.

This project explicitly uses `framework = espidf`, not Arduino.

## JSON Lines commands

Send one JSON object followed by a newline:

```json
{"cmd":"INFO"}
{"cmd":"RUN","test":"firmware_identity"}
{"cmd":"RUN","test":"digital_loopback"}
{"cmd":"RUN","test":"supply_voltage"}
{"cmd":"RUN_ALL"}
```

Responses are one JSON object per line. `supply_voltage` is intentionally marked `implemented: false`; do not treat it as a real measurement yet.

## Loopback test wiring

For the current example, connect GPIO25 to GPIO26 with a jumper. Run the loopback test with the DUT disconnected from those pins. GPIOs are not 5 V tolerant. Do not connect external voltages directly to ESP32 pins.

## Current scope and limitations

- Console I/O uses the default ESP-IDF serial console, normally USB-to-UART on generic ESP32 DevKit boards. Native USB CDC behavior differs by chip/board.
- The digital loopback test checks the tester's GPIO path, not a customer DUT.
- Supply-voltage and current measurement are not implemented. Add a protected, calibrated external ADC/current-sense front end and validate the analog design before claiming measurement accuracy.
- No persistent test log, DUT fixture control, calibration storage, or firmware-update flow is implemented yet.
- The initial `RUN_ALL` result is FAIL while any configured test remains unimplemented; this is deliberate to avoid a false PASS.

## Suggested next milestones

1. Add host-side Python app and serial protocol tests.
2. Add a hardware abstraction for a selected external ADC/current monitor.
3. Add fixture I/O and hardware interlocks.
4. Add calibration data with schema/version and validity checks.
5. Add CI build and pin the tested PlatformIO platform/toolchain versions.
