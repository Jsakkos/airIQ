// Host unit tests for airq_logic.h (no ESPHome needed).
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <string>

#include "airq_logic.h"

using namespace airq;

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(expr)                                                  \
  do {                                                               \
    ++g_checks;                                                      \
    if (!(expr)) {                                                   \
      ++g_failures;                                                  \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr);    \
    }                                                                \
  } while (0)

int main() {
  // CO2 bands
  CHECK(co2_band(NAN) == Band::Unknown);  CHECK(co2_band(-1) == Band::Unknown);
  CHECK(co2_band(799) == Band::Green);    CHECK(co2_band(800) == Band::Yellow);
  CHECK(co2_band(999) == Band::Yellow);
  CHECK(co2_band(1000) == Band::Orange);  CHECK(co2_band(1499) == Band::Orange);
  CHECK(co2_band(1500) == Band::Red);

  // PM2.5 bands
  CHECK(pm25_band(NAN) == Band::Unknown); CHECK(pm25_band(-0.1f) == Band::Unknown);
  CHECK(pm25_band(9.0f) == Band::Green);  CHECK(pm25_band(9.1f) == Band::Yellow);
  CHECK(pm25_band(35.4f) == Band::Yellow); CHECK(pm25_band(35.5f) == Band::Orange);
  CHECK(pm25_band(55.4f) == Band::Orange);
  CHECK(pm25_band(55.5f) == Band::Red);
  CHECK(pm25_band(125.4f) == Band::Red);  CHECK(pm25_band(125.5f) == Band::Purple);
  CHECK(pm25_band(225.4f) == Band::Purple);
  CHECK(pm25_band(225.5f) == Band::Maroon);

  // Hysteresis
  CHECK(co2_band_hyst(810, Band::Green) == Band::Green);   CHECK(co2_band_hyst(826, Band::Green) == Band::Yellow);
  CHECK(co2_band_hyst(790, Band::Yellow) == Band::Yellow); CHECK(co2_band_hyst(774, Band::Yellow) == Band::Green);
  CHECK(co2_band_hyst(900, Band::Unknown) == Band::Yellow);
  CHECK(co2_band_hyst(10, Band::Unknown) == Band::Green);
  CHECK(co2_band_hyst(NAN, Band::Green) == Band::Unknown);
  CHECK(co2_band_hyst(-5, Band::Green) == Band::Unknown);
  CHECK(pm25_band_hyst(9.3f, Band::Green) == Band::Green); CHECK(pm25_band_hyst(9.6f, Band::Green) == Band::Yellow);
  CHECK(pm25_band_hyst(NAN, Band::Red) == Band::Unknown);
  CHECK(pm25_band_hyst(20.0f, Band::Unknown) == Band::Yellow);

  // worse
  CHECK(worse(Band::Green, Band::Orange) == Band::Orange); CHECK(worse(Band::Unknown, Band::Green) == Band::Green);
  CHECK(worse(Band::Green, Band::Unknown) == Band::Green);
  CHECK(worse(Band::Unknown, Band::Unknown) == Band::Unknown);
  CHECK(worse(Band::Maroon, Band::Red) == Band::Maroon);

  // colours
  CHECK(band_color(Band::Unknown).r == 0 && band_color(Band::Unknown).g == 0 && band_color(Band::Unknown).b == 0);
  CHECK(band_color(Band::Green).g == 1.0f && band_color(Band::Green).r == 0.0f);
  CHECK(band_color(Band::Yellow).g == 0.93f);
  CHECK(band_color(Band::Orange).g == 0.4f);
  CHECK(band_color(Band::Purple).r == 0.85f && band_color(Band::Purple).b == 1.0f);
  CHECK(band_color(Band::Maroon).b == 0.22f);

  // brightness
  CHECK(light_brightness(0.5f, 0.6f) == 0.6f * 0.05f); CHECK(light_brightness(300, 0.6f) == 0.6f);
  CHECK(light_brightness(1e6f, 0.6f) == 0.6f);         CHECK(light_brightness(NAN, 0.6f) == 0.3f);
  {
    bool mono = true, bounded = true;
    for (int lux = 1; lux <= 300; ++lux) {
      float b0 = light_brightness((float) lux, 0.6f);
      float b1 = light_brightness((float) (lux + 1), 0.6f);
      if (b1 < b0) mono = false;
      if (b0 < 0.0f || b0 > 0.6f) bounded = false;
    }
    CHECK(mono);
    CHECK(bounded);
  }

  // button
  CHECK(classify_press(30) == Press::None);     CHECK(classify_press(400) == Press::ToggleLight);
  CHECK(classify_press(49) == Press::None);     CHECK(classify_press(50) == Press::ToggleLight);
  CHECK(classify_press(999) == Press::ToggleLight); CHECK(classify_press(1000) == Press::None);
  CHECK(classify_press(3000) == Press::None);   CHECK(classify_press(5000) == Press::ForceCo2Calibration);
  CHECK(classify_press(14999) == Press::ForceCo2Calibration);
  CHECK(classify_press(15000) == Press::SafeModeReboot);

  // text
  CHECK(co2_text(612.4f) == "612");  CHECK(co2_text(NAN) == "--");  CHECK(co2_text(40000) == "40000");
  CHECK(co2_text(-1) == "--");
  CHECK(pm25_text(4.4f) == "4");     CHECK(pm25_text(4.6f) == "5"); CHECK(pm25_text(-2) == "--");
  CHECK(pm25_text(NAN) == "--");

  // refresh policy
  CHECK(decide_refresh(1000, 0, false, true, 0) == Refresh::Full);
  CHECK(decide_refresh(5, 0, false, false, 0) == Refresh::Full);
  CHECK(decide_refresh(179999, 0, true, true, 0) == Refresh::None);
  CHECK(decide_refresh(180000, 0, true, false, 0) == Refresh::None);
  CHECK(decide_refresh(180000, 0, true, true, 4) == Refresh::Partial);
  CHECK(decide_refresh(180000, 0, true, true, 5) == Refresh::Full);
  CHECK(decide_refresh(100000, 4294900000u, true, true, 0) == Refresh::None);  // millis() wrap: 167 296 ms elapsed
  CHECK(decide_refresh(200000, 4294900000u, true, true, 0) == Refresh::Partial);  // wrap, 267 296 ms elapsed

  if (g_failures != 0) {
    std::printf("%d of %d checks FAILED\n", g_failures, g_checks);
    return 1;
  }
  std::printf("%d checks passed\n", g_checks);
  return 0;
}
