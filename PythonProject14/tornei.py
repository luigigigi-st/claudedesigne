"""
tornei.py  —  Gestione Tornei di Briscola

Interfaccia CLI / Dashboard
UX: Uscita rapida con INVIO in tutti i menu. Input case-insensitive.
"""

from config import db, print_errore, PASSWORD_TORNEI
from libreriax.console import IO
from utils import yes_or_no_veloce, input_scelta_veloce


# ══════════════════════════════════════════════════════════════
#  STATI DEL TORNEO E RELATIVA RAPPRESENTAZIONE
# ══════════════════════════════════════════════════════════════

_STATI_TORNEO = {
    "iscrizioni_aperte": ("●", "green",  "Iscrizioni APERTE"),
    "attesa":            ("~", "yellow", "Fase GIRONI - attesa di configurazione"),
    "gironi":            ("⚔", "cyan",   "Fase GIRONI in corso"),
    "playoff":           ("🏆", "green", "Fase PLAYOFF in corso"),
    "concluso":          ("✓", "white",  "Torneo CONCLUSO"),
}


def _calcola_stato_torneo(t: dict) -> str:
    """Allinea lo stato tornei alla stessa logica usata in partite1.py."""
    from partite1 import _get_stato, _calcola_fase

    stato = _get_stato(t["nome"])
    if stato is None:
        return "iscrizioni_aperte"
    return _calcola_fase(stato)


def _stato_colorato(t: dict) -> str:
    chiave = _calcola_stato_torneo(t)
    icona, colore, label = _STATI_TORNEO.get(chiave, ("?", "white", chiave))
    return IO.color(f"{icona} {label}", colore)


# ══════════════════════════════════════════════════════════════
#  MENU PRINCIPALE E DASHBOARD
# ══════════════════════════════════════════════════════════════

def svolgi():
    """Entrypoint gestore tornei. Accetta lettere maiuscole e minuscole. INVIO per uscire."""
    while True:
        _stampa_dashboard_principale()

        print(IO.color("  Operazioni disponibili:\n", "cyan"))
        voci = [
            ("1", "Nuovo Torneo",     "Crea un nuovo torneo nel sistema"),
            ("2", "Mostra Tutti",     "Elenca tutti i tornei in archivio"),
            ("3", "Filtra Singoli",   "Mostra solo i tornei individuali (1 vs 1)"),
            ("4", "Filtra Coppie",    "Mostra solo i tornei a squadre (2 vs 2)"),
            ("5", "Classifiche",      "Visualizza classifiche o playoff di un torneo"),
            ("D", "Elimina Torneo",   "Rimuove definitivamente un torneo dal database"),
        ]

        for tasto, azione, spiegazione in voci:
            if tasto == "D":
                col_btn, col_txt = "red", "red"
            else:
                col_btn, col_txt = "green", "white"

            fmt_tasto = IO.color(f"[{tasto}]", col_btn)
            fmt_azion = IO.color(f"{azione:<20}", col_btn if tasto == "D" else "cyan")
            fmt_spieg = IO.color(spiegazione, col_txt)
            print(f"  {fmt_tasto:<13} {fmt_azion} - {fmt_spieg}")

        print(f"  {IO.color('[INVIO]', 'yellow'):<13} "
              f"{IO.color('Esci dal modulo', 'white')} – "
              f"{IO.color('Torna alla Home', 'yellow')}\n")

        risp = input(IO.color("➜ Seleziona: ", "yellow")).strip().lower()

        match risp:
            case "" | "u" | "exit" | "esci":
                print(IO.color("\n  Uscita confermata. Ritorno alla Home...", "blue"))
                break
            case "1": input_and_insert_torneo()
            case "2": _sessione_lista_tornei("tutti")
            case "3": _sessione_lista_tornei("singolo")
            case "4": _sessione_lista_tornei("coppie")
            case "5": print_classifica()
            case "d": delete_torneo()
            case _:
                print(IO.color("  ✖ Scelta non valida. Digita il numero o la lettera corrispondente.", "red"))

        if risp not in ("", "u", "exit", "esci"):
            _pausa()


def _stampa_dashboard_principale():
    tornei = db.select_as_dict("torneo") or []

    in_attesa = sum(1 for t in tornei if _calcola_stato_torneo(t) == "iscrizioni_aperte")
    conclusi  = sum(1 for t in tornei if _calcola_stato_torneo(t) == "concluso")
    in_gioco  = len(tornei) - in_attesa - conclusi

    print("\n" + IO.color("═══════════════════════════════════════════════════════════════════════", "cyan"))
    print(IO.color(" ❖ PANNELLO DI CONTROLLO TORNEI", "cyan"))
    print(IO.color("═══════════════════════════════════════════════════════════════════════", "cyan"))

    if tornei:
        print(f"   Tornei totali      : {IO.color(str(len(tornei)), 'white')}")
        print(f"   Iscrizioni aperte  : {IO.color(str(in_attesa), 'green')}")
        print(f"   In corso           : {IO.color(str(in_gioco), 'cyan')}")
        print(f"   Conclusi           : {IO.color(str(conclusi), 'magenta')}")
    else:
        print(IO.color("   Nessun torneo presente nel database.", "yellow"))

    print(IO.color("───────────────────────────────────────────────────────────────────────", "cyan"))
    print()


# ══════════════════════════════════════════════════════════════
#  ELENCO E FILTRI TORNEI
# ══════════════════════════════════════════════════════════════

def _sessione_lista_tornei(filtro: str):
    if filtro == "singolo":
        tornei = db.select_as_dict("torneo", condizione="singolo_doppio = %s", params=(1,))
        titolo = "TORNEI INDIVIDUALI (1 VS 1)"
    elif filtro == "coppie":
        tornei = db.select_as_dict("torneo", condizione="singolo_doppio = %s", params=(0,))
        titolo = "TORNEI A COPPIE (2 VS 2)"
    else:
        tornei = db.select_as_dict("torneo")
        titolo = "TUTTI I TORNEI"

    print_errore()
    print(IO.color(f"\n── {titolo} ──", "cyan"))

    if not tornei:
        print(IO.color("   Nessun torneo trovato per questo filtro.", "yellow"))
        return

    print(IO.color(f"  {len(tornei)} torneo/i trovato/i:\n", "white"))
    for t in tornei:
        _stampa_card_torneo(t)


def _stampa_card_torneo(t: dict):
    is_singolo = (t["singolo_doppio"] == 1)
    tipo_str   = "Individuale (1 vs 1)" if is_singolo else "Coppie fisse (2 vs 2)"
    entita     = "Giocatori " if is_singolo else "Squadre   "

    if is_singolo:
        r_sq = db.execute_select(
            "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = %s", params=(t['nome'],)
        )
    else:
        r_sq = db.execute_select("""
            SELECT COUNT(*) AS n FROM squadra s
            WHERE  s.nome_torneo = %s
              AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 2
        """, params=(t['nome'],))
    n_sq = r_sq[0]["n"] if (db.risultato.successo and r_sq) else 0
    max_sq = t.get("max_squadre")

    if max_sq:
        rimasti = max_sq - n_sq
        clr = "green" if rimasti > 0 else "red"
        txt_limit = f"(max: {max_sq} | posti liberi: {IO.color(str(rimasti), clr)})"
    else:
        txt_limit = "(nessun limite di iscrizioni)"

    str_occupazione = IO.color(f"{n_sq} iscritti ", "green") + IO.color(txt_limit, "white")

    r_par = db.execute_select("""
        SELECT COUNT(DISTINCT par.id_partita) AS n
        FROM   partita par
        JOIN   turno   t2 ON t2.id_turno = par.id_turno
        WHERE  t2.nome_torneo = %s
    """, params=(t['nome'],))
    n_par = r_par[0]["n"] if (db.risultato.successo and r_par) else 0

    print(IO.color("  ┌───────────────────────────────────────────────────────────────────", "cyan"))
    print(IO.color("  │ Nome             |  ", "cyan") + IO.color(t['nome'].upper(), "magenta"))
    print(IO.color("  │ Formato          |  ", "cyan") + IO.color(tipo_str, "white"))
    print(IO.color("  │ Stato            |  ", "cyan") + _stato_colorato(t))
    print(IO.color(f"  │ {entita:<17}|  ", "cyan") + str_occupazione)
    print(IO.color("  │ Partite          |  ", "cyan") + IO.color(f"{n_par} disputate", "white"))

    if t.get("quota_iscrizione") is not None:
        q = float(t["quota_iscrizione"])
        txt_quota = f"{q:.2f} €/persona"
        if not is_singolo:
            txt_quota += IO.color(f"  (totale per squadra: {q * 2:.2f} €)", "yellow")
        print(IO.color("  │ Quota iscrizione |  ", "cyan") + IO.color(txt_quota, "white"))

    if t.get("email_iscrizioni"):
        print(IO.color("  │ Contatto / Email |  ", "cyan") + IO.color(t['email_iscrizioni'], "blue"))

    print(IO.color("  └───────────────────────────────────────────────────────────────────\n", "cyan"))


def input_and_check_torneo() -> list[dict] | None:
    """Cerca un torneo per nome. INVIO vuoto per annullare."""
    print_all_tornei()

    ricerca = input(IO.color("\n➜ Nome torneo (o INVIO per annullare): ", "yellow")).strip()

    if not ricerca:
        return None

    ric_db = db.select_as_dict("torneo", condizione="nome = %s", params=(ricerca,))

    if not db.risultato.successo:
        print(IO.color(f"  ✖ Errore database: {db.risultato.get_msg()}", "red"))
        return None

    if not ric_db:
        print(IO.color("  ✖ Torneo non trovato. Controlla il nome e riprova.", "red"))
        return None

    _stampa_card_torneo(ric_db[0])
    return ric_db


def print_all_tornei():
    tornei = db.select_as_dict("torneo")
    print_errore()
    print(IO.color("\n── Tornei disponibili ──", "cyan"))

    if not tornei:
        print(IO.color("  Nessun torneo registrato. Creane uno prima!", "yellow"))
        return

    for t in tornei:
        tipo_str = "SINGOLO" if t["singolo_doppio"] == 1 else "COPPIE"
        stato_str = _stato_colorato(t)
        max_sq = t.get("max_squadre")
        is_singolo_t = (t["singolo_doppio"] == 1)

        if is_singolo_t:
            r_sq = db.execute_select(
                "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = %s",
                params=(t['nome'],)
            )
        else:
            r_sq = db.execute_select("""
                SELECT COUNT(*) AS n FROM squadra s
                WHERE  s.nome_torneo = %s
                  AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 2
            """, params=(t['nome'],))
        n_sq = r_sq[0]["n"] if (db.risultato.successo and r_sq) else 0
        slot = f" [{n_sq}/{max_sq}]" if max_sq else f" [{n_sq}]"

        print(
            IO.color(f"  [{tipo_str}]  ", "white") +
            IO.color(f"{t['nome']:<35}", "cyan") +
            IO.color(slot, "white") +
            f"  {stato_str}"
        )
    print()


# ══════════════════════════════════════════════════════════════
#  CREAZIONE TORNEO
# ══════════════════════════════════════════════════════════════

def input_and_insert_torneo():
    _input_torneo()
    print_errore()


def _input_torneo():
    print(IO.color("\n" + "═" * 58, "cyan"))
    print(IO.color("  ✚  Creazione Nuovo Torneo di Briscola", "cyan"))
    print(IO.color("═" * 58, "cyan"))

    # ── Nome ─────────────────────────────────────────────────
    nome = input(IO.color("Nome del torneo (deve essere unico): ", "yellow")).strip()
    if not nome:
        print(IO.color("  Operazione annullata.", "white"))
        return

    esis = db.select_as_dict("torneo", condizione="nome = %s", params=(nome,))
    if esis:
        print(IO.color(f"  ✖ Esiste già un torneo chiamato '{nome}'. Scegline un altro.", "red"))
        return

    # ── Tipo ─────────────────────────────────────────────────
    tipo_input = input_scelta_veloce(
        ["singolo", "coppie"],
        "Tipo di torneo?",
        default="coppie",
    )
    valore_db = 1 if tipo_input == "singolo" else 0
    tipo_str  = "Singolo" if valore_db == 1 else "Coppie"
    entita    = "giocatori" if valore_db == 1 else "coppie"
    print(IO.color(
        f"  ✓ Tipo: {tipo_str} ({'1 vs 1' if valore_db == 1 else '2 vs 2'})", "green"
    ))

    # ── Informazioni iscrizione (opzionali) ──────────────────
    print(IO.color("\n── Informazioni iscrizione (opzionali) ──", "yellow"))

    quota = None
    raw = input(IO.color(
        "Quota iscrizione in € a persona (INVIO = nessuna quota): ", "yellow"
    )).strip()
    if raw:
        try:
            quota = float(raw.replace(",", "."))
            if quota <= 0:
                raise ValueError
            print(IO.color(f"  ✓ Quota: {quota:.2f}€ / persona.", "green"))
        except ValueError:
            print(IO.color("  Valore non valido (deve essere positivo), quota non impostata.", "yellow"))
            quota = None

    email = input(IO.color(
        "Email per invio iscrizioni (INVIO = nessuna): ", "yellow"
    )).strip() or None
    if email:
        print(IO.color(f"  ✓ Email: {email}", "green"))

    max_squadre = None
    raw = input(IO.color(
        f"Numero massimo di {entita} iscrivibili (INVIO = nessun limite): ", "yellow"
    )).strip()
    if raw:
        try:
            max_squadre = int(raw)
            if max_squadre < 2:
                raise ValueError
            print(IO.color(f"  ✓ Limite: {max_squadre} {entita}.", "green"))
        except ValueError:
            print(IO.color("  Valore non valido, nessun limite impostato.", "yellow"))
            max_squadre = None

    # ── Riepilogo ────────────────────────────────────────────
    print(IO.color("\n── Riepilogo ──", "cyan"))
    print(IO.color("  " + "─" * 52, "white"))
    print(IO.color(f"  Nome            : {nome}", "white"))
    print(IO.color(f"  Tipo            : {tipo_str}", "white"))
    if quota is not None:
        extra = f"  ({quota * 2:.2f}€ a coppia)" if valore_db == 0 else ""
        print(IO.color(f"  Quota           : {quota:.2f}€ / persona{extra}", "white"))
    if email:
        print(IO.color(f"  Email           : {email}", "white"))
    if max_squadre:
        print(IO.color(f"  Max iscritti    : {max_squadre} {entita}", "white"))
    print(IO.color("  " + "─" * 52, "white"))

    if yes_or_no_veloce("Salva questo torneo?", default="si") == "no":
        print(IO.color("  Inserimento annullato.", "yellow"))
        return

    db.insert(
        "torneo",
        ["nome", "singolo_doppio", "quota_iscrizione", "email_iscrizioni", "max_squadre"],
        [nome, valore_db, quota if quota is not None else 0, email, max_squadre],
    )

    if db.risultato.successo:
        print(IO.color(f"\n  ✓ Torneo '{nome}' creato con successo!", "green"))
        if email:
            print(IO.color(
                f"     Le iscrizioni vanno inviate a: {IO.color(email, 'cyan')}", "white"
            ))
        if quota:
            extra = f" ({quota * 2:.2f}€ a coppia)" if valore_db == 0 else ""
            print(IO.color(
                f"     Quota: {IO.color(f'{quota:.2f}€', 'green')} / persona{extra}.", "white"
            ))
    else:
        print(IO.color(f"\n  ✖ Errore nel salvataggio: {db.risultato.get_msg()}", "red"))


# ══════════════════════════════════════════════════════════════
#  CLASSIFICHE E PLAYOFF
# ══════════════════════════════════════════════════════════════

def print_classifica():
    torneo_scelto = input_and_check_torneo()
    if not torneo_scelto:
        return

    target = torneo_scelto[0]
    is_st  = _calcola_stato_torneo(target)

    if is_st in ("gironi", "playoff", "concluso"):
        try:
            from partite1 import mostra_classifica_gironi, classifica_finale
            if is_st == "concluso":
                classifica_finale(target["nome"], target["singolo_doppio"] == 1)
            else:
                mostra_classifica_gironi(target["nome"], target["singolo_doppio"] == 1)
        except ImportError:
            print(IO.color("  ✖ Modulo 'partite' non trovato. Verifica i file del progetto.", "red"))
    else:
        print(IO.color(
            f"\n  Il torneo «{target['nome']}» è ancora in fase di iscrizioni.\n"
            f"  Genera i gironi nel modulo apposito prima di visualizzare le classifiche.",
            "yellow"
        ))


# ══════════════════════════════════════════════════════════════
#  ELIMINAZIONE TORNEO
# ══════════════════════════════════════════════════════════════

def delete_torneo():
    print(IO.color("\n" + "═" * 58, "red"))
    print(IO.color("  ⚠  ELIMINAZIONE TORNEO — Operazione irreversibile!", "red"))
    print(IO.color("═" * 58, "red"))
    print(IO.color(
        "  Tutti i dati collegati (partecipanti, turni, partite, punteggi)\n"
        "  verranno eliminati definitivamente.\n",
        "red",
    ))

    targhettare_scelto = input_and_check_torneo()
    if not targhettare_scelto:
        return

    target = targhettare_scelto[0]["nome"]

    r_sq = db.execute_select(
        "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = %s", params=(target,)
    )
    n_sq = r_sq[0]["n"] if (db.risultato.successo and r_sq) else 0

    r_par = db.execute_select("""
        SELECT COUNT(DISTINCT par.id_partita) AS n
        FROM   partita par
        JOIN   turno t2 ON t2.id_turno = par.id_turno
        WHERE  t2.nome_torneo = %s
    """, params=(target,))
    n_par = r_par[0]["n"] if (db.risultato.successo and r_par) else 0

    if n_sq > 0 or n_par > 0:
        print(IO.color(
            f"  Attenzione: verranno eliminati in cascata\n"
            f"    • {n_sq} squadra/e o giocatore/i iscritti\n"
            f"    • {n_par} partita/e disputate",
            "yellow",
        ))

    if yes_or_no_veloce(f"\nConfermi l'eliminazione di '{target}'?", default="no") == "no":
        print(IO.color("  Eliminazione annullata.", "green"))
        return

    pwd = input(IO.color(
        "\n  Inserisci la password amministratore per procedere (INVIO per annullare):\n  ➜ ", "red"
    )).strip()

    if not pwd:
        print(IO.color("  Operazione annullata.", "yellow"))
        return

    if pwd != PASSWORD_TORNEI:
        print(IO.color("  ✖ Password errata. Eliminazione bloccata.", "red"))
        return

    db.delete("torneo", condizione="nome = %s", params=(target,))

    if db.risultato.successo:
        print(IO.color(f"\n  ✓ Torneo '{target}' e tutti i dati correlati eliminati.", "green"))
    else:
        print(IO.color(f"  ✖ Errore durante l'eliminazione: {db.risultato.get_msg()}", "red"))

    print_errore()


def _pausa():
    input(IO.color("\n  [ Premi INVIO per tornare al menu... ]", "cyan"))
