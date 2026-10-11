"""Register map for Sinergia VMC units (CPRO3OEM-K electronics, HRD/HRD+).

Source: "Manuale di collegamento e impostazioni MODBUS HRD/HRD+" (Sinergia,
r.03_10-2023 / r.05), cross-checked against a real RS-485 register scan.
Time bands, hour counters and the board clock are NOT documented by Sinergia:
they were deduced from a full register scan matched against the EVCO
"c-pro 3 OEM DE" application manual (144CP3ODI104).

IMPORTANT addressing note: the manual's "Addr DEC" column is always
Addr_HEX + 1 (except in the "COMANDI TEST" group, which is excluded here -
its own table looks inconsistent with every other group and needs field
verification before use). Every address below is the REAL address to call
over Modbus (Addr_HEX / Addr_DEC - 1).

IMPORTANT enable note: per the manual, H02/H27/H28 (see `Enables` below)
MUST be set to 1 for the corresponding writes (on/off, integration,
dehumidify) to have any effect at all. Without them the unit silently
ignores the write - no error, nothing happens.
"""

from __future__ import annotations

from enum import IntEnum

from modbus_connection.model import Component, Device
from modbus_connection.model.fields import boolean, enum, gauge, integer, uint32

__all__ = [
    "Alarms",
    "Calibrations",
    "TimeBandCode",
    "TimeBandSetpoints",
    "TimeBands",
    "Command",
    "DigitalIO",
    "Enables",
    "FanSpeeds",
    "Maintenance",
    "Outputs",
    "Probes",
    "Setpoints",
    "UnitStatusCode",
    "Status",
    "VmcDevice",
]


# --------------------------------------------------------------------------- #
# Enums for the more useful status registers
# --------------------------------------------------------------------------- #


class UnitStatusCode(IntEnum):
    OFF = 0
    OFF_DI = 1
    OFF_BMS = 2
    OFF_SCHEDULER = 3
    OFF_RTC = 4
    ON = 5


class ModeStatusCode(IntEnum):
    SUMMER_MANUAL = 0
    WINTER_MANUAL = 1
    SUMMER_AUTO = 2
    WINTER_AUTO = 3
    SUMMER_DI = 4
    WINTER_DI = 5


class FanStatusCode(IntEnum):
    DISABLE = 0
    OFF = 1
    WAIT_ON = 2
    ON = 3
    WAIT_OFF = 4
    ALARM = 5


class CompressorStatusCode(IntEnum):
    DISABLE = 0
    ALARM = 1
    MANUAL = 2
    WAIT_ON = 3
    ON = 4
    WAIT_OFF = 5
    OFF = 6


class DamperStatusCode(IntEnum):
    DISABLE = 0
    OFF = 1
    WAIT_OFF = 2
    ON = 3


class TimeBandCode(IntEnum):
    """Tipo di fascia oraria (EVCO c-pro 3 OEM, menù "tb")."""

    DISABLED = 0
    OFF = 1
    COMFORT = 2
    ECONOMY = 3
    NIGHT = 4


class RecircDamperStatusCode(IntEnum):
    OFF = 0
    ON = 1
    DISABLE = 2


# --------------------------------------------------------------------------- #
# Read-only components
# --------------------------------------------------------------------------- #


class Probes(Component):
    """Sonde di temperatura/umidità interne all'unità (R/O)."""

    register_space = "holding"

    temp_return_room = gauge(499, 0.1, unit="°C")
    """Sonda temperatura ambiente/ripresa sul pannello a muro.
    Non leggibile se il pannello remoto non è presente/abilitato."""

    temp_outdoor = gauge(500, 0.1, unit="°C")
    temp_water = gauge(501, 0.1, unit="°C")
    temp_exhaust = gauge(502, 0.1, unit="°C")
    temp_free_cooling = gauge(510, 0.1, unit="°C")

    temp_evaporation = gauge(511, 0.1, unit="°C")
    """Solo versione Inverter con compressore."""

    humidity_return_room = integer(505, signed=False, unit="%")
    """Sonda umidità ambiente/ripresa sul pannello a muro.
    Non leggibile se il pannello remoto non è presente/abilitato."""


class Outputs(Component):
    """Uscite analogiche ventilatori/compressore/serranda, in % (R/O)."""

    register_space = "holding"

    supply_fan_pct = gauge(639, 0.01, signed=False, unit="%")
    return_fan_pct = gauge(640, 0.01, signed=False, unit="%")

    compressor_pct = gauge(641, 0.01, signed=False, unit="%")
    """Solo versione Inverter."""

    external_damper_pct = gauge(642, 0.01, signed=False, unit="%")


class Alarms(Component):
    """Allarmi: bitmask grezze + registro cumulativo (R/O)."""

    register_space = "holding"

    # bit00=AL01 ... bit15=AL16
    packed_1 = integer(768, signed=False)
    # bit00=AL17 ... bit15=AL32
    packed_2 = integer(769, signed=False)
    # bit00=AL33, bit01=AL34, bit02=AL35, bit03=riservato, bit04=AL37,
    # bit05=AL38, bit06=AL39
    packed_3 = integer(770, signed=False)

    active = boolean(1103)
    """Allarme cumulativo attivo (OR di tutti gli allarmi)."""


class DigitalIO(Component):
    """Ingressi/uscite digitali, come bitmask grezze (R/O)."""

    register_space = "holding"

    # bit0-1=Remote on/off, bit2-3=Summer/Winter, bit4-5=Dehum request,
    # bit6-7=Thermo request
    logic_di1 = integer(257, signed=False)

    # bit0-1=Supply fan, bit2-3=Return fan, bit4-5=Compressor,
    # bit6-7=External damper, bit8-9=Recirculation damper,
    # bit10-11=Water flow valve, bit12-13=Water condensation valve,
    # bit14-15=Air condensation valve
    do1 = integer(384, signed=False)

    # bit2-3=Bypass Free-Cooling, bit4-5=On/Off, bit6-7=Summer/Winter,
    # bit8-9=Serious alarm, bit10-11=Light alarm, bit12-13=High humidity
    do2 = integer(385, signed=False)


class Status(Component):
    """Stato dettagliato dell'unità al momento dell'interrogazione (R/O)."""

    register_space = "holding"

    unit_status = enum(1104, UnitStatusCode)
    mode_status = enum(1110, ModeStatusCode)
    actual_setpoint = gauge(1111, 0.1, unit="°C")

    supply_fan_status = enum(1119, FanStatusCode)
    return_fan_status = enum(1120, FanStatusCode)
    dehum_request = boolean(1121)
    compressor_status = enum(1122, CompressorStatusCode)

    external_damper_modulating_pct = gauge(1127, 0.01, signed=False, unit="%")
    external_damper_status = enum(1128, DamperStatusCode)

    freecooling_heating_request = boolean(1132)
    recirc_damper_status = enum(1134, RecircDamperStatusCode)

    board_clock = uint32(1101, word_order="little", writable=True)
    """Orologio (RTC) della scheda, in secondi dal 2000-01-01, ora locale.
    NON documentato da Sinergia: dedotto da scansione. Scrivibile (da
    verificare sul campo): usato per sincronizzarlo con Home Assistant."""

    active_time_band = integer(1106, signed=False)
    """Fascia oraria attiva (valori di `TimeBandCode`). NON documentato da
    Sinergia: dedotto da scansione (vale 2=Comfort durante la fascia Comfort),
    da confermare a un cambio di fascia."""


class Maintenance(Component):
    """Contatori ore di funzionamento e manutenzione (EVCO PM00-PM04, PM90).

    Valori a 32 bit (word bassa all'indirizzo indicato, word alta al
    successivo), espressi direttamente in ore: il pannello li mostra in
    "ore x10" (es. 906.8 sul display = 9068 h, cfr. esempio del manuale
    Sinergia "450 = 4500 h").
    """

    register_space = "holding"

    supply_fan_hours = uint32(1604, word_order="little", unit="h")
    """PM01 - ore di funzionamento ventilatore mandata."""

    return_fan_hours = uint32(1606, word_order="little", unit="h")
    """PM02 - ore di funzionamento ventilatore ripresa."""

    compressor_hours_limit = uint32(1608, word_order="little", writable=True, unit="h")
    """PM03 - limite ore compressore oltre il quale scatta l'allarme."""

    compressor_hours = uint32(1610, word_order="little", unit="h")
    """PM04 - ore di funzionamento compressore."""

    last_maintenance = uint32(1612, word_order="little")
    """PM90 - data ultima manutenzione, in secondi dal 2000-01-01 (ora locale
    della scheda). 2008-01-01 = mai impostata."""


# --------------------------------------------------------------------------- #
# Writable components
# --------------------------------------------------------------------------- #


class Enables(Component):
    """Flag di abilitazione OBBLIGATORI per il controllo via Modbus/BMS (R/W).

    Dal manuale: "Parametri da impostare obbligatoriamente per rendere
    funzionanti le impostazioni tramite MODBUS, se non viene fatto l'unità
    non terrà conto dei registri chiamati."
    """

    register_space = "holding"

    onoff_by_bms = boolean(1778, writable=True)
    """H02 - deve essere True per poter controllare l'accensione/spegnimento
    scrivendo su Command.onoff_by_supervisor."""

    integ_by_bms = boolean(1869, writable=True)
    """H27 - deve essere True per controllare l'integrazione di calore."""

    dehum_by_bms = boolean(1870, writable=True)
    """H28 - deve essere True per controllare la deumidifica."""

    time_bands_enabled = boolean(1779, writable=True)
    """PH03 - abilita la regolazione a fasce orarie. NON documentato da
    Sinergia: dedotto da scansione + manuale EVCO (segue H01/H02 nel menù
    "Varie", e i registri successivi coincidono con PH04-PH10)."""

    onoff_by_keyboard = boolean(1777, writable=True)
    """H01 - abilita accensione/spegnimento da tastiera locale (default True,
    di solito non serve toccarlo)."""


class Command(Component):
    """Comandi operativi e reset allarmi manuali (R/W)."""

    register_space = "holding"

    onoff_by_supervisor = boolean(1105, writable=True)
    """Accende/spegne l'unità. Richiede Enables.onoff_by_bms = True."""

    integ_request_by_bms = boolean(1140, writable=True)
    """Richiesta integrazione di calore. Richiede Enables.integ_by_bms = True."""

    dehum_request_by_bms = boolean(1141, writable=True)
    """Richiesta deumidifica. Richiede Enables.dehum_by_bms = True."""

    summer_winter_mode = boolean(1583, writable=True)
    """MOdE - Modalità operativa: False=Estate, True=Inverno."""

    priority_display_mode = boolean(1878, writable=True)
    """C11 - Priorità cambio modalità: False=Display/BMS, True=DI (ingresso
    digitale). Va impostato se il comando remoto (pannello) è presente e si
    vuole gestire il cambio stagione da contatto digitale/supervisione."""

    reset_alarm_al02 = boolean(780, writable=True)
    """Reset manuale allarme AL02 (alta umidità) - scrittura a impulso."""

    reset_alarm_al12 = boolean(786, writable=True)
    """Reset manuale allarme AL12 (alta pressione compressore) - impulso."""

    fans_hours_limit = uint32(1602, word_order="little", writable=True, unit="h")
    """M00/PM00 - limite ore di lavoro ventilatori oltre il quale scatta
    l'allarme filtri sporchi (32 bit, in ore; default 20000 h = "2000.0"
    sul pannello)."""


class Setpoints(Component):
    """Setpoint di temperatura/umidità (R/W).

    Utilizzabili solo in presenza del comando remoto, perché le sonde sono
    al suo interno.
    """

    register_space = "holding"

    summer = gauge(1584, 0.1, writable=True, unit="°C")
    """SEtC - default 24.0°C, range -15.0..158.0."""

    winter = gauge(1585, 0.1, writable=True, unit="°C")
    """SEtH - default 20.0°C, range -15.0..158.0."""

    humidity = integer(1586, signed=False, writable=True, unit="%")
    """PU01 - default 55%, range 0..100."""

    dehum_differential = integer(1694, signed=False, writable=True, unit="%")
    """PU07 - differenziale deumidifica, default 10%, range 0..100. Con
    compressore on/off la deumidifica parte sopra PU01 + PU07 e si ferma
    sotto PU01. NON documentato da Sinergia: dedotto dal manuale EVCO c-pro 3
    OEM DE (ordine parametri PU02..PS07, ancorato a S06=1703/S07=1704 e
    A19=1735) e da scansione (vale 10 = default)."""

    freecooling_heating = gauge(1703, 0.1, writable=True, unit="°C")
    """S06 - default 4.0°C, range 0.0..68.0."""

    freecooling_heating_diff = gauge(1704, 0.1, writable=True, unit="°C")
    """S07 - default 2.0°C, range 0.0..36.0."""

    high_humidity_warning = integer(1735, signed=False, writable=True, unit="%")
    """A19 - default 100% (=disabilitato se non presente serranda aria
    esterna), range 0..100."""

    summer_commutation_water = gauge(1633, 0.1, writable=True, unit="°C")
    """C07 - default 30.0°C, range 0.0..158.0."""

    winter_commutation_water = gauge(1634, 0.1, writable=True, unit="°C")
    """C08 - default 20.0°C, range 0.0..158.0."""

    max_time_dehum_by_di_warning = integer(1877, signed=False, writable=True, unit="min")
    """PA58 - default 0, range 0..999."""


class FanSpeeds(Component):
    """Velocità minime/massime ventilatori per modalità, in % (R/W).

    ATTENZIONE dal manuale: i valori vanno scritti/letti con due decimali
    (es. 40% <-> raw 4000): gestito automaticamente dallo scale=0.01 qui
    sotto, quindi si legge/scrive direttamente in %.
    """

    register_space = "holding"

    min_supply_vmc_mode = gauge(1644, 0.01, signed=False, writable=True, unit="%")
    """F07 - default 30%, mandata in modalità VMC."""

    max_supply_vmc_mode = gauge(1645, 0.01, signed=False, writable=True, unit="%")
    """F08 - default 60%, mandata in modalità VMC."""

    min_supply_integration = gauge(1852, 0.01, signed=False, writable=True, unit="%")
    """F27 - default 50%, mandata in integrazione."""

    max_supply_integration = gauge(1646, 0.01, signed=False, writable=True, unit="%")
    """F09 - default 85%, mandata in integrazione."""

    min_supply_dehum = gauge(1853, 0.01, signed=False, writable=True, unit="%")
    """F28 - default 50%, mandata in deumidifica."""

    max_supply_dehum = gauge(1647, 0.01, signed=False, writable=True, unit="%")
    """F10 - default 85%, mandata in deumidifica."""

    min_return = gauge(1854, 0.01, signed=False, writable=True, unit="%")
    """F29 - default 40%, ripresa in qualsiasi modalità."""

    max_return = gauge(1855, 0.01, signed=False, writable=True, unit="%")
    """F30 - default 75%, ripresa in qualsiasi modalità."""


# --------------------------------------------------------------------------- #
# Fasce orarie (NON documentate da Sinergia)
#
# Ricavate incrociando una scansione completa dei registri con il manuale
# EVCO "c-pro 3 OEM DE - Manuale applicativo" (144CP3ODI104): l'ordine dei
# parametri nelle tabelle EVCO coincide con quello dei registri.
# --------------------------------------------------------------------------- #

TIME_BAND_DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TIME_BANDS_PER_DAY = 4
_TIME_BANDS_BASE = 1499


def _time_band_fields() -> dict:
    """Tabella fasce: 7 giorni x 4 fasce, 3 registri per fascia.

    Per ogni fascia: tipo (`TimeBandCode`), poi orario di inizio in secondi
    dalla mezzanotte su 32 bit (word bassa, word alta).
    """
    fields: dict = {
        "__doc__": "Programmazione a fasce orarie e vacanza (R/W).",
        "register_space": "holding",
        "vacation_days": integer(1497, signed=False, unit="d"),
        "vacation_hours": integer(1498, signed=False, unit="h"),
    }
    for d, day in enumerate(TIME_BAND_DAYS):
        for b in range(TIME_BANDS_PER_DAY):
            addr = _TIME_BANDS_BASE + 12 * d + 3 * b
            fields[f"{day}_{b + 1}_type"] = integer(addr, signed=False, writable=True)
            fields[f"{day}_{b + 1}_start"] = uint32(
                addr + 1, word_order="little", writable=True, unit="s"
            )
    return fields


# 58 campi generati: più leggibile che scriverli uno per uno.
TimeBands = type("TimeBands", (Component,), _time_band_fields())


def time_band(bands: TimeBands, day: str, index: int) -> tuple[int | None, int | None]:
    """Ritorna (tipo, secondi dalla mezzanotte) della fascia `index` (1-4)."""
    return getattr(bands, f"{day}_{index}_type"), getattr(bands, f"{day}_{index}_start")


async def async_write_time_band_start(
    bands: TimeBands, day: str, index: int, seconds: int
) -> None:
    """Scrive l'orario di inizio di una fascia, una word alla volta.

    La scheda applica le due word separatamente e satura a 23:59:59 ogni
    valore intermedio oltre le 24 ore: scrivendo 18:00 (hi=0) sopra 20:00
    (hi=1) con la word bassa per prima, il valore intermedio hi=1/lo=64800
    diventa 23:59:59 e il risultato finale è 05:47:43. Si scrive quindi per
    prima la word alta quando scende e la word bassa quando sale, così ogni
    valore intermedio resta valido.
    """
    address = _TIME_BANDS_BASE + 12 * TIME_BAND_DAYS.index(day) + 3 * (index - 1) + 1
    old = getattr(bands, f"{day}_{index}_start") or 0
    lo, hi = seconds & 0xFFFF, seconds >> 16
    unit = bands.modbus_unit
    if hi < old >> 16:
        await unit.write_register(address + 1, hi)
        await unit.write_register(address, lo)
    else:
        await unit.write_register(address, lo)
        await unit.write_register(address + 1, hi)


class Calibrations(Component):
    """Calibrazione (offset) delle sonde, EVCO PM80-PM86 (R/W).

    NON documentato da Sinergia: verificato sul campo impostando M80/M86 dal
    pannello (menù Manutentore -> CAL) e confrontando due scansioni.
    """

    register_space = "holding"

    room_temperature = gauge(1616, 0.1, writable=True, unit="°C")
    """M80 - sonda temperatura ambiente (pannello a muro), -10.0..10.0."""

    outdoor_temperature = gauge(1617, 0.1, writable=True, unit="°C")
    """M81 - sonda temperatura aria esterna, -10.0..10.0."""

    water_temperature = gauge(1618, 0.1, writable=True, unit="°C")
    """M82 - sonda temperatura acqua, -10.0..10.0."""

    exhaust_temperature = gauge(1619, 0.1, writable=True, unit="°C")
    """M83 - sonda temperatura aria espulsa, -10.0..10.0."""

    room_humidity = integer(1622, writable=True, unit="%")
    """M86 - sonda umidità ambiente (pannello a muro), -10..10."""


class TimeBandSetpoints(Component):
    """Setpoint e velocità ventilatori per fascia oraria (R/W)."""

    register_space = "holding"

    comfort_summer = gauge(1587, 0.1, writable=True, unit="°C")
    """SCC - setpoint freddo fascia comfort (default EVCO 24.0)."""

    comfort_winter = gauge(1588, 0.1, writable=True, unit="°C")
    """SCH - setpoint caldo fascia comfort (default EVCO 21.0)."""

    economy_offset_summer = gauge(1589, 0.1, writable=True, unit="°C")
    """OEC - offset freddo fascia economy (default +1.0)."""

    economy_offset_winter = gauge(1590, 0.1, writable=True, unit="°C")
    """OEH - offset caldo fascia economy (default -1.0)."""

    night_offset_summer = gauge(1591, 0.1, writable=True, unit="°C")
    """ONC - offset freddo fascia night (default +2.0)."""

    night_offset_winter = gauge(1592, 0.1, writable=True, unit="°C")
    """ONH - offset caldo fascia night (default -2.0)."""

    supply_fan_comfort = gauge(1595, 0.01, signed=False, writable=True, unit="%")
    """FSC - velocità ventilatore mandata fascia comfort."""

    supply_fan_economy = gauge(1596, 0.01, signed=False, writable=True, unit="%")
    """FSE - velocità ventilatore mandata fascia economy."""

    supply_fan_night = gauge(1597, 0.01, signed=False, writable=True, unit="%")
    """FSN - velocità ventilatore mandata fascia night."""

    return_fan_comfort = gauge(1859, 0.01, signed=False, writable=True, unit="%")
    """FRC - velocità ventilatore ripresa fascia comfort (meno certo dei
    precedenti: non contiguo a FSC/FSE/FSN, dedotto dai valori)."""

    return_fan_economy = gauge(1860, 0.01, signed=False, writable=True, unit="%")
    """FRE - velocità ventilatore ripresa fascia economy (vedi FRC)."""

    return_fan_night = gauge(1861, 0.01, signed=False, writable=True, unit="%")
    """FRN - velocità ventilatore ripresa fascia night (vedi FRC)."""


# --------------------------------------------------------------------------- #
# Device
# --------------------------------------------------------------------------- #


class VmcDevice(Device):
    """Unità VMC Sinergia (elettronica CPRO3OEM-K, HRD/HRD+) su Modbus RTU."""

    #: Nomi dei componenti, nell'ordine consigliato di lettura (usare con
    #: ``device.async_poll(device.COMPONENT_NAMES)``).
    COMPONENT_NAMES: tuple[str, ...] = (
        "probes",
        "outputs",
        "alarms",
        "digital_io",
        "status",
        "maintenance",
        "enables",
        "command",
        "setpoints",
        "fan_speeds",
        "time_bands",
        "time_band_setpoints",
        "calibrations",
    )

    def __init__(self, unit) -> None:  # noqa: ANN001 - ModbusUnit from modbus_connection
        super().__init__(unit)
        self.probes = Probes(unit)
        self.outputs = Outputs(unit)
        self.alarms = Alarms(unit)
        self.digital_io = DigitalIO(unit)
        self.status = Status(unit)
        self.maintenance = Maintenance(unit)
        self.enables = Enables(unit)
        self.command = Command(unit)
        self.setpoints = Setpoints(unit)
        self.fan_speeds = FanSpeeds(unit)
        self.time_bands = TimeBands(unit)
        self.time_band_setpoints = TimeBandSetpoints(unit)
        self.calibrations = Calibrations(unit)
