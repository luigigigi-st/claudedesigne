from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QInputDialog, QLineEdit, QPushButton, QDoubleSpinBox, QComboBox, QSpinBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import os

# Se impostato da main.py, viene chiamato invece di _popola_tornei(ui_widget) dopo ogni modifica
_refresh_override = None

from config import db
from partecipanti import _conta_iscritti
from tornei import _calcola_stato_torneo
from classifica_widget import ClassificaWidget


def _refresh(ui_widget):
    if _refresh_override is not None:
        _refresh_override()
    else:
        _popola_tornei(ui_widget)


def _chiudi_dialog(dialog: QDialog):
    try:
        dialog.close()
    except Exception:
        pass


_COLONNE_WIDTHS = [200, 80, 175, 85, 85, 75, 180]

_STATO_COLORI = {
    "apert":    QColor("#27ae60"),
    "attesa":   QColor("#f1c40f"),
    "gironi":   QColor("#1abc9c"),
    "playoff":  QColor("#e67e22"),
    "concluso": QColor("#95a5a6"),
}

def _popola_tornei(ui_widget: QtWidgets.QWidget):
    tree = ui_widget.findChild(QtWidgets.QTreeWidget, "tournament_tree")
    if tree is None:
        return

    # salva stato corrente
    selected_nome = None
    if tree.selectedItems():
        selected_nome = tree.selectedItems()[0].text(0)
    hscroll = tree.horizontalScrollBar().value()
    vscroll = tree.verticalScrollBar().value()
    first_load = tree.topLevelItemCount() == 0

    tree.setUpdatesEnabled(False)
    tree.clear()

    headers = ["Nome", "Tipo", "Email Iscrizioni", "Quota", "Max Iscr.", "Iscritti", "Stato"]
    if tree.columnCount() != len(headers):
        tree.setColumnCount(len(headers))
        tree.setHeaderLabels(headers)

    tornei = db.select_as_dict("torneo") or []
    item_da_selezionare = None

    for t in tornei:
        nome = t.get("nome", "")
        singolo = t.get("singolo_doppio", 1)
        tipo = "singolo" if str(singolo) == "1" else "doppio"
        quota = t.get("quota_iscrizione")
        email = t.get("email_iscrizioni")
        max_squadre = t.get("max_squadre")
        iscritti = _conta_iscritti(nome, singolo == 1)

        stato_key = _calcola_stato_torneo({"nome": nome, "singolo_doppio": singolo})
        stato = {
            "iscrizioni_aperte": "Iscrizioni APERTE",
            "attesa": "Fase GIRONI in attesa",
            "gironi": "Fase GIRONI in corso",
            "playoff": "Fase PLAYOFF in corso",
            "concluso": "Torneo CONCLUSO",
        }.get(stato_key, str(stato_key))

        row = [nome, tipo, email or "-",
               str(quota) if quota is not None else "-",
               str(max_squadre) if max_squadre is not None else "-",
               str(iscritti), stato]
        item = QTreeWidgetItem(row)

        stato_lower = stato.lower()
        color = next((c for k, c in _STATO_COLORI.items() if k in stato_lower), QColor("#2c3e50"))
        item.setForeground(6, color)

        tree.addTopLevelItem(item)
        if nome == selected_nome:
            item_da_selezionare = item

    # ridimensiona colonne solo al primo caricamento
    if first_load:
        for i, w in enumerate(_COLONNE_WIDTHS):
            tree.setColumnWidth(i, w)

    tree.setUpdatesEnabled(True)

    # ripristina selezione e posizione scroll
    if item_da_selezionare:
        tree.setCurrentItem(item_da_selezionare)
    tree.horizontalScrollBar().setValue(hscroll)
    tree.verticalScrollBar().setValue(vscroll)


def _aggiungi_torneo(ui_widget: QtWidgets.QWidget):
    dialog = QDialog(ui_widget)
    # try to load claude/tournament_dialog.ui
    from PyQt5 import uic
    loaded = False
    for path in ["claude/tournament_dialog.ui", "tournament_dialog.ui"]:
        if os.path.exists(path):
            try:
                uic.loadUi(path, dialog)
                loaded = True
                break
            except Exception:
                continue
    if not loaded:
        QMessageBox.critical(ui_widget, "Errore UI", "Impossibile caricare la finestra di inserimento dati per torneo.")
        return
    # Collega i pulsanti Salva/Annulla se presenti
    btn_cancel = dialog.findChild(QPushButton, "btn_cancel")
    if btn_cancel:
        btn_cancel.clicked.connect(dialog.reject)
    btn_save = dialog.findChild(QPushButton, "btn_save")
    if btn_save:
        btn_save.clicked.connect(dialog.accept)
    if dialog.exec_() != QDialog.Accepted:
        return
    data = {}
    # testo vecchio: leggere nomi/ot form
    for w in dialog.findChildren(QLineEdit):
        name = w.objectName().lower()
        if "nome" in name:
            data["nome"] = w.text().strip()
        elif "email" in name:
            data["email_iscrizioni"] = w.text().strip()
    # read quota dal spin
    spin_quota = dialog.findChild(QDoubleSpinBox, "spin_quota")
    if spin_quota is not None:
        data["quota_iscrizione"] = float(spin_quota.value())
    # read max dal spin
    spin_max = dialog.findChild(QSpinBox, "spin_max")
    if spin_max is not None:
        try:
            maxv = int(spin_max.value())
            data["max_squadre"] = maxv if maxv > 0 else None
        except Exception:
            data["max_squadre"] = None
    # tipo: combo_tipo
    combo_tipo = dialog.findChild(QComboBox, "combo_tipo")
    if combo_tipo is not None:
        t = combo_tipo.currentText().lower()
        data["singolo_doppio"] = 1 if 'sing' in t or 'solo' in t else 0
    else:
        data["singolo_doppio"] = 0
    singolo = data.get("singolo_doppio", 1) and 1 or 0
    # Valida non vuoto anche in modifica
    if data.get("nome") is not None and (str(data.get("nome")).strip() == ""):
        QMessageBox.warning(ui_widget, "Errore", "Il Nome del torneo non può essere vuoto.")
        return
    # Valida nome non vuoto
    if not data.get("nome") or data["nome"].strip() == "":
        QMessageBox.warning(ui_widget, "Errore", "Il Nome del torneo non può essere vuoto.")
        return
    for cb in dialog.findChildren(QPushButton):
        pass
    # insert
    if not data.get("nome") or data["nome"].strip() == "":
        QMessageBox.warning(ui_widget, "Errore", "Il Nome del torneo non può essere vuoto.")
        return
    # Check for duplicate tournament name before inserting
    try:
        dup_check = db.select_as_dict("torneo", colonne=["nome"], condizione="nome = %s", params=(data.get("nome"),))
        if db.risultato.successo and dup_check:
            Q = data.get("nome")
            QMessageBox.warning(ui_widget, "Duplicato", f"Esiste già un torneo chiamato '{Q}'. Inserimento annullato.")
            return
    except Exception:
        # If the check fails, proceed with insert (to avoid blocking generation)
        pass
    db.start_transaction()
    try:
        db.insert("torneo", ["nome", "singolo_doppio", "quota_iscrizione", "email_iscrizioni", "max_squadre"],
                  [data.get("nome"), singolo, data.get("quota_iscrizione"), data.get("email_iscrizioni"), data.get("max_squadre")])
        db.commit_transaction()
        _refresh(ui_widget)
    except Exception as e:
        db.rollback_transaction()
        QMessageBox.critical(ui_widget, "Errore", str(e))


def _modifica_torneo(ui_widget: QtWidgets.QWidget):
    tree = ui_widget.findChild(QtWidgets.QTreeWidget, "tournament_tree")
    if not tree:
        return
    items = tree.selectedItems()
    if not items:
        QMessageBox.information(ui_widget, "Modifica", "Seleziona un torneo da modificare.")
        return
    nome = items[0].text(0)
    dialog = QDialog(ui_widget)
    from PyQt5 import uic
    loaded = False
    for path in ["claude/tournament_dialog.ui", "tournament_dialog.ui"]:
        if os.path.exists(path):
            try:
                uic.loadUi(path, dialog)
                loaded = True
                break
            except Exception:
                continue
    if not loaded:
        QMessageBox.critical(ui_widget, "Errore UI", "Impossibile caricare la finestra di modifica torneo.")
        return
    # connect Save/Cancel on modify dialog if present
    btn_cancel = dialog.findChild(QPushButton, "btn_cancel")
    if btn_cancel:
        btn_cancel.clicked.connect(dialog.reject)
    btn_save = dialog.findChild(QPushButton, "btn_save")
    if btn_save:
        btn_save.clicked.connect(dialog.accept)
    row = db.select_as_dict("torneo", condizione="nome = %s", params=(nome,))
    if row:
        t = row[0]
        for w in dialog.findChildren(QLineEdit):
            n = w.objectName().lower()
            if "nome" in n:
                w.setText(t.get("nome", ""))
            elif "quota" in n:
                v = t.get("quota_iscrizione")
                w.setText(str(v) if v else "")
            elif "email" in n:
                w.setText(t.get("email_iscrizioni", ""))
            elif "max" in n:
                v = t.get("max_squadre")
                w.setText(str(v) if v is not None else "")
    if dialog.exec_() != QDialog.Accepted:
        return
    data = {}
    for w in dialog.findChildren(QLineEdit):
        name = w.objectName().lower()
        if "nome" in name:
            data["nome"] = w.text().strip()
        elif "quota" in name:
            raw_q = w.text().strip()
            if raw_q:
                try:
                    q_val = float(raw_q)
                    if q_val <= 0:
                        raise ValueError
                    data["quota_iscrizione"] = q_val
                except ValueError:
                    QMessageBox.warning(ui_widget, "Errore", "La quota deve essere un valore positivo (> 0).")
                    return
            else:
                data["quota_iscrizione"] = 0
        elif "email" in name:
            data["email_iscrizioni"] = w.text().strip()
        elif "max" in name:
            try:
                data["max_squadre"] = int(w.text().strip())
            except Exception:
                data["max_squadre"] = None
    # guard duplicate on rename when modifying
    new_nome = data.get("nome", None)
    if new_nome and new_nome.strip() != "" and new_nome.strip() != nome:
        try:
            rdupe = db.select_as_dict("torneo", colonne=["nome"], condizione="nome = %s", params=(new_nome,))
            if db.risultato.successo and rdupe:
                QMessageBox.warning(ui_widget, "Duplicato", f"Esiste già un torneo chiamato '{new_nome}'. Modifica annullata.")
                return
        except Exception:
            pass
    singolo = data.get("singolo_doppio", 1) and 1 or 0
    db.start_transaction()
    try:
        db.execute_alt(
            "UPDATE torneo SET singolo_doppio = %s, quota_iscrizione = %s, email_iscrizioni = %s, max_squadre = %s WHERE nome = %s",
            params=(data.get("singolo_doppio", singolo), data.get("quota_iscrizione", 0), data.get("email_iscrizioni"), data.get("max_squadre"), nome)
        )
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())
        db.commit_transaction()
        _refresh(ui_widget)
    except Exception as e:
        db.rollback_transaction()
        QMessageBox.critical(ui_widget, "Errore", str(e))


def _elimina_torneo(ui_widget: QtWidgets.QWidget):
    tree = ui_widget.findChild(QtWidgets.QTreeWidget, "tournament_tree")
    if not tree:
        return
    items = tree.selectedItems()
    if not items:
        QMessageBox.information(ui_widget, "Elimina", "Seleziona un torneo da eliminare.")
        return
    nome = items[0].text(0)
    if QMessageBox.question(ui_widget, "Conferma eliminazione", f"Eliminare il torneo '{nome}'?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
        return
    from config import PASSWORD_TORNEI
    pwd, ok = QInputDialog.getText(ui_widget, "Password amministratore", "Inserisci password:", echo=QtWidgets.QLineEdit.Password)
    if not ok or pwd != PASSWORD_TORNEI:
        QMessageBox.warning(ui_widget, "Errore", "Password errata.")
        return
    db.start_transaction()
    try:
        db.delete("torneo", condizione="nome = %s", params=(nome,))
        if not db.risultato.successo:
            raise Exception(db.risultato.get_msg())
        db.commit_transaction()
        _refresh(ui_widget)
    except Exception as e:
        db.rollback_transaction()
        QMessageBox.critical(ui_widget, "Errore", str(e))


def _vedi_classifica(ui_widget: QtWidgets.QWidget):
    tree = ui_widget.findChild(QtWidgets.QTreeWidget, "tournament_tree")
    if not tree:
        return
    items = tree.selectedItems()
    if not items:
        QMessageBox.information(ui_widget, "Classifica", "Seleziona un torneo per la classifica.")
        return
    nome = items[0].text(0)
    w = ClassificaWidget()
    w.seleziona_e_carica(nome)
    w.show()


def connect_tornei_bridge(ui_widget: QtWidgets.QWidget):
    """Collega la UI claude/tornei_w.ui alle azioni di DB senza toccare i file esistenti."""
    # popola inizialmente
    _popola_tornei(ui_widget)

    # connect bottoni
    btn_add = ui_widget.findChild(QPushButton, "btn_add")
    if btn_add:
        btn_add.clicked.connect(lambda: _aggiungi_torneo(ui_widget))

    btn_edit = ui_widget.findChild(QPushButton, "btn_edit")
    if btn_edit:
        btn_edit.clicked.connect(lambda: _modifica_torneo(ui_widget))

    btn_delete = ui_widget.findChild(QPushButton, "btn_delete")
    if btn_delete:
        btn_delete.clicked.connect(lambda: _elimina_torneo(ui_widget))

    btn_classifica = ui_widget.findChild(QPushButton, "btn_classifica")
    if btn_classifica:
        btn_classifica.clicked.connect(lambda: _vedi_classifica(ui_widget))

    # double-click sul tree apre la classifica
    tree = ui_widget.findChild(QTreeWidget, "tournament_tree")
    if tree:
        tree.itemDoubleClicked.connect(lambda it, col: _vedi_classifica(ui_widget))
