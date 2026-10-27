#include "minifct/protocol.hpp"
#include "minifct/config.hpp"
#include "minifct/test_engine.hpp"
#include "minifct/hal.hpp"

#include "cJSON.h"
#include <cstdio>
#include <cstring>

namespace minifct {
namespace {
void send_error(const char* message) {
  cJSON* root = cJSON_CreateObject();
  cJSON_AddBoolToObject(root, "ok", false);
  cJSON_AddStringToObject(root, "error", message);
  char* output = cJSON_PrintUnformatted(root);
  if (output) { printf("%s\n", output); cJSON_free(output); }
  cJSON_Delete(root);
}

void send_info() {
  size_t count = 0;
  const TestDefinition* tests = test_registry(count);
  cJSON* root = cJSON_CreateObject();
  cJSON_AddBoolToObject(root, "ok", true);
  cJSON_AddStringToObject(root, "device", config::kDeviceName);
  cJSON_AddStringToObject(root, "firmware_version", config::kFirmwareVersion);
  cJSON_AddStringToObject(root, "protocol_version", config::kProtocolVersion);
  cJSON* array = cJSON_AddArrayToObject(root, "tests");
  for (size_t i = 0; i < count; ++i) cJSON_AddItemToArray(array, cJSON_CreateString(tests[i].name));
  char* output = cJSON_PrintUnformatted(root);
  if (output) { printf("%s\n", output); cJSON_free(output); }
  cJSON_Delete(root);
}

void send_test_result(const TestResult& r) {
  cJSON* root = cJSON_CreateObject();
  cJSON_AddBoolToObject(root, "ok", true);
  cJSON_AddStringToObject(root, "type", "test_result");
  cJSON_AddStringToObject(root, "test", r.name);
  cJSON_AddBoolToObject(root, "passed", r.passed);
  cJSON_AddBoolToObject(root, "implemented", r.implemented);
  cJSON_AddNumberToObject(root, "value", r.value);
  cJSON_AddStringToObject(root, "unit", r.unit);
  cJSON_AddStringToObject(root, "message", r.message);
  char* output = cJSON_PrintUnformatted(root);
  if (output) { printf("%s\n", output); cJSON_free(output); }
  cJSON_Delete(root);
}
}

void protocol_handle_line(const char* line) {
  if (!line || std::strlen(line) == 0) return;
  cJSON* root = cJSON_Parse(line);
  if (!root) { send_error("invalid_json"); return; }
  const cJSON* cmd_item = cJSON_GetObjectItemCaseSensitive(root, "cmd");
  const char* cmd = cJSON_IsString(cmd_item) ? cmd_item->valuestring : "";

  if (std::strcmp(cmd, "INFO") == 0) {
    send_info();
  } else if (std::strcmp(cmd, "RUN_ALL") == 0) {
    run_all_tests();
    hal::safe_state();
  } else if (std::strcmp(cmd, "RUN") == 0) {
    const cJSON* test_item = cJSON_GetObjectItemCaseSensitive(root, "test");
    const char* test_name = cJSON_IsString(test_item) ? test_item->valuestring : "";
    TestResult result{};
    if (!run_test(test_name, result)) send_error("unknown_test");
    else send_test_result(result);
    hal::safe_state();
  } else {
    send_error("unknown_command");
  }
  cJSON_Delete(root);
}
}
