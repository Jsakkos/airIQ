# airQ

Open-source indoor air-quality monitor: ESP32-C6 + Sensirion SEN66 (PM, CO2, VOC, NOx, temperature, humidity), e-paper display, RGB status LED, ESPHome firmware, KiCad PCB and a 3D-printed enclosure.

**Status:** v3 is in design and early implementation.

- Design spec: [docs/superpowers/specs/2026-11-25-airq-v3-design.md](docs/superpowers/specs/2026-11-25-airq-v3-design.md)
- Implementation plans: [docs/superpowers/plans/](docs/superpowers/plans/)
- Research report: [docs/research/reports/Air quality monitor refresh.md](docs/research/reports/Air%20quality%20monitor%20refresh.md)
- Hardware interface contract (GPIOs, I2C addresses, connector pinouts): [hardware/interface.yaml](hardware/interface.yaml)
- Previous generation (v2, ESP8266): [legacy/v2/](legacy/v2/README.md)

## Licences

- `firmware/` and `tools/`: [MIT](LICENSE)
- `hardware/` and `enclosure/`: [CC-BY-SA 4.0](hardware/LICENSE.md)
