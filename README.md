# FranklinWH Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)

This is a modern custom integration for [Home Assistant](https://www.home-assistant.io/) that provides comprehensive monitoring and control for FranklinWH home energy storage systems.

> ⚠️ This project is unofficial and not affiliated with FranklinWH.

> 📝 **About This Fork**: Complete rewrite by Joshua Seidel ([@JoshuaSeidel](https://github.com/JoshuaSeidel)) with Anthropic Claude Sonnet 4.5. Originally inspired by [@richo](https://github.com/richo)'s [homeassistant-franklinwh](https://github.com/richo/homeassistant-franklinwh) and uses the [franklinwh-python](https://github.com/richo/franklinwh-python) library.

---

## ✨ Features

### Monitoring
- 📊 Live battery status (State of Charge, charging/discharging power)
- ☀️ Solar production and energy generation tracking
- 🔌 Grid import/export monitoring with totals
- ⚡ Generator production and energy insights
- 🏠 Home load power monitoring and total energy consumption
- 🔀 Smart circuit switch monitoring (Switches 1-3)
- 🚗 V2L (Vehicle-to-Load) data support

### Control
- 🎛️ Individual smart circuit switch control
- ⚙️ Operation mode selection (self_use, backup, time_of_use)
- 🔋 Battery reserve setting
- 🌐 Grid connection control

### Modern Features
- 🎨 **Config Flow**: Easy setup through the Home Assistant UI
- 🔄 **DataUpdateCoordinator**: Efficient polling with minimal API calls
- 📱 **Device Registry**: All entities grouped under one device
- 🔍 **Diagnostics**: Built-in debugging support
- 🌐 **Local API Support**: Experimental local communication (when available)
- 🛠️ **Services**: Custom services for advanced control

---

## 📦 Installation

### Via HACS (Recommended)

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the menu (⋮) → **Custom repositories**.
3. Add this repository URL: `https://github.com/JoshuaSeidel/homeassistant-franklinwh`
4. Choose category **Integration** and click **Add**.
5. Search for **FranklinWH** in HACS and click **Download**.
6. Restart Home Assistant.

### Manual Installation

1. Download this repository as a ZIP file.
2. Extract the contents to your Home Assistant `custom_components/franklin_wh/` directory.
3. Restart Home Assistant.

---

## ⚙️ Configuration

### Easy Setup (Config Flow - Recommended)

1. Go to **Settings → Devices & Services**.
2. Click **+ Add Integration**.
3. Search for **FranklinWH**.
4. Enter your credentials:
   - **Email Address**: Your FranklinWH account email
   - **Password**: Your FranklinWH account password
   - **Gateway ID**: Find this in the FranklinWH app under **More → Site Address → SN**
   - **Use Local API** (optional): Enable for experimental local communication
   - **Local Host** (optional): IP address of your FranklinWH gateway

5. Click **Submit** and your devices will be added automatically!

### Legacy YAML Configuration (Deprecated)

> ⚠️ **Note**: YAML configuration is deprecated and will be removed in a future version. Please migrate to Config Flow setup above.

<details>
<summary>Click to expand legacy YAML configuration</summary>

```yaml
# This is the old configuration method - NOT RECOMMENDED
# Please use Config Flow instead

sensor:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: "100xxxxxxxxxxxx"

switch:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: "100xxxxxxxxxxxx"
    switches: [1, 2, 3]
    name: "All Switches"
```
</details>

---

## 📊 Available Entities

After setup, all entities will be organized under a single **FranklinWH** device:

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| **State of Charge** | Battery state of charge | % |
| **Battery Use** | Battery charging/discharging rate (negative = charging) | kW |
| **Battery Charge** | Total energy charged to battery | kWh |
| **Battery Discharge** | Total energy discharged from battery | kWh |
| **Battery Charge from Grid** | Energy charged to battery from grid (direct telemetry) | kWh |
| **Home Load** | Instantaneous home power consumption | kW |
| **Grid Use** | Net grid power (positive = importing, negative = exporting) | kW |
| **Grid Import** | Total energy imported from grid | kWh |
| **Grid Export** | Total energy exported to grid | kWh |
| **Solar Production** | Instantaneous solar power generation | kW |
| **Solar Energy** | Total solar energy produced | kWh |
| **Generator Use** | Generator power output (live) | kW |
| **Generator Energy** | Total generator energy produced | kWh |
| **Switch 1 Load** | Power draw on Switch 1 | W |
| **Switch 1 Lifetime Use** | Total energy used by Switch 1 | kWh |
| **Switch 2 Load** | Power draw on Switch 2 | W |
| **Switch 2 Lifetime Use** | Total energy used by Switch 2 | kWh |
| **V2L Use** | Power via Vehicle-to-Load | W |
| **V2L Import** | Total energy drawn from V2L | kWh |
| **V2L Export** | Total energy delivered to V2L | kWh |
| **Home Energy Total** | Total energy consumed by home | kWh |

### Switches

| Entity | Description |
|--------|-------------|
| **Switch 1** | Control smart circuit 1 |
| **Switch 2** | Control smart circuit 2 |
| **Switch 3** | Control smart circuit 3 |
| **Grid Connection** | Monitor and control grid connection status |

---

## 🔧 Services

The integration provides custom services for advanced control:

### `franklin_wh.set_operation_mode`

Set the operation mode of your FranklinWH system.

**Parameters:**
- `mode`: Operation mode (`self_use`, `backup`, `time_of_use`, `clean_backup`)

**Example:**
```yaml
service: franklin_wh.set_operation_mode
data:
  mode: self_use
```

### `franklin_wh.set_battery_reserve`

Set the minimum battery reserve percentage.

**Parameters:**
- `reserve_percent`: Minimum battery charge to maintain (0-100)

**Example:**
```yaml
service: franklin_wh.set_battery_reserve
data:
  reserve_percent: 20
```

---

## 🔋 Energy Dashboard Integration

All energy sensors are compatible with Home Assistant's **Energy Dashboard**:

1. Go to **Settings → Dashboards → Energy**
2. Configure your energy sources:
   - **Solar Production**: Use "Solar Energy" sensor
   - **Battery**: Use "Battery Charge" and "Battery Discharge" sensors
   - **Battery from Grid**: Use "Battery Charge from Grid" sensor
   - **Grid**: Use "Grid Import" and "Grid Export" sensors

---

## 🐛 Troubleshooting

### No entities appear after setup
1. Check **Settings → System → Logs** for errors containing `franklin_wh`
2. Verify your credentials are correct
3. Confirm your Gateway ID is correct (found in FranklinWH app)
4. Ensure FranklinWH cloud services are online

### Authentication errors
1. Try re-authenticating:
   - Go to **Settings → Devices & Services**
   - Find your FranklinWH integration
   - Click **Configure** → **Re-authenticate**
2. Verify your password is correct

### Entities show as "Unavailable"
1. Check your internet connection
2. Verify the FranklinWH cloud service is accessible
3. Check the integration logs for API errors
4. Try reloading the integration

### Gateway Timeout Errors
If you see "Device response timed out":
1. **Verify gateway is online**: Check the FranklinWH mobile app
2. **Check Gateway ID**: Must be exact SN from app (More → Site Address → SN)
3. **FranklinWH cloud status**: Service may be temporarily down
4. **Disable local API**: If enabled, switch back to cloud polling
5. **Wait and retry**: Gateway may be rebooting or updating

### Local API Issues
The local API is **experimental** and may not work:
- Most users should use **cloud polling** (default)
- Local API requires the gateway to support local communication
- If local API times out, disable it and use cloud polling
- Local API support depends on gateway firmware version

### Diagnostics
To get detailed diagnostic information:
1. Go to **Settings → Devices & Services**
2. Find your FranklinWH integration
3. Click the device, then click **Download Diagnostics**
4. Attach the diagnostics file when reporting issues

---

## 🔍 Local API Support (Experimental)

This integration includes experimental support for local API communication. Currently, the FranklinWH library primarily uses cloud polling, but local API support is being explored.

**To enable local API (when available):**
1. Enable "Use Local API" during setup
2. Enter your gateway's local IP address
3. The integration will attempt local communication with faster polling (10 seconds vs 60 seconds)

> 📝 **Note**: Local API support depends on the underlying `franklinwh` Python library and may not be fully functional yet. This is an area of active development.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and open a pull request:

👉 [https://github.com/JoshuaSeidel/homeassistant-franklinwh](https://github.com/JoshuaSeidel/homeassistant-franklinwh)

### Development Setup

1. Clone the repository
2. Install development dependencies
3. Use VS Code with Dev Containers for a consistent environment
4. Test your changes thoroughly before submitting

### Reporting Issues

When reporting issues, please:
1. Download diagnostics from your integration
2. Include Home Assistant and integration versions
3. Provide relevant log entries
4. Describe steps to reproduce

---

## 📋 Changelog

### Version 1.1.0 (Current)
- ⬆️ **UPGRADED**: Updated to franklinwh library 1.0.0
- ✨ **NEW**: Full operation mode control (self_use, backup, time_of_use)
- ✨ **NEW**: Battery reserve percentage setting
- ✨ **NEW**: Grid connection switch for monitoring and control
- ✨ **NEW**: Home Energy Total sensor (total home consumption)
- 🐛 **FIXED**: Integration now properly works with franklinwh 1.0.0 API
- ♻️ **IMPROVED**: Updated imports to use properly exported classes
- 📝 **DOCS**: Updated README to reflect available features

### Version 1.0.9
- ⬆️ **UPGRADED**: Updated to franklinwh library 1.0.0
- ✨ **NEW**: Full operation mode control (self_use, backup, time_of_use)
- ✨ **NEW**: Battery reserve percentage setting
- ✨ **NEW**: Grid connection switch for monitoring and control
- ✨ **NEW**: Home Energy Total sensor (total home consumption)
- 🐛 **FIXED**: Integration now properly works with franklinwh 1.0.0 API
- ♻️ **IMPROVED**: Updated imports to use properly exported classes
- 📝 **DOCS**: Updated README to reflect available features

### Version 1.0.7
- 🐛 **CRITICAL FIX**: Removed Grid Connection switch (requires unreleased library version)
- 🐛 **FIXED**: ImportError for AccessoryType and GridStatus classes
- 🐛 **FIXED**: Integration now loads successfully with franklinwh 0.4.1
- ℹ️ **NOTE**: Smart circuit switches (1-3) still work correctly

### Version 1.0.6
- 🐛 **CRITICAL FIX**: Fixed Stats class import from franklinwh.client module
- 🐛 **FIXED**: "cannot import name 'Stats'" ImportError on setup

### Version 1.0.5
- 🐛 **CRITICAL FIX**: Corrected franklinwh package requirement to 0.4.1 (was incorrectly set to 0.5.0 which doesn't exist)
- 🐛 **FIXED**: "Requirements for franklin_wh not found" error on setup

### Version 1.0.4
- ✨ **NEW**: Battery Charge from Grid calculated sensor
- 🐛 **FIXED**: Entities no longer flicker unavailable during temporary failures
- 🐛 **FIXED**: Energy Dashboard compatibility (all sensors in kWh)
- ♻️ **IMPROVED**: Resilient coordinator with 3-failure grace period
- ♻️ **IMPROVED**: Better error logging and failure tracking
- ⚠️ **NOTE**: Grid Connection switch from this version removed in 1.0.7 (library compatibility)

### Version 1.0.0-1.0.3
- ✨ **NEW**: Modern config flow for UI-based setup
- ✨ **NEW**: DataUpdateCoordinator for efficient API polling
- ✨ **NEW**: Device registry integration
- ✨ **NEW**: Diagnostics support
- ✨ **NEW**: Experimental local API support
- ✨ **NEW**: Custom services (placeholders for future features)
- 🐛 **FIXED**: All typos and copy-paste errors in entity IDs
- 🐛 **FIXED**: Consolidated caching logic
- 🐛 **FIXED**: Improved error handling
- ♻️ **REFACTOR**: Complete code modernization
- ♻️ **REFACTOR**: Better entity organization

### Version 0.4.1 (Legacy)
- Initial YAML-based platform configuration by @richo
- Basic sensor and switch support

---

## 📄 License

This project is dual-licensed under:
- **MIT License**
- **Apache License 2.0**

You may choose either license when using or contributing to this project.

---

## 🙏 Acknowledgments

- **Original Integration**: [@richo](https://github.com/richo) for the initial implementation
- **Python Library**: [`franklinwh-python`](https://github.com/richo/franklinwh-python) by @richo
- **Rewrite**: Joshua Seidel with Anthropic Claude Sonnet 4.5
- **Community**: Thanks to the Home Assistant community
- **Contributors**: Special thanks to all contributors including [@jkt628](https://github.com/jkt628) for Grid Connection switch

---

# ⚠️ Disclaimer

This integration is not affiliated with, endorsed by, or supported by FranklinWH. Use at your own risk. The developers are not responsible for any damage to your system or equipment.

---

**Enjoy your FranklinWH integration! 🎉**

For support, please open an issue on [GitHub](https://github.com/JoshuaSeidel/homeassistant-franklinwh/issues).
