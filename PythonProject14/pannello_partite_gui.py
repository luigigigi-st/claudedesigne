
"""
pannello_partite_gui.py — Pannello Partite (GUI PyQt5)
Implementa tutta la logica di partite1.py adattata all'interfaccia
definita in partite_widget.ui + partita_dialog.ui.

Widget principali del .ui:
  - cmb_tornei          : QComboBox selezione torneo
  - tab_partite         : QTabWidget (Gironi | Playoff)
  - tbl_calendario      : QTableWidget (tab Gironi)
  - tbl_classifica_gironi: QTableWidget (tab Gironi)
  - btn_assegna_gironi  : QPushButton  (visibile solo se gironi non ancora assegnati)
  - btn_reset_gironi    : QPushButton  (visibile solo se gironi già assegnati, sostituisce assegna)
  - btn_genera_calendario: QPushButton
  - btn_inserisci_risultato: QPushButton
  - btn_correggi_risultato : QPushButton
  - tbl_tabellone       : QTableWidget (tab Playoff)
  - tbl_classifica_finale: QTableWidget (tab Playoff)
  - btn_genera_playoff  : QPushButton
  - btn_inserisci_finale: QPushButton (= inserisci risultato playoff)
  - btn_esporta_classifica: QPushButton (CSV)
"""

import random
import csv
import os
from collections import defaultdict
from datetime import datetime


from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QDialog, QMessageBox, QInputDialog, QLineEdit,
    QTableWidgetItem, QComboBox, QSpinBox, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QAbstractItemView, QMenu, QAction,
    QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from config import db

# ── costante punteggio totale (specchio di partite1.py) ───────────────────────
PUNTEGGIO_TOTALE_DEFAULT = 120
try:
    from config import PUNTEGGIO_MAX_PARITA as PUNTEGGIO_TOTALE
except ImportError:
    PUNTEGGIO_TOTALE = PUNTEGGIO_TOTALE_DEFAULT

UI_DIR    = "claude/"
UI_PARTITE = UI_DIR + "partite_widget.ui"

# ── etichette fasi (specchio di partite1.py) ──────────────────────────────────
_LABEL_FASE = {
    "girone_A":           "Girone A",
    "girone_B":           "Girone B",
    "semifinale_A":       "Semifinale  1-4  posto",
    "semifinale_B":       "Semifinale  5-8  posto",
    "semifinale_C":       "Semifinale  9-12 posto",
    "finale_1_2":         "Finale  1 - 2  posto",
    "finale_3_4":         "Finale  3 - 4  posto",
    "finale_5_6":         "Finale  5 - 6  posto",
    "finale_7_8":         "Finale  7 - 8  posto",
    "finale_9_10":        "Finale  9 - 10 posto",
    "finale_11_12":       "Finale 11 - 12 posto",
    "finale_diretta_5_6":  "Finale diretta  5 - 6  posto",
    "finale_diretta_9_10": "Finale diretta  9 - 10 posto",
}

_SEMI_A_FINALI = {
    "semifinale_A": ("finale_1_2",  "finale_3_4"),
    "semifinale_B": ("finale_5_6",  "finale_7_8"),
    "semifinale_C": ("finale_9_10", "finale_11_12"),
}

_FINALE_POSIZIONI = {
    "finale_1_2":  (1, 2),  "finale_3_4":  (3, 4),
    "finale_5_6":  (5, 6),  "finale_7_8":  (7, 8),
    "finale_9_10": (9, 10), "finale_11_12": (11, 12),
    "finale_diretta_5_6":  (5, 6),
    "finale_diretta_9_10": (9, 10),
}

_ORDINE_FASI = [
    "girone_A", "girone_B",
    "semifinale_A", "semifinale_B", "semifinale_C",
    "finale_1_2",  "finale_3_4",
    "finale_diretta_5_6", "finale_5_6",  "finale_7_8",
    "finale_diretta_9_10","finale_9_10", "finale_11_12",
]

_FASE_ISCRIZIONI = "iscrizioni"
_FASE_ATTESA     = "attesa"
_FASE_GIRONI     = "gironi"
_FASE_PLAYOFF    = "playoff"
_FASE_CONCLUSO   = "concluso"


def _calcola_fase_gui(stato: dict) -> str:
    """Mirror di _calcola_fase() in partite1.py."""
    if stato["fase_corrente"] is None:
        return _FASE_ATTESA if stato["gironi_assegnati"] else _FASE_ISCRIZIONI
    fc = stato["fase_corrente"]
    if "finale" in fc:
        return _FASE_CONCLUSO if stato["pending"] == 0 else _FASE_PLAYOFF
    if "semifinale" in fc:
        return _FASE_PLAYOFF
    if stato["gironi_completi"]:
        if stato.get("is_single_group"):
            return _FASE_CONCLUSO
        if stato["playoff_avviato"]:
            return _FASE_PLAYOFF
    return _FASE_GIRONI


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER MESSAGGI
# ══════════════════════════════════════════════════════════════════════════════

def _err(parent, testo: str):
    QMessageBox.critical(parent, "Errore", testo)

def _ok(parent, testo: str):
    QMessageBox.information(parent, "Successo", testo)

def _confirm(parent, titolo: str, testo: str) -> bool:
    r = QMessageBox.question(parent, titolo, testo,
                             QMessageBox.Yes | QMessageBox.No)
    return r == QMessageBox.Yes


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER DB (cloni delle funzioni private di partite1.py)
# ══════════════════════════════════════════════════════════════════════════════

def _get_nomi_squadre(ids: list) -> dict | None:
    if not ids:
        return {}
    clean = [str(int(i)) for i in ids if isinstance(i, (int, float))]
    if not clean:
        return {}
    ids_str = ", ".join(clean)
    rows = db.execute_select(f"""
        SELECT sq.id_squadra, sq.nome AS team_name,
               p.id_partecipante, p.nome AS p_nome, p.cognome AS p_cognome,
               p.soprannome AS p_soprannome
        FROM   squadra sq
        LEFT JOIN partecipante p ON p.id_squadra = sq.id_squadra
        WHERE  sq.id_squadra IN ({ids_str})
        ORDER BY sq.id_squadra, p.cognome, p.nome
    """)
    if not db.risultato.successo:
        return None
    if not rows:
        return {}

    teams = defaultdict(lambda: {"team_name": None, "participants": []})
    for r in rows:
        sid = r["id_squadra"]
        if teams[sid]["team_name"] is None:
            teams[sid]["team_name"] = r["team_name"]
        if r["p_nome"]:
            teams[sid]["participants"].append(r)

    prelim = {}
    base2ids = defaultdict(list)
    for sid, data in teams.items():
        tn = data["team_name"]
        if tn and not tn.startswith("_singolo_"):
            base = tn
        elif data["participants"]:
            p = data["participants"][0]
            base = f"{p['p_nome']} {p['p_cognome']}"
        else:
            base = f"Squadra ID{sid}"
        prelim[sid] = base
        base2ids[base].append(sid)

    result = {}
    for sid, base in prelim.items():
        if len(base2ids[base]) > 1:
            result[sid] = f"{base} (ID:{sid})"
        else:
            result[sid] = base
    return result


def _get_ids_girone(nome_torneo: str, girone: str) -> list | None:
    r = db.execute_select(
        "SELECT id_squadra FROM squadra WHERE nome_torneo=%s AND girone=%s",
        params=(nome_torneo, girone)
    )
    if not db.risultato.successo:
        return None
    return [row["id_squadra"] for row in r] if r else []


def _classifica_girone(nome_torneo: str, girone: str) -> list | None:
    ids = _get_ids_girone(nome_torneo, girone)
    if ids is None:
        return None
    if not ids:
        return []
    ids_str = ", ".join(str(i) for i in ids)
    partite = db.execute_select(f"""
        SELECT ps1.id_squadra AS id1, ps1.punteggio AS p1,
               ps2.id_squadra AS id2, ps2.punteggio AS p2
        FROM   partita_squadra ps1
        JOIN   partita_squadra ps2
               ON  ps2.id_partita = ps1.id_partita AND ps2.id_squadra > ps1.id_squadra
        JOIN   partita par ON par.id_partita = ps1.id_partita
        JOIN   turno   t   ON t.id_turno     = par.id_turno
        WHERE  t.nome_torneo=%s AND t.fase=%s
          AND  ps1.id_squadra IN ({ids_str})
    """, params=(nome_torneo, f"girone_{girone}"))
    if not db.risultato.successo:
        return None
    partite = partite or []
    nomi = _get_nomi_squadre(ids)
    if nomi is None:
        return None

    stats = {
        sid: {"id": sid, "nome": nomi.get(sid, f"ID{sid}"),
              "PG": 0, "V": 0, "P": 0, "S": 0,
              "PF": 0, "PS": 0, "punti_class": 0}
        for sid in ids
    }
    for m in partite:
        if m["p1"] is None or m["p2"] is None:
            continue
        a, b, pa, pb = m["id1"], m["id2"], m["p1"], m["p2"]
        stats[a]["PG"] += 1; stats[b]["PG"] += 1
        stats[a]["PF"] += pa; stats[a]["PS"] += pb
        stats[b]["PF"] += pb; stats[b]["PS"] += pa
        if pa > pb:
            stats[a]["V"] += 1; stats[a]["punti_class"] += 3; stats[b]["S"] += 1
        elif pb > pa:
            stats[b]["V"] += 1; stats[b]["punti_class"] += 3; stats[a]["S"] += 1
        else:
            stats[a]["P"] += 1; stats[a]["punti_class"] += 1
            stats[b]["P"] += 1; stats[b]["punti_class"] += 1

    return _applica_spareggi(list(stats.values()), list(partite))


def _applica_spareggi(teams: list, partite: list) -> list:
    by_pts: dict = {}
    for t in teams:
        by_pts.setdefault(t["punti_class"], []).append(t)
    result = []
    for pts in sorted(by_pts.keys(), reverse=True):
        gruppo = by_pts[pts]
        result.extend(gruppo if len(gruppo) == 1
                      else _spareggio_gruppo(gruppo, partite))
    return result


def _spareggio_gruppo(gruppo: list, tutte: list) -> list:
    ids = {t["id"] for t in gruppo}
    dirette = [m for m in tutte
               if m.get("id1") in ids and m.get("id2") in ids and m.get("p1") is not None]
    if len(gruppo) == 2:
        a, b = gruppo[0], gruppo[1]
        for m in dirette:
            if {m["id1"], m["id2"]} == {a["id"], b["id"]}:
                pa = m["p1"] if m["id1"] == a["id"] else m["p2"]
                pb = m["p1"] if m["id1"] == b["id"] else m["p2"]
                if pa > pb: return [a, b]
                elif pb > pa: return [b, a]
    avp = {t["id"]: 0 for t in gruppo}
    avf = {t["id"]: 0 for t in gruppo}
    avs = {t["id"]: 0 for t in gruppo}
    for m in dirette:
        id1, id2, p1, p2 = m["id1"], m["id2"], m["p1"], m["p2"]
        avf[id1] += p1; avs[id1] += p2
        avf[id2] += p2; avs[id2] += p1
        if p1 > p2: avp[id1] += 3
        elif p2 > p1: avp[id2] += 3
        else: avp[id1] += 1; avp[id2] += 1
    def ratio(f, s): return (f/s) if s > 0 else (float("inf") if f > 0 else 0.0)
    return sorted(gruppo, key=lambda t: (
        -avp[t["id"]], -ratio(avf[t["id"]], avs[t["id"]]),
        -ratio(t["PF"], t["PS"]), t["nome"]
    ))


def _prossimo_numero_turno(nome: str) -> int | None:
    r = db.select_as_dict("turno", colonne=["COALESCE(MAX(numero),0) AS ult"],
                          condizione="nome_torneo=%s", params=(nome,))
    if not db.risultato.successo:
        return None
    return r[0]["ult"] + 1


def _round_robin(ids: list) -> list:
    pool = list(ids)
    if len(pool) % 2:
        pool.append(None)
    n = len(pool)
    rounds = []
    for _ in range(n - 1):
        coppie = [(pool[i], pool[n-1-i])
                  for i in range(n // 2)
                  if pool[i] is not None and pool[n-1-i] is not None]
        rounds.append(coppie)
        if n > 1:
            pool = [pool[0]] + [pool[-1]] + pool[1:-1]
    return rounds


def _crea_partita_db(id_turno: int, luogo: str, id1: int, id2: int) -> bool:
    id_p = db.insert("partita", ["id_turno", "luogo"], [id_turno, luogo])
    if not db.risultato.successo:
        return False
    for sid in (id1, id2):
        db.insert("partita_squadra", ["id_partita", "id_squadra"], [id_p, sid])
        if not db.risultato.successo:
            return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  DIALOG RISULTATO
# ══════════════════════════════════════════════════════════════════════════════

class DialogRisultato(QDialog):
    """
    Dialog per inserire / correggere il punteggio di una partita.
    Rispetta la logica di _registra_un_risultato() in partite1.py:
    - punteggio_totale fisso (es. 120)
    - il secondo punteggio è calcolato automaticamente
    - in caso di pareggio in fase KO, chiede il vincitore della mano extra
    """

    def __init__(self, parent, id_partita: int, id1: int, id2: int,
                 n1: str, n2: str, is_ko: bool = False,
                 p1_attuale=None, p2_attuale=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle("Inserisci Risultato")
        self.resize(480, 320)
        self._id_p  = id_partita
        self._id1, self._id2 = id1, id2
        self._n1,  self._n2  = n1,  n2
        self._is_ko = is_ko
        self._successo = False

        self.setStyleSheet("""
            QDialog { background-color: #ecf0f1; }
            QLabel  { color: #34495e; font-size: 11pt; }
            QSpinBox{ border:1px solid #bdc3c7; border-radius:4px;
                      padding:6px; font-size:11pt; background:white; }
            QSpinBox:focus { border:1px solid #3498db; }
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(28, 20, 28, 20)

        # intestazione
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet("QFrame{background:#2c3e50;border-radius:6px;}")
        hl = QVBoxLayout(hdr)
        lbl = QLabel("Inserisci Risultato")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("QLabel{color:white;font-size:14pt;font-weight:bold;}")
        hl.addWidget(lbl)
        lay.addWidget(hdr)

        # info partita
        info = QLabel(f"<b>{n1}</b>  vs  <b>{n2}</b>"
                      f"<br><small>Totale punti partita: {PUNTEGGIO_TOTALE}</small>")
        info.setAlignment(Qt.AlignCenter)
        lay.addWidget(info)

        # spin punteggio
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.addWidget(QLabel(f"Punti {n1}:"), 0, 0)
        self.spin1 = QSpinBox()
        self.spin1.setRange(0, PUNTEGGIO_TOTALE)
        self.spin1.setValue(p1_attuale if p1_attuale is not None else PUNTEGGIO_TOTALE // 2)
        grid.addWidget(self.spin1, 0, 1)

        grid.addWidget(QLabel(f"Punti {n2}:"), 1, 0)
        self.lbl_p2 = QLabel(str(PUNTEGGIO_TOTALE - self.spin1.value()))
        self.lbl_p2.setStyleSheet("font-weight:bold; font-size:13pt;")
        grid.addWidget(self.lbl_p2, 1, 1)

        lay.addLayout(grid)
        self.spin1.valueChanged.connect(self._aggiorna_p2)

        # risultato live
        self.lbl_risultato = QLabel("")
        self.lbl_risultato.setAlignment(Qt.AlignCenter)
        self.lbl_risultato.setStyleSheet("font-size:11pt;")
        lay.addWidget(self.lbl_risultato)
        self._aggiorna_p2(self.spin1.value())

        # bottoni
        blay = QHBoxLayout()
        blay.addStretch()
        btn_ann = QPushButton("Annulla")
        btn_ann.setFixedSize(120, 38)
        btn_ann.setStyleSheet("QPushButton{background:#95a5a6;color:white;border-radius:6px;"
                              "font-size:11pt;font-weight:bold;}"
                              "QPushButton:hover{background:#7f8c8d;}")
        btn_ann.clicked.connect(self.reject)
        blay.addWidget(btn_ann)
        self.btn_salva = QPushButton("Salva")
        self.btn_salva.setFixedSize(120, 38)
        self.btn_salva.setStyleSheet("QPushButton{background:#1abc9c;color:white;border-radius:6px;"
                                     "font-size:11pt;font-weight:bold;}"
                                     "QPushButton:hover{background:#16a085;}")
        self.btn_salva.clicked.connect(self._salva)
        self.btn_salva.setDefault(True)
        blay.addWidget(self.btn_salva)
        lay.addLayout(blay)

    def _aggiorna_p2(self, v: int):
        p2 = PUNTEGGIO_TOTALE - v
        self.lbl_p2.setText(str(p2))
        if v > p2:
            self.lbl_risultato.setText(f"<span style='color:#27ae60'>Vince {self._n1}</span>  {v}-{p2}")
        elif p2 > v:
            self.lbl_risultato.setText(f"<span style='color:#27ae60'>Vince {self._n2}</span>  {p2}-{v}")
        else:
            self.lbl_risultato.setText(f"<span style='color:#e67e22'>Pareggio  {v}-{p2}</span>")

    def _salva(self):
        p1 = self.spin1.value()
        p2 = PUNTEGGIO_TOTALE - p1

        # pareggio in fase KO → chiedi vincitore mano supplementare
        if p1 == p2 and self._is_ko:
            vincitore, ok = QInputDialog.getItem(
                self, "Mano supplementare",
                f"Pareggio ({p1}-{p2}). Chi ha vinto la mano extra?",
                [self._n1, self._n2], 0, False
            )
            if not ok:
                return
            if vincitore == self._n1:
                p1 += 1
            else:
                p2 += 1

        # salva nel DB
        query = """
            INSERT INTO partita_squadra (id_partita, id_squadra, punteggio)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE punteggio = VALUES(punteggio)
        """
        db.start_transaction()
        if not db.risultato.successo:
            _err(self, "Errore avvio transazione: " + db.risultato.get_msg())
            return
        try:
            db.execute_alt(query, params=(self._id_p, self._id1, p1))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.execute_alt(query, params=(self._id_p, self._id2, p2))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.commit_transaction()
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            self._successo = True
            _ok(self, f"Risultato salvato!\n{self._n1}: {p1}  —  {self._n2}: {p2}")
            self.accept()
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore salvataggio: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  DIALOG ASSEGNA GIRONI
# ══════════════════════════════════════════════════════════════════════════════

class DialogAssegnaGironi(QDialog):
    """
    Permette di assegnare le squadre ai gironi A e B (o solo A se ≤3 squadre).
    Metodo casuale o manuale, analogo a _assegna_gironi() di partite1.py.
    """

    def __init__(self, parent, nome_torneo: str, is_singolo: bool):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle("Assegna Gironi")
        self.resize(560, 500)
        self._nome = nome_torneo
        self._is_singolo = is_singolo
        self._confermato = False

        self.setStyleSheet("""
            QDialog { background-color: #ecf0f1; }
            QLabel  { color: #34495e; font-size: 11pt; }
            QListWidget { border:1px solid #bdc3c7; border-radius:4px;
                          background:white; font-size:10pt; }
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 18, 24, 18)

        # header
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet("QFrame{background:#2c3e50;border-radius:6px;}")
        hl = QVBoxLayout(hdr)
        lbl = QLabel("Assegnazione Gironi")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("QLabel{color:white;font-size:14pt;font-weight:bold;}")
        hl.addWidget(lbl)
        lay.addWidget(hdr)

        # squadre disponibili
        self._squadre = self._carica_squadre()
        n = len(self._squadre)

        info = QLabel(f"{n} squadre disponibili")
        info.setAlignment(Qt.AlignCenter)
        lay.addWidget(info)

        if n < 6:
            lay.addWidget(QLabel(
                f"Con {n} squadre (minimo 6 per i gironi) tutte saranno assegnate\n"
                "al Girone A (girone unico). Il torneo si conclude al termine del girone,\n"
                "senza playoff: il vincitore è il primo in classifica."
            ))
            self._girone_A = list(self._squadre)
            self._girone_B = []
            self._mostra_riepilogo(lay)
        else:
            # scelta metodo
            mlay = QHBoxLayout()
            mlay.addWidget(QLabel("Metodo:"))
            self.cmb_metodo = QComboBox()
            self.cmb_metodo.addItems(["Casuale", "Manuale"])
            mlay.addWidget(self.cmb_metodo)
            mlay.addStretch()
            lay.addLayout(mlay)

            # lista squadre
            from PyQt5.QtWidgets import QListWidget
            self.lista_sq = QListWidget()
            self.lista_sq.setSelectionMode(QListWidget.MultiSelection)
            for sq in self._squadre:
                self.lista_sq.addItem(f"[{sq['id_squadra']}] {sq['display']}")
            lay.addWidget(QLabel("Seleziona le squadre per il <b>Girone A</b> (metodo manuale):"))
            lay.addWidget(self.lista_sq)

            self.cmb_metodo.currentIndexChanged.connect(
                lambda i: self.lista_sq.setEnabled(i == 1)
            )
            self.lista_sq.setEnabled(False)  # default casuale

        # bottoni
        blay = QHBoxLayout()
        blay.addStretch()
        btn_ann = QPushButton("Annulla")
        btn_ann.setFixedSize(120, 38)
        btn_ann.setStyleSheet("QPushButton{background:#95a5a6;color:white;border-radius:6px;"
                              "font-size:11pt;font-weight:bold;}"
                              "QPushButton:hover{background:#7f8c8d;}")
        btn_ann.clicked.connect(self.reject)
        blay.addWidget(btn_ann)
        btn_conf = QPushButton("Conferma")
        btn_conf.setFixedSize(120, 38)
        btn_conf.setStyleSheet("QPushButton{background:#1abc9c;color:white;border-radius:6px;"
                               "font-size:11pt;font-weight:bold;}"
                               "QPushButton:hover{background:#16a085;}")
        btn_conf.clicked.connect(self._conferma)
        btn_conf.setDefault(True)
        blay.addWidget(btn_conf)
        lay.addLayout(blay)

    def _mostra_riepilogo(self, lay):
        """Aggiunge label di riepilogo quando il girone è già determinato (< 6 squadre)."""
        riq = QLabel("Girone A: " + ", ".join(s["display"] for s in self._girone_A))
        riq.setWordWrap(True)
        lay.addWidget(riq)

    def _carica_squadre(self) -> list:
        if self._is_singolo:
            q = """
                SELECT sq.id_squadra,
                       CONCAT(p.nome,' ',p.cognome) AS display
                FROM   squadra sq
                JOIN   partecipante p ON p.id_squadra = sq.id_squadra
                WHERE  sq.nome_torneo=%s
                  AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra=sq.id_squadra)=1
                ORDER BY p.cognome, p.nome
            """
        else:
            q = """
                SELECT sq.id_squadra, sq.nome AS display
                FROM   squadra sq
                WHERE  sq.nome_torneo=%s
                  AND  (SELECT COUNT(*) FROM partecipante WHERE id_squadra=sq.id_squadra)=2
                ORDER BY sq.id_squadra
            """
        r = db.execute_select(q, params=(self._nome,))
        return r if (db.risultato.successo and r) else []

    def _conferma(self):
        n = len(self._squadre)
        if n < 6:
            # già assegnate in __init__ (girone unico)
            self._salva_db()
            return

        metodo = self.cmb_metodo.currentText()
        if metodo == "Casuale":
            pool = list(self._squadre)
            random.shuffle(pool)
            meta = (n + 1) // 2
            self._girone_A = pool[:meta]
            self._girone_B = pool[meta:]
        else:
            # manuale: prende le selezionate per A
            sel = [self.lista_sq.row(i) for i in self.lista_sq.selectedItems()]
            sel_idxs = [self.lista_sq.row(i) for i in self.lista_sq.selectedItems()]
            # PyQt: selectedItems restituisce QListWidgetItem
            sel_items = self.lista_sq.selectedItems()
            if len(sel_items) < 2:
                _err(self, "Seleziona almeno 2 squadre per il Girone A."); return
            sel_idxs_set = set()
            for item in sel_items:
                sel_idxs_set.add(self.lista_sq.row(item))
            self._girone_A = [self._squadre[i] for i in sorted(sel_idxs_set)]
            self._girone_B = [self._squadre[i] for i in range(n) if i not in sel_idxs_set]
            if len(self._girone_B) < 1:
                _err(self, "Il Girone B deve avere almeno 1 squadra."); return

        msg = f"Girone A: {len(self._girone_A)} squadre\nGirone B: {len(self._girone_B)} squadre"
        if not _confirm(self, "Conferma assegnazione", msg + "\n\nConfermi?"):
            return
        self._salva_db()

    def _salva_db(self):
        db.start_transaction()
        if not db.risultato.successo:
            _err(self, "Errore transazione: " + db.risultato.get_msg()); return
        try:
            db.execute_alt("UPDATE squadra SET girone=NULL WHERE nome_torneo=%s",
                           params=(self._nome,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            for sq in self._girone_A:
                db.execute_alt("UPDATE squadra SET girone='A' WHERE id_squadra=%s",
                               params=(sq["id_squadra"],))
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
            for sq in getattr(self, "_girone_B", []):
                db.execute_alt("UPDATE squadra SET girone='B' WHERE id_squadra=%s",
                               params=(sq["id_squadra"],))
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
            db.commit_transaction()
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            _ok(self, "Gironi assegnati con successo!\nOra puoi generare il calendario.")
            self._confermato = True
            self.accept()
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore salvataggio gironi: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  PANNELLO PARTITE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

class PannelloPartite(QWidget):
    """
    Widget principale del pannello Partite.
    Caricato da partite_widget.ui; gestisce:
      - Tab Gironi: calendario, classifica, bottoni azione
      - Tab Playoff: tabellone, classifica finale, esporta CSV
    """

    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(UI_PARTITE, self)
        except Exception as e:
            print(f"Errore caricamento UI partite: {e}")
            return

        # ── alias widget (nomi del .ui) ───────────────────────────────────
        self.combo_torneo: QComboBox = getattr(self, "cmb_tornei", None)
        self.tabs = getattr(self, "tab_partite", None)

        # tab Gironi
        self.tbl_cal: QTableWidgetItem  = getattr(self, "tbl_calendario", None)
        self.tbl_class_g               = getattr(self, "tbl_classifica_gironi", None)
        self.btn_assegna               = getattr(self, "btn_assegna_gironi", None)
        self.btn_calendario            = getattr(self, "btn_genera_calendario", None)
        self.btn_ins_ris               = getattr(self, "btn_inserisci_risultato", None)
        self.btn_correggi              = getattr(self, "btn_correggi_risultato", None)
        self.btn_reset                 = getattr(self, "btn_reset_gironi", None)

        # tab Playoff
        self.tbl_tab                   = getattr(self, "tbl_tabellone", None)
        self.tbl_class_f               = getattr(self, "tbl_classifica_finale", None)
        self.btn_playoff               = getattr(self, "btn_genera_playoff", None)
        self.btn_ins_fin               = getattr(self, "btn_inserisci_finale", None)
        self.btn_export                = getattr(self, "btn_esporta_classifica", None)

        # ── configurazione colonne ────────────────────────────────────────
        self._setup_tabelle()

        # ── segnali ──────────────────────────────────────────────────────
        if self.combo_torneo is not None:
            self.combo_torneo.currentIndexChanged.connect(lambda _: self.carica())
            self.combo_torneo.activated.connect(lambda _: self.carica())

        if self.btn_assegna:
            self.btn_assegna.clicked.connect(self._on_assegna_gironi)
        if self.btn_calendario:
            self.btn_calendario.clicked.connect(self._on_genera_calendario)
        if self.btn_ins_ris:
            self.btn_ins_ris.clicked.connect(self._on_inserisci_risultato)
        if self.btn_correggi:
            self.btn_correggi.clicked.connect(self._on_correggi_risultato)
        if self.btn_reset:
            self.btn_reset.clicked.connect(self._on_reset_gironi)
        if self.btn_playoff:
            self.btn_playoff.clicked.connect(self._on_genera_playoff)
        if self.btn_ins_fin:
            self.btn_ins_fin.clicked.connect(self._on_inserisci_risultato_playoff)
        if self.btn_export:
            self.btn_export.clicked.connect(self._on_esporta_csv)

        self._carica_combo_tornei()

    # ──────────────────────────────────────────────────────────────────────
    #  SETUP TABELLE
    # ──────────────────────────────────────────────────────────────────────

    def _setup_tabelle(self):
        """Configura intestazioni e comportamento delle QTableWidget."""
        if self.tbl_cal:
            self.tbl_cal.setColumnCount(8)
            self.tbl_cal.setHorizontalHeaderLabels([
                "ID", "Turno", "Fase", "Squadra A", "Punt. A", "Punt. B", "Squadra B", "Luogo"
            ])
            self.tbl_cal.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tbl_cal.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tbl_cal.setAlternatingRowColors(True)
            self.tbl_cal.setSortingEnabled(True)
            for col, w in enumerate([45, 55, 150, 180, 60, 60, 180, 110]):
                self.tbl_cal.setColumnWidth(col, w)

        if self.tbl_class_g:
            self.tbl_class_g.setColumnCount(8)
            self.tbl_class_g.setHorizontalHeaderLabels([
                "Pos.", "Girone", "Squadra", "PG", "V", "P", "Punti", "Diff."
            ])
            self.tbl_class_g.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tbl_class_g.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tbl_class_g.setAlternatingRowColors(True)
            self.tbl_class_g.setSortingEnabled(True)
            for col, w in enumerate([40, 60, 200, 40, 40, 40, 60, 60]):
                self.tbl_class_g.setColumnWidth(col, w)

        if self.tbl_tab:
            self.tbl_tab.setColumnCount(6)
            self.tbl_tab.setHorizontalHeaderLabels([
                "ID", "Fase", "Squadra A", "Punt. A", "Punt. B", "Squadra B"
            ])
            self.tbl_tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tbl_tab.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tbl_tab.setAlternatingRowColors(True)
            self.tbl_tab.setSortingEnabled(True)
            for col, w in enumerate([45, 160, 180, 60, 60, 180]):
                self.tbl_tab.setColumnWidth(col, w)

        if self.tbl_class_f:
            self.tbl_class_f.setColumnCount(3)
            self.tbl_class_f.setHorizontalHeaderLabels([
                "Posto", "Squadra", "Punti Totali"
            ])
            self.tbl_class_f.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tbl_class_f.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tbl_class_f.setAlternatingRowColors(True)
            self.tbl_class_f.setSortingEnabled(True)
            for col, w in enumerate([55, 280, 100]):
                self.tbl_class_f.setColumnWidth(col, w)

    # ──────────────────────────────────────────────────────────────────────
    #  COMBO TORNEI
    # ──────────────────────────────────────────────────────────────────────

    def _carica_combo_tornei(self):
        if self.cmb_tornei is None:
            return

        selezione_corrente = self._torneo_corrente()

        self.cmb_tornei.blockSignals(True)
        self.cmb_tornei.clear()
        self.cmb_tornei.addItem("— Seleziona un torneo —", None)
        lista = db.select_as_dict("torneo")
        if db.risultato.successo and lista:
            for t in lista:
                nome = t["nome"]
                self.cmb_tornei.addItem(nome, nome)

        if selezione_corrente:
            idx = self.cmb_tornei.findData(selezione_corrente)
            if idx >= 0:
                self.cmb_tornei.setCurrentIndex(idx)
        self.cmb_tornei.blockSignals(False)


    def _torneo_corrente(self) -> str | None:
        if self.combo_torneo is None:
            return None
        t = self.combo_torneo.currentData()
        if t is None:
            t = self.combo_torneo.currentText()
        if not t or str(t).startswith("—"):
            return None
        return str(t).strip()

    def seleziona_e_carica(self, nome: str | None = None):
        self._carica_combo_tornei()
        if self.combo_torneo is None:
            return

        if nome:
            idx = self.combo_torneo.findData(nome)
            if idx < 0:
                idx = self.combo_torneo.findText(nome)
            if idx >= 0:
                self.combo_torneo.setCurrentIndex(idx)

        self.carica()

    def _is_singolo(self, nome: str) -> bool:
        r = db.select_as_dict("torneo", condizione="nome=%s", params=(nome,))
        if db.risultato.successo and r:
            return str(r[0].get("singolo_doppio", "1")) == "1"
        return True

    # ──────────────────────────────────────────────────────────────────────
    #  CARICAMENTO PRINCIPALE
    # ──────────────────────────────────────────────────────────────────────

    def carica(self):
        """Aggiorna entrambe le tab con i dati del torneo selezionato."""
        nome = self._torneo_corrente()
        self._pulisci_tutte()
        if not nome:
            return
        self._carica_tab_gironi(nome)
        self._carica_tab_playoff(nome)
        self._aggiorna_stato_bottoni(nome)

    def _pulisci_tutte(self):
        for tbl in [self.tbl_cal, self.tbl_class_g, self.tbl_tab, self.tbl_class_f]:
            if tbl:
                tbl.setRowCount(0)

    # ──────────────────────────────────────────────────────────────────────
    #  TAB GIRONI
    # ──────────────────────────────────────────────────────────────────────

    def _carica_tab_gironi(self, nome: str):
        self._carica_calendario(nome)
        self._carica_classifica_gironi(nome)

    def _carica_calendario(self, nome: str):
        if not self.tbl_cal:
            return
        righe = db.execute_select("""
            SELECT  t.fase, t.numero AS turno,
                    par.id_partita, par.luogo,
                    ps1.id_squadra AS id1, ps1.punteggio AS p1,
                    ps2.id_squadra AS id2, ps2.punteggio AS p2
            FROM    turno t
            JOIN    partita         par ON par.id_turno    = t.id_turno
            JOIN    partita_squadra ps1 ON ps1.id_partita  = par.id_partita
            JOIN    partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                       AND ps2.id_squadra   > ps1.id_squadra
            WHERE   t.nome_torneo=%s
            ORDER BY t.numero ASC, par.id_partita ASC
        """, params=(nome,))
        if not db.risultato.successo or not righe:
            return

        ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
        nomi = _get_nomi_squadre(list(ids_all)) or {}

        self.tbl_cal.setRowCount(len(righe))
        for row_i, r in enumerate(righe):
            n1 = nomi.get(r["id1"], f"ID{r['id1']}")
            n2 = nomi.get(r["id2"], f"ID{r['id2']}")
            p1 = r["p1"]; p2 = r["p2"]
            label_fase = _LABEL_FASE.get(r["fase"], r["fase"])

            valori = [
                str(r["id_partita"]),
                str(r["turno"]),
                label_fase,
                n1,
                str(p1) if p1 is not None else "—",
                str(p2) if p2 is not None else "—",
                n2,
                r["luogo"] or "",
            ]
            for col_i, testo in enumerate(valori):
                item = QTableWidgetItem(testo)
                item.setTextAlignment(Qt.AlignCenter)
                # colora righe con risultato
                if p1 is not None:
                    if p1 > p2:
                        item.setForeground(QColor("#27ae60") if col_i == 3
                                           else QColor("#e74c3c") if col_i == 6
                                           else QColor("#2c3e50"))
                    elif p2 > p1:
                        item.setForeground(QColor("#e74c3c") if col_i == 3
                                           else QColor("#27ae60") if col_i == 6
                                           else QColor("#2c3e50"))
                self.tbl_cal.setItem(row_i, col_i, item)

    def _carica_classifica_gironi(self, nome: str):
        if not self.tbl_class_g:
            return
        righe_totali = []
        for girone in ("A", "B"):
            ids = _get_ids_girone(nome, girone)
            if not ids:
                continue
            cl = _classifica_girone(nome, girone)
            if not cl:
                continue
            for pos, t in enumerate(cl, 1):
                pf = t["PF"]; ps = t["PS"]
                diff = pf - ps
                righe_totali.append({
                    "pos": pos,
                    "girone": girone,
                    "nome": t["nome"],
                    "PG": t["PG"],
                    "V": t["V"],
                    "P": t["P"],
                    "punti": t["punti_class"],
                    "diff": f"+{diff}" if diff >= 0 else str(diff),
                    "top2": pos <= 2,
                })

        self.tbl_class_g.setRowCount(len(righe_totali))
        _MEDAGLIE = {1: "🥇", 2: "🥈", 3: "🥉"}
        for row_i, r in enumerate(righe_totali):
            medaglia = _MEDAGLIE.get(r["pos"], "")
            valori = [
                f"{r['pos']}. {medaglia}",
                r["girone"],
                r["nome"],
                str(r["PG"]),
                str(r["V"]),
                str(r["P"]),
                str(r["punti"]),
                r["diff"],
            ]
            for col_i, testo in enumerate(valori):
                item = QTableWidgetItem(testo)
                item.setTextAlignment(Qt.AlignCenter)
                if r["top2"]:
                    item.setBackground(QColor("#e8f8f0"))
                    item.setForeground(QColor("#1e8449"))
                self.tbl_class_g.setItem(row_i, col_i, item)

    # ──────────────────────────────────────────────────────────────────────
    #  TAB PLAYOFF
    # ──────────────────────────────────────────────────────────────────────

    def _carica_tab_playoff(self, nome: str):
        self._carica_tabellone(nome)
        self._carica_classifica_finale(nome)

    def _carica_tabellone(self, nome: str):
        if not self.tbl_tab:
            return
        righe = db.execute_select("""
            SELECT  t.fase, par.id_partita,
                    ps1.id_squadra AS id1, ps1.punteggio AS p1,
                    ps2.id_squadra AS id2, ps2.punteggio AS p2
            FROM    turno t
            JOIN    partita         par ON par.id_turno    = t.id_turno
            JOIN    partita_squadra ps1 ON ps1.id_partita  = par.id_partita
            JOIN    partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                       AND ps2.id_squadra   > ps1.id_squadra
            WHERE   t.nome_torneo=%s
              AND   t.fase NOT IN ('girone_A','girone_B')
            ORDER BY t.numero ASC, par.id_partita ASC
        """, params=(nome,))
        if not db.risultato.successo or not righe:
            return

        ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
        nomi = _get_nomi_squadre(list(ids_all)) or {}

        # ordine visivo per fase
        per_fase = {}
        for r in righe:
            per_fase.setdefault(r["fase"], []).append(r)

        riga_corrente = 0
        self.tbl_tab.setRowCount(len(righe))
        for fase in _ORDINE_FASI:
            if fase not in per_fase:
                continue
            for r in per_fase[fase]:
                n1 = nomi.get(r["id1"], f"ID{r['id1']}")
                n2 = nomi.get(r["id2"], f"ID{r['id2']}")
                p1, p2 = r["p1"], r["p2"]
                label = _LABEL_FASE.get(fase, fase)

                valori = [
                    str(r["id_partita"]),
                    label,
                    n1,
                    str(p1) if p1 is not None else "—",
                    str(p2) if p2 is not None else "—",
                    n2,
                ]
                for col_i, testo in enumerate(valori):
                    item = QTableWidgetItem(testo)
                    item.setTextAlignment(Qt.AlignCenter)
                    if p1 is not None:
                        if p1 > p2:
                            item.setForeground(QColor("#27ae60") if col_i == 2
                                               else QColor("#e74c3c") if col_i == 5
                                               else QColor("#2c3e50"))
                        elif p2 > p1:
                            item.setForeground(QColor("#e74c3c") if col_i == 2
                                               else QColor("#27ae60") if col_i == 5
                                               else QColor("#2c3e50"))
                    # evidenzia semifinali
                    if "semifinale" in fase:
                        item.setBackground(QColor("#eaf4fb"))
                    elif "finale" in fase:
                        item.setBackground(QColor("#fef9e7"))
                    self.tbl_tab.setItem(riga_corrente, col_i, item)
                riga_corrente += 1

    def _carica_classifica_finale(self, nome: str):
        """Calcola e mostra la classifica finale (specchio di classifica_finale() in partite1.py)."""
        if not self.tbl_class_f:
            return

        finali = db.execute_select("""
            SELECT t.fase,
                   ps1.id_squadra AS id1, ps1.punteggio AS p1,
                   ps2.id_squadra AS id2, ps2.punteggio AS p2
            FROM   turno t
            JOIN   partita         par ON par.id_turno    = t.id_turno
            JOIN   partita_squadra ps1 ON ps1.id_partita  = par.id_partita
            JOIN   partita_squadra ps2 ON ps2.id_partita  = par.id_partita
                                      AND ps2.id_squadra > ps1.id_squadra
            WHERE  t.nome_torneo=%s AND t.fase LIKE 'finale%%'
              AND  ps1.punteggio IS NOT NULL
        """, params=(nome,))
        if not db.risultato.successo or not finali:
            return

        posizioni: dict = {}
        for f in finali:
            fase = f["fase"]
            if fase not in _FINALE_POSIZIONI:
                continue
            pos_v, pos_p = _FINALE_POSIZIONI[fase]
            if f["p1"] > f["p2"]:
                posizioni[f["id1"]] = pos_v
                posizioni[f["id2"]] = pos_p
            else:
                posizioni[f["id2"]] = pos_v
                posizioni[f["id1"]] = pos_p

        if not posizioni:
            return

        # squadre escluse dai playoff
        tutte = db.execute_select("SELECT id_squadra FROM squadra WHERE nome_torneo=%s",
                                  params=(nome,))
        if db.risultato.successo and tutte:
            ids_escluse = {r["id_squadra"] for r in tutte} - set(posizioni)
            if ids_escluse:
                ids_str = ",".join(str(i) for i in ids_escluse)
                exc = db.execute_select(f"""
                    SELECT ps.id_squadra,
                           SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 3
                                    WHEN ps.punteggio = ps2.punteggio THEN 1
                                    ELSE 0 END) AS punti_class,
                           COALESCE(SUM(ps.punteggio),0)  AS PF,
                           COALESCE(SUM(ps2.punteggio),0) AS PS
                    FROM   partita_squadra ps
                    JOIN   partita_squadra ps2
                           ON  ps2.id_partita  = ps.id_partita
                           AND ps2.id_squadra != ps.id_squadra
                    JOIN   partita par ON par.id_partita = ps.id_partita
                    JOIN   turno   t   ON t.id_turno     = par.id_turno
                    WHERE  t.nome_torneo=%s AND t.fase LIKE 'girone%%'
                      AND  ps.punteggio IS NOT NULL AND ps.id_squadra IN ({ids_str})
                    GROUP BY ps.id_squadra
                """, params=(nome,))
                escluse = []
                trovati = set()
                if db.risultato.successo and exc:
                    for row in exc:
                        escluse.append({
                            "id": row["id_squadra"],
                            "punti_class": row["punti_class"] or 0,
                            "PF": row["PF"] or 0,
                            "PS": row["PS"] or 0,
                        })
                        trovati.add(row["id_squadra"])
                for sid in ids_escluse - trovati:
                    escluse.append({"id": sid, "punti_class": 0, "PF": 0, "PS": 0})
                escluse.sort(key=lambda t: (
                    -t["punti_class"],
                    -(t["PF"]/t["PS"] if t["PS"] > 0 else float("inf"))
                ))
                next_pos = max(posizioni.values()) + 1
                for i, team in enumerate(escluse):
                    posizioni[team["id"]] = next_pos + i

        nomi = _get_nomi_squadre(list(posizioni.keys())) or {}

        # statistiche globali (punti totali)
        ids_str = ",".join(str(i) for i in posizioni.keys())
        stats_r = db.execute_select(f"""
            SELECT ps.id_squadra, COALESCE(SUM(ps.punteggio),0) AS PF
            FROM   partita_squadra ps
            JOIN   partita par ON par.id_partita = ps.id_partita
            JOIN   turno   t   ON t.id_turno     = par.id_turno
            WHERE  t.nome_torneo=%s AND ps.punteggio IS NOT NULL
              AND  ps.id_squadra IN ({ids_str})
            GROUP BY ps.id_squadra
        """, params=(nome,))
        stats = {}
        if db.risultato.successo and stats_r:
            for row in stats_r:
                stats[row["id_squadra"]] = row["PF"]

        posizioni_ordinate = sorted(set(posizioni.values()))
        self.tbl_class_f.setRowCount(len(posizioni_ordinate))
        _MEDAGLIE = {1: "🏆", 2: "🥈", 3: "🥉"}

        for row_i, pos in enumerate(posizioni_ordinate):
            sq_id = next((k for k, v in posizioni.items() if v == pos), None)
            if sq_id is None:
                continue
            nome_sq = nomi.get(sq_id, f"ID{sq_id}")
            medaglia = _MEDAGLIE.get(pos, "")
            pf = stats.get(sq_id, 0)

            valori = [f"{pos}. {medaglia}", nome_sq, str(pf)]
            for col_i, testo in enumerate(valori):
                item = QTableWidgetItem(testo)
                item.setTextAlignment(Qt.AlignCenter)
                if pos == 1:
                    item.setBackground(QColor("#fef9e7"))
                    item.setForeground(QColor("#b7950b"))
                elif pos == 2:
                    item.setBackground(QColor("#f2f3f4"))
                    item.setForeground(QColor("#616a6b"))
                elif pos == 3:
                    item.setBackground(QColor("#fdf6ec"))
                    item.setForeground(QColor("#a04000"))
                self.tbl_class_f.setItem(row_i, col_i, item)

    # ──────────────────────────────────────────────────────────────────────
    #  STATO BOTTONI
    # ──────────────────────────────────────────────────────────────────────

    def _aggiorna_stato_bottoni(self, nome: str):
        """
        Visibilità progressiva e abilitazione bottoni: specchio di _costruisci_menu() in partite1.py.
        Usa setVisible() per apparizione progressiva, setEnabled() per blocco temporaneo.
        """
        stato = self._get_stato(nome)
        if stato is None:
            return

        fase             = _calcola_fase_gui(stato)
        gironi_ass       = stato["gironi_assegnati"]
        ha_turni_g       = stato["ha_turni_girone"]
        gironi_completi  = stato["gironi_completi"]
        playoff_avviato  = stato["playoff_avviato"]
        pending          = stato["pending"]
        ris_inseriti     = stato["risultati_inseriti"]
        playoff_completo = stato["playoff_completo"]
        is_single        = stato["is_single_group"]

        # assegna/reset: si escludono — assegna se gironi non assegnati, reset altrimenti
        if self.btn_assegna:
            self.btn_assegna.setVisible(not gironi_ass)
            self.btn_assegna.setEnabled(not gironi_ass)
        if self.btn_reset:
            self.btn_reset.setVisible(gironi_ass)
            self.btn_reset.setEnabled(gironi_ass)

        # calendario: appare solo dopo assegnazione gironi
        if self.btn_calendario:
            self.btn_calendario.setVisible(gironi_ass)
            can_cal = gironi_ass and pending == 0
            self.btn_calendario.setEnabled(can_cal)
            self.btn_calendario.setToolTip(
                "" if can_cal else "Completa i risultati pendenti prima di rigenerare il calendario."
            )

        # inserisci risultato gironi: appare solo con calendario attivo e partite pendenti
        if self.btn_ins_ris:
            vis = ha_turni_g and fase == _FASE_GIRONI and pending > 0
            self.btn_ins_ris.setVisible(vis)
            self.btn_ins_ris.setEnabled(vis)

        # correggi: appare solo se esistono risultati inseriti
        if self.btn_correggi:
            self.btn_correggi.setVisible(ris_inseriti > 0)
            self.btn_correggi.setEnabled(ris_inseriti > 0)

        # playoff: solo torneo multi-girone, solo quando gironi completi e non ancora avviato
        if self.btn_playoff:
            show_po = gironi_completi and not is_single and not playoff_avviato
            self.btn_playoff.setVisible(show_po)
            self.btn_playoff.setEnabled(show_po)

        # inserisci risultato playoff: appare solo durante fase playoff
        if self.btn_ins_fin:
            vis_fin = playoff_avviato and not playoff_completo
            self.btn_ins_fin.setVisible(vis_fin)
            self.btn_ins_fin.setEnabled(vis_fin)

        # export: sempre visibile
        if self.btn_export:
            self.btn_export.setVisible(True)
            self.btn_export.setEnabled(True)

        # tab Playoff: nascosta per tornei single-group (nessun playoff)
        if self.tabs:
            show_tab = not is_single or playoff_avviato
            tab_bar = self.tabs.tabBar()
            if hasattr(tab_bar, "setTabVisible"):
                tab_bar.setTabVisible(1, show_tab)
            else:
                self.tabs.setTabEnabled(1, show_tab)

    def _get_stato(self, nome: str) -> dict | None:
        """Raccoglie le informazioni di stato del torneo (analogo a _get_stato() di partite1.py)."""
        r1 = db.execute_select(
            "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone IS NOT NULL",
            params=(nome,)
        )
        gironi_ass = bool(r1[0]["n"]) if (db.risultato.successo and r1) else False

        r2 = db.execute_select(
            "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase IN ('girone_A','girone_B')",
            params=(nome,)
        )
        ha_turni_g = bool(r2[0]["n"]) if (db.risultato.successo and r2) else False

        r3 = db.execute_select("""
            SELECT COUNT(*) AS n
            FROM   partita_squadra ps
            JOIN   partita par ON par.id_partita = ps.id_partita
            JOIN   turno   t   ON t.id_turno     = par.id_turno
            WHERE  t.nome_torneo=%s AND ps.punteggio IS NULL
        """, params=(nome,))
        pending = (r3[0]["n"] // 2) if (db.risultato.successo and r3) else 0

        r4 = db.execute_select("""
            SELECT COUNT(*) AS n
            FROM   partita_squadra ps
            JOIN   partita par ON par.id_partita = ps.id_partita
            JOIN   turno   t   ON t.id_turno     = par.id_turno
            WHERE  t.nome_torneo=%s AND ps.punteggio IS NOT NULL
        """, params=(nome,))
        ris_ins = (r4[0]["n"] // 2) if (db.risultato.successo and r4) else 0

        r5 = db.execute_select("""
            SELECT COUNT(*) AS n
            FROM   partita_squadra ps
            JOIN   partita par ON par.id_partita = ps.id_partita
            JOIN   turno   t   ON t.id_turno     = par.id_turno
            WHERE  t.nome_torneo=%s AND t.fase IN ('girone_A','girone_B')
              AND  ps.punteggio IS NULL
        """, params=(nome,))
        pending_g = (r5[0]["n"] // 2) if (db.risultato.successo and r5) else 0
        gironi_completi = ha_turni_g and pending_g == 0

        r6 = db.execute_select(
            "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase LIKE 'semifinale%%'",
            params=(nome,)
        )
        playoff_avviato = bool(r6[0]["n"]) if (db.risultato.successo and r6) else False

        # playoff completo = nessuna partita finale senza risultato
        r7 = db.execute_select("""
            SELECT COUNT(*) AS n
            FROM   partita_squadra ps
            JOIN   partita par ON par.id_partita = ps.id_partita
            JOIN   turno   t   ON t.id_turno     = par.id_turno
            WHERE  t.nome_torneo=%s AND t.fase LIKE 'finale%%' AND ps.punteggio IS NULL
        """, params=(nome,))
        pending_playoff = (r7[0]["n"] // 2) if (db.risultato.successo and r7) else 0
        playoff_completo = playoff_avviato and pending_playoff == 0

        r8 = db.execute_select(
            "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone='B'",
            params=(nome,)
        )
        is_single_group = not bool(r8[0]["n"]) if (db.risultato.successo and r8) else True

        r9 = db.execute_select(
            "SELECT fase FROM turno WHERE nome_torneo=%s ORDER BY numero DESC LIMIT 1",
            params=(nome,)
        )
        fase_corrente = r9[0]["fase"] if (db.risultato.successo and r9) else None

        return {
            "gironi_assegnati":   gironi_ass,
            "ha_turni_girone":    ha_turni_g,
            "pending":            pending,
            "risultati_inseriti": ris_ins,
            "gironi_completi":    gironi_completi,
            "playoff_avviato":    playoff_avviato,
            "playoff_completo":   playoff_completo,
            "is_single_group":    is_single_group,
            "fase_corrente":      fase_corrente,
        }

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: ASSEGNA GIRONI
    # ──────────────────────────────────────────────────────────────────────

    def _on_assegna_gironi(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return
        is_singolo = self._is_singolo(nome)

        if is_singolo:
            q_cnt = """SELECT COUNT(*) AS n FROM squadra sq
                       JOIN partecipante p ON p.id_squadra=sq.id_squadra
                       WHERE sq.nome_torneo=%s
                         AND (SELECT COUNT(*) FROM partecipante WHERE id_squadra=sq.id_squadra)=1"""
        else:
            q_cnt = """SELECT COUNT(*) AS n FROM squadra sq
                       WHERE sq.nome_torneo=%s
                         AND (SELECT COUNT(*) FROM partecipante WHERE id_squadra=sq.id_squadra)=2"""
        r_cnt = db.execute_select(q_cnt, params=(nome,))
        n_sq = r_cnt[0]["n"] if (db.risultato.successo and r_cnt) else 0
        if n_sq == 0:
            _err(self, "Nessuna squadra iscritta.\nNon è possibile organizzare i gironi.")
            return

        dlg = DialogAssegnaGironi(self, nome, is_singolo)
        if dlg.exec_() == QDialog.Accepted:
            self.carica()

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: GENERA CALENDARIO
    # ──────────────────────────────────────────────────────────────────────

    def _on_genera_calendario(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return

        # controlla calendario esistente
        r_ex = db.execute_select(
            "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase IN ('girone_A','girone_B')",
            params=(nome,)
        )
        if db.risultato.successo and r_ex and r_ex[0]["n"] > 0:
            if not _confirm(self, "Attenzione",
                            f"Esiste già un calendario con {r_ex[0]['n']} turni.\n"
                            "Procedendo, verrà eliminato definitivamente.\n\nConfermi?"):
                return
            # elimina precedente
            turni = db.execute_select(
                "SELECT id_turno FROM turno WHERE nome_torneo=%s AND fase IN ('girone_A','girone_B')",
                params=(nome,)
            )
            if db.risultato.successo and turni:
                self._elimina_turni([r["id_turno"] for r in turni])

        ids_A = _get_ids_girone(nome, "A")
        ids_B = _get_ids_girone(nome, "B")
        if not ids_A:
            _err(self, "Girone A non configurato. Assegna prima i gironi."); return

        rounds_A = _round_robin(ids_A)
        rounds_B = _round_robin(ids_B) if ids_B else []

        n_round   = max(len(rounds_A), len(rounds_B)) if rounds_B else len(rounds_A)
        n_partite = sum(len(r) for r in rounds_A) + sum(len(r) for r in rounds_B)

        luogo, ok = QInputDialog.getText(self, "Luogo partite",
                                         "Luogo delle partite:",
                                         QLineEdit.Normal, "Sala Principale")
        if not ok:
            return
        luogo = luogo.strip() or "Sala Principale"

        if not _confirm(self, "Genera Calendario",
                        f"Verranno generate {n_partite} partite in {n_round} round.\n\nConfermi?"):
            return

        db.start_transaction()
        if not db.risultato.successo:
            _err(self, "Errore transazione: " + db.risultato.get_msg()); return

        num = _prossimo_numero_turno(nome)
        partite_ok = 0
        try:
            for i in range(n_round):
                if i < len(rounds_A) and rounds_A[i]:
                    id_t = db.insert("turno", ["numero", "nome_torneo", "fase"],
                                     [num, nome, "girone_A"])
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())
                    for id1, id2 in rounds_A[i]:
                        if not _crea_partita_db(id_t, luogo, id1, id2):
                            raise Exception("Errore creazione partita")
                        partite_ok += 1
                    num += 1

                if rounds_B and i < len(rounds_B) and rounds_B[i]:
                    id_t = db.insert("turno", ["numero", "nome_torneo", "fase"],
                                     [num, nome, "girone_B"])
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())
                    for id1, id2 in rounds_B[i]:
                        if not _crea_partita_db(id_t, luogo, id1, id2):
                            raise Exception("Errore creazione partita")
                        partite_ok += 1
                    num += 1

            db.commit_transaction()
            if db.risultato.successo:
                _ok(self, f"Calendario generato: {partite_ok} partite schedulate.")
                self.carica()
            else:
                raise Exception(db.risultato.get_msg())
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore generazione calendario: {e}")

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: INSERISCI RISULTATO (gironi)
    # ──────────────────────────────────────────────────────────────────────

    def _on_inserisci_risultato(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return
        self._inserisci_risultati_pendenti(nome, solo_gironi=True)

    def _on_inserisci_risultato_playoff(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return
        self._inserisci_risultati_pendenti(nome, solo_playoff=True)

    def _inserisci_risultati_pendenti(self, nome: str,
                                      solo_gironi=False, solo_playoff=False):
        where_fase = ""
        if solo_gironi:
            where_fase = "AND t.fase IN ('girone_A','girone_B')"
        elif solo_playoff:
            where_fase = "AND (t.fase LIKE 'semifinale%' OR t.fase LIKE 'finale%')"

        righe = db.execute_select(f"""
            SELECT  par.id_partita, par.luogo,
                    t.numero AS turno, t.fase AS fase_turno,
                    ps1.id_squadra AS id1, ps2.id_squadra AS id2
            FROM    partita par
            JOIN    turno   t   ON t.id_turno    = par.id_turno
            JOIN    partita_squadra ps1 ON ps1.id_partita = par.id_partita
            JOIN    partita_squadra ps2 ON ps2.id_partita = par.id_partita
                                       AND ps2.id_squadra > ps1.id_squadra
            WHERE   t.nome_torneo=%s AND ps1.punteggio IS NULL {where_fase}
            ORDER BY t.numero ASC, par.id_partita ASC
        """, params=(nome,))

        if not db.risultato.successo:
            _err(self, "Errore DB: " + db.risultato.get_msg()); return
        if not righe:
            _ok(self, "Nessuna partita in sospeso. Sei in pari!"); return

        ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
        nomi = _get_nomi_squadre(list(ids_all)) or {}

        registrate = 0
        for r in righe:
            id1, id2 = r["id1"], r["id2"]
            n1 = nomi.get(id1, f"ID{id1}")
            n2 = nomi.get(id2, f"ID{id2}")
            fase_t = r.get("fase_turno", "")
            is_ko = "semifinale" in fase_t or "finale" in fase_t
            label = _LABEL_FASE.get(fase_t, fase_t)

            dlg = DialogRisultato(self, r["id_partita"], id1, id2, n1, n2, is_ko=is_ko)
            dlg.setWindowTitle(f"Risultato — {label}")
            if dlg.exec_() == QDialog.Accepted and dlg._successo:
                registrate += 1

        if registrate > 0:
            # tenta di generare finali se semifinali complete
            self._prova_genera_finali(nome)
            self.carica()
            _ok(self, f"Risultati inseriti: {registrate}/{len(righe)}.")

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: CORREGGI RISULTATO
    # ──────────────────────────────────────────────────────────────────────

    def _on_correggi_risultato(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return

        righe = db.execute_select("""
            SELECT  par.id_partita, par.luogo,
                    t.fase AS fase_turno,
                    ps1.id_squadra AS id1, ps1.punteggio AS p1,
                    ps2.id_squadra AS id2, ps2.punteggio AS p2
            FROM    partita par
            JOIN    turno   t   ON t.id_turno    = par.id_turno
            JOIN    partita_squadra ps1 ON ps1.id_partita = par.id_partita
            JOIN    partita_squadra ps2 ON ps2.id_partita = par.id_partita
                                       AND ps2.id_squadra > ps1.id_squadra
            WHERE   t.nome_torneo=%s AND ps1.punteggio IS NOT NULL
            ORDER BY t.numero ASC, par.id_partita ASC
        """, params=(nome,))

        if not db.risultato.successo:
            _err(self, "Errore DB: " + db.risultato.get_msg()); return
        if not righe:
            _ok(self, "Nessuna partita con risultato trovata."); return

        ids_all = {r["id1"] for r in righe} | {r["id2"] for r in righe}
        nomi = _get_nomi_squadre(list(ids_all)) or {}

        # costruisce la lista per QInputDialog
        voci = []
        for r in righe:
            n1 = nomi.get(r["id1"], f"ID{r['id1']}")
            n2 = nomi.get(r["id2"], f"ID{r['id2']}")
            label = _LABEL_FASE.get(r["fase_turno"], r["fase_turno"])
            p1, p2 = r["p1"], r["p2"]
            voci.append(f"[{label}]  {n1} {p1}-{p2} {n2}")

        scelta, ok = QInputDialog.getItem(
            self, "Correggi Risultato",
            f"Seleziona la partita da correggere ({len(voci)} con risultato):",
            voci, 0, False
        )
        if not ok:
            return
        idx = voci.index(scelta)
        r = righe[idx]
        id1, id2 = r["id1"], r["id2"]
        n1 = nomi.get(id1, f"ID{id1}")
        n2 = nomi.get(id2, f"ID{id2}")
        fase_t = r["fase_turno"]
        is_ko = "semifinale" in fase_t or "finale" in fase_t

        # guardia anti-paradosso temporale (stessa logica di partite1.py)
        if fase_t.startswith("girone_"):
            chk = db.execute_select(
                "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s "
                "AND (fase LIKE 'semifinale%%' OR fase LIKE 'finale%%')",
                params=(nome,)
            )
            if db.risultato.successo and chk and chk[0]["n"] > 0:
                if not _confirm(self, "⚠ Azione pericolosa",
                                "Modificare i gironi comporterà l'eliminazione definitiva "
                                "dei playoff attuali.\n\nProcedere?"):
                    return
                self._elimina_playoff(nome)
                if not db.risultato.successo:
                    return

        dlg = DialogRisultato(self, r["id_partita"], id1, id2, n1, n2,
                              is_ko=is_ko, p1_attuale=r["p1"], p2_attuale=r["p2"])
        dlg.setWindowTitle("Correggi Risultato")
        if dlg.exec_() == QDialog.Accepted and dlg._successo:
            self.carica()

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: RESET GIRONI
    # ──────────────────────────────────────────────────────────────────────

    def _on_reset_gironi(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return

        # Avvisa se ci sono squadre senza girone assegnato
        chk = db.execute_select(
            "SELECT COUNT(*) AS n FROM squadra WHERE nome_torneo=%s AND girone IS NULL",
            params=(nome,)
        )
        if db.risultato.successo and chk and chk[0]["n"] > 0:
            n_sq = chk[0]["n"]
            if not _confirm(self, "⚠ Squadre senza girone",
                            f"{n_sq} squadra/e non ha ancora un girone assegnato.\n\n"
                            "Procedendo con il reset i gironi verranno comunque azzerati.\n\n"
                            "Continuare?"):
                return

        if not _confirm(self, "⚠ Reset Totale Gironi",
                        "Verranno eliminati:\n"
                        " • Tutti i turni e le partite del torneo\n"
                        " • Tutti i risultati inseriti\n\n"
                        "Gli iscritti NON verranno eliminati.\n\nProcedere?"):
            return

        turni = db.execute_select(
            "SELECT id_turno FROM turno WHERE nome_torneo=%s", params=(nome,)
        )
        if not db.risultato.successo:
            _err(self, "Errore DB: " + db.risultato.get_msg()); return

        db.start_transaction()
        if not db.risultato.successo:
            _err(self, "Errore transazione: " + db.risultato.get_msg()); return
        try:
            if turni:
                ids_str = ",".join(str(r["id_turno"]) for r in turni)
                db.execute_alt(f"""
                    DELETE ps FROM partita_squadra ps
                    JOIN partita par ON par.id_partita = ps.id_partita
                    WHERE par.id_turno IN ({ids_str})
                """)
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
                db.execute_alt(f"DELETE FROM partita WHERE id_turno IN ({ids_str})")
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())
                db.execute_alt(f"DELETE FROM turno WHERE id_turno IN ({ids_str})")
                if not db.risultato.successo:
                    raise Exception(db.risultato.get_msg())

            db.execute_alt("UPDATE squadra SET girone=NULL WHERE nome_torneo=%s",
                           params=(nome,))
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())

            db.commit_transaction()
            _ok(self, "Reset completato. Il torneo è tornato alla fase iniziale.")
            self.carica()
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore durante il reset: {e}")

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: GENERA TABELLONE PLAYOFF
    # ──────────────────────────────────────────────────────────────────────

    def _on_genera_playoff(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo.")
            return

        class_A = _classifica_girone(nome, "A")
        class_B = _classifica_girone(nome, "B")

        if class_A is None or class_B is None:
            _err(self, "Errore nel recupero delle classifiche.")
            return

        # Caso Girone Unico (se non c'è il Girone B)
        if not class_B:
            if not class_A or len(class_A) < 2:
                _err(self, "Squadre insufficienti per la finale.")
                return
            self._genera_finale_girone_unico(nome, class_A)
            return

        # Preparazione dati
        nA, nB = len(class_A), len(class_B)
        all_ids = [t["id"] for t in class_A] + [t["id"] for t in class_B]
        nomi = _get_nomi_squadre(all_ids) or {}

        fasi_semi = []
        fasi_dirette = []

        # Logica Semifinali A (1-4 posto)
        if nA >= 2 and nB >= 2:
            fasi_semi.append({
                "fase": "semifinale_A",
                "coppie": [(class_A[0]["id"], class_B[1]["id"]), (class_B[0]["id"], class_A[1]["id"])]
            })

        # Logica Semifinali B o Finale Diretta (5-8 posto)
        if nA >= 3 and nB >= 3:
            if nA >= 4 and nB >= 4:
                fasi_semi.append({
                    "fase": "semifinale_B",
                    "coppie": [(class_A[2]["id"], class_B[3]["id"]), (class_B[2]["id"], class_A[3]["id"])]
                })
            else:
                fasi_dirette.append({
                    "fase": "finale_diretta_5_6",
                    "id1": class_A[2]["id"], "id2": class_B[2]["id"]
                })

        # Logica Semifinali C o Finale Diretta (9-12 posto)
        if nA >= 5 and nB >= 5:
            if nA >= 6 and nB >= 6:
                fasi_semi.append({
                    "fase": "semifinale_C",
                    "coppie": [(class_A[4]["id"], class_B[5]["id"]), (class_B[4]["id"], class_A[5]["id"])]
                })
            else:
                fasi_dirette.append({
                    "fase": "finale_diretta_9_10",
                    "id1": class_A[4]["id"], "id2": class_B[4]["id"]
                })

        if not fasi_semi and not fasi_dirette:
            _err(self, "Squadre insufficienti per generare il playoff.")
            return

        # Costruzione Anteprima (FIX Sintassi f-string)
        preview = []
        for fs in fasi_semi:
            label = _LABEL_FASE.get(fs["fase"], fs["fase"])
            preview.append(f"\n{label}:")
            for id1, id2 in fs["coppie"]:
                nome1 = nomi.get(id1, f"ID{id1}")
                nome2 = nomi.get(id2, f"ID{id2}")
                preview.append(f"  {nome1}  vs  {nome2}")

        for fd in fasi_dirette:
            label = _LABEL_FASE.get(fd["fase"], fd["fase"])
            preview.append(f"\n{label}:")
            nome1 = nomi.get(fd["id1"], f"ID{fd['id1']}")
            nome2 = nomi.get(fd["id2"], f"ID{fd['id2']}")
            preview.append(f"  {nome1}  vs  {nome2}")

        # Input Luogo
        luogo, ok = QInputDialog.getText(self, "Luogo playoff", "Luogo delle partite:", QLineEdit.Normal,
                                         "Sala Principale")
        if not ok: return
        luogo = luogo.strip() or "Sala Principale"

        # Conferma
        if not _confirm(self, "Genera Tabellone Playoff", "\n".join(preview) + "\n\nConfermi?"):
            return

        # Operazione Database
        db.start_transaction()
        if not db.risultato.successo:
            _err(self, "Errore DB: " + db.risultato.get_msg())
            return

        num = _prossimo_numero_turno(nome)
        try:
            for fs in fasi_semi:
                id_t = db.insert("turno", ["numero", "nome_torneo", "fase"], [num, nome, fs["fase"]])
                if not db.risultato.successo: raise Exception(db.risultato.get_msg())
                for id1, id2 in fs["coppie"]:
                    if not _crea_partita_db(id_t, luogo, id1, id2): raise Exception("Errore partita SF")
                num += 1

            for fd in fasi_dirette:
                id_t = db.insert("turno", ["numero", "nome_torneo", "fase"], [num, nome, fd["fase"]])
                if not db.risultato.successo: raise Exception(db.risultato.get_msg())
                if not _crea_partita_db(id_t, luogo, fd["id1"], fd["id2"]): raise Exception("Errore partita Dir")
                num += 1

            db.commit_transaction()
            _ok(self, "Tabellone playoff generato!")
            self.carica()
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore generazione playoff: {e}")

    def _genera_finale_girone_unico(self, nome: str, classifica: list):
        nomi = _get_nomi_squadre([t["id"] for t in classifica]) or {}
        id1, id2 = classifica[0]["id"], classifica[1]["id"]
        n1 = nomi.get(id1, f"ID{id1}")
        n2 = nomi.get(id2, f"ID{id2}")

        luogo, ok = QInputDialog.getText(self, "Luogo finale",
                                         "Luogo della finale:",
                                         QLineEdit.Normal, "Sala Principale")
        if not ok:
            return
        luogo = luogo.strip() or "Sala Principale"

        if not _confirm(self, "Finale Girone Unico",
                        f"Finale 1-2 posto:\n  {n1}  vs  {n2}\n\nConfermi?"):
            return

        db.start_transaction()
        if not db.risultato.successo:
            _err(self, "Errore transazione: " + db.risultato.get_msg()); return
        num = _prossimo_numero_turno(nome)
        try:
            id_t = db.insert("turno", ["numero", "nome_torneo", "fase"],
                             [num, nome, "finale_1_2"])
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            if not _crea_partita_db(id_t, luogo, id1, id2):
                raise Exception("Errore creazione partita finale")
            db.commit_transaction()
            if db.risultato.successo:
                _ok(self, "Finale generata!")
                self.carica()
            else:
                raise Exception(db.risultato.get_msg())
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore generazione finale: {e}")

    # ──────────────────────────────────────────────────────────────────────
    #  AUTO-GENERAZIONE FINALI (dopo semifinali complete)
    # ──────────────────────────────────────────────────────────────────────

    def _prova_genera_finali(self, nome: str):
        """
        Se tutte le partite di una semifinale sono complete,
        genera automaticamente le finali corrispondenti.
        Specchio di _prova_genera_finali() in partite1.py.
        """
        fasi_sf = db.execute_select(
            "SELECT fase, id_turno FROM turno WHERE nome_torneo=%s AND fase LIKE 'semifinale%%'",
            params=(nome,)
        )
        if not db.risultato.successo or not fasi_sf:
            return

        semifinali_pronte = []
        for row in fasi_sf:
            fase_sf = row["fase"]
            id_t    = row["id_turno"]
            if fase_sf not in _SEMI_A_FINALI:
                continue
            fase_v, fase_p = _SEMI_A_FINALI[fase_sf]

            # finali già create?
            r_ex = db.execute_select(
                "SELECT COUNT(*) AS n FROM turno WHERE nome_torneo=%s AND fase IN (%s,%s)",
                params=(nome, fase_v, fase_p)
            )
            if db.risultato.successo and r_ex and r_ex[0]["n"] > 0:
                continue

            # semifinale completa?
            r_pend = db.execute_select("""
                SELECT COUNT(*) AS n FROM partita_squadra ps
                JOIN   partita par ON par.id_partita = ps.id_partita
                WHERE  par.id_turno=%s AND ps.punteggio IS NULL
            """, params=(id_t,))
            if not db.risultato.successo:
                continue
            if r_pend and r_pend[0]["n"] > 0:
                continue

            partite_sf = db.execute_select("""
                SELECT ps1.id_squadra AS id1, ps1.punteggio AS p1,
                       ps2.id_squadra AS id2, ps2.punteggio AS p2,
                       par.luogo
                FROM   partita_squadra ps1
                JOIN   partita_squadra ps2
                       ON  ps2.id_partita = ps1.id_partita AND ps2.id_squadra > ps1.id_squadra
                JOIN   partita par ON par.id_partita = ps1.id_partita
                WHERE  par.id_turno=%s AND ps1.punteggio IS NOT NULL
            """, params=(id_t,))
            if not db.risultato.successo or not partite_sf:
                continue

            vincenti, perdenti = [], []
            luogo = partite_sf[0]["luogo"]
            for p in partite_sf:
                if p["p1"] > p["p2"]:
                    vincenti.append(p["id1"]); perdenti.append(p["id2"])
                else:
                    vincenti.append(p["id2"]); perdenti.append(p["id1"])

            if len(vincenti) < 2 or len(perdenti) < 2:
                continue

            semifinali_pronte.append({
                "fase_v": fase_v, "fase_p": fase_p,
                "vincenti": vincenti, "perdenti": perdenti,
                "luogo": luogo,
            })

        if not semifinali_pronte:
            return

        db.start_transaction()
        if not db.risultato.successo:
            return
        num = _prossimo_numero_turno(nome)
        finali_gen = 0
        try:
            for sf in semifinali_pronte:
                for fase_f, coppie in ((sf["fase_v"], sf["vincenti"]),
                                       (sf["fase_p"], sf["perdenti"])):
                    if len(coppie) < 2:
                        continue
                    id_t2 = db.insert("turno", ["numero", "nome_torneo", "fase"],
                                      [num, nome, fase_f])
                    if not db.risultato.successo:
                        raise Exception(db.risultato.get_msg())
                    if not _crea_partita_db(id_t2, sf["luogo"], coppie[0], coppie[1]):
                        raise Exception("Errore creazione finale")
                    num += 1
                    finali_gen += 1

            db.commit_transaction()
            if db.risultato.successo and finali_gen:
                _ok(self, f"{finali_gen} finali generate automaticamente!")
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore generazione finali automatiche: {e}")

    # ──────────────────────────────────────────────────────────────────────
    #  AZIONE: ESPORTA CSV
    # ──────────────────────────────────────────────────────────────────────

    def _on_esporta_csv(self):
        """Split-button: mostra menu con due opzioni di esportazione."""
        menu = QMenu(self)
        act_class = QAction("📊 Esporta classifica finale (CSV)", self)
        act_cal   = QAction("📅 Esporta calendario partite (CSV)", self)
        act_class.triggered.connect(self._esporta_classifica_csv)
        act_cal.triggered.connect(self._esporta_calendario_csv)
        menu.addAction(act_class)
        menu.addAction(act_cal)
        if self.btn_export:
            menu.exec_(self.btn_export.mapToGlobal(self.btn_export.rect().bottomLeft()))
        else:
            menu.exec_()

    def _esporta_classifica_csv(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return
        if not self.tbl_class_f or self.tbl_class_f.rowCount() == 0:
            _err(self, "Classifica finale non disponibile. "
                 "Completa il torneo prima di esportare."); return

        default = f"classifica_{nome.replace(' ', '_')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Salva classifica", default,
                                              "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Posto", "Squadra", "Punti Totali"])
                for i in range(self.tbl_class_f.rowCount()):
                    w.writerow([self.tbl_class_f.item(i, c).text()
                                if self.tbl_class_f.item(i, c) else ""
                                for c in range(3)])
            _ok(self, f"Classifica esportata in:\n{os.path.abspath(path)}")
        except Exception as e:
            _err(self, f"Errore esportazione CSV:\n{e}")

    def _esporta_calendario_csv(self):
        nome = self._torneo_corrente()
        if not nome:
            _err(self, "Seleziona prima un torneo."); return

        righe = db.execute_select(
            """
            SELECT t.numero AS turno, t.fase,
                   s1.nome AS squadra_a, ps1.punteggio AS punt_a,
                   ps2.punteggio AS punt_b, s2.nome AS squadra_b,
                   p.luogo
            FROM turno t
            JOIN partita p ON p.id_turno = t.id_turno
            JOIN partita_squadra ps1 ON ps1.id_partita = p.id_partita
            JOIN squadra s1 ON s1.id_squadra = ps1.id_squadra
            JOIN partita_squadra ps2 ON ps2.id_partita = p.id_partita
                 AND ps2.id_squadra != ps1.id_squadra
            JOIN squadra s2 ON s2.id_squadra = ps2.id_squadra
            WHERE t.nome_torneo = %s
              AND ps1.id_squadra < ps2.id_squadra
            ORDER BY t.numero, p.id_partita
            """,
            params=(nome,)
        )
        if not db.risultato.successo:
            _err(self, "Errore DB: " + db.risultato.get_msg()); return
        if not righe:
            _err(self, "Nessuna partita trovata per questo torneo."); return

        default = f"calendario_{nome.replace(' ', '_')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Salva calendario", default,
                                              "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Turno", "Fase", "Squadra A", "Punt. A",
                            "Punt. B", "Squadra B", "Luogo"])
                for r in righe:
                    w.writerow([
                        r["turno"], r["fase"],
                        r["squadra_a"],
                        r["punt_a"] if r["punt_a"] is not None else "",
                        r["punt_b"] if r["punt_b"] is not None else "",
                        r["squadra_b"], r["luogo"]
                    ])
            _ok(self, f"Calendario esportato in:\n{os.path.abspath(path)}")
        except Exception as e:
            _err(self, f"Errore esportazione CSV:\n{e}")

    # ──────────────────────────────────────────────────────────────────────
    #  HELPER: ELIMINA TURNI / PLAYOFF
    # ──────────────────────────────────────────────────────────────────────

    def _elimina_turni(self, ids_turni: list):
        if not ids_turni:
            return
        ids_str = ",".join(str(i) for i in ids_turni)
        db.start_transaction()
        if not db.risultato.successo:
            return
        try:
            db.execute_alt(f"""
                DELETE ps FROM partita_squadra ps
                JOIN partita par ON par.id_partita = ps.id_partita
                WHERE par.id_turno IN ({ids_str})
            """)
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.execute_alt(f"DELETE FROM partita WHERE id_turno IN ({ids_str})")
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.execute_alt(f"DELETE FROM turno WHERE id_turno IN ({ids_str})")
            if not db.risultato.successo:
                raise Exception(db.risultato.get_msg())
            db.commit_transaction()
        except Exception as e:
            db.rollback_transaction()
            _err(self, f"Errore eliminazione turni: {e}")

    def _elimina_playoff(self, nome: str):
        turni = db.execute_select(
            "SELECT id_turno FROM turno WHERE nome_torneo=%s "
            "AND (fase LIKE 'semifinale%%' OR fase LIKE 'finale%%')",
            params=(nome,)
        )
        if not db.risultato.successo or not turni:
            return
        self._elimina_turni([r["id_turno"] for r in turni])
