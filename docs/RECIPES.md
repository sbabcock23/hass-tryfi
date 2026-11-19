# Recipes

Automations and dashboard snippets. They use a pet called Rex and a phone
notifier called `notify.mobile_app_phone`; swap in your own entity ids from
**Settings → Devices & Services → TryFi**.

## The dog has got out

Tell you when Rex leaves home, but not for the blink of a poor fix. Waits two
minutes, and ignores the tracker coming back from unknown or unavailable, so a
TryFi outage does not look like an escape.

```yaml
alias: Rex has left home
triggers:
  - trigger: state
    entity_id: device_tracker.rex_tracker
    to: not_home
    not_from: [unknown, unavailable]
    for: { minutes: 2 }
actions:
  - action: notify.mobile_app_phone
    data:
      title: Rex has left home
      message: "{{ state_attr('device_tracker.rex_tracker', 'latitude') }}, {{ state_attr('device_tracker.rex_tracker', 'longitude') }}"
mode: single
```

## Walking, with nobody out with him

Activity type turns to `walking` when the collar sees a walk. If everyone is
home, nobody is walking him.

```yaml
alias: Rex is walking on his own
triggers:
  - trigger: state
    entity_id: sensor.rex_activity_type
    to: walking
conditions:
  # zone.home's state is how many people are in it: everyone, here.
  - condition: template
    value_template: "{{ states('zone.home') | int(0) == states.person | count }}"
actions:
  - action: notify.mobile_app_phone
    data:
      message: Rex is out walking and everyone is at home.
```

## Charge the collar

```yaml
alias: Charge Rex's collar
triggers:
  - trigger: numeric_state
    entity_id: sensor.rex_collar_battery_level
    below: 15
conditions:
  - condition: state
    entity_id: binary_sensor.rex_collar_battery_charging
    state: "off"
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Rex's collar is at {{ states('sensor.rex_collar_battery_level') }}%."
```

## End of the day

```yaml
alias: Rex's day
triggers:
  - trigger: time
    at: "21:00:00"
actions:
  - action: notify.mobile_app_phone
    data:
      message: >-
        {{ states('sensor.rex_daily_steps') }} steps,
        {{ states('sensor.rex_daily_distance') }} km,
        {{ (states('sensor.rex_daily_sleep') | float(0) / 60) | round(1) }} hours asleep.
```

## The light on after dark

Turn the collar light on when Rex goes out in the dark. The collar picks the
nearest of its own colours to the one you ask for.

```yaml
alias: Rex's light after dark
triggers:
  - trigger: state
    entity_id: device_tracker.rex_tracker
    from: home
conditions:
  - condition: sun
    after: sunset
    before: sunrise
actions:
  - action: light.turn_on
    target:
      entity_id: light.rex_collar_light
    data:
      rgb_color: [255, 255, 255]
```

## Lost Mode from a dashboard

Lost Mode is a select, so it is set with `select.select_option` (not
`input_select`, which is for helpers).

```yaml
type: tile
entity: select.rex_lost_mode
features:
  - type: select-options
```

Or from a script:

```yaml
action: select.select_option
target:
  entity_id: select.rex_lost_mode
data:
  option: Lost
```
