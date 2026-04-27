"""
partecipanti.py — Gestione Iscrizioni e Squadre
Interfaccia CLI allineata allo stile di tornei.py.
Logica semplificata: nessun codice fiscale, nessuna data di nascita.
Struttura DB (db_chill.txt): partecipante.id_squadra → FK diretta verso squadra.
"""

import random

from libreriax.console import IO
from config import db, print_errore
from tornei import input_and_check_torneo
from utils import yes_or_no_veloce, input_scelta_veloce


# ══════════════════════════════════════════════════════════════
#  MENU PRINCIPALE
# ══════════════════════════════════════════════════════════════

def main_partecipanti():
    print(IO.color("\n" + "═" * 60, "cyan"))
    print(IO.color("  👤  GESTIONE ISCRIZIONI E SQUADRE", "cyan"))
    print(IO.color("═" * 60, "cyan"))

    while True:
        voci = [
            ("T", "Scegli un torneo per iscrivere giocatori o formare coppie"),
            ("A", "Mostra l'elenco di tutti i giocatori nel sistema"),
            ("U", IO.color("Torna al menu principale", "yellow")),
        ]
        for chiave, desc in voci:
            colore = "red" if chiave == "U" else "green"
            hint = f"  {IO.color('[INVIO]', 'yellow')}" if chiave == "U" else ""
            print(f"  {IO.color(chiave, colore)}. {desc}{hint}")
        print()

        risp = input(IO.color("➜ Scelta: ", "yellow")).upper().strip()

        if risp in ("U", ""):
            print(IO.color("  Torno al menu principale. A presto!", "yellow"))
            break
        elif risp == "A":
            print_all_partecipanti()
            _pausa()
        elif risp == "T":
            lista = input_and_check_torneo()
            if lista is None:
                continue
            _sessione_torneo(lista[0])
        else:
            print(IO.color("  ✖ Scelta non valida.", "red"))


# ══════════════════════════════════════════════════════════════
#  SESSIONE TORNEO
# ══════════════════════════════════════════════════════════════

def _gironi_assegnati(nome: str) -> bool:
    """Restituisce True se almeno una squadra del torneo ha girone != NULL."""
    r = db.execute_select(
        "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = %s AND girone IS NOT NULL",
        params=(nome,)
    )
    return bool(r[0]["n"]) if (db.risultato.successo and r) else False


def _sessione_torneo(torneo: dict):
    nome = torneo["nome"]
    is_singolo = torneo["singolo_doppio"] == 1

    while True:
        r_turni = db.select_as_dict(
            "turno", colonne=["COUNT(*) AS n"],
            condizione="nome_torneo = %s", params=(nome,)
        )
        turni_esistono = (r_turni[0]["n"] > 0) if (db.risultato.successo and r_turni) else False
        gironi_attivi  = _gironi_assegnati(nome)

        n_singoli = _conta_singoli_in_attesa(nome) if not is_singolo else 0

        max_sq = torneo.get("max_squadre")
        n_complete = _conta_iscritti(nome, is_singolo) or 0
        torneo_pieno = bool(max_sq and n_complete >= max_sq)

        _stampa_dashboard(torneo, is_singolo, turni_esistono, gironi_attivi, n_singoli)

        voci = _costruisci_menu(is_singolo, turni_esistono, gironi_attivi, n_singoli, torneo_pieno)
        valide = {v[0] for v in voci if v[0] != "-"}

        for chiave, desc in voci:
            if chiave == "-":
                print(f"  {IO.color('•', 'red')}  {desc}")
            else:
                colore = "red" if chiave == "U" else "green"
                hint = f"  {IO.color('[INVIO]', 'yellow')}" if chiave == "U" else ""
                print(f"  {IO.color(chiave, colore)}. {desc}{hint}")
        print()

        risp = input(IO.color("➜ Scelta: ", "yellow")).upper().strip()

        if risp == "":
            break
        if risp not in valide:
            print(IO.color("  ✖ Scelta non valida.", "red"))
            continue

        match risp:
            case "U":
                break
            case "I":
                input_partecipanti_torneo(torneo, turni_esistono, gironi_attivi)
                _pausa()
            case "D":
                _elimina_partecipante(nome, is_singolo)
                _pausa()
            case "E":
                stampa_partecipanti_torneo(nome, is_singolo)
                _pausa()
            case "S":
                _stampa_coppie_torneo(nome)
                _pausa()
            case "P":
                _accoppia_singoli(nome)
                _pausa()


def _costruisci_menu(is_singolo: bool, turni_esistono: bool,
                     gironi_attivi: bool, n_singoli: int,
                     torneo_pieno: bool = False) -> list:
    tipo_testo = "un giocatore" if is_singolo else "una coppia o un singolo"
    iscr_bloccate = turni_esistono or gironi_attivi
    voci = []

    if gironi_attivi:
        voci.append(("-", IO.color(
            "⚠ Iscrizioni CHIUSE: I gironi sono già stati generati.\n"
            "     Per aggiungere ritardatari, usa 'Reset Gironi' nel menu Partite.",
            "yellow"
        )))
    elif turni_esistono:
        voci.append(("-", IO.color("ISCRIZIONI BLOCCATE — il torneo è già iniziato.", "white")))
    elif torneo_pieno:
        voci.append(("-", IO.color("Torneo al completo — non si accettano altri partecipanti.", "red")))
    else:
        voci.append(("I", f"Iscrivi {tipo_testo} a questo torneo"))

    if not iscr_bloccate:
        voci.append(("D", "Elimina un partecipante dal torneo"))

    voci.append(("E", "Visualizza la lista completa degli iscritti"))

    if not is_singolo:
        voci.append(("S", "Controlla lo stato delle coppie formate e dei gironi"))

    if n_singoli > 0 and not iscr_bloccate:
        voci.append(("P", IO.color(
            f"Abbina automaticamente i singoli in attesa  [{n_singoli} disponibili]",
            "cyan"
        )))

    voci.append(("U", "Indietro"))
    return voci


# ══════════════════════════════════════════════════════════════
#  DASHBOARD TORNEO
# ══════════════════════════════════════════════════════════════

def _stampa_dashboard(torneo: dict, is_singolo: bool, turni_esistono: bool,
                      gironi_attivi: bool, n_singoli: int):
    nome    = torneo["nome"]
    tipo    = IO.color("SINGOLO", "cyan") if is_singolo else IO.color("COPPIE", "yellow")
    entita  = "giocatori" if is_singolo else "coppie complete"
    max_sq  = torneo.get("max_squadre")

    n_complete = _conta_iscritti(nome, is_singolo) or 0

    if max_sq:
        rimasti  = max_sq - n_complete
        col      = "green" if rimasti > 0 else "red"
        slot_str = (
            f"{IO.color(str(n_complete), 'green')}/{IO.color(str(max_sq), 'white')}"
            f" {entita}  │  Posti liberi: {IO.color(str(rimasti), col)}"
        )
    else:
        slot_str = f"{IO.color(str(n_complete), 'green')} {entita}"

    if n_singoli > 0:
        slot_str += f"  │  {IO.color(str(n_singoli), 'yellow')} singolo/i in attesa"

    if gironi_attivi:
        stato_iscr = IO.color("⚔ Iscrizioni CHIUSE (Gironi in corso)", "yellow")
    elif turni_esistono:
        stato_iscr = IO.color("🔒 Iscrizioni BLOCCATE — torneo già avviato", "red")
    else:
        stato_iscr = IO.color("● Iscrizioni APERTE", "green")

    print("\n" + IO.color("═" * 64, "cyan"))
    print(IO.color(f"  Torneo   : {nome}  [{tipo}]", "cyan"))
    print(IO.color(f"  Stato    : {stato_iscr}", "white"))
    print(IO.color(f"  Iscritti : {slot_str}", "white"))

    quota = torneo.get("quota_iscrizione")
    if quota is not None:
        extra = f"  ({float(quota) * 2:.2f}€ a coppia)" if not is_singolo else ""
        print(IO.color(
            f"  Quota    : {IO.color(f'{float(quota):.2f}€', 'green')} / persona{extra}", "white"
        ))
    email = torneo.get("email_iscrizioni")
    if email:
        print(IO.color(f"  Email    : {IO.color(email, 'cyan')}", "white"))

    print(IO.color("═" * 64, "cyan"))
    print()


# ══════════════════════════════════════════════════════════════
#  ISCRIZIONE A UN TORNEO
# ══════════════════════════════════════════════════════════════

def input_partecipanti_torneo(torneo: dict, turni_esistono: bool,
                              gironi_attivi: bool = False):
    nome_torneo  = torneo["nome"]
    is_singolo_t = torneo["singolo_doppio"] == 1
    max_sq       = torneo.get("max_squadre")

    if gironi_attivi or _gironi_assegnati(nome_torneo):
        print(IO.color(
            "\n  ⚠ Impossibile iscrivere: i gironi sono già stati generati.\n"
            "    Per aggiungere ritardatari, usa 'Reset Gironi' nel menu Partite.",
            "red"
        ))
        return

    if turni_esistono:
        print(IO.color(
            "\n  ⚠ Impossibile iscrivere: il torneo ha già turni in corso.", "red"
        ))
        return

    if max_sq is not None:
        n_iscritti = _conta_iscritti(nome_torneo, is_singolo_t)
        if n_iscritti >= max_sq:
            entita_msg = "giocatori" if is_singolo_t else "coppie complete"
            print(IO.color(
                f"\n  ✗ Torneo al completo! "
                f"{entita_msg.capitalize()}: {IO.color(str(n_iscritti), 'red')}/{max_sq}.",
                "red"
            ))
            return

    quota = torneo.get("quota_iscrizione")
    email = torneo.get("email_iscrizioni")

    if quota is not None:
        extra = f"  ({float(quota) * 2:.2f}€ a coppia)" if not is_singolo_t else ""
        print(IO.color(
            f"\n  💶 Quota: {IO.color(f'{float(quota):.2f}€', 'green')} / persona{extra}", "white"
        ))
    if email:
        print(IO.color(f"  📧 Iscrizioni via: {IO.color(email, 'cyan')}", "white"))
    print(IO.color("  ⚠ Le iscrizioni sono DEFINITIVE.\n", "yellow"))

    if is_singolo_t:
        _input_giocatore_singolo(nome_torneo)
    else:
        mod = input_scelta_veloce(
            ["coppia", "singolo"],
            "\n  Iscrivi come 'coppia' (2 giocatori subito) o 'singolo' (in attesa di compagno)?",
            default="coppia",
        )
        if mod == "coppia":
            _input_coppia(nome_torneo)
        else:
            _input_singolo_in_attesa(nome_torneo)


# ══════════════════════════════════════════════════════════════
#  FLUSSI DI INSERIMENTO
# ══════════════════════════════════════════════════════════════

def _input_giocatore_singolo(nome_torneo: str):
    """Torneo singolo — 1 giocatore = 1 squadra. Il nome squadra è il soprannome."""
    print(IO.color(f"\n── Iscrizione: {nome_torneo} [SINGOLO] ──", "cyan"))
    print(IO.color("  Premi INVIO senza scrivere sul primo campo per annullare.\n", "yellow"))

    _stampa_iscritti_sintetica(nome_torneo, is_singolo=True)

    dati = _chiedi_dati_giocatore(nome_torneo)
    if dati is None:
        return

    if _squadra_esiste(dati["soprannome"], nome_torneo):
        print(IO.color(f"  ✖ Esiste già un iscritto con soprannome '{dati['soprannome']}'.", "red"))
        return

    db.start_transaction()
    try:
        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [dati["soprannome"], nome_torneo])
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.insert(
            "partecipante",
            ["nome", "cognome", "soprannome", "id_squadra"],
            [dati["nome"], dati["cognome"], dati["soprannome"], id_sq]
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        print(IO.color(
            f"\n  ✓ {dati['nome']} {dati['cognome']} «{dati['soprannome']}» iscritto con successo!",
            "green"
        ))
    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\n  ✖ Errore durante l'iscrizione: {e}", "red"))


def _input_coppia(nome_torneo: str):
    """Torneo coppie — 1 squadra con 2 giocatori."""
    print(IO.color(f"\n── Iscrizione: {nome_torneo} [COPPIE] ──", "cyan"))
    print(IO.color("  Premi INVIO senza scrivere sul primo campo per annullare.\n", "yellow"))

    _stampa_iscritti_sintetica(nome_torneo, is_singolo=False)

    nome_squadra = input(IO.color("  Nome della coppia: ", "yellow")).strip()
    if not nome_squadra:
        print(IO.color("  Iscrizione annullata.", "yellow"))
        return

    if _squadra_esiste(nome_squadra, nome_torneo):
        print(IO.color(f"  ✖ Esiste già una coppia chiamata '{nome_squadra}'.", "red"))
        return

    giocatori = []
    for i in range(2):
        print(IO.color(f"\n── Giocatore {i + 1} di 2 ──", "cyan"))
        dati = _chiedi_dati_giocatore(nome_torneo)
        if dati is None:
            print(IO.color("  Iscrizione coppia annullata.", "yellow"))
            return
        giocatori.append(dati)

    db.start_transaction()
    try:
        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [nome_squadra, nome_torneo])
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        for g in giocatori:
            db.insert(
                "partecipante",
                ["nome", "cognome", "soprannome", "id_squadra"],
                [g["nome"], g["cognome"], g["soprannome"], id_sq]
            )
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        nomi = " e ".join(
            f"{g['nome']} {g['cognome']} «{g['soprannome']}»" for g in giocatori
        )
        print(IO.color(
            f"\n  ✓ Coppia '{nome_squadra}' iscritta con successo!\n"
            f"    Componenti: {nomi}",
            "green"
        ))
    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\n  ✖ Errore: {e}", "red"))


def _input_singolo_in_attesa(nome_torneo: str):
    """Torneo coppie — 1 giocatore in attesa di compagno. Squadra = soprannome."""
    print(IO.color(f"\n── Iscrizione Singolo in Attesa: {nome_torneo} ──", "cyan"))
    print(IO.color("  Il giocatore sarà accoppiato prima dell'inizio con 'Abbina singoli'.", "yellow"))
    print(IO.color("  Premi INVIO senza scrivere sul primo campo per annullare.\n", "yellow"))

    _stampa_iscritti_sintetica(nome_torneo, is_singolo=False)

    dati = _chiedi_dati_giocatore(nome_torneo)
    if dati is None:
        return

    # La squadra usa il soprannome come nome (verrà rinominata all'accoppiamento)
    if _squadra_esiste(dati["soprannome"], nome_torneo):
        print(IO.color(f"  ✖ Il soprannome '{dati['soprannome']}' è già in uso.", "red"))
        return

    db.start_transaction()
    try:
        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [dati["soprannome"], nome_torneo])
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.insert(
            "partecipante",
            ["nome", "cognome", "soprannome", "id_squadra"],
            [dati["nome"], dati["cognome"], dati["soprannome"], id_sq]
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        print(IO.color(
            f"\n  ✓ {dati['nome']} {dati['cognome']} «{dati['soprannome']}» iscritto in attesa di compagno.\n"
            f"    Usa 'Abbina singoli' nel menu per formare la coppia.",
            "green"
        ))
    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\n  ✖ Errore: {e}", "red"))


def _chiedi_dati_giocatore(nome_torneo: str) -> dict | None:
    """
    Raccoglie nome, cognome e soprannome (tutti obbligatori).
    Premi INVIO vuoto sul nome per annullare l'intera iscrizione.
    Il soprannome viene riproposto finché non è univoco nel torneo.
    """
    nome = input(IO.color("  Nome: ", "yellow")).strip()
    if not nome:
        print(IO.color("  Iscrizione annullata.", "yellow"))
        return None
    if not any(c.isalpha() for c in nome):
        print(IO.color("  Il nome non può essere composto solo da numeri.", "red"))
        return None

    cognome = input(IO.color("  Cognome: ", "yellow")).strip()
    if not cognome:
        print(IO.color("  Iscrizione annullata.", "yellow"))
        return None
    if not any(c.isalpha() for c in cognome):
        print(IO.color("  Il cognome non può essere composto solo da numeri.", "red"))
        return None

    while True:
        soprannome = input(IO.color("  Soprannome (nome usato nel torneo): ", "yellow")).strip()
        if not soprannome:
            print(IO.color("  Il soprannome è obbligatorio — scrivi qualcosa.", "red"))
            continue

        dup = db.select_as_dict(
            "partecipante AS p",
            colonne=["p.id_partecipante"],
            join="JOIN squadra s ON s.id_squadra = p.id_squadra",
            condizione="s.nome_torneo = %s AND LOWER(p.soprannome) = LOWER(%s)",
            params=(nome_torneo, soprannome)
        )
        if not db.risultato.successo:
            print(IO.color(f"  ✖ Errore DB: {db.risultato.get_msg()}", "red"))
            return None
        if dup:
            print(IO.color(
                f"  ✖ Il soprannome '{soprannome}' è già in uso in questo torneo. Scegline un altro.",
                "red"
            ))
            continue
        break

    return {"nome": nome, "cognome": cognome, "soprannome": soprannome}


# ══════════════════════════════════════════════════════════════
#  CONTATORI
# ══════════════════════════════════════════════════════════════

def _conta_iscritti(nome_torneo: str, is_singolo: bool) -> int:
    """
    Conta gli iscritti che occupano un posto nel torneo:
    - Singolo   → tutte le squadre (1 membro ciascuna)
    - Coppie    → solo le squadre con 2 membri (coppie complete)
                  i singoli in attesa NON occupano posto
    """
    if is_singolo:
        r = db.execute_select(
            "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = %s",
            params=(nome_torneo,)
        )
    else:
        r = db.execute_select("""
            SELECT COUNT(*) AS n FROM squadra s
            WHERE  s.nome_torneo = %s
              AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 2
        """, params=(nome_torneo,))
    return r[0]["n"] if (db.risultato.successo and r) else 0


def _conta_singoli_in_attesa(nome_torneo: str) -> int:
    """Conta le squadre con un solo membro (singoli in attesa di compagno)."""
    r = db.execute_select("""
        SELECT COUNT(*) AS n FROM squadra s
        WHERE  s.nome_torneo = %s
          AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 1
    """, params=(nome_torneo,))
    return r[0]["n"] if (db.risultato.successo and r) else 0


def _squadra_esiste(nome_squadra: str, nome_torneo: str) -> bool:
    r = db.select_as_dict(
        "squadra", colonne=["id_squadra"],
        condizione="nome_torneo = %s AND nome = %s",
        params=(nome_torneo, nome_squadra)
    )
    return bool(r) if db.risultato.successo else False


# ══════════════════════════════════════════════════════════════
#  ACCOPPIAMENTO SINGOLI
# ══════════════════════════════════════════════════════════════

def _accoppia_singoli(nome_torneo: str):
    print(IO.color("\n── Accoppiamento Singoli ──", "cyan"))

    singoli = db.execute_select("""
        SELECT s.id_squadra,
               p.nome            AS nome_g,
               p.cognome         AS cognome_g,
               p.soprannome      AS soprannome_g,
               p.id_partecipante
        FROM   squadra s
        JOIN   partecipante p ON p.id_squadra = s.id_squadra
        WHERE  s.nome_torneo = %s
          AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 1
        ORDER BY s.id_squadra
    """, params=(nome_torneo,))

    if not db.risultato.successo:
        print(IO.color(f"  ✖ Errore DB: {db.risultato.get_msg()}", "red"))
        return
    if not singoli:
        print(IO.color("  Nessun singolo in attesa di accoppiamento.", "green"))
        return

    n = len(singoli)
    print(IO.color(f"  {n} giocatore/i in attesa:\n", "yellow"))
    for g in singoli:
        print(IO.color(f"    •  {g['nome_g']} {g['cognome_g']} «{g['soprannome_g']}»", "white"))

    if n < 2:
        print(IO.color("\n  Serve almeno un secondo singolo per formare una coppia.", "yellow"))
        _gestisci_singolo_spaiato(singoli[0], nome_torneo)
        return

    avviso = " (attenzione: numero dispari — uno resterà spaiato)" if n % 2 else ""
    if IO.yes_or_no_input(
        IO.color(f"\n  Procedere con l'accoppiamento casuale{avviso}? (si/no): ", "yellow"),
        IO.color("  Rispondi solo 'si' o 'no': ", "red"),
    ) == "no":
        print(IO.color("  Accoppiamento annullato.", "yellow"))
        return

    pool = list(singoli)
    random.shuffle(pool)
    coppie_create = 0

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"  ✖ Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    try:
        for i in range(0, len(pool) - 1, 2):
            g1 = pool[i]
            g2 = pool[i + 1]
            nome_coppia = f"{g1['soprannome_g']} & {g2['soprannome_g']}"

            # Sposta g2 nella squadra di g1
            db.execute_alt(
                "UPDATE partecipante SET id_squadra = %s WHERE id_partecipante = %s",
                params=(g1["id_squadra"], g2["id_partecipante"])
            )
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            # Rinomina la squadra di g1
            db.execute_alt(
                "UPDATE squadra SET nome = %s WHERE id_squadra = %s",
                params=(nome_coppia, g1["id_squadra"])
            )
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            # Elimina la vecchia squadra di g2 (ora vuota)
            db.delete("squadra", condizione="id_squadra = %s", params=(g2["id_squadra"],))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            print(IO.color(
                f"  ✓  {g1['nome_g']} {g1['cognome_g']} «{g1['soprannome_g']}»"
                f"  ↔  {g2['nome_g']} {g2['cognome_g']} «{g2['soprannome_g']}»"
                f"  →  Coppia \"{nome_coppia}\"",
                "green"
            ))
            coppie_create += 1

        db.commit_transaction()

    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"  ✖ Errore durante l'accoppiamento: {e}", "red"))
        print(IO.color("  Rollback eseguito. Nessuna modifica salvata.", "red"))
        return

    if len(pool) % 2:
        g_rest = pool[-1]
        print(IO.color(
            f"\n  ⚠  {g_rest['nome_g']} {g_rest['cognome_g']} «{g_rest['soprannome_g']}» "
            "è rimasto senza compagno.",
            "yellow"
        ))
        _gestisci_singolo_spaiato(g_rest, nome_torneo)

    print(IO.color(f"\n  ✓  {coppie_create} coppia/e formata/e.", "green"))


def _gestisci_singolo_spaiato(g: dict, nome_torneo: str):
    """Lascia in attesa oppure rimuove dal torneo un giocatore rimasto senza compagno."""
    print(IO.color(
        f"\n  Puoi lasciare {g['nome_g']} {g['cognome_g']} «{g['soprannome_g']}» in attesa\n"
        "  oppure rimuoverlo dal torneo.",
        "white"
    ))

    scelta = input_scelta_veloce(
        ["attesa", "rimuovi"],
        "  Cosa vuoi fare?",
        default="attesa",
    )

    if scelta == "attesa":
        print(IO.color(
            f"  ✓ {g['nome_g']} {g['cognome_g']} rimane in attesa di un compagno.", "cyan"
        ))
        return

    conferma = input(IO.color(
        f"\n  Confermi la rimozione di {g['nome_g']} {g['cognome_g']}"
        f" dal torneo '{nome_torneo}'? (s/N) [INVIO = NO]: ",
        "red"
    )).strip().lower()
    if conferma != "s":
        print(IO.color("  Rimozione annullata. Rimane in attesa.", "yellow"))
        return

    # ON DELETE CASCADE su partecipante.id_squadra:
    # eliminare la squadra rimuove anche il partecipante collegato.
    db.delete("squadra", condizione="id_squadra = %s", params=(g["id_squadra"],))
    if not db.risultato.successo:
        print(IO.color(f"  ✖ Errore nella rimozione: {db.risultato.get_msg()}", "red"))
        return

    print(IO.color(f"  ✓ {g['nome_g']} {g['cognome_g']} rimosso dal torneo.", "green"))


# ══════════════════════════════════════════════════════════════
#  VISUALIZZAZIONE DATI
# ══════════════════════════════════════════════════════════════

def _elimina_partecipante(nome_torneo: str, is_singolo: bool):
    print(IO.color("\n── Elimina partecipante ──", "cyan"))

    if is_singolo:
        righe = db.execute_select("""
            SELECT s.id_squadra, p.nome, p.cognome, p.soprannome
            FROM   squadra s
            JOIN   partecipante p ON p.id_squadra = s.id_squadra
            WHERE  s.nome_torneo = %s
            ORDER BY p.cognome, p.nome
        """, params=(nome_torneo,))
    else:
        righe = db.execute_select("""
            SELECT s.id_squadra, s.nome AS nome_sq,
                   GROUP_CONCAT(
                       CONCAT(p.nome, ' ', p.cognome)
                       ORDER BY p.cognome SEPARATOR ' / '
                   ) AS giocatori,
                   COUNT(p.id_partecipante) AS n_membri
            FROM   squadra s
            JOIN   partecipante p ON p.id_squadra = s.id_squadra
            WHERE  s.nome_torneo = %s
            GROUP BY s.id_squadra, s.nome
            ORDER BY s.nome
        """, params=(nome_torneo,))

    if not db.risultato.successo:
        print(IO.color(f"  Errore DB: {db.risultato.get_msg()}", "red"))
        return
    if not righe:
        entita = "giocatori" if is_singolo else "squadre"
        print(IO.color(f"  Nessun/a {entita} iscritto/a.", "yellow"))
        return

    print()
    for i, r in enumerate(righe, 1):
        if is_singolo:
            sopr = f" «{r['soprannome']}»" if r.get("soprannome") else ""
            print(IO.color(f"  {i:>2}. {r['nome']} {r['cognome']}{sopr}", "white"))
        else:
            stato = "" if r["n_membri"] == 2 else IO.color("  [singolo in attesa]", "yellow")
            print(IO.color(f"  {i:>2}. {r['nome_sq']:<22} {r['giocatori']}{stato}", "white"))
    print()

    raw = input(IO.color("  Numero da eliminare (INVIO = annulla): ", "yellow")).strip()
    if not raw:
        print(IO.color("  Annullato.", "yellow"))
        return
    try:
        idx = int(raw) - 1
        if idx < 0 or idx >= len(righe):
            raise ValueError
    except ValueError:
        print(IO.color("  Numero non valido.", "red"))
        return

    riga = righe[idx]
    id_squadra = riga["id_squadra"]

    if is_singolo:
        descrizione = f"{riga['nome']} {riga['cognome']}"
    else:
        descrizione = f"{riga['nome_sq']} ({riga['giocatori']})"

    conferma = input(IO.color(
        f"\n  Eliminare '{descrizione}' dal torneo? (s/N): ", "red"
    )).strip().lower()
    if conferma != "s":
        print(IO.color("  Annullato.", "yellow"))
        return

    db.start_transaction()
    if not db.risultato.successo:
        print(IO.color(f"  Errore avvio transazione: {db.risultato.get_msg()}", "red"))
        return

    try:
        db.execute_alt(
            "DELETE FROM partecipante WHERE id_squadra = %s", params=(id_squadra,)
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.execute_alt(
            "DELETE FROM squadra WHERE id_squadra = %s", params=(id_squadra,)
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        print(IO.color(f"\n  ✓ '{descrizione}' eliminato dal torneo.", "green"))
    except Exception as e:
        db.rollback_transaction()
        print(IO.color(f"\n  Errore durante l'eliminazione: {e}. Rollback eseguito.", "red"))


def _stampa_iscritti_sintetica(nome_torneo: str, is_singolo: bool):
    """Lista compatta degli iscritti mostrata prima di ogni nuovo inserimento."""
    if is_singolo:
        righe = db.execute_select("""
            SELECT p.nome, p.cognome, p.soprannome
            FROM   partecipante p
            JOIN   squadra s ON s.id_squadra = p.id_squadra
            WHERE  s.nome_torneo = %s
            ORDER BY p.cognome, p.nome
        """, params=(nome_torneo,))

        if not db.risultato.successo or not righe:
            print(IO.color("  (Nessun giocatore iscritto ancora)\n", "yellow"))
            return

        print(IO.color(f"  ── Giocatori iscritti ({len(righe)}) ──", "cyan"))
        for r in righe:
            sopr = f" «{r['soprannome']}»" if r.get("soprannome") else ""
            print(IO.color(f"    • {r['nome']} {r['cognome']}{sopr}", "white"))
        print()

    else:
        coppie = db.execute_select("""
            SELECT s.id_squadra, s.nome AS nome_sq,
                   GROUP_CONCAT(
                       CONCAT(p.nome, ' ', p.cognome, ' «', IFNULL(p.soprannome, ''), '»')
                       ORDER BY p.cognome SEPARATOR ' / '
                   ) AS giocatori,
                   COUNT(p.id_partecipante) AS n_membri
            FROM   squadra s
            JOIN   partecipante p ON p.id_squadra = s.id_squadra
            WHERE  s.nome_torneo = %s
            GROUP BY s.id_squadra, s.nome
            ORDER BY n_membri DESC, s.nome
        """, params=(nome_torneo,))

        if not db.risultato.successo or not coppie:
            print(IO.color("  (Nessuna coppia iscritta ancora)\n", "yellow"))
            return

        complete  = [c for c in coppie if c["n_membri"] == 2]
        in_attesa = [c for c in coppie if c["n_membri"] == 1]

        if complete:
            print(IO.color(f"  ── Coppie complete ({len(complete)}) ──", "cyan"))
            for c in complete:
                print(IO.color(f"    • {c['nome_sq']:<22} {c['giocatori']}", "white"))
        if in_attesa:
            print(IO.color(f"  ── Singoli in attesa ({len(in_attesa)}) ──", "yellow"))
            for c in in_attesa:
                print(IO.color(f"    ⏳ {c['giocatori']}", "yellow"))
        print()


def stampa_partecipanti_torneo(nome_torneo: str, is_singolo: bool):
    """Tabella formattata degli iscritti al torneo, raggruppata per squadra."""
    if is_singolo:
        righe = db.execute_select("""
            SELECT p.id_partecipante,
                   p.nome, p.cognome,
                   IFNULL(p.soprannome, '—') AS soprannome
            FROM   partecipante p
            JOIN   squadra s ON s.id_squadra = p.id_squadra
            WHERE  s.nome_torneo = %s
            ORDER BY p.cognome, p.nome
        """, params=(nome_torneo,))
        headers = ["ID", "Cognome, Nome", "Soprannome"]
    else:
        righe = db.execute_select("""
            SELECT p.id_partecipante,
                   p.nome, p.cognome,
                   IFNULL(p.soprannome, '—') AS soprannome,
                   s.id_squadra,
                   s.nome                     AS coppia,
                   IFNULL(s.girone, '—')      AS girone
            FROM   partecipante p
            JOIN   squadra s ON s.id_squadra = p.id_squadra
            WHERE  s.nome_torneo = %s
            ORDER BY s.girone ASC, s.id_squadra ASC, p.cognome ASC
        """, params=(nome_torneo,))
        headers = ["ID", "Coppia", "Girone", "Cognome, Nome", "Soprannome"]

    if not db.risultato.successo or righe is None:
        print_errore()
        return

    print(IO.color(f"\n  ╔══ Iscritti: {nome_torneo} ══╗", "cyan"))

    if not righe:
        print(IO.color("  Nessun partecipante trovato.\n", "yellow"))
        return

    def _valori(r) -> list[str]:
        base = [
            str(r["id_partecipante"]),
            f"{r['cognome'].upper()}, {r['nome'].capitalize()}",
            r["soprannome"],
        ]
        if not is_singolo:
            base.insert(1, r["coppia"])
            base.insert(2, r["girone"])
        return base

    dati      = [_valori(r) for r in righe]
    larghezze = [
        max(len(headers[i]), max((len(row[i]) for row in dati), default=0))
        for i in range(len(headers))
    ]

    def fmt(valori, color=None) -> str:
        testo = "  " + "  ".join(v.ljust(w) for v, w in zip(valori, larghezze))
        return IO.color(testo, color) if color else testo

    sep = "  " + "─" * (sum(larghezze) + 2 * (len(larghezze) - 1))

    print(IO.color(fmt(headers), "magenta"))
    print(IO.color(sep, "blue"))

    id_squadra_prec = None
    for r, vals in zip(righe, dati):
        if not is_singolo:
            id_sq = r["id_squadra"]
            if id_sq != id_squadra_prec:
                if id_squadra_prec is not None:
                    print(IO.color(sep, "blue"))
                id_squadra_prec = id_sq
            else:
                # Nascondi coppia e girone per la seconda riga della stessa squadra
                vals = [vals[0], "", "", vals[3], vals[4]]
        print(fmt(vals))

    print(IO.color(sep, "blue"))
    n = len(righe)
    print(IO.color(f"  Totale: {n} partecipante{'i' if n != 1 else ''}\n", "cyan"))


def _stampa_coppie_torneo(nome_torneo: str):
    """Elenco coppie raggruppate per girone con indicazione dei singoli in attesa."""
    squadre = db.execute_select("""
        SELECT s.id_squadra, s.nome, s.squalificato, s.girone,
               COUNT(p.id_partecipante) AS n_membri
        FROM   squadra s
        LEFT JOIN partecipante p ON p.id_squadra = s.id_squadra
        WHERE  s.nome_torneo = %s
        GROUP BY s.id_squadra, s.nome, s.squalificato, s.girone
        ORDER BY s.girone ASC, n_membri DESC, s.nome ASC
    """, params=(nome_torneo,))

    if not db.risultato.successo or not squadre:
        print(IO.color("  Nessuna squadra registrata per questo torneo.\n", "yellow"))
        return

    complete  = [s for s in squadre if s["n_membri"] == 2]
    in_attesa = [s for s in squadre if s["n_membri"] == 1]

    print(IO.color(f"\n── Situazione Coppie: {nome_torneo} ──", "cyan"))
    print(IO.color(
        f"  {len(complete)} coppia/e complete  │  {len(in_attesa)} singolo/i in attesa\n",
        "white"
    ))

    if complete:
        girone_prec = "__NESSUNO__"
        for sq in complete:
            girone_curr = sq.get("girone") or ""

            if girone_curr != girone_prec:
                if girone_curr:
                    print(IO.color(f"\n  ╔══ GIRONE {girone_curr} ══╗", "cyan"))
                else:
                    print(IO.color("\n  ╔══ Gironi non ancora assegnati ══╗", "yellow"))
                girone_prec = girone_curr

            squalif    = IO.color("  [SQ]", "red") if sq["squalificato"] else ""
            girone_tag = IO.color(f" [G{girone_curr}]", "cyan") if girone_curr else ""
            print(IO.color(
                f"  ┌── {sq['nome']}{girone_tag}{squalif}  (ID {sq['id_squadra']})", "cyan"
            ))

            membri = db.execute_select("""
                SELECT p.nome, p.cognome, IFNULL(p.soprannome, '—') AS soprannome
                FROM   partecipante p
                WHERE  p.id_squadra = %s
            """, params=(sq["id_squadra"],))

            if not db.risultato.successo or not membri:
                print(IO.color("  │   (errore nel recupero membri)", "red"))
            else:
                for m in membri:
                    print(IO.color(
                        f"  │   {m['nome']} {m['cognome']} «{m['soprannome']}»", "white"
                    ))
            print(IO.color("  └" + "─" * 46, "cyan"))

    if in_attesa:
        print(IO.color(f"\n  ╔══ Singoli in attesa di compagno ══╗", "yellow"))
        for sq in in_attesa:
            p_rows = db.execute_select(
                "SELECT nome, cognome, soprannome FROM partecipante WHERE id_squadra = %s",
                params=(sq["id_squadra"],)
            )
            if p_rows:
                g = p_rows[0]
                print(IO.color(
                    f"  ⏳  {g['nome']} {g['cognome']} «{g['soprannome']}»", "yellow"
                ))
    print()


def print_all_partecipanti():
    """Elenco di tutti i giocatori nel sistema, raggruppati per torneo."""
    print(IO.color("\n" + "═" * 60, "cyan"))
    print(IO.color("  👥  Tutti i giocatori registrati nel sistema", "cyan"))
    print(IO.color("═" * 60, "cyan"))

    righe = db.execute_select("""
        SELECT p.id_partecipante,
               p.nome, p.cognome,
               IFNULL(p.soprannome, '—') AS soprannome,
               s.nome        AS squadra,
               s.nome_torneo AS torneo
        FROM   partecipante p
        JOIN   squadra s ON s.id_squadra = p.id_squadra
        ORDER BY s.nome_torneo, p.cognome, p.nome
    """)

    if not db.risultato.successo or not righe:
        print(IO.color("  Nessun giocatore nel sistema.\n", "yellow"))
        return

    print(IO.color(f"  Totale: {len(righe)} giocatore/i registrati\n", "white"))

    headers = ["ID", "Cognome, Nome", "Soprannome", "Squadra", "Torneo"]
    dati    = [
        [
            str(r["id_partecipante"]),
            f"{r['cognome'].upper()}, {r['nome'].capitalize()}",
            r["soprannome"],
            r["squadra"],
            r["torneo"],
        ]
        for r in righe
    ]
    larghezze = [
        max(len(headers[i]), max((len(row[i]) for row in dati), default=0))
        for i in range(len(headers))
    ]

    def fmt(valori, color=None) -> str:
        testo = "  " + "  ".join(v.ljust(w) for v, w in zip(valori, larghezze))
        return IO.color(testo, color) if color else testo

    sep = "  " + "─" * (sum(larghezze) + 2 * (len(larghezze) - 1))

    print(IO.color(fmt(headers), "magenta"))
    print(IO.color(sep, "blue"))

    torneo_prec = None
    for r, vals in zip(righe, dati):
        if r["torneo"] != torneo_prec:
            if torneo_prec is not None:
                print(IO.color(sep, "blue"))
            torneo_prec = r["torneo"]
        print(fmt(vals))

    print(IO.color(sep, "blue"))
    print()


# ══════════════════════════════════════════════════════════════
#  UTILITÀ
# ══════════════════════════════════════════════════════════════

def _pausa():
    input(IO.color("\n  [ Premi INVIO per continuare... ]", "cyan"))