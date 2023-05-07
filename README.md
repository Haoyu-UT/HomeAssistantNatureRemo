# HomeAssistantNatureRemo
An integration for accessing Nature Remo sensors and appliances from [Home Assistant](https://www.home-assistant.io/).

## Screenshot
![image](https://user-images.githubusercontent.com/69963492/236665821-5efbe795-638a-4de5-9b4d-afa97840813d.png)


## Features
* temperature sensor
* humidity sensor
* illuminance sensor
* movement sensor
* electricity meter
* controlling air conditioner
* controlling light
* sending IR signals to general appliances

By design it should operate with arbitrary number of remo devices linked with the token, but I don't have multiple ones so if you encounter any bugs please create an issue.

## Pros
* Fully UI-based configuration🤗
* Support for multiple remo devices
* Air conditioner status set from smartphone APP can be synchronized
* Memorizing swing mode, air volume, target temperature for each AC mode, so no need to set these settings again when you switch the AC mode
* Tested on latest version of Home Assistant (2023.5.2)

## Installation
Copy the folder `remo` into `<config directory>/custom_components/`. If you do not have access to the `<config directory>`, you can install the `Samba share` add-on and access it from SAMBA. Restart Home Assistant and add the integration `nature_remo`. During the process you will be asked to enter your API access token; you can get one from [here](https://home.nature.global/).

## Update
**Remove the integration and overwrite `<config directory>/custom_components/remo`, then add and reconfigure the integration.**

## Note
### Configuration Changes from Smartphone App
**It is recommended that you finish all configurations on your smartphone app before using this integration.**

All devices and appliances are detected and configured only once when adding the integration to Home Assistant, so if you changed your configuration from you smartphone app it will not be synchronized. **Remove and add the integration again if you wish to reflect the changes.**
### Air Conditoner
Only swing modes on vertical direction is supported; horizontal ones are unsupported due to limitations of Home Assistant.
### Light
Lights are registered twice: one light entity and one select & button entity. Light eitities make intuitive sense for controlling; however, it's impossible to cover all functionalities of your light, and the `is_on` state is also unreliable. Use the select & button entity to control your light without modifying the `is_on` state (thus fix wrong state), and gain access to more functionalities of your light.

The control of the light entity is implemented as sending `onoff` button signal. Please contact me if you find it's not working for your light.
