# reQnet Recuperator — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)

Local push integration for **reQnet** recuperators (by [Inprax](https://inprax.pl)).  
Communicates via **MQTT** (push, real-time) for state and **REST API** for commands — no cloud required.

MQTT by reverse engineering what actually recuperator pushes to MQTT as imprax does not provide any dev documentation

---

## 🇵🇱 Polski

### Wymagania

- Home Assistant 2024.1+
- Integracja **MQTT** (Mosquitto) skonfigurowana w HA
- Rekuperator reQnet podłączony do sieci lokalnej
- Znany adres IP urządzenia

### Instalacja przez HACS

1. W HACS → **Integracje** → ⋮ → **Własne repozytoria**
2. Dodaj URL: `https://github.com/wsobczak/reqnet-ha`  (typ: *Integration*)
3. Znajdź „reQnet Recuperator" i kliknij **Pobierz**
4. Uruchom ponownie Home Assistant

### Instalacja ręczna

Skopiuj folder `custom_components/reqnet/` do `<config>/custom_components/` i zrestartuj HA.

### Konfiguracja

1. **Ustawienia → Urządzenia i usługi → + Dodaj integrację → reQnet Recuperator**
2. Podaj adres IP rekuperatora — integracja automatycznie:
   - Sprawdzi połączenie REST
   - Wyśle `ChangeAdditionalBrokerConfiguration` na urządzenie (konfiguruje dodatkowy broker MQTT)
   - Wykryje adres MAC z pierwszej wiadomości MQTT (do 30 s)
3. Gotowe!

> **Jeśli wykrycie MAC się nie uda:** podaj MAC ręcznie (naklejka na urządzeniu lub aplikacja reQnet). Następnie naciśnij przycisk **„Skonfiguruj broker MQTT"** na karcie urządzenia w HA.

### Tworzone encje

| Platforma | Encja | Opis |
|-----------|-------|------|
| `climate` | Rekuperator | Główna karta — tryb, temp. komfortu, wentylator |
| `sensor` | Temperatura nawiewu/wywiewu/zewnętrzna/wyrzutu | °C |
| `sensor` | Temperatura komfortu (zadana) | Odczyt z urządzenia |
| `sensor` | Wilgotność | % RH |
| `sensor` | Stężenie CO₂ | ppm |
| `sensor` | Przepływ nawiewu / wywiewu | m³/h |
| `sensor` | Wentylator (prędkość) | % — obliczany z przepływu |
| `sensor` | Sprawność odzysku ciepła | % — obliczana |
| `sensor` | Dni do wymiany filtrów | dni |
| `sensor` | Tryb pracy | tekst |
| `binary_sensor` | Alarm filtrów | problem |
| `binary_sensor` | Bypass otwarty | opening |
| `binary_sensor` | Błąd urządzenia | problem |
| `switch` | Wietrzenie / Oczyszczanie / Grzanie / Chłodzenie / … | tryby |
| `select` | Tryb bypass | auto / otwarty / zamknięty |
| `number` | Preset ręczny nawiew/wywiew | % |
| `number` | Czas wietrzenia | min (0 = bez limitu) |
| `button` | Skonfiguruj broker MQTT | diagnostyka |
| `button` | Resetuj licznik filtrów | serwis |

### Rozwiązywanie problemów

**MQTT disconnected po dodaniu:**
Naciśnij przycisk „Skonfiguruj broker MQTT" na karcie urządzenia. Sprawdź logi HA czy pojawia się `ReqNet MQTT broker config:` z potwierdzeniem.

**Encje nieaktywne:**
Urządzenie nie wysyła jeszcze danych. Sprawdź czy MQTT jest skonfigurowany i broker poprawnie ustawiony na rekuperatorze.

**Nieznany tryb pracy:**
Mapa trybów oparta jest na obserwacjach konkretnego urządzenia — może się różnić dla różnych firmware. Otwórz issue z wartością `diag_work_mode_int` (widoczna w logach podczas startu integracji).

---

## 🇬🇧 English

### Requirements

- Home Assistant 2024.1+
- **MQTT integration** (Mosquitto) configured in HA
- reQnet recuperator on the local network
- Known device IP address

### HACS Installation

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add URL: `https://github.com/wsobczak/reqnet-ha` (category: *Integration*)
3. Find "reQnet Recuperator" and click **Download**
4. Restart Home Assistant

### Manual Installation

Copy `custom_components/reqnet/` to `<config>/custom_components/` and restart HA.

### Setup

1. **Settings → Devices & Services → + Add Integration → reQnet Recuperator**
2. Enter the recuperator's IP address. The integration will automatically:
   - Verify REST API connectivity
   - Send `ChangeAdditionalBrokerConfiguration` to the device (sets secondary MQTT broker)
   - Discover the MAC address from the first MQTT message (up to 30 s)
3. Done!

> **If MAC discovery times out:** enter the MAC manually (label on device or reQnet app), then press the **"Configure MQTT Broker"** button on the device card.

### Architecture

- **State**: MQTT push — near real-time, no polling
- **Commands**: REST API (`/API/RunFunction`)
- **`iot_class`**: `local_push`

### Known Limitations

- Work mode integer mapping is based on empirical observation (mode 9 = auto confirmed). Other modes may differ across firmware versions. Please open an issue if you notice incorrect mode labels.
- `filter_days` sensor may not be reliable for all firmware versions — index mapping unverified.
- Comfort temperature setpoint is read from `Values[67]` (verified on firmware 9.25).

### Contributing

PRs and issues welcome! If you have a different firmware version, please share MQTT payload samples to help improve the mapping.

---

## Tested With

| Firmware | Device type | Status |
|----------|-------------|--------|
| 9.25 | REQNET (type 9) | ✅ Working |

---

*This integration is not affiliated with or endorsed by Inprax / reQnet.*
