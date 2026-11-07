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
- Live position, battery level and online state, polled from the bridge.
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

## License

MIT — see [LICENSE](LICENSE).
