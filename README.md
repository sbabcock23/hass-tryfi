# TryFi for Home Assistant
![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png?style=for-the-badge)
[![](https://img.shields.io/github/release/sbabcock23/hass-tryfi/all.svg?style=for-the-badge)](https://github.com/sbabcock23/hass-tryfi/releases)
![release_date](https://img.shields.io/github/release-date/sbabcock23/hass-tryfi.svg?style=for-the-badge)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![](https://img.shields.io/github/license/sbabcock23/hass-tryfi?style=for-the-badge)](LICENSE)
[![](https://img.shields.io/github/workflow/status/sbabcock23/hass-tryfi/Validate%20with%20hassfest?style=for-the-badge)](https://github.com/sbabcock23/hass-tryfi/actions)

This allows you to integrate [TryFi](https://tryfi.com) Smart GPS Collars with Home Assistant.

## Features
Current functionality includes:
* Device Tracker - your pet will show up in HA using the GPS coordinates from the collar
* Step Counter - it will report your pets daily, weekly, and monthly steps
* Distance Counter - it will report your pets daily, weekly and monthly distance
* Battery Level - it will report your Pet's collar battery level
* Battery Charging - it will report if your Pet's collar is charging
* Collar Light - you can control the light on the collar by turning it on and off and setting the color
* Lost Dog Mode - allows you to select Lost mode if your dog if it is lost and select Safe if it is found
* Bases - reports the status of the base (online/offline)

## Donate
If you would like to donate you can use my TryFi referral code "[395FX4](https://shop.tryfi.com/r/395FX4/?utm_source=referrals)" on your next purchase.

# Installation
## Pre-Requisities
* Home Assistant >= 2023.1.0
* TryFi dog collar with active cellular subscription
* [HACS](https://github.com/custom-components/hacs) is already installed

## Installation Methods

### HACS Install
1. Search for `TryFi` under `Integrations` in the HACS Store tab.
2. Add the [Integration](#configuration) to your HA and configure.

### Manual Install
1. In your `/config` directory, create a `custom_components` folder if one does not exist.
2. Copy the [tryfi](https://github.com/sbabcock23/hass-tryfi/tree/master/custom_components) folder and all of it's contents to your `custom_components` directory.
3. Restart Home Assistant.
4. Add the [Integration](#configuration) to your HA and configure.

## Configuration
1. After installing TryFi go to Configuration --> Integrations and add a new Integration
2. Search for TryFi
3. Enter in your TryFi username and password. Optionally you can select a polling frequency option (in seconds). Suggestion is nothing less then 5.
4. Click Submit

![Setup](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/setup.jpg?raw=true)

## Validation
Once you have added the integration, you will see 1 or more devices and entities associated with this integration. To validate its accuracy, you can review the steps and distance counters for your pet or its current whereabouts.

![Integration](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/tryfiaftersetup.jpg?raw=true)

### Dog Device and Entities
#### Device

![Dog Device](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/dogdevice.jpg?raw=true)

#### Entities

![Dog Entities](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/dogentities.jpg?raw=true)

### Base Device and Entities

![Base Device and Entities](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/dogbase.jpg?raw=true)

# How to Use
## Light Collar
The light on your Pet's collar is represented as a light switch in HA. It can either be turned on or off.
The color can be set. The collar only supports Red, Green, Blue, LightBlue, Purple, Yellow, and White. The closest color to your selection will be used.

![Lovelace](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/doglight.jpg?raw=true)

## Lost Dog Mode
TryFi is equiped with a "Lost Dog Mode" functionality. In HA this is represented by a select entity.
Select Lost if your pet is lost or Safe if your pet is OK.

![Lovelace](https://github.com/sbabcock23/hass-tryfi/blob/master/docs/doglostmode.png?raw=true)

# Lovelace

## Entities
```
type: entities
entities:
  - entity: select.harley_lost_state
  - entity: sensor.harley_collar_battery_level
  - entity: binary_sensor.harley_collar_battery_charging
  - entity: sensor.home_base
  - entity: sensor.harley_daily_steps
  - entity: sensor.harley_weekly_steps
  - entity: sensor.harley_monthly_steps
  - entity: sensor.harley_daily_distance
  - entity: sensor.harley_weekly_distance
  - entity: sensor.harley_monthly_distance
  - entity: sensor.harley_daily_sleep
  - entity: sensor.harley_weekly_sleep
  - entity: sensor.harley_monthly_sleep
  - entity: sensor.harley_daily_nap
  - entity: sensor.harley_weekly_nap
  - entity: sensor.harley_monthly_nap
```
## Light
```
type: light
entity: light.harley_collar_light
```

# Automation Examples
## Turn on the Collar Light After Dark
Turns on the collar light after dark if the pet is not home.
```
- id: '1604060166498'
  alias: Turn on Light After Dark If Not Home
  description: ''
  trigger:
  - platform: sun
    event: sunset
  condition:
  - condition: and
    conditions:
    - condition: device
      device_id: a7237a6c1144fcd90828b21de2572603
      domain: device_tracker
      entity_id: device_tracker.pet_tracker
      type: is_not_home
  action:
  - type: turn_on
    device_id: a7237a6c1144fcd90828b21de2572603
    entity_id: light.pet_collar_light
    domain: light
  mode: single
```
## Fully Charged Notification
Sends notification when battery has charged to 100%.
```
- id: '1661129896868'
  alias: Pet's Collar - Fully Charged
  description: ''
  trigger:
  - platform: state
    entity_id:
    - sensor.pet_collar_battery_level
    to: '100'
    for:
      hours: 0
      minutes: 0
      seconds: 0
  condition:
  - condition: state
    entity_id: binary_sensor.pet_collar_battery_charging
    state: 'on'
  action:
  - service: notify.everyone_phone
    data:
      message: Pet's collar is fully charged!
  mode: single
```
# Known Issues
* It sometimes takes time for the status to accurately refresh in HA. For example the light on/off status and the Lost Mode select status.

# Future Enhacements
* Allow for the selection of the LED light color
* Enable possibility of if pet not home and not with owner then trigger lost dog mode

# Version History
## 0.0.22
* Added support for changing the color of the colar's LED light. This is currently based on a pre-defined set of colors.
## 0.0.21
* Version bump of pytry package
## 0.0.20
* Fix - Due to recent changes by TryFi, additional changes were required in the pytryfi library. Bumping version to include those changes/fixes.
## 0.0.19
* Fix - pets without collars were causing errors.
## 0.0.18
* Enhancement - Battery Charging - it will report if your Pet's collar is charging
## 0.0.17
* Enhancement - added the attribute ConnectedTo which will determine if the pet is connected to a person, base, etc.
* Fix - base data was not updating. This issue is resolved.
## 0.0.16
* Enhancement - requested to add the attributes Activity Type, Current Place Name and Current Place Address.
## 0.0.15
* Version bump to support latest pytryfi version 0.0.16 that includes multiple households
## 0.0.14
* Fix - fixed sleep and nap units from hours to minutes with proper conversion
## 0.0.13
* Enhancement - Added Sleep and Nap "sensors"/attributes based on new version of pytryfi
## 0.0.12
* Fix - Issue where base status (online/offline) was not set correctly.
## 0.0.11
* Version bump to support latest pytryfi version 0.0.14.1
## 0.0.10
* Lost Mode is now a select entity instead of a lock entity
## 0.0.9
* Updated dependency version of pytryfi
* Fixed [Issue #30](https://github.com/sbabcock23/hass-tryfi/issues/30) - Convert to Async
## 0.0.8
* Updating dependency version of pytryfi
## 0.0.7
* Updating dependency version of pytryfi
## 0.0.6
* Steps unit was added to enable charting of dogs steps over time.
## 0.0.5
* Fixed [Issue #15](https://github.com/sbabcock23/hass-tryfi/issues/15) - dependency update
## 0.0.4
* Fixed [Issue #17](https://github.com/sbabcock23/hass-tryfi/issues/17) - converted to async
## 0.0.3
* Multiple bases fix
## 0.0.2
* Documentation updates
## 0.0.1
* Initial Release with basic functionality including light on/off, device tracker, lock mode of dog and general stats

# Links
* [Python TryFi Interface](https://github.com/sbabcock23/pytryfi)
* [TryFi]((https://tryfi.com/))
