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

  // glance_band: never a false green on partial readings
  CHECK(glance_band(Band::Unknown, Band::Unknown) == Band::Unknown);
  CHECK(glance_band(Band::Unknown, Band::Green) == Band::Unknown);
  CHECK(glance_band(Band::Green, Band::Unknown) == Band::Unknown);
  CHECK(glance_band(Band::Unknown, Band::Orange) == Band::Orange);
  CHECK(glance_band(Band::Yellow, Band::Unknown) == Band::Yellow);
  CHECK(glance_band(Band::Green, Band::Green) == Band::Green);
  CHECK(glance_band(Band::Green, Band::Red) == Band::Red);

  // Sensirion CRC-8 / SEN6x forced CO2 recalibration
  {
    const uint8_t beef[2] = {0xBE, 0xEF};
    CHECK(sensirion_crc8(beef, 2) == 0x92);
    auto cmd = sen6x_frc_command(420);
    CHECK(cmd[0] == 0x67); CHECK(cmd[1] == 0x07); CHECK(cmd[2] == 0x01); CHECK(cmd[3] == 0xA4);
    CHECK(cmd[4] == sensirion_crc8(cmd.data() + 2, 2));
    CHECK(sen6x_frc_command(420)[4] == 0x4D);  // literal CRC of {0x01, 0xA4}
    int corr = 12345;
    const uint8_t good_w[2] = {0x80, 0x0A};  // 0x800A -> +10 ppm
    uint8_t good[3] = {0x80, 0x0A, sensirion_crc8(good_w, 2)};
    CHECK(sen6x_frc_correction(good, &corr)); CHECK(corr == 10);
    const uint8_t neg_w[2] = {0x7F, 0xF6};  // -10 ppm
    uint8_t neg[3] = {0x7F, 0xF6, sensirion_crc8(neg_w, 2)};
    CHECK(sen6x_frc_correction(neg, &corr)); CHECK(corr == -10);
    uint8_t bad[3] = {0x80, 0x0A, (uint8_t) (good[2] ^ 0xFF)};
    corr = 777;
    CHECK(!sen6x_frc_correction(bad, &corr)); CHECK(corr == 777);
    const uint8_t ff_w[2] = {0xFF, 0xFF};
    uint8_t ff[3] = {0xFF, 0xFF, sensirion_crc8(ff_w, 2)};
    CHECK(!sen6x_frc_correction(ff, &corr)); CHECK(corr == 777);
  }

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

  // R26: placeholder -> value bypasses the 180 s floor; nothing else does
  CHECK(decide_refresh(10000, 0, true, true, 0, true, false) == Refresh::Partial);
  CHECK(decide_refresh(10000, 0, true, true, 5, true, false) == Refresh::Full);
  CHECK(decide_refresh(10000, 0, true, false, 0, true, false) == Refresh::None);  // unchanged
  CHECK(decide_refresh(10000, 0, true, true, 0, false, false) == Refresh::None);  // shown has no placeholder
  CHECK(decide_refresh(10000, 0, true, true, 0, true, true) == Refresh::None);    // new still has one
  CHECK(decide_refresh(10000, 0, true, true, 0, false, true) == Refresh::None);   // value -> placeholder waits
  CHECK(has_placeholder("--")); CHECK(has_placeholder("-- --")); CHECK(!has_placeholder("612"));

  // R29: custom band thresholds shift the boundaries
  {
    const Co2Bands cb{600.0f, 900.0f, 1200.0f};
    CHECK(co2_band(700, cb) == Band::Yellow);   CHECK(co2_band(700) == Band::Green);
    CHECK(co2_band(599, cb) == Band::Green);    CHECK(co2_band(600, cb) == Band::Yellow);
    CHECK(co2_band(900, cb) == Band::Orange);   CHECK(co2_band(1200, cb) == Band::Red);
    CHECK(co2_band(1300) == Band::Orange);
    CHECK(co2_band_hyst(610, Band::Green, cb) == Band::Green);
    CHECK(co2_band_hyst(626, Band::Green, cb) == Band::Yellow);
    CHECK(co2_band_hyst(NAN, Band::Green, cb) == Band::Unknown);
    const Pm25Bands pb{5.0f, 15.0f, 30.0f, 60.0f, 100.0f};
    CHECK(pm25_band(7.0f, pb) == Band::Yellow); CHECK(pm25_band(7.0f) == Band::Green);
    CHECK(pm25_band(5.0f, pb) == Band::Green);  CHECK(pm25_band(15.0f, pb) == Band::Yellow);
    CHECK(pm25_band(30.1f, pb) == Band::Red);   CHECK(pm25_band(60.1f, pb) == Band::Purple);
    CHECK(pm25_band(100.1f, pb) == Band::Maroon);
    CHECK(pm25_band_hyst(5.3f, Band::Green, pb) == Band::Green);
    CHECK(pm25_band_hyst(5.6f, Band::Green, pb) == Band::Yellow);
    const Co2Bands cd;
    const Pm25Bands pd;
    CHECK(cd.yellow == 800.0f && cd.orange == 1000.0f && cd.red == 1500.0f);
    CHECK(pd.green_max == 9.0f && pd.yellow_max == 35.4f && pd.orange_max == 55.4f &&
          pd.red_max == 125.4f && pd.purple_max == 225.4f);
  }

  // non-finite text
  CHECK(co2_text(INFINITY) == "--"); CHECK(co2_text(-INFINITY) == "--");
  CHECK(pm25_text(INFINITY) == "--"); CHECK(pm25_text(-INFINITY) == "--");

  // forced recalibration needs >= 3 min of measurement
  CHECK(!frc_allowed(0)); CHECK(!frc_allowed(179999)); CHECK(frc_allowed(180000));

  if (g_failures != 0) {
    std::printf("%d of %d checks FAILED\n", g_failures, g_checks);
    return 1;
  }
  std::printf("%d checks passed\n", g_checks);
  return 0;
}
