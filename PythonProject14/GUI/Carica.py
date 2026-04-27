import sys
from typing import Optional, List, Dict, Union

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QTreeWidget,
    QTreeWidgetItem,
    QDialog,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve

from libreriax.utils.Risultato import Risultato


class AppManager:
    _app: Optional[QApplication] = None

    def __init__(self):
        if not AppManager._app:
            AppManager._app = QApplication(sys.argv)
        self.finestre: dict[str, Union[QWidget, QMainWindow, QDialog]] = {}
        self.risultato = Risultato()

    # ---------------- UI LOADING ----------------
    def load(self, nome: str, percorso_ui: str, tipo: str = None, parent: QWidget = None) -> Optional[Union[QWidget, QMainWindow, QDialog]]:
        """
        Carica un file .ui e lo salva sotto 'nome'.
        Il tipo di widget (QMainWindow / QWidget / QDialog) viene rilevato
        automaticamente dal file .ui — non serve istanziare la classe prima.
        Il parametro 'tipo' è mantenuto per compatibilità ma ignorato.
        """
        try:
            finestra = uic.loadUi(percorso_ui)   # ← auto-rileva la classe corretta
            if parent is not None:
                finestra.setParent(parent)
            self.finestre[nome] = finestra
            self.risultato.successo = True
            return finestra
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.load] Errore caricamento '{percorso_ui}': {e}")
            return None

    # ---------------- QDialog helpers ----------------
    def show_dialog(self, nome: str) -> bool:
        """Mostra un widget/dialog con show() (non bloccante)."""
        try:
            d = self.finestre.get(nome)
            if d is None:
                raise ValueError(f"Dialog '{nome}' non trovato")
            d.show()
            self.risultato.successo = True
            return True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.show_dialog] {e}")
            return False

    def exec_dialog(self, nome: str) -> Optional[int]:
        """
        Esegue un QDialog in modalità bloccante (exec_).
        Ritorna QDialog.Accepted / QDialog.Rejected oppure None se errore.
        """
        try:
            d = self.finestre.get(nome)
            if d is None:
                raise ValueError(f"Dialog '{nome}' non trovato")
            if not hasattr(d, "exec_"):
                raise TypeError(f"'{nome}' non supporta exec_() — non è un QDialog")
            self.risultato.successo = True
            return d.exec_()
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.exec_dialog] {e}")
            return None

    def close_dialog(self, nome: str) -> bool:
        """Chiude un widget/dialog."""
        try:
            d = self.finestre.get(nome)
            if d is None:
                raise ValueError(f"Dialog '{nome}' non trovato")
            d.close()
            self.risultato.successo = True
            return True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.close_dialog] {e}")
            return False

    # ---------------- stackedWidget helpers ----------------
    def add_widget_to_main(self, nome_main: str, widget_da_aggiungere: QWidget) -> bool:
        """
        Aggiunge widget allo stackedWidget del main; ritorna True se ok.
        """
        try:
            main = self.finestre.get(nome_main)
            if main is None:
                raise ValueError(f"Main '{nome_main}' non trovato")
            stacked = getattr(main, "stackedWidget", None)
            if stacked is None:
                raise AttributeError("stackedWidget non trovato nel main")
            stacked.addWidget(widget_da_aggiungere)
            self.risultato.successo = True
            return True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.add_widget_to_main] {e}")
            return False

    def set_widget_to_main(self, nome_main: str, widget_or_index: Union[QWidget, int]) -> bool:
        """
        Se main ha stackedWidget -> setCurrentWidget / setCurrentIndex,
        altrimenti, se widget viene passato come QWidget, lo mostra direttamente.
        """
        try:
            main = self.finestre.get(nome_main)
            if main is None:
                raise ValueError(f"Main '{nome_main}' non trovato")

            stacked = getattr(main, "stackedWidget", None)
            if stacked is not None:
                if isinstance(widget_or_index, int):
                    stacked.setCurrentIndex(widget_or_index)
                else:
                    stacked.setCurrentWidget(widget_or_index)
            else:
                if isinstance(widget_or_index, QWidget):
                    widget_or_index.show()
            self.risultato.successo = True
            return True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.set_widget_to_main] {e}")
            return False

    # ---------------- showing / running ----------------
    def show(self, nome: str) -> bool:
        try:
            w = self.finestre.get(nome)
            if w is None:
                raise ValueError(f"Nessuna finestra con il nome '{nome}'")
            w.show()
            self.risultato.successo = True
            return True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.show] {e}")
            return False

    def esegui(self):
        if not self.check():
            print("[AppManager.esegui] check fallito, non eseguo QApplication")
            return
        AppManager._app.exec_()

    def check(self) -> bool:
        for nome, w in self.finestre.items():
            if w is None:
                print(f"[AppManager.check] finestra '{nome}' è None")
                return False
        return True

    # ---------------- utility per widget / tree ----------------
    def find_widget(self, nome_widget: str) -> Optional[Union[QWidget, QMainWindow, QDialog]]:
        return self.finestre.get(nome_widget)

    def find_tree(self, widget_or_name: Union[str, QWidget], tree_name: str) -> Optional[QTreeWidget]:
        """
        Cerca e ritorna un QTreeWidget con objectName tree_name dentro il widget registrato.
        """
        try:
            if isinstance(widget_or_name, str):
                widget = self.finestre.get(widget_or_name)
            else:
                widget = widget_or_name

            if widget is None:
                print(f"[AppManager.find_tree] widget '{widget_or_name}' non trovato")
                return None

            tree = widget.findChild(QTreeWidget, tree_name)
            if tree is not None:
                return tree

            trees = widget.findChildren(QTreeWidget)
            if trees:
                print("[AppManager.find_tree] tree colti con fallback (primo trovato):", [t.objectName() for t in trees])
                return trees[0]

            print(f"[AppManager.find_tree] nessun QTreeWidget trovato in '{widget_or_name}'")
            return None
        except Exception as e:
            print(f"[AppManager.find_tree] eccezione: {e}")
            return None

    def populate_tree(self, tree: QTreeWidget, lista: list, keys: list):
        """Popola tree con lista di dict. keys è l'ordine delle colonne."""
        try:
            if tree is None:
                raise ValueError("tree è None")
            tree.clear()

            for rec in lista:
                row = ["" if rec.get(k) is None else str(rec.get(k)) for k in keys]
                item = QTreeWidgetItem(row)
                for col_index in range(len(row)):
                    item.setTextAlignment(col_index, Qt.AlignCenter)
                tree.addTopLevelItem(item)

            self.risultato.successo = True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager.populate_tree] {e}")

    def setup_tree_widget(
        self,
        tree: QTreeWidget,
        column_widths: dict = None,
        stretch_last: bool = True
    ):
        """Imposta larghezza colonne, modalità resize, centra intestazioni e testo."""
        if tree is None:
            return

        header = tree.header()
        col_count = tree.columnCount()

        for col in range(col_count):
            if column_widths and col in column_widths:
                width = column_widths[col]
                header.setSectionResizeMode(col, header.Fixed)
                tree.setColumnWidth(col, width)
            else:
                if stretch_last and col == col_count - 1:
                    header.setSectionResizeMode(col, header.Stretch)
                else:
                    header.setSectionResizeMode(col, header.Interactive)

        for col in range(col_count):
            tree.headerItem().setTextAlignment(col, Qt.AlignCenter)

    # ---------------- fade transition ----------------
    def _fade_switch(self, nome_main: str, nuovo_widget: QWidget, durata_ms: int = 180):
        """
        Cambia pannello con animazione fade-out → fade-in.
        Nota: se la finestra contiene QTreeWidget con molti dati, ridurre
        durata_ms a 100 per evitare lag su Windows.
        """
        try:
            main = self.finestre.get(nome_main)
            if main is None:
                return self.set_widget_to_main(nome_main, nuovo_widget)
            stacked = getattr(main, "stackedWidget", None)
            if stacked is None:
                return self.set_widget_to_main(nome_main, nuovo_widget)

            corrente = stacked.currentWidget()
            if corrente is None or corrente is nuovo_widget:
                stacked.setCurrentWidget(nuovo_widget)
                return True

            # fade-out del widget corrente
            effect_out = QGraphicsOpacityEffect(corrente)
            corrente.setGraphicsEffect(effect_out)
            anim_out = QPropertyAnimation(effect_out, b"opacity", corrente)
            anim_out.setDuration(durata_ms)
            anim_out.setStartValue(1.0)
            anim_out.setEndValue(0.0)
            anim_out.setEasingCurve(QEasingCurve.InOutCubic)

            def _on_out_finished():
                corrente.setGraphicsEffect(None)
                stacked.setCurrentWidget(nuovo_widget)
                # fade-in del nuovo widget
                effect_in = QGraphicsOpacityEffect(nuovo_widget)
                nuovo_widget.setGraphicsEffect(effect_in)
                anim_in = QPropertyAnimation(effect_in, b"opacity", nuovo_widget)
                anim_in.setDuration(durata_ms)
                anim_in.setStartValue(0.0)
                anim_in.setEndValue(1.0)
                anim_in.setEasingCurve(QEasingCurve.InOutCubic)
                anim_in.finished.connect(lambda: nuovo_widget.setGraphicsEffect(None))
                anim_in.start()

            anim_out.finished.connect(_on_out_finished)
            anim_out.start()
            self.risultato.successo = True
            return True
        except Exception as e:
            self.risultato.fallito(e)
            print(f"[AppManager._fade_switch] {e}")
            return self.set_widget_to_main(nome_main, nuovo_widget)

    # ---------------- accesso comodo ----------------
    def __getitem__(self, nome: str):
        return self.finestre.get(nome)