import sys
import csv
import os

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QTreeWidgetItem, QMessageBox, QInputDialog, QLineEdit,
    QAbstractItemView, QListWidgetItem, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt
from collections import defaultdict

from config import db, PASSWORD_TORNEI

# ── percorsi .ui ──────────────────────────────────────────────────────────────
UI_DIR                       = "claude/"
UI_MAIN                      = UI_DIR + "m_w.ui"
UI_TORNEI                    = UI_DIR + "tornei_w.ui"
UI_TOURNAMENT_DLG            = UI_DIR + "tournament_dialog.ui"
UI_PARTECIPANTI              = UI_DIR + "partecipanti_widget.ui"
UI_PARTECIPANTE_DLG          = UI_DIR + "partecipante_dialog.ui"
UI_CLASSIFICA                = UI_DIR + "classifica_w.ui"
UI_DETTAGLI_PARTECIPANTE_DLG = UI_DIR + "dettagli_partecipante_dialog.ui"
UI_PARTITE                   = UI_DIR + "partite_widget.ui"


# =============================================================================
# UTILITÀ
# =============================================================================

def msg_err(parent, testo: str):
    QMessageBox.critical(parent, "Errore", testo)

def msg_ok(parent, testo: str):
    QMessageBox.information(parent, "Successo", testo)

def msg_confirm(parent, titolo: str, testo: str) -> bool:
    r = QMessageBox.question(parent, titolo, testo,
                             QMessageBox.Yes | QMessageBox.No)
    return r == QMessageBox.Yes


_STATI_TORNEO_GUI = {
    "iscrizioni_aperte": ("Iscrizioni APERTE", Qt.darkGreen),
    "attesa":            ("Fase GIRONI - attesa di configurazione", Qt.darkYellow),
    "gironi":        ("Fase GIRONI in corso", Qt.darkCyan),
    "playoff":       ("Fase PLAYOFF in corso", Qt.darkGreen),
    "concluso":      ("Torneo CONCLUSO", Qt.black),
}


def _stato_torneo_gui(nome: str) -> tuple[str, Qt.GlobalColor]:
    """
    Allinea la GUI alla logica del terminale in partite1.py.
    Restituisce etichetta leggibile + colore per la colonna Stato.
    """
    try:
        from partite1 import _get_stato, _calcola_fase
        stato = _get_stato(nome)
        if stato is None:
            return ("Stato non disponibile", Qt.darkRed)
        fase = _calcola_fase(stato)
        return _STATI_TORNEO_GUI.get(fase, (fase, Qt.black))
    except Exception:
        return ("Stato non disponibile", Qt.darkRed)


# =============================================================================
# DIALOG TORNEO  (tournament_dialog.ui)
# Chill: niente date (data_inizio, data_fine, iscrizioni)
# =============================================================================

class DialogTorneo(QDialog):

    def __init__(self, parent=None, dati_iniziali: dict = None):
        super().__init__(parent)
        uic.loadUi(UI_TOURNAMENT_DLG, self)
        self.setWindowModality(Qt.ApplicationModal)
        self.dati    = None
        self._saving = False

        if dati_iniziali:
            self.label_dialog_title.setText("Modifica Torneo")
            self.entry_nome.setText(dati_iniziali.get("nome", ""))
            sd = dati_iniziali.get("singolo_doppio", 1)
            self.combo_tipo.setCurrentIndex(0 if str(sd) == "1" else 1)
            self.entry_email.setText(dati_iniziali.get("email_iscrizioni", "") or "")
            self.spin_quota.setValue(float(dati_iniziali.get("quota_iscrizione") or 0))
            self.spin_max.setValue(int(dati_iniziali.get("max_squadre") or 0))
        else:
            self.label_dialog_title.setText("Nuovo Torneo")
            self.entry_email.setText("")
            self.spin_quota.setValue(0.0)
            self.spin_max.setValue(0)

        self.btn_save.clicked.connect(self._salva)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.setDefault(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._salva()
        else:
            super().keyPressEvent(event)

    def _salva(self):
        if self._saving:
            return
        self._saving = True
        try:
            self._salva_impl()
        finally:
            self._saving = False

    def _salva_impl(self):
        nome = self.entry_nome.text().strip()
        if not nome:
            msg_err(self, "Il nome del torneo non può essere vuoto."); return

        singolo = 1 if self.combo_tipo.currentIndex() == 0 else 0

        self.dati = {
            "nome":             nome,
            "singolo_doppio":   singolo,
            "email_iscrizioni": self.entry_email.text().strip() or None,
            "quota_iscrizione": self.spin_quota.value() if self.spin_quota.value() > 0 else None,
            "max_squadre":      self.spin_max.value() if self.spin_max.value() > 0 else None,
        }
        self.accept()


# =============================================================================
# PANNELLO TORNEI  (tornei_w.ui)
# Chill: niente colonne data nel DB
# =============================================================================

class PannelloTornei(QWidget):
    COLONNE_DB = ["nome", "singolo_doppio", "email_iscrizioni", "quota_iscrizione", "max_squadre"]

    def __init__(self, apri_classifica_fn=None, on_delete_cb=None):
        print(f"PannelloTornei init, apri_classifica_fn: {apri_classifica_fn}")
        super().__init__()
        uic.loadUi(UI_TORNEI, self)
        self._apri_classifica = apri_classifica_fn
        self._on_delete_cb = on_delete_cb  # <-- Salviamo il callback

        self.btn_edit.setVisible(False)
        self.tournament_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)

        for col, w in enumerate([220, 100, 190, 100, 110, 100, 170]):
            self.tournament_tree.setColumnWidth(col, w)

        self.entry_tournament_name_list.textChanged.connect(self.carica)
        self.btn_add.clicked.connect(self._aggiungi)
        self.btn_delete.clicked.connect(self._elimina)
        self.btn_classifica.clicked.connect(self._vedi_classifica)

        self.carica()

    def carica(self):
        self.tournament_tree.clear()
        filtro = self.entry_tournament_name_list.text().strip()
        where = f"WHERE t.nome LIKE '%{filtro}%'" if filtro else ""

        query = f"""
            SELECT
                t.nome,
                t.singolo_doppio,
                IFNULL(t.email_iscrizioni, '')    AS email_iscrizioni,
                IFNULL(t.quota_iscrizione, 0)     AS quota_iscrizione,
                IFNULL(t.max_squadre, 0)          AS max_squadre,
                COUNT(s.id_squadra)               AS iscritti
            FROM torneo t
            LEFT JOIN squadra s ON s.nome_torneo = t.nome
            {where}
            GROUP BY t.nome, t.singolo_doppio, t.email_iscrizioni, t.quota_iscrizione, t.max_squadre
            ORDER BY t.nome
        """

        lista = db.execute_select(query)
        if not db.risultato.successo or lista is None:
            msg_err(self, "Errore DB: " + db.risultato.get_msg());
            return

        for t in lista:
            tipo = "Singolo" if str(t.get("singolo_doppio")) == "1" else "Coppie"
            quota = t.get("quota_iscrizione") or 0
            max_sq = int(t.get("max_squadre") or 0)
            iscritti = int(t.get("iscritti") or 0)
            stato_colore = Qt.black

            # calcolo stato
            turno_info = db.execute_select(
                f"SELECT fase FROM turno WHERE nome_torneo = '{t['nome']}' ORDER BY numero DESC LIMIT 1"
            )
            if turno_info:
                fase = turno_info[0].get("fase", "")
                fasi_concluse = {"finale_1_2", "finale_3_4", "finale_5_6", "finale_7_8",
                                 "finale_9_10", "finale_11_12", "finale_diretta_5_6", "finale_diretta_9_10"}
                fasi_playoff = {"semifinale_A", "semifinale_B", "semifinale_C"}
                fasi_gironi = {"girone_A", "girone_B", "girone"}

                if fase in fasi_concluse:
                    finale_giocata = db.execute_select(
                        f"SELECT ps.punteggio FROM turno t "
                        f"JOIN partita p ON p.id_turno = t.id_turno "
                        f"JOIN partita_squadra ps ON ps.id_partita = p.id_partita "
                        f"WHERE t.nome_torneo = '{t['nome']}' AND t.fase = '{fase}' "
                        f"AND ps.punteggio IS NOT NULL LIMIT 1"
                    )
                    stato = "✅ Concluso" if finale_giocata else "🏆 Playoff"
                elif fase in fasi_playoff:
                    stato = "🏆 Playoff"
                elif fase in fasi_gironi:
                    stato = "🟡 Gironi in corso"
                else:
                    stato = "🔵 In corso"
            else:
                gironi_ass = db.execute_select(
                    f"SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = '{t['nome']}' AND girone IS NOT NULL"
                )
                if gironi_ass and gironi_ass[0]["n"] > 0:
                    stato = "🟡 Gironi assegnati"
                elif max_sq and iscritti >= max_sq:
                    stato = "🔴 Iscrizioni chiuse"
                elif iscritti > 0:
                    stato = "📝 Iscrizioni aperte"
                else:
                    stato = "🔵 Non iniziato"

            righe = [
                t.get("nome", ""),
                tipo,
                t.get("email_iscrizioni", "") or "",
                f"€ {float(quota):.2f}" if quota else "—",
                str(max_sq) if max_sq else "—",
                f"{iscritti}/{max_sq}" if max_sq else str(iscritti),
                stato,
            ]
            item = QTreeWidgetItem(righe)
            stato, stato_colore = _stato_torneo_gui(t.get("nome", ""))
            item.setText(6, stato)
            for c in range(7):
                item.setTextAlignment(c, Qt.AlignCenter)
            item.setForeground(6, stato_colore)
            self.tournament_tree.addTopLevelItem(item)

    def _aggiungi(self):
        dlg = DialogTorneo(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.dati

        if db.select_as_dict("torneo", condizione=f"nome = '{d['nome']}'"):
            msg_err(self, f"Esiste già un torneo chiamato '{d['nome']}'.");
            return

        db.insert(
            "torneo",
            ["nome", "singolo_doppio", "email_iscrizioni", "quota_iscrizione", "max_squadre"],
            [d["nome"], d["singolo_doppio"], d["email_iscrizioni"], d["quota_iscrizione"], d["max_squadre"]],
        )
        if not db.risultato.successo:
            msg_err(self, "Errore DB: " + db.risultato.get_msg());
            return

        msg_ok(self, f"Torneo '{d['nome']}' creato!")
        self.carica()

    def _elimina(self):
        item = self.tournament_tree.currentItem()
        if not item:
            msg_err(self, "Seleziona prima un torneo dalla lista.");
            return

        nome = item.text(0)
        pwd, ok = QInputDialog.getText(self, "Password richiesta",
                                       f"Password per eliminare '{nome}':",
                                       QLineEdit.Password)
        if not ok: return
        if pwd != PASSWORD_TORNEI:
            msg_err(self, "Password errata! Operazione annullata.");
            return
        if not msg_confirm(self, "Conferma",
                           f"Eliminare definitivamente '{nome}' e TUTTI i dati associati (iscritti, gironi, partite)?"):
            return

        # 1. ELIMINAZIONE MANUALE DATI COLLEGATI (Cascade manuale)
        # Eliminiamo i partecipanti
        db.execute_alt(
            f"DELETE FROM partecipante WHERE id_squadra IN (SELECT id_squadra FROM squadra WHERE nome_torneo = '{nome}')")
        # Eliminiamo le squadre
        db.execute_alt(f"DELETE FROM squadra WHERE nome_torneo = '{nome}'")
        # Le partite e i turni verranno eliminati dal database (se hai configurato i vincoli)
        # o puoi aggiungere DELETE simili per 'partita' e 'turno' qui se necessario.

        # 2. ELIMINAZIONE TORNEO
        db.delete("torneo", condizione=f"nome = '{nome}'")

        if not db.risultato.successo:
            msg_err(self, "Errore DB: " + db.risultato.get_msg());
            return

        msg_ok(self, f"Torneo '{nome}' eliminato con successo.")
        self.carica()

        # 3. AGGIORNA IL PANNELLO PARTECIPANTI
        if self._on_delete_cb:
            self._on_delete_cb()

    def _vedi_classifica(self):
        item = self.tournament_tree.currentItem()
        nome_torneo = item.text(0) if item else None
        if self._apri_classifica:
            self._apri_classifica(nome_torneo)


# =============================================================================
# DIALOG PARTECIPANTE  (partecipante_dialog.ui)
# Chill: niente CF, niente data_nascita
# Per nuovo: raccoglie dati senza fare INSERT (lo fa _iscrivi_torneo)
# Per modifica: esegue UPDATE direttamente
# =============================================================================

class DialogPartecipante(QDialog):

    def __init__(self, parent=None, dati_iniziali: dict = None, modifica: bool = False, nome_torneo: str = None):
        super().__init__(parent)
        uic.loadUi(UI_PARTECIPANTE_DLG, self)
        self.setWindowModality(Qt.ApplicationModal)
        self._modifica      = modifica
        self._dati_iniziali = dati_iniziali
        self._nome_torneo   = nome_torneo
        self.dati           = None
        self._saving        = False

        if modifica and dati_iniziali:
            self.label_dialog_title.setText("Modifica Partecipante")
            self.entry_nome.setText(dati_iniziali.get("nome", ""))
            self.entry_cognome.setText(dati_iniziali.get("cognome", ""))
            self.entry_soprannome.setText(dati_iniziali.get("soprannome", "") or "")
            self.entry_via.setText(dati_iniziali.get("via", "") or "")
            self.entry_civico.setText(str(dati_iniziali.get("numero_civico", "") or ""))
            self.entry_cap.setText(str(dati_iniziali.get("cap", "") or ""))
            self.entry_citta.setText(dati_iniziali.get("citta", "") or "")
        else:
            self.label_dialog_title.setText("Nuovo Partecipante")

        self.btn_save.clicked.connect(self._salva)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.setDefault(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._salva()
        else:
            super().keyPressEvent(event)

    def _salva(self):
        if self._saving:
            return
        self._saving = True
        try:
            self._salva_impl()
        finally:
            self._saving = False

    def _salva_impl(self):
        nome       = self.entry_nome.text().strip()
        cognome    = self.entry_cognome.text().strip()
        soprannome = self.entry_soprannome.text().strip()

        # MODIFICA: Aggiunto controllo su soprannome
        if not nome or not cognome or not soprannome:
                msg_err(self, "Nome, Cognome e Soprannome sono obbligatori.")
                return

            # ... resto del codice invariato ...

        new_via    = self.entry_via.text().strip()
        new_civico = self.entry_civico.text().strip()
        new_cap    = self.entry_cap.text().strip()
        new_citta  = self.entry_citta.text().strip()

        all_empty = not (new_via or new_civico or new_cap or new_citta)
        all_full  = bool(new_via and new_civico and new_cap and new_citta)

        if not (all_empty or all_full):
            msg_err(self, "I campi indirizzo devono essere tutti compilati o tutti vuoti."); return

        if self._modifica:
            id_partecipante = self._dati_iniziali["id_partecipante"]
            db.update("partecipante",
                      {"nome": nome, "cognome": cognome, "soprannome": soprannome or None},
                      f"id_partecipante = {id_partecipante}")
            if not db.risultato.successo:
                msg_err(self, "Errore DB: " + db.risultato.get_msg()); return

            orig_id_ind = self._dati_iniziali.get("id_indirizzo")
            if orig_id_ind:
                if all_empty:
                    db.update("partecipante", {"id_indirizzo": None},
                              f"id_partecipante = {id_partecipante}")
                    db.delete("indirizzo", f"id_indirizzo = {orig_id_ind}")
                elif all_full:
                    db.update("indirizzo",
                              {"via": new_via, "numero_civico": new_civico,
                               "cap": new_cap, "citta": new_citta},
                              f"id_indirizzo = {orig_id_ind}")
            else:
                if all_full:
                    new_id_ind = db.insert("indirizzo",
                                           ["via", "numero_civico", "cap", "citta"],
                                           [new_via, new_civico, new_cap, new_citta])
                    if not db.risultato.successo:
                        msg_err(self, "Errore DB: " + db.risultato.get_msg()); return
                    db.update("partecipante", {"id_indirizzo": new_id_ind},
                              f"id_partecipante = {id_partecipante}")

            msg_ok(self, f"Partecipante '{nome} {cognome}' salvato con successo!")

        # Controllo soprannome duplicato (solo nuova iscrizione, se nome_torneo noto)
        if not self._modifica and self._nome_torneo and soprannome:
            dup = db.execute_select(
                f"SELECT p.id_partecipante FROM partecipante p "
                f"JOIN squadra s ON s.id_squadra = p.id_squadra "
                f"WHERE s.nome_torneo = '{self._nome_torneo}' "
                f"AND LOWER(p.soprannome) = LOWER('{soprannome}')"
            )
            if dup:
                msg_err(self, f"Il soprannome '{soprannome}' è già in uso in questo torneo.")
                return

        self.dati = {
            "nome":       nome,
            "cognome":    cognome,
            "soprannome": soprannome or None,
            "via":        new_via or None,
            "civico":     new_civico or None,
            "cap":        new_cap or None,
            "citta":      new_citta or None,
        }
        self.accept()


# =============================================================================
# DIALOG DETTAGLI E MODIFICA PARTECIPANTE (dettagli_partecipante_dialog.ui)
# Chill: niente CF, niente data_nascita
# =============================================================================

class DialogDettagliPartecipante(QDialog):

    def __init__(self, parent=None, dati_partecipante: dict = None, tornei_iscritti: list = None):
        super().__init__(parent)
        uic.loadUi(UI_DETTAGLI_PARTECIPANTE_DLG, self)
        self.setWindowModality(Qt.ApplicationModal)
        self._dati_iniziali = dati_partecipante
        self._saving        = False

        self.btn_save.clicked.connect(self._salva)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.setDefault(True)

        if dati_partecipante:
            self._popola_dati(dati_partecipante)

        if tornei_iscritti:
            self._popola_tornei(tornei_iscritti)
        else:
            self.list_tornei_iscritti.addItem("Nessun torneo trovato.")
            self.list_tornei_iscritti.setEnabled(False)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._salva()
        else:
            super().keyPressEvent(event)

    def _popola_dati(self, dati: dict):
        self.entry_nome.setText(dati.get("nome", ""))
        self.entry_cognome.setText(dati.get("cognome", ""))
        # CF and data_nascita are not in chill DB — hide if widgets exist
        if hasattr(self, "entry_cf"):
            self.entry_cf.setVisible(False)
        if hasattr(self, "date_nascita"):
            self.date_nascita.setVisible(False)
        if hasattr(self, "label_cf_static"):
            self.label_cf_static.setVisible(False)
        if hasattr(self, "label_data_nascita_static"):
            self.label_data_nascita_static.setVisible(False)
        self.entry_via.setText(dati.get("via", "") or "")
        self.entry_civico.setText(str(dati.get("numero_civico", "") or ""))
        self.entry_cap.setText(str(dati.get("cap", "") or ""))
        self.entry_citta.setText(dati.get("citta", "") or "")
        self.label_dialog_title.setText(
            f"Dettagli e Modifica: {dati.get('nome', '')} {dati.get('cognome', '')}"
        )

    def _popola_tornei(self, tornei: list):
        self.list_tornei_iscritti.clear()
        if tornei:
            for nome in tornei:
                self.list_tornei_iscritti.addItem(QListWidgetItem(nome))
        else:
            self.list_tornei_iscritti.addItem("Nessun torneo a cui è iscritto.")
            self.list_tornei_iscritti.setEnabled(False)

    def _salva(self):
        if self._saving:
            return
        self._saving = True
        try:
            self._salva_impl()
        finally:
            self._saving = False

    # Se nella classe DialogDettagliPartecipante hai l'entry per il soprannome:
    def _salva_impl(self):
        nome = self.entry_nome.text().strip()
        cognome = self.entry_cognome.text().strip()
        # Esempio se hai aggiunto l'entry_soprannome anche qui:
        soprannome = self.entry_soprannome.text().strip() if hasattr(self, 'entry_soprannome') else "OK"

        if not nome or not cognome or not soprannome:
            msg_err(self, "Tutti i campi (Nome, Cognome, Soprannome) sono obbligatori.");
            return

        # ... resto del codice ...

        id_partecipante = self._dati_iniziali["id_partecipante"]
        orig_id_ind     = self._dati_iniziali.get("id_indirizzo")

        new_via    = self.entry_via.text().strip()
        new_civico = self.entry_civico.text().strip()
        new_cap    = self.entry_cap.text().strip()
        new_citta  = self.entry_citta.text().strip()

        all_empty = not (new_via or new_civico or new_cap or new_citta)
        all_full  = bool(new_via and new_civico and new_cap and new_citta)

        if not (all_empty or all_full):
            msg_err(self, "I campi indirizzo devono essere tutti compilati o tutti vuoti."); return

        db.update("partecipante", {"nome": nome, "cognome": cognome},
                  f"id_partecipante = {id_partecipante}")
        if not db.risultato.successo:
            msg_err(self, "Errore DB: " + db.risultato.get_msg()); return

        if orig_id_ind:
            if all_empty:
                db.update("partecipante", {"id_indirizzo": None},
                          f"id_partecipante = {id_partecipante}")
                db.delete("indirizzo", f"id_indirizzo = {orig_id_ind}")
            elif all_full:
                db.update("indirizzo",
                          {"via": new_via, "numero_civico": new_civico,
                           "cap": new_cap, "citta": new_citta},
                          f"id_indirizzo = {orig_id_ind}")
        else:
            if all_full:
                new_id_ind = db.insert(
                    "indirizzo",
                    ["via", "numero_civico", "cap", "citta"],
                    [new_via, new_civico, new_cap, new_citta]
                )
                if not db.risultato.successo:
                    msg_err(self, "Errore DB: " + db.risultato.get_msg()); return
                db.update("partecipante", {"id_indirizzo": new_id_ind},
                          f"id_partecipante = {id_partecipante}")

        msg_ok(self, f"Partecipante '{nome} {cognome}' aggiornato con successo!")
        self.accept()


# =============================================================================
# PANNELLO PARTECIPANTI  (partecipanti_widget.ui)
# Chill: niente CF, niente data_nascita; relazione diretta partecipante→squadra
# =============================================================================


# =============================================================================
# DIALOG ISCRIZIONE COPPIA
# =============================================================================

class DialogCoppia(QDialog):
    """Dialog per iscrivere o modificare una coppia."""

    def __init__(self, parent=None, nome_torneo: str = "", dati_iniziali: dict = None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self._nome_torneo = nome_torneo
        self._dati_iniziali = dati_iniziali  # Se valorizzato, siamo in modalità MODIFICA
        self._saving = False

        self.setWindowTitle(
            f"Iscrivi Coppia — {nome_torneo}" if not dati_iniziali else f"Modifica Coppia — {nome_torneo}")
        self.resize(520, 580)

        self.setStyleSheet("""
            QDialog { background-color: #ecf0f1; }
            QLabel { color: #34495e; font-family: Helvetica; font-size: 11pt; }
            QLineEdit { border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px;
                        font-family: Helvetica; font-size: 11pt; background-color: white; }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QFrame()
        header.setFixedHeight(54)
        header.setStyleSheet("QFrame { background-color: #2c3e50; border-radius: 6px; }")
        h_lay = QVBoxLayout(header)
        self.lbl_title = QLabel(f"Nuova Coppia" if not dati_iniziali else "Modifica Coppia")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("QLabel { color: white; font-size: 14pt; font-weight: bold; }")
        h_lay.addWidget(self.lbl_title)
        layout.addWidget(header)

        row_sq = QHBoxLayout()
        row_sq.addWidget(QLabel("Nome coppia *"))
        self.entry_nome_squadra = QLineEdit()
        self.entry_nome_squadra.setPlaceholderText("Es. Rossi & Bianchi")
        row_sq.addWidget(self.entry_nome_squadra)
        layout.addLayout(row_sq)

        # --- GIOCATORE 1 ---
        lbl1 = QLabel("── Giocatore 1 ──")
        lbl1.setStyleSheet("QLabel { font-weight: bold; color: #2c3e50; }")
        layout.addWidget(lbl1)
        grid1 = QGridLayout()
        grid1.setHorizontalSpacing(12)
        grid1.addWidget(QLabel("Nome *"), 0, 0)
        self.entry_nome1 = QLineEdit();
        self.entry_nome1.setPlaceholderText("Nome")
        grid1.addWidget(self.entry_nome1, 0, 1)
        grid1.addWidget(QLabel("Cognome *"), 0, 2)
        self.entry_cognome1 = QLineEdit();
        self.entry_cognome1.setPlaceholderText("Cognome")
        grid1.addWidget(self.entry_cognome1, 0, 3)

        self.lbl_sop1 = QLabel("Soprannome *")
        grid1.addWidget(self.lbl_sop1, 1, 0)
        self.entry_sop1 = QLineEdit();
        self.entry_sop1.setPlaceholderText("Nome usato in gara")
        grid1.addWidget(self.entry_sop1, 1, 1, 1, 3)
        layout.addLayout(grid1)

        # indirizzo g1
        self._frame_ind1 = QFrame()
        self._frame_ind1.setVisible(False)
        self._frame_ind1.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #bdc3c7; border-radius: 4px; }")
        gi1 = QGridLayout(self._frame_ind1)
        gi1.setHorizontalSpacing(10);
        gi1.setVerticalSpacing(6);
        gi1.setContentsMargins(10, 8, 10, 8)
        gi1.addWidget(QLabel("Via"), 0, 0)
        self.entry_via1 = QLineEdit();
        self.entry_via1.setPlaceholderText("Nome della via")
        gi1.addWidget(self.entry_via1, 0, 1, 1, 3)
        gi1.addWidget(QLabel("N° Civico"), 1, 0)
        self.entry_civico1 = QLineEdit();
        self.entry_civico1.setPlaceholderText("Es. 12/A")
        gi1.addWidget(self.entry_civico1, 1, 1)
        gi1.addWidget(QLabel("CAP"), 1, 2)
        self.entry_cap1 = QLineEdit();
        self.entry_cap1.setPlaceholderText("00000")
        gi1.addWidget(self.entry_cap1, 1, 3)
        gi1.addWidget(QLabel("Città"), 2, 0)
        self.entry_citta1 = QLineEdit();
        self.entry_citta1.setPlaceholderText("Città di residenza")
        gi1.addWidget(self.entry_citta1, 2, 1, 1, 3)
        layout.addWidget(self._frame_ind1)
        self._btn_ind1 = QPushButton("📍 Aggiungi indirizzo (opzionale)")
        self._btn_ind1.setStyleSheet(
            "QPushButton{background-color:#ecf0f1;color:#34495e;border:1px solid #bdc3c7;border-radius:4px;font-size:10pt;padding:4px 10px;}QPushButton:hover{background-color:#d5dbdb;}")
        self._btn_ind1.clicked.connect(lambda: self._toggle_indirizzo(self._frame_ind1, self._btn_ind1))
        hl1 = QHBoxLayout();
        hl1.addWidget(self._btn_ind1);
        hl1.addStretch()
        layout.addLayout(hl1)

        # --- GIOCATORE 2 ---
        lbl2 = QLabel("── Giocatore 2 ──")
        lbl2.setStyleSheet("QLabel { font-weight: bold; color: #2c3e50; }")
        layout.addWidget(lbl2)
        grid2 = QGridLayout()
        grid2.setHorizontalSpacing(12)
        grid2.addWidget(QLabel("Nome *"), 0, 0)
        self.entry_nome2 = QLineEdit();
        self.entry_nome2.setPlaceholderText("Nome")
        grid2.addWidget(self.entry_nome2, 0, 1)
        grid2.addWidget(QLabel("Cognome *"), 0, 2)
        self.entry_cognome2 = QLineEdit();
        self.entry_cognome2.setPlaceholderText("Cognome")
        grid2.addWidget(self.entry_cognome2, 0, 3)

        self.lbl_sop2 = QLabel("Soprannome *")
        grid2.addWidget(self.lbl_sop2, 1, 0)
        self.entry_sop2 = QLineEdit();
        self.entry_sop2.setPlaceholderText("Nome usato in gara")
        grid2.addWidget(self.entry_sop2, 1, 1, 1, 3)
        layout.addLayout(grid2)

        # indirizzo g2
        self._frame_ind2 = QFrame()
        self._frame_ind2.setVisible(False)
        self._frame_ind2.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #bdc3c7; border-radius: 4px; }")
        gi2 = QGridLayout(self._frame_ind2)
        gi2.setHorizontalSpacing(10);
        gi2.setVerticalSpacing(6);
        gi2.setContentsMargins(10, 8, 10, 8)
        gi2.addWidget(QLabel("Via"), 0, 0)
        self.entry_via2 = QLineEdit();
        self.entry_via2.setPlaceholderText("Nome della via")
        gi2.addWidget(self.entry_via2, 0, 1, 1, 3)
        gi2.addWidget(QLabel("N° Civico"), 1, 0)
        self.entry_civico2 = QLineEdit();
        self.entry_civico2.setPlaceholderText("Es. 12/A")
        gi2.addWidget(self.entry_civico2, 1, 1)
        gi2.addWidget(QLabel("CAP"), 1, 2)
        self.entry_cap2 = QLineEdit();
        self.entry_cap2.setPlaceholderText("00000")
        gi2.addWidget(self.entry_cap2, 1, 3)
        gi2.addWidget(QLabel("Città"), 2, 0)
        self.entry_citta2 = QLineEdit();
        self.entry_citta2.setPlaceholderText("Città di residenza")
        gi2.addWidget(self.entry_citta2, 2, 1, 1, 3)
        layout.addWidget(self._frame_ind2)
        self._btn_ind2 = QPushButton("📍 Aggiungi indirizzo (opzionale)")
        self._btn_ind2.setStyleSheet(
            "QPushButton{background-color:#ecf0f1;color:#34495e;border:1px solid #bdc3c7;border-radius:4px;font-size:10pt;padding:4px 10px;}QPushButton:hover{background-color:#d5dbdb;}")
        self._btn_ind2.clicked.connect(lambda: self._toggle_indirizzo(self._frame_ind2, self._btn_ind2))
        hl2 = QHBoxLayout();
        hl2.addWidget(self._btn_ind2);
        hl2.addStretch()
        layout.addLayout(hl2)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("Annulla")
        btn_cancel.setFixedSize(120, 38)
        btn_cancel.setStyleSheet(
            "QPushButton{background-color:#95a5a6;color:white;border-radius:6px;font-size:11pt;font-weight:bold;}QPushButton:hover{background-color:#7f8c8d;}")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        self.btn_save = QPushButton("✅Salva")
        self.btn_save.setFixedSize(120, 38)
        self.btn_save.setStyleSheet(
            "QPushButton{background-color:#1abc9c;color:white;border-radius:6px;font-size:11pt;font-weight:bold;}QPushButton:hover{background-color:#16a085;}")
        self.btn_save.clicked.connect(self._salva)
        self.btn_save.setDefault(True)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # --- LOGICA MODIFICA: Nascondi Soprannomi e Popola ---
        if self._dati_iniziali:
            self.lbl_sop1.setVisible(False)
            self.entry_sop1.setVisible(False)
            self.lbl_sop2.setVisible(False)
            self.entry_sop2.setVisible(False)
            self._popola_campi()

    def _popola_campi(self):
        d = self._dati_iniziali
        self.entry_nome_squadra.setText(d['squadra']['nome'])
        # G1
        g1 = d['g1']
        self.entry_nome1.setText(g1['nome'])
        self.entry_cognome1.setText(g1['cognome'])
        if g1.get('via'):
            self._toggle_indirizzo(self._frame_ind1, self._btn_ind1)
            self.entry_via1.setText(g1['via']);
            self.entry_civico1.setText(str(g1['numero_civico'] or ""))
            self.entry_cap1.setText(str(g1['cap'] or ""));
            self.entry_citta1.setText(g1['citta'] or "")
        # G2
        g2 = d['g2']
        self.entry_nome2.setText(g2['nome'])
        self.entry_cognome2.setText(g2['cognome'])
        if g2.get('via'):
            self._toggle_indirizzo(self._frame_ind2, self._btn_ind2)
            self.entry_via2.setText(g2['via']);
            self.entry_civico2.setText(str(g2['numero_civico'] or ""))
            self.entry_cap2.setText(str(g2['cap'] or ""));
            self.entry_citta2.setText(g2['citta'] or "")

    def _toggle_indirizzo(self, frame, btn):
        visible = not frame.isVisible()
        frame.setVisible(visible)
        btn.setText("📍 Rimuovi indirizzo" if visible else "📍 Aggiungi indirizzo")
        self.adjustSize()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._salva()
        else:
            super().keyPressEvent(event)

    def _salva(self):
        if self._saving: return
        self._saving = True
        try:
            self._salva_impl()
        finally:
            self._saving = False

    def _salva_impl(self):
        nome_sq = self.entry_nome_squadra.text().strip()
        n1 = self.entry_nome1.text().strip()
        c1 = self.entry_cognome1.text().strip()
        n2 = self.entry_nome2.text().strip()
        c2 = self.entry_cognome2.text().strip()

        if not nome_sq:
            msg_err(self, "Il nome della coppia è obbligatorio.");
            return

        # --- CONTROLLO DUPLICATO NOME SQUADRA (Sia per Nuova che per Modifica) ---
        condizione_dup = f"nome = '{nome_sq}' AND nome_torneo = '{self._nome_torneo}'"
        if self._dati_iniziali:
            # Se siamo in modifica, escludiamo la squadra stessa dal controllo
            id_attuale = self._dati_iniziali['squadra']['id_squadra']
            condizione_dup += f" AND id_squadra != {id_attuale}"

        dup_check = db.select_as_dict("squadra", condizione=condizione_dup)
        if dup_check:
            msg_err(self, f"Esiste già una coppia chiamata '{nome_sq}' in questo torneo.");
            return
        # ------------------------------------------------------------------------

        # Se non siamo in modifica, il soprannome è obbligatorio
        if not self._dati_iniziali:
            s1 = self.entry_sop1.text().strip()
            s2 = self.entry_sop2.text().strip()
            if not n1 or not c1 or not s1:
                msg_err(self, "Dati del Giocatore 1 incompleti.");
                return
            if not n2 or not c2 or not s2:
                msg_err(self, "Dati del Giocatore 2 incompleti.");
                return

            # Controlli duplicati soprannome (Solo per Nuova Iscrizione)
            if s1.lower() == s2.lower():
                msg_err(self, f"I due compagni non possono avere lo stesso soprannome ({s1}).");
                return
            check_sop = db.execute_select(f"""
                SELECT p.soprannome FROM partecipante p
                JOIN squadra s ON p.id_squadra = s.id_squadra
                WHERE s.nome_torneo = '{self._nome_torneo}'
                AND (LOWER(p.soprannome) = LOWER('{s1}') OR LOWER(p.soprannome) = LOWER('{s2}'))
            """)
            if check_sop:
                msg_err(self, f"Il soprannome '{check_sop[0]['soprannome']}' è già in uso.");
                return
        else:
            # In modifica controlliamo solo Nome e Cognome
            if not n1 or not c1 or not n2 or not c2:
                msg_err(self, "Nome e Cognome di entrambi i giocatori sono obbligatori.");
                return

        # --- LOGICA SALVATAGGIO (UPDATE o INSERT) ---
        if self._dati_iniziali:
            # MODALITÀ UPDATE
            id_sq = self._dati_iniziali['squadra']['id_squadra']
            db.update("squadra", {"nome": nome_sq}, f"id_squadra = {id_sq}")

            # Update G1
            self._salva_giocatore_update(1, self._dati_iniziali['g1'])
            # Update G2
            self._salva_giocatore_update(2, self._dati_iniziali['g2'])

            msg_ok(self, f"Coppia '{nome_sq}' aggiornata con successo!")
        else:
            # MODALITÀ INSERT
            id_sq = db.insert("squadra", ["nome", "nome_torneo"], [nome_sq, self._nome_torneo])
            self._salva_giocatore_insert(1, id_sq, n1, c1, self.entry_sop1.text().strip())
            self._salva_giocatore_insert(2, id_sq, n2, c2, self.entry_sop2.text().strip())
            msg_ok(self, f"Coppia '{nome_sq}' iscritta con successo!")

        self.accept()

    def _salva_giocatore_insert(self, idx, id_sq, nome, cognome, soprannome):
        via = getattr(self, f"entry_via{idx}").text().strip()
        civ = getattr(self, f"entry_civico{idx}").text().strip()
        cap = getattr(self, f"entry_cap{idx}").text().strip()
        cit = getattr(self, f"entry_citta{idx}").text().strip()

        id_ind = None
        if any([via, civ, cap, cit]):
            id_ind = db.insert("indirizzo", ["via", "numero_civico", "cap", "citta"], [via, civ, cap, cit])

        db.insert("partecipante", ["nome", "cognome", "soprannome", "id_squadra", "id_indirizzo"],
                  [nome, cognome, soprannome, id_sq, id_ind])

    def _salva_giocatore_update(self, idx, dati_vecchi):
        id_part = dati_vecchi['id_partecipante']
        nome = getattr(self, f"entry_nome{idx}").text().strip()
        cognome = getattr(self, f"entry_cognome{idx}").text().strip()

        via = getattr(self, f"entry_via{idx}").text().strip()
        civ = getattr(self, f"entry_civico{idx}").text().strip()
        cap = getattr(self, f"entry_cap{idx}").text().strip()
        cit = getattr(self, f"entry_citta{idx}").text().strip()

        db.update("partecipante", {"nome": nome, "cognome": cognome}, f"id_partecipante = {id_part}")

        old_id_ind = dati_vecchi.get('id_indirizzo')
        if any([via, civ, cap, cit]):
            if old_id_ind:
                db.update("indirizzo", {"via": via, "numero_civico": civ, "cap": cap, "citta": cit},
                          f"id_indirizzo = {old_id_ind}")
            else:
                new_id = db.insert("indirizzo", ["via", "numero_civico", "cap", "citta"], [via, civ, cap, cit])
                db.update("partecipante", {"id_indirizzo": new_id}, f"id_partecipante = {id_part}")
        elif old_id_ind:
            db.update("partecipante", {"id_indirizzo": None}, f"id_partecipante = {id_part}")
            db.delete("indirizzo", f"id_indirizzo = {old_id_ind}")


class PannelloPartecipanti(QWidget):

    def __init__(self):
        super().__init__()
        uic.loadUi(UI_PARTECIPANTI, self)

        # larghezze colonne singoli
        for col, w in enumerate([45, 130, 130, 130, 120, 170]):
            self.participants_tree.setColumnWidth(col, w)

        # larghezze colonne coppie
        for col, w in enumerate([220, 130, 160, 100]):
            self.coppie_tree.setColumnWidth(col, w)

        # filtri — aggiornano entrambe le tab
        for campo in [self.entry_filter_nome, self.entry_filter_cognome]:
            campo.textChanged.connect(self._aggiorna)
        combo_filter = getattr(self, "combo_filter_torneo", None) or getattr(self, "combo_tornei_singoli", None)
        if combo_filter:
            combo_filter.currentIndexChanged.connect(self._aggiorna)
        self.combo_ordina_per.currentIndexChanged.connect(self._aggiorna)

        # tab buttons
        self.btn_tab_singoli.clicked.connect(self._vai_singoli)
        self.btn_tab_coppie.clicked.connect(self._vai_coppie)

        # bottoni singoli
        self.participants_tree.itemDoubleClicked.connect(
            self._vedi_dettagli_partecipante_e_modifica
        )
        self.btn_edit.clicked.connect(self._modifica)
        self.btn_iscrivi_singolo.clicked.connect(self._iscrivi_singolo)
        btn_elim_singolo = getattr(self, "btn_elimina_singolo", None)
        if btn_elim_singolo:
            btn_elim_singolo.clicked.connect(self._elimina_coppia)

        # bottoni e interazioni coppie
        self.coppie_tree.itemDoubleClicked.connect(self._modifica_coppia)
        self.btn_modifica_coppia.clicked.connect(self._modifica_coppia_btn)
        btn_elim_coppia = getattr(self, "btn_elimina_coppia", None) or getattr(self, "btn_elimina_attesa", None)
        if btn_elim_coppia:
            btn_elim_coppia.clicked.connect(self._elimina_coppia)
        self.btn_iscrivi_coppia.clicked.connect(self._iscrivi_coppia)
        self.btn_iscrivi_singolo_attesa.clicked.connect(self._iscrivi_singolo_in_attesa)
        self.btn_abbina_singoli.clicked.connect(self._abbina_singoli)
        self._coppie_espanse = True
        self.btn_toggle_coppie.clicked.connect(self._toggle_coppie)

        self._carica_tornei_combo()
        self._aggiorna()

    # ------------------------------------------------------------------ #
    #  TAB NAVIGATION                                                      #
    # ------------------------------------------------------------------ #
    def _toggle_coppie(self):
        if self._coppie_espanse:
            self.coppie_tree.collapseAll()
            self._coppie_espanse = False
        else:
            self.coppie_tree.expandAll()
            self._coppie_espanse = True

    def _vai_singoli(self):
        self.btn_tab_singoli.setChecked(True)
        self.btn_tab_coppie.setChecked(False)
        self.stacked_partecipanti.setCurrentWidget(self.page_singoli)
        self._carica_tornei_combo()

    def _vai_coppie(self):
        self.btn_tab_singoli.setChecked(False)
        self.btn_tab_coppie.setChecked(True)
        self.stacked_partecipanti.setCurrentWidget(self.page_coppie)
        self._carica_tornei_combo()

    def _aggiorna(self):
        self.carica()
        self._carica_coppie()

    # ------------------------------------------------------------------ #
    #  MODIFICA COPPIA (Nuova logica)                                     #
    # ------------------------------------------------------------------ #
    def _modifica_coppia(self, item: QTreeWidgetItem):
        if item.parent():
            item = item.parent()

        id_squadra = item.data(0, Qt.UserRole)
        nome_torneo = item.text(2)
        in_attesa = item.data(0, Qt.UserRole + 1)

        res_sq = db.select_as_dict("squadra", condizione=f"id_squadra = {id_squadra}")
        if not res_sq: return

        giocatori = db.execute_select(f"""
            SELECT p.*, i.via, i.numero_civico, i.cap, i.citta
            FROM partecipante p
            LEFT JOIN indirizzo i ON p.id_indirizzo = i.id_indirizzo
            WHERE p.id_squadra = {id_squadra}
            ORDER BY p.id_partecipante ASC
        """)

        if not giocatori:
            return

        if in_attesa:
            # Singolo in attesa: apri DialogPartecipante in modifica
            g = giocatori[0]
            dlg = DialogPartecipante(parent=self, dati_iniziali=g, modifica=True)
            if dlg.exec_() == QDialog.Accepted:
                self._aggiorna()
        else:
            if len(giocatori) < 2:
                msg_err(self, "Impossibile modificare: la coppia deve avere due componenti.")
                return
            payload = {
                "squadra": res_sq[0],
                "g1": giocatori[0],
                "g2": giocatori[1]
            }
            dlg = DialogCoppia(parent=self, nome_torneo=nome_torneo, dati_iniziali=payload)
            if dlg.exec_() == QDialog.Accepted:
                self._aggiorna()

    # ------------------------------------------------------------------ #
    #  RESTO DEL CODICE (Invariato come da tuo snippet)                   #
    # ------------------------------------------------------------------ #
    def _carica_tornei_combo(self):
        # Filtro per tab solo se lo stacked è già inizializzato
        where = ""
        try:
            tab = self.stacked_partecipanti.currentWidget()
            if tab is self.page_singoli:
                where = "WHERE singolo_doppio = 1"
            elif tab is self.page_coppie:
                where = "WHERE singolo_doppio = 0"
        except Exception:
            pass

        self.combo_filter_torneo.blockSignals(True)
        self.combo_filter_torneo.clear()
        self.combo_filter_torneo.addItem("Tutti i tornei")

        tornei = db.execute_select(
            f"SELECT nome FROM torneo {where} ORDER BY nome"
        )
        if not db.risultato.successo or not tornei:
            # fallback: tutti i tornei senza filtro
            tornei = db.execute_select("SELECT nome FROM torneo ORDER BY nome")

        if db.risultato.successo and tornei:
            for t in tornei:
                self.combo_filter_torneo.addItem(t["nome"])

        self.combo_filter_torneo.blockSignals(False)

    def carica(self):
        self.participants_tree.clear()
        filtro_nome = self.entry_filter_nome.text().strip()
        filtro_cognome = self.entry_filter_cognome.text().strip()
        filtro_torneo = self.combo_filter_torneo.currentText()

        where_parts = ["t.singolo_doppio = 1"]
        if filtro_nome:
            where_parts.append(f"p.nome LIKE '%{filtro_nome}%'")
        if filtro_cognome:
            where_parts.append(f"p.cognome LIKE '%{filtro_cognome}%'")
        if filtro_torneo != "Tutti i tornei":
            where_parts.append(f"s.nome_torneo = '{filtro_torneo}'")
        where = "WHERE " + " AND ".join(where_parts)

        ordine = self.combo_ordina_per.currentText()
        if ordine == 'Nome':
            order_by = "p.nome, p.cognome"
        elif ordine == 'Soprannome':
            order_by = "IFNULL(p.soprannome, p.cognome), p.cognome"
        else:
            order_by = "p.cognome, p.nome"

        query = f"""
            SELECT p.id_partecipante, p.nome, p.cognome, IFNULL(p.soprannome, '') AS soprannome,
                   IFNULL(i.citta, '') AS citta, s.nome_torneo AS torneo
            FROM partecipante p
            JOIN squadra s ON s.id_squadra = p.id_squadra
            JOIN torneo t ON t.nome = s.nome_torneo
            LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo
            {where}
            ORDER BY {order_by}
        """
        lista = db.execute_select(query)
        if not db.risultato.successo or lista is None: return

        for r in lista:
            righe = [str(r.get("id_partecipante", "")), r.get("nome", ""), r.get("cognome", ""),
                     r.get("soprannome", ""), r.get("citta", ""), r.get("torneo", "")]
            item = QTreeWidgetItem(righe)
            for c in range(6): item.setTextAlignment(c, Qt.AlignCenter)
            self.participants_tree.addTopLevelItem(item)

    def _carica_coppie(self):
        self.coppie_tree.clear()
        filtro_nome = self.entry_filter_nome.text().strip()
        filtro_cognome = self.entry_filter_cognome.text().strip()
        filtro_torneo = self.combo_filter_torneo.currentText()

        where_parts = ["t.singolo_doppio = 0"]
        if filtro_torneo != "Tutti i tornei":
            where_parts.append(f"s.nome_torneo = '{filtro_torneo}'")
        where_sq = "WHERE " + " AND ".join(where_parts)

        query_sq = f"""
            SELECT s.id_squadra, s.nome AS nome_squadra, s.nome_torneo,
                   COUNT(p.id_partecipante) AS n_membri
            FROM squadra s
            JOIN torneo t ON t.nome = s.nome_torneo
            LEFT JOIN partecipante p ON p.id_squadra = s.id_squadra
            {where_sq}
            GROUP BY s.id_squadra, s.nome, s.nome_torneo
            ORDER BY s.nome_torneo, n_membri DESC, s.nome
        """
        ordine = self.combo_ordina_per.currentText()
        if ordine == 'Nome coppia':
            query_sq = query_sq.replace(
                'ORDER BY s.nome_torneo, n_membri DESC, s.nome',
                'ORDER BY s.nome'
            )
        squadre = db.execute_select(query_sq)
        if not db.risultato.successo or squadre is None: return

        for sq in squadre:
            n_membri = int(sq.get('n_membri') or 0)
            in_attesa = n_membri == 1
            label = (f"⏳ {sq['nome_squadra']}  (in attesa)" if in_attesa else f"👫 {sq['nome_squadra']}")
            parent_item = QTreeWidgetItem([label, "", sq["nome_torneo"], ""])
            parent_item.setData(0, Qt.UserRole, sq["id_squadra"])
            parent_item.setData(0, Qt.UserRole + 1, in_attesa)

            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            if in_attesa:
                from PyQt5.QtGui import QColor
                parent_item.setForeground(0, QColor('#e67e22'))

            giocatori = db.execute_select(f"""
                SELECT p.nome, p.cognome, IFNULL(p.soprannome,'') AS soprannome, IFNULL(i.citta,'') AS citta
                FROM partecipante p
                LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo
                WHERE p.id_squadra = {sq['id_squadra']}
                ORDER BY p.cognome, p.nome
            """)
            if db.risultato.successo and giocatori:
                for g in giocatori:
                    child = QTreeWidgetItem([f"  {g['nome']} {g['cognome']}", g["soprannome"], "", g["citta"]])
                    parent_item.addChild(child)

            self.coppie_tree.addTopLevelItem(parent_item)
        self.coppie_tree.expandAll()

    # --- Gli altri metodi (_seleziona_riga, _modifica, _elimina, _iscrivi_singolo, _elimina_coppia, ecc.)
    # rimangono identici a quelli che hai inviato ---

    def _seleziona_riga(self, item):
        self._selected_item = item

    def _modifica(self):
        item = self.participants_tree.currentItem()
        if not item:
            msg_err(self, "Seleziona prima un partecipante dalla lista.");
            return
        id_part = int(item.text(0))
        res = db.select_as_dict(
            "partecipante AS p",
            colonne=["p.*", "IFNULL(i.via,'') AS via", "IFNULL(i.numero_civico,'') AS numero_civico",
                     "IFNULL(i.cap,'') AS cap", "IFNULL(i.citta,'') AS citta"],
            join="LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo",
            condizione=f"p.id_partecipante = {id_part}"
        )
        if not db.risultato.successo or not res: return
        dlg = DialogPartecipante(parent=self, dati_iniziali=res[0], modifica=True)
        if dlg.exec_() == QDialog.Accepted: self._aggiorna()

    def _elimina(self):
        item = self.participants_tree.currentItem()
        if not item: return
        id_part = int(item.text(0))
        nome = f"{item.text(1)} {item.text(2)}"
        pwd, ok = QInputDialog.getText(self, "Password", f"Password per '{nome}':", QLineEdit.Password)
        if not ok or pwd != PASSWORD_TORNEI: return
        if not msg_confirm(self, "Conferma", f"Eliminare '{nome}'?"): return
        db.delete("partecipante", condizione=f"id_partecipante = {id_part}")
        self._aggiorna()

    def _iscrivi_singolo(self):
        tornei = db.execute_select("SELECT nome FROM torneo WHERE singolo_doppio = 1 ORDER BY nome")
        if not tornei: return
        nomi = [t["nome"] for t in tornei]
        nome_torneo, ok = QInputDialog.getItem(self, "Scegli Torneo", "Torneo:", nomi, 0, False)
        if not ok or not self._controlla_torneo(nome_torneo): return
        dlg = DialogPartecipante(parent=self, modifica=False, nome_torneo=nome_torneo)
        if dlg.exec_() != QDialog.Accepted: return
        d = dlg.dati
        soprannome = d.get("soprannome") or ""
        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [soprannome, nome_torneo])
        if not db.risultato.successo:
            msg_err(self, "Errore creazione squadra: " + db.risultato.get_msg());
            return
        id_ind = None
        if d.get("via"):
            id_ind = db.insert("indirizzo", ["via", "numero_civico", "cap", "citta"],
                               [d["via"], d["civico"], d["cap"], d["citta"]])
            if not db.risultato.successo:
                msg_err(self, "Errore indirizzo: " + db.risultato.get_msg());
                return
        db.insert("partecipante", ["nome", "cognome", "soprannome", "id_squadra", "id_indirizzo"],
                  [d["nome"], d["cognome"], soprannome, id_sq, id_ind])
        if not db.risultato.successo:
            msg_err(self, "Errore creazione partecipante: " + db.risultato.get_msg());
            return
        msg_ok(self, f"{d['nome']} {d['cognome']} iscritto a '{nome_torneo}'!")
        self._aggiorna()

    def _elimina_coppia(self):
        item = self.coppie_tree.currentItem()
        if not item or item.parent(): return
        id_squadra = item.data(0, Qt.UserRole)
        nome_coppia = item.text(0)
        pwd, ok = QInputDialog.getText(self, "Password", f"Password per '{nome_coppia}':", QLineEdit.Password)
        if not ok or pwd != PASSWORD_TORNEI: return
        if not msg_confirm(self, "Conferma", f"Eliminare la coppia '{nome_coppia}'?"): return
        db.delete("squadra", condizione=f"id_squadra = {id_squadra}")
        self._aggiorna()

    def _modifica_coppia_btn(self):
        item = self.coppie_tree.currentItem()
        if not item:
            msg_err(self, "Seleziona prima una coppia dalla lista."); return
        if item.parent():
            item = item.parent()
        self._modifica_coppia(item)

    def _elimina_attesa(self):
        item = self.coppie_tree.currentItem()
        if not item:
            msg_err(self, "Seleziona prima un giocatore dalla lista."); return
        if item.parent():
            item = item.parent()
        in_attesa = item.data(0, Qt.UserRole + 1)
        if not in_attesa:
            msg_err(self, "Puoi eliminare solo giocatori in attesa.\n"
                          "Le coppie già formate non possono essere eliminate da qui."); return
        id_squadra = item.data(0, Qt.UserRole)
        nome = item.text(0)
        pwd, ok = QInputDialog.getText(self, "Password richiesta",
                                       f"Password per eliminare '{nome}':",
                                       QLineEdit.Password)
        if not ok or pwd != PASSWORD_TORNEI:
            msg_err(self, "Password errata! Operazione annullata."); return
        if not msg_confirm(self, "Conferma", f"Eliminare '{nome}' dalla lista d'attesa?"):
            return
        db.delete("squadra", condizione=f"id_squadra = {id_squadra}")
        if not db.risultato.successo:
            msg_err(self, "Errore DB: " + db.risultato.get_msg()); return
        msg_ok(self, f"'{nome}' rimosso dalla lista d'attesa.")
        self._aggiorna()

    def _iscrivi_coppia(self):
        tornei = db.execute_select("SELECT nome FROM torneo WHERE singolo_doppio = 0 ORDER BY nome")
        if not tornei: return
        nomi = [t["nome"] for t in tornei]
        nome_torneo, ok = QInputDialog.getItem(self, "Scegli Torneo", "Torneo:", nomi, 0, False)
        if not ok or not self._controlla_torneo(nome_torneo): return
        dlg = DialogCoppia(parent=self, nome_torneo=nome_torneo)
        if dlg.exec_() == QDialog.Accepted: self._aggiorna()

    def _iscrivi_singolo_in_attesa(self):
        # 1. Recupero tornei
        tornei = db.execute_select("SELECT nome FROM torneo WHERE singolo_doppio = 0 ORDER BY nome")
        if not db.risultato.successo or not tornei:
            msg_err(self, "Nessun torneo a coppie disponibile.");
            return

        nomi = [t["nome"] for t in tornei]
        nome_torneo, ok = QInputDialog.getItem(self, "Scegli Torneo", "Torneo:", nomi, 0, False)
        if not ok or not self._controlla_torneo(nome_torneo): return

        # 2. Dialog partecipante
        dlg = DialogPartecipante(parent=self, modifica=False, nome_torneo=nome_torneo)
        if dlg.exec_() != QDialog.Accepted: return
        d = dlg.dati

        # Determiniamo il soprannome definitivo da controllare
        # Se l'utente non lo ha messo, usiamo Nome + Cognome
        soprannome_effettivo = (d.get("soprannome") or f"{d['nome']} {d['cognome']}").strip()

        # Prepariamo la stringa per la query SQL (gestione apostrofi)
        sop_sql = soprannome_effettivo.replace("'", "''")

        # 3. CONTROLLO DUPLICATO SOPRANNOME (Case Insensitive e Trimmed)
        check_sop = db.execute_select(f"""
            SELECT p.id_partecipante 
            FROM partecipante p
            JOIN squadra s ON p.id_squadra = s.id_squadra
            WHERE s.nome_torneo = '{nome_torneo}'
            AND LOWER(p.soprannome) = LOWER('{sop_sql}')
        """)

        if check_sop:
            msg_err(self, f"Il soprannome '{soprannome_effettivo}' è già in uso in questo torneo.\nScegline un altro.");
            return

        # 4. INSERIMENTO SQUADRA (La squadra prende il nome del soprannome del singolo)
        id_sq = db.insert("squadra", ["nome", "nome_torneo"], [soprannome_effettivo, nome_torneo])
        if not db.risultato.successo:
            msg_err(self, "Errore creazione squadra: " + db.risultato.get_msg());
            return

        # 5. INSERIMENTO INDIRIZZO (opzionale)
        id_ind = None
        if d.get("via"):
            id_ind = db.insert("indirizzo", ["via", "numero_civico", "cap", "citta"],
                               [d["via"], d["civico"], d["cap"], d["citta"]])
            if not db.risultato.successo:
                msg_err(self, "Errore indirizzo: " + db.risultato.get_msg());
                return

        # 6. INSERIMENTO PARTECIPANTE
        db.insert("partecipante",
                  ["nome", "cognome", "soprannome", "id_squadra", "id_indirizzo"],
                  [d["nome"], d["cognome"], soprannome_effettivo, id_sq, id_ind])

        if not db.risultato.successo:
            msg_err(self, "Errore creazione partecipante: " + db.risultato.get_msg());
            return

        msg_ok(self, f"{d['nome']} {d['cognome']} iscritto in attesa a '{nome_torneo}'!")
        self._aggiorna()

    def _abbina_singoli(self):
        tornei = db.execute_select("SELECT nome FROM torneo WHERE singolo_doppio = 0 ORDER BY nome")
        if not tornei: return
        nomi = [t["nome"] for t in tornei]
        nome_torneo, ok = QInputDialog.getItem(self, "Abbina Singoli", "Torneo:", nomi, 0, False)
        if not ok: return

        singoli = db.execute_select(
            f"SELECT s.id_squadra, p.nome AS nome_g, p.cognome AS cognome_g, p.soprannome AS soprannome_g, p.id_partecipante "
            f"FROM squadra s JOIN partecipante p ON p.id_squadra = s.id_squadra "
            f"WHERE s.nome_torneo = '{nome_torneo}' "
            f"AND (SELECT COUNT(*) FROM partecipante WHERE id_squadra = s.id_squadra) = 1 "
            f"ORDER BY s.id_squadra")

        if not singoli or len(singoli) < 2:
            msg_err(self, "Non ci sono abbastanza singoli in attesa per formare una coppia.");
            return

        import random as _random
        pool = list(singoli)
        _random.shuffle(pool)

        coppie_formate = []

        for i in range(0, len(pool) - 1, 2):
            g1, g2 = pool[i], pool[i + 1]
            nome_coppia = f"{g1['soprannome_g']} & {g2['soprannome_g']}"

            # Sposta il giocatore 2 nella squadra del giocatore 1
            db.execute_alt(
                f"UPDATE partecipante SET id_squadra = {g1['id_squadra']} WHERE id_partecipante = {g2['id_partecipante']}")

            # Rinomina la squadra del giocatore 1 con i nomi di entrambi
            db.execute_alt(f"UPDATE squadra SET nome = '{nome_coppia}' WHERE id_squadra = {g1['id_squadra']}")

            # Elimina la squadra (ora vuota) del giocatore 2
            db.delete("squadra", condizione=f"id_squadra = {g2['id_squadra']}")

            coppie_formate.append(nome_coppia)

        if coppie_formate:
            elenco = "\n".join([f"• {c}" for c in coppie_formate])
            msg_ok(self, f"Abbinamento completato con successo!\n\nCoppie formate:\n{elenco}")

        self._aggiorna()

    def _controlla_torneo(self, nome_torneo: str) -> bool:

        t_info = db.select_as_dict("torneo", condizione=f"nome = '{nome_torneo}'")
        if not t_info:
            msg_err(self, "Torneo non trovato.");
            return False
        t = t_info[0]

        # --- STATO: concluso o già iniziato (PRIMA del limite) ---
        ultimo = db.execute_select(
            f"SELECT fase FROM turno WHERE nome_torneo = '{nome_torneo}' ORDER BY numero DESC LIMIT 1"
        )
        if ultimo:
            fase = ultimo[0]["fase"]
            fasi_concluse = {"finale_1_2", "finale_3_4", "finale_5_6", "finale_7_8",
                             "finale_9_10", "finale_11_12", "finale_diretta_5_6", "finale_diretta_9_10"}
            if fase in fasi_concluse:
                giocata = db.execute_select(
                    f"SELECT ps.punteggio FROM turno t "
                    f"JOIN partita p ON p.id_turno = t.id_turno "
                    f"JOIN partita_squadra ps ON ps.id_partita = p.id_partita "
                    f"WHERE t.nome_torneo = '{nome_torneo}' AND t.fase = '{fase}' "
                    f"AND ps.punteggio IS NOT NULL LIMIT 1"
                )
                if giocata:
                    msg_err(self, f"Il torneo '{nome_torneo}' è già concluso.");
                    return False
            if "girone" in fase or "semifinale" in fase or "finale" in fase:
                msg_err(self, f"Il torneo '{nome_torneo}' è già iniziato.");
                return False

        # --- GIRONI ASSEGNATI ---
        gironi_ass = db.execute_select(
            f"SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = '{nome_torneo}' AND girone IS NOT NULL"
        )
        if gironi_ass and gironi_ass[0]["n"] > 0:
            msg_err(self, f"Il torneo '{nome_torneo}' è già iniziato.");
            return False

        # --- LIMITE PARTECIPANTI ---
        max_sq = t.get("max_squadre")
        if max_sq:
            res_count = db.execute_select(
                f"SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo = '{nome_torneo}'"
            )
            if res_count and res_count[0]['n'] >= int(max_sq):
                msg_err(self, f"Il torneo '{nome_torneo}' ha raggiunto il numero massimo di partecipanti ({max_sq}).");
                return False

        return True

    def _vedi_dettagli_partecipante_e_modifica(self, item: QTreeWidgetItem, column: int):
        id_part = int(item.text(0))
        res_dati = db.select_as_dict("partecipante AS p", colonne=["p.*", "IFNULL(i.via,'') AS via",
                                                                   "IFNULL(i.numero_civico,'') AS numero_civico",
                                                                   "IFNULL(i.cap,'') AS cap",
                                                                   "IFNULL(i.citta,'') AS citta"],
                                     join="LEFT JOIN indirizzo i ON i.id_indirizzo = p.id_indirizzo",
                                     condizione=f"p.id_partecipante = {id_part}")
        if not res_dati: return
        res_tornei = db.execute_select(
            f"SELECT DISTINCT t.nome FROM torneo t JOIN squadra s ON s.nome_torneo = t.nome JOIN partecipante p ON p.id_squadra = s.id_squadra WHERE p.id_partecipante = {id_part} ORDER BY t.nome")
        dlg = DialogDettagliPartecipante(parent=self, dati_partecipante=res_dati[0],
                                         tornei_iscritti=[t["nome"] for t in res_tornei])
        if dlg.exec_() == QDialog.Accepted: self._aggiorna()


# =============================================================================
# PANNELLO CLASSIFICA  (classifica_widget.ui)
# Chill: join singolo tramite partecipante.id_squadra (no squadra_partecipante)
# =============================================================================

class PannelloClassifica(QWidget):

    def __init__(self, torna_a_tornei_fn=None):
        print("CLASSIFICA __init__ start")
        super().__init__()
        print("CLASSIFICA super ok")
        uic.loadUi(UI_CLASSIFICA, self)
        print("CLASSIFICA ui ok")
        self._torna = torna_a_tornei_fn

        for col, w in enumerate([45, 240, 120, 90, 100, 110]):
            self.classifica_tree.setColumnWidth(col, w)
        print("CLASSIFICA colonne ok")

        self.combo_torneo.currentIndexChanged.connect(self._on_torneo_changed)
        print("CLASSIFICA combo ok")
        print("CLASSIFICA btn_refresh ok")
        self.btn_export_csv.clicked.connect(self._esporta_csv)
        print("CLASSIFICA btn_export_csv ok")
        self.btn_export_pdf.clicked.connect(self._esporta_pdf)
        print("CLASSIFICA init fine")

        self._reset_podio()

        super().__init__()
        uic.loadUi(UI_CLASSIFICA, self)
        self._torna = torna_a_tornei_fn

        for col, w in enumerate([45, 240, 120, 90, 100, 110]):
            self.classifica_tree.setColumnWidth(col, w)

        self.combo_torneo.currentIndexChanged.connect(self._on_torneo_changed)
        self.btn_export_csv.clicked.connect(self._esporta_csv)
        self.btn_export_pdf.clicked.connect(self._esporta_pdf)

        self._reset_podio()

    def carica_tornei(self, seleziona: str = None):
        self.combo_torneo.blockSignals(True)
        self.combo_torneo.clear()
        self.combo_torneo.addItem("Seleziona un torneo...")
        tornei = db.select_as_dict("torneo", colonne=["nome"])
        if db.risultato.successo and tornei:
            for t in tornei:
                self.combo_torneo.addItem(t["nome"])
        self.combo_torneo.blockSignals(False)
        if seleziona:
            idx2 = self.combo_torneo.findText(seleziona)
            if idx2 >= 0:
                self.combo_torneo.setCurrentIndex(idx2)


    def _on_torneo_changed(self):
        try:
            self._carica_classifica()
        except Exception as e:
            import traceback; traceback.print_exc()

    def _carica_classifica(self):
        self.combo_torneo.blockSignals(True)
        self.classifica_tree.clear()
        self._reset_podio()
        self._ferma_animazione_coppa()

        nome = self.combo_torneo.currentText()
        if not nome or nome.startswith("Seleziona"):
            self.combo_torneo.blockSignals(False)
            self._ferma_animazione_coppa()
            self.label_title.setText("📊 Classifica")
            self.label_title.setStyleSheet(
                "color: #2c3e50; font-family: Helvetica; font-size: 13pt; font-weight: bold;")
            self.classifica_tree.clear()
            self._reset_podio()

        torneo_info = db.select_as_dict("torneo", condizione=f"nome = '{nome}'")
        if not db.risultato.successo or not torneo_info:
            self.combo_torneo.blockSignals(False)
            return

        is_singolo = (str(torneo_info[0]["singolo_doppio"]) == "1")
        if is_singolo:
            etichetta_col = "p.nome"
            join_singolo  = "JOIN partecipante p ON p.id_squadra = s.id_squadra"
        else:
            etichetta_col = "s.nome"
            join_singolo  = ""

        _FINALE_POS = {
            "finale_1_2":         (1, 2),  "finale_3_4":   (3, 4),
            "finale_5_6":         (5, 6),  "finale_7_8":   (7, 8),
            "finale_9_10":        (9, 10), "finale_11_12": (11, 12),
            "finale_diretta_5_6": (5, 6),  "finale_diretta_9_10": (9, 10),
        }

        finali = db.execute_select(f"""
            SELECT tu.fase,
                   ps1.id_squadra AS id1, ps1.punteggio AS p1,
                   ps2.id_squadra AS id2, ps2.punteggio AS p2
            FROM   turno tu
            JOIN   partita         par ON par.id_turno    = tu.id_turno
            JOIN   partita_squadra ps1 ON ps1.id_partita  = par.id_partita
            JOIN   partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                       AND ps2.id_squadra  > ps1.id_squadra
            WHERE  tu.nome_torneo = '{nome}'
              AND  LEFT(tu.fase, 6) = 'finale'
              AND  ps1.punteggio IS NOT NULL
        """)

        posizioni = {}
        if db.risultato.successo and finali:
            for f in finali:
                if f["fase"] not in _FINALE_POS:
                    continue
                pos_v, pos_p = _FINALE_POS[f["fase"]]
                if f["p1"] > f["p2"]:
                    posizioni[f["id1"]] = pos_v
                    posizioni[f["id2"]] = pos_p
                else:
                    posizioni[f["id2"]] = pos_v
                    posizioni[f["id1"]] = pos_p

        stats_rows = db.execute_select(f"""
            SELECT ps.id_squadra,
                   COUNT(*) AS PG,
                   SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 1 ELSE 0 END) AS V,
                   SUM(CASE WHEN ps.punteggio = ps2.punteggio THEN 1 ELSE 0 END) AS Par,
                   COALESCE(SUM(ps.punteggio), 0) AS PF
            FROM   partita_squadra ps
            JOIN   partita_squadra ps2
                   ON  ps2.id_partita  = ps.id_partita
                   AND ps2.id_squadra != ps.id_squadra
            JOIN   partita par ON par.id_partita = ps.id_partita
            JOIN   turno   tu  ON tu.id_turno    = par.id_turno
            WHERE  tu.nome_torneo = '{nome}'
              AND  ps.punteggio  IS NOT NULL
            GROUP BY ps.id_squadra
        """)
        stats = {}
        if db.risultato.successo and stats_rows:
            for row in stats_rows:
                stats[row["id_squadra"]] = row

        righe = []

        if posizioni:
            et_rows = db.execute_select(f"""
                SELECT s.id_squadra, {etichetta_col} AS etichetta
                FROM   squadra s {join_singolo}
                WHERE  s.nome_torneo = '{nome}'
            """)
            etichette = {}
            if db.risultato.successo and et_rows:
                for row in et_rows:
                    etichette[row["id_squadra"]] = row["etichetta"]

            tutte = db.execute_select(
                f"SELECT id_squadra FROM squadra WHERE nome_torneo = '{nome}'"
            )
            if db.risultato.successo and tutte:
                ids_escluse = {r["id_squadra"] for r in tutte} - set(posizioni)
                if ids_escluse:
                    ids_str = ", ".join(str(i) for i in ids_escluse)
                    exc_rows = db.execute_select(f"""
                        SELECT ps.id_squadra,
                               SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 3
                                        WHEN ps.punteggio = ps2.punteggio THEN 1
                                        ELSE 0 END) AS punti_class,
                               COALESCE(SUM(ps.punteggio), 0) AS PF,
                               COALESCE(SUM(ps2.punteggio), 0) AS PS
                        FROM   partita_squadra ps
                        JOIN   partita_squadra ps2
                               ON  ps2.id_partita  = ps.id_partita
                               AND ps2.id_squadra != ps.id_squadra
                        JOIN   partita par ON par.id_partita = ps.id_partita
                        JOIN   turno   tu  ON tu.id_turno    = par.id_turno
                        WHERE  tu.nome_torneo = '{nome}'
                          AND  tu.fase LIKE 'girone%'
                          AND  ps.punteggio IS NOT NULL
                          AND  ps.id_squadra IN ({ids_str})
                        GROUP BY ps.id_squadra
                    """)
                    escluse = []
                    ids_trovati = set()
                    if db.risultato.successo and exc_rows:
                        for row in exc_rows:
                            escluse.append({
                                "id": row["id_squadra"],
                                "punti_class": row["punti_class"] or 0,
                                "PF": row["PF"] or 0,
                                "PS": row["PS"] or 0,
                            })
                            ids_trovati.add(row["id_squadra"])
                    for sid in ids_escluse - ids_trovati:
                        escluse.append({"id": sid, "punti_class": 0, "PF": 0, "PS": 0})
                    escluse.sort(key=lambda x: (
                        -x["punti_class"],
                        -(x["PF"] / x["PS"]) if x["PS"] > 0 else 0,
                    ))
                    next_pos = max(posizioni.values()) + 1
                    for i, team in enumerate(escluse):
                        posizioni[team["id"]] = next_pos + i

            for pos in sorted(set(posizioni.values())):
                for sq_id, p in posizioni.items():
                    if p != pos:
                        continue
                    st = stats.get(sq_id, {})
                    righe.append({
                        "etichetta": etichette.get(sq_id, f"ID{sq_id}"),
                        "partite":   st.get("PG", 0),
                        "vittorie":  st.get("V",  0),
                        "pareggi":   st.get("Par", 0),
                        "punti":     st.get("PF", 0),
                        "_pos":      pos,
                    })
        else:
            raw = db.execute_select(f"""
                SELECT {etichetta_col} AS etichetta,
                       COUNT(DISTINCT ps.id_partita) AS partite,
                       SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 1 ELSE 0 END) AS vittorie,
                       SUM(CASE WHEN ps.punteggio = ps2.punteggio THEN 1 ELSE 0 END) AS pareggi,
                       COALESCE(SUM(ps.punteggio), 0) AS punti
                FROM   squadra AS s
                {join_singolo}
                LEFT JOIN partita_squadra AS ps  ON ps.id_squadra  = s.id_squadra
                LEFT JOIN partita         AS par ON par.id_partita  = ps.id_partita
                LEFT JOIN partita_squadra AS ps2
                    ON ps2.id_partita = ps.id_partita AND ps2.id_squadra != s.id_squadra
                WHERE  s.nome_torneo = '{nome}'
                GROUP BY s.id_squadra {("," + etichetta_col) if is_singolo else ""}
                ORDER BY punti DESC, vittorie DESC
            """)
            if not db.risultato.successo or not raw:
                self.combo_torneo.blockSignals(False)
                return
            righe = [{**r, "pareggi": r.get("pareggi", 0), "_pos": i + 1} for i, r in enumerate(raw)]

        self.combo_torneo.blockSignals(False)

        if not righe:
            return

        # Determina stato torneo
        fasi_concluse = {"finale_1_2","finale_3_4","finale_5_6","finale_7_8",
                         "finale_9_10","finale_11_12","finale_diretta_5_6","finale_diretta_9_10"}
        if posizioni and any(
            f["fase"] in fasi_concluse for f in (finali or [])
        ):
            stato_label = "🏆 Classifica Finale"
            colore = "#1abc9c"
        elif posizioni:
            stato_label = "⚡ Classifica Parziale — Playoff in corso"
            colore = "#e67e22"
        else:
            stato_label = "📊 Classifica Parziale — Gironi in corso"
            colore = "#2e86c1"

        self.label_title.setText(f"{nome}  —  {stato_label}")
        self.label_title.setStyleSheet(f"color: {colore}; font-family: Helvetica; font-size: 13pt; font-weight: bold;")

        max_pos_playoff = max(posizioni.values()) if posizioni else 0

        for r in righe:
            etichetta = r["etichetta"]
            if posizioni and r["_pos"] > max_pos_playoff:
                etichetta = "❌  " + etichetta

            valori = [str(r["_pos"]), etichetta, str(r["partite"]),
                      str(r["vittorie"]), str(r["pareggi"]), str(r["punti"])]
            item = QTreeWidgetItem(valori)
            for c in [0, 2, 3, 4, 5]:
                item.setTextAlignment(c, Qt.AlignCenter)
            self.classifica_tree.addTopLevelItem(item)

        self._aggiorna_podio(righe)
        # Animazione coppa solo se torneo concluso
        if posizioni and any(f["fase"] in fasi_concluse for f in (finali or [])):
            self._avvia_animazione_coppa()


    def _avvia_animazione_coppa(self):
        from PyQt5.QtCore import QTimer
        self._coppa_frames = ["🏆", "👑", "🏆", "✨", "🏆", "⭐", "🏆", "✨"]
        self._coppa_idx = 0
        if not hasattr(self, '_coppa_timer'):
            self._coppa_timer = QTimer(self)
            self._coppa_timer.timeout.connect(self._step_animazione_coppa)
        self._coppa_timer.start(400)

    def _step_animazione_coppa(self):
        frame = self._coppa_frames[self._coppa_idx % len(self._coppa_frames)]
        self.label_1st_medal.setText(frame)
        self._coppa_idx += 1

    def _ferma_animazione_coppa(self):
        if hasattr(self, '_coppa_timer') and self._coppa_timer.isActive():
            self._coppa_timer.stop()
        self.label_1st_medal.setText("🥇")

    def _reset_podio(self):
        self.label_1st_name.setText("—");  self.label_1st_score.setText("0 pt")
        self.label_2nd_name.setText("—");  self.label_2nd_score.setText("0 pt")
        self.label_3rd_name.setText("—");  self.label_3rd_score.setText("0 pt")

    def _aggiorna_podio(self, righe):
        self.score_ = [
            (0, self.label_1st_name, self.label_1st_score),
            (1, self.label_2nd_name, self.label_2nd_score),
            (2, self.label_3rd_name, self.label_3rd_score),
        ]
        for idx, lbl_n, lbl_s in self.score_:
            if idx < len(righe):
                lbl_n.setText(righe[idx]["etichetta"])
                lbl_s.setText(f"{righe[idx]['punti']} pt")
            else:
                lbl_n.setText("—"); lbl_s.setText("0 pt")

    def _esporta_csv(self):
        nome_torneo = self.combo_torneo.currentText()
        if nome_torneo.startswith("Seleziona"):
            msg_err(self, "Seleziona prima un torneo."); return
        nome_file = f"classifica_{nome_torneo.replace(' ', '_')}.csv"
        try:
            with open(nome_file, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["#", "Squadra/Giocatore", "Partite", "Vittorie", "Sconfitte", "Punti"])
                root = self.classifica_tree.invisibleRootItem()
                for i in range(root.childCount()):
                    item = root.child(i)
                    w.writerow([item.text(c) for c in range(6)])
            msg_ok(self, f"Classifica esportata in:\n{os.path.abspath(nome_file)}")
        except Exception as e:
            msg_err(self, f"Errore esportazione CSV:\n{e}")

    def _esporta_pdf(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        nome_torneo = self.combo_torneo.currentText()
        if nome_torneo.startswith("Seleziona"):
            msg_err(self, "Seleziona prima un torneo."); return

        nome_file = f"classifica_{nome_torneo.replace(' ', '_')}.pdf"
        try:
            doc = SimpleDocTemplate(nome_file, pagesize=A4)
            styles = getSampleStyleSheet()
            elementi = []
            elementi.append(Paragraph(f"Classifica — {nome_torneo}", styles["Title"]))
            elementi.append(Spacer(1, 12))

            intestazioni = ["#", "Squadra/Giocatore", "Partite", "Vittorie", "Sconfitte", "Punti"]
            dati = [intestazioni]
            root = self.classifica_tree.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                dati.append([item.text(c) for c in range(6)])

            tabella = Table(dati, repeatRows=1)
            tabella.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elementi.append(tabella)
            doc.build(elementi)
            msg_ok(self, f"PDF esportato in:\n{os.path.abspath(nome_file)}")
        except Exception as e:
            msg_err(self, f"Errore esportazione PDF:\n{e}")


# =============================================================================
# PANNELLO PARTITE  (partite_widget.ui)
# Chill: niente data/orario in partita; niente squadra_partecipante
# =============================================================================

# === TROVA QUESTA PARTE NEL TUO FILE E SOSTITUISCILA ===

from PyQt5.QtWidgets import QTableWidgetItem  # Assicurati che sia importato in alto


class PannelloPartite(QWidget):

    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(UI_PARTITE, self)
        except Exception as e:
            print(f"Errore nel caricamento del file UI: {e}")
            return

        # --- ADATTAMENTO AI TUOI NOMI REALI ---
        # Nel tuo UI si chiama 'tbl_calendario' ed è una TableWidget, non un Tree
        self.partite_table = getattr(self, "tbl_calendario", None)
        self.combo_filter_torneo = getattr(self, "cmb_tornei", None)

        # Se questi mancano, creiamo dei puntatori a None per evitare crash
        self.combo_filter_turno = getattr(self, "combo_filter_turno", None)
        self.combo_filter_fase = getattr(self, "combo_filter_fase", None)
        self.btn_reset_filter = getattr(self, "btn_reset_filter", None)

        if self.partite_table is None:
            print("ATTENZIONE: 'tbl_calendario' non trovato nel file UI!")
            return

        # Configurazione colonne per QTableWidget
        self.partite_table.setColumnCount(9)
        self.partite_table.setHorizontalHeaderLabels([
            "ID", "Torneo", "Fase", "Turno", "Luogo", "Squadra 1", "Risultato", "Squadra 2", "Stato"
        ])

        # Collegamento eventi
        if self.combo_filter_torneo:
            self.combo_filter_torneo.currentIndexChanged.connect(self.carica)

        if self.btn_reset_filter:
            self.btn_reset_filter.clicked.connect(self._reset_filtri)

        self._carica_combo_tornei()
        self.carica()

    def _carica_combo_tornei(self):
        if not self.combo_filter_torneo: return
        self.combo_filter_torneo.blockSignals(True)
        self.combo_filter_torneo.clear()
        self.combo_filter_torneo.addItem("Tutti i tornei")
        lista = db.select_as_dict("torneo")
        if db.risultato.successo and lista:
            for t in lista:
                self.combo_filter_torneo.addItem(t["nome"])
        self.combo_filter_torneo.blockSignals(False)

    def carica(self):
        if not self.partite_table: return
        self.partite_table.setRowCount(0)  # Pulisce la tabella

        if not self.combo_filter_torneo: return
        torneo = self.combo_filter_torneo.currentText()
        if torneo == "Tutti i tornei": return

        # Query (rimane uguale)
        query = f"""
            SELECT  t.fase, t.numero AS turno,
                    par.id_partita, par.luogo,
                    ps1.id_squadra AS id1, ps1.punteggio AS p1,
                    ps2.id_squadra AS id2, ps2.punteggio AS p2
            FROM    turno t
            JOIN    partita         par ON par.id_turno    = t.id_turno
            JOIN    partita_squadra ps1 ON ps1.id_partita  = par.id_partita
            JOIN    partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                       AND ps2.id_squadra   > ps1.id_squadra
            WHERE   t.nome_torneo = '{torneo}'
            ORDER BY t.numero ASC
        """
        righe = db.execute_select(query)
        if not db.risultato.successo or not righe: return

        # Caricamento dati nella Tabella
        for row_idx, r in enumerate(righe):
            self.partite_table.insertRow(row_idx)

            # Prepariamo i dati da mostrare
            punteggio = f"{r['p1']} - {r['p2']}" if r['p1'] is not None else "N.D."
            stato = "✅" if r['p1'] is not None else "⚠️"

            dati_riga = [
                str(r["id_partita"]),
                torneo,
                str(r["fase"]),
                str(r["turno"]),
                str(r["luogo"] or ""),
                f"Squadra {r['id1']}",  # Sostituire con nomi reali se necessario
                punteggio,
                f"Squadra {r['id2']}",
                stato
            ]

            for col_idx, testo in enumerate(dati_riga):
                item = QTableWidgetItem(testo)
                item.setTextAlignment(Qt.AlignCenter)
                self.partite_table.setItem(row_idx, col_idx, item)

    def _reset_filtri(self):
        if self.combo_filter_torneo:
            self.combo_filter_torneo.setCurrentIndex(0)
        self.carica()

# =============================================================================
# FINESTRA PRINCIPALE  (m_w.ui)
# =============================================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi(UI_MAIN, self)

        from home_widget import PannelloHome

        self._p_partecipanti = PannelloPartecipanti()
        self._p_tornei = PannelloTornei(
            apri_classifica_fn=self._vai_classifica_torneo,
            on_delete_cb=self._p_partecipanti._aggiorna
        )
        self._p_classifica = PannelloClassifica(
            torna_a_tornei_fn=self._vai_tornei
        )
        self._p_partite = PannelloPartite()
        self._p_home = PannelloHome()

        for p in [self._p_tornei, self._p_partecipanti,
                  self._p_classifica, self._p_partite, self._p_home]:
            self.stackedWidget.addWidget(p)

        self.btn_list_tournaments.clicked.connect(self._vai_tornei)
        self.btn_manage_players.clicked.connect(self._vai_partecipanti)
        self.btn_manage_matches.clicked.connect(self._vai_partite)
        self.btn_dashboard.clicked.connect(
            lambda: [self._p_home.aggiorna(),
                     self.stackedWidget.setCurrentWidget(self._p_home)]
        )
        self.btn_exit_app.clicked.connect(self.close)

        self.stackedWidget.setCurrentWidget(self.page_home)

    def _vai_tornei(self):
        self._p_tornei.carica()
        self.stackedWidget.setCurrentWidget(self._p_tornei)

    def _vai_partecipanti(self):
        # Questi due metodi sono già chiamati dentro _aggiorna,
        # ma tenerli qui per sicurezza quando si cambia tab va bene.
        self._p_partecipanti._carica_tornei_combo()
        self._p_partecipanti.carica()
        self.stackedWidget.setCurrentWidget(self._p_partecipanti)

    def _vai_classifica_torneo(self, nome_torneo: str = None):
        self._p_classifica.carica_tornei(seleziona=nome_torneo)
        self.stackedWidget.setCurrentWidget(self._p_classifica)

    def _vai_partite(self):
        # Forza il ricaricamento dei tornei ogni volta che si clicca il tasto
        if hasattr(self._p_partite, "_carica_combo_tornei"):
            self._p_partite._carica_combo_tornei()
        self._p_partite.carica()
        self.stackedWidget.setCurrentWidget(self._p_partite)




# =============================================================================
# ENTRY POINT
# La GUI si apre e si chiude senza terminare il processo Python (menu CLI vivo)
# =============================================================================

def frg():
    app = QApplication.instance() or QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec_()
