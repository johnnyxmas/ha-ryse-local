# RYSE SmartBridge (local) for Home Assistant

A **local-only** Home Assistant integration for [RYSE SmartShade](https://helloryse.com)
motorized shades driven through a RYSE **SmartBridge**. It talks directly to the
bridge on your LAN over its HTTP API — no cloud account, no polling of RYSE's
servers, and it keeps working if the internet is down.

> Not affiliated with, endorsed by, or supported by RYSE / Axis Labs. "RYSE",
> "SmartBridge" and "SmartShade" are the property of their respective owners.

## Features

- Each shade appears as a `cover` entity with **open**, **close**, and
  **set position** (0–100, where 100 = fully open).
- Live position, online state and battery level, polled from the bridge.
- One battery sensor per shade that reports a battery level.
- One config entry per bridge; all shades on that bridge are added automatically.
- Pure local HTTP — works without the RYSE cloud.

## Requirements

- A RYSE **SmartBridge** on the same network as Home Assistant, with a static or
  reserved IP address (recommended, since the integration connects by IP).
- The shades already paired to the bridge using the RYSE app.

## Installation (HACS)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**, add
   `https://github.com/johnnyxmas/ha-ryse-local` as category **Integration**.
2. Install **RYSE SmartBridge (local)** and restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → RYSE SmartBridge (local)**.
4. Enter the bridge's IP address. Leave **Serial** blank unless your bridge has
   local security enabled (see below).

## Configuration

| Field | Required | Notes |
|---|---|---|
| Bridge IP address | yes | e.g. `192.168.0.123` |
| Serial number | no | Only needed if the bridge's local-security option is on. When set, it is sent as the `Authorization` header on every request. |

## How it works

The integration uses the bridge's local API:

- `GET /lua/device` — enumerates shades (id, name, position, battery, online).
- `GET  /lua/device/<dvc_id>/gear/<gear_id>/position` — one shade's position.
- `POST /lua/device/<dvc_id>/gear/<gear_id>/position` with body `{"position": 0-100}` — move a shade.

Positions use Home Assistant's convention: **100 = open, 0 = closed**.

## Limitations

- **Polling.** Position/battery refresh on an interval (default 20 s). A move
  triggers an immediate refresh, but the motor takes several seconds to settle.
- **No tilt / no stop.** The bridge API exposes absolute position only.
- **Speed and obstacle detection are not exposed yet.** The bridge stores a
  per-shade speed and an on/off obstacle-detection setting, but the integration
  doesn't surface either. Speed is accepted only in the bridge range 40-100,
  which the app shows as 0-100%.
- **Routines are not available.** The app's routines (scenes) don't have a known
  local API, so the integration cannot run them.
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
