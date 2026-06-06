# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog.
This project follows semantic versioning where practical.

## [1.1.1] - 2026-06-06

### Fixed
- Improved command handling stability for Home Assistant MQTT switches to avoid callback crashes on malformed payload/topic inputs.
- Made `uhubctl` output parsing more robust for hub headers and action responses.
- Added guard logic to prevent index errors when parsing action results before publishing updated state.

### Changed
- Bridge version updated to `v1.1.1` in startup logging.
- Add-on version bumped from `1.1.0` to `1.1.1`.

## [1.1.0] - 2026-06-06

### Added
- Home Assistant MQTT autodiscovery for USB port switches.
- New add-on options in `uhubctl/config.json`:
    - `DISCOVERY_ENABLED` (default: `true`)
    - `DISCOVERY_PREFIX` (default: `homeassistant`)
    - `FORCE_OPTIMISTIC` (default: `false`)
- Discovery payload now includes Home Assistant `device` metadata, so one USB hub is represented as one HA device with per-port switch entities.
- Optional forced optimistic mode in discovery payload (`optimistic: true`) when `FORCE_OPTIMISTIC=true`.

### Changed
- Bridge version updated to `v1.1.0` in startup logging.
- Add-on version bumped from `1.0.6` to `1.1.0`.
- MQTT state publishing remains retained to improve state restoration after reconnect/restart.

### Documentation
- Updated `README.md`, `uhubctl/README.md`, and `uhubctl/DOCS.md`:
    - autodiscovery behavior
    - discovery topic format
    - new configuration options
    - note that manual YAML is optional fallback

### Compatibility / Migration Notes
- Existing manual MQTT switch YAML can remain, but may create duplicate entities if autodiscovery is enabled.
- Recommended migration path:
    1. Enable autodiscovery (default already enabled),
    2. verify discovered entities in Home Assistant,
    3. remove manual YAML entries if no longer needed.
- If switch state behavior is unstable in a specific setup, set `FORCE_OPTIMISTIC=true`.

## [1.0.0] - 2026-06-06

### Added
- Initial modernized release of the MQTT bridge for `uhubctl`.
- Improved error handling and logging.
- Configuration validation.
- Health checks for container monitoring.

### Changed
- Updated `paho-mqtt` to `2.0.0+` (from older 1.x line).
- Build configuration cleanup and image optimization.
- Improved startup/runtime script robustness.

### Fixed
- Build configuration issues (malformed base image tag).