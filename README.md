# HomeAssistantNatureRemo
An integration for accessing Nature Remo sensors and appliances from [Home Assistant](https://www.home-assistant.io/).

## Screenshot
![image](https://user-images.githubusercontent.com/69963492/236558104-b5fcf0d3-cf5e-4653-a01d-bceae0d88f64.png)

## Features
It currently supports features listed below, and I'm still working on more functionalities.
* temperature sensor
* humidity sensor
* illuminance sensor
* movement sensor
* electricity meter
* sending IR signals to general appliances (except air conditioner and light)

By design it should operate with arbitrary number of remo devices linked with the token, but I don't have multiple ones so if you encounter any bugs please create an issue.

## Pros
* Fully UI-based configuration🤗
* Support for multiple remo devices
* Tested on latest version of Home Assistant (2023.5.1)

## Installation
Copy the folder `remo` into `<config directory>/custom_components/`. If you do not have access to the `<config directory>`, you can install the `Samba share` add-on and access it from SAMBA. Restart Home Assistant and add the integration `nature_remo`. During the process you will be asked to enter your API access token; you can get one from [here](https://home.nature.global/).

## Note
All devices and appliances are detected and configured only once when adding the integration to Home Assistant, so if you changed your configuration from you smartphone app it will not be synchronized. **Remove and add the integration again if you wish to reflect the changes.**
