#include "minifct/test_engine.hpp"
#include "minifct/hal.hpp"
#include "minifct/config.hpp"
#include "minifct/protocol.hpp"

#include "cJSON.h"
#include <cstring>
#include <cstdio>

namespace minifct {
namespace {
TestResult test_firmware_identity() {
  return {"firmware_identity", true, true, 1.0, "bool", "Firmware initialized"};
}

TestResult test_digital_loopback() {
  bool passed = false;
  const bool executed = hal::digital_loopback_test(passed);
  if (!executed) {
    return {"digital_loopback", false, true, 0.0, "bool", "GPIO setup failed"};
  }
  return {"digital_loopback", passed, true, passed ? 1.0 : 0.0, "bool",
          passed ? "Loopback OK" : "Loopback failed; check GPIO25-GPIO26 jumper"};
}

TestResult test_supply_voltage_placeholder() {
  return {"supply_voltage", false, false, 0.0, "V",
          "Not implemented: add protected, calibrated external measurement hardware"};
}

const TestDefinition kTests[] = {
  {"firmware_identity", test_firmware_identity},
  {"digital_loopback", test_digital_loopback},
  {"supply_voltage", test_supply_voltage_placeholder},
};
}

const TestDefinition* test_registry(size_t& count) {
  count = sizeof(kTests) / sizeof(kTests[0]);
  return kTests;
}

bool run_test(const char* name, TestResult& result) {
  if (name == nullptr) return false;
  size_t count = 0;
  const TestDefinition* tests = test_registry(count);
  for (size_t i = 0; i < count; ++i) {
    if (std::strcmp(name, tests[i].name) == 0) {
      result = tests[i].run();
      return true;
    }
  }
  return false;
}

void run_all_tests() {
  size_t count = 0;
  const TestDefinition* tests = test_registry(count);
  cJSON* root = cJSON_CreateObject();
  cJSON_AddBoolToObject(root, "ok", true);
  cJSON_AddStringToObject(root, "type", "run_complete");
  cJSON_AddStringToObject(root, "device", config::kDeviceName);
  cJSON_AddStringToObject(root, "firmware_version", config::kFirmwareVersion);
  cJSON* results = cJSON_AddArrayToObject(root, "results");
  bool all_passed = true;
  size_t passed_count = 0;
  size_t executed_count = 0;

  for (size_t i = 0; i < count; ++i) {
    const TestResult r = tests[i].run();
    cJSON* item = cJSON_CreateObject();
    cJSON_AddStringToObject(item, "test", r.name);
    cJSON_AddBoolToObject(item, "passed", r.passed);
    cJSON_AddBoolToObject(item, "implemented", r.implemented);
    cJSON_AddNumberToObject(item, "value", r.value);
    cJSON_AddStringToObject(item, "unit", r.unit);
    cJSON_AddStringToObject(item, "message", r.message);
    cJSON_AddItemToArray(results, item);

    if (r.implemented) {
      ++executed_count;
      if (r.passed) ++passed_count;
      else all_passed = false;
    } else {
      // Do not silently report PASS while any configured test is unimplemented.
      all_passed = false;
    }
  }

  cJSON_AddBoolToObject(root, "passed", all_passed);
  cJSON_AddNumberToObject(root, "passed_count", static_cast<double>(passed_count));
  cJSON_AddNumberToObject(root, "executed_count", static_cast<double>(executed_count));
  cJSON_AddNumberToObject(root, "configured_count", static_cast<double>(count));
  char* serialized = cJSON_PrintUnformatted(root);
  if (serialized) {
    printf("%s\n", serialized);
    cJSON_free(serialized);
  }
  cJSON_Delete(root);
}
}
