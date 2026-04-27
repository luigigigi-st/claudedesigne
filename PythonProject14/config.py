"""
config.py — Configurazione centralizzata del progetto torneo.

Importa da qui invece che da prova.py per avere un unico punto di controllo.
"""
from datetime import datetime

from libreriax.DataBase.PS1 import DB
from libreriax.utils.Data import get_localdate_from_input

# ── Limiti età partecipanti ───────────────────────────────────
ETA_MIN: int = 8
ETA_MAX: int = 99

# ── Punteggio massimo per partita (somma p1+p2) ──────────────
PUNTEGGIO_MAX_PARITA: int = 120

# ── Password per operazioni distruttive ──────────────────────
PASSWORD_TORNEI: str = "admin"

# ── Formato date/ora stampa ───────────────────────────────────
FMT_DATA  = "%d/%m/%Y"
FMT_ORA   = "%H:%M"
FMT_FULL  = "%d/%m/%Y %H:%M"


db = DB("Progetto_Torneo_chill")



def print_errore(msg : str = ""):
    if not db.risultato.successo:
        if msg != "":
            print(msg)
        print("errore: " + db.risultato.get_msg())





def proviamo():
    data = get_localdate_from_input(
        "data della partita: ",
        "data non valida, reinserisci: "
    )

    if data < datetime.now().date():
        print("prima")
