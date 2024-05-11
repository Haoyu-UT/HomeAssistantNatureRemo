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

## Pros
* Fully UI-based configuration🤗
* Support for installation with [HACS](https://hacs.xyz/)
* Support for arbitary number of remo devices & appliances
* Air conditioner status set from smartphone APP can be synchronized
* Memorizing swing mode, air volume, target temperature for each AC mode, so no need to set again upon switching the AC mode
* Tested on latest version of Home Assistant (2023.5.2)

## Installation
### Automatic Installation with HACS
It's easy to start with [HACS](https://hacs.xyz/), a community-supported store! Just add the URL of this repository to custom components, and install `Integration for Nature Remo` from HACS.
![屏幕截图 2023-05-10 201120](https://github.com/Haoyu-UT/HomeAssistantNatureRemo/assets/69963492/af9ace4f-c2cb-4c73-b684-ca065cfc743c)

### Manual Installation
Copy the folder `custom_components/nature_remo` into `<config directory>/custom_components/` on your device. If you do not have access to the `<config directory>`, you can install the `Samba share` add-on and access it from SAMBA.

### Configuration
After installation, restart Home Assistant and add the integration `nature_remo` from settings. During the process you will be asked to enter your API access token; you can get one from [here](https://home.nature.global/).

## Upgrade
In addtion to upgrading the package itself, **it is required to delete the hub registered by the integration, restart HA, and add the integration again.**
<img width="1278" alt="image" src="https://github.com/Haoyu-UT/HomeAssistantNatureRemo/assets/69963492/8d4b0166-f6f0-4105-a933-2f642492eb44">


## Note
### Configuration Changes from Smartphone App
**It is recommended that you finish all configurations on your smartphone app before using this integration.**

All devices and appliances are detected and configured only once when adding the integration to Home Assistant, so if you changed your configuration from you smartphone app it will not be synchronized. **Remove the hub registered by this integration and add the integration again if you wish to reflect the changes.**

### Light
Lights are registered twice: one light entity and one select & button entity. Light eitities make intuitive sense for controlling; however, it's impossible to cover all functionalities of your light, and the `is_on` state is unreliable due to the lack of feedback. Use the select & button entity to control your light without modifying the `is_on` state (thus fixing wrong states), and access extra abilities of your light.

The control of the light entity is implemented as sending `onoff` button signal, or sending `on` and `off` separately if `onoff` is not present. Please contact me if you find it's not working for your light.
