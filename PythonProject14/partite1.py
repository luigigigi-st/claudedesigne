"""
partite1.py - Gestione tabelloni e calendario [VERSIONE CHILL]
Modulo di gestione dello stato d'avanzamento dei tornei:
Gironi, refertazione partite, classifiche, tabellone e finali.
"""

import random
from datetime import datetime
from collections import defaultdict

from libreriax.console import IO
from config import db, print_errore
from utils import yes_or_no_veloce, input_scelta_veloce

from tornei import input_and_check_torneo
from partecipanti import _conta_singoli_in_attesa

PUNTEGGIO_TOTALE_PARTITA_DEFAULT = 120
try:
    from config import PUNTEGGIO_MAX_PARITA as punteggio_totale_partita
except ImportError:
    punteggio_totale_partita = PUNTEGGIO_TOTALE_PARTITA_DEFAULT

# ══════════════════════════════════════════════════════════════
#  COSTANTI E DIZIONARI
# ══════════════════════════════════════════════════════════════

_LABEL_FASE = {
    "girone_A": "Girone A",
    "girone_B": "Girone B",
    "semifinale_A": "Semifinale  1-4  posto",
    "semifinale_B": "Semifinale  5-8  posto",
    "semifinale_C": "Semifinale  9-12 posto",
    "finale_1_2":   "Finale  1 - 2  posto",
    "finale_3_4":   "Finale  3 - 4  posto",
    "finale_5_6":   "Finale  5 - 6  posto",
    "finale_7_8":   "Finale  7 - 8  posto",
    "finale_9_10":  "Finale  9 - 10 posto",
    "finale_11_12": "Finale 11 - 12 posto",
    "finale_diretta_5_6":  "Finale diretta  5 - 6  posto",
    "finale_diretta_9_10": "Finale diretta  9 - 10 posto",
}

_SEMI_A_FINALI = {
    "semifinale_A": ("finale_1_2", "finale_3_4"),
    "semifinale_B": ("finale_5_6", "finale_7_8"),
    "semifinale_C": ("finale_9_10", "finale_11_12"),
}

_FINALE_POSIZIONI = {
    "finale_1_2": (1, 2), "finale_3_4": (3, 4),
    "finale_5_6": (5, 6), "finale_7_8": (7, 8),
    "finale_9_10": (9, 10), "finale_11_12": (11, 12),
    "finale_diretta_5_6": (5, 6), "finale_diretta_9_10": (9, 10),
}

FASE_ISCRIZIONI  = "iscrizioni_aperte"
FASE_ATTESA_AVVIO = "attesa"
FASE_GIRONI      = "gironi"
FASE_PLAYOFF     = "playoff"
FASE_CONCLUSO    = "concluso"

_MEDAGLIE_GIRONI = {1: "🥇", 2: "🥈", 3: "🥉"}
_MEDAGLIE_FINALI = {1: "🏆", 2: "🥈", 3: "🥉"}


# ══════════════════════════════════════════════════════════════
#  MENU PRINCIPALE E FLUSSO DI LAVORO
# ══════════════════════════════════════════════════════════════

def svolgi_partite():
    print(IO.color("\n" + "═" * 58, "cyan"))
    print(IO.color("  🎴 PANNELLO GESTIONE PARTITE E TABELLONI", "cyan"))
    print(IO.color("═" * 58, "cyan"))

    while True:
        print(IO.color("\nScegli il torneo su cui lavorare.", "yellow"))
        lista = input_and_check_torneo()
        if lista is None:
            print(IO.color("  Nessun torneo selezionato. Torno al menu.", "yellow"))
            return
        _sessione_torneo(lista[0])
        if yes_or_no_veloce("\nVuoi lavorare su un altro torneo?", default="no") == "no":
            break


def _sessione_torneo(torneo: dict):
    nome = torneo["nome"]
    is_singolo = (torneo["singolo_doppio"] == 1)

    while True:
        stato = _get_stato(nome)
        if stato is None:
            print(IO.color("Impossibile recuperare lo stato del torneo. Uscita dalla sessione.", "red"))
            break
        fase = _calcola_fase(stato)
        _stampa_dashboard(nome, is_singolo, stato, fase)

        voci = _costruisci_menu(stato, fase)
        valide = {v[0] for v in voci if v[0] != "-"}

        for chiave, desc in voci:
            if chiave == "-":
                print(f"  {IO.color('─', 'white')}  {desc}")
            else:
                colore = "red" if chiave == "U" else "green"
                hint = f"  {IO.color('[INVIO]', 'yellow')}" if chiave == "U" else ""
                print(f"  {IO.color(chiave, colore)}. {desc}{hint}")
        print()

        risp = input(IO.color("Scelta: ", "yellow")).upper().strip()
        if risp == "":
            break
        if risp not in valide:
            print(IO.color("Scelta non valida.", "red"))
            continue

        if risp == "U":
            break
        elif risp == "G":
            _assegna_gironi(nome, is_singolo)
            _pausa()
        elif risp == "K":
            _genera_calendario_gironi(nome, is_singolo)
            _pausa()
        elif risp == "R":
            _inserisci_risultati_pendenti(nome, is_singolo)
            _pausa()
        elif risp == "X":
            _correggi_risultato(nome, is_singolo)
            _pausa()
        elif risp == "C":
            mostra_classifica_gironi(nome, is_singolo)
            _pausa()
        elif risp == "P":
            _genera_tabellone_playoff(nome, is_singolo)
            _pausa()
        elif risp == "F":
            classifica_finale(nome, is_singolo)
            _pausa()
        elif risp == "A":
            _pubblica_calendario(nome, is_singolo)
            _pausa()
        elif risp == "Z":
            _reset_torneo_gironi(nome)
            _pausa()


# ══════════════════════════════════════════════════════════════
#  ANALISI STATO TORNEO
# ══════════════════════════════════════════════════════════════

def _get_stato(nome: str) -> dict | None:
    r = db.execute_select(
        "SELECT numero, fase FROM turno WHERE nome_torneo=%s ORDER BY numero DESC LIMIT 1",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero stato: {db.risultato.get_msg()}", "red"))
        return None
    turno_corrente = r[0]["numero"] if r else None
    fase_corrente  = r[0]["fase"]   if r else None

    r2 = db.execute_select("""
        SELECT COUNT(*) AS n
        FROM   partita_squadra ps
        JOIN   partita par ON par.id_partita = ps.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo = %s AND ps.punteggio IS NULL
    """, params=(nome,))
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero partite in sospeso: {db.risultato.get_msg()}", "red"))
        return None
    pending = (r2[0]["n"] // 2) if r2 else 0

    r_ins = db.execute_select("""
        SELECT COUNT(*) AS n
        FROM   partita_squadra ps
        JOIN   partita par ON par.id_partita = ps.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo = %s AND ps.punteggio IS NOT NULL
    """, params=(nome,))
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero risultati inseriti: {db.risultato.get_msg()}", "red"))
        return None
    risultati_inseriti = (r_ins[0]["n"] // 2) if r_ins else 0

    r3 = db.execute_select(
        "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone IS NOT NULL",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero gironi assegnati: {db.risultato.get_msg()}", "red"))
        return None
    gironi_assegnati = bool(r3[0]["n"]) if r3 else False

    r_gb = db.execute_select(
        "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone='B'",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero girone B: {db.risultato.get_msg()}", "red"))
        return None
    is_single_group = not bool(r_gb[0]["n"]) if r_gb else True

    r5 = db.execute_select(
        "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase IN ('girone_A','girone_B')",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero turni girone: {db.risultato.get_msg()}", "red"))
        return None
    ha_turni_girone = bool(r5[0]["n"]) if r5 else False

    r4 = db.execute_select("""
        SELECT COUNT(*) AS n
        FROM   partita_squadra ps
        JOIN   partita par ON par.id_partita = ps.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo = %s
          AND  t.fase IN ('girone_A','girone_B')
          AND  ps.punteggio IS NULL
    """, params=(nome,))
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero pending gironi: {db.risultato.get_msg()}", "red"))
        return None
    pending_gironi = (r4[0]["n"] // 2) if r4 else 0
    gironi_completi = ha_turni_girone and pending_gironi == 0

    r6 = db.execute_select(
        "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase LIKE %s",
        params=(nome, 'semifinale%')
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero playoff avviato: {db.risultato.get_msg()}", "red"))
        return None
    playoff_avviato = bool(r6[0]["n"]) if r6 else False

    return {
        "turno_corrente":    turno_corrente,
        "fase_corrente":     fase_corrente,
        "pending":           pending,
        "risultati_inseriti": risultati_inseriti,
        "gironi_assegnati":  gironi_assegnati,
        "gironi_completi":   gironi_completi,
        "playoff_avviato":   playoff_avviato,
        "is_single_group":   is_single_group,
    }


def _calcola_fase(stato: dict) -> str:
    if stato["fase_corrente"] is None:
        return FASE_ATTESA_AVVIO if stato["gironi_assegnati"] else FASE_ISCRIZIONI

    fc = stato["fase_corrente"]
    if "finale" in fc:
        return FASE_CONCLUSO if stato["pending"] == 0 else FASE_PLAYOFF
    if "semifinale" in fc:
        return FASE_PLAYOFF
    if stato["gironi_completi"]:
        if stato.get("is_single_group"):
            return FASE_CONCLUSO
        if stato["playoff_avviato"]:
            return FASE_PLAYOFF
    return FASE_GIRONI


def _stampa_dashboard(nome: str, is_singolo: bool, stato: dict, fase: str):
    _ICONE = {
        FASE_ISCRIZIONI:   ("*", "cyan",   "Iscrizioni APERTE"),
        FASE_ATTESA_AVVIO: ("~", "yellow", "Fase GIRONI - attesa di configurazione"),
        FASE_GIRONI:       ("x", "cyan",   "Fase GIRONI in corso"),
        FASE_PLAYOFF:      ("!", "green",  "Fase PLAYOFF in corso"),
        FASE_CONCLUSO:     ("v", "white",  "Torneo CONCLUSO"),
    }
    icona, colore, label = _ICONE.get(fase, ("?", "white", fase))
    entita = "giocatori" if is_singolo else "coppie"

    pending_str = (
        IO.color(f"{stato['pending']} in sospeso", "yellow")
        if stato["pending"] > 0
        else IO.color("tutti inseriti e giocati", "green")
    )

    info_g = []
    for g in ("A", "B"):
        r = db.execute_select(
            "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone=%s",
            params=(nome, g)
        )
        n = r[0]["n"] if (r and db.risultato.successo) else 0
        if n:
            info_g.append(f"Girone {g}: {IO.color(str(n), 'cyan')} {entita}")

    print("\n" + IO.color("═" * 64, "cyan"))
    print(IO.color(f"  Torneo : {nome}", "cyan"))
    print(IO.color(f"  Fase   : ", "cyan") + IO.color(f"{icona} {label}", colore))
    if info_g:
        print(IO.color("  Gironi : " + "  |  ".join(info_g), "white"))
    fc = stato.get("fase_corrente")
    print(IO.color(
        f"  Turno  : {IO.color(str(stato['turno_corrente'] or '---'), 'white')}"
        f"  [{_LABEL_FASE.get(fc, fc or '---')}]"
        f"  |  Risultati: ",
        "white",
    ) + pending_str)
    print(IO.color("═" * 64, "cyan"))
    print()


def _costruisci_menu(s: dict, fase: str) -> list:
    voci = []

    if fase == FASE_ISCRIZIONI:
        voci.append(("G", "Assegna le squadre ai gironi  [passo 1]"))

    elif fase == FASE_ATTESA_AVVIO:
        if not s["gironi_assegnati"]:
            voci.append(("G", "Assegna le squadre ai gironi  [passo 1]"))
        else:
            if s["pending"] > 0:
                voci.append(("-", IO.color(
                    f"  ⚠ Per generare il calendario, inserisci i risultati passati. ({s['pending']} partite in sospeso)",
                    "red")))
            else:
                voci.append(("K", IO.color("Genera il calendario dei gironi  [passo 2]", "green")))
            voci.append(("G", "Riassegna i gironi"))

    elif fase == FASE_GIRONI:
        if s["pending"] > 0:
            voci.append(("R", "Inserisci risultati in sospeso  "
                         + IO.color(f"[{s['pending']} partite]", "yellow")))
        else:
            voci.append(("-", IO.color("Tutti i risultati inseriti e giocati.", "green")))

        if s["risultati_inseriti"] > 0:
            voci.append(("X", "Correggi un risultato gia inserito"))

        if s["gironi_completi"] and not s["playoff_avviato"]:
            if s["pending"] > 0:
                voci.append(("-", IO.color(
                    f"  ⚠ Playoff bloccato: completa i risultati. ({s['pending']} partite in sospeso)",
                    "red")))
            else:
                voci.append(("P", IO.color("Genera tabellone PLAYOFF", "green")))

        voci.append(("C", "Classifica gironi"))
        voci.append(("A", "Visualizza calendario / storico partite"))

    elif fase == FASE_PLAYOFF:
        if s["pending"] > 0:
            voci.append(("R", "Inserisci risultati playoff  "
                         + IO.color(f"[{s['pending']} partite]", "yellow")))
        else:
            voci.append(("-", IO.color("Tutti i risultati inseriti e giocati.", "green")))
        if s["risultati_inseriti"] > 0:
            voci.append(("X", "Correggi un risultato gia inserito"))
        voci.append(("C", "Classifica gironi"))
        voci.append(("A", "Visualizza calendario / storico partite"))

    elif fase == FASE_CONCLUSO:
        voci.append(("F", IO.color("Classifica finale del torneo", "green")))
        if s["risultati_inseriti"] > 0:
            voci.append(("X", "Correggi un risultato gia inserito"))
        if not s.get("is_single_group"):
            voci.append(("C", "Classifica gironi"))
        voci.append(("A", "Visualizza calendario / storico partite"))

    if fase in (FASE_ATTESA_AVVIO, FASE_GIRONI, FASE_CONCLUSO) and s["gironi_assegnati"]:
        voci.append(("Z", IO.color(
            "Reset totale gironi e partite  [mantiene gli iscritti]", "red"
        )))

    voci.append(("U", "Esci"))
    return voci


# ══════════════════════════════════════════════════════════════
#  RESET TOTALE GIRONI
# ══════════════════════════════════════════════════════════════

def _reset_torneo_gironi(nome: str):
    """Cancella turni, partite e girone di tutte le squadre. Mantiene gli iscritti."""
    print(IO.color("\n" + "═" * 58, "red"))
    print(IO.color("  ⚠  RESET TOTALE GIRONI — Operazione irreversibile!", "red"))
    print(IO.color("═" * 58, "red"))
    print(IO.color(
        "  Verranno eliminati:\n"
        "    • Tutti i turni e le partite del torneo\n"
        "    • Tutti i risultati inseriti\n"
        "  Gli iscritti al torneo NON verranno eliminati.\n",
        "red",
    ))

    conferma = input(IO.color(
        "  Procedere? (s/N) [INVIO = NO]: ", "red"
    )).strip().lower()

    if conferma != "s":
        print(IO.color("  Reset annullato.", "yellow"))
        return

    turni = db.execute_select(
        "SELECT id_turno FROM turno WHERE nome_torneo = %s", params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"  Errore recupero turni: {db.risultato.get_msg()}", "red"))
        return

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"  Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    try:
        if turni:
            ids_str = ", ".join(str(r["id_turno"]) for r in turni)
            db.execute_alt(f"""
                DELETE ps FROM partita_squadra ps
                JOIN partita par ON par.id_partita = ps.id_partita
                WHERE par.id_turno IN ({ids_str})
            """)
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            db.execute_alt(f"DELETE FROM partita WHERE id_turno IN ({ids_str})")
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            db.execute_alt(f"DELETE FROM turno WHERE id_turno IN ({ids_str})")
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

        db.execute_alt(
            "UPDATE squadra SET girone = NULL WHERE nome_torneo = %s", params=(nome,)
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        print(IO.color(
            f"\n  ✓ Reset completato. Tutti i turni, partite e gironi eliminati.\n"
            f"    Il torneo è tornato alla fase ISCRIZIONI APERTE.",
            "green",
        ))
    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"  Errore durante il reset: {e}. Rollback eseguito.", "red"))


# ══════════════════════════════════════════════════════════════
#  BLOCCO SINGOLI SPAIATI
# ══════════════════════════════════════════════════════════════

def _controlla_singoli_prima_di_avviare(nome_torneo: str, is_singolo: bool) -> bool:
    if is_singolo:
        return True

    n_singoli = _conta_singoli_in_attesa(nome_torneo)
    if n_singoli == 0:
        return True

    print(IO.color(
        f"\n  Ci sono {IO.color(str(n_singoli), 'yellow')} giocatore/i "
        "iscritti singolarmente e non ancora accoppiati.",
        "yellow",
    ))

    singoli = db.execute_select("""
        SELECT p.nome, p.cognome
        FROM   squadra sq
        JOIN   partecipante p ON p.id_squadra = sq.id_squadra
        WHERE  sq.nome_torneo = %s
          AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = sq.id_squadra) = 1
        ORDER BY p.cognome, p.nome
    """, params=(nome_torneo,))

    if db.risultato.successo and singoli:
        for g in singoli:
            print(IO.color(f"    {g['nome']} {g['cognome']}", "yellow"))

    print(IO.color(
        "\n  Non è possibile avviare i gironi finché esistono singoli spaiati.\n"
        "  Torna nel modulo Partecipanti -> 'Accoppia singoli' per gestirli.",
        "red",
    ))
    return False


# ══════════════════════════════════════════════════════════════
#  MOTORE SORTEGGI GIRONI
# ══════════════════════════════════════════════════════════════

def _assegna_gironi(nome_torneo: str, is_singolo: bool = False):
    print(IO.color("\n-- Assegnazione Gironi --", "cyan"))

    if not _controlla_singoli_prima_di_avviare(nome_torneo, is_singolo):
        return

    if is_singolo:
        query_squadre = """
            SELECT sq.id_squadra,
                   CONCAT(p.nome, ' ', p.cognome) AS display
            FROM   squadra sq
            JOIN   partecipante p ON p.id_squadra = sq.id_squadra
            WHERE  sq.nome_torneo = %s
              AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = sq.id_squadra) = 1
            ORDER BY p.cognome, p.nome
        """
    else:
        query_squadre = """
            SELECT sq.id_squadra, sq.nome AS display
            FROM   squadra sq
            WHERE  sq.nome_torneo = %s
              AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = sq.id_squadra) = 2
            ORDER BY sq.id_squadra
        """

    squadre = db.execute_select(query_squadre, params=(nome_torneo,))
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero squadre: {db.risultato.get_msg()}", "red"))
        return
    if not squadre:
        entita = "giocatori" if is_singolo else "coppie complete"
        print(IO.color(f"  Nessun/a {entita} trovato/a.", "red"))
        return

    n = len(squadre)
    if n < 2:
        print(IO.color(f"  Servono almeno 2 squadre (trovate: {n}).", "red"))
        return
    if n > 12:
        print(IO.color(f"  Attenzione: {n} squadre > 12. Verranno considerate solo le prime 12.", "yellow"))
        squadre = squadre[:12]
        n = 12

    entita_label = "giocatori" if is_singolo else "coppie"
    print(IO.color(f"\n  {n} {entita_label} disponibili:\n", "white"))
    for idx, sq in enumerate(squadre, 1):
        print(IO.color(f"    {idx:>2}.  {sq['display']}", "white"))

    # Mostra gironi attuali se già assegnati
    r_attuali = db.execute_select("""
        SELECT sq.id_squadra, sq.girone, sq.nome AS display
        FROM   squadra sq
        WHERE  sq.nome_torneo = %s AND sq.girone IS NOT NULL
        ORDER BY sq.girone, sq.id_squadra
    """, params=(nome_torneo,))
    if db.risultato.successo and r_attuali:
        print(IO.color("\n  ─── Assegnazione attuale ───", "yellow"))
        for g in ("A", "B"):
            gruppo = [r for r in r_attuali if r["girone"] == g]
            if gruppo:
                print(IO.color(f"  Girone {g}:", "cyan"))
                for r in gruppo:
                    print(IO.color(f"    • {r['display']}", "white"))

    # Con meno di 6 squadre non si formano 2 gironi distinti.
    # Tutte le squadre vanno in un unico Girone A; il torneo si conclude al girone.
    if n < 6:
        print(IO.color(
            f"\n  Con {n} squadre (minimo 6 per i gironi) tutte saranno assegnate\n"
            "  al Girone A (girone unico). Il torneo si conclude al termine del girone,\n"
            "  senza playoff: il vincitore è il primo in classifica.",
            "yellow",
        ))
        girone_A = list(squadre)
        girone_B = []
    else:
        metodo = input_scelta_veloce(
            ["casuale", "manuale", "annulla"],
            "\nAssegnazione gironi?",
            default="casuale",
        )
        if metodo == "annulla":
            print(IO.color("  Assegnazione annullata.", "yellow"))
            return

        if metodo == "casuale":
            pool = list(squadre)
            random.shuffle(pool)
            meta = (n + 1) // 2
            girone_A = pool[:meta]
            girone_B = pool[meta:]
        else:
            girone_A = []
            ids_rimasti_idx = set(range(n))
            print(IO.color(
                f"\n  Inserisci i numeri per il Girone A "
                f"(almeno 2, massimo {min(6, n - 1)}). INVIO vuoto per terminare.",
                "yellow",
            ))
            while True:
                raw = input(IO.color("  Numero (INVIO = fine): ", "yellow")).strip()
                if not raw:
                    if len(girone_A) >= 2:
                        break
                    print(IO.color("  Serve almeno 2 squadre nel Girone A.", "red"))
                    continue
                try:
                    idx = int(raw) - 1
                    if idx not in ids_rimasti_idx:
                        raise ValueError
                    if len(girone_A) >= 6:
                        print(IO.color("  Girone A è al massimo (6 squadre).", "yellow"))
                        continue
                    girone_A.append(squadre[idx])
                    ids_rimasti_idx.remove(idx)
                    print(IO.color(f"    -> {squadre[idx]['display']} -> Girone A", "green"))
                except (ValueError, IndexError):
                    print(IO.color("  Numero non valido o già assegnato.", "red"))
            girone_B = [squadre[i] for i in ids_rimasti_idx]

    print(IO.color("\n  ─── Girone A ───", "cyan"))
    for sq in girone_A:
        print(IO.color(f"    {sq['display']}", "white"))
    if girone_B:
        print(IO.color("  ─── Girone B ───", "cyan"))
        for sq in girone_B:
            print(IO.color(f"    {sq['display']}", "white"))

    if yes_or_no_veloce("\nConfermi questa assegnazione?", default="si") == "no":
        print(IO.color("Assegnazione annullata.", "yellow"))
        return

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    try:
        db.execute_alt("UPDATE squadra SET girone = NULL WHERE nome_torneo = %s", params=(nome_torneo,))
        if not db.risultato.successo:
            raise Exception(f"Errore pulizia gironi: {db.risultato.get_msg()}")

        for sq in girone_A:
            db.execute_alt("UPDATE squadra SET girone='A' WHERE id_squadra=%s", params=(sq['id_squadra'],))
            if not db.risultato.successo:
                raise Exception(f"Errore assegnazione Girone A (id {sq['id_squadra']}): {db.risultato.get_msg()}")

        for sq in girone_B:
            db.execute_alt("UPDATE squadra SET girone='B' WHERE id_squadra=%s", params=(sq['id_squadra'],))
            if not db.risultato.successo:
                raise Exception(f"Errore assegnazione Girone B (id {sq['id_squadra']}): {db.risultato.get_msg()}")

        db.commit_transaction()
        if db.risultato.successo:
            print(IO.color("\nGironi assegnati! Ora puoi generare il calendario.", "green"))
        else:
            print(IO.color(f"Errore durante il commit: {db.risultato.get_msg()}", "red"))

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\nErrore durante il salvataggio dei gironi: {e}. Rollback eseguito.", "red"))


# ══════════════════════════════════════════════════════════════
#  CALENDARIO — ROUND ROBIN
# ══════════════════════════════════════════════════════════════

def _round_robin(ids: list) -> list:
    pool = list(ids)
    if len(pool) % 2:
        pool.append(None)
    n = len(pool)
    rounds = []
    for _ in range(n - 1):
        coppie = [
            (pool[i], pool[n - 1 - i])
            for i in range(n // 2)
            if pool[i] is not None and pool[n - 1 - i] is not None
        ]
        rounds.append(coppie)
        if n > 1:
            pool = [pool[0]] + [pool[-1]] + pool[1:-1]
    return rounds


def _genera_calendario_gironi(nome: str, is_singolo: bool = False):
    print(IO.color("\n-- Generazione Calendario Gironi --", "cyan"))

    if not _controlla_singoli_prima_di_avviare(nome, is_singolo):
        return

    r_exist = db.execute_select(
        "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase IN ('girone_A','girone_B')",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel controllo calendario esistente: {db.risultato.get_msg()}", "red"))
        return

    if r_exist and r_exist[0]["n"] > 0:
        print(IO.color(
            f"\n  Attenzione: esiste già un calendario con {r_exist[0]['n']} turni per i gironi.",
            "yellow",
        ))
        print(IO.color(
            "  Procedendo, i turni e le partite esistenti verranno eliminati definitivamente.",
            "red",
        ))
        if yes_or_no_veloce("  Sei sicuro di voler sovrascrivere?", default="no") == "no":
            print(IO.color("  Generazione annullata.", "yellow"))
            return

        db.start_transaction()
        if not db.risultato.successo:
            print(IO.color(f"Errore avvio transazione per pulizia: {db.risultato.get_msg()}", "red"))
            return
        try:
            db.execute_alt(
                "DELETE FROM turno WHERE nome_torneo=%s AND fase IN ('girone_A','girone_B')",
                params=(nome,)
            )
            if not db.risultato.successo:
                raise Exception(f"Errore eliminazione turni: {db.risultato.get_msg()}")
            db.commit_transaction()
            print(IO.color("  Calendario precedente eliminato.", "cyan"))
        except Exception as e:
            db.rollback_transaction()
            print(IO.color(f"  Errore durante la pulizia: {e}. Rollback eseguito.", "red"))
            return

    ids_A = _get_ids_girone(nome, "A")
    ids_B = _get_ids_girone(nome, "B")

    if ids_A is None or ids_B is None:
        print(IO.color("Errore nel recupero degli ID dei gironi. Annullamento.", "red"))
        return
    if not ids_A:
        print(IO.color("  Girone A non configurato o vuoto. Assegna prima le squadre.", "red"))
        return

    rounds_A = _round_robin(ids_A)
    rounds_B = _round_robin(ids_B) if ids_B else []
    n_round   = max(len(rounds_A), len(rounds_B)) if rounds_B else len(rounds_A)
    n_partite = sum(len(r) for r in rounds_A) + sum(len(r) for r in rounds_B)

    info_b = f"Girone B: {len(ids_B)} squadre  |  " if ids_B else "Girone B: (assente)  |  "
    print(IO.color(
        f"\n  Girone A: {len(ids_A)} squadre  |  {info_b}"
        f"{n_round} round  |  {n_partite} partite totali",
        "white",
    ))

    luogo = input(IO.color("\nLuogo delle partite (INVIO = 'Sala Principale'): ", "yellow")).strip() or "Sala Principale"

    if yes_or_no_veloce("Confermi e generi il calendario?", default="si") == "no":
        print(IO.color("Generazione annullata.", "yellow"))
        return

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    partite_ok = 0
    num_turno = _prossimo_numero_turno(nome)
    if num_turno is None:
        db.rollback_transaction()
        return

    try:
        for round_idx in range(n_round):
            if round_idx < len(rounds_A) and rounds_A[round_idx]:
                id_t = db.insert("turno", ["numero", "nome_torneo", "fase"], [num_turno, nome, "girone_A"])
                if not db.risultato.successo:
                    raise Exception(f"Errore creazione turno girone A: {db.risultato.get_msg()}")
                for id1, id2 in rounds_A[round_idx]:
                    if not _crea_partita(id_t, luogo, id1, id2):
                        raise Exception(f"Errore creazione partita {id1} vs {id2}")
                    partite_ok += 1
                num_turno += 1

            if rounds_B and round_idx < len(rounds_B) and rounds_B[round_idx]:
                id_t = db.insert("turno", ["numero", "nome_torneo", "fase"], [num_turno, nome, "girone_B"])
                if not db.risultato.successo:
                    raise Exception(f"Errore creazione turno girone B: {db.risultato.get_msg()}")
                for id1, id2 in rounds_B[round_idx]:
                    if not _crea_partita(id_t, luogo, id1, id2):
                        raise Exception(f"Errore creazione partita {id1} vs {id2}")
                    partite_ok += 1
                num_turno += 1

        db.commit_transaction()
        if db.risultato.successo:
            print(IO.color(f"\nCalendario generato! {partite_ok} partite schedulate.", "green"))
        else:
            print(IO.color(f"Errore durante il commit: {db.risultato.get_msg()}", "red"))

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\nErrore durante la generazione del calendario: {e}. Rollback eseguito.", "red"))


def _crea_partita(id_turno: int, luogo: str, id1: int, id2: int) -> bool:
    id_p = db.insert("partita", ["id_turno", "luogo"], [id_turno, luogo])
    if not db.risultato.successo:
        print(IO.color(f"  Errore creazione partita: {db.risultato.get_msg()}", "red"))
        return False
    return _collega(id_p, id1) and _collega(id_p, id2)


def _collega(id_partita: int, id_squadra: int) -> bool:
    db.insert("partita_squadra", ["id_partita", "id_squadra"], [id_partita, id_squadra])
    if not db.risultato.successo:
        print(IO.color(
            f"  Errore collegamento squadra {id_squadra} alla partita {id_partita}: {db.risultato.get_msg()}", "red"
        ))
        return False
    return True


def _prossimo_numero_turno(nome: str) -> int | None:
    r = db.select_as_dict(
        "turno",
        colonne=["COALESCE(MAX(numero), 0) AS ult"],
        condizione="nome_torneo = %s",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore nel recuperare il prossimo numero di turno: {db.risultato.get_msg()}", "red"))
        return None
    return r[0]["ult"] + 1


# ══════════════════════════════════════════════════════════════
#  CLASSIFICA GIRONI CON SPAREGGI
# ══════════════════════════════════════════════════════════════

def _get_ids_girone(nome_torneo: str, girone: str) -> list | None:
    r = db.execute_select(
        "SELECT id_squadra FROM squadra WHERE nome_torneo=%s AND girone=%s",
        params=(nome_torneo, girone)
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero ID squadre per girone '{girone}': {db.risultato.get_msg()}", "red"))
        return None
    return [row["id_squadra"] for row in r] if r else []


def _conta_squadre_girone(nome_torneo: str, lettera: str) -> int:
    r = db.execute_select(
        "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone=%s",
        params=(nome_torneo, lettera),
    )
    if not db.risultato.successo or not r:
        return 0
    return r[0]["n"]


def _label_fase_dinamica(nome_torneo: str, fase: str) -> str:
    if fase in ("girone_A", "girone_B"):
        lettera = fase[-1]
        if _conta_squadre_girone(nome_torneo, lettera) == 2:
            return f"Qualificazione Gruppo {lettera}"
    return _LABEL_FASE.get(fase, fase)


def _classifica_girone(nome_torneo: str, girone: str) -> list | None:
    ids = _get_ids_girone(nome_torneo, girone)
    if ids is None:
        return None
    if not ids:
        return []

    ids_str = ", ".join(str(i) for i in ids)
    partite = db.execute_select(f"""
        SELECT ps1.id_squadra AS id1, ps1.punteggio AS p1,
               ps2.id_squadra AS id2, ps2.punteggio AS p2
        FROM   partita_squadra ps1
        JOIN   partita_squadra ps2
               ON  ps2.id_partita  = ps1.id_partita
               AND ps2.id_squadra  > ps1.id_squadra
        JOIN   partita par ON par.id_partita = ps1.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo = %s
          AND  t.fase        = %s
          AND  ps1.id_squadra IN ({ids_str})
    """, params=(nome_torneo, f'girone_{girone}'))

    if not db.risultato.successo:
        print(IO.color(f"Errore DB classifica girone {girone}: {db.risultato.get_msg()}", "red"))
        return None

    partite = partite or []
    nomi = _get_nomi_squadre(ids)
    if nomi is None:
        return None

    stats = {
        sid: {
            "id": sid, "nome": nomi.get(sid, f"ID{sid}"),
            "PG": 0, "V": 0, "P": 0, "S": 0,
            "PF": 0, "PS": 0, "punti_class": 0,
        }
        for sid in ids
    }

    for m in partite:
        if m["p1"] is None or m["p2"] is None:
            continue
        a, b, pa, pb = m["id1"], m["id2"], m["p1"], m["p2"]
        stats[a]["PG"] += 1; stats[b]["PG"] += 1
        stats[a]["PF"] += pa; stats[a]["PS"] += pb
        stats[b]["PF"] += pb; stats[b]["PS"] += pa
        if pa > pb:
            stats[a]["V"] += 1; stats[a]["punti_class"] += 3; stats[b]["S"] += 1
        elif pb > pa:
            stats[b]["V"] += 1; stats[b]["punti_class"] += 3; stats[a]["S"] += 1
        else:
            stats[a]["P"] += 1; stats[a]["punti_class"] += 1
            stats[b]["P"] += 1; stats[b]["punti_class"] += 1

    return _applica_spareggi(list(stats.values()), list(partite))


def _applica_spareggi(teams: list, partite: list) -> list:
    if not teams:
        return teams
    by_pts: dict = {}
    for t in teams:
        by_pts.setdefault(t["punti_class"], []).append(t)
    result = []
    for pts in sorted(by_pts.keys(), reverse=True):
        gruppo = by_pts[pts]
        result.extend(gruppo if len(gruppo) == 1
                      else _spareggio_gruppo(gruppo, partite))
    return result


def _spareggio_gruppo(gruppo: list, tutte_partite: list) -> list:
    ids = {t["id"] for t in gruppo}
    dirette = [
        m for m in tutte_partite
        if m.get("id1") in ids and m.get("id2") in ids and m.get("p1") is not None
    ]

    if len(gruppo) == 2:
        a, b = gruppo[0], gruppo[1]
        for m in dirette:
            if {m["id1"], m["id2"]} == {a["id"], b["id"]}:
                pa = m["p1"] if m["id1"] == a["id"] else m["p2"]
                pb = m["p1"] if m["id1"] == b["id"] else m["p2"]
                if pa > pb:
                    return [a, b]
                elif pb > pa:
                    return [b, a]

    avulsa_pts = {t["id"]: 0 for t in gruppo}
    avulsa_pf  = {t["id"]: 0 for t in gruppo}
    avulsa_ps  = {t["id"]: 0 for t in gruppo}

    for m in dirette:
        id1, id2, p1, p2 = m["id1"], m["id2"], m["p1"], m["p2"]
        avulsa_pf[id1] += p1; avulsa_ps[id1] += p2
        avulsa_pf[id2] += p2; avulsa_ps[id2] += p1
        if p1 > p2:
            avulsa_pts[id1] += 3
        elif p2 > p1:
            avulsa_pts[id2] += 3
        else:
            avulsa_pts[id1] += 1; avulsa_pts[id2] += 1

    def ratio(pf, ps):
        return (pf / ps) if ps > 0 else (float("inf") if pf > 0 else 0.0)

    return sorted(gruppo, key=lambda t: (
        -avulsa_pts[t["id"]],
        -ratio(avulsa_pf[t["id"]], avulsa_ps[t["id"]]),
        -ratio(t["PF"], t["PS"]),
        t["nome"],
    ))


def mostra_classifica_gironi(nome: str, is_singolo: bool):
    print(IO.color("\n" + "═" * 66, "cyan"))
    print(IO.color(f"  CLASSIFICA GIRONI -- {nome}", "cyan"))
    print(IO.color("═" * 66, "cyan"))

    for girone in ("A", "B"):
        ids = _get_ids_girone(nome, girone)
        if ids is None:
            print(IO.color(f"Errore nel recupero squadre per il Girone {girone}.", "red"))
            continue
        if not ids:
            continue

        class_g = _classifica_girone(nome, girone)
        if class_g is None:
            print(IO.color(f"Errore nel calcolo classifica per il Girone {girone}.", "red"))
            continue

        print(IO.color(f"\n  GIRONE {girone}  ({len(ids)} squadre)", "cyan"))

        header = (
            f"  {'Pos':<7}  {'Squadra':<24}"
            f"  {'PG':>3}  {'V':>3}  {'P':>3}  {'S':>3}"
            f"  {'PF':>5}  {'Pts':>4}"
        )
        print(IO.color(header, "white"))
        print(IO.color("  " + "─" * 54, "white"))

        for pos, t in enumerate(class_g, 1):
            medaglia = _MEDAGLIE_GIRONI.get(pos, "  ")
            col = "cyan" if pos <= 2 else ("yellow" if pos <= 4 else "white")
            display_name = (t['nome'][:24] + '..') if len(t['nome']) > 24 else t['nome']
            riga = (
                f"  {pos:>3}.{medaglia} {display_name:<24}"
                f"  {t['PG']:>3}  {t['V']:>3}  {t['P']:>3}  {t['S']:>3}"
                f"  {t['PF']:>5}  {t['punti_class']:>4}"
            )
            print(IO.color(riga, col))

        print(IO.color("  " + "─" * 54, "white"))

    print(IO.color(
        "\n  Legenda: PG=Partite giocate  V=Vinte  P=Pareggiate  "
        "S=Perse  PF=Punti fatti  Pts=Punti class.",
        "white",
    ))
    print(IO.color(
        "  Spareggi: 1)Scontro diretto  2)Class. avulsa  "
        "3)Quoz. diretto  4)Quoz. totale",
        "white",
    ))
    print(IO.color(f"  Aggiornata: {datetime.now().strftime('%d/%m/%Y %H:%M')}", "white"))
    print(IO.color("═" * 66, "cyan"))


# ══════════════════════════════════════════════════════════════
#  PLAYOFF — TABELLONE PRINCIPALE
# ══════════════════════════════════════════════════════════════

def _genera_tabellone_playoff(nome: str, is_singolo: bool):
    print(IO.color("\n-- Generazione Tabellone Playoff --", "cyan"))

    class_A = _classifica_girone(nome, "A")
    class_B = _classifica_girone(nome, "B")

    if class_A is None or class_B is None:
        print(IO.color("Errore nel recupero delle classifiche dei gironi. Impossibile procedere.", "red"))
        return

    # Caso speciale: girone unico (≤3 squadre, nessun girone B)
    if not class_B:
        if not class_A or len(class_A) < 2:
            print(IO.color("  Classifiche non disponibili. Impossibile procedere.", "red"))
            return
        _genera_finale_girone_unico(nome, class_A)
        return

    if not class_A:
        print(IO.color("  Classifiche non disponibili. Impossibile procedere.", "red"))
        return

    nA, nB = len(class_A), len(class_B)

    all_team_ids = [t["id"] for t in class_A] + [t["id"] for t in class_B]
    nomi = _get_nomi_squadre(all_team_ids)
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi delle squadre. Annullamento.", "red"))
        return

    fasi_semi   = []
    fasi_dirette = []

    if nA == 2 and nB == 2:
        # Caso speciale: ogni "girone" è uno scontro 1-vs-1 di qualificazione.
        # Niente semifinali: vincitori → finale 1-2, perdenti → finale 3-4.
        fasi_dirette.append({
            "fase": "finale_1_2",
            "label": "Finale 1°-2° posto",
            "id1": class_A[0]["id"], "id2": class_B[0]["id"],
        })
        fasi_dirette.append({
            "fase": "finale_3_4",
            "label": "Finale 3°-4° posto",
            "id1": class_A[1]["id"], "id2": class_B[1]["id"],
        })
    else:
        if nA >= 2 and nB >= 2:
            fasi_semi.append({
                "fase": "semifinale_A",
                "label": "Semifinale 1-4 posto",
                "coppie": [
                    (class_A[0]["id"], class_B[1]["id"]),
                    (class_B[0]["id"], class_A[1]["id"]),
                ],
            })

    if nA >= 3 and nB >= 3:
        if nA >= 4 and nB >= 4:
            fasi_semi.append({
                "fase": "semifinale_B",
                "label": "Semifinale 5-8 posto",
                "coppie": [
                    (class_A[2]["id"], class_B[3]["id"]),
                    (class_B[2]["id"], class_A[3]["id"]),
                ],
            })
        else:
            fasi_dirette.append({
                "fase": "finale_diretta_5_6",
                "label": "Finale diretta  5 - 6  posto",
                "id1": class_A[2]["id"],
                "id2": class_B[2]["id"],
            })

    if nA >= 5 and nB >= 5:
        if nA >= 6 and nB >= 6:
            fasi_semi.append({
                "fase": "semifinale_C",
                "label": "Semifinale 9-12 posto",
                "coppie": [
                    (class_A[4]["id"], class_B[5]["id"]),
                    (class_B[4]["id"], class_A[5]["id"]),
                ],
            })
        else:
            fasi_dirette.append({
                "fase": "finale_diretta_9_10",
                "label": "Finale diretta  9 - 10 posto",
                "id1": class_A[4]["id"],
                "id2": class_B[4]["id"],
            })

    if not fasi_semi and not fasi_dirette:
        print(IO.color("  Squadre insufficienti per il playoff.", "red"))
        return

    if fasi_semi:
        print(IO.color("\n  ─── Semifinali ───", "cyan"))
        for fs in fasi_semi:
            print(IO.color(f"\n  {fs['label']}:", "cyan"))
            for id1, id2 in fs["coppie"]:
                n1 = nomi.get(id1, f'ID{id1}')
                n2 = nomi.get(id2, f'ID{id2}')
                n1_d = (n1[:28] + '..') if len(n1) > 28 else n1
                n2_d = (n2[:28] + '..') if len(n2) > 28 else n2
                print(IO.color(f"    {n1_d:<28}  vs  {n2_d}", "white"))

    if fasi_dirette:
        print(IO.color("\n  ─── Finali dirette ───", "cyan"))
        for fd in fasi_dirette:
            n1 = nomi.get(fd["id1"], f'ID{fd["id1"]}')
            n2 = nomi.get(fd["id2"], f'ID{fd["id2"]}')
            n1_d = (n1[:28] + '..') if len(n1) > 28 else n1
            n2_d = (n2[:28] + '..') if len(n2) > 28 else n2
            print(IO.color(f"\n  {fd['label']}:", "cyan"))
            print(IO.color(f"    {n1_d:<28}  vs  {n2_d}", "white"))

    luogo = input(IO.color("\nLuogo delle partite di playoff (INVIO = 'Sala Principale'): ", "yellow")).strip() or "Sala Principale"

    if yes_or_no_veloce("\nConfermi e generi il tabellone?", default="si") == "no":
        print(IO.color("Operazione annullata.", "yellow"))
        return

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    num_turno = _prossimo_numero_turno(nome)
    if num_turno is None:
        db.rollback_transaction()
        return

    try:
        for fs in fasi_semi:
            id_turno = db.insert("turno", ["numero", "nome_torneo", "fase"], [num_turno, nome, fs["fase"]])
            if not db.risultato.successo:
                raise Exception(f"Errore creazione turno semifinale '{fs['fase']}': {db.risultato.get_msg()}")
            for id1, id2 in fs["coppie"]:
                if not _crea_partita(id_turno, luogo, id1, id2):
                    raise Exception(f"Errore creazione partita {id1} vs {id2}")
            num_turno += 1

        for fd in fasi_dirette:
            id_turno = db.insert("turno", ["numero", "nome_torneo", "fase"], [num_turno, nome, fd["fase"]])
            if not db.risultato.successo:
                raise Exception(f"Errore creazione turno finale diretta '{fd['fase']}': {db.risultato.get_msg()}")
            if not _crea_partita(id_turno, luogo, fd["id1"], fd["id2"]):
                raise Exception(f"Errore creazione partita diretta {fd['id1']} vs {fd['id2']}")
            num_turno += 1

        db.commit_transaction()
        if db.risultato.successo:
            msg = "Tabellone playoff generato!"
            if fasi_semi:
                msg += " Registra i risultati delle semifinali per generare le finali."
            elif fasi_dirette:
                msg += " Registra i risultati delle finali per chiudere il torneo."
            print(IO.color(f"\n{msg}", "green"))
            _pubblica_calendario(nome, is_singolo)
        else:
            print(IO.color(f"Errore durante il commit: {db.risultato.get_msg()}", "red"))

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\nErrore durante la generazione del tabellone playoff: {e}. Rollback eseguito.", "red"))


def _genera_finale_girone_unico(nome: str, classifica: list):
    """Genera una finale_1_2 per tornei con un unico girone (≤3 squadre)."""
    nomi = _get_nomi_squadre([t["id"] for t in classifica])
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi.", "red"))
        return

    id1, id2 = classifica[0]["id"], classifica[1]["id"]
    n1 = nomi.get(id1, f"ID{id1}")
    n2 = nomi.get(id2, f"ID{id2}")

    print(IO.color("\n  ─── Finale (Girone Unico) ───", "cyan"))
    print(IO.color(f"\n  Finale 1 - 2 posto:", "cyan"))
    print(IO.color(f"    {n1:<28}  vs  {n2}", "white"))

    luogo = input(IO.color("\nLuogo della finale (INVIO = 'Sala Principale'): ", "yellow")).strip() or "Sala Principale"

    if yes_or_no_veloce("\nConfermi e generi la finale?", default="si") == "no":
        print(IO.color("Operazione annullata.", "yellow"))
        return

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    num_turno = _prossimo_numero_turno(nome)
    if num_turno is None:
        db.rollback_transaction()
        return

    try:
        id_turno = db.insert("turno", ["numero", "nome_torneo", "fase"], [num_turno, nome, "finale_1_2"])
        if not db.risultato.successo:
            raise Exception(f"Errore creazione turno finale: {db.risultato.get_msg()}")
        if not _crea_partita(id_turno, luogo, id1, id2):
            raise Exception("Errore creazione partita finale")

        db.commit_transaction()
        if db.risultato.successo:
            print(IO.color("\nFinale generata!", "green"))
            if len(classifica) > 2:
                id3 = classifica[2]["id"]
                n3 = nomi.get(id3, f"ID{id3}")
                print(IO.color(
                    f"\n  ⚠ NOTA: La squadra {n3} (3ª classificata) non accede "
                    f"alla finale e mantiene il 3° posto assoluto.",
                    "yellow",
                ))
        else:
            print(IO.color(f"Errore commit: {db.risultato.get_msg()}", "red"))

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\nErrore: {e}. Rollback eseguito.", "red"))


def _prova_genera_finali(nome: str):
    """Auto-genera le finali dopo che le semifinali sono complete."""
    fasi_sf = db.execute_select(
        "SELECT fase, id_turno FROM turno WHERE nome_torneo=%s AND fase LIKE %s",
        params=(nome, 'semifinale%')
    )
    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero semifinali: {db.risultato.get_msg()}", "red"))
        return
    if not fasi_sf:
        return

    semifinali_pronte = []

    for row in fasi_sf:
        fase_sf = row["fase"]
        id_t    = row["id_turno"]
        if fase_sf not in _SEMI_A_FINALI:
            continue

        fase_fin_v, fase_fin_p = _SEMI_A_FINALI[fase_sf]

        r_exist = db.execute_select(
            "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase IN (%s, %s)",
            params=(nome, fase_fin_v, fase_fin_p)
        )
        if not db.risultato.successo:
            continue
        if r_exist and r_exist[0]["n"] > 0:
            continue

        r_pend = db.execute_select("""
            SELECT COUNT(*) AS n FROM partita_squadra ps
            JOIN   partita par ON par.id_partita = ps.id_partita
            WHERE  par.id_turno = %s AND ps.punteggio IS NULL
        """, params=(id_t,))
        if not db.risultato.successo:
            continue
        pending = (r_pend[0]["n"] // 2) if r_pend else 1
        if pending > 0:
            continue

        partite_sf = db.execute_select("""
            SELECT ps1.id_squadra AS id1, ps1.punteggio AS p1,
                   ps2.id_squadra AS id2, ps2.punteggio AS p2,
                   par.luogo
            FROM   partita_squadra ps1
            JOIN   partita_squadra ps2
                   ON  ps2.id_partita = ps1.id_partita
                   AND ps2.id_squadra > ps1.id_squadra
            JOIN   partita par ON par.id_partita = ps1.id_partita
            WHERE  par.id_turno = %s AND ps1.punteggio IS NOT NULL
        """, params=(id_t,))
        if not db.risultato.successo or not partite_sf:
            continue

        vincenti, perdenti = [], []
        luogo_partita = partite_sf[0]["luogo"]
        for p in partite_sf:
            if p["p1"] > p["p2"]:
                vincenti.append(p["id1"]); perdenti.append(p["id2"])
            else:
                vincenti.append(p["id2"]); perdenti.append(p["id1"])

        if len(vincenti) < 2 or len(perdenti) < 2:
            continue

        semifinali_pronte.append({
            "fase_fin_v": fase_fin_v,
            "fase_fin_p": fase_fin_p,
            "vincenti":   vincenti,
            "perdenti":   perdenti,
            "luogo":      luogo_partita,
        })

    if not semifinali_pronte:
        return

    print(IO.color("\n  Semifinali completate -> generazione automatica finali...", "cyan"))

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    num = _prossimo_numero_turno(nome)
    if num is None:
        db.rollback_transaction()
        return

    finali_generate = 0
    try:
        for sf in semifinali_pronte:
            for fase_f, coppie in ((sf["fase_fin_v"], sf["vincenti"]), (sf["fase_fin_p"], sf["perdenti"])):
                label = _LABEL_FASE.get(fase_f, fase_f)
                if len(coppie) < 2:
                    print(IO.color(f"  ⚠ Insufficienti squadre per '{label}'.", "red"))
                    continue

                id_t2 = db.insert("turno", ["numero", "nome_torneo", "fase"], [num, nome, fase_f])
                if not db.risultato.successo:
                    raise Exception(f"Errore creazione turno finale '{fase_f}': {db.risultato.get_msg()}")

                if not _crea_partita(id_t2, sf["luogo"], coppie[0], coppie[1]):
                    raise Exception(f"Errore creazione partita finale '{fase_f}'")

                nomi_f = _get_nomi_squadre(list(coppie))
                if nomi_f:
                    n1 = nomi_f.get(coppie[0], f"ID{coppie[0]}")
                    n2 = nomi_f.get(coppie[1], f"ID{coppie[1]}")
                    print(IO.color(f"  {label}: {n1}  vs  {n2}", "cyan"))

                num += 1
                finali_generate += 1

        db.commit_transaction()
        if db.risultato.successo and finali_generate:
            print(IO.color(f"\n{finali_generate} finali generate automaticamente!", "green"))
        elif not db.risultato.successo:
            print(IO.color(f"Errore commit finali: {db.risultato.get_msg()}", "red"))

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\nErrore durante la generazione delle finali: {e}. Rollback eseguito.", "red"))


# ══════════════════════════════════════════════════════════════
#  INSERIMENTO RISULTATI
# ══════════════════════════════════════════════════════════════

def _inserisci_risultati_pendenti(nome: str, is_singolo: bool):
    print(IO.color("\n-- Risultati in sospeso --", "cyan"))

    righe = db.execute_select("""
        SELECT  par.id_partita,
                par.luogo,
                t.numero         AS turno,
                t.fase           AS fase_turno,
                ps1.id_squadra   AS id1,
                ps2.id_squadra   AS id2
        FROM    partita par
        JOIN    turno   t   ON t.id_turno    = par.id_turno
        JOIN    partita_squadra ps1 ON ps1.id_partita = par.id_partita
        JOIN    partita_squadra ps2 ON ps2.id_partita = par.id_partita
                                   AND ps2.id_squadra > ps1.id_squadra
        WHERE   t.nome_torneo = %s AND ps1.punteggio IS NULL
        ORDER BY t.numero ASC, par.id_partita ASC
    """, params=(nome,))

    if not db.risultato.successo:
        print(IO.color(f"Errore DB: {db.risultato.get_msg()}", "red"))
        return
    if not righe:
        print(IO.color("  Nessuna partita in sospeso. Sei in pari!", "green"))
        return

    ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
    nomi = _get_nomi_squadre(list(ids_all))
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi delle squadre. Annullamento.", "red"))
        return

    registrate = 0
    print(IO.color(f"  {len(righe)} partite senza risultato:\n", "yellow"))

    for r in righe:
        id_p = r["id_partita"]
        id1, id2 = r["id1"], r["id2"]
        n1 = nomi.get(id1, f"ID{id1}")
        n2 = nomi.get(id2, f"ID{id2}")
        fase_t    = r.get("fase_turno", "")
        is_ko     = "semifinale" in fase_t or "finale" in fase_t
        label_fase = _LABEL_FASE.get(fase_t, fase_t)

        n1_display = (n1[:20] + '..') if len(n1) > 20 else n1
        n2_display = (n2[:20] + '..') if len(n2) > 20 else n2

        print(IO.color("  " + "─" * 62, "white"))
        print(IO.color(f"  {label_fase}  |  #{id_p:<4}  |  {r['luogo']}", "white"))
        print(f"      {IO.color(n1_display, 'cyan')}  vs  {IO.color(n2_display, 'cyan')}")
        print(IO.color("  Inserisci direttamente il risultato:", "yellow"))

        _registra_un_risultato(id_p, id1, id2, n1, n2, is_ko=is_ko, is_pending_insert=True)
        if db.risultato.successo:
            registrate += 1

        print()

    print(IO.color("  " + "─" * 62, "white"))

    if registrate > 0:
        print(IO.color(f"\n  Risultati inseriti: {registrate}/{len(righe)}.", "green"))
        mostra_classifica_gironi(nome, is_singolo)
        _prova_genera_finali(nome)
    else:
        print(IO.color("  Nessun risultato inserito.", "yellow"))


def _registra_un_risultato(id_p: int, id1: int, id2: int,
                            n1: str, n2: str, is_ko: bool = False,
                            is_pending_insert: bool = False):
    global punteggio_totale_partita

    while True:
        p1 = IO.int_positivo_or_neutro_input(
            IO.color(f"  Punteggio di {n1} (max {punteggio_totale_partita}, il resto va all'avversario): ", "yellow"),
            IO.color("  Inserisci un intero >= 0: ", "red"),
        )
        if p1 <= punteggio_totale_partita:
            break
        print(IO.color(
            f"  Il punteggio non può superare il limite complessivo ({punteggio_totale_partita}).",
            "red"))

    p2 = punteggio_totale_partita - p1
    vincitore_name  = ""
    vincitore_score = 0

    if p1 > p2:
        print(IO.color(
            f"  -> {n1}: {IO.color(str(p1), 'green')}  "
            f"{n2}: {IO.color(str(p2), 'red')}  -- vince {n1}", "white"
        ))
        vincitore_name  = n1
        vincitore_score = p1
    elif p2 > p1:
        print(IO.color(
            f"  -> {n1}: {IO.color(str(p1), 'red')}  "
            f"{n2}: {IO.color(str(p2), 'green')}  -- vince {n2}", "white"
        ))
        vincitore_name  = n2
        vincitore_score = p2
    else:
        print(IO.color(
            f"  -> {n1}: {IO.color(str(p1), 'yellow')}  "
            f"{n2}: {IO.color(str(p2), 'yellow')}  -- PAREGGIO", "yellow"
        ))
        if is_ko:
            print(IO.color("  Pareggio in fase eliminatoria: mano supplementare.", "yellow"))
            vincitore_choice = IO.input_choice(
                [n1, n2],
                IO.color(f"  Chi ha vinto la mano supplementare? ('{n1}' / '{n2}'): ", "yellow"),
                IO.color(f"  Rispondi '{n1}' o '{n2}': ", "red"),
            )
            if vincitore_choice == n1:
                p1 += 1
                vincitore_name  = n1
                vincitore_score = p1
            else:
                p2 += 1
                vincitore_name  = n2
                vincitore_score = p2
            print(IO.color(
                f"  Dopo mano supplementare -> "
                f"{n1}: {IO.color(str(p1), 'green' if vincitore_name == n1 else 'red')}  "
                f"{n2}: {IO.color(str(p2), 'green' if vincitore_name == n2 else 'red')}",
                "white",
            ))
        else:
            vincitore_name = "Pareggio"

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"  Errore avvio transazione per partita {id_p}: {db.risultato.get_msg()}", "red"))
        db.risultato.successo = False
        return

    try:
        query = """
            INSERT INTO partita_squadra (id_partita, id_squadra, punteggio)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE punteggio = VALUES(punteggio)
        """
        db.execute_alt(query, params=(id_p, id1, p1))
        if not db.risultato.successo:
            raise Exception(f"Salvataggio punteggio squadra {id1}: {db.risultato.get_msg()}")
        db.execute_alt(query, params=(id_p, id2, p2))
        if not db.risultato.successo:
            raise Exception(f"Salvataggio punteggio squadra {id2}: {db.risultato.get_msg()}")

        db.commit_transaction()
        if db.risultato.successo:
            if vincitore_name == "Pareggio":
                print(IO.color(f"  Risultato salvato! Esito: Pareggio ({p1}-{p2})", "green"))
            else:
                print(IO.color(f"  Risultato salvato! Vincitore: {vincitore_name} ({vincitore_score})", "green"))
        else:
            print(IO.color(f"  Errore commit risultato {id_p}: {db.risultato.get_msg()}", "red"))
            db.risultato.successo = False

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"  Errore salvataggio risultato {id_p}: {e}. Rollback eseguito.", "red"))
        db.risultato.successo = False

    if not is_pending_insert:
        print()


def _correggi_risultato(nome: str, is_singolo: bool):
    print(IO.color("\n-- Correzione Risultato --", "cyan"))

    righe = db.execute_select("""
        SELECT  par.id_partita,
                par.luogo,
                t.fase           AS fase_turno,
                ps1.id_squadra   AS id1, ps1.punteggio AS p1,
                ps2.id_squadra   AS id2, ps2.punteggio AS p2
        FROM    partita par
        JOIN    turno   t   ON t.id_turno    = par.id_turno
        JOIN    partita_squadra ps1 ON ps1.id_partita = par.id_partita
        JOIN    partita_squadra ps2 ON ps2.id_partita = par.id_partita
                                   AND ps2.id_squadra > ps1.id_squadra
        WHERE   t.nome_torneo = %s
          AND   ps1.punteggio IS NOT NULL
        ORDER BY t.numero ASC, par.id_partita ASC
    """, params=(nome,))

    if not db.risultato.successo:
        print(IO.color(f"Errore DB: {db.risultato.get_msg()}", "red"))
        return
    if not righe:
        print(IO.color("  Nessuna partita con risultato trovata.", "yellow"))
        return

    ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
    nomi = _get_nomi_squadre(list(ids_all))
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi delle squadre. Annullamento.", "red"))
        return

    print(IO.color(f"  {len(righe)} partite con risultato:\n", "white"))
    for idx, r in enumerate(righe, 1):
        n1 = nomi.get(r["id1"], f"ID{r['id1']}")
        n2 = nomi.get(r["id2"], f"ID{r['id2']}")
        label_fase = _LABEL_FASE.get(r["fase_turno"], r["fase_turno"])

        if r['p1'] is not None and r['p2'] is not None:
            if r['p1'] > r['p2']:
                n1_d = IO.color(n1, 'green'); p1_d = IO.color(str(r['p1']), 'green')
                n2_d = IO.color(n2, 'red');   p2_d = IO.color(str(r['p2']), 'red')
                esito = f", Vincitore: {n1} ({r['p1']})"
            elif r['p2'] > r['p1']:
                n1_d = IO.color(n1, 'red');   p1_d = IO.color(str(r['p1']), 'red')
                n2_d = IO.color(n2, 'green'); p2_d = IO.color(str(r['p2']), 'green')
                esito = f", Vincitore: {n2} ({r['p2']})"
            else:
                n1_d = IO.color(n1, 'yellow'); p1_d = IO.color(str(r['p1']), 'yellow')
                n2_d = IO.color(n2, 'yellow'); p2_d = IO.color(str(r['p2']), 'yellow')
                esito = ", Esito: Pareggio"
        else:
            n1_d = n1; p1_d = str(r['p1']); n2_d = n2; p2_d = str(r['p2']); esito = ""

        print(IO.color(
            f"  {idx:>3}.  [{label_fase}]  |  "
            f"{n1_d} {p1_d} - {p2_d} {n2_d}{esito}",
            "white",
        ))

    print()
    raw = input(IO.color("Numero della partita da correggere (INVIO = annulla): ", "yellow")).strip()
    if not raw:
        print(IO.color("Correzione annullata.", "yellow"))
        return

    try:
        scelta = int(raw) - 1
        if scelta < 0 or scelta >= len(righe):
            raise ValueError
    except ValueError:
        print(IO.color("Numero non valido.", "red"))
        return

    r = righe[scelta]
    id_p = r["id_partita"]
    id1, id2 = r["id1"], r["id2"]
    n1 = nomi.get(id1, f"ID{id1}")
    n2 = nomi.get(id2, f"ID{id2}")
    is_ko = "semifinale" in r["fase_turno"] or "finale" in r["fase_turno"]

    # Guard Anti-Paradosso Temporale: correggere un girone con playoff già generati
    if r["fase_turno"].startswith("girone_"):
        chk = db.execute_select(
            "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo = %s "
            "AND (fase LIKE 'semifinale%' OR fase LIKE 'finale%')",
            params=(nome,)
        )
        if db.risultato.successo and chk and chk[0]["n"] > 0:
            print(IO.color(
                "\n  ⚠ AZIONE PERICOLOSA: Modificare i gironi comporterà\n"
                "  l'eliminazione definitiva dei playoff attuali.",
                "red",
            ))
            conferma_distr = input(IO.color(
                "  Procedere? (s/N) [INVIO = NO]: ", "red"
            )).strip().lower()
            if conferma_distr != "s":
                print(IO.color("  Operazione annullata.", "yellow"))
                return
            _elimina_playoff(nome)
            if not db.risultato.successo:
                return

    print(IO.color(
        f"\n  Correggendo: {n1}  {r['p1']} - {r['p2']}  {n2}\n"
        f"  Inserisci i nuovi punteggi:",
        "yellow",
    ))
    _registra_un_risultato(id_p, id1, id2, n1, n2, is_ko=is_ko)
    if db.risultato.successo:
        mostra_classifica_gironi(nome, is_singolo)


def _elimina_playoff(nome: str):
    """Cancella dal DB tutti i turni playoff (semifinali e finali) e le relative partite."""
    turni = db.execute_select(
        "SELECT id_turno FROM turno WHERE nome_torneo = %s "
        "AND (fase LIKE 'semifinale%' OR fase LIKE 'finale%')",
        params=(nome,)
    )
    if not db.risultato.successo:
        print(IO.color(f"  Errore recupero turni playoff: {db.risultato.get_msg()}", "red"))
        return
    if not turni:
        return

    ids_turni = [row["id_turno"] for row in turni]
    ids_str = ", ".join(str(i) for i in ids_turni)

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"  Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    try:
        db.execute_alt(f"""
            DELETE ps FROM partita_squadra ps
            JOIN partita par ON par.id_partita = ps.id_partita
            WHERE par.id_turno IN ({ids_str})
        """)
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.execute_alt(f"DELETE FROM partita WHERE id_turno IN ({ids_str})")
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.execute_alt(f"DELETE FROM turno WHERE id_turno IN ({ids_str})")
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        print(IO.color(
            f"  ✓ {len(ids_turni)} turno/i di playoff eliminati. "
            f"Torneo riportato alla fase GIRONI.",
            "green",
        ))
    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"  Errore eliminazione playoff: {e}. Rollback eseguito.", "red"))


# ══════════════════════════════════════════════════════════════
#  CLASSIFICA FINALE
# ══════════════════════════════════════════════════════════════

def _classifica_finale_girone_unico_diretta(nome: str, is_singolo: bool):
    """Classifica finale per tornei a girone unico (<6 squadre, nessun playoff)."""
    class_g = _classifica_girone(nome, "A")
    if not class_g:
        print(IO.color("  Nessun risultato disponibile.", "yellow"))
        print(IO.color("═" * 70, "cyan"))
        return

    ids = [t["id"] for t in class_g]
    nomi = _get_nomi_squadre(ids)
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi delle squadre.", "red"))
        print(IO.color("═" * 70, "cyan"))
        return

    ids_str = ", ".join(str(i) for i in ids)
    stats_rows = db.execute_select(f"""
        SELECT ps.id_squadra,
               COUNT(*)                                                    AS PG,
               SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 1 ELSE 0 END) AS V,
               SUM(CASE WHEN ps.punteggio < ps2.punteggio THEN 1 ELSE 0 END) AS S,
               COALESCE(SUM(ps.punteggio), 0)                              AS PF
        FROM   partita_squadra ps
        JOIN   partita_squadra ps2
               ON  ps2.id_partita  = ps.id_partita
               AND ps2.id_squadra != ps.id_squadra
        JOIN   partita par ON par.id_partita = ps.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo = %s AND ps.punteggio IS NOT NULL
          AND  ps.id_squadra IN ({ids_str})
        GROUP BY ps.id_squadra
    """, params=(nome,))

    stats: dict = {}
    if db.risultato.successo and stats_rows:
        for row in stats_rows:
            stats[row["id_squadra"]] = row

    dettagli = {}
    if not is_singolo:
        membri_rows = db.execute_select(f"""
            SELECT sq.id_squadra,
                   GROUP_CONCAT(
                       CONCAT(p.nome, ' ', p.cognome)
                       ORDER BY p.cognome SEPARATOR ' / '
                   ) AS giocatori
            FROM   squadra sq
            JOIN   partecipante p ON p.id_squadra = sq.id_squadra
            WHERE  sq.id_squadra IN ({ids_str})
            GROUP BY sq.id_squadra
        """, params=())
        if db.risultato.successo and membri_rows:
            for row in membri_rows:
                dettagli[row["id_squadra"]] = row["giocatori"]

    hdr_stats = f"  {'PG':>3}  {'V':>3}  {'S':>3}  {'Punti':>6}"
    print(IO.color(
        f"  {'Pos':<7}  {'Nome':<24}{hdr_stats}  Giocatori"
        if not is_singolo else f"  {'Pos':<7}  {'Nome':<24}{hdr_stats}",
        "white",
    ))
    print(IO.color("  " + "─" * 68, "white"))

    for pos, t in enumerate(class_g, 1):
        sq_id = t["id"]
        nome_sq = nomi.get(sq_id, f"ID{sq_id}")
        medaglia = _MEDAGLIE_FINALI.get(pos, "  ")
        col = "cyan" if pos <= 3 else ("yellow" if pos <= 6 else "white")
        display_name = (nome_sq[:24] + '..') if len(nome_sq) > 24 else nome_sq
        st = stats.get(sq_id)
        if st:
            st_str = f"  {st['PG']:>3}  {st['V']:>3}  {st['S']:>3}  {st['PF']:>6}"
        else:
            st_str = f"  {'—':>3}  {'—':>3}  {'—':>3}  {'—':>6}"
        riga = f"  {pos:>3}.{medaglia}  {display_name:<24}{st_str}"
        if not is_singolo and sq_id in dettagli:
            riga += f"  {dettagli[sq_id]}"
        print(IO.color(riga, col))

    print(IO.color("  " + "─" * 68, "white"))
    print(IO.color(f"  Generata il: {datetime.now().strftime('%d/%m/%Y %H:%M')}", "white"))
    print(IO.color("═" * 70, "cyan"))


def classifica_finale(nome: str, is_singolo: bool):
    print(IO.color("\n" + "═" * 70, "cyan"))
    print(IO.color(f"  CLASSIFICA FINALE -- {nome}", "cyan"))
    print(IO.color("═" * 70, "cyan"))

    finali = db.execute_select("""
        SELECT t.fase,
               ps1.id_squadra AS id1, ps1.punteggio AS p1,
               ps2.id_squadra AS id2, ps2.punteggio AS p2
        FROM   turno t
        JOIN   partita         par ON par.id_turno    = t.id_turno
        JOIN   partita_squadra ps1 ON ps1.id_partita  = par.id_partita
        JOIN   partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                  AND ps2.id_squadra > ps1.id_squadra
        WHERE  t.nome_torneo = %s
          AND  t.fase LIKE %s
          AND  ps1.punteggio IS NOT NULL
    """, params=(nome, 'finale%'))

    if not db.risultato.successo:
        print(IO.color(f"Errore DB: {db.risultato.get_msg()}", "red"))
        print(IO.color("═" * 70, "cyan"))
        return
    if not finali:
        ids_B = _get_ids_girone(nome, "B")
        if ids_B is not None and not ids_B:
            _classifica_finale_girone_unico_diretta(nome, is_singolo)
            return
        print(IO.color("  Classifica finale non disponibile: nessuna finale con risultati.", "yellow"))
        print(IO.color("═" * 70, "cyan"))
        return

    posizioni: dict = {}
    for f in finali:
        fase = f["fase"]
        if fase not in _FINALE_POSIZIONI:
            continue
        pos_v, pos_p = _FINALE_POSIZIONI[fase]
        if f["p1"] > f["p2"]:
            posizioni[f["id1"]] = pos_v
            posizioni[f["id2"]] = pos_p
        else:
            posizioni[f["id2"]] = pos_v
            posizioni[f["id1"]] = pos_p

    if not posizioni:
        print(IO.color("  Nessuna finale con risultato valido trovata.", "yellow"))
        print(IO.color("═" * 70, "cyan"))
        return

    # ── Append squadre escluse dai playoff ───────────────────────────────
    tutte_sq = db.execute_select(
        "SELECT id_squadra FROM squadra WHERE nome_torneo = %s", params=(nome,)
    )
    if db.risultato.successo and tutte_sq:
        tutti_ids = {r["id_squadra"] for r in tutte_sq}
        ids_escluse = tutti_ids - set(posizioni.keys())

        if ids_escluse:
            escluse_stats = []
            for girone in ("A", "B"):
                class_g = _classifica_girone(nome, girone)
                if class_g:
                    for rank, team in enumerate(class_g, 1):
                        if team["id"] in ids_escluse:
                            escluse_stats.append({
                                "id": team["id"],
                                "punti_class": team["punti_class"],
                                "PF": team["PF"],
                                "PS": team["PS"],
                                "rank_girone": rank,
                            })

            escluse_stats.sort(key=lambda t: (
                -t["punti_class"],
                -(t["PF"] / t["PS"] if t["PS"] > 0 else float("inf")),
                t["rank_girone"],
            ))

            next_pos = max(posizioni.values()) + 1
            for i, team in enumerate(escluse_stats):
                posizioni[team["id"]] = next_pos + i

    # ── Recupera nomi e dettagli per tutte le squadre posizionate ────────
    nomi = _get_nomi_squadre(list(posizioni.keys()))
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi delle squadre.", "red"))
        print(IO.color("═" * 70, "cyan"))
        return

    # ── Statistiche globali (tutte le partite del torneo) ─────────────────
    ids_str = ", ".join(str(i) for i in posizioni.keys())
    stats_rows = db.execute_select(f"""
        SELECT ps.id_squadra,
               COUNT(*)                                                    AS PG,
               SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 1 ELSE 0 END) AS V,
               SUM(CASE WHEN ps.punteggio < ps2.punteggio THEN 1 ELSE 0 END) AS S,
               COALESCE(SUM(ps.punteggio), 0)                              AS PF
        FROM   partita_squadra ps
        JOIN   partita_squadra ps2
               ON  ps2.id_partita  = ps.id_partita
               AND ps2.id_squadra != ps.id_squadra
        JOIN   partita par ON par.id_partita = ps.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo = %s
          AND  ps.punteggio  IS NOT NULL
          AND  ps.id_squadra IN ({ids_str})
        GROUP BY ps.id_squadra
    """, params=(nome,))

    stats: dict = {}
    if db.risultato.successo and stats_rows:
        for row in stats_rows:
            stats[row["id_squadra"]] = row

    dettagli = {}
    if not is_singolo:
        membri_rows = db.execute_select(f"""
            SELECT sq.id_squadra,
                   GROUP_CONCAT(
                       CONCAT(p.nome, ' ', p.cognome)
                       ORDER BY p.cognome SEPARATOR ' / '
                   ) AS giocatori
            FROM   squadra sq
            JOIN   partecipante p ON p.id_squadra = sq.id_squadra
            WHERE  sq.id_squadra IN ({ids_str})
            GROUP BY sq.id_squadra
        """, params=())
        if db.risultato.successo and membri_rows:
            for row in membri_rows:
                dettagli[row["id_squadra"]] = row["giocatori"]

    hdr_stats = f"  {'PG':>3}  {'V':>3}  {'S':>3}  {'Punti':>6}"
    print(IO.color(
        f"  {'Pos':<7}  {'Nome':<24}{hdr_stats}  Giocatori"
        if not is_singolo else f"  {'Pos':<7}  {'Nome':<24}{hdr_stats}",
        "white",
    ))
    print(IO.color("  " + "─" * 68, "white"))

    for pos in sorted(posizioni.values()):
        sq_id = next((k for k, v in posizioni.items() if v == pos), None)
        if sq_id is None:
            continue
        nome_sq  = nomi.get(sq_id, f"ID{sq_id}")
        medaglia = _MEDAGLIE_FINALI.get(pos, "  ")
        col      = "cyan" if pos <= 3 else ("yellow" if pos <= 6 else "white")

        display_name = (nome_sq[:24] + '..') if len(nome_sq) > 24 else nome_sq
        st = stats.get(sq_id)
        if st:
            st_str = f"  {st['PG']:>3}  {st['V']:>3}  {st['S']:>3}  {st['PF']:>6}"
        else:
            st_str = f"  {'—':>3}  {'—':>3}  {'—':>3}  {'—':>6}"
        riga = f"  {pos:>3}.{medaglia}  {display_name:<24}{st_str}"
        if not is_singolo and sq_id in dettagli:
            riga += f"  {dettagli[sq_id]}"
        print(IO.color(riga, col))

    print(IO.color("  " + "─" * 68, "white"))
    print(IO.color(f"  Generata il: {datetime.now().strftime('%d/%m/%Y %H:%M')}", "white"))
    print(IO.color("═" * 70, "cyan"))


# ══════════════════════════════════════════════════════════════
#  CALENDARIO COMPLETO / STORICO
# ══════════════════════════════════════════════════════════════

def _pubblica_calendario(nome: str, is_singolo: bool):
    print(IO.color("\n" + "═" * 74, "cyan"))
    print(IO.color(f"  CALENDARIO / STORICO PARTITE -- {nome}", "cyan"))
    print(IO.color("═" * 74, "cyan"))

    righe = db.execute_select("""
        SELECT  t.fase, t.numero AS turno,
                par.id_partita, par.luogo,
                ps1.id_squadra AS id1, ps1.punteggio AS p1,
                ps2.id_squadra AS id2, ps2.punteggio AS p2
        FROM    turno t
        JOIN    partita         par ON par.id_turno    = t.id_turno
        JOIN    partita_squadra ps1 ON ps1.id_partita  = par.id_partita
        JOIN    partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                   AND ps2.id_squadra   > ps1.id_squadra
        WHERE   t.nome_torneo = %s
        ORDER BY t.numero ASC, par.id_partita ASC
    """, params=(nome,))

    if not db.risultato.successo:
        print(IO.color(f"Errore DB: {db.risultato.get_msg()}", "red"))
        print(IO.color("═" * 74, "cyan"))
        return
    if not righe:
        print(IO.color("  Nessuna partita schedulata.", "yellow"))
        print(IO.color("═" * 74, "cyan"))
        return

    ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
    nomi = _get_nomi_squadre(list(ids_all))
    if nomi is None:
        print(IO.color("Errore nel recupero dei nomi delle squadre.", "red"))
        print(IO.color("═" * 74, "cyan"))
        return

    per_fase: dict = {}
    for r in righe:
        per_fase.setdefault(r["fase"], []).append(r)

    ordine_fasi = [
        "girone_A", "girone_B",
        "semifinale_A", "semifinale_B", "semifinale_C",
        "finale_1_2", "finale_3_4",
        "finale_diretta_5_6", "finale_5_6", "finale_7_8",
        "finale_diretta_9_10", "finale_9_10", "finale_11_12",
    ]

    for fase in ordine_fasi:
        if fase not in per_fase:
            continue

        label = _label_fase_dinamica(nome, fase)
        print(IO.color(f"\n  +── {label.upper()} ──", "cyan"))

        for r in per_fase[fase]:
            id1, id2 = r["id1"], r["id2"]
            n1 = nomi.get(id1, f"ID{id1}")
            n2 = nomi.get(id2, f"ID{id2}")
            p1, p2 = r["p1"], r["p2"]

            n1_short = (n1[:15] + '..') if len(n1) > 15 else n1
            n2_short = (n2[:15] + '..') if len(n2) > 15 else n2

            if p1 is not None and p2 is not None:
                if p1 > p2:
                    n1_c = IO.color(n1_short, 'green'); p1_c = IO.color(str(p1), 'green')
                    n2_c = IO.color(n2_short, 'red');   p2_c = IO.color(str(p2), 'red')
                    suf = f", Vincitore: {n1} ({p1})"
                elif p2 > p1:
                    n1_c = IO.color(n1_short, 'red');   p1_c = IO.color(str(p1), 'red')
                    n2_c = IO.color(n2_short, 'green'); p2_c = IO.color(str(p2), 'green')
                    suf = f", Vincitore: {n2} ({p2})"
                else:
                    n1_c = IO.color(n1_short, 'yellow'); p1_c = IO.color(str(p1), 'yellow')
                    n2_c = IO.color(n2_short, 'yellow'); p2_c = IO.color(str(p2), 'yellow')
                    suf = ", Esito: Pareggio"
                res_display = f"{n1_c} {p1_c}-{p2_c} {n2_c}{suf}"
                stato_tag = IO.color("v", "green")
            else:
                res_display = (
                    f"{IO.color(n1_short, 'white'):<15}  vs  "
                    f"{IO.color(n2_short, 'white'):<15}  |  "
                    f"{IO.color('Risultato mancante', 'yellow')}"
                )
                stato_tag = IO.color("!", "yellow")

            print(IO.color(
                f"  |  [{stato_tag}]  {r['luogo']:<16}  |  {res_display}",
                "white",
            ))

        print(IO.color("  +" + "─" * 71, "cyan"))

    print(IO.color(f"\n  Stampato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}", "white"))
    print(IO.color("═" * 74, "cyan"))


# ══════════════════════════════════════════════════════════════
#  HELPERS DB
# ══════════════════════════════════════════════════════════════

def _get_nomi_squadre(ids: list) -> dict | None:
    if not ids:
        return {}

    clean_ids = [str(int(i)) for i in ids if isinstance(i, (int, float))]
    if not clean_ids:
        return {}

    ids_str = ", ".join(clean_ids)

    detailed_data = db.execute_select(f"""
        SELECT
            sq.id_squadra,
            sq.nome AS team_name,
            p.id_partecipante,
            p.nome        AS p_nome,
            p.cognome     AS p_cognome,
            p.soprannome  AS p_soprannome
        FROM   squadra sq
        LEFT JOIN partecipante p ON p.id_squadra = sq.id_squadra
        WHERE  sq.id_squadra IN ({ids_str})
        ORDER BY sq.id_squadra, p.cognome, p.nome
    """, params=())

    if not db.risultato.successo:
        print(IO.color(f"Errore DB nel recupero nomi squadre: {db.risultato.get_msg()}", "red"))
        return None

    if not detailed_data:
        return {}

    teams_info = defaultdict(lambda: {'team_name': None, 'participants': []})
    for row in detailed_data:
        sq_id = row['id_squadra']
        if teams_info[sq_id]['team_name'] is None:
            teams_info[sq_id]['team_name'] = row['team_name']
        if row['p_nome']:
            teams_info[sq_id]['participants'].append({
                'id_partecipante': row['id_partecipante'],
                'nome':      row['p_nome'],
                'cognome':   row['p_cognome'],
                'soprannome': row['p_soprannome'],
            })

    preliminary_names_map = {}
    base_name_to_sq_ids   = defaultdict(list)

    for sq_id, data in teams_info.items():
        team_name = data['team_name']
        if team_name and not team_name.startswith("_singolo_"):
            base_name = team_name
        elif data['participants']:
            p = data['participants'][0]
            base_name = f"{p['nome']} {p['cognome']}"
        else:
            base_name = f"Squadra ID{sq_id}"

        preliminary_names_map[sq_id] = base_name
        base_name_to_sq_ids[base_name].append(sq_id)

    final_names = {}
    for sq_id, base_name in preliminary_names_map.items():
        if len(base_name_to_sq_ids[base_name]) > 1:
            team_data = teams_info[sq_id]
            disambiguating_suffix = ""

            if team_data['participants']:
                p = team_data['participants'][0]
                sop = p.get('soprannome')
                if sop and sop != f"{p['nome']} {p['cognome']}":
                    is_unique = True
                    for other_id in base_name_to_sq_ids[base_name]:
                        if other_id != sq_id and teams_info[other_id]['participants']:
                            other_sop = teams_info[other_id]['participants'][0].get('soprannome')
                            if other_sop == sop:
                                is_unique = False
                                break
                    if is_unique:
                        disambiguating_suffix = f" (Sop: {sop})"

            if not disambiguating_suffix:
                disambiguating_suffix = f" (ID: {sq_id})"

            final_names[sq_id] = f"{base_name}{disambiguating_suffix}"
        else:
            final_names[sq_id] = base_name

    return final_names


def _pausa():
    input(IO.color("\n[ Premi INVIO per continuare... ]", "cyan"))
