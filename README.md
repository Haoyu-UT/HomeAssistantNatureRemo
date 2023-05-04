# HomeAssistantNatureRemo
An integration for accessing Nature Remo sensors from [Home Assistant](https://www.home-assistant.io/).

## Functionality
It currently only supports fetching sensor data from [Nature Remo API](https://swagger.nature.global/), and I'm still working on more functionalities.
* temperature sensor
* humidity sensor
* illuminance sensor
* movement sensor
* power meter

By design it should operate with arbitrary number of remo devices linked with the token, but I don't have multiple ones so if you encounter any bugs please create an issue.

## Pros
* UI-based configuration🤗


## Installation
Copy the folder `remo` into `<config directory>/custom_components/`. If you do not have access to the `<config directory>`, you can install the `Samba share` add-on and access it from SAMBA. Restart Home Assistant and add the integration `nature_remo`. During the process you will be asked to enter your API access token; you can get one from [here](https://home.nature.global/).

## Note
All devices are detected and configured only once when adding the integration to Home Assistant, so if you changed your configuration from you smartphone app it will not be synchronized. **Remove and add the integration again if you wish to reflect the changes.**
