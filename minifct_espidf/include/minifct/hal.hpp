#pragma once
namespace minifct::hal {
void init();
void safe_state();
bool digital_loopback_test(bool& passed);
}
