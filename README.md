# HomeAssistantNatureRemo
An integration for accessing Nature Remo sensors from Home Assistant
## Functionality
It currently only supports fetching temperature sensor data, but I'm still working on it. By design it should support multiple remo devices, but I don't have multiple ones so if you encounter any bugs please create an issue. And if you modify anything from your smartphone app, please remove and re-configure the integration.
## Installation
Copy the folder `remo` into `<config directory>/custom_components/`. If you do not have access to the folder, you can install the `Samba share` add-on and access it from SAMBA. Restart the HomeAssistant and add the integration `nature_remo`. During the process you will be asked to enter you access token; get one from [here](https://home.nature.global/).
