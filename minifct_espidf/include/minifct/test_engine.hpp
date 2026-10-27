#pragma once
#include <cstddef>
#include <cstdint>

namespace minifct {
struct TestResult {
  const char* name;
  bool passed;
  bool implemented;
  double value;
  const char* unit;
  const char* message;
};

using TestFunction = TestResult (*)();
struct TestDefinition {
  const char* name;
  TestFunction run;
};

const TestDefinition* test_registry(size_t& count);
bool run_test(const char* name, TestResult& result);
void run_all_tests();
}
