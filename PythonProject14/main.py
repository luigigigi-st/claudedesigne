from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QComboBox, QLabel
from GUI.Carica import AppManager
from GUI.GPT import frame_gpt
from GUI.pss import run_tournament_ui_demo
from config import db

from partite1 import svolgi_partite
from libreriax.console import IO


def menu_principale():
    """
    Mostra il menu principale del programma per la gestione dei tornei di briscola.
    """
    titolo = IO.color("--- Benvenuto nel Gestore Tornei di Briscola FALCONERO! ---", "cyan")
    menu = f"""
{IO.color('Cosa vuoi fare ora? Scegli un\'opzione digitando il numero o la lettera corrispondente:', 'yellow')}
  {IO.color('1', 'green')}. Gestire i TORNEI (crea, modifica)
  {IO.color('2', 'green')}. Gestire i PARTECIPANTI (iscrivi giocatori, vedi elenchi)
  {IO.color('3', 'green')}. Gestire le PARTITE (programma, inserisci risultati, vedi dettagli, vedi classifiche)
  {IO.color('U', 'yellow')}. USCIRE dal programma  {IO.color('[INVIO]', 'yellow')}
"""
    print(titolo + "\n" + menu)


def menù_delete():
    print("inserisci")
    stringa = """ 1. CANCELLA tutti i tornei
    2. cancella tutte le squadre
    3. cancella tutti i partecipanti

    """


from partecipanti import main_partecipanti
from tornei import svolgi
from claude import tornei_bridge


def main():
    print(IO.color("Benvenuto nel programma di gestione Torneo Briscola!", "cyan"))
    while True:

        print("db: " + str(db.CONNECT()))
        print("ddb: " + str(db))

        menu_principale()
        risposta = input(IO.color("Scelta: ", "yellow")).strip().lower()

        match risposta:
            case "u" | "":
                break
            case "1":
                svolgi()
            case "2":
                main_partecipanti()
            case "3":
                svolgi_partite()
            case "gpt":
                frame_gpt()
            case "gemini":
                run_tournament_ui_demo()
            case "p1":
                try:
                    apri_app()
                except Exception as e:
                    import traceback
                    print("[apri_app ERRORE]", e)
                    traceback.print_exc()

        print("\n" + IO.color("Ben ritornato nel programma di gestione Torneo Briscola!", "cyan"))


def apri_app():
    print("[apri_app] avvio nuova GUI...")
    from home_widget import PannelloHome
    from pannello_partite_gui import PannelloPartite
    from partecipanti_widget import PartecipantiWidget
    from dashboard_widget import DashboardWidget
    from classifica_widget import ClassificaWidget

    # ------------------- INIZIO APP -------------------
    app = AppManager()

    # Carica le UI
    main             = app.load("frame", "claude/m_w.ui", "main")
    gestione_tornei  = app.load("gestione_tornei", "claude/tornei_w.ui", "widget")
    # Collega i bottoni e la logica di listing per i tornei senza modificare tornei.py
    try:
        tornei_bridge.connect_tornei_bridge(gestione_tornei)
    except Exception as e:
        print("[bridge] errore di connessione tornei_bridge:", e)
    classifica_w     = ClassificaWidget()

    if main is None:
        print("[MAIN] main non caricato")
        return

    # Istanzia widget con logica propria
    home_w          = PannelloHome()
    partite_w       = PannelloPartite()
    partecipanti_w  = PartecipantiWidget()
    dashboard_w     = DashboardWidget()

    # Aggiungi tutti i pannelli allo stackedWidget
    for w in [home_w, gestione_tornei, partite_w, classifica_w, partecipanti_w, dashboard_w]:
        if w is not None:
            app.add_widget_to_main("frame", w)

    # ------------------- TORNEI -------------------
    combo_ordina_tornei = getattr(gestione_tornei, "combo_ordina_tornei", None)
    if combo_ordina_tornei is None:
        form_frame = getattr(gestione_tornei, "form_frame", None)
        layout = form_frame.layout() if form_frame is not None else None
        if layout is not None:
            lbl_ordina_tornei = QLabel("Ordina per:")
            lbl_ordina_tornei.setStyleSheet("color: #34495e; font-size: 12pt;")
            combo_ordina_tornei = QComboBox()
            combo_ordina_tornei.setObjectName("combo_ordina_tornei")
            combo_ordina_tornei.addItems([
                "Nome A-Z",
                "Nome Z-A",
                "Tipo",
                "Piu iscritti",
                "Meno iscritti",
                "Stato",
            ])
            combo_ordina_tornei.setStyleSheet(
                "QComboBox { border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px; "
                "font-family: Helvetica; font-size: 11pt; background-color: white; color: #2c3e50; }"
            )
            layout.addWidget(lbl_ordina_tornei, 0, 2)
            layout.addWidget(combo_ordina_tornei, 0, 3)

    def _chiave_stato_torneo(fase: str) -> int:
        return {
            "iscrizioni_aperte": 0,
            "attesa": 1,
            "gironi": 2,
            "playoff": 3,
            "concluso": 4,
        }.get(fase, 99)

    _tree_tornei_init = False

    def _popola_tornei():
        """Ricarica dati tornei nel tree (richiamabile anche dopo modifiche)."""
        nonlocal _tree_tornei_init
        from partecipanti import _conta_iscritti
        from partite1 import _get_stato, _calcola_fase

        fase_label = {
            "iscrizioni_aperte": "Iscrizioni APERTE",
            "attesa": "Fase GIRONI - attesa di configurazione",
            "gironi": "Fase GIRONI in corso",
            "playoff": "Fase PLAYOFF in corso",
            "concluso": "Torneo CONCLUSO",
        }
        fase_colore = {
            "iscrizioni_aperte": Qt.darkGreen,
            "attesa": Qt.darkYellow,
            "gironi": Qt.darkCyan,
            "playoff": Qt.darkGreen,
            "concluso": Qt.black,
        }

        lista_tornei = db.select_as_dict("torneo")
        tree = app.find_tree(gestione_tornei, "tournament_tree")
        if tree is None:
            return

        # salva stato corrente
        selected_nome = None
        if tree.selectedItems():
            selected_nome = tree.selectedItems()[0].text(0)
        hscroll = tree.horizontalScrollBar().value()
        vscroll = tree.verticalScrollBar().value()

        tree.setUpdatesEnabled(False)
        tree.clear()

        # imposta colonne solo al primo caricamento
        if not _tree_tornei_init:
            app.setup_tree_widget(
                tree,
                column_widths={0: 220, 1: 100, 2: 190, 3: 100, 4: 110, 5: 100, 6: 170},
                stretch_last=False,
            )
            tree.setSortingEnabled(False)
            tree.setAlternatingRowColors(True)
            _tree_tornei_init = True

        if not db.risultato.successo or not lista_tornei:
            tree.setUpdatesEnabled(True)
            return

        righe_tornei = []
        for rec in lista_tornei:
            nome = rec.get("nome", "")
            is_singolo = str(rec.get("singolo_doppio")) == "1"
            tipo = "singolo" if is_singolo else "doppio"
            quota = rec.get("quota_iscrizione")
            max_squadre = rec.get("max_squadre")
            iscritti = _conta_iscritti(nome, is_singolo)

            stato_info = _get_stato(nome)
            fase = _calcola_fase(stato_info) if stato_info else "iscrizioni_aperte"
            stato = fase_label.get(fase, fase)
            colore = fase_colore.get(fase, Qt.black)

            righe_tornei.append({
                "nome": nome,
                "tipo": tipo,
                "email": rec.get("email_iscrizioni") or "",
                "quota": f"EUR {float(quota):.2f}" if quota is not None else "-",
                "max": str(max_squadre) if max_squadre is not None else "-",
                "iscritti": iscritti,
                "stato": stato,
                "fase": fase,
                "colore": colore,
            })

        ordine = combo_ordina_tornei.currentText() if combo_ordina_tornei is not None else "Nome A-Z"
        if ordine == "Nome Z-A":
            righe_tornei.sort(key=lambda r: r["nome"].lower(), reverse=True)
        elif ordine == "Tipo":
            righe_tornei.sort(key=lambda r: (r["tipo"], r["nome"].lower()))
        elif ordine == "Piu iscritti":
            righe_tornei.sort(key=lambda r: (-r["iscritti"], r["nome"].lower()))
        elif ordine == "Meno iscritti":
            righe_tornei.sort(key=lambda r: (r["iscritti"], r["nome"].lower()))
        elif ordine == "Stato":
            righe_tornei.sort(key=lambda r: (_chiave_stato_torneo(r["fase"]), r["nome"].lower()))
        else:
            righe_tornei.sort(key=lambda r: r["nome"].lower())

        item_da_selezionare = None
        for row in righe_tornei:
            item = QTreeWidgetItem([
                row["nome"],
                row["tipo"],
                row["email"],
                row["quota"],
                row["max"],
                str(row["iscritti"]),
                row["stato"],
            ])
            for col in range(7):
                item.setTextAlignment(col, Qt.AlignCenter)
            item.setForeground(6, row["colore"])
            tree.addTopLevelItem(item)
            if row["nome"] == selected_nome:
                item_da_selezionare = item

        tree.setUpdatesEnabled(True)

        # ripristina selezione e scroll
        if item_da_selezionare:
            tree.setCurrentItem(item_da_selezionare)
        tree.horizontalScrollBar().setValue(hscroll)
        tree.verticalScrollBar().setValue(vscroll)

        if search_bar:
            _on_search_tornei(search_bar.text())

    # dopo add/elimina da tornei_bridge usa _popola_tornei di main.py (colori e scroll corretti)
    tornei_bridge._refresh_override = _popola_tornei

    def apri_gestione_torneo():
        _popola_tornei()
        ok = app._fade_switch("frame", gestione_tornei)
        if not ok:
            gestione_tornei.show()

    # Ricerca real-time sul tree tornei
    def _on_search_tornei(testo: str):
        tree = app.find_tree(gestione_tornei, "tournament_tree")
        if tree is None:
            return
        testo = testo.strip().lower()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            item.setHidden(bool(testo) and testo not in item.text(0).lower())

    search_bar = getattr(gestione_tornei, "entry_tournament_name_list", None)
    if search_bar:
        search_bar.textChanged.connect(_on_search_tornei)
    if combo_ordina_tornei is not None:
        combo_ordina_tornei.currentIndexChanged.connect(lambda _: _popola_tornei())

    # Doppio click → switch classifica
    def _on_torneo_dblclick(item, col):
        nome = item.text(0)
        apri_classifica(nome)

    tree_tornei = app.find_tree(gestione_tornei, "tournament_tree")
    if tree_tornei:
        tree_tornei.itemDoubleClicked.connect(_on_torneo_dblclick)

    # Pulsante "Vedi Classifica" nel pannello tornei
    btn_classifica_tornei = getattr(gestione_tornei, "btn_classifica", None)
    if btn_classifica_tornei:
        def _classifica_da_selezione():
            tree = app.find_tree(gestione_tornei, "tournament_tree")
            if tree is None:
                return
            items = tree.selectedItems()
            nome = items[0].text(0) if items else None
            apri_classifica(nome)
        btn_classifica_tornei.clicked.connect(_classifica_da_selezione)

    # ------------------- CLASSIFICA -------------------
    def apri_classifica(nome_torneo: str = None):
        if classifica_w is None:
            return
        if nome_torneo:
            classifica_w.seleziona_e_carica(nome_torneo)
        else:
            classifica_w._carica()
        app._fade_switch("frame", classifica_w)

    # ------------------- PARTITE -------------------
    def apri_partite():
        partite_w.seleziona_e_carica()
        app._fade_switch("frame", partite_w)

    # ------------------- HOME -------------------
    def apri_home():
        app._fade_switch("frame", home_w)
        QTimer.singleShot(400, home_w.aggiorna)

    # ------------------- COLLEGA PULSANTI MENU -------------------
    btn_tornei      = getattr(main, "btn_list_tournaments", None)
    btn_players     = getattr(main, "btn_manage_players", None)
    btn_matches     = getattr(main, "btn_manage_matches", None)
    btn_dashboard   = getattr(main, "btn_dashboard", None)
    btn_exit        = getattr(main, "btn_exit_app", None)

    if btn_tornei:
        btn_tornei.clicked.connect(apri_gestione_torneo)
    if btn_players:
        def apri_partecipanti():
            app._fade_switch("frame", partecipanti_w)
            QTimer.singleShot(400, partecipanti_w.aggiorna)
        btn_players.clicked.connect(apri_partecipanti)
    if btn_matches:
        btn_matches.clicked.connect(apri_partite)
    if btn_dashboard:
        def _apri_dashboard():
            app._fade_switch("frame", dashboard_w)
            QTimer.singleShot(400, dashboard_w.aggiorna)
        btn_dashboard.clicked.connect(_apri_dashboard)
    if btn_exit:
        btn_exit.clicked.connect(AppManager._app.quit)

    # Mostra home all'avvio — switch diretto (no fade) per evitare flash page_home
    app.set_widget_to_main("frame", dashboard_w)

    # mostra main e avvia l'app
    app.show("frame")
    QTimer.singleShot(100, dashboard_w.aggiorna)
    app.esegui()


def prova_f():
    app = AppManager()
    frame = app.load(nome="main", percorso_ui="files_ui/main.ui", tipo="main")
    primo = app.load("primo", "files_ui/panel1.ui", "widget")
    secondo = app.load("secondo", "files_ui/panel2.ui", "widget")
    app.add_widget_to_main("main", primo)
    app.add_widget_to_main("main", secondo)

    def apri_primo():
        app.set_widget_to_main("main", primo)

    apri_primo()

    def apri_secondo():
        app.set_widget_to_main("main", secondo)

    primo.btn.clicked.connect(apri_secondo)
    secondo.btn.clicked.connect(apri_primo)

    lista_tornei = db.select_as_dict("torneo")
    if not db.risultato.successo:
        print("error" + db.risultato.get_msg())
        return
    for i in lista_tornei:
        secondo.lista.addItem(i["nome"])
    # secondo.lista.itemClicked.connect(apri_primo)
    secondo.lista.itemDoubleClicked.connect(apri_primo)

    app.show("main")

    app.esegui()


if __name__ == '__main__':
    main()
