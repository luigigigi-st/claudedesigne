"""
utils.py — Utility condivise tra i moduli del progetto torneo.

Funzioni:
  - _chiedi_data        : input interattivo di una data
  - _sanitize           : escaping minimo anti SQL-injection
  - _normalizza_orario  : normalizza TIME dal driver MySQL
  - _normalizza_data    : normalizza DATE dal driver MySQL
  - _partita_futura     : True se la partita non è ancora disputata
  - _format_data_orario : stringa formattata (data_str, ora_str)

NOTA SQL INJECTION:
  _sanitize() offre una protezione minima (escape delle virgolette).
  La soluzione corretta è usare query parametrizzate con %s nel db layer.
  Applica _sanitize() a TUTTI i valori stringa inseriti dall'utente
  nelle query, in attesa di migrare il db layer a prepared statements.
"""

from datetime import date, datetime, time as dt_time, timedelta

from libreriax.console import IO

# Importa il formato dal config se disponibile, altrimenti usa default
try:
    from config import FMT_DATA, FMT_ORA
except ImportError:
    FMT_DATA = "%d/%m/%Y"
    FMT_ORA  = "%H:%M"


# ══════════════════════════════════════════════════════════════
#  INPUT VELOCE — funzioni centralizzate Enter-to-default
# ══════════════════════════════════════════════════════════════

def input_veloce(prompt: str, default_val: str, default_text: str) -> str:
    """Restituisce il default se si preme solo Invio."""
    risposta = input(IO.color(f"{prompt} [INVIO = {default_text}]: ", "yellow")).strip().upper()
    return default_val if risposta == "" else risposta


def yes_or_no_veloce(prompt: str, default: str = "si") -> str:
    """Chiede si/no con default su Invio. default deve essere 'si' o 'no'."""
    default_text = default.upper()
    while True:
        raw = input(IO.color(f"{prompt} (si/no) [INVIO = {default_text}]: ", "yellow")).strip().lower()
        if raw == "":
            return default
        if raw in ("si", "no"):
            return raw
        print(IO.color("Rispondi solo 'si' o 'no': ", "red"))


def input_scelta_veloce(opzioni: list[str], prompt: str, default: str) -> str:
    """Scelta tra opzioni con default su Invio. Le opzioni devono essere stringhe lowercase."""
    opzioni_str = " / ".join(f"'{o}'" for o in opzioni)
    while True:
        raw = input(IO.color(f"{prompt} [{opzioni_str}, INVIO = '{default}']: ", "yellow")).strip().lower()
        if raw == "":
            return default
        if raw in opzioni:
            return raw
        print(IO.color(f"Rispondi solo {opzioni_str}: ", "red"))


# ══════════════════════════════════════════════════════════════
#  INPUT DATA
# ══════════════════════════════════════════════════════════════

def chiedi_data(label: str) -> date:
    """
    Input interattivo di una data (giorno/mese/anno su righe separate).
    Unica definizione condivisa — NON ridefinire nei singoli moduli.
    """
    print(IO.color(label, "yellow"))
    while True:
        try:
            g = int(input(IO.color("  giorno: ", "yellow")).strip())
            m = int(input(IO.color("  mese:   ", "yellow")).strip())
            a = int(input(IO.color("  anno:   ", "yellow")).strip())
            return date(a, m, g)
        except (ValueError, TypeError):
            print(IO.color("  Data non valida. Reinserisci.", "red"))


# ══════════════════════════════════════════════════════════════
#  SQL SANITIZATION
# ══════════════════════════════════════════════════════════════

def s(val) -> str:
    """
    Escaping minimo per stringhe inserite in query SQL via f-string.

    Protegge dalle injection più comuni (apostrofi, backslash).
    NON è un sostituto dei prepared statements — è una misura
    temporanea in attesa di migrare il db layer a query parametrizzate.

    Uso:
        db.execute_select(f"... WHERE nome = '{s(nome_utente)}' ...")
    """
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace("'", "\\'")


# ══════════════════════════════════════════════════════════════
#  NORMALIZZAZIONE DATA / ORARIO DAL DRIVER MYSQL
# ══════════════════════════════════════════════════════════════

def normalizza_orario(orario_r) -> dt_time:
    """
    Converte in datetime.time qualunque tipo restituito dal driver MySQL:
      - datetime.time      → passthrough
      - datetime.timedelta → secondi totali → time (mysqlclient/PyMySQL)
      - str "HH:MM:SS" o "HH:MM" → parsing manuale

    Solleva ValueError se il valore non è convertibile.
    """
    if isinstance(orario_r, dt_time):
        return orario_r
    if isinstance(orario_r, timedelta):
        total = int(orario_r.total_seconds())
        if total < 0:
            raise ValueError(f"Orario negativo non valido: {orario_r}")
        return dt_time(total // 3600, (total % 3600) // 60, total % 60)
    parti = str(orario_r).strip().split(":")
    if len(parti) < 2:
        raise ValueError(f"Formato orario non riconosciuto: {orario_r!r}")
    return dt_time(int(parti[0]), int(parti[1]), int(parti[2]) if len(parti) > 2 else 0)


def normalizza_data(data_r) -> date:
    """
    Converte in datetime.date qualunque tipo restituito dal driver MySQL:
      - datetime → estrae .date()
      - date     → passthrough
      - str "YYYY-MM-DD" → parsing
    """
    if isinstance(data_r, datetime):
        return data_r.date()
    if isinstance(data_r, date):
        return data_r
    return datetime.strptime(str(data_r).strip(), "%Y-%m-%d").date()


def partita_futura(data_r, orario_r) -> bool:
    """
    Restituisce True se la partita è schedulata nel futuro rispetto a ora.

    Gestisce tutti i tipi che MySQL può restituire per DATE e TIME.
    In caso di errore di parsing restituisce False (comportamento sicuro:
    permette l'inserimento piuttosto che bloccare tutto silenziosamente).
    """
    try:
        d = normalizza_data(data_r)
        t = normalizza_orario(orario_r)
        return datetime.combine(d, t) > datetime.now()
    except Exception:
        return False


def format_data_orario(data_r, orario_r) -> tuple[str, str]:
    """
    Restituisce (data_str, ora_str) formattate per la stampa.
    Tollerante ai tipi: usa le funzioni normalizza_* e in caso di
    errore ricade su str() grezzo.
    """
    try:
        data_str = normalizza_data(data_r).strftime(FMT_DATA)
    except Exception:
        data_str = str(data_r)
    try:
        ora_str = normalizza_orario(orario_r).strftime(FMT_ORA)
    except Exception:
        ora_str = str(orario_r)
    return data_str, ora_str
