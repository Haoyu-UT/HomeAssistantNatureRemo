[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# HomeAssistantNatureRemo
An integration for accessing Nature Remo sensors and appliances from [Home Assistant](https://www.home-assistant.io/).

## Screenshot
![image](https://user-images.githubusercontent.com/69963492/236665821-5efbe795-638a-4de5-9b4d-afa97840813d.png)

## Features
* controlling air conditioner
* controlling light
* sending IR signals to general appliances
* temperature sensor
* humidity sensor
* illuminance sensor
* movement sensor
* electricity meter
* Adjustable polling rates for sensors and application state synchronization

## Pros
* Fully UI-based configuration, easy to install with [HACS](https://hacs.xyz/)
* Support for arbitary number of remo devices & appliances
* Light and air conditioner operations through Nature Home app can be synchronized, opeartions through physical remote control can be synchronized if you have latest Nature Remo hardware
* Swing mode, air volume, target temperature are memorized for each AC mode, no need to set again when switching the AC mode
* Tested on latest version of Home Assistant (2026.7.4)

## Installation
### Installation with HACS
It's easy to start with [HACS](https://hacs.xyz/), a community-supported store! Just add the URL of this repository to custom components, and install `Integration for Nature Remo` from HACS.
![screenshot](https://github.com/Haoyu-UT/HomeAssistantNatureRemo/assets/69963492/af9ace4f-c2cb-4c73-b684-ca065cfc743c)

### Manual Installation
Copy the folder `custom_components/nature_remo` into `<config directory>/custom_components/` on your device. If you do not have access to the `<config directory>`, you can install the `Samba share` add-on and access it from SAMBA.

### Configuration
After installation, restart Home Assistant and add the integration `nature_remo` from settings. During the process you will be asked to enter your API access token; get one from [here](https://home.nature.global/).

You are then asked, for each of your lights, which button on its remote turns the light on and which turns it off. If the remote has only a single toggle button, choose that same button for both: the light can then only be toggled.

## Upgrade
In addtion to upgrading the package itself, **it is required to restart HA.** \(Migration of outdated configurations is automatically handled.\)

## Note
### Appliance Changes from Nature Home App
**It is recommended that you finish all configurations on your smartphone app before using this integration.**

All devices and appliances are detected and configured only once when adding the integration to Home Assistant, so if you changed your configuration from Nature Home app it will not be synchronized. **Remove the hub registered by this integration and setup again to reflect the changes.**

### Light
A light is registered as multiple entities: one light entity and one select & one button entity. Light entities make intuitive sense for controlling; however, it's impossible to cover all functionalities of your light. Select entity selects a signal, and button entity sends it. Use the select & button entity to control your light without modifying the `is_on` state, and access extra abilities of your light.

#### How on/off works for lights
You are asked to designate a signal for on and a signal for off. They can be the same or different, and if you assigned the same signal for on and off it means your light can only toggle. For a light only toggles, on and off will first overwrite its current state (overwrite with on if you send off) and toggle.
