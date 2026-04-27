from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt

from config import db

UI_PATH = "claude/classifica_w.ui"


class ClassificaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            print(f"[ClassificaWidget] errore UI: {e}")
            return
        self._popola_combo()
        combo = getattr(self, "combo_torneo", None)
        if combo:
            combo.currentIndexChanged.connect(self._carica)
        tree = getattr(self, "classifica_tree", None)
        if tree is not None:
            tree.setSortingEnabled(True)
            tree.setAlternatingRowColors(True)

    def _popola_combo(self):
        combo = getattr(self, "combo_torneo", None)
        if not combo:
            return
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Seleziona un torneo...")
        lista = db.select_as_dict("torneo")
        if db.risultato.successo and lista:
            for t in lista:
                combo.addItem(t["nome"])
        combo.blockSignals(False)

    def seleziona_e_carica(self, nome: str):
        self._popola_combo()
        combo = getattr(self, "combo_torneo", None)
        if not combo:
            return
        idx = combo.findText(nome)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            self._carica()

    def _carica(self):
        combo = getattr(self, "combo_torneo", None)
        if not combo:
            return
        nome = combo.currentText()
        if not nome or nome.startswith("Seleziona"):
            self._svuota()
            return
        self._popola_classifica(nome)

    def _svuota(self):
        tree = getattr(self, "classifica_tree", None)
        if tree:
            tree.clear()
        for attr in ("label_1st_name", "label_2nd_name", "label_3rd_name"):
            lbl = getattr(self, attr, None)
            if lbl:
                lbl.setText("—")
        for attr in ("label_1st_score", "label_2nd_score", "label_3rd_score"):
            lbl = getattr(self, attr, None)
            if lbl:
                lbl.setText("0 pt")

    def _popola_classifica(self, nome: str):
        from pannello_partite_gui import _classifica_girone, _get_nomi_squadre

        tree = getattr(self, "classifica_tree", None)
        if tree is None:
            return
        tree.clear()
        # Disable sorting while we insert to preserve explicit ranking order
        tree.setSortingEnabled(False)

        # Girone classifica (A + B)
        classifica = []
        for girone in ("A", "B"):
            cl = _classifica_girone(nome, girone)
            if cl:
                classifica.extend(cl)
        classifica.sort(key=lambda x: (-x["punti_class"], -x["PF"]))

        # Fallback: stats globali da tutte le partite
        if not classifica:
            classifica = self._stats_globali(nome)

        # Ordenamento definitivo: top al migliore (ordine discendente)
        classifica = sorted(classifica, key=lambda t: (
            t.get("punti_class", 0),
            t.get("PF", 0),
            t.get("PS", 0),
            t.get("nome", "")
        ), reverse=True)
        for i, (name_attr, score_attr) in enumerate([
            ("label_1st_name", "label_1st_score"),
            ("label_2nd_name", "label_2nd_score"),
            ("label_3rd_name", "label_3rd_score"),
        ]):
            entry = classifica[i] if i < len(classifica) else None
            lbl = getattr(self, name_attr, None)
            slbl = getattr(self, score_attr, None)
            if lbl:
                lbl.setText(entry["nome"] if entry else "—")
            if slbl:
                slbl.setText(f"{entry.get('punti_class', 0)} pt" if entry else "0 pt")

        # Tree
        _MEDAGLIE = {1: "🥇", 2: "🥈", 3: "🥉"}
        for pos, entry in enumerate(classifica, 1):
            medaglia = _MEDAGLIE.get(pos, "")
            item = QTreeWidgetItem([
                f"{pos}. {medaglia}",
                entry["nome"],
                str(entry.get("PG", "—")),
                str(entry.get("V", "—")),
                str(entry.get("P", "—")),
                str(entry.get("PF", "—")),
            ])
            for col in range(6):
                item.setTextAlignment(col, Qt.AlignCenter)
            tree.addTopLevelItem(item)

    def _stats_globali(self, nome: str) -> list:
        """Fallback: stats da tutte le partite del torneo (qualsiasi fase)."""
        rows = db.execute_select("""
            SELECT ps.id_squadra,
                   COUNT(DISTINCT ps.id_partita) AS PG,
                   SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 1 ELSE 0 END) AS V,
                   SUM(CASE WHEN ps.punteggio = ps2.punteggio THEN 1 ELSE 0 END) AS P,
                   SUM(CASE WHEN ps.punteggio < ps2.punteggio THEN 1 ELSE 0 END) AS S,
                   COALESCE(SUM(ps.punteggio), 0) AS PF,
                   COALESCE(SUM(ps2.punteggio), 0) AS PS,
                   SUM(CASE WHEN ps.punteggio > ps2.punteggio THEN 3
                            WHEN ps.punteggio = ps2.punteggio THEN 1
                            ELSE 0 END) AS punti_class
            FROM partita_squadra ps
            JOIN partita_squadra ps2
                 ON ps2.id_partita = ps.id_partita AND ps2.id_squadra != ps.id_squadra
            JOIN partita par ON par.id_partita = ps.id_partita
            JOIN turno t ON t.id_turno = par.id_turno
            WHERE t.nome_torneo=%s AND ps.punteggio IS NOT NULL
            GROUP BY ps.id_squadra
            ORDER BY punti_class DESC, PF DESC
        """, params=(nome,))

        if not db.risultato.successo or not rows:
            return []

        from pannello_partite_gui import _get_nomi_squadre
        nomi = _get_nomi_squadre([r["id_squadra"] for r in rows]) or {}
        return [
            {
                "nome": nomi.get(r["id_squadra"], f"ID{r['id_squadra']}"),
                "PG": r["PG"], "V": r["V"], "P": r["P"], "S": r["S"],
                "PF": r["PF"], "PS": r["PS"], "punti_class": r["punti_class"],
            }
            for r in rows
        ]
