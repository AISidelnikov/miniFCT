#include "minifct/config.hpp"
#include "minifct/hal.hpp"
#include "minifct/protocol.hpp"

#include "esp_log.h"
#include <cstdio>
#include <cstring>

namespace {
constexpr char kTag[] = "MiniFCT";
constexpr size_t kLineBufferSize = 512;
}

extern "C" void app_main(void) {
  minifct::hal::init();
  ESP_LOGI(kTag, "%s firmware %s starting", minifct::config::kDeviceName,
           minifct::config::kFirmwareVersion);
  printf("{\"ok\":true,\"type\":\"boot\",\"device\":\"MiniFCT\",\"firmware_version\":\"%s\"}\n",
         minifct::config::kFirmwareVersion);

  // PlatformIO's ESP-IDF default console is used as the JSON Lines transport.
  // Send one JSON object per line at 115200 baud.
  char line[kLineBufferSize];

  while (true) {
    if (std::fgets(line, sizeof(line), stdin) == nullptr) {
      if (std::feof(stdin) || std::ferror(stdin)) {
        // Avoid a busy loop if the console reaches EOF or reports an error.
        std::clearerr(stdin);
        vTaskDelay(pdMS_TO_TICKS(10));
      }
      continue;
    }

    const size_t length = std::strlen(line);

    if (length > 0 && line[length - 1] == '\n') {
      line[length - 1] = '\0';
    } else if (length == sizeof(line) - 1) {
      int ch;
      while ((ch = std::getchar()) != '\n' && ch != EOF) {
        vTaskDelay(1);
      }

      printf("{\"ok\":false,\"error\":\"command_too_long\"}\n");
      continue;
    }

    minifct::protocol_handle_line(line);
  }
}
