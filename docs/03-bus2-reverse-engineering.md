# Knowledge Base: Bus2 (`bus2.info` / `mobilibus.com`) Reverse Engineering (`dfnoponto.semob.df.gov.br`)

> **Primary Authority for Schedules:** Secondary source for updated timetables and departure frequencies.  
> **Host Portal:** `https://dfnoponto.semob.df.gov.br/pesquisa-por-linhas/` embeds `https://bus2.info/reports/2you/3c189`.  
> **Backend System:** Powered by Mobilibus Technology (`mobilibus.com` / `painel.mobilibus.com`).

---

## 1. Architecture Overview & Discovered Endpoints

Through static analysis of the Angular JavaScript bundles (`main.*.js` and lazy chunk `244.*.js`) delivered by `bus2.info`, all backend REST API endpoints were uncovered.

### 1.1 Key Project Identifiers

* **Brasília Project Hash (`project_hash`):** `"3c189"` (Base36 representation of integer ID `5600313`).
* **Encryption Passphrase (Public Frontend Constant):** `"GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n"`.

---

## 2. Verified REST Endpoints

### 2.1 Master Route Catalog (Plain JSON)

* **URL:** `GET https://mobilibus.com/api/routes?project_hash=3c189`
* **Response:** Array of 930 route objects (928 Federal District bus routes with `shortName` plus 2 Metrô-DF lines with `shortName: null`).
* **Fields:** `routeId` (Base36, e.g. `"kt6a"`), `shortName` (e.g. `"0.110"`), `longName`, `agencyId`, `price`, `color`, `textColor`.
* **Output Artifact:** Production catalog saved at `data/catalog/bus2_routes.json` and mapped in `data/catalog/bus2_route_map.json` (with offline discovery cache and exploratory scrapes in `data/bus2 drafts/`).

### 2.2 Operators / Agencies (Plain JSON)

* **URL:** `GET https://mobilibus.com/api/agencies?project_hash=3c189`
* **Response:** Array of operators in DF (Urbi Mobilidade, Viação Pioneira, Piracicabana, BsBus, Marechal, etc.).

### 2.3 Comprehensive Timetable & Trips (Plain JSON)

* **URL:** `GET https://mobilibus.com/api/timetable?v=2&route_hash={routeId_b36}`
* **Example:** `https://mobilibus.com/api/timetable?v=2&route_hash=kt6a` (Line `0.110`).
* **Response Structure:**
  * `timetable.directions[]`: Direction variants (`directionId`, `desc`).
    * `services[]`: Split by operating calendar profile:
      * `"Segunda a Sexta"` (`serviceId`: `"cc4i"`, `days`: `[false, true, true, true, true, true, false]`).
      * `"Sábado"` (`serviceId`: `"cc4j"`).
      * `"Domingo e Feriado"` / `"Domingo"`.
      * `departures[]`: Array of departures with `dep` (`"05:55"`), `arr` (`"06:27"`), `seq`, `wa`.
  * `timetable.trips[]`: Maps direction and sequence to Base36 `tripId` (e.g., `"3gp36"`), `headsign`, and `directionId`.

### 2.4 Intermediate Stop Offsets & Polyline Geometry (Plain JSON)

* **URL:** `GET https://mobilibus.com/api/trip-details?v=2&trip_hash={tripId_b36}`
* **Example:** `https://mobilibus.com/api/trip-details?v=2&trip_hash=3gp36` (Line `0.110`, Outbound).
* **Key Finding:** Contains pre-calculated cumulative travel time offsets in seconds (`"int"`) for every intermediate stop!
  * Stop 0 (`Terminal Rodoviário`): `int: 0`
  * Stop 1 (`Biblioteca Nacional`): `int: 97` (~1m 37s)
  * Stop 2 (`Ministério da Indústria`): `int: 239` (~4m 00s)
  * Stop 3 (`L2 Norte`): `int: 270` (~4m 30s)
  * Stop 4 (`SGAN 601 SERPRO`): `int: 377` (~6m 17s)
  * Also includes `stops[].lat`, `stops[].lng`, `stops[].name`, and Google encoded polyline `shape`.

### 2.5 Encrypted Painel Endpoints (CryptoJS AES / OpenSSL Format)

* **Endpoints:**
  * `GET https://painel.mobilibus.com/v2/api/public/get-trips/?ph=3c189&rsn={shortName}`
  * `GET https://painel.mobilibus.com/v2/api/public/get-trip-template/{tripId}`
* **Payload Format:** `{"data": "U2FsdGVkX1..."}` (AES-CBC encrypted using passphrase `"GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n"`).
* **Decryption Implementation:** Fully implemented in `bus2_client.decrypt_payload()` using `cryptography` via OpenSSL `EVP_BytesToKey` MD5 key derivation.

#### 2.5.1 Passphrase Lifecycle & Rotation Procedure
The current passphrase `"GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n"` is a build-time frontend constant embedded inside Bus2's compiled Angular webpack chunks (`main.*.js` and `244.*.js`). Because this asset is deployed publicly to anonymous browsers visiting `https://bus2.info/reports/2you/3c189`, there are no backend credentials or API keys involved.

**If Bus2 rotates the passphrase in a new frontend release:**
1. **Detection:** Decryption calls in `bus2_client.py` will fail with a padding error (`ValueError: Invalid padding bytes`).
2. **Sniffing / Extraction:**
   - Fetch the latest Angular runtime chunks from `https://bus2.info/reports/2you/3c189`:
     ```bash
     curl -s https://bus2.info/reports/2you/3c189 | grep -o 'src="[^"]*main[^"]*"'
     ```
   - Search the downloaded `main.*.js` or chunk `244.*.js` using regular expressions for the CryptoJS AES decryption call:
     ```python
     re.findall(r'decrypt\([^,]+,\s*["\']([^"\']{15,40})["\']', js_content)
     ```
3. **Decoupled Override:**
   - The passphrase is decoupled in `config.py` as `BUS2_ENCRYPTION_KEY`.
   - Operators can override the key without modifying source code via the environment variable:
     ```bash
     export BUS2_ENCRYPTION_KEY="<new_passphrase>"
     ```

### 2.6 `pesquisa-geral` Web App

Both `https://dfnoponto.semob.df.gov.br/pesquisa-geral/` and `https://dfnoponto.com.br/pesquisa-geral/` embed `<iframe src="https://bus2.info/embed/df/brasilia">`, which runs against the exact same backend endpoints listed above.

---

## 3. Base36 Database Key Encoding

All alphanumeric identifiers in the Bus2 URLs and API endpoints are auto-incrementing integer database primary keys encoded in **Base36** (`0-9`, `a-z`):

| Parameter | Example (`0.110`) | Example (`110.2`) | Decoded Base10 (`0.110`) | Decoded Base10 (`110.2`) | Delta | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Project Hash** | `3c189` | `3c189` | `5600313` | `5600313` | `0` | Fixed ID for Brasília (DF no Ponto). |
| **`routeId`** | `kt6a` | `kt6d` | `970930` | `970933` | `+3` | Sequential DB ID for the bus line. |
| **`tripId`** | `3gp36` | `3gp3a` | `5817858` | `5817862` | `+4` | Sequential DB ID for the direction itinerary. |

### Base36 Python Utility (Implemented in `bus2_client.py`)

```python
def base36_decode(token: str) -> int:
    """Converts a Base36 string (e.g., 'kt6a') to its integer ID (970930)."""
    return int(token, 36)

def base36_encode(num: int) -> str:
    """Converts an integer ID (970930) to a Base36 string ('kt6a')."""
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    chars = []
    while num > 0:
        num, rem = divmod(num, 36)
        chars.append(alphabet[rem])
    return "".join(reversed(chars))

if __name__ == "__main__":
    assert base36_decode("3c189") == 5600313
    assert base36_decode("kt6a") == 970930
    assert base36_decode("kt6d") == 970933
    assert base36_decode("3gp36") == 5817858
    assert base36_decode("3gp3a") == 5817862

```

---

## 4. Summary Matrix for GTFS Pipeline

| Pipeline Step | Endpoint Used | Purpose |
| :--- | :--- | :--- |
| **Catalog Discovery** | `GET /api/routes?project_hash=3c189` | All 928 active bus lines without third-party scraping |
| **Updated Schedules** | `GET /api/timetable?v=2&route_hash={id}` | Recent departure times per service calendar |
| **Stop Offsets** | `GET /api/trip-details?v=2&trip_hash={id}` | Empirical intermediate stop travel times (`int`) |
| **Stops & Shapes** | Official DFTrans API (`sistemas.dftrans.df.gov.br`) | Core authoritative spatial data (`/percurso/` & `/parada/geo/paradas`) |
