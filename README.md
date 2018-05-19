# Xiaomi Mi Electric Rice Cooker

This is a custom component for home assistant to integrate the Xiaomi Mi Electric Rice Cooker V2.

Please follow the instructions on [Retrieving the Access Token](https://home-assistant.io/components/xiaomi/#retrieving-the-access-token) to get the API token to use in the configuration.yaml file.

Credits: Thanks to [Rytilahti](https://github.com/rytilahti/python-miio) for all the work.

## Features

### Rice Cooker V2

* Start cooking a profile
* Stop cooking
* Attributes
  - mode
  - menu
  - temperature
  - start_time
  - remaining
  - cooking_delayed
  - duration
  - settings
  - favorite
  - stage(?)

## Setup

```yaml
# configuration.yaml

platform: xiaomi_cooker
  host: 192.168.130.88
  token: b7c4a758c251955d2c24b1d9e41ce47d
  model: chunmi.cooker.normal2
```

Configuration variables:
- **host** (*Required*): The IP of your cooker.
- **token** (*Required*): The API token of your cooker.
- **model** (*Optional*): The model of your device. Valid values are `chunmi.cooker.normal2` and `chunmi.cooker.normal5`. This setting can be used to bypass the device model detection and is recommended if your device isn't always available.

## Platform services

#### Service `xiaomi_cooker.start`

Start cooking a profile.

| Service data attribute    | Optional | Description                                                          |
|---------------------------|----------|----------------------------------------------------------------------|
| `entity_id`               |      yes | Only act on a specific air purifier. Else targets all.               |
| `profile`                 |       no | Profile data which describes the temperature curve.                  |

#### Service `xiaomi_cooker.stop`

Stop the cooking process.

| Service data attribute    | Optional | Description                                                          |
|---------------------------|----------|----------------------------------------------------------------------|
| `entity_id`               |      yes | Only act on a specific air purifier. Else targets all.               |
