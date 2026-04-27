from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QSizePolicy, QAbstractItemView, QComboBox,
)
from PyQt5.QtCore import Qt

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'

from config import db
from home_widget import GraficoCanvas, BG, TEXT, COLORS, GRID_C, ACCENT, BLUE, RED, ORANGE

UI_PATH = "claude/dashboard_widget.ui"

_COLS_TORNEI = ["Nome Torneo", "Tipo", "Stato", "Iscritti", "Max", "Partite Giocate", "Partite Totali"]

_BTN_MOSTRA_STYLE = (
    "QPushButton { background-color: #7f8c8d; color: white; border-radius: 6px; "
    "font-family: Helvetica; font-size: 10pt; font-weight: bold; padding: 6px 16px; border: none; } "
    "QPushButton:hover { background-color: #636e72; }"
)


class DashboardWidget(QWidget):
    """
    Pannello Dashboard — carica dashboard_widget.ui.
    Aggiunge grafici matplotlib responsivi e tabella Top 10 / mostra tutti.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            print(f"[DashboardWidget] Errore caricamento UI: {e}")
            return

        self._mostra_tutti: bool = False

        # ── sorting tbl_tornei ────────────────────────────────────────────
        tbl = getattr(self, "tbl_tornei", None)
        if tbl:
            tbl.setSortingEnabled(False)
            tbl.setAlternatingRowColors(True)
            tbl.setSelectionBehavior(QAbstractItemView.SelectRows)

        # ── pulsante "Mostra tutti" aggiunto via codice ───────────────────
        self._btn_mostra_tutti = QPushButton("Mostra tutti")
        self._btn_mostra_tutti.setStyleSheet(_BTN_MOSTRA_STYLE)
        self._btn_mostra_tutti.clicked.connect(self._toggle_mostra_tutti)
        self._lbl_ordina = QLabel("Ordina:")
        self._lbl_ordina.setStyleSheet(
            "QLabel { color: #2c3e50; font-family: Helvetica; font-size: 10pt; font-weight: bold; }"
        )
        self._combo_ordina = QComboBox()
        self._combo_ordina.addItems([
            "Nome A-Z",
            "Nome Z-A",
            "Piu iscritti",
            "Meno iscritti",
            "Piu partite giocate",
            "Piu partite totali",
            "Stato",
        ])
        self._combo_ordina.setStyleSheet(
            "QComboBox { border: 1px solid #bdc3c7; border-radius: 6px; padding: 5px 10px; "
            "font-family: Helvetica; font-size: 10pt; background-color: white; color: #2c3e50; }"
        )
        self._combo_ordina.currentIndexChanged.connect(self._carica_tbl_tornei)

        hl_buttons = self.findChild(type(None.__class__), "hl_buttons")
        # cerca il layout dei bottoni tramite btn_refresh
        btn_refresh = getattr(self, "btn_refresh", None)
        if btn_refresh and btn_refresh.parent() and btn_refresh.parent().layout():
            btn_refresh.parent().layout().insertWidget(0, self._lbl_ordina)
            btn_refresh.parent().layout().insertWidget(1, self._combo_ordina)
            btn_refresh.parent().layout().insertWidget(2, self._btn_mostra_tutti)
        elif self.layout():
            self.layout().addWidget(self._lbl_ordina)
            self.layout().addWidget(self._combo_ordina)
            self.layout().addWidget(self._btn_mostra_tutti)

        # ── grafici matplotlib ────────────────────────────────────────────
        self._canvas_barre = GraficoCanvas(width=5, height=3.5)
        self._canvas_torta = GraficoCanvas(width=5, height=3.5)
        for c in [self._canvas_barre, self._canvas_torta]:
            c.setStyleSheet("border: 1px solid #e8ecf0; border-radius: 8px; background: white;")

        hl_grafici = QHBoxLayout()
        hl_grafici.setSpacing(12)
        hl_grafici.addWidget(self._canvas_barre)
        hl_grafici.addWidget(self._canvas_torta)

        # inserisci grafici dentro vl_content (che ha i margini corretti)
        root_layout = self.layout()
        vl_content = root_layout.itemAt(0).layout() if root_layout and root_layout.count() > 0 else None
        target = vl_content if vl_content is not None else root_layout
        if target is not None:
            target.addLayout(hl_grafici)
        else:
            lyt = QVBoxLayout()
            lyt.addLayout(hl_grafici)
            self.setLayout(lyt)

        # ── segnali ──────────────────────────────────────────────────────
        if btn_refresh:
            btn_refresh.clicked.connect(self.aggiorna)

    # ──────────────────────────────────────────────────────────────────────
    #  TOP 10 / MOSTRA TUTTI
    # ──────────────────────────────────────────────────────────────────────

    def _toggle_mostra_tutti(self):
        self._mostra_tutti = not self._mostra_tutti
        self._carica_tbl_tornei()

    # ──────────────────────────────────────────────────────────────────────
    #  AGGIORNAMENTO DATI
    # ──────────────────────────────────────────────────────────────────────

    def aggiorna(self):
        self._carica_card_stats()
        self._carica_tbl_tornei()
        self._grafico_barre()
        self._grafico_torta()

    def _carica_card_stats(self):
        # Totali
        res = db.execute_select("SELECT COUNT(*) AS n FROM torneo")
        totali = res[0]["n"] if db.risultato.successo and res else 0

        # In corso (hanno almeno un turno)
        res = db.execute_select(
            "SELECT COUNT(DISTINCT nome_torneo) AS n FROM turno"
        )
        in_corso = res[0]["n"] if db.risultato.successo and res else 0

        # Conclusi (hanno la finale_1_2 con punteggio)
        res = db.execute_select(
            "SELECT COUNT(DISTINCT t.nome_torneo) AS n "
            "FROM turno t "
            "JOIN partita p ON p.id_turno = t.id_turno "
            "JOIN partita_squadra ps ON ps.id_partita = p.id_partita "
            "WHERE t.fase = 'finale_1_2' AND ps.punteggio IS NOT NULL"
        )
        conclusi = res[0]["n"] if db.risultato.successo and res else 0

        # Partecipanti totali
        res = db.execute_select("SELECT COUNT(*) AS n FROM partecipante")
        partecipanti = res[0]["n"] if db.risultato.successo and res else 0

        # Partite giocate (partite che hanno almeno un punteggio registrato)
        res = db.execute_select(
            "SELECT COUNT(DISTINCT id_partita) AS n FROM partita_squadra "
            "WHERE punteggio IS NOT NULL"
        )
        partite = res[0]["n"] if db.risultato.successo and res else 0

        self._set_card("lbl_totali_val",       str(totali))
        self._set_card("lbl_in_corso_val",      str(in_corso))
        self._set_card("lbl_conclusi_val",      str(conclusi))
        self._set_card("lbl_partecipanti_val",  str(partecipanti))
        self._set_card("lbl_partite_val",       str(partite))

    def _set_card(self, name: str, val: str):
        lbl = getattr(self, name, None)
        if lbl:
            lbl.setText(val)

    def _carica_tbl_tornei(self):
        tbl = getattr(self, "tbl_tornei", None)
        if tbl is None:
            return

        query = (
            "SELECT t.nome, "
            "  CASE t.singolo_doppio WHEN 1 THEN 'Singolo' ELSE 'Doppio' END AS tipo, "
            "  (SELECT COUNT(DISTINCT tu.id_turno) FROM turno tu WHERE tu.nome_torneo = t.nome) AS n_turni, "
            "  (SELECT COUNT(*) FROM squadra s WHERE s.nome_torneo = t.nome) AS iscritti, "
            "  COALESCE(t.max_squadre, 0) AS max_sq, "
            "  (SELECT COUNT(DISTINCT ps.id_partita) FROM partita_squadra ps "
            "   JOIN partita pa ON pa.id_partita = ps.id_partita "
            "   JOIN turno tu ON tu.id_turno = pa.id_turno "
            "   WHERE tu.nome_torneo = t.nome AND ps.punteggio IS NOT NULL) AS partite_giocate, "
            "  (SELECT COUNT(DISTINCT pa.id_partita) FROM partita pa "
            "   JOIN turno tu ON tu.id_turno = pa.id_turno "
            "   WHERE tu.nome_torneo = t.nome) AS partite_totali "
            "FROM torneo t "
            "ORDER BY t.nome"
        )
        if not self._mostra_tutti:
            query = query.rstrip() + " LIMIT 10"

        righe = db.execute_select(query)

        tbl.clear()
        tbl.setColumnCount(7)
        tbl.setHeaderLabels(_COLS_TORNEI)

        if not db.risultato.successo or not righe:
            n_tot_res = db.execute_select("SELECT COUNT(*) AS n FROM torneo")
            n_tot = n_tot_res[0]["n"] if db.risultato.successo and n_tot_res else 0
            self._aggiorna_btn_mostra(n_tot)
            return

        from PyQt5.QtWidgets import QTreeWidgetItem
        for r in righe:
            # Calcola stato testuale
            if r["partite_giocate"] and r["partite_totali"] and r["partite_giocate"] >= r["partite_totali"] and r["n_turni"] > 0:
                stato = "Concluso"
            elif r["n_turni"] > 0:
                stato = "In corso"
            else:
                stato = "Iscrizioni"

            max_txt = str(r["max_sq"]) if r["max_sq"] else "–"
            item = QTreeWidgetItem([
                r["nome"],
                r["tipo"],
                stato,
                str(r["iscritti"]),
                max_txt,
                str(r["partite_giocate"]),
                str(r["partite_totali"]),
            ])
            for col in range(7):
                item.setTextAlignment(col, Qt.AlignCenter)
            tbl.addTopLevelItem(item)

        n_tot_res = db.execute_select("SELECT COUNT(*) AS n FROM torneo")
        n_tot = n_tot_res[0]["n"] if db.risultato.successo and n_tot_res else len(righe)
        self._aggiorna_btn_mostra(n_tot)

    def _carica_tbl_tornei(self):
        tbl = getattr(self, "tbl_tornei", None)
        if tbl is None:
            return

        query = (
            "SELECT t.nome, "
            "  CASE t.singolo_doppio WHEN 1 THEN 'Singolo' ELSE 'Doppio' END AS tipo, "
            "  (SELECT COUNT(DISTINCT tu.id_turno) FROM turno tu WHERE tu.nome_torneo = t.nome) AS n_turni, "
            "  (SELECT COUNT(*) FROM squadra s WHERE s.nome_torneo = t.nome) AS iscritti, "
            "  COALESCE(t.max_squadre, 0) AS max_sq, "
            "  (SELECT COUNT(DISTINCT ps.id_partita) FROM partita_squadra ps "
            "   JOIN partita pa ON pa.id_partita = ps.id_partita "
            "   JOIN turno tu ON tu.id_turno = pa.id_turno "
            "   WHERE tu.nome_torneo = t.nome AND ps.punteggio IS NOT NULL) AS partite_giocate, "
            "  (SELECT COUNT(DISTINCT pa.id_partita) FROM partita pa "
            "   JOIN turno tu ON tu.id_turno = pa.id_turno "
            "   WHERE tu.nome_torneo = t.nome) AS partite_totali "
            "FROM torneo t"
        )

        righe = db.execute_select(query)

        tbl.clear()
        tbl.setColumnCount(7)
        tbl.setHeaderLabels(_COLS_TORNEI)

        if not db.risultato.successo or not righe:
            n_tot_res = db.execute_select("SELECT COUNT(*) AS n FROM torneo")
            n_tot = n_tot_res[0]["n"] if db.risultato.successo and n_tot_res else 0
            self._aggiorna_btn_mostra(n_tot)
            return

        ordine = self._combo_ordina.currentText() if hasattr(self, "_combo_ordina") else "Nome A-Z"
        righe_ordinate = []
        for r in righe:
            if r["partite_giocate"] and r["partite_totali"] and r["partite_giocate"] >= r["partite_totali"] and r["n_turni"] > 0:
                stato = "Concluso"
            elif r["n_turni"] > 0:
                stato = "In corso"
            else:
                stato = "Iscrizioni"

            righe_ordinate.append({
                "nome": r["nome"],
                "tipo": r["tipo"],
                "stato": stato,
                "iscritti": int(r["iscritti"] or 0),
                "max_txt": str(r["max_sq"]) if r["max_sq"] else "-",
                "partite_giocate": int(r["partite_giocate"] or 0),
                "partite_totali": int(r["partite_totali"] or 0),
            })

        if ordine == "Nome Z-A":
            righe_ordinate.sort(key=lambda r: r["nome"].lower(), reverse=True)
        elif ordine == "Piu iscritti":
            righe_ordinate.sort(key=lambda r: (-r["iscritti"], r["nome"].lower()))
        elif ordine == "Meno iscritti":
            righe_ordinate.sort(key=lambda r: (r["iscritti"], r["nome"].lower()))
        elif ordine == "Piu partite giocate":
            righe_ordinate.sort(key=lambda r: (-r["partite_giocate"], r["nome"].lower()))
        elif ordine == "Piu partite totali":
            righe_ordinate.sort(key=lambda r: (-r["partite_totali"], r["nome"].lower()))
        elif ordine == "Stato":
            priorita = {"Iscrizioni": 0, "In corso": 1, "Concluso": 2}
            righe_ordinate.sort(key=lambda r: (priorita.get(r["stato"], 99), r["nome"].lower()))
        else:
            righe_ordinate.sort(key=lambda r: r["nome"].lower())

        if not self._mostra_tutti:
            righe_ordinate = righe_ordinate[:10]

        from PyQt5.QtWidgets import QTreeWidgetItem
        for r in righe_ordinate:
            item = QTreeWidgetItem([
                r["nome"],
                r["tipo"],
                r["stato"],
                str(r["iscritti"]),
                r["max_txt"],
                str(r["partite_giocate"]),
                str(r["partite_totali"]),
            ])
            for col in range(7):
                item.setTextAlignment(col, Qt.AlignCenter)
            tbl.addTopLevelItem(item)

        n_tot_res = db.execute_select("SELECT COUNT(*) AS n FROM torneo")
        n_tot = n_tot_res[0]["n"] if db.risultato.successo and n_tot_res else len(righe_ordinate)
        self._aggiorna_btn_mostra(n_tot)

    def _aggiorna_btn_mostra(self, n_tot: int):
        if self._mostra_tutti:
            self._btn_mostra_tutti.setText("Mostra top 10")
        else:
            rimanenti = max(0, n_tot - 10)
            self._btn_mostra_tutti.setText(
                f"Mostra tutti ({n_tot})" if rimanenti > 0 else "Mostra tutti"
            )
        self._btn_mostra_tutti.setVisible(n_tot > 10 or self._mostra_tutti)

    # ──────────────────────────────────────────────────────────────────────
    #  GRAFICI
    # ──────────────────────────────────────────────────────────────────────

    def _grafico_barre(self):
        """Barre orizzontali: iscritti per torneo (top 10)."""
        fig = self._canvas_barre.fig
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)
        fig.patch.set_facecolor(BG)

        try:
            res = db.execute_select(
                "SELECT t.nome, COUNT(s.id_squadra) AS n "
                "FROM torneo t "
                "LEFT JOIN squadra s ON s.nome_torneo = t.nome "
                "GROUP BY t.nome ORDER BY n DESC LIMIT 10"
            )
            if not db.risultato.successo or not res:
                raise ValueError("nessun dato")

            nomi   = [r["nome"][:18] for r in res]
            valori = [r["n"] for r in res]

            ax.barh(nomi, valori, color=ACCENT, edgecolor="none", height=0.65)
            ax.set_xlabel("Iscritti", color=TEXT, fontsize=8)
            ax.tick_params(colors=TEXT, labelsize=7)
            ax.spines[:].set_visible(False)
            ax.xaxis.grid(True, color=GRID_C, linewidth=0.5)
            ax.set_axisbelow(True)
            ax.invert_yaxis()
            ax.set_xlim(0, max(valori) * 1.15 if valori and max(valori) > 0 else 1)
        except Exception:
            ax.text(0.5, 0.5, "Nessun dato", ha="center", va="center",
                    color="#95a5a6", fontsize=10, transform=ax.transAxes)
            ax.axis("off")

        ax.set_title("Iscritti per torneo (top 10)", color=TEXT, fontsize=9, fontweight="bold")
        fig.tight_layout(pad=1.0)
        self._canvas_barre.draw()

    def _grafico_torta(self):
        """Torta: distribuzione tornei singolo vs doppio."""
        res = db.execute_select(
            "SELECT singolo_doppio, COUNT(*) AS n FROM torneo GROUP BY singolo_doppio"
        )
        if not db.risultato.successo or not res:
            return

        etichette, valori, colori = [], [], []
        color_map = {1: ACCENT, 0: ORANGE, True: ACCENT, False: ORANGE}
        label_map = {1: "Singolo", 0: "Doppio", True: "Singolo", False: "Doppio"}
        for r in res:
            k = r["singolo_doppio"]
            etichette.append(label_map.get(k, str(k)))
            valori.append(r["n"])
            colori.append(color_map.get(k, BLUE))

        fig = self._canvas_torta.fig
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)
        fig.patch.set_facecolor(BG)

        wedges, texts, autotexts = ax.pie(
            valori, labels=etichette, colors=colori,
            autopct="%1.0f%%", startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
            textprops={"color": TEXT, "fontsize": 8},
        )
        for at in autotexts:
            at.set_color("white")
            at.set_fontsize(8)
        ax.set_title("Tipologia tornei", color=TEXT, fontsize=9, fontweight="bold")

        fig.tight_layout(pad=1.0)
        self._canvas_torta.draw()
