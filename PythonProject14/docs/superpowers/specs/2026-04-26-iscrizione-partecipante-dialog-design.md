# Design: Collegamento Iscrizione → partecipante_dialog.ui

**Data:** 2026-04-26  
**File:** `partecipanti_widget.py`  
**UI:** `claude/partecipante_dialog.ui`

## Problema

`_open_partecipante_dialog` ha 4 bug:
1. Path typo `"claude/participante_dialog.ui"` (manca `e`) → load sempre fallisce
2. `btn_save`/`btn_cancel` non connessi → `dialog.exec_()` non risolve mai
3. Campi indirizzo presenti nel dialog ma non letti né salvati
4. `_iscrivi_singolo_in_attesa_dialog` usa `QInputDialog` invece del dialog UI

## Approccio: Fix minimo (A)

Fix mirati su `_open_partecipante_dialog` + flussi iscrizione.

## Design

### `_open_partecipante_dialog(nome_torneo) → dict | None`

1. Path corretto: `"claude/partecipante_dialog.ui"`
2. Connetti segnali: `btn_save.clicked → dialog.accept()`, `btn_cancel.clicked → dialog.reject()`
3. Leggi campi per nome: `entry_nome`, `entry_cognome`, `entry_soprannome` (obbligatori)
4. Leggi campi indirizzo: `entry_via`, `entry_civico`, `entry_cap`, `entry_citta` (opzionali)
5. Logica indirizzo:
   - tutti vuoti → `id_indirizzo = None`
   - almeno uno pieno → valida tutti; incompleto → warning, `return None`
   - tutti pieni → `INSERT indirizzo` → ottieni `id_indirizzo`
6. Ritorna `{nome, cognome, soprannome, id_indirizzo}`

### Flussi iscrizione (tutti e 3)

Ordine transazione:
1. `INSERT indirizzo` se presente → `id_indirizzo`
2. `INSERT squadra` → `id_sq`
3. `INSERT partecipante(nome, cognome, soprannome, id_squadra, id_indirizzo)`

`_iscrivi_singolo_in_attesa_dialog` → rimuovi `QInputDialog`, usa `_open_partecipante_dialog`.

## Campi DB

- `indirizzo`: via, numero_civico, cap, citta (tutti NOT NULL → tutto-o-niente)
- `partecipante.id_indirizzo`: nullable FK

## Nessuna modifica a

- `partecipanti.py` (CLI — invariato)
- `.ui` files
- Schema DB
