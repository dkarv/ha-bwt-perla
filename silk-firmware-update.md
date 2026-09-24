# Perla Silk — local firmware update (unofficial)

> **⚠️ WARNING — DO THIS AT YOUR OWN RISK**
>
> Flashing firmware can brick your softener’s Wi‑Fi module, interrupt softening,
> void warranty, and require BWT service to recover. There is **no** official
> support for this procedure. Wrong image, interrupted transfer, power loss, or
> an MD5 mismatch mid‑process can leave the device unusable. Only proceed if you
> accept full responsibility for any damage or data loss. Prefer asking BWT
> support for an official OTA when possible.

This note documents a **community reverse‑engineered** path for BWT Perla Silk
Wi‑Fi devices that expose the local HTTP API on port 80. It is **not** part of
the Home Assistant integration runtime; it is research / recovery documentation
only.

---

## 0. Read current firmware info (safe)

On the LAN (no auth):

```bash
curl -s "http://DEVICE_IP/silk/status" | jq .
```

Useful fields:

| Field | Meaning |
| --- | --- |
| `version` | Firmware version string (e.g. `2.0307`) |
| `gitver` | Build / git counter (e.g. `157`) — UI often shows `version - gitver` |
| `productCode` | Device product code |
| `state` | Device state (`M_STATE_CONFIGURED`, `M_STATE_OTA`, `M_STATE_REBOOT`, …) |
| `network.ip` / `network.mac` | LAN identity |
| `registration.registered` | Cloud registration flag |

Example display string: `{version} - {gitver}` → `2.0307 - 157`.

---

## 1. Get an API access token from the BWT app

Official cloud calls use OIDC against BWT Account, same as the
**BWT Best Water Home** mobile app.

**Recommended (no secrets in scripts):** capture a live Bearer token while the
app is logged in.

1. Put a TLS‑intercepting proxy on your phone path (e.g. mitmproxy / Charles) **only on a device you control**.
2. Open the BWT app and load your Silk device.
3. Copy an `Authorization: Bearer …` header from a request to  
   `https://api.bwt-group.com/api/...`
4. Export it for the shell (short‑lived; refresh when it expires):

```bash
export BWT_TOKEN='eyJ...'   # paste access_token only
export API='https://api.bwt-group.com/api'
```

Notes:

- Production API base: `https://api.bwt-group.com/api/`
- Auth host: `https://account.bwt-group.com/auth/v2/connect/...`
- Scopes used by the app include `openid offline_access email profile aidu-api bwt_digital_toolbox`
- Do **not** commit tokens. Do **not** publish refresh tokens.

---

## 2. Discover / download the latest firmware binary

### 2a. Ask the cloud for “latest” metadata

The app calls:

```http
GET /firmware/productfamily/{productFamilyName}/latest
Authorization: Bearer <token>
```

Example (family name must match your product line — Silk cloud `DeviceType` is
often `persil`; confirm against your account / product profile):

```bash
# Try the family name that matches your product (inspect app traffic if unsure)
curl -sS -H "Authorization: Bearer $BWT_TOKEN" \
  "$API/firmware/productfamily/persil/latest" | jq .
```

Inspect the JSON for:

- a **version** field (app code uses `versionString`)
- a **download URL** (field name varies; look for `http(s)://…` pointing at a `.bin`)
- an **MD5** (32 hex chars) if present — the device verifies MD5 before reboot

Download the image:

```bash
# Replace URL with the one from the JSON response
curl -L -o firmware.bin 'https://EXAMPLE-HOST/path/to/image.bin'
md5 firmware.bin   # macOS; or: md5sum firmware.bin
```

Valid ESP32 app images for this platform typically start with magic byte `0xE9`.

### 2b. Optional: let BWT cloud push OTA (no local flash)

If you only want BWT’s servers to schedule an update (same path as the app’s
“update to latest” for other product families):

```bash
# productInstanceId from your product profile / device list in the API
curl -sS -X PUT -H "Authorization: Bearer $BWT_TOKEN" \
  "$API/productidentities/PRODUCT_INSTANCE_ID/firmware/update_to_latest"
```

That path talks to the device over the **cloud** (Azure IoT `FirmwareUpdate`
with URL + MD5). It is still **at your own risk** and may not be exposed for
every Silk account / region.

### 2c. If you already have a `.bin`

You can skip the cloud download and host the file yourself on any HTTP server
reachable from the softener (same LAN recommended):

```bash
# Example: serve current directory on port 8000
python3 -m http.server 8000
# Device will fetch: http://YOUR_PC_LAN_IP:8000/firmware.bin
```

Compute MD5 of the exact bytes you will serve — the softener rejects bad MD5.

---

## 3. Trigger local OTA on the device (URL + MD5)

Firmware analysis and live probes show:

```http
POST http://DEVICE_IP/firmware/ota
Content-Type: application/json

{"url":"http://HOST/path/firmware.bin","md5":"<32-hex-md5-lowercase>"}
```

Example:

```bash
DEVICE_IP=192.168.x.x
BIN_URL="http://YOUR_PC_LAN_IP:8000/firmware.bin"
BIN_MD5="$(md5 -q firmware.bin)"   # or: md5sum firmware.bin | awk '{print $1}'

curl -sS -X POST "http://$DEVICE_IP/firmware/ota" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"$BIN_URL\",\"md5\":\"$BIN_MD5\"}"
# Expected body on accept: Accepted
```

Then watch state:

```bash
watch -n 2 "curl -s http://$DEVICE_IP/silk/status | jq -c '{state,version,gitver}'"
```

Observed behaviour:

1. Response body `Accepted`
2. `/silk/status` → `state` becomes `M_STATE_OTA`
3. Device HTTP‑GETs `url`, checks MD5, writes ESP32 OTA partition
4. On success → reboot (`M_STATE_REBOOT` / similar) then back to `M_STATE_CONFIGURED`
5. On failure (bad URL / bad MD5 / not enough space) it should leave OTA and return
   to configured — **do not power‑cycle mid‑write**

Firmware log strings (for debugging): `Set OTA Values URL[%s], MD5[%s]`,
`Cancelling update, rejected MD5`, `Update successfully completed. Rebooting`.

---

## 4. Alternative: direct upload endpoint

The same firmware also registers:

```text
POST http://DEVICE_IP/firmware/upload
```

This is intended for a **multipart file upload** (webserver supports
`Expect: 100-continue`). Exact form field names are less well documented than
`/firmware/ota`. Prefer the URL+MD5 flow in §3 unless you are experimenting.

Example sketch (verify on a non‑critical device first):

```bash
curl -sS -X POST "http://$DEVICE_IP/firmware/upload" \
  -F "file=@firmware.bin;filename=firmware.bin"
```

Large uploads may take a long time; do not interrupt.

---

## 5. Minimal checklist

1. Note current `version` / `gitver` from `/silk/status`.
2. Obtain a matching Silk Wi‑Fi image (same product line).
3. Verify MD5 of the file you will serve.
4. Serve the file over HTTP from the LAN.
5. `POST /firmware/ota` with `url` + `md5`.
6. Wait for `M_STATE_OTA` → reboot → `M_STATE_CONFIGURED`.
7. Confirm new `version` / `gitver`.

---

## References (unofficial)

- Local status / registers: `GET /silk/status`, `GET /silk/registers`
- Local OTA routes present in firmware webserver: `/firmware/ota`, `/firmware/upload`
- Cloud (app): `GET firmware/productfamily/{family}/latest`,  
  `PUT productidentities/{id}/firmware/update_to_latest`
- Cloud OTA to device uses a `FirmwareUpdate` command with **URL + MD5**
  (same parameters as local `/firmware/ota`)

---

> **⚠️ WARNING — DO THIS AT YOUR OWN RISK**
>
> This document is best‑effort reverse engineering. Endpoints, JSON field names,
> and product‑family identifiers can change with firmware or region. Using the
> wrong binary or aborting an update can permanently damage the device. You are
> solely responsible for the outcome. When in doubt, stop and contact BWT
> support for an official update.
