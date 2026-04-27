# Iscrizione → partecipante_dialog.ui Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collegare il flusso iscrizione partecipanti in `partecipanti_widget.py` con `claude/partecipante_dialog.ui`, salvando tutti i dati (anagrafica + indirizzo opzionale) in modo atomico.

**Architecture:** `_open_partecipante_dialog` torna dati raw (inclusi campi indirizzo come stringhe). Ogni flusso di iscrizione inserisce indirizzo + squadra + partecipante in un'unica transazione, evitando righe orfane se un INSERT fallisce.

**Tech Stack:** PyQt5, `uic.loadUi`, MySQL via `db` (config.py), transazioni con `db.start_transaction()`/`db.commit_transaction()`/`db.rollback_transaction()`

---

## File Map

| File | Azione |
|------|--------|
| `partecipanti_widget.py` | Modifica: `_open_partecipante_dialog`, `_iscrivi_singolo_dialog`, `_iscrivi_coppia_dialog`, `_iscrivi_singolo_in_attesa_dialog` |
| `claude/partecipante_dialog.ui` | Solo lettura (nessuna modifica) |

Schema rilevante:
```sql
indirizzo(id_indirizzo PK AUTO_INCREMENT, via NOT NULL, numero_civico NOT NULL, cap NOT NULL, citta NOT NULL)
partecipante(id_partecipante PK, nome, cognome, soprannome, id_squadra FK NOT NULL, id_indirizzo FK nullable)
```

`db.insert(tabella, colonne, valori)` ritorna l'`id` auto-generated (o `None` se fallisce).  
`db.risultato.successo` indica esito dell'ultima operazione.

---

## Task 1: Fix `_open_partecipante_dialog` — solo raccolta dati

**Files:**
- Modify: `partecipanti_widget.py:499-562`

`_open_partecipante_dialog` ora ritorna solo dati raw (nessun INSERT). Gli INSERT stanno nei flussi.

- [ ] **Step 1: Sostituisci l'intero metodo `_open_partecipante_dialog`**

Individua riga 499 (`def _open_partecipante_dialog`) fino a riga 562 e sostituisci con:

```python
def _open_partecipante_dialog(self, nome_torneo: str) -> dict | None:
    """Apri partecipante_dialog.ui.
    Ritorna dict {nome, cognome, soprannome, via, civico, cap, citta, ha_indirizzo}
    oppure None se annullato o dati invalidi.
    """
    from PyQt5.QtWidgets import QPushButton
    dialog = QDialog(self)
    try:
        uic.loadUi("claude/partecipante_dialog.ui", dialog)
    except Exception as e:
        QMessageBox.critical(self, "Errore UI", f"Impossibile caricare la finestra: {e}")
        return None

    for btn in dialog.findChildren(QPushButton):
        if btn.objectName() == "btn_save":
            btn.clicked.connect(dialog.accept)
        elif btn.objectName() == "btn_cancel":
            btn.clicked.connect(dialog.reject)

    if dialog.exec_() != QDialog.Accepted:
        return None

    def _get(obj_name: str) -> str:
        w = dialog.findChild(QLineEdit, obj_name)
        return w.text().strip() if w else ""

    nome       = _get("entry_nome")
    cognome    = _get("entry_cognome")
    soprannome = _get("entry_soprannome")

    if not nome or not cognome or not soprannome:
        QMessageBox.warning(self, "Dati obbligatori", "Nome, Cognome e Soprannome sono obbligatori.")
        return None

    via    = _get("entry_via")
    civico = _get("entry_civico")
    cap    = _get("entry_cap")
    citta  = _get("entry_citta")

    campi_addr = [via, civico, cap, citta]
    if any(campi_addr) and not all(campi_addr):
        QMessageBox.warning(
            self, "Indirizzo incompleto",
            "Se inserisci l'indirizzo, compila tutti i campi (Via, N° Civico, CAP, Città)."
        )
        return None

    dup = db.select_as_dict(
        "partecipante AS p",
        colonne=["p.id_partecipante"],
        join="JOIN squadra s ON s.id_squadra = p.id_squadra",
        condizione="s.nome_torneo = %s AND LOWER(p.soprannome) = LOWER(%s)",
        params=(nome_torneo, soprannome),
    )
    if not db.risultato.successo:
        QMessageBox.critical(self, "Errore DB", db.risultato.get_msg())
        return None
    if dup:
        QMessageBox.warning(self, "Duplicato", f"Il soprannome '{soprannome}' è già in uso in questo torneo.")
        return None

    return {
        "nome": nome, "cognome": cognome, "soprannome": soprannome,
        "via": via, "civico": civico, "cap": cap, "citta": citta,
        "ha_indirizzo": all(campi_addr),
    }
```

- [ ] **Step 2: Verifica manuale — dialog si apre e chiude**

Avvia `python main.py` → opzione 1 (GUI).  
Partecipanti → seleziona torneo singolo → clicca "Iscrivi Singolo".  
Verifica: si apre `partecipante_dialog.ui`. Clicca "Annulla" → finestra chiude senza errori.

---

## Task 2: Aggiorna `_iscrivi_singolo_dialog`

**Files:**
- Modify: `partecipanti_widget.py:363-402`

- [ ] **Step 1: Sostituisci `_iscrivi_singolo_dialog`**

```python
def _iscrivi_singolo_dialog(self, nome_torneo: str):
    dati = self._open_partecipante_dialog(nome_torneo)
    if dati is None:
        return

    db.start_transaction()
    try:
        id_indirizzo = None
        if dati["ha_indirizzo"]:
            id_indirizzo = db.insert(
                "indirizzo",
                ["via", "numero_civico", "cap", "citta"],
                [dati["via"], dati["civico"], dati["cap"], dati["citta"]],
            )
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [dati["soprannome"], nome_torneo])
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.insert(
            "partecipante",
            ["nome", "cognome", "soprannome", "id_squadra", "id_indirizzo"],
            [dati["nome"], dati["cognome"], dati["soprannome"], id_sq, id_indirizzo],
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        QMessageBox.information(
            self, "Iscrizione OK",
            f"Iscritto {dati['nome']} {dati['cognome']} «{dati['soprannome']}»!"
        )
        self._refresh_preservando_selezione()
    except Exception as e:
        db.rollback_transaction()
        QMessageBox.critical(self, "Errore iscrizione", str(e))
```

- [ ] **Step 2: Verifica manuale — iscrizione singolo senza indirizzo**

Torneo singolo → "Iscrivi" → compila solo nome/cognome/soprannome → Salva.  
Verifica: partecipante appare in lista, `id_indirizzo = NULL` in DB.

- [ ] **Step 3: Verifica manuale — iscrizione singolo con indirizzo**

Torneo singolo → "Iscrivi" → compila tutti i campi incluso indirizzo → Salva.  
Verifica: partecipante appare in lista, riga in `indirizzo` presente in DB.

---

## Task 3: Aggiorna `_iscrivi_coppia_dialog`

**Files:**
- Modify: `partecipanti_widget.py:404-449`

- [ ] **Step 1: Sostituisci `_iscrivi_coppia_dialog`**

```python
def _iscrivi_coppia_dialog(self, nome_torneo: str):
    nome_coppia, ok = QInputDialog.getText(self, "Iscrizione Coppia", "Nome della coppia:")
    if not ok or not nome_coppia.strip():
        QMessageBox.information(self, "Iscrizione", "Iscrizione annullata.")
        return
    nome_coppia = nome_coppia.strip()
    if _squadra_esiste(nome_coppia, nome_torneo):
        QMessageBox.warning(self, "Duplicato", f"Esiste già una coppia chiamata '{nome_coppia}'.")
        return

    g1 = self._open_partecipante_dialog(nome_torneo)
    if g1 is None:
        return
    g2 = self._open_partecipante_dialog(nome_torneo)
    if g2 is None:
        return

    db.start_transaction()
    try:
        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [nome_coppia, nome_torneo])
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        for g in (g1, g2):
            id_indirizzo = None
            if g["ha_indirizzo"]:
                id_indirizzo = db.insert(
                    "indirizzo",
                    ["via", "numero_civico", "cap", "citta"],
                    [g["via"], g["civico"], g["cap"], g["citta"]],
                )
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
            db.insert(
                "partecipante",
                ["nome", "cognome", "soprannome", "id_squadra", "id_indirizzo"],
                [g["nome"], g["cognome"], g["soprannome"], id_sq, id_indirizzo],
            )
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        noms = (
            f"{g1['nome']} {g1['cognome']} «{g1['soprannome']}» e "
            f"{g2['nome']} {g2['cognome']} «{g2['soprannome']}»"
        )
        QMessageBox.information(self, "Iscrizione OK", f"Coppia '{nome_coppia}' iscritta!\nComponenti: {noms}")
        self._refresh_preservando_selezione()
    except Exception as e:
        db.rollback_transaction()
        QMessageBox.critical(self, "Errore iscrizione", str(e))
```

- [ ] **Step 2: Verifica manuale — iscrizione coppia**

Torneo coppie → "Iscrivi" → scegli "coppia" → nome coppia + 2 giocatori via dialog.  
Verifica: coppia appare in tab Coppie con entrambi i membri.

---

## Task 4: Aggiorna `_iscrivi_singolo_in_attesa_dialog`

**Files:**
- Modify: `partecipanti_widget.py:451-497`

- [ ] **Step 1: Sostituisci `_iscrivi_singolo_in_attesa_dialog`**

```python
def _iscrivi_singolo_in_attesa_dialog(self, nome_torneo: str):
    """Iscrizione singolo in attesa di compagno. Nome squadra = soprannome."""
    dati = self._open_partecipante_dialog(nome_torneo)
    if dati is None:
        return

    if _squadra_esiste(dati["soprannome"], nome_torneo):
        QMessageBox.warning(self, "Duplicato", f"Il soprannome '{dati['soprannome']}' è già in uso.")
        return

    db.start_transaction()
    try:
        id_indirizzo = None
        if dati["ha_indirizzo"]:
            id_indirizzo = db.insert(
                "indirizzo",
                ["via", "numero_civico", "cap", "citta"],
                [dati["via"], dati["civico"], dati["cap"], dati["citta"]],
            )
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [dati["soprannome"], nome_torneo])
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.insert(
            "partecipante",
            ["nome", "cognome", "soprannome", "id_squadra", "id_indirizzo"],
            [dati["nome"], dati["cognome"], dati["soprannome"], id_sq, id_indirizzo],
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())

        db.commit_transaction()
        QMessageBox.information(
            self, "Iscrizione OK",
            f"Iscritto {dati['nome']} {dati['cognome']} «{dati['soprannome']}» in attesa di compagno."
        )
        self._refresh_preservando_selezione()
    except Exception as e:
        db.rollback_transaction()
        QMessageBox.critical(self, "Errore iscrizione", str(e))
```

- [ ] **Step 2: Verifica manuale — singolo in attesa**

Torneo coppie → "Iscrivi" → scegli "singolo" → compila dialog → Salva.  
Verifica: compare in tab Coppie come singolo in attesa.

---

## Task 5: Commit finale

- [ ] **Step 1: Commit**

```bash
git add partecipanti_widget.py
git commit -m "feat: wire partecipante_dialog.ui to iscrizione flow, save address data"
```
