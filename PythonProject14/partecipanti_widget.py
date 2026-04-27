import os
from typing import Optional

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QLabel, QMessageBox, QDialog, QTreeWidgetItem,
    QAbstractItemView, QSizePolicy, QInputDialog, QLineEdit,
    QVBoxLayout, QFormLayout, QDialogButtonBox, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import db
from partecipanti import (
    _conta_iscritti,
    _gironi_assegnati,
    _conta_singoli_in_attesa,
    _squadra_esiste
)

UI_PATH = "claude/partecipanti_widget.ui"

_LABEL_ISCRITTI_STYLE = (
    "color: #7f8c8d; font-family: Helvetica; font-size: 9pt; padding-left: 4px;"
)


class PartecipantiWidget(QWidget):
    """
    Pannello Partecipanti — carica partecipanti_widget.ui.
    Gestisce visualizzazione singoli/coppie, filtri, label iscritti/limite.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            print(f"[PartecipantiWidget] Errore caricamento UI: {e}")
            return

        self._ultimo_torneo: Optional[str] = None

        # ── label iscritti aggiunta via codice ────────────────────────────
        self._lbl_iscritti = QLabel("Iscritti: – / –")
        self._lbl_iscritti.setStyleSheet(_LABEL_ISCRITTI_STYLE)
        frame_filter = getattr(self, "frame_filter", None)
        if frame_filter and frame_filter.layout():
            frame_filter.layout().addWidget(self._lbl_iscritti)

        # ── sorting ───────────────────────────────────────────────────────
        for tree in [
            getattr(self, "participants_tree", None),
            getattr(self, "coppie_tree", None),
        ]:
            if tree is not None:
                tree.setSortingEnabled(True)
                tree.setAlternatingRowColors(True)

        # ── segnali ──────────────────────────────────────────────────────
        combo_s = getattr(self, "combo_tornei_singoli", None)
        combo_c = getattr(self, "combo_tornei_coppie", None)
        if combo_s:
            combo_s.currentIndexChanged.connect(self._on_filtro_singoli_cambiato)
        if combo_c:
            combo_c.currentIndexChanged.connect(self._on_filtro_coppie_cambiato)

        entry_nome    = getattr(self, "entry_filter_nome", None)
        entry_cognome = getattr(self, "entry_filter_cognome", None)
        if entry_nome:
            entry_nome.textChanged.connect(lambda _: self._applica_filtri_live())
        if entry_cognome:
            entry_cognome.textChanged.connect(lambda _: self._applica_filtri_live())

        combo_ordina = getattr(self, "combo_ordina_per", None)
        if combo_ordina:
            combo_ordina.currentIndexChanged.connect(self._on_ordine_cambiato)

        btn_singoli = getattr(self, "btn_tab_singoli", None)
        btn_coppie  = getattr(self, "btn_tab_coppie", None)
        if btn_singoli:
            btn_singoli.clicked.connect(self._switch_singoli)
        if btn_coppie:
            btn_coppie.clicked.connect(self._switch_coppie)

        btn_toggle = getattr(self, "btn_toggle_coppie", None)
        if btn_toggle:
            btn_toggle.clicked.connect(self._toggle_coppie)

        # CRUD — stub (implementazione futura)
        btn_edit           = getattr(self, "btn_edit", None)
        btn_iscrivi_s      = getattr(self, "btn_iscrivi_singolo", None)
        btn_elim_singolo   = getattr(self, "btn_elimina_singolo", None)
        btn_mod_coppia     = getattr(self, "btn_modifica_coppia", None)
        btn_elim_coppia    = getattr(self, "btn_elimina_coppia", None)
        btn_abbina         = getattr(self, "btn_abbina_singoli", None)
        btn_iscrivi_att    = getattr(self, "btn_iscrivi_singolo_attesa", None)
        btn_iscrivi_coppia = getattr(self, "btn_iscrivi_coppia", None)

        if btn_edit:
            btn_edit.clicked.connect(self._modifica_partecipante)
        if btn_elim_singolo:
            btn_elim_singolo.clicked.connect(self._elimina_singolo)

        tree_singoli = getattr(self, "participants_tree", None)
        if tree_singoli:
            tree_singoli.itemDoubleClicked.connect(lambda item, col: self._modifica_partecipante())
        if btn_iscrivi_s:
            btn_iscrivi_s.clicked.connect(lambda: self._iscrivi_singolo())
        if btn_mod_coppia:
            btn_mod_coppia.clicked.connect(self._modifica_coppia)
        if btn_elim_coppia:
            btn_elim_coppia.clicked.connect(self._elimina_coppia)
        if btn_abbina:
            btn_abbina.clicked.connect(self._abbina_singoli)
        if btn_iscrivi_att:
            btn_iscrivi_att.clicked.connect(self._iscrivi_singolo_in_attesa)
        if btn_iscrivi_coppia:
            btn_iscrivi_coppia.clicked.connect(lambda: self._iscrivi_coppia())

        # carica dati iniziali
        self._carica_combo_tornei()
        self._aggiorna_tabs_per_torneo()
        self._carica_dati()
        self._aggiorna_visibilita_btn_abbina()

    # ──────────────────────────────────────────────────────────────────────
    #  NAVIGAZIONE TAB
    # ──────────────────────────────────────────────────────────────────────

    def _switch_singoli(self):
        stacked = getattr(self, "stacked_partecipanti", None)
        if stacked:
            stacked.setCurrentIndex(0)
        btn_s = getattr(self, "btn_tab_singoli", None)
        btn_c = getattr(self, "btn_tab_coppie", None)
        if btn_s: btn_s.setChecked(True)
        if btn_c: btn_c.setChecked(False)

    def _switch_coppie(self):
        stacked = getattr(self, "stacked_partecipanti", None)
        if stacked:
            stacked.setCurrentIndex(1)
        btn_s = getattr(self, "btn_tab_singoli", None)
        btn_c = getattr(self, "btn_tab_coppie", None)
        if btn_s: btn_s.setChecked(False)
        if btn_c: btn_c.setChecked(True)
        self._carica_coppie()

    def _tipo_torneo_corrente(self) -> Optional[int]:
        nome = self._torneo_corrente()
        if not nome:
            return None
        res = db.select_as_dict(
            "torneo",
            colonne=["singolo_doppio"],
            condizione="nome = %s",
            params=(nome,),
        )
        if db.risultato.successo and res:
            return int(res[0]["singolo_doppio"])
        return None

    def _aggiorna_tabs_per_torneo(self):
        tipo = self._tipo_torneo_corrente()
        btn_s = getattr(self, "btn_tab_singoli", None)
        btn_c = getattr(self, "btn_tab_coppie", None)
        stacked = getattr(self, "stacked_partecipanti", None)
        if btn_s is None or btn_c is None or stacked is None:
            return

        # entrambe le tab sono sempre visibili e accessibili
        btn_s.setVisible(True)
        btn_c.setVisible(True)
        btn_s.setEnabled(True)
        btn_c.setEnabled(True)

        # porta al tab di default coerente col tipo di torneo selezionato
        if tipo == 0:
            self._switch_coppie()
        elif not btn_s.isChecked() and not btn_c.isChecked():
            self._switch_singoli()

    def _toggle_coppie(self):
        tree = getattr(self, "coppie_tree", None)
        if tree is None:
            return
        if tree.topLevelItemCount() == 0:
            return
        primo = tree.topLevelItem(0)
        espandi = not primo.isExpanded()
        for i in range(tree.topLevelItemCount()):
            tree.topLevelItem(i).setExpanded(espandi)

    # ──────────────────────────────────────────────────────────────────────
    #  COMBO TORNEI
    # ──────────────────────────────────────────────────────────────────────

    def _carica_combo_tornei(self):
        lista = db.select_as_dict("torneo") or []
        combo_s = getattr(self, "combo_tornei_singoli", None)
        combo_c = getattr(self, "combo_tornei_coppie", None)

        for combo, placeholder, tipo in (
            (combo_s, "Tutti (singoli)", 1),
            (combo_c, "Tutti (coppie)",  0),
        ):
            if combo is None:
                continue
            sel = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(placeholder)
            if db.risultato.successo:
                for t in lista:
                    if str(t.get("singolo_doppio", -1)) == str(tipo):
                        combo.addItem(t["nome"])
            idx = combo.findText(sel)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    # ──────────────────────────────────────────────────────────────────────
    #  LABEL ISCRITTI
    # ──────────────────────────────────────────────────────────────────────

    def _aggiorna_lbl_iscritti(self, nome_torneo: str):
        if not nome_torneo or nome_torneo == "Tutti i tornei":
            self._lbl_iscritti.setText("Iscritti: – / –")
            return
        res_lim = db.execute_select(
            "SELECT max_squadre FROM torneo WHERE nome = %s",
            params=(nome_torneo,)
        )
        tipo = self._tipo_torneo_corrente()
        n = _conta_iscritti(nome_torneo, tipo == 1) if tipo is not None else "?"
        lim = None
        if db.risultato.successo and res_lim and res_lim[0]["max_squadre"] is not None:
            lim = res_lim[0]["max_squadre"]
        lim_txt = str(lim) if lim is not None else "illimitato"
        self._lbl_iscritti.setText(f"Iscritti: {n} / {lim_txt}")

    # ──────────────────────────────────────────────────────────────────────
    #  CARICAMENTO DATI
    # ──────────────────────────────────────────────────────────────────────

    def _aggiorna_visibilita_btn_abbina(self):
        btn = getattr(self, "btn_abbina_singoli", None)
        if btn is None:
            return
        nome = self._torneo_corrente()
        tipo = self._tipo_torneo_corrente()
        if nome and tipo == 0:
            btn.setVisible(_conta_singoli_in_attesa(nome) > 0)
        else:
            btn.setVisible(False)

    def _on_filtro_singoli_cambiato(self):
        combo = getattr(self, "combo_tornei_singoli", None)
        nome = combo.currentText().strip() if combo else None
        placeholders = {"Tutti i tornei", "Tutti (singoli)"}
        nome = None if not nome or nome in placeholders else nome
        self._aggiorna_lbl_iscritti(nome or "")
        self._carica_singoli()
        self._aggiorna_visibilita_btn_abbina()

    def _on_filtro_coppie_cambiato(self):
        combo = getattr(self, "combo_tornei_coppie", None)
        nome = combo.currentText().strip() if combo else None
        placeholders = {"Tutti i tornei", "Tutti (coppie)"}
        nome = None if not nome or nome in placeholders else nome
        self._aggiorna_lbl_iscritti(nome or "")
        self._carica_coppie()
        self._aggiorna_visibilita_btn_abbina()

    def _on_ordine_cambiato(self):
        self._carica_singoli()
        self._carica_coppie()

    def _on_filtro_cambiato(self):
        nome = self._torneo_corrente()
        self._aggiorna_tabs_per_torneo()
        self._aggiorna_lbl_iscritti(nome)
        self._carica_dati()
        self._aggiorna_visibilita_btn_abbina()

    def _refresh_preservando_selezione(self):
        """Ricarica i dati mantenendo la selezione del torneo attuale."""
        self._ultimo_torneo = self._torneo_corrente()
        self._carica_combo_tornei()
        if self._ultimo_torneo:
            for combo_name in ("combo_tornei_singoli", "combo_tornei_coppie"):
                combo = getattr(self, combo_name, None)
                if combo:
                    idx = combo.findText(self._ultimo_torneo)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
        self._aggiorna_tabs_per_torneo()
        self._carica_dati()
        self._aggiorna_lbl_iscritti(self._torneo_corrente())
        self._aggiorna_visibilita_btn_abbina()

    def _torneo_corrente(self) -> Optional[str]:
        """Torneo selezionato nel combo attivo (dipende dal tab)."""
        stacked = getattr(self, "stacked_partecipanti", None)
        on_coppie = stacked is not None and stacked.currentIndex() == 1
        combo = getattr(self, "combo_tornei_coppie" if on_coppie else "combo_tornei_singoli", None)
        if combo is None:
            return None
        val = combo.currentText().strip()
        placeholders = {"Tutti i tornei", "Tutti (singoli)", "Tutti (coppie)"}
        return val if val and val not in placeholders else None

    def _torneo_singoli(self) -> Optional[str]:
        combo = getattr(self, "combo_tornei_singoli", None)
        if combo is None:
            return None
        val = combo.currentText().strip()
        return val if val and val not in {"Tutti i tornei", "Tutti (singoli)"} else None

    def _torneo_coppie(self) -> Optional[str]:
        combo = getattr(self, "combo_tornei_coppie", None)
        if combo is None:
            return None
        val = combo.currentText().strip()
        return val if val and val not in {"Tutti i tornei", "Tutti (coppie)"} else None

    def _ordine_corrente(self) -> str:
        # Legge l'ordinamento direttamente dalla combobox di ordinamento,
        # indipendentemente dalla scheda (singoli/coppie).
        combo = getattr(self, "combo_ordina_per", None)
        if combo is None:
            return "p.cognome"
        testo = combo.currentText()
        # Mappa i testi visualizzati nella UI ai nomi di colonne usate nelle query.
        # Default sicuro se il testo non è tra le chiavi conosciute.
        mapping = {
            "Cognome":     "p.cognome",
            "Nome":        "p.nome",
            "Soprannome":  "p.soprannome",
            "Nome coppia": "s.nome",
        }
        return mapping.get(testo, "p.cognome")

    def _carica_dati(self):
        self._carica_singoli()
        # le coppie si caricano solo se la tab coppie è visibile
        stacked = getattr(self, "stacked_partecipanti", None)
        if stacked and stacked.currentIndex() == 1:
            self._carica_coppie()

    # ══════════════════════════════════════════════════════════════
    #  ISCRIZIONE TORNEO (GUI) — implementazioni
    # ══════════════════════════════════════════════════════════════

    def _iscrivi_singolo(self):
        nome_torneo = self._torneo_corrente()
        if not nome_torneo:
            QMessageBox.information(self, "Iscrizione", "Seleziona un torneo prima di iscriversi.")
            return

        # recupera info torneo
        t = db.select_as_dict(
            "torneo",
            colonne=["singolo_doppio","max_squadre","quota_iscrizione","email_iscrizioni"],
            condizione="nome = %s",
            params=(nome_torneo,),
        )
        if not db.risultato.successo or not t:
            QMessageBox.critical(self, "Errore DB", "Impossibile recuperare il torneo.")
            return
        is_singolo_t = (t[0]["singolo_doppio"] == 1)

        # logiche di gating (simili a partecipanti.py)
        if _gironi_assegnati(nome_torneo):
            QMessageBox.warning(
                self,
                "Iscrizioni CHIUSE",
                "I gironi sono già stati generati. Per aggiungere ritardatari, usa 'Reset Gironi' nel menu Partite.",
            )
            return

        r_turni = db.select_as_dict(
            "turno",
            colonne=["COUNT(*) AS n"],
            condizione="nome_torneo = %s",
            params=(nome_torneo,),
        )
        turni_esistono = (r_turni[0]["n"] > 0) if (db.risultato.successo and r_turni) else False
        if turni_esistono:
            QMessageBox.warning(
                self,
                "Iscrizioni BLOCCATE",
                "Il torneo ha già turni in corso.",
            )
            return

        max_sq = t[0].get("max_squadre")
        n_complete = _conta_iscritti(nome_torneo, is_singolo_t)
        if max_sq is not None and n_complete >= max_sq:
            entita_msg = "giocatori" if is_singolo_t else "coppie complete"
            QMessageBox.information(
                self,
                "Iscrizione",
                f"Torneo al completo! {entita_msg.capitalize()}: {n_complete}/{max_sq}.",
            )
            return

        quota = t[0].get("quota_iscrizione")
        email = t[0].get("email_iscrizioni")
        if quota is not None:
            extra = f"  ({float(quota) * 2:.2f}€ a coppia)" if not is_singolo_t else ""
            QMessageBox.information(
                self,
                "Quota Iscrizione",
                f"Quota: {float(quota):.2f}€ / persona{extra}",
            )
        if email:
            QMessageBox.information(self, "Info Iscrizioni", f"Iscrizioni via: {email}")

        # Iscrizione in base al tipo di torneo
        if is_singolo_t:
            self._iscrivi_singolo_dialog(nome_torneo)
        else:
            # per tornei a coppie, offrire scelta tra coppia o singolo in attesa
            choices = ["coppia", "singolo"]
            choice, ok = QInputDialog.getItem(self, "Iscrizione", "Iscrivi come:", choices, 0, False)
            if not ok:
                return
            if choice == "coppia":
                self._iscrivi_coppia_dialog(nome_torneo)
            else:
                # Attuale semplificazione: iscrivi singolo in attesa (stile CLI)
                self._iscrivi_singolo_in_attesa_dialog(nome_torneo)

    def _iscrivi_singolo_dialog(self, nome_torneo: str):
        """Dialogo iscrizione singolo (torneo singolo) via partecipante_dialog.ui."""
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
            QMessageBox.information(self, "Iscrizione OK", f"Iscritto {dati['nome']} {dati['cognome']} «{dati['soprannome']}»!")
            self._refresh_preservando_selezione()
        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(self, "Errore iscrizione", str(e))

    def _iscrivi_coppia_dialog(self, nome_torneo: str):
        """Dialogo iscrizione coppia (2 giocatori) usando partecipante_dialog.ui."""
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

    def _iscrivi_singolo_in_attesa_dialog(self, nome_torneo: str):
        """Iscrizione singolo in attesa di compagno via partecipante_dialog.ui.
        Usa soprannome come nome della squadra, come nel CLI.
        """
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

    def _open_partecipante_dialog(self, nome_torneo: str) -> dict | None:
        """Apri partecipante_dialog.ui per inserire dati partecipante.
        Ritorna dict {nome, cognome, soprannome, via, civico, cap, citta, ha_indirizzo}
        oppure None se annullato o dati invalidi.
        """
        from PyQt5.QtWidgets import QPushButton
        dialog = QDialog(self)
        # Try multiple relative paths (no hard-coded absolute paths)
        loaded = False
        for path in ["claude/partecipante_dialog.ui", "partecipante_dialog.ui"]:
            try:
                if os.path.exists(path):
                    uic.loadUi(path, dialog)
                    loaded = True
                    break
            except Exception:
                pass
        if not loaded:
            # Fallback: try path relative to this file's directory
            alt_paths = [
                os.path.join(os.path.dirname(__file__), "claude", "partecipante_dialog.ui"),
                os.path.join(os.path.dirname(__file__), "partecipante_dialog.ui"),
            ]
            for ap in alt_paths:
                if os.path.exists(ap):
                    try:
                        uic.loadUi(ap, dialog)
                        loaded = True
                        break
                    except Exception:
                        continue
        if not loaded:
            QMessageBox.critical(self, "Errore UI", "Impossibile caricare partecipante_dialog.ui.")
            return None

        def _get(obj_name: str) -> str:
            w = dialog.findChild(QLineEdit, obj_name)
            return w.text().strip() if w else ""

        def _validate_and_accept():
            nome       = _get("entry_nome")
            cognome    = _get("entry_cognome")
            soprannome = _get("entry_soprannome")

            if not nome:
                QMessageBox.warning(dialog, "Campo obbligatorio", "Il campo 'Nome' è obbligatorio.")
                return
            if not cognome:
                QMessageBox.warning(dialog, "Campo obbligatorio", "Il campo 'Cognome' è obbligatorio.")
                return
            if not soprannome:
                QMessageBox.warning(dialog, "Campo obbligatorio", "Il campo 'Soprannome' è obbligatorio.")
                return

            via    = _get("entry_via")
            civico = _get("entry_civico")
            cap    = _get("entry_cap")
            citta  = _get("entry_citta")
            campi_addr = [via, civico, cap, citta]
            if any(campi_addr) and not all(campi_addr):
                mancanti = [n for n, v in [("Via", via), ("N° Civico", civico), ("CAP", cap), ("Città", citta)] if not v]
                QMessageBox.warning(
                    dialog, "Indirizzo incompleto",
                    f"Compila anche: {', '.join(mancanti)}."
                )
                return

            dup = db.select_as_dict(
                "partecipante AS p",
                colonne=["p.id_partecipante"],
                join="JOIN squadra s ON s.id_squadra = p.id_squadra",
                condizione="s.nome_torneo = %s AND LOWER(p.soprannome) = LOWER(%s)",
                params=(nome_torneo, soprannome),
            )
            if not db.risultato.successo:
                QMessageBox.critical(dialog, "Errore DB", db.risultato.get_msg())
                return
            if dup:
                QMessageBox.warning(dialog, "Duplicato", f"Il soprannome '{soprannome}' è già in uso in questo torneo.")
                return

            dialog.accept()

        for btn in dialog.findChildren(QPushButton):
            if btn.objectName() == "btn_save":
                btn.clicked.connect(_validate_and_accept)
            elif btn.objectName() == "btn_cancel":
                btn.clicked.connect(dialog.reject)

        if dialog.exec_() != QDialog.Accepted:
            return None

        nome       = _get("entry_nome")
        cognome    = _get("entry_cognome")
        soprannome = _get("entry_soprannome")
        via        = _get("entry_via")
        civico     = _get("entry_civico")
        cap        = _get("entry_cap")
        citta      = _get("entry_citta")
        campi_addr = [via, civico, cap, citta]

        return {
            "nome": nome, "cognome": cognome, "soprannome": soprannome,
            "via": via, "civico": civico, "cap": cap, "citta": citta,
            "ha_indirizzo": all(campi_addr),
        }

    def _persisti_refresh(self, torneo_nome: str):
        self._refresh_preservando_selezione()

    def _check_iscrizioni_aperte(self, nome_torneo: str) -> bool:
        if _gironi_assegnati(nome_torneo):
            QMessageBox.warning(self, "Iscrizioni CHIUSE", "I gironi sono già stati assegnati.")
            return False
        r_turni = db.select_as_dict(
            "turno", colonne=["COUNT(*) AS n"],
            condizione="nome_torneo = %s", params=(nome_torneo,),
        )
        if (r_turni[0]["n"] > 0) if (db.risultato.successo and r_turni) else False:
            QMessageBox.warning(self, "Iscrizioni BLOCCATE", "Il torneo ha già turni in corso.")
            return False
        return True

    def _iscrivi_singolo_in_attesa(self):
        torneo = self._torneo_corrente()
        if not torneo:
            QMessageBox.information(self, "Iscrizione", "Nessun torneo selezionato.")
            return
        if not self._check_iscrizioni_aperte(torneo):
            return
        self._iscrivi_singolo_in_attesa_dialog(torneo)

    def _iscrivi_coppia(self):
        torneo = self._torneo_corrente()
        if not torneo:
            QMessageBox.information(self, "Iscrizione", "Nessun torneo selezionato.")
            return
        if not self._check_iscrizioni_aperte(torneo):
            return
        self._iscrivi_coppia_dialog(torneo)

    def _carica_singoli(self):
        tree = getattr(self, "participants_tree", None)
        if tree is None:
            return

        nome = self._torneo_singoli()
        ordine = self._ordine_corrente()

        if nome:
            query = (
                "SELECT p.id_partecipante, p.nome, p.cognome, p.soprannome, "
                "COALESCE(i.citta, '') AS citta, s.nome_torneo "
                "FROM partecipante p "
                "JOIN squadra s ON s.id_squadra = p.id_squadra "
                "JOIN torneo t ON t.nome = s.nome_torneo "
                "LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo "
                f"WHERE t.singolo_doppio = 1 AND s.nome_torneo = %s "
                f"ORDER BY {ordine}"
            )
            righe = db.execute_select(query, params=(nome,))
        else:
            query = (
                "SELECT p.id_partecipante, p.nome, p.cognome, p.soprannome, "
                "COALESCE(i.citta, '') AS citta, s.nome_torneo "
                "FROM partecipante p "
                "JOIN squadra s ON s.id_squadra = p.id_squadra "
                "JOIN torneo t ON t.nome = s.nome_torneo "
                "LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo "
                f"WHERE t.singolo_doppio = 1 "
                f"ORDER BY {ordine}"
            )
            righe = db.execute_select(query)

        tree.setUpdatesEnabled(False)
        tree.clear()
        if db.risultato.successo and righe:
            for r in righe:
                item = QTreeWidgetItem([
                    str(r["id_partecipante"]),
                    r["nome"] or "",
                    r["cognome"] or "",
                    r["soprannome"] or "",
                    r["citta"] or "",
                    r["nome_torneo"] or "",
                ])
                for col in range(6):
                    item.setTextAlignment(col, Qt.AlignCenter)
                tree.addTopLevelItem(item)
        tree.setUpdatesEnabled(True)
        tree.viewport().update()

        self._applica_filtri_live()

    def _carica_coppie(self):
        tree = getattr(self, "coppie_tree", None)
        if tree is None:
            return

        nome = self._torneo_coppie()
        ordine_raw = self._ordine_corrente()
        inner_sort = ordine_raw if not ordine_raw.startswith("s.") else "p.cognome"

        if nome:
            query = (
                "SELECT s.id_squadra, s.nome AS nome_squadra, s.nome_torneo, "
                "p.nome AS p_nome, p.cognome AS p_cognome, p.soprannome, "
                "COALESCE(i.citta, '') AS citta "
                "FROM squadra s "
                "JOIN torneo t ON t.nome = s.nome_torneo "
                "JOIN partecipante p ON p.id_squadra = s.id_squadra "
                "LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo "
                f"WHERE t.singolo_doppio = 0 AND s.nome_torneo = %s "
                f"ORDER BY s.nome, {inner_sort}"
            )
            righe = db.execute_select(query, params=(nome,))
        else:
            query = (
                "SELECT s.id_squadra, s.nome AS nome_squadra, s.nome_torneo, "
                "p.nome AS p_nome, p.cognome AS p_cognome, p.soprannome, "
                "COALESCE(i.citta, '') AS citta "
                "FROM squadra s "
                "JOIN torneo t ON t.nome = s.nome_torneo "
                "JOIN partecipante p ON p.id_squadra = s.id_squadra "
                "LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo "
                f"WHERE t.singolo_doppio = 0 "
                f"ORDER BY s.nome_torneo, s.nome, {inner_sort}"
            )
            righe = db.execute_select(query)

        tree.setUpdatesEnabled(False)
        tree.clear()
        if db.risultato.successo and righe:
            squadre: dict = {}
            for r in righe:
                sid = r["id_squadra"]
                if sid not in squadre:
                    squadre[sid] = {
                        "nome": r["nome_squadra"],
                        "torneo": r["nome_torneo"],
                        "giocatori": [],
                    }
                squadre[sid]["giocatori"].append(r)

            for sid, sq in squadre.items():
                root = QTreeWidgetItem([sq["nome"], "", sq["torneo"], ""])
                root.setFont(0, QFont("Helvetica", 10, QFont.Bold))
                for g in sq["giocatori"]:
                    child = QTreeWidgetItem(["",
                                             g["soprannome"] or "",
                                             "",
                                             g["citta"] or ""])
                    root.addChild(child)
                tree.addTopLevelItem(root)
                root.setExpanded(True)
        tree.setUpdatesEnabled(True)
        tree.viewport().update()

    # ──────────────────────────────────────────────────────────────────────
    #  FILTRO LIVE (nome/cognome)
    # ──────────────────────────────────────────────────────────────────────

    def _applica_filtri_live(self):
        tree = getattr(self, "participants_tree", None)
        if tree is None:
            return
        f_nome    = (getattr(self, "entry_filter_nome", None) or _NullWidget()).text().lower()
        f_cognome = (getattr(self, "entry_filter_cognome", None) or _NullWidget()).text().lower()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            nome    = item.text(1).lower()
            cognome = item.text(2).lower()
            hidden = (
                (bool(f_nome)    and f_nome    not in nome) or
                (bool(f_cognome) and f_cognome not in cognome)
            )
            item.setHidden(hidden)

    # ──────────────────────────────────────────────────────────────────────
    #  STUB CRUD
    # ──────────────────────────────────────────────────────────────────────

    def _abbina_singoli(self):
        import random
        nome = self._torneo_corrente()
        if not nome:
            QMessageBox.information(self, "Abbina", "Seleziona un torneo prima.")
            return

        singoli = db.execute_select("""
            SELECT s.id_squadra, p.nome AS nome_g, p.cognome AS cognome_g,
                   p.soprannome AS soprannome_g, p.id_partecipante
            FROM squadra s
            JOIN partecipante p ON p.id_squadra = s.id_squadra
            WHERE s.nome_torneo = %s
              AND (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 1
            ORDER BY s.id_squadra
        """, params=(nome,))

        if not db.risultato.successo:
            QMessageBox.critical(self, "Errore DB", db.risultato.get_msg())
            return
        if not singoli:
            QMessageBox.information(self, "Abbina", "Nessun singolo in attesa.")
            self._aggiorna_visibilita_btn_abbina()
            return

        n = len(singoli)
        if n < 2:
            g = singoli[0]
            QMessageBox.information(
                self, "Abbina Singoli",
                f"Non ci sono abbastanza partecipanti per abbinare.\n"
                f"{g['nome_g']} {g['cognome_g']} «{g['soprannome_g']}» è l'unico in attesa."
            )
            return
        lista = "\n".join(
            f"  • {g['nome_g']} {g['cognome_g']} «{g['soprannome_g']}»" for g in singoli
        )
        avviso = "\n\n⚠ Numero dispari — uno resterà senza compagno." if n % 2 else ""
        ret = QMessageBox.question(
            self, "Abbina Singoli",
            f"{n} giocatore/i in attesa:\n{lista}{avviso}\n\nProcedere con l'accoppiamento casuale?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        pool = list(singoli)
        random.shuffle(pool)

        db.start_transaction()
        try:
            for i in range(0, len(pool) - 1, 2):
                g1, g2 = pool[i], pool[i + 1]
                nome_coppia = f"{g1['soprannome_g']} & {g2['soprannome_g']}"
                db.execute_alt(
                    "UPDATE partecipante SET id_squadra = %s WHERE id_partecipante = %s",
                    params=(g1["id_squadra"], g2["id_partecipante"]),
                )
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
                db.execute_alt(
                    "UPDATE squadra SET nome = %s WHERE id_squadra = %s",
                    params=(nome_coppia, g1["id_squadra"]),
                )
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
                db.delete("squadra", condizione="id_squadra = %s", params=(g2["id_squadra"],))
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
            db.commit_transaction()
        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(self, "Errore accoppiamento", str(e))
            return

        if n % 2:
            g_rest = pool[-1]
            ret = QMessageBox.question(
                self, "Singolo Spaiato",
                f"{g_rest['nome_g']} {g_rest['cognome_g']} «{g_rest['soprannome_g']}» è rimasto senza compagno.\n\nRimuovere dal torneo?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.Yes:
                db.delete("squadra", condizione="id_squadra = %s", params=(g_rest["id_squadra"],))
                if not db.risultato.successo:
                    QMessageBox.critical(self, "Errore", db.risultato.get_msg())

        coppie_create = (n - (n % 2)) // 2
        QMessageBox.information(self, "Abbinamento OK", f"{coppie_create} coppia/e formata/e!")
        self._refresh_preservando_selezione()

    # ──────────────────────────────────────────────────────────────────────
    #  MODIFICA PARTECIPANTE
    # ──────────────────────────────────────────────────────────────────────

    def _modifica_partecipante(self):
        tree = getattr(self, "participants_tree", None)
        if tree is None:
            return
        items = tree.selectedItems()
        if not items:
            QMessageBox.information(self, "Modifica", "Seleziona prima un partecipante dalla lista.")
            return
        id_p_str = items[0].text(0)
        if not id_p_str:
            return
        self._apri_dettagli_dialog(int(id_p_str))

    def _apri_dettagli_dialog(self, id_partecipante: int):
        row = db.execute_select("""
            SELECT p.nome, p.cognome, p.soprannome, p.id_indirizzo,
                   i.via, i.numero_civico AS civico, i.cap, i.citta
            FROM   partecipante p
            LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo
            WHERE  p.id_partecipante = %s
        """, params=(id_partecipante,))
        if not db.risultato.successo or not row:
            QMessageBox.critical(self, "Errore DB", "Partecipante non trovato.")
            return
        dati = row[0]

        tornei_r = db.execute_select("""
            SELECT s.nome_torneo, s.nome AS nome_squadra
            FROM   partecipante p
            JOIN   squadra s ON s.id_squadra = p.id_squadra
            WHERE  p.id_partecipante = %s
        """, params=(id_partecipante,))

        dialog = QDialog(self)
        loaded = False
        for path in [
            "claude/dettagli_partecipante_dialog.ui",
            "dettagli_partecipante_dialog.ui",
            os.path.join(os.path.dirname(__file__), "claude", "dettagli_partecipante_dialog.ui"),
        ]:
            if os.path.exists(path):
                try:
                    uic.loadUi(path, dialog)
                    loaded = True
                    break
                except Exception:
                    continue
        if not loaded:
            QMessageBox.critical(self, "Errore UI", "Impossibile caricare dettagli_partecipante_dialog.ui.")
            return

        def _set(name, val):
            w = dialog.findChild(QLineEdit, name)
            if w:
                w.setText(val or "")

        _set("entry_nome",    dati["nome"])
        _set("entry_cognome", dati["cognome"])
        _set("entry_via",     dati["via"])
        _set("entry_civico",  dati["civico"])
        _set("entry_cap",     dati["cap"])
        _set("entry_citta",   dati["citta"])

        list_w = dialog.findChild(QListWidget, "list_tornei_iscritti")
        if list_w and db.risultato.successo and tornei_r:
            for t in tornei_r:
                list_w.addItem(QListWidgetItem(f"{t['nome_torneo']}  ({t['nome_squadra']})"))

        def _salva():
            def _get(name):
                w = dialog.findChild(QLineEdit, name)
                return w.text().strip() if w else ""

            nome    = _get("entry_nome")
            cognome = _get("entry_cognome")
            if not nome:
                QMessageBox.warning(dialog, "Campo obbligatorio", "Il campo 'Nome' è obbligatorio.")
                return
            if not cognome:
                QMessageBox.warning(dialog, "Campo obbligatorio", "Il campo 'Cognome' è obbligatorio.")
                return

            via    = _get("entry_via")
            civico = _get("entry_civico")
            cap    = _get("entry_cap")
            citta  = _get("entry_citta")
            campi  = [via, civico, cap, citta]
            if any(campi) and not all(campi):
                mancanti = [n for n, v in [("Via", via), ("N° Civico", civico), ("CAP", cap), ("Città", citta)] if not v]
                QMessageBox.warning(dialog, "Indirizzo incompleto", f"Compila anche: {', '.join(mancanti)}.")
                return

            ha_indirizzo = all(campi)
            id_ind       = dati["id_indirizzo"]

            db.start_transaction()
            try:
                db.execute_alt(
                    "UPDATE partecipante SET nome=%s, cognome=%s WHERE id_partecipante=%s",
                    params=(nome, cognome, id_partecipante),
                )
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())

                if ha_indirizzo:
                    if id_ind:
                        db.execute_alt(
                            "UPDATE indirizzo SET via=%s, numero_civico=%s, cap=%s, citta=%s WHERE id_indirizzo=%s",
                            params=(via, civico, cap, citta, id_ind),
                        )
                    else:
                        id_ind = db.insert("indirizzo", ["via","numero_civico","cap","citta"], [via, civico, cap, citta])
                        if not db.risultato.successo:
                            raise Exception(db.risultato.get_msg())
                        db.execute_alt(
                            "UPDATE partecipante SET id_indirizzo=%s WHERE id_partecipante=%s",
                            params=(id_ind, id_partecipante),
                        )
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())
                elif not any(campi) and id_ind:
                    db.execute_alt(
                        "UPDATE partecipante SET id_indirizzo=NULL WHERE id_partecipante=%s",
                        params=(id_partecipante,),
                    )
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())

                db.commit_transaction()
                QMessageBox.information(dialog, "Salvato", "Dati aggiornati con successo.")
                dialog.accept()
            except Exception as e:
                db.rollback_transaction()
                QMessageBox.critical(dialog, "Errore DB", str(e))

        for btn in dialog.findChildren(QPushButton):
            if btn.objectName() == "btn_save":
                btn.clicked.connect(_salva)
                btn.setDefault(True)
            elif btn.objectName() == "btn_cancel":
                btn.clicked.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            self._refresh_preservando_selezione()

    def _modifica_coppia(self):
        tree = getattr(self, "coppie_tree", None)
        if tree is None:
            return
        item = tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Modifica Coppia", "Seleziona prima una coppia dalla lista.")
            return
        # risali al nodo radice (la squadra)
        root = item if item.parent() is None else item.parent()

        nome_coppia_attuale = root.text(0)
        torneo = root.text(2)

        # carica id_squadra e partecipanti dal DB
        sq_res = db.execute_select(
            "SELECT id_squadra FROM squadra WHERE nome = %s AND nome_torneo = %s",
            params=(nome_coppia_attuale, torneo),
        )
        if not db.risultato.successo or not sq_res:
            QMessageBox.critical(self, "Errore DB", "Coppia non trovata nel database.")
            return
        id_squadra = sq_res[0]["id_squadra"]

        giocatori = db.execute_select(
            """SELECT p.id_partecipante, p.nome, p.cognome, p.soprannome, p.id_indirizzo,
                      i.via, i.numero_civico AS civico, i.cap, i.citta
               FROM partecipante p
               LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo
               WHERE p.id_squadra = %s ORDER BY p.id_partecipante""",
            params=(id_squadra,),
        )
        if not db.risultato.successo:
            QMessageBox.critical(self, "Errore DB", db.risultato.get_msg())
            return

        # ── costruzione dialog ────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle("Modifica Coppia")
        dlg.setMinimumWidth(380)
        dlg.setStyleSheet("""
            QDialog { background-color: #ecf0f1; }
            QLabel  { color: #34495e; font-family: Helvetica; font-size: 11pt; }
            QLabel#title { color: white; font-size: 15pt; font-weight: bold; }
            QFrame#header { background-color: #2c3e50; }
            QLineEdit { border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px;
                        font-family: Helvetica; font-size: 11pt; background: white; }
            QLineEdit:focus { border: 1px solid #3498db; }
            QPushButton { border-radius: 6px; font-family: Helvetica; font-size: 11pt;
                          font-weight: bold; color: white; padding: 8px 20px; }
            QPushButton#btn_save   { background-color: #1abc9c; }
            QPushButton#btn_save:hover { background-color: #16a085; }
            QPushButton#btn_cancel { background-color: #95a5a6; }
            QPushButton#btn_cancel:hover { background-color: #7f8c8d; }
        """)

        vl = QVBoxLayout(dlg)
        vl.setSpacing(0)
        vl.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(55)
        hl_h = QVBoxLayout(header)
        lbl_title = QLabel("Modifica Coppia")
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignCenter)
        hl_h.addWidget(lbl_title)
        vl.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 20)
        body.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        entry_nome_coppia = QLineEdit(nome_coppia_attuale)
        form.addRow("Nome coppia:", entry_nome_coppia)

        giocatori_entries = []
        for i, g in enumerate(giocatori, 1):
            lbl_sep = QLabel(f"── Giocatore {i}  (soprannome: {g['soprannome'] or '—'}) ──")
            lbl_sep.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
            form.addRow(lbl_sep)
            e_nome    = QLineEdit(g["nome"] or "")
            e_cognome = QLineEdit(g["cognome"] or "")
            e_via     = QLineEdit(g["via"] or "")
            e_civico  = QLineEdit(g["civico"] or "")
            e_cap     = QLineEdit(g["cap"] or "")
            e_citta   = QLineEdit(g["citta"] or "")
            form.addRow("Nome:",      e_nome)
            form.addRow("Cognome:",   e_cognome)
            form.addRow("Via:",       e_via)
            form.addRow("N° Civico:", e_civico)
            form.addRow("CAP:",       e_cap)
            form.addRow("Città:",     e_citta)
            giocatori_entries.append({
                "id_partecipante": g["id_partecipante"],
                "id_indirizzo":    g["id_indirizzo"],
                "e_nome":    e_nome,   "e_cognome": e_cognome,
                "e_via":     e_via,    "e_civico":  e_civico,
                "e_cap":     e_cap,    "e_citta":   e_citta,
            })

        body.addLayout(form)

        hl_btn = QHBoxLayout()
        hl_btn.addStretch()
        btn_cancel = QPushButton("Annulla")
        btn_cancel.setObjectName("btn_cancel")
        btn_save = QPushButton("Salva")
        btn_save.setObjectName("btn_save")
        btn_save.setDefault(True)
        hl_btn.addWidget(btn_cancel)
        hl_btn.addWidget(btn_save)
        body.addLayout(hl_btn)

        vl.addLayout(body)

        btn_cancel.clicked.connect(dlg.reject)

        def _salva():
            nuovo_nome = entry_nome_coppia.text().strip()
            if not nuovo_nome:
                QMessageBox.warning(dlg, "Errore", "Il nome della coppia non può essere vuoto.")
                return

            # controllo unicità nome coppia nel torneo (escludi se stesso)
            if nuovo_nome != nome_coppia_attuale:
                dup = db.execute_select(
                    "SELECT id_squadra FROM squadra WHERE nome = %s AND nome_torneo = %s AND id_squadra != %s",
                    params=(nuovo_nome, torneo, id_squadra),
                )
                if db.risultato.successo and dup:
                    QMessageBox.warning(dlg, "Duplicato", f"Esiste già una coppia chiamata '{nuovo_nome}' in questo torneo.")
                    return

            for g in giocatori_entries:
                if not g["e_nome"].text().strip() or not g["e_cognome"].text().strip():
                    QMessageBox.warning(dlg, "Errore", "Nome e Cognome non possono essere vuoti.")
                    return
                via    = g["e_via"].text().strip()
                civico = g["e_civico"].text().strip()
                cap    = g["e_cap"].text().strip()
                citta  = g["e_citta"].text().strip()
                campi  = [via, civico, cap, citta]
                if any(campi) and not all(campi):
                    mancanti = [n for n, v in [("Via", via), ("N° Civico", civico), ("CAP", cap), ("Città", citta)] if not v]
                    QMessageBox.warning(dlg, "Indirizzo incompleto", f"Compila anche: {', '.join(mancanti)}.")
                    return

            db.start_transaction()
            try:
                if nuovo_nome != nome_coppia_attuale:
                    db.execute_alt(
                        "UPDATE squadra SET nome = %s WHERE id_squadra = %s",
                        params=(nuovo_nome, id_squadra),
                    )
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())

                for g in giocatori_entries:
                    id_p   = g["id_partecipante"]
                    id_ind = g["id_indirizzo"]
                    nome   = g["e_nome"].text().strip()
                    cognome = g["e_cognome"].text().strip()
                    via    = g["e_via"].text().strip()
                    civico = g["e_civico"].text().strip()
                    cap    = g["e_cap"].text().strip()
                    citta  = g["e_citta"].text().strip()
                    campi  = [via, civico, cap, citta]
                    ha_ind = all(campi)

                    db.execute_alt(
                        "UPDATE partecipante SET nome = %s, cognome = %s WHERE id_partecipante = %s",
                        params=(nome, cognome, id_p),
                    )
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())

                    if ha_ind:
                        if id_ind:
                            db.execute_alt(
                                "UPDATE indirizzo SET via=%s, numero_civico=%s, cap=%s, citta=%s WHERE id_indirizzo=%s",
                                params=(via, civico, cap, citta, id_ind),
                            )
                        else:
                            new_id = db.insert("indirizzo", ["via","numero_civico","cap","citta"], [via, civico, cap, citta])
                            if not db.risultato.successo:
                                raise Exception(db.risultato.get_msg())
                            db.execute_alt(
                                "UPDATE partecipante SET id_indirizzo=%s WHERE id_partecipante=%s",
                                params=(new_id, id_p),
                            )
                        if not db.risultato.successo:
                            raise Exception(db.risultato.get_msg())
                    elif not any(campi) and id_ind:
                        db.execute_alt(
                            "UPDATE partecipante SET id_indirizzo=NULL WHERE id_partecipante=%s",
                            params=(id_p,),
                        )
                        if not db.risultato.successo:
                            raise Exception(db.risultato.get_msg())

                db.commit_transaction()
                dlg.accept()
            except Exception as e:
                db.rollback_transaction()
                QMessageBox.critical(dlg, "Errore DB", str(e))

        btn_save.clicked.connect(_salva)

        if dlg.exec_() == QDialog.Accepted:
            self._refresh_preservando_selezione()

    def _elimina_singolo(self):
        from config import PASSWORD_TORNEI
        tree = getattr(self, "participants_tree", None)
        if tree is None:
            return
        item = tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Elimina", "Seleziona prima un partecipante dalla lista.")
            return

        id_p = int(item.text(0))
        nome_display = f"{item.text(1)} {item.text(2)} «{item.text(3)}»"
        torneo = item.text(5)

        if not self._check_iscrizioni_aperte(torneo):
            return

        if not QMessageBox.question(
            self, "Conferma eliminazione",
            f"Eliminare {nome_display} dal torneo '{torneo}'?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            return

        pwd, ok = QInputDialog.getText(self, "Password richiesta", "Password amministratore:", QLineEdit.Password)
        if not ok or pwd != PASSWORD_TORNEI:
            QMessageBox.warning(self, "Errore", "Password errata. Operazione annullata.")
            return

        db.start_transaction()
        try:
            sq = db.execute_select(
                "SELECT id_squadra FROM partecipante WHERE id_partecipante = %s", params=(id_p,)
            )
            if not db.risultato.successo or not sq:
                raise Exception("Partecipante non trovato.")
            id_sq = sq[0]["id_squadra"]

            db.execute_alt("DELETE FROM partecipante WHERE id_partecipante = %s", params=(id_p,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.execute_alt("DELETE FROM squadra WHERE id_squadra = %s", params=(id_sq,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            db.commit_transaction()
            QMessageBox.information(self, "Eliminato", f"{nome_display} rimosso dal torneo.")
            self._refresh_preservando_selezione()
        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(self, "Errore DB", str(e))

    def _elimina_coppia(self):
        from config import PASSWORD_TORNEI
        tree = getattr(self, "coppie_tree", None)
        if tree is None:
            return
        item = tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Elimina", "Seleziona prima una coppia dalla lista.")
            return

        root = item if item.parent() is None else item.parent()
        nome_coppia = root.text(0)
        torneo = root.text(2)

        if not self._check_iscrizioni_aperte(torneo):
            return

        if not QMessageBox.question(
            self, "Conferma eliminazione",
            f"Eliminare la coppia '{nome_coppia}' dal torneo '{torneo}'?\nVerranno eliminati anche tutti i partecipanti della coppia.",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            return

        pwd, ok = QInputDialog.getText(self, "Password richiesta", "Password amministratore:", QLineEdit.Password)
        if not ok or pwd != PASSWORD_TORNEI:
            QMessageBox.warning(self, "Errore", "Password errata. Operazione annullata.")
            return

        sq_res = db.execute_select(
            "SELECT id_squadra FROM squadra WHERE nome = %s AND nome_torneo = %s",
            params=(nome_coppia, torneo),
        )
        if not db.risultato.successo or not sq_res:
            QMessageBox.critical(self, "Errore DB", "Coppia non trovata nel database.")
            return
        id_sq = sq_res[0]["id_squadra"]

        db.start_transaction()
        try:
            db.execute_alt("DELETE FROM partecipante WHERE id_squadra = %s", params=(id_sq,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.execute_alt("DELETE FROM squadra WHERE id_squadra = %s", params=(id_sq,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            db.commit_transaction()
            QMessageBox.information(self, "Eliminata", f"Coppia '{nome_coppia}' rimossa dal torneo.")
            self._refresh_preservando_selezione()
        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(self, "Errore DB", str(e))

    def _stub(self, azione: str):
        QMessageBox.information(self, "In arrivo",
                                f"'{azione}' sarà disponibile nella prossima versione.")

    def aggiorna(self):
        """Ricarica tutto (chiamato da main.py al cambio pannello)."""
        self._refresh_preservando_selezione()


class _NullWidget:
    """Fallback per widget non trovati nel UI."""
    def text(self):
        return ""

    
# ══════════════════════════════════════════════════════════════════════
#  ISCRIZIONE TORNEO (GUI) — utilità
# ══════════════════════════════════════════════════════════════════════

    
def _answer(msg: str):
    # helper placeholder to keep syntax valid if expanded in future
    return msg
