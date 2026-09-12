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
* Adjustable polling rates for all sensors mentioned above

## Pros
* Fully UI-based configuration🤗
* Support for installation with [HACS](https://hacs.xyz/)
* Support for arbitary number of remo devices & appliances
* Air conditioner status set from smartphone APP can be synchronized
* Light status is synchronized too, including presses of the light's own physical remote on Remo devices that watch for them
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

You are then asked, for each of your lights, which button on its remote turns the light on and which turns it off. If the remote has only a single toggle button, choose that same button for both: the light can then only be toggled. Existing installations keep working without being asked; their buttons are detected as before.

## Upgrade
In addtion to upgrading the package itself, **it is required to restart HA.** \(Migration of outdated configurations is automatically handled now.\)

## Note
### Configuration Changes from Smartphone App
**It is recommended that you finish all configurations on your smartphone app before using this integration.**

All devices and appliances are detected and configured only once when adding the integration to Home Assistant, so if you changed your configuration from you smartphone app it will not be synchronized. **Remove the hub registered by this integration and add the integration again if you wish to reflect the changes.**

### Light
Lights are registered twice: one light entity and one select & button entity. Light eitities make intuitive sense for controlling; however, it's impossible to cover all functionalities of your light. Use the select & button entity to control your light without modifying the `is_on` state, and access extra abilities of your light.

#### Which buttons are sent
The light entity sends the buttons you chose when adding the integration. When they are two different buttons, turning the light on and off sends the matching button directly. When you chose one button for both, that is all the remote can do, so the entity toggles: turning it on assumes the light is currently off, and turning it off assumes it is currently on. Prefer `toggle` in that case.

If you were never asked (an installation predating this step, or a light added to the Nature app afterwards), the buttons are detected instead: `on` and `off` when the remote has both, otherwise `onoff`.

#### State synchronization
The `is_on` state is read back from the Nature API on every appliance poll, so a change made outside Home Assistant is picked up: the smartphone app, another client, or — on Remo devices that watch for it — a press of the light's own physical remote. For a toggle-only light this is what makes `toggle` dependable: turning the light on with its own remote used to leave Home Assistant believing it was off, so the next toggle turned it on again.

Two things to expect:

* **It is not instant.** The API offers no push channel, so the only way to notice a change is to poll for it. Expect up to one polling interval of delay (60 seconds by default). Lowering `Polling interval (sec) for power meter` makes lights react sooner, but the API allows only 30 requests per 5 minutes in total, shared with sensor polling and with every command you send.
* **It needs your Remo to report the state.** Older devices only report a light's power after *they* changed it, so a press of the physical remote will not show up. Nothing breaks in that case; the state simply updates less often, exactly as it did before.

Immediately after Home Assistant sends a command, incoming reports are distrusted for a few seconds. A poll already in flight would otherwise carry the state from just before the command and undo it, and unlike an air conditioner's settings a light's reported state carries no timestamp to recognise that by.
