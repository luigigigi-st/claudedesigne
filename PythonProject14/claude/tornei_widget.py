from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QMessageBox, QPushButton, QDialog,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from config import db, print_errore
from partecipanti import _conta_iscritti
from classifica_widget import ClassificaWidget

UI_PATH = "claude/tornei_w.ui"

_STATO_COLORS = {
    "iscrizioni_aperte": ("#d5f5e3", "#1e8449"),
    "attesa":            ("#fef9e7", "#b7950b"),
    "gironi":            ("#d6eaf8", "#1a5276"),
    "playoff":           ("#e8daef", "#6c3483"),
    "concluso":          ("#f2f3f4", "#717d7e"),
}


class TorneiWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            print(f"[TorneiWidget] Errore caricamento UI: {e}")
            return

        self._tree: QTreeWidget = self.findChild(QTreeWidget, "tournament_tree")

        self._carica_tornei()

        for btn in self.findChildren(QPushButton):
            txt = btn.text().strip().lower()
            if any(k in txt for k in ("aggiungi", "nuovo")):
                btn.clicked.connect(self._aggiungi_torneo)
            elif "elimina" in txt:
                btn.clicked.connect(self._elimina_torneo)
            elif any(k in txt for k in ("classifica",)):
                btn.clicked.connect(self._vedi_classifica)

        # filtro in tempo reale
        filter_edit = self.findChild(QLineEdit, "entry_tournament_name_list")
        if filter_edit:
            filter_edit.textChanged.connect(self._filtra)

    # ───────────────────────────────────────────────────────────────────
    def _carica_tornei(self):
        if not self._tree:
            return
        self._tree.clear()

        tornei = db.select_as_dict("torneo") or []

        from tornei import _calcola_stato_torneo

        for t in tornei:
            nome    = t.get("nome", "")
            singolo = t.get("singolo_doppio", 1)
            tipo    = "Singolo" if singolo == 1 else "Doppio"
            quota   = t.get("quota_iscrizione")
            email   = t.get("email_iscrizioni") or "-"
            max_sq  = t.get("max_squadre")
            iscritti = _conta_iscritti(nome, singolo == 1)

            stato_key = "iscrizioni_aperte"
            stato_label = "Iscrizioni APERTE"
            try:
                stato_key = _calcola_stato_torneo(t)
                mapping = {
                    "iscrizioni_aperte": "Iscrizioni APERTE",
                    "attesa":            "Fase GIRONI in attesa",
                    "gironi":            "Fase GIRONI in corso",
                    "playoff":           "Playoff in corso",
                    "concluso":          "Torneo CONCLUSO",
                }
                stato_label = mapping.get(stato_key, str(stato_key))
            except Exception:
                pass

            quota_str = f"{quota:.2f} €" if isinstance(quota, (int, float)) and quota > 0 else "Gratuito"
            max_str   = str(max_sq) if max_sq else "Illimitato"

            item = QTreeWidgetItem([
                nome, tipo, email, quota_str, max_str, str(iscritti), stato_label
            ])

            bg, fg = _STATO_COLORS.get(stato_key, ("#ffffff", "#000000"))
            for col in range(7):
                item.setTextAlignment(col, Qt.AlignLeft | Qt.AlignVCenter)
            # colora solo colonna Stato
            item.setBackground(6, QBrush(QColor(bg)))
            item.setForeground(6, QBrush(QColor(fg)))

            self._tree.addTopLevelItem(item)

        for col in range(self._tree.columnCount()):
            self._tree.resizeColumnToContents(col)

    def _filtra(self, testo: str):
        testo = testo.strip().lower()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            item.setHidden(testo not in item.text(0).lower())

    def _get_selected_torneo(self) -> str | None:
        if not self._tree:
            return None
        item = self._tree.currentItem()
        if item is None:
            return None
        return item.text(0)

    # ───────────────────────────────────────────────────────────────────
    def _aggiungi_torneo(self):
        dialog = QDialog(self)
        try:
            uic.loadUi("claude/tournament_dialog.ui", dialog)
        except Exception as e:
            QMessageBox.critical(self, "Errore UI", f"Impossibile caricare dialog torneo: {e}")
            return

        if dialog.exec_() != QDialog.Accepted:
            return

        nome_edit = dialog.findChild(QLineEdit, "entry_nome")
        nome = nome_edit.text().strip() if nome_edit else ""
        if not nome:
            QMessageBox.warning(self, "Errore", "Nome del torneo è obbligatorio.")
            return

        combo_tipo = dialog.findChild(QComboBox, "combo_tipo")
        singolo_doppio = 1
        if combo_tipo:
            singolo_doppio = 1 if "sing" in combo_tipo.currentText().lower() else 0

        spin_quota = dialog.findChild(QDoubleSpinBox, "spin_quota")
        quota = spin_quota.value() if spin_quota else 0.0

        spin_max = dialog.findChild(QSpinBox, "spin_max")
        max_sq = spin_max.value() if spin_max else 0
        if max_sq == 0:
            max_sq = None

        email_edit = dialog.findChild(QLineEdit, "entry_email")
        email = email_edit.text().strip() if email_edit else None
        if not email:
            email = None

        db.start_transaction()
        try:
            db.insert(
                "torneo",
                ["nome", "singolo_doppio", "quota_iscrizione", "email_iscrizioni", "max_squadre"],
                [nome, singolo_doppio, quota, email, max_sq],
            )
            db.commit_transaction()
            self._carica_tornei()
        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(self, "Errore", str(e))

    def _elimina_torneo(self):
        nome = self._get_selected_torneo()
        if not nome:
            QMessageBox.information(self, "Elimina", "Seleziona un torneo da eliminare.")
            return
        if QMessageBox.question(
            self, "Conferma eliminazione",
            f"Eliminare il torneo '{nome}'?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        pwd, ok = QInputDialog.getText(
            self, "Password amministratore", "Inserisci password:", QLineEdit.Password
        )
        if not ok or pwd != getattr(__import__('config'), 'PASSWORD_TORNEI', ''):
            QMessageBox.warning(self, "Errore", "Password errata.")
            return
        db.start_transaction()
        try:
            db.delete("torneo", condizione="nome = %s", params=(nome,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.commit_transaction()
            self._carica_tornei()
        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(self, "Errore", str(e))

    def _vedi_classifica(self):
        nome = self._get_selected_torneo()
        if not nome:
            QMessageBox.information(self, "Classifica", "Seleziona un torneo per la classifica.")
            return
        cw = ClassificaWidget()
        cw.seleziona_e_carica(nome)
        cw.show()
