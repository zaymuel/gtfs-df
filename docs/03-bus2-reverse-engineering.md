# Knowledge Base: Bus2 (`bus2.info`) Reverse Engineering (`dfnoponto.com.br`)

## 1. Architecture Overview
The schedule lookup page at `https://dfnoponto.com.br/pesquisa-por-linhas/` embeds the **Bus2 Reports** web application (`technology by bus2`):
* **Interactive Web App URL:** `https://bus2.info/reports/2you/3c189?route={route_b36}&trip={trip_b36}`
* **Print / PDF View URL:** `https://bus2.info/reports/2you/3c189/print?route={route_b36}&trip={trip_b36}`

## 2. URL Parameter Reverse Engineering (Base36 Encoding)
All alphanumeric identifiers in the `bus2.info` URLs are **auto-incrementing integer primary keys encoded in Base36** (`0-9`, `a-z`):

| Parameter | Example (`0.110`) | Example (`110.2`) | Decoded Base10 (`0.110`) | Decoded Base10 (`110.2`) | Delta | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Agency / Project ID** | `3c189` | `3c189` | `5600313` | `5600313` | `0` | Fixed ID for Brasília (DF no Ponto) on Bus2. |
| **`route`** | `kt6a` | `kt6d` | `970930` | `970933` | `+3` | Sequential database ID for the bus line (`kt6b` = `970931`, `kt6c` = `970932`). |
| **`trip`** | `3gp36` | `3gp3a` | `5817858` | `5817862` | `+4` | Sequential database ID for the specific direction/itinerary (e.g., Outbound). |

### Key Takeaway
Because `route` and `trip` are sequential database primary keys rather than hashes of the line number (`"0.110"`), you do not need to brute-force them. The web app loads a master catalog JSON on initialization to populate the **Route** and **Trip** selector dropdowns.

## 3. UI Capabilities & Data Extraction Targets
Within the `bus2.info/reports/2you/3c189` interface:
1. **Filters:** `Company` (`All companies`), `Route` (e.g., `0.110 Rodoviária Do Plano Piloto/Unb`), and `Trip` (e.g., `Outbound direction Rodoviária do Plano Piloto / UnB`).
2. **Calendar Selectors:** `Today`, `Weekdays` (`Segunda a Sexta`), `Saturday` (`Sábado`), `Sunday and holidays`, and `Select a date` (includes validity metadata such as `Effective from: 23/08/2025`).
3. **Schedule Views:**
   * `View as departures`: Standard grid of origin departure times.
   * `View as table`: Tabular schedule view (check XHR payload for timepoint columns).
4. **Spatial View:**
   * `Stops and route` tab (top-right of the sub-header): Loads ordered stop lists and route shapes for the selected `trip`.

## 4. Base36 Utility Functions (Python)

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