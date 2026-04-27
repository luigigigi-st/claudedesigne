from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QTextBrowser,
    QPushButton, QHBoxLayout, QListWidgetItem, QSizePolicy,
    QLabel, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from config import db

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'

UI_HOME = "claude/home_widget.ui"

REGOLAMENTO = """REGOLAMENTO — BRISCOLA TOURNAMENT MANAGER
Gruppo FALCONERO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥  PARTECIPANTI
• Ogni partecipante deve avere un soprannome univoco nel torneo.
• È possibile iscriversi a più tornei.
• Per le coppie i due giocatori devono avere soprannomi diversi.
• Il soprannome è obbligatorio per tutti.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆  FORMULA DEL TORNEO
• Fase a gironi: i partecipanti vengono suddivisi in gironi e si sfidano.
• Fase playoff: i migliori accedono alle semifinali e finali.
• La classifica finale assegna posizioni dalla 1ª in poi.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🃏  PUNTEGGIO PARTITE
• Vittoria  →  il vincente ottiene TUTTI i punti della partita.
• Sconfitta →  nessun punto al perdente.
• Pareggio  →  metà punteggio a ciascuno.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️  REGOLE GENERALI
• Non è possibile far giocare la stessa squadra contro se stessa.
• La cancellazione di dati richiede una password di autorizzazione.
• Le iscrizioni si chiudono una volta avviati i gironi.
• Un torneo è concluso quando la finale è stata giocata.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊  CLASSIFICA
Calcolata automaticamente in base ai punti. In caso di parità si
considera il numero di vittorie, poi la differenza punti.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒  SICUREZZA
Per eliminare dati è richiesta una password di autorizzazione.
"""

BG      = "#ffffff"
BG_PAGE = "#ecf0f1"
TEXT    = "#2c3e50"
GRID_C  = "#e8ecf0"
ACCENT  = "#1abc9c"
BLUE    = "#2e86c1"
RED     = "#e74c3c"
ORANGE  = "#e67e22"
PURPLE  = "#8e44ad"
COLORS  = [ACCENT, BLUE, RED, ORANGE, PURPLE, "#27ae60", "#d35400", "#2c3e50"]

CARD_STYLE = """
    QFrame {
        background-color: white;
        border: 1.5px solid #dce1e7;
        border-radius: 12px;
    }
"""
TITLE_STYLE = "color: #2c3e50; font-family: Helvetica; font-size: 11pt; font-weight: bold;"
LIST_STYLE = """
    QListWidget {
        background-color: transparent;
        border: none;
        color: #2c3e50;
        font-family: Helvetica;
        font-size: 10pt;
    }
    QListWidget::item {
        padding: 7px 8px;
        border-bottom: 1px solid #f0f3f5;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background-color: #eaf6f2;
        color: #1abc9c;
    }
    QListWidget::item:hover {
        background-color: #f8fffe;
    }
"""


def make_card(parent=None):
    f = QFrame(parent)
    f.setStyleSheet(CARD_STYLE)
    return f


class GraficoCanvas(FigureCanvas):
    def __init__(self, width=4, height=3.2):
        self.fig = Figure(figsize=(width, height), dpi=96, facecolor=BG)
        super().__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("border: none; background: white;")


class DialogRegolamento(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📖 Regolamento del Torneo")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(620, 560)
        self.setStyleSheet("""
            QDialog { background-color: #ecf0f1; }
            QTextBrowser {
                background-color: white; color: #2c3e50;
                font-family: Courier New; font-size: 10pt;
                border: 1.5px solid #dce1e7; border-radius: 10px; padding: 14px;
            }
            QPushButton {
                background-color: #2c3e50; color: white; border-radius: 8px;
                font-family: Helvetica; font-size: 11pt; font-weight: bold;
                padding: 10px 32px; border: none;
            }
            QPushButton:hover { background-color: #1a252f; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)
        txt = QTextBrowser()
        txt.setPlainText(REGOLAMENTO)
        layout.addWidget(txt)
        hl = QHBoxLayout()
        hl.addStretch()
        btn = QPushButton("Chiudi")
        btn.clicked.connect(self.accept)
        hl.addWidget(btn)
        layout.addLayout(hl)


class PannelloHome(QWidget):

    def __init__(self):
        super().__init__()
        uic.loadUi(UI_HOME, self)
        self.setStyleSheet(f"QWidget#HomeWidget {{ background-color: {BG_PAGE}; }}")
        self.btn_regolamento.clicked.connect(self._apri_regolamento)

        # Aggiusta stile delle card statistiche caricate dall'ui
        for name in ["frame_stat_tornei", "frame_stat_attivi",
                     "frame_stat_partecipanti", "frame_stat_conclusi"]:
            w = self.findChild(QFrame, name)
            if w:
                w.setStyleSheet(CARD_STYLE)

        for name in ["frame_attivi", "frame_ultime", "frame_prossime"]:
            w = self.findChild(QFrame, name)
            if w:
                w.setStyleSheet(CARD_STYLE)

        # Stile label titolo sezioni
        for name in ["lbl_attivi_title", "lbl_ultime_title", "lbl_prossime_title",
                     "lbl_tornei_attivi_title"]:
            w = self.findChild(QLabel, name)
            if w:
                w.setStyleSheet(TITLE_STYLE)

        # Stile liste
        for name in ["list_tornei_attivi", "list_ultime_partite", "list_prossime_partite"]:
            w = self.findChild(QWidget, name)
            if w:
                w.setStyleSheet(LIST_STYLE)

        # Label numeri stat - dimensioni maggiori
        for name, color in [
            ("lbl_num_tornei", TEXT),
            ("lbl_num_attivi", ACCENT),
            ("lbl_num_partecipanti", BLUE),
            ("lbl_num_conclusi", RED),
        ]:
            w = self.findChild(QLabel, name)
            if w:
                w.setStyleSheet(f"color:{color}; font-family:Helvetica; font-size:36pt; font-weight:bold;")

        for name in ["lbl_desc_tornei","lbl_desc_attivi","lbl_desc_partecipanti","lbl_desc_conclusi"]:
            w = self.findChild(QLabel, name)
            if w:
                w.setStyleSheet("color:#95a5a6; font-family:Helvetica; font-size:8pt; letter-spacing:2px;")

        # Header
        lbl_t = self.findChild(QLabel, "lbl_titolo")
        if lbl_t:
            lbl_t.setStyleSheet("color:#2c3e50; font-family:Helvetica; font-size:22pt; font-weight:bold;")
        lbl_s = self.findChild(QLabel, "lbl_sottotitolo")
        if lbl_s:
            lbl_s.setStyleSheet("color:#7f8c8d; font-family:Helvetica; font-size:10pt;")

        # Bottone regolamento
        self.btn_regolamento.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50; color: white; border-radius: 8px;
                font-family: Helvetica; font-size: 10pt; font-weight: bold;
                padding: 10px 22px; border: none;
            }
            QPushButton:hover { background-color: #1a252f; }
        """)

        # Sezione grafici (aggiorna() viene chiamato dopo che il widget è visibile)
        self._build_grafici()

    def _build_grafici(self):
        """Crea il frame con i 4 grafici e lo aggiunge al layout principale."""
        frame = make_card(self)
        frame.setStyleSheet(CARD_STYLE + "QFrame { padding: 4px; }")

        vl = QVBoxLayout(frame)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(6)

        lbl = QLabel("📈  Statistiche grafiche")
        lbl.setStyleSheet(TITLE_STYLE)
        vl.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(10)

        self._canvas_torta   = GraficoCanvas()
        self._canvas_barre   = GraficoCanvas()
        self._canvas_donut   = GraficoCanvas()
        self._canvas_pareggi = GraficoCanvas()

        for c in [self._canvas_torta, self._canvas_barre,
                  self._canvas_donut, self._canvas_pareggi]:
            c.setStyleSheet("border: 1px solid #e8ecf0; border-radius: 8px; background: white;")

        grid.addWidget(self._canvas_torta,   0, 0)
        grid.addWidget(self._canvas_barre,   0, 1)
        grid.addWidget(self._canvas_donut,   1, 0)
        grid.addWidget(self._canvas_pareggi, 1, 1)

        vl.addLayout(grid)
        self.layout().addWidget(frame)

    def setGraphicsEffect(self, effect):
        # FigureCanvas creates native HWNDs that crash Windows when composited
        # through QGraphicsOpacityEffect — hide them during animation
        for attr in ('_canvas_torta', '_canvas_barre', '_canvas_donut', '_canvas_pareggi'):
            canvas = getattr(self, attr, None)
            if canvas:
                canvas.setVisible(effect is None)
        super().setGraphicsEffect(effect)

    def aggiorna(self):
        self._carica_stats()
        self._grafico_torta()
        self._grafico_barre()
        self._grafico_donut()
        self._grafico_pareggi()

    def _n(self, query):
        res = db.execute_select(query)
        return int(res[0]["n"]) if res and db.risultato.successo else 0

    def _carica_stats(self):
        self.lbl_num_tornei.setText(str(self._n("SELECT COUNT(*) AS n FROM torneo")))
        self.lbl_num_partecipanti.setText(str(self._n("SELECT COUNT(*) AS n FROM partecipante")))

        fasi_c = ("'finale_1_2','finale_3_4','finale_5_6','finale_7_8',"
                  "'finale_9_10','finale_11_12','finale_diretta_5_6','finale_diretta_9_10'")

        n_conclusi = self._n(f"""
            SELECT COUNT(DISTINCT tu.nome_torneo) AS n FROM turno tu
            JOIN partita p ON p.id_turno = tu.id_turno
            JOIN partita_squadra ps ON ps.id_partita = p.id_partita
            WHERE tu.fase IN ({fasi_c}) AND ps.punteggio IS NOT NULL
        """)
        self.lbl_num_conclusi.setText(str(n_conclusi))

        n_attivi = self._n(f"""
            SELECT COUNT(DISTINCT nome_torneo) AS n FROM turno
            WHERE nome_torneo NOT IN (
                SELECT DISTINCT tu.nome_torneo FROM turno tu
                JOIN partita p ON p.id_turno = tu.id_turno
                JOIN partita_squadra ps ON ps.id_partita = p.id_partita
                WHERE tu.fase IN ({fasi_c}) AND ps.punteggio IS NOT NULL
            )
        """)
        self.lbl_num_attivi.setText(str(n_attivi))

        _FASE = {
            "girone_A": "Girone A", "girone_B": "Girone B", "girone": "Gironi",
            "semifinale_A": "Semifinali", "semifinale_B": "Semifinali",
            "finale_1_2": "Finale", "finale_3_4": "Finale 3°-4°",
        }
        self.list_tornei_attivi.clear()
        attivi = db.execute_select(f"""
            SELECT tu.nome_torneo, tu.fase FROM turno tu
            WHERE tu.numero = (
                SELECT MAX(tu2.numero) FROM turno tu2 WHERE tu2.nome_torneo = tu.nome_torneo
            )
            AND tu.nome_torneo NOT IN (
                SELECT DISTINCT tu3.nome_torneo FROM turno tu3
                JOIN partita p ON p.id_turno = tu3.id_turno
                JOIN partita_squadra ps ON ps.id_partita = p.id_partita
                WHERE tu3.fase IN ({fasi_c}) AND ps.punteggio IS NOT NULL
            )
            GROUP BY tu.nome_torneo ORDER BY tu.nome_torneo
        """)
        if attivi and db.risultato.successo:
            for t in attivi:
                fase = _FASE.get(t["fase"], t["fase"].replace("_", " ").title())
                self.list_tornei_attivi.addItem(f"  {t['nome_torneo']}   —   {fase}")
        else:
            self.list_tornei_attivi.addItem("  Nessun torneo in corso")

        self.list_ultime_partite.clear()
        ultime = db.execute_select("""
            SELECT s1.nome AS sq1, ps1.punteggio AS p1,
                   s2.nome AS sq2, ps2.punteggio AS p2,
                   tu.nome_torneo
            FROM partita par
            JOIN turno tu ON tu.id_turno = par.id_turno
            JOIN partita_squadra ps1 ON ps1.id_partita = par.id_partita
            JOIN partita_squadra ps2 ON ps2.id_partita = par.id_partita
                AND ps2.id_squadra > ps1.id_squadra
            JOIN squadra s1 ON s1.id_squadra = ps1.id_squadra
            JOIN squadra s2 ON s2.id_squadra = ps2.id_squadra
            WHERE ps1.punteggio IS NOT NULL
            ORDER BY par.id_partita DESC LIMIT 6
        """)
        if ultime and db.risultato.successo:
            for r in ultime:
                self.list_ultime_partite.addItem(
                    f"  {r['sq1']}   {r['p1']} – {r['p2']}   {r['sq2']}   [{r['nome_torneo']}]")
        else:
            self.list_ultime_partite.addItem("  Nessuna partita ancora giocata")

        self.list_prossime_partite.clear()
        mancanti = db.execute_select("""
            SELECT s1.nome AS sq1, s2.nome AS sq2, tu.nome_torneo
            FROM partita par
            JOIN turno tu ON tu.id_turno = par.id_turno
            JOIN partita_squadra ps1 ON ps1.id_partita = par.id_partita
            JOIN partita_squadra ps2 ON ps2.id_partita = par.id_partita
                AND ps2.id_squadra > ps1.id_squadra
            JOIN squadra s1 ON s1.id_squadra = ps1.id_squadra
            JOIN squadra s2 ON s2.id_squadra = ps2.id_squadra
            WHERE ps1.punteggio IS NULL
            ORDER BY tu.nome_torneo, par.id_partita LIMIT 8
        """)
        if mancanti and db.risultato.successo:
            for r in mancanti:
                self.list_prossime_partite.addItem(
                    f"  {r['sq1']}  vs  {r['sq2']}   [{r['nome_torneo']}]")
        else:
            self.list_prossime_partite.addItem("  Nessun risultato mancante ✅")

    def _ax_style(self, ax, title):
        ax.set_facecolor(BG)
        ax.set_title(title, color=TEXT, fontsize=10, fontweight="bold", pad=10)
        ax.tick_params(colors=TEXT, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_C)

    def _grafico_torta(self):
        fig = self._canvas_torta.fig
        fig.clear()
        fig.patch.set_facecolor(BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)

        n_s = self._n("SELECT COUNT(*) AS n FROM torneo WHERE singolo_doppio = 1")
        n_c = self._n("SELECT COUNT(*) AS n FROM torneo WHERE singolo_doppio = 0")

        if n_s + n_c == 0:
            ax.text(0.5, 0.5, "Nessun torneo", ha="center", va="center",
                    color="#95a5a6", fontsize=10, transform=ax.transAxes)
            ax.axis("off")
        else:
            wedges, texts, autotexts = ax.pie(
                [n_s, n_c],
                labels=[f"Singolo\n({n_s})", f"Coppie\n({n_c})"],
                colors=[ACCENT, BLUE],
                autopct="%1.0f%%", startangle=90,
                textprops={"color": TEXT, "fontsize": 9},
                wedgeprops={"edgecolor": "white", "linewidth": 2.5},
                pctdistance=0.75
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontweight("bold")
                at.set_fontsize(9)

        ax.set_title("Tipo di tornei", color=TEXT, fontsize=10, fontweight="bold", pad=10)
        fig.tight_layout(pad=1.2)
        self._canvas_torta.draw()

    def _grafico_barre(self):
        fig = self._canvas_barre.fig
        fig.clear()
        fig.patch.set_facecolor(BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)

        res = db.execute_select("""
            SELECT t.nome, COUNT(s.id_squadra) AS n
            FROM torneo t
            LEFT JOIN squadra s ON s.nome_torneo = t.nome
            GROUP BY t.nome ORDER BY n DESC LIMIT 8
        """)

        if not res or not db.risultato.successo:
            ax.text(0.5, 0.5, "Nessun dato", ha="center", va="center",
                    color="#95a5a6", fontsize=10, transform=ax.transAxes)
            ax.axis("off")
        else:
            nomi = [r["nome"][:16] + "…" if len(r["nome"]) > 16 else r["nome"] for r in res]
            vals = [r["n"] for r in res]
            bars = ax.barh(nomi, vals, color=COLORS[:len(vals)],
                           edgecolor="white", linewidth=1.2, height=0.6)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_width() + 0.15,
                        bar.get_y() + bar.get_height() / 2,
                        str(v), va="center", color=TEXT, fontsize=9, fontweight="bold")
            ax.set_xlabel("Iscritti", color="#7f8c8d", fontsize=8)
            ax.tick_params(colors=TEXT, labelsize=8)
            ax.set_xlim(0, max(max(vals) * 1.25, 1) if vals else 1)
            ax.grid(axis="x", color=GRID_C, linewidth=0.7, linestyle="--")
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_C)
            ax.invert_yaxis()

        ax.set_title("Iscritti per torneo", color=TEXT, fontsize=10, fontweight="bold", pad=10)
        fig.tight_layout(pad=1.2)
        self._canvas_barre.draw()

    def _grafico_donut(self):
        fig = self._canvas_donut.fig
        fig.clear()
        fig.patch.set_facecolor(BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)

        n_giocate = self._n("""
            SELECT COUNT(DISTINCT par.id_partita) AS n FROM partita par
            JOIN partita_squadra ps ON ps.id_partita = par.id_partita
            WHERE ps.punteggio IS NOT NULL
        """)
        n_tot = self._n("SELECT COUNT(*) AS n FROM partita")
        n_mancanti = max(0, n_tot - n_giocate)

        if n_tot == 0:
            ax.text(0.5, 0.5, "Nessuna partita\nprogrammata", ha="center", va="center",
                    color="#95a5a6", fontsize=10, transform=ax.transAxes, multialignment="center")
            ax.axis("off")
        else:
            wedges, _ = ax.pie(
                [n_giocate, n_mancanti],
                colors=[ACCENT, GRID_C],
                startangle=90,
                wedgeprops={"width": 0.52, "edgecolor": "white", "linewidth": 2.5}
            )
            pct = int(n_giocate / n_tot * 100) if n_tot else 0
            ax.text(0, 0.06, f"{pct}%", ha="center", va="center",
                    fontsize=16, fontweight="bold", color=ACCENT)
            ax.text(0, -0.18, "completato", ha="center", va="center",
                    fontsize=8, color="#7f8c8d")
            ax.legend(
                wedges,
                [f"Giocate ({n_giocate})", f"Da giocare ({n_mancanti})"],
                loc="lower center", fontsize=8, frameon=False,
                labelcolor=TEXT, ncol=2, bbox_to_anchor=(0.5, -0.06)
            )

        ax.set_title("Avanzamento partite", color=TEXT, fontsize=10, fontweight="bold", pad=10)
        fig.tight_layout(pad=1.2)
        self._canvas_donut.draw()

    def _grafico_pareggi(self):
        fig = self._canvas_pareggi.fig
        fig.clear()
        fig.patch.set_facecolor(BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)

        res = db.execute_select("""
            SELECT tu.nome_torneo,
                   SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 1 ELSE 0 END) AS vittorie,
                   SUM(CASE WHEN ps.punteggio = ps2.punteggio THEN 1 ELSE 0 END) AS pareggi
            FROM partita_squadra ps
            JOIN partita_squadra ps2
                ON ps2.id_partita = ps.id_partita AND ps2.id_squadra != ps.id_squadra
            JOIN partita par ON par.id_partita = ps.id_partita
            JOIN turno tu ON tu.id_turno = par.id_turno
            WHERE ps.punteggio IS NOT NULL
            GROUP BY tu.nome_torneo ORDER BY tu.nome_torneo LIMIT 6
        """)

        if not res or not db.risultato.successo:
            ax.text(0.5, 0.5, "Nessun dato\ndisponibile", ha="center", va="center",
                    color="#95a5a6", fontsize=10, transform=ax.transAxes, multialignment="center")
            ax.axis("off")
        else:
            import numpy as np
            nomi = [r["nome_torneo"][:12] + "…" if len(r["nome_torneo"]) > 12
                    else r["nome_torneo"] for r in res]
            vittorie = [r["vittorie"] or 0 for r in res]
            pareggi  = [r["pareggi"] or 0 for r in res]
            x = np.arange(len(nomi))
            w = 0.32
            b1 = ax.bar(x - w/2, vittorie, w, label="Vittorie",
                        color=ACCENT, edgecolor="white", linewidth=1)
            b2 = ax.bar(x + w/2, pareggi,  w, label="Pareggi",
                        color=ORANGE, edgecolor="white", linewidth=1)
            for bar in list(b1) + list(b2):
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, h + 0.1,
                            str(int(h)), ha="center", va="bottom",
                            fontsize=7.5, color=TEXT, fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels(nomi, rotation=22, ha="right", fontsize=8)
            ax.tick_params(colors=TEXT, labelsize=8)
            ax.legend(fontsize=8.5, frameon=False, labelcolor=TEXT,
                      loc="upper right")
            ax.grid(axis="y", color=GRID_C, linewidth=0.7, linestyle="--")
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_C)
            ax.set_axisbelow(True)

        ax.set_title("Vittorie e pareggi per torneo", color=TEXT,
                     fontsize=10, fontweight="bold", pad=10)
        fig.tight_layout(pad=1.4)
        self._canvas_pareggi.draw()

    def _apri_regolamento(self):
        DialogRegolamento(parent=self).exec_()