# sinergia-vmc-modbus

Device library (standalone, non legata a Home Assistant) per le unità VMC
Sinergia con elettronica **CPRO3OEM-K** (HRD/HRD+), basata sul documento
ufficiale *"Manuale di collegamento e impostazioni MODBUS HRD/HRD+"*
(Sinergia, r.03_10-2023 / r.05) e verificata sul campo su un'unità HRD H
con elettronica CPRO3OEM-K e pannello di comando a muro EVJD920N2VW.

Costruita sopra [`modbus-connection`](https://pypi.org/project/modbus-connection/),
seguendo il pattern "device library" descritto in
https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/
(vedi [darkrain-nl/sofar-modbus](https://github.com/darkrain-nl/sofar-modbus)
come riferimento).

## Collegamento fisico

RS-485 (A+/B-/GND) sui morsetti dedicati della scheda. Impostazioni seriali
di fabbrica: **9600 baud, 8 bit, parità NESSUNA, 1 stop bit** (dichiarate
esplicitamente dal manuale Sinergia; la tabella parametri H11-H14 dello
stesso documento riporta invece un default "parità Pari" per H13 — le due
sezioni sono in contraddizione. Se la connessione non risponde, riprova con
parità Even).

## Indirizzamento registri — nota importante

Il manuale Sinergia elenca "Addr HEX" e "Addr DEC" per ogni registro, ma
`Addr DEC = Addr_HEX_convertito + 1` in tutti i gruppi tranne "COMANDI TEST"
(dove sembrano coincidere — probabile refuso, per questo quel gruppo non è
incluso qui). Gli indirizzi usati in questa libreria sono già quelli reali
da chiamare via Modbus (`Addr_HEX` / `Addr_DEC - 1`), verificati incrociando
12+ registri con la scansione reale RS-485 fatta sul campo da un altro
utente della stessa VMC.

## Uso

```python
import asyncio
from modbus_connection.pymodbus import connect_serial
from sinergia_vmc_modbus import VmcDevice

async def main():
    connection = await connect_serial(
        "/dev/ttyUSB0", baudrate=9600, parity="N", stopbits=1, timeout=3
    )
    unit = connection.for_unit(1)  # indirizzo Modbus della scheda (H11, default 1)
    device = VmcDevice(unit)

    # Abilitazioni obbligatorie (H02/H27/H28) - vedi note nel modulo device.py:
    # senza queste la macchina IGNORA le scritture sui registri corrispondenti.
    await device.enables.write("onoff_by_bms", True)

    await device.async_poll(device.COMPONENT_NAMES)
    print("Temperatura esterna:", device.probes.temp_outdoor, "°C")
    print("Stato unità:", device.status.unit_status)

    await device.command.write("onoff_by_supervisor", True)  # accende la VMC

    await connection.close()

asyncio.run(main())
```

## Struttura

- `probes` — sonde di temperatura/umidità (R/O)
- `outputs` — uscite analogiche ventilatori/compressore/serranda in % (R/O)
- `alarms` — bitmask allarmi grezze + allarme cumulativo (R/O)
- `digital_io` — bitmask ingressi/uscite digitali (R/O)
- `status` — stato dettagliato unità/ventilatori/compressore/serranda (R/O)
- `maintenance` — ore di funzionamento ventilatore mandata (R/O)
- `enables` — flag di abilitazione controllo da BMS/Modbus (R/W, **obbligatori**)
- `command` — accensione, priorità cambio modalità, modalità estate/inverno,
  reset allarmi manuali (R/W)
- `setpoints` — setpoint estate/inverno/umidità/free-cooling (R/W)
- `fan_speeds` — velocità minime/massime ventilatori per ogni modalità (R/W)
- `time_bands` — programmazione settimanale a fasce orarie (R/O), leggibile
  con `time_band(device.time_bands, "mon", 1)` → `(tipo, secondi dalla mezzanotte)`
- `time_band_setpoints` — setpoint Comfort, offset Economy/Night e velocità
  ventilatori per fascia (R/W)

Inoltre `status.active_time_band` (fascia attiva, valori di `TimeBandCode`),
`status.board_clock` (orologio della scheda, R/W) ed `enables.time_bands_enabled`
(PH03, abilitazione fasce orarie).

## Registri non documentati da Sinergia

Fasce orarie, contatori ore a 32 bit (`maintenance`) e orologio della scheda
non compaiono nel manuale Sinergia: sono stati ricavati da una scansione
completa dei registri confrontata con il manuale applicativo EVCO
*c-pro 3 OEM DE* (144CP3ODI104), in cui l'ordine dei parametri coincide con
quello dei registri.

- Contatori ore: valori a 32 bit (word bassa per prima) **già in ore**; il
  pannello li mostra in "ore x10" (906.8 sul display = 9068 h).
- Orologio e date: secondi dal 2000-01-01, ora locale della scheda (non
  segue da solo il cambio ora legale/solare).
- Da confermare sul campo: `status.active_time_band` (registro 1106) e le
  velocità di ripresa per fascia (registri 1859-1861).

Registri del gruppo "COMANDI TEST" (PT01-PT11) sono volutamente esclusi
(vedi nota sopra); possono essere aggiunti in futuro dopo verifica sul campo.
