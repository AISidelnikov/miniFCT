#include "minifct/hal.hpp"
#include "minifct/config.hpp"

#include "driver/gpio.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace minifct::hal {
void init() {
  gpio_reset_pin(static_cast<gpio_num_t>(config::kLoopOutPin));
  gpio_reset_pin(static_cast<gpio_num_t>(config::kLoopInPin));
  gpio_set_direction(static_cast<gpio_num_t>(config::kLoopOutPin), GPIO_MODE_INPUT);
  gpio_set_direction(static_cast<gpio_num_t>(config::kLoopInPin), GPIO_MODE_INPUT);
}

void safe_state() {
  // Leave test output pins high impedance when not actively testing.
  gpio_set_direction(static_cast<gpio_num_t>(config::kLoopOutPin), GPIO_MODE_INPUT);
}

bool digital_loopback_test(bool& passed) {
  // Requires a physical jumper GPIO25 <-> GPIO26. Disconnect DUT wiring first.
  const auto out_pin = static_cast<gpio_num_t>(config::kLoopOutPin);
  const auto in_pin = static_cast<gpio_num_t>(config::kLoopInPin);

  esp_err_t err = gpio_set_direction(out_pin, GPIO_MODE_OUTPUT);
  if (err != ESP_OK) {
    safe_state();
    passed = false;
    return false;
  }
  err = gpio_set_direction(in_pin, GPIO_MODE_INPUT);
  if (err != ESP_OK) {
    safe_state();
    passed = false;
    return false;
  }

  bool low_ok = false;
  bool high_ok = false;
  gpio_set_level(out_pin, 0);
  vTaskDelay(pdMS_TO_TICKS(5));
  low_ok = (gpio_get_level(in_pin) == 0);

  gpio_set_level(out_pin, 1);
  vTaskDelay(pdMS_TO_TICKS(5));
  high_ok = (gpio_get_level(in_pin) == 1);

  gpio_set_level(out_pin, 0);
  safe_state();
  passed = low_ok && high_ok;
  return true;
}
}
