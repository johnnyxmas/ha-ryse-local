# RYSE SmartBridge (local) for Home Assistant

A **local-only** Home Assistant integration for [RYSE SmartShade](https://helloryse.com)
motorized shades driven through a RYSE **SmartBridge**. It talks directly to the
bridge on your LAN over its HTTP API — no cloud account, no polling of RYSE's
servers, and it keeps working if the internet is down.

> Not affiliated with, endorsed by, or supported by RYSE / Axis Labs. "RYSE",
> "SmartBridge" and "SmartShade" are the property of their respective owners.

## Features

- Each shade appears as a `cover` entity with **open**, **close**, and
  **set position** (0-100, where 100 = fully open).
- **Speed** (`number`, 0-100%): how fast the shade's motor moves, on the same
  scale as the RYSE app.
- **Obstacle detection** (`switch`): stops a shade when it meets resistance.
- **Battery** (`sensor`, %) and **Power source** (`sensor`: battery, AC adapter
  or USB charger) per shade.
- The bridge and each shade are separate devices, with firmware and hardware
  versions shown; shades hang off the bridge.
- One config entry per bridge; all shades on that bridge are added automatically.
- Pure local HTTP - works without the RYSE cloud.

## Requirements

- A RYSE **SmartBridge** on the same network as Home Assistant, with a static or
  reserved IP address (recommended, since the integration connects by IP).
- The shades already paired to the bridge using the RYSE app.

## Installation

### From HACS (recommended)

1. In HACS → **Integrations**, search for **RYSE SmartBridge (local)** and download it.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → RYSE SmartBridge (local)**.
4. Enter the bridge's IP address. Leave **Serial** blank unless your bridge has
   local security enabled (see below).

### Fallback: custom repository

If the integration isn't yet in your HACS catalog, add it manually:

1. In HACS → **Integrations** → ⋮ → **Custom repositories**, add
   `https://github.com/johnnyxmas/ha-ryse-local` as category **Integration**.
2. Then follow steps 2–4 above.

## Configuration

| Field | Required | Notes |
|---|---|---|
| Bridge IP address | yes | e.g. `192.168.0.123` |
| Serial number | no | Only needed if the bridge's local-security option is on. When set, it is sent as the `Authorization` header on every request. |

## How it works

The integration uses the bridge's local API through the
[`pyryse`](https://pypi.org/project/pyryse/) library, which documents the API in
full ([`PROTOCOL.md`](https://github.com/johnnyxmas/pyryse/blob/main/docs/PROTOCOL.md)):

- `GET /lua/device/<dvc_id>` - the bridge and every shade (position, battery,
  speed, obstacle detection, power type, firmware).
- `POST /lua/device/<dvc_id>/gear/<gear_id>/position` with `{"position": 0-100}` -
  move a shade.
- `GET`/`POST .../gear/<gear_id>/speed` and `.../obstacle_detection` - the
  per-shade settings.

Home Assistant's convention is **100 = open, 0 = closed**; the bridge uses the
opposite, and the integration converts. Speed is stored by the bridge as 40-100;
the integration shows the app's 0-100% (`app % = (bridge - 40) / 60 * 100`).

## Limitations

- **Polling.** Position/battery refresh on an interval (default 20 s). A move
  triggers an immediate refresh, but the motor takes several seconds to settle.
- **No tilt / no stop.** The bridge API exposes absolute position only.
- **Routines are not available.** The app's routines (scenes) don't have a known
  local API, so the integration cannot run them.
- **Settings are slow to apply.** After you change speed or obstacle detection,
  the bridge takes a few seconds to apply it. The controls keep showing the
  value you set for up to 30 seconds so they don't jump back while the bridge
  catches up.
- **Turning obstacle detection off removes a safety feature.** The shade will no
  longer stop when it meets resistance.
- **Not every speed percentage is reachable.** The bridge has 61 speed values
  for the app's 101 percentages, so a few percentages read back one lower than
  you set (for example 2% reads as 1%), the same as in the app.
- **Power source is inferred.** RYSE doesn't document it; the mapping (battery,
  AC adapter, USB charger) comes from watching one shade's reading change as its
  power source was swapped.
- **Offline shades** show as unavailable until they rejoin the bridge.
- **One local connection.** Keep the RYSE phone app closed if you see conflicts.
- Tested against SmartShade firmware `5.3.2` on a 2023-era SmartBridge. Other
  firmware is unverified — please open an issue with what you see.

## Security & privacy

The SmartBridge's local API is, by default, **reachable without authentication**
by any device on the same LAN. This integration does not weaken anything — it
uses the same interface the RYSE app uses — but you should treat the bridge like
any other IoT device: keep it on a trusted network segment / IoT VLAN. If RYSE
ships a firmware that requires the serial as a credential, set it in the
integration's **Serial** field.

## Examples: quick-set presets

The shades expose position, so presets like "open / half / closed" are a couple
of small scripts plus a dashboard card — kept here as examples rather than built
into the integration, so you choose the positions and which shades they cover.

`scripts.yaml` (replace the entity list with your own shade entities):

```yaml
shades_open_all:
  alias: Shades - open all
  sequence:
    - action: cover.set_cover_position
      target:
        entity_id: [cover.living_room_2, cover.living_room_3, cover.living_room_4, cover.living_room_5]
      data: {position: 100}
shades_half_all:
  alias: Shades - half open
  sequence:
    - action: cover.set_cover_position
      target:
        entity_id: [cover.living_room_2, cover.living_room_3, cover.living_room_4, cover.living_room_5]
      data: {position: 50}
shades_close_all:
  alias: Shades - close all
  sequence:
    - action: cover.set_cover_position
      target:
        entity_id: [cover.living_room_2, cover.living_room_3, cover.living_room_4, cover.living_room_5]
      data: {position: 0}
```

A row of buttons for a dashboard view:

```yaml
type: horizontal-stack
cards:
  - type: button
    name: Open
    tap_action: {action: perform-action, perform_action: script.shades_open_all}
  - type: button
    name: Half
    tap_action: {action: perform-action, perform_action: script.shades_half_all}
  - type: button
    name: Closed
    tap_action: {action: perform-action, perform_action: script.shades_close_all}
```

## Icon / branding

Brand images ship in [`custom_components/ryse_local/brand/`](custom_components/ryse_local/brand/)
(`icon.png`, `logo.png`). Since Home Assistant 2026.3, custom integrations serve
their own brand images from this `brand/` folder through the brands proxy
(`/api/brands/integration/ryse_local/…`) — local images take priority over the
CDN, with no registration and no entry in `home-assistant/brands` required.

The images are a **RYSE trademark**, included only to identify the RYSE product
this integration controls. They are **not** covered by this repository's MIT
license — see [`custom_components/ryse_local/brand/NOTICE`](custom_components/ryse_local/brand/NOTICE).

## License

MIT — see [LICENSE](LICENSE). Covers the integration code only, not the RYSE name
or logo.
