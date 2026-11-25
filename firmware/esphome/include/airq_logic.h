// airq_logic.h - dependency-free decision logic for the airQ v3 firmware.
// Standard library only, so it is unit-tested on the host (firmware/tests)
// and #included from ESPHome lambdas.
#pragma once

#include <cmath>
#include <cstdint>
#include <string>

namespace airq {

enum class Band : uint8_t { Unknown, Green, Yellow, Orange, Red, Purple, Maroon };

struct Rgb {
  float r, g, b;
};

// CO2 bands (ppm): <800, <1000, <1500, >=1500. NaN or negative -> Unknown.
inline Band co2_band(float ppm) {
  if (std::isnan(ppm) || ppm < 0.0f) return Band::Unknown;
  if (ppm < 800.0f) return Band::Green;
  if (ppm < 1000.0f) return Band::Yellow;
  if (ppm < 1500.0f) return Band::Orange;
  return Band::Red;
}

// PM2.5 bands (ug/m3): <=9.0, <=35.4, <=55.4, <=125.4, <=225.4, above.
inline Band pm25_band(float ugm3) {
  if (std::isnan(ugm3) || ugm3 < 0.0f) return Band::Unknown;
  if (ugm3 <= 9.0f) return Band::Green;
  if (ugm3 <= 35.4f) return Band::Yellow;
  if (ugm3 <= 55.4f) return Band::Orange;
  if (ugm3 <= 125.4f) return Band::Red;
  if (ugm3 <= 225.4f) return Band::Purple;
  return Band::Maroon;
}

namespace detail {
// Keep prev if it lies between lo and hi (enum order), else use the raw band.
inline Band apply_hyst(Band raw, Band lo, Band hi, Band prev) {
  if (prev == Band::Unknown) return raw;
  if (lo > hi) {
    Band t = lo;
    lo = hi;
    hi = t;
  }
  if (prev >= lo && prev <= hi) return prev;
  return raw;
}
}  // namespace detail

inline Band co2_band_hyst(float ppm, Band prev) {
  if (std::isnan(ppm) || ppm < 0.0f) return Band::Unknown;
  const float margin = 25.0f;
  return detail::apply_hyst(co2_band(ppm), co2_band(ppm - margin), co2_band(ppm + margin), prev);
}

inline Band pm25_band_hyst(float ugm3, Band prev) {
  if (std::isnan(ugm3) || ugm3 < 0.0f) return Band::Unknown;
  const float margin = 0.5f;
  return detail::apply_hyst(pm25_band(ugm3), pm25_band(ugm3 - margin), pm25_band(ugm3 + margin), prev);
}

// Worst of two bands; a known band always beats Unknown.
inline Band worse(Band a, Band b) {
  if (a == Band::Unknown) return b;
  if (b == Band::Unknown) return a;
  return a > b ? a : b;
}

inline Rgb band_color(Band b) {
  switch (b) {
    case Band::Green: return {0.0f, 1.0f, 0.0f};
    case Band::Yellow: return {1.0f, 0.93f, 0.0f};
    case Band::Orange: return {1.0f, 0.4f, 0.0f};
    case Band::Red: return {1.0f, 0.0f, 0.0f};
    case Band::Purple: return {0.85f, 0.0f, 1.0f};
    case Band::Maroon: return {1.0f, 0.0f, 0.22f};
    case Band::Unknown:
    default: return {0.0f, 0.0f, 0.0f};
  }
}

// Brightness in [0, cap]: <=1 lux -> 0.05*cap, >=300 lux -> cap, log-linear
// between; NaN -> 0.5*cap.
inline float light_brightness(float lux, float cap) {
  if (std::isnan(lux)) return cap * 0.5f;
  if (lux <= 1.0f) return cap * 0.05f;
  if (lux >= 300.0f) return cap;
  const float t = std::log10(lux) / std::log10(300.0f);
  return cap * (0.05f + 0.95f * t);
}

enum class Press : uint8_t { None, ToggleLight, ForceCo2Calibration, SafeModeReboot };

// <50 ms ignored; <1 s toggle; 1-5 s ignored; 5-15 s CO2 calibration; >=15 s safe mode.
inline Press classify_press(uint32_t held_ms) {
  if (held_ms < 50) return Press::None;
  if (held_ms < 1000) return Press::ToggleLight;
  if (held_ms < 5000) return Press::None;
  if (held_ms < 15000) return Press::ForceCo2Calibration;
  return Press::SafeModeReboot;
}

inline std::string co2_text(float ppm) {
  if (std::isnan(ppm) || ppm < 0.0f) return "--";
  return std::to_string(std::lround(ppm));
}

inline std::string pm25_text(float ugm3) {
  if (std::isnan(ugm3) || ugm3 < 0.0f) return "--";
  return std::to_string(std::lround(ugm3));
}

enum class Refresh : uint8_t { None, Partial, Full };

// Refresh only if text changed and >=180000 ms since last refresh; every 6th
// refresh is full. The first paint is always Full. uint32 subtraction handles
// millis() wrap-around.
inline Refresh decide_refresh(uint32_t now_ms, uint32_t last_ms, bool ever_refreshed, bool changed,
                              uint8_t partials_since_full) {
  if (!ever_refreshed) return Refresh::Full;
  if (!changed) return Refresh::None;
  const uint32_t elapsed = now_ms - last_ms;
  if (elapsed < 180000u) return Refresh::None;
  return partials_since_full >= 5 ? Refresh::Full : Refresh::Partial;
}

}  // namespace airq
