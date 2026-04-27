import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkcalendar import DateEntry
import datetime


# =====================================================================
# Definizione delle classi dei Widget (incorporate in un unico modulo)
# =====================================================================

class TournamentCreationWidget(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#ecf0f1")  # Colore di sfondo del contenuto

        self.create_form()

    def create_form(self):
        # Titolo della sezione
        title_label = tk.Label(
            self,
            text="🏆 Crea Nuovo Torneo",
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        title_label.pack(pady=20)

        # Frame per i campi del form per una migliore organizzazione
        form_frame = tk.Frame(self, bg="#ecf0f1")
        form_frame.pack(pady=10, padx=20, fill="x")

        # Funzione helper per creare etichette e campi input
        def create_input_row(parent, label_text, widget_type=tk.Entry, **widget_kwargs):
            row_frame = tk.Frame(parent, bg="#ecf0f1")
            row_frame.pack(fill="x", pady=5)

            label = tk.Label(
                row_frame,
                text=label_text,
                font=("Helvetica", 12),
                bg="#ecf0f1",
                fg="#34495e",
                width=20,
                anchor="w"
            )
            label.pack(side="left", padx=10)

            if widget_type == DateEntry:
                widget = widget_type(
                    row_frame,
                    selectmode='day',
                    date_pattern='dd/mm/yyyy',
                    font=("Helvetica", 12),
                    background="#bdc3c7",
                    foreground="black",
                    headersbackground="#34495e",
                    headersforeground="white",
                    normalbackground="white",
                    **widget_kwargs
                )
            else:
                widget = widget_type(
                    row_frame,
                    font=("Helvetica", 12),
                    bd=1,
                    relief="solid",
                    highlightbackground="#bdc3c7",
                    highlightcolor="#3498db",
                    **widget_kwargs
                )
            widget.pack(side="left", expand=True, fill="x", padx=10)
            return widget

        self.entry_nome_torneo = create_input_row(form_frame, "Nome Torneo:", tk.Entry)

        # Tipo di torneo (Singolo/Doppio)
        type_frame = tk.Frame(form_frame, bg="#ecf0f1")
        type_frame.pack(fill="x", pady=5)
        tk.Label(
            type_frame,
            text="Tipo Torneo:",
            font=("Helvetica", 12),
            bg="#ecf0f1",
            fg="#34495e",
            width=20,
            anchor="w"
        ).pack(side="left", padx=10)
        self.var_tipo_torneo = tk.BooleanVar(value=True)  # True for singolo, False for doppio
        tk.Radiobutton(
            type_frame,
            text="Singolo",
            variable=self.var_tipo_torneo,
            value=True,
            font=("Helvetica", 12),
            bg="#ecf0f1",
            fg="#34495e",
            selectcolor="#1abc9c",
            activebackground="#ecf0f1",
            activeforeground="#34495e"
        ).pack(side="left", padx=10)
        tk.Radiobutton(
            type_frame,
            text="Doppio/Squadre",
            variable=self.var_tipo_torneo,
            value=False,
            font=("Helvetica", 12),
            bg="#ecf0f1",
            fg="#34495e",
            selectcolor="#1abc9c",
            activebackground="#ecf0f1",
            activeforeground="#34495e"
        ).pack(side="left", padx=10)

        self.entry_data_inizio = create_input_row(form_frame, "Data Inizio:", DateEntry)
        self.entry_data_fine = create_input_row(form_frame, "Data Fine:", DateEntry)
        self.entry_data_inizio_iscrizione = create_input_row(form_frame, "Inizio Iscrizioni:", DateEntry)
        self.entry_data_fine_iscrizione = create_input_row(form_frame, "Fine Iscrizioni:", DateEntry)

        # Pulsante Crea Torneo
        create_button = tk.Button(
            self,
            text="Crea Torneo",
            command=self._create_tournament_action,
            font=("Helvetica", 14, "bold"),
            bg="#1abc9c",
            fg="white",
            bd=0,
            height=2,
            width=20,
            cursor="hand2"
        )
        create_button.pack(pady=30, ipadx=10, ipady=5)

    def _create_tournament_action(self):
        # Qui potresti raccogliere i dati e passandoli ad una funzione nel tuo mainwindow
        # che si occuperà della logica di database.
        nome = self.entry_nome_torneo.get()
        tipo = "Singolo" if self.var_tipo_torneo.get() else "Doppio/Squadre"
        # Controllo per assicurarsi che le date siano state selezionate
        try:
            data_inizio = self.entry_data_inizio.get_date().strftime('%Y-%m-%d')
            data_fine = self.entry_data_fine.get_date().strftime('%Y-%m-%d')
            data_inizio_iscrizione = self.entry_data_inizio_iscrizione.get_date().strftime('%Y-%m-%d')
            data_fine_iscrizione = self.entry_data_fine_iscrizione.get_date().strftime('%Y-%m-%d')
        except AttributeError:  # get_date() might return None if no date selected
            messagebox.showerror("Errore Data", "Assicurati di selezionare tutte le date.")
            return

        print(
            f"Nuovo Torneo: {nome}, Tipo: {tipo}, Inizio: {data_inizio}, Fine: {data_fine}, Iscrizioni: {data_inizio_iscrizione} - {data_fine_iscrizione}")
        # Placeholder per la logica di creazione del torneo
        messagebox.showinfo("Successo", f"Torneo '{nome}' creato (simulato).")


class PlayerManagementWidget(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#ecf0f1")
        self.style = ttk.Style()  # Inizializza lo stile per Treeview

        self.current_player_id = None  # Per tenere traccia del giocatore selezionato
        self.create_layout()

    def create_layout(self):
        title_label = tk.Label(
            self,
            text="👥 Gestione Partecipanti",
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        title_label.pack(pady=20)

        # Frame superiore per il form di aggiunta/modifica
        self.form_frame = tk.Frame(self, bg="#ecf0f1", padx=10, pady=10, relief="groove", bd=1)
        self.form_frame.pack(fill="x", padx=20, pady=10)
        self._create_player_form(self.form_frame)

        # Frame per la lista dei partecipanti
        list_frame = tk.Frame(self, bg="#ecf0f1")
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._create_player_list(list_frame)

        # Pulsanti di azione
        button_frame = tk.Frame(self, bg="#ecf0f1")
        button_frame.pack(pady=10)

        btn_style = {
            "font": ("Helvetica", 12, "bold"),
            "fg": "white",
            "bd": 0,
            "height": 2,
            "width": 15,
            "cursor": "hand2",
            "relief": "flat"
        }

        tk.Button(button_frame, text="Aggiungi", command=self._add_player_action, bg="#1abc9c", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Modifica", command=self._edit_player_action, bg="#3498db", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Elimina", command=self._delete_player_action, bg="#e74c3c", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Pulisci Campi", command=self._clear_form, bg="#95a5a6", **btn_style).pack(
            side="left", padx=5)

    def _create_player_form(self, parent_frame):
        # Etichette e campi di input per i dettagli del partecipante
        self.entries = {}
        fields = [
            ("Nome:", "nome"),
            ("Cognome:", "cognome"),
            ("Codice Fiscale:", "codice_fiscale"),
            ("Data Nascita:", "data_nascita"),
            ("Via:", "via"),
            ("Numero Civico:", "numero_civico"),
            ("CAP:", "cap"),
            ("Città:", "citta"),
            ("Soprannome:", "soprannome")
        ]

        row = 0
        col = 0
        for label_text, key in fields:
            label = tk.Label(parent_frame, text=label_text, font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e")
            label.grid(row=row, column=col, sticky="w", padx=5, pady=2)

            if key == "data_nascita":
                entry = DateEntry(
                    parent_frame,
                    selectmode='day',
                    date_pattern='dd/mm/yyyy',
                    font=("Helvetica", 10),
                    background="#bdc3c7",
                    foreground="black",
                    headersbackground="#34495e",
                    headersforeground="white",
                    normalbackground="white"
                )
            else:
                entry = tk.Entry(
                    parent_frame,
                    font=("Helvetica", 10),
                    bd=1,
                    relief="solid",
                    highlightbackground="#bdc3c7",
                    highlightcolor="#3498db"
                )
            entry.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)
            self.entries[key] = entry

            col += 2
            if col >= 4:  # 2 colonne di input per riga
                col = 0
                row += 1

        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_columnconfigure(3, weight=1)

    def _create_player_list(self, parent_frame):
        # Configura il Treeview per la lista dei partecipanti
        self.player_tree = ttk.Treeview(
            parent_frame,
            columns=("ID", "Nome", "Cognome", "CF", "Data Nascita", "Città", "Soprannome"),
            show="headings",
            selectmode="browse"
        )

        # Stile per le intestazioni della tabella
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 10), rowheight=25)
        self.style.map('Treeview', background=[('selected', '#3498db')])

        self.player_tree.heading("ID", text="ID", anchor="center")
        self.player_tree.heading("Nome", text="Nome", anchor="w")
        self.player_tree.heading("Cognome", text="Cognome", anchor="w")
        self.player_tree.heading("CF", text="Codice Fiscale", anchor="w")
        self.player_tree.heading("Data Nascita", text="Data Nascita", anchor="center")
        self.player_tree.heading("Città", text="Città", anchor="w")
        self.player_tree.heading("Soprannome", text="Soprannome", anchor="w")

        self.player_tree.column("ID", width=40, anchor="center")
        self.player_tree.column("Nome", width=100)
        self.player_tree.column("Cognome", width=100)
        self.player_tree.column("CF", width=120)
        self.player_tree.column("Data Nascita", width=100, anchor="center")
        self.player_tree.column("Città", width=100)
        self.player_tree.column("Soprannome", width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=scrollbar.set)

        self.player_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.player_tree.bind("<<TreeviewSelect>>", self._load_selected_player_to_form)

        self._load_players_data()  # Carica dati di esempio all'avvio

    def _load_players_data(self):
        # Simula il caricamento dei dati dal DB
        # Sostituisci con la tua logica di recupero dati reale
        for item in self.player_tree.get_children():
            self.player_tree.delete(item)

        sample_players = [
            (1, "Mario", "Rossi", "MRORSS80A01H501Z", "15/01/1980", "Roma", "SuperMario"),
            (2, "Luigi", "Verdi", "LGIVRD85B02G602Y", "20/02/1985", "Milano", "IlBaffo"),
            (3, "Anna", "Bianchi", "ANNBCN92C03L703X", "01/03/1992", "Napoli", ""),
            (4, "Marco", "Gialli", "MRCGLL95D04M804W", "10/04/1995", "Torino", "IlGiallo")
        ]
        for player in sample_players:
            self.player_tree.insert("", "end", iid=player[0], values=player)

    def _clear_form(self):
        for entry in self.entries.values():
            if isinstance(entry, DateEntry):
                entry.set_date(None)  # Clear date
            else:
                entry.delete(0, tk.END)
        self.player_tree.selection_remove(self.player_tree.selection())  # Deseleziona treeview
        self.current_player_id = None

    def _load_selected_player_to_form(self, event):
        selected_item = self.player_tree.focus()
        if not selected_item:
            return

        values = self.player_tree.item(selected_item, 'values')
        self.current_player_id = values[0]  # ID del partecipante

        self._clear_form()
        self.entries["nome"].insert(0, values[1])
        self.entries["cognome"].insert(0, values[2])
        self.entries["codice_fiscale"].insert(0, values[3])
        # Gestione della data, supponendo formato dd/mm/yyyy per DateEntry
        try:
            day, month, year = map(int, values[4].split('/'))
            self.entries["data_nascita"].set_date(datetime.date(year, month, day))
        except (ValueError, IndexError):
            self.entries["data_nascita"].set_date(None)  # Clear if invalid

        self.entries["citta"].insert(0, values[5])  # This is simplified for now
        self.entries["soprannome"].insert(0, values[6])

        # Qui potresti voler caricare i dettagli completi dell'indirizzo dal DB
        # basandoti sull'ID del partecipante e popolare i campi via, numero_civico, cap

    def _add_player_action(self):
        nome = self.entries["nome"].get()
        cognome = self.entries["cognome"].get()
        cf = self.entries["codice_fiscale"].get()
        data_nascita_str = ""
        try:
            data_nascita_str = self.entries["data_nascita"].get_date().strftime('%Y-%m-%d')
        except AttributeError:  # get_date() might return None if no date selected
            pass

        citta = self.entries["citta"].get()  # Simplified
        soprannome = self.entries["soprannome"].get()

        if not nome or not cognome:
            messagebox.showerror("Errore", "Nome e Cognome sono campi obbligatori.")
            return

        print(f"Aggiungi Partecipante: {nome} {cognome} ({cf}), Data Nascita: {data_nascita_str}")
        # Logica per inserire nel DB
        messagebox.showinfo("Successo", f"Partecipante '{nome} {cognome}' aggiunto (simulato).")
        self._load_players_data()
        self._clear_form()

    def _edit_player_action(self):
        if not hasattr(self, 'current_player_id') or not self.current_player_id:
            messagebox.showerror("Errore", "Seleziona un partecipante da modificare.")
            return

        nome = self.entries["nome"].get()
        cognome = self.entries["cognome"].get()
        cf = self.entries["codice_fiscale"].get()
        data_nascita_str = ""
        try:
            data_nascita_str = self.entries["data_nascita"].get_date().strftime('%Y-%m-%d')
        except AttributeError:
            pass

        citta = self.entries["citta"].get()  # Simplified
        soprannome = self.entries["soprannome"].get()

        if not nome or not cognome:
            messagebox.showerror("Errore", "Nome e Cognome sono campi obbligatori.")
            return

        print(f"Modifica Partecipante ID {self.current_player_id}: {nome} {cognome}, Data Nascita: {data_nascita_str}")
        # Logica per aggiornare nel DB
        messagebox.showinfo("Successo", f"Partecipante '{nome} {cognome}' modificato (simulato).")
        self._load_players_data()
        self._clear_form()

    def _delete_player_action(self):
        if not hasattr(self, 'current_player_id') or not self.current_player_id:
            messagebox.showerror("Errore", "Seleziona un partecipante da eliminare.")
            return

        if messagebox.askyesno("Conferma Eliminazione",
                               f"Sei sicuro di voler eliminare il partecipante ID {self.current_player_id}?"):
            print(f"Elimina Partecipante ID {self.current_player_id}")
            # Logica per eliminare dal DB
            messagebox.showinfo("Successo", "Partecipante eliminato (simulato).")
            self._load_players_data()
            self._clear_form()


class TeamManagementWidget(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#ecf0f1")
        self.style = ttk.Style()  # Inizializza lo stile per Treeview

        self.current_tournament = "Torneo di Briscola 2026"  # Placeholder
        self.current_team_id = None
        self.create_layout()

    def create_layout(self):
        title_label = tk.Label(
            self,
            text="👥 Gestione Squadre",
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        title_label.pack(pady=20)

        # Selezione Torneo (se ci sono più tornei)
        tournament_select_frame = tk.Frame(self, bg="#ecf0f1")
        tournament_select_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(tournament_select_frame, text="Seleziona Torneo:", font=("Helvetica", 12), bg="#ecf0f1",
                 fg="#34495e").pack(side="left", padx=5)
        self.tournament_combobox = ttk.Combobox(tournament_select_frame, font=("Helvetica", 12), state="readonly")
        self.tournament_combobox['values'] = ["Torneo di Briscola 2026", "Torneo Estivo 2025"]  # Esempio
        self.tournament_combobox.set(self.current_tournament)
        self.tournament_combobox.pack(side="left", expand=True, fill="x", padx=5)
        self.tournament_combobox.bind("<<ComboboxSelected>>", self._on_tournament_selected)

        # Frame per la creazione/modifica squadra
        team_form_frame = tk.Frame(self, bg="#ecf0f1", padx=10, pady=10, relief="groove", bd=1)
        team_form_frame.pack(fill="x", padx=20, pady=10)
        self._create_team_form(team_form_frame)

        # Frame per la lista delle squadre
        teams_list_frame = tk.Frame(self, bg="#ecf0f1")
        teams_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._create_teams_list(teams_list_frame)

        # Pulsanti di azione per le squadre
        button_frame = tk.Frame(self, bg="#ecf0f1")
        button_frame.pack(pady=10)

        btn_style = {
            "font": ("Helvetica", 12, "bold"),
            "fg": "white",
            "bd": 0,
            "height": 2,
            "width": 15,
            "cursor": "hand2",
            "relief": "flat"
        }

        tk.Button(button_frame, text="Aggiungi Squadra", command=self._add_team_action, bg="#1abc9c", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Modifica Squadra", command=self._edit_team_action, bg="#3498db",
                  **btn_style).pack(side="left", padx=5)
        tk.Button(button_frame, text="Elimina Squadra", command=self._delete_team_action, bg="#e74c3c",
                  **btn_style).pack(side="left", padx=5)
        tk.Button(button_frame, text="Gestisci Membri", command=self._manage_team_members, bg="#f39c12",
                  **btn_style).pack(side="left", padx=5)

    def _create_team_form(self, parent_frame):
        tk.Label(parent_frame, text="Nome Squadra:", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e").grid(row=0,
                                                                                                              column=0,
                                                                                                              sticky="w",
                                                                                                              padx=5,
                                                                                                              pady=2)
        self.entry_team_name = tk.Entry(parent_frame, font=("Helvetica", 12), bd=1, relief="solid",
                                        highlightbackground="#bdc3c7", highlightcolor="#3498db")
        self.entry_team_name.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        parent_frame.grid_columnconfigure(1, weight=1)

    def _create_teams_list(self, parent_frame):
        self.teams_tree = ttk.Treeview(
            parent_frame,
            columns=("ID", "Nome Squadra", "Torneo", "Data Iscrizione", "Squalificata"),
            show="headings",
            selectmode="browse"
        )
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 10), rowheight=25)
        self.style.map('Treeview', background=[('selected', '#3498db')])

        self.teams_tree.heading("ID", text="ID", anchor="center")
        self.teams_tree.heading("Nome Squadra", text="Nome Squadra", anchor="w")
        self.teams_tree.heading("Torneo", text="Torneo", anchor="w")
        self.teams_tree.heading("Data Iscrizione", text="Data Iscrizione", anchor="center")
        self.teams_tree.heading("Squalificata", text="Squalificata", anchor="center")

        self.teams_tree.column("ID", width=40, anchor="center")
        self.teams_tree.column("Nome Squadra", width=150)
        self.teams_tree.column("Torneo", width=150)
        self.teams_tree.column("Data Iscrizione", width=120, anchor="center")
        self.teams_tree.column("Squalificata", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.teams_tree.yview)
        self.teams_tree.configure(yscrollcommand=scrollbar.set)

        self.teams_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.teams_tree.bind("<<TreeviewSelect>>", self._load_selected_team_to_form)

        self._load_teams_data()

    def _on_tournament_selected(self, event):
        self.current_tournament = self.tournament_combobox.get()
        self._load_teams_data()

    def _load_teams_data(self):
        for item in self.teams_tree.get_children():
            self.teams_tree.delete(item)

        # Simula il caricamento delle squadre per il torneo selezionato
        sample_teams = [
            (101, "I Fortissimi", self.current_tournament, "2026-01-10", "No"),
            (102, "Gli Imbattibili", self.current_tournament, "2026-01-12", "No"),
            (103, "Le Carte Pazze", self.current_tournament, "2026-01-15",
             "Si" if self.current_tournament == "Torneo Estivo 2025" else "No")
        ]
        for team in sample_teams:
            self.teams_tree.insert("", "end", iid=team[0], values=team)

    def _clear_form(self):
        self.entry_team_name.delete(0, tk.END)
        self.teams_tree.selection_remove(self.teams_tree.selection())
        self.current_team_id = None

    def _load_selected_team_to_form(self, event):
        selected_item = self.teams_tree.focus()
        if not selected_item:
            return

        values = self.teams_tree.item(selected_item, 'values')
        self.current_team_id = values[0]

        self._clear_form()
        self.entry_team_name.insert(0, values[1])
        # Non popolare il torneo qui, dato che è gestito dal combobox

    def _add_team_action(self):
        nome_squadra = self.entry_team_name.get()
        if not nome_squadra:
            messagebox.showerror("Errore", "Il nome della squadra è obbligatorio.")
            return

        print(f"Aggiungi Squadra: {nome_squadra} al torneo {self.current_tournament}")
        # Logica per inserire nel DB
        messagebox.showinfo("Successo", f"Squadra '{nome_squadra}' aggiunta (simulato).")
        self._load_teams_data()
        self._clear_form()

    def _edit_team_action(self):
        if not hasattr(self, 'current_team_id') or not self.current_team_id:
            messagebox.showerror("Errore", "Seleziona una squadra da modificare.")
            return

        nome_squadra = self.entry_team_name.get()
        if not nome_squadra:
            messagebox.showerror("Errore", "Il nome della squadra è obbligatorio.")
            return

        print(f"Modifica Squadra ID {self.current_team_id}: {nome_squadra}")
        # Logica per aggiornare nel DB
        messagebox.showinfo("Successo", f"Squadra '{nome_squadra}' modificata (simulato).")
        self._load_teams_data()
        self._clear_form()

    def _delete_team_action(self):
        if not hasattr(self, 'current_team_id') or not self.current_team_id:
            messagebox.showerror("Errore", "Seleziona una squadra da eliminare.")
            return

        if messagebox.askyesno("Conferma Eliminazione",
                               f"Sei sicuro di voler eliminare la squadra ID {self.current_team_id}?"):
            print(f"Elimina Squadra ID {self.current_team_id}")
            # Logica per eliminare dal DB
            messagebox.showinfo("Successo", "Squadra eliminata (simulato).")
            self._load_teams_data()
            self._clear_form()

    def _manage_team_members(self):
        if not hasattr(self, 'current_team_id') or not self.current_team_id:
            messagebox.showerror("Errore", "Seleziona una squadra per gestire i membri.")
            return

        team_name = self.entry_team_name.get()
        messagebox.showinfo("Gestione Membri", f"Gestisci membri per la squadra '{team_name}' (work in progress).")
        # Qui potresti aprire una nuova finestra di dialogo o caricare un altro widget
        # per aggiungere/rimuovere partecipanti alla squadra selezionata.


class MatchManagementWidget(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#ecf0f1")
        self.style = ttk.Style()  # Inizializza lo stile per Treeview

        self.current_tournament = "Torneo di Briscola 2026"  # Placeholder
        self.current_turn_id = None
        self.current_match_id = None
        self.create_layout()

    def create_layout(self):
        title_label = tk.Label(
            self,
            text="🃏 Gestione Partite",
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        title_label.pack(pady=20)

        # Selezione Torneo
        tournament_select_frame = tk.Frame(self, bg="#ecf0f1")
        tournament_select_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(tournament_select_frame, text="Seleziona Torneo:", font=("Helvetica", 12), bg="#ecf0f1",
                 fg="#34495e").pack(side="left", padx=5)
        self.tournament_combobox = ttk.Combobox(tournament_select_frame, font=("Helvetica", 12), state="readonly")
        self.tournament_combobox['values'] = ["Torneo di Briscola 2026", "Torneo Estivo 2025"]  # Esempio
        self.tournament_combobox.set(self.current_tournament)
        self.tournament_combobox.pack(side="left", expand=True, fill="x", padx=5)
        self.tournament_combobox.bind("<<ComboboxSelected>>", self._on_tournament_selected)

        # Main content frame con due colonne (Turni e Partite)
        main_content_frame = tk.Frame(self, bg="#ecf0f1")
        main_content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        main_content_frame.grid_columnconfigure(0, weight=1)
        main_content_frame.grid_columnconfigure(1, weight=3)  # Partite più spazio

        # Colonna Turni
        turn_column_frame = tk.Frame(main_content_frame, bg="#ecf0f1", padx=10, pady=10, relief="groove", bd=1)
        turn_column_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._create_turn_section(turn_column_frame)

        # Colonna Partite
        match_column_frame = tk.Frame(main_content_frame, bg="#ecf0f1", padx=10, pady=10, relief="groove", bd=1)
        match_column_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._create_match_section(match_column_frame)

    def _create_turn_section(self, parent_frame):
        tk.Label(parent_frame, text="Gestione Turni", font=("Helvetica", 16, "bold"), bg="#ecf0f1", fg="#2c3e50").pack(
            pady=10)

        # Form per aggiungere turno
        turn_form_frame = tk.Frame(parent_frame, bg="#ecf0f1")
        turn_form_frame.pack(fill="x", pady=5)
        tk.Label(turn_form_frame, text="Numero Turno:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").pack(
            side="left", padx=5)
        self.entry_turn_number = tk.Entry(turn_form_frame, font=("Helvetica", 10), width=5, bd=1, relief="solid")
        self.entry_turn_number.pack(side="left", padx=5)
        tk.Button(
            turn_form_frame,
            text="Aggiungi Turno",
            command=self._add_turn_action,
            font=("Helvetica", 10, "bold"),
            bg="#2ecc71",
            fg="white",
            bd=0,
            cursor="hand2"
        ).pack(side="left", padx=5)

        # Lista dei turni
        self.turns_tree = ttk.Treeview(
            parent_frame,
            columns=("ID", "Numero"),
            show="headings",
            selectmode="browse",
            height=10  # Per limitare l'altezza in questa colonna
        )
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 9), rowheight=20)
        self.style.map('Treeview', background=[('selected', '#3498db')])

        self.turns_tree.heading("ID", text="ID", anchor="center")
        self.turns_tree.heading("Numero", text="Numero Turno", anchor="center")
        self.turns_tree.column("ID", width=40, anchor="center")
        self.turns_tree.column("Numero", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.turns_tree.yview)
        self.turns_tree.configure(yscrollcommand=scrollbar.set)

        self.turns_tree.pack(fill="both", expand=True, pady=10)
        scrollbar.pack(side="right", fill="y")
        self.turns_tree.bind("<<TreeviewSelect>>", self._on_turn_selected)
        self._load_turns_data()

    def _create_match_section(self, parent_frame):
        tk.Label(parent_frame, text="Dettagli Partite", font=("Helvetica", 16, "bold"), bg="#ecf0f1",
                 fg="#2c3e50").pack(pady=10)

        # Form per aggiungere/modificare partita
        match_form_frame = tk.Frame(parent_frame, bg="#ecf0f1", pady=5)
        match_form_frame.pack(fill="x")

        tk.Label(match_form_frame, text="Data:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").grid(row=0,
                                                                                                          column=0,
                                                                                                          sticky="w",
                                                                                                          padx=5)
        self.entry_match_date = DateEntry(match_form_frame, selectmode='day', date_pattern='dd/mm/yyyy',
                                          font=("Helvetica", 10))
        self.entry_match_date.grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(match_form_frame, text="Orario:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").grid(row=0,
                                                                                                            column=2,
                                                                                                            sticky="w",
                                                                                                            padx=5)
        self.entry_match_time = tk.Entry(match_form_frame, font=("Helvetica", 10), bd=1, relief="solid")
        self.entry_match_time.insert(0, datetime.datetime.now().strftime("%H:%M"))
        self.entry_match_time.grid(row=0, column=3, sticky="ew", padx=5)

        tk.Label(match_form_frame, text="Luogo:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").grid(row=1,
                                                                                                           column=0,
                                                                                                           sticky="w",
                                                                                                           padx=5)
        self.entry_match_location = tk.Entry(match_form_frame, font=("Helvetica", 10), bd=1, relief="solid")
        self.entry_match_location.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5)

        match_form_frame.grid_columnconfigure(1, weight=1)
        match_form_frame.grid_columnconfigure(3, weight=1)

        team_selection_frame = tk.Frame(parent_frame, bg="#ecf0f1", pady=5)
        team_selection_frame.pack(fill="x")
        tk.Label(team_selection_frame, text="Squadra 1:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").pack(
            side="left", padx=5)
        self.team1_combobox = ttk.Combobox(team_selection_frame, font=("Helvetica", 10), state="readonly")
        self.team1_combobox.pack(side="left", expand=True, fill="x", padx=5)
        tk.Label(team_selection_frame, text="Squadra 2:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").pack(
            side="left", padx=5)
        self.team2_combobox = ttk.Combobox(team_selection_frame, font=("Helvetica", 10), state="readonly")
        self.team2_combobox.pack(side="left", expand=True, fill="x", padx=5)
        self._load_teams_for_comboboxes()

        match_buttons_frame = tk.Frame(parent_frame, bg="#ecf0f1")
        match_buttons_frame.pack(pady=5)
        tk.Button(match_buttons_frame, text="Aggiungi Partita", command=self._add_match_action,
                  font=("Helvetica", 10, "bold"), bg="#1abc9c", fg="white", bd=0, cursor="hand2").pack(side="left",
                                                                                                       padx=5)
        tk.Button(match_buttons_frame, text="Aggiorna Partita", command=self._update_match_action,
                  font=("Helvetica", 10, "bold"), bg="#3498db", fg="white", bd=0, cursor="hand2").pack(side="left",
                                                                                                       padx=5)
        tk.Button(match_buttons_frame, text="Elimina Partita", command=self._delete_match_action,
                  font=("Helvetica", 10, "bold"), bg="#e74c3c", fg="white", bd=0, cursor="hand2").pack(side="left",
                                                                                                       padx=5)
        tk.Button(match_buttons_frame, text="Pulisci", command=self._clear_match_form, font=("Helvetica", 10, "bold"),
                  bg="#95a5a6", fg="white", bd=0, cursor="hand2").pack(side="left", padx=5)

        # Lista delle partite
        self.matches_tree = ttk.Treeview(
            parent_frame,
            columns=("ID", "Data", "Orario", "Luogo", "Squadra 1", "Punteggio 1", "Squadra 2", "Punteggio 2"),
            show="headings",
            selectmode="browse"
        )
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 9), rowheight=20)
        self.style.map('Treeview', background=[('selected', '#3498db')])

        self.matches_tree.heading("ID", text="ID", anchor="center")
        self.matches_tree.heading("Data", text="Data", anchor="center")
        self.matches_tree.heading("Orario", text="Orario", anchor="center")
        self.matches_tree.heading("Luogo", text="Luogo", anchor="w")
        self.matches_tree.heading("Squadra 1", text="Sq 1", anchor="w")
        self.matches_tree.heading("Punteggio 1", text="Punt 1", anchor="center")
        self.matches_tree.heading("Squadra 2", text="Sq 2", anchor="w")
        self.matches_tree.heading("Punteggio 2", text="Punt 2", anchor="center")

        self.matches_tree.column("ID", width=30, anchor="center")
        self.matches_tree.column("Data", width=80, anchor="center")
        self.matches_tree.column("Orario", width=60, anchor="center")
        self.matches_tree.column("Luogo", width=80)
        self.matches_tree.column("Squadra 1", width=70)
        self.matches_tree.column("Punteggio 1", width=60, anchor="center")
        self.matches_tree.column("Squadra 2", width=70)
        self.matches_tree.column("Punteggio 2", width=60, anchor="center")

        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.matches_tree.yview)
        self.matches_tree.configure(yscrollcommand=scrollbar.set)

        self.matches_tree.pack(fill="both", expand=True, pady=10)
        scrollbar.pack(side="right", fill="y")
        self.matches_tree.bind("<<TreeviewSelect>>", self._on_match_selected)

        # Punteggi (da aggiungere/modificare dopo che la partita è stata selezionata)
        score_frame = tk.Frame(parent_frame, bg="#ecf0f1", pady=10)
        score_frame.pack(fill="x", pady=5)
        tk.Label(score_frame, text="Punteggio Squadra 1:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").pack(
            side="left", padx=5)
        self.entry_score1 = tk.Entry(score_frame, font=("Helvetica", 10), width=5, bd=1, relief="solid")
        self.entry_score1.pack(side="left", padx=5)
        tk.Label(score_frame, text="Punteggio Squadra 2:", font=("Helvetica", 10), bg="#ecf0f1", fg="#34495e").pack(
            side="left", padx=5)
        self.entry_score2 = tk.Entry(score_frame, font=("Helvetica", 10), width=5, bd=1, relief="solid")
        self.entry_score2.pack(side="left", padx=5)
        tk.Button(score_frame, text="Salva Punteggi", command=self._save_scores_action, font=("Helvetica", 10, "bold"),
                  bg="#f39c12", fg="white", bd=0, cursor="hand2").pack(side="right", padx=5)

    def _on_tournament_selected(self, event):
        self.current_tournament = self.tournament_combobox.get()
        self.current_turn_id = None
        self._load_turns_data()
        self._load_matches_data()
        self._load_teams_for_comboboxes()
        self._clear_match_form()

    def _load_turns_data(self):
        for item in self.turns_tree.get_children():
            self.turns_tree.delete(item)
        # Simula caricamento turni per il torneo selezionato
        sample_turns = [
            (1, 1),
            (2, 2),
            (3, 3)
        ]
        if self.current_tournament == "Torneo Estivo 2025":
            sample_turns = [(10, 1), (11, 2)]

        for turn in sample_turns:
            self.turns_tree.insert("", "end", iid=turn[0], values=turn)

    def _load_teams_for_comboboxes(self):
        # Simula il caricamento delle squadre disponibili per il torneo corrente
        # In un'applicazione reale, dovresti filtrare le squadre iscritte al torneo
        all_teams = ["Squadra Alpha", "Squadra Beta", "Squadra Gamma", "Squadra Delta"]
        self.team1_combobox['values'] = all_teams
        self.team2_combobox['values'] = all_teams
        self.team1_combobox.set("")
        self.team2_combobox.set("")

    def _add_turn_action(self):
        turn_number = self.entry_turn_number.get()
        if not turn_number.isdigit():
            messagebox.showerror("Errore", "Il numero del turno deve essere un numero intero.")
            return

        print(f"Aggiungi Turno {turn_number} al torneo {self.current_tournament}")
        # Logica per inserire turno nel DB
        messagebox.showinfo("Successo", f"Turno {turn_number} aggiunto (simulato).")
        self._load_turns_data()
        self.entry_turn_number.delete(0, tk.END)

    def _on_turn_selected(self, event):
        selected_item = self.turns_tree.focus()
        if not selected_item:
            self.current_turn_id = None
            self._load_matches_data()  # Clear matches
            return

        values = self.turns_tree.item(selected_item, 'values')
        self.current_turn_id = values[0]
        self._load_matches_data()
        self._clear_match_form()

    def _load_matches_data(self):
        for item in self.matches_tree.get_children():
            self.matches_tree.delete(item)

        if not self.current_turn_id:
            return

        # Simula caricamento partite per il turno selezionato
        sample_matches = []
        if self.current_turn_id == 1:
            sample_matches = [
                (101, "2026-02-28", "18:00", "Palestra A", "Squadra Alpha", 2, "Squadra Beta", 0),
                (102, "2026-02-28", "19:00", "Palestra A", "Squadra Gamma", 1, "Squadra Delta", 1)
            ]
        elif self.current_turn_id == 2:
            sample_matches = [
                (103, "2026-03-05", "18:30", "Circolo Sportivo", "Squadra Alpha", None, "Squadra Gamma", None)
            ]

        for match in sample_matches:
            self.matches_tree.insert("", "end", iid=match[0], values=match)

    def _clear_match_form(self):
        self.entry_match_date.set_date(None)
        self.entry_match_time.delete(0, tk.END)
        self.entry_match_time.insert(0, datetime.datetime.now().strftime("%H:%M"))
        self.entry_match_location.delete(0, tk.END)
        self.team1_combobox.set("")
        self.team2_combobox.set("")
        self.entry_score1.delete(0, tk.END)
        self.entry_score2.delete(0, tk.END)
        self.matches_tree.selection_remove(self.matches_tree.selection())
        self.current_match_id = None

    def _on_match_selected(self, event):
        selected_item = self.matches_tree.focus()
        if not selected_item:
            self._clear_match_form()
            return

        values = self.matches_tree.item(selected_item, 'values')
        self.current_match_id = values[0]

        self._clear_match_form()
        # Data
        try:
            # Tenta di parsare sia YYYY-MM-DD che DD/MM/YYYY
            date_str = values[1]
            try:
                # Try YYYY-MM-DD format first
                year, month, day = map(int, date_str.split('-'))
                self.entry_match_date.set_date(datetime.date(year, month, day))
            except ValueError:
                # If YYYY-MM-DD fails, try DD/MM/YYYY
                day, month, year = map(int, date_str.split('/'))
                self.entry_match_date.set_date(datetime.date(year, month, day))
        except (ValueError, IndexError):
            self.entry_match_date.set_date(None)

        self.entry_match_time.delete(0, tk.END)
        self.entry_match_time.insert(0, values[2])
        self.entry_match_location.delete(0, tk.END)
        self.entry_match_location.insert(0, values[3])
        self.team1_combobox.set(values[4])
        self.team2_combobox.set(values[6])
        self.entry_score1.insert(0, values[5] if values[5] is not None else "")
        self.entry_score2.insert(0, values[7] if values[7] is not None else "")

    def _add_match_action(self):
        if not self.current_turn_id:
            messagebox.showerror("Errore", "Seleziona un turno prima di aggiungere una partita.")
            return

        data_str = ""
        try:
            data_str = self.entry_match_date.get_date().strftime('%Y-%m-%d')
        except AttributeError:
            messagebox.showerror("Errore", "Seleziona una data per la partita.")
            return

        orario = self.entry_match_time.get()
        luogo = self.entry_match_location.get()
        squadra1 = self.team1_combobox.get()
        squadra2 = self.team2_combobox.get()

        if not all([data_str, orario, luogo, squadra1, squadra2]):
            messagebox.showerror("Errore", "Compila tutti i campi della partita.")
            return
        if squadra1 == squadra2:
            messagebox.showerror("Errore", "Le due squadre non possono essere le stesse.")
            return

        print(
            f"Aggiungi Partita a Turno {self.current_turn_id}: {squadra1} vs {squadra2} il {data_str} alle {orario} a {luogo}")
        # Logica per inserire nel DB
        messagebox.showinfo("Successo", "Partita aggiunta (simulato).")
        self._load_matches_data()
        self._clear_match_form()

    def _update_match_action(self):
        if not self.current_match_id:
            messagebox.showerror("Errore", "Seleziona una partita da aggiornare.")
            return

        data_str = ""
        try:
            data_str = self.entry_match_date.get_date().strftime('%Y-%m-%d')
        except AttributeError:
            messagebox.showerror("Errore", "Seleziona una data per la partita.")
            return

        orario = self.entry_match_time.get()
        luogo = self.entry_match_location.get()
        squadra1 = self.team1_combobox.get()
        squadra2 = self.team2_combobox.get()

        if not all([data_str, orario, luogo, squadra1, squadra2]):
            messagebox.showerror("Errore", "Compila tutti i campi della partita.")
            return
        if squadra1 == squadra2:
            messagebox.showerror("Errore", "Le due squadre non possono essere le stesse.")
            return

        print(
            f"Aggiorna Partita ID {self.current_match_id}: {squadra1} vs {squadra2} il {data_str} alle {orario} a {luogo}")
        # Logica per aggiornare nel DB
        messagebox.showinfo("Successo", "Partita aggiornata (simulato).")
        self._load_matches_data()
        self._clear_match_form()

    def _delete_match_action(self):
        if not self.current_match_id:
            messagebox.showerror("Errore", "Seleziona una partita da eliminare.")
            return

        if messagebox.askyesno("Conferma Eliminazione",
                               f"Sei sicuro di voler eliminare la partita ID {self.current_match_id}?"):
            print(f"Elimina Partita ID {self.current_match_id}")
            # Logica per eliminare dal DB
            messagebox.showinfo("Successo", "Partita eliminata (simulato).")
            self._load_matches_data()
            self._clear_match_form()

    def _save_scores_action(self):
        if not self.current_match_id:
            messagebox.showerror("Errore", "Seleziona una partita per salvare i punteggi.")
            return

        score1 = self.entry_score1.get()
        score2 = self.entry_score2.get()

        if not score1.isdigit() or not score2.isdigit():
            messagebox.showerror("Errore", "I punteggi devono essere numeri interi.")
            return

        print(f"Salva punteggi per Partita ID {self.current_match_id}: {score1}-{score2}")
        # Logica per salvare punteggi nel DB
        messagebox.showinfo("Successo", "Punteggi salvati (simulato).")
        self._load_matches_data()
        self._clear_match_form()


class RankingWidget(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#ecf0f1")
        self.style = ttk.Style()  # Inizializza lo stile per Treeview

        self.current_tournament = "Torneo di Briscola 2026"  # Placeholder
        self.create_layout()

    def create_layout(self):
        title_label = tk.Label(
            self,
            text="📊 Classifica Torneo",
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        title_label.pack(pady=20)

        # Selezione Torneo
        tournament_select_frame = tk.Frame(self, bg="#ecf0f1")
        tournament_select_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(tournament_select_frame, text="Seleziona Torneo:", font=("Helvetica", 12), bg="#ecf0f1",
                 fg="#34495e").pack(side="left", padx=5)
        self.tournament_combobox = ttk.Combobox(tournament_select_frame, font=("Helvetica", 12), state="readonly")
        self.tournament_combobox['values'] = ["Torneo di Briscola 2026", "Torneo Estivo 2025"]  # Esempio
        self.tournament_combobox.set(self.current_tournament)
        self.tournament_combobox.pack(side="left", expand=True, fill="x", padx=5)
        self.tournament_combobox.bind("<<ComboboxSelected>>", self._on_tournament_selected)

        # Tabella Classifica
        ranking_frame = tk.Frame(self, bg="#ecf0f1")
        ranking_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._create_ranking_table(ranking_frame)

        self._load_ranking_data()

    def _create_ranking_table(self, parent_frame):
        self.ranking_tree = ttk.Treeview(
            parent_frame,
            columns=("Posizione", "Squadra", "Vittorie", "Sconfitte", "Pareggi", "Punti"),
            show="headings",
            selectmode="none"  # Non selezionabile per una classifica
        )

        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 10), rowheight=25)
        self.style.map('Treeview',
                       background=[('selected', '#3498db')])  # Anche se non selezionabile, utile per consistenza

        self.ranking_tree.heading("Posizione", text="Pos.", anchor="center")
        self.ranking_tree.heading("Squadra", text="Squadra", anchor="w")
        self.ranking_tree.heading("Vittorie", text="V", anchor="center")
        self.ranking_tree.heading("Sconfitte", text="S", anchor="center")
        self.ranking_tree.heading("Pareggi", text="P", anchor="center")
        self.ranking_tree.heading("Punti", text="Punti", anchor="center")

        self.ranking_tree.column("Posizione", width=50, anchor="center")
        self.ranking_tree.column("Squadra", width=200)
        self.ranking_tree.column("Vittorie", width=50, anchor="center")
        self.ranking_tree.column("Sconfitte", width=50, anchor="center")
        self.ranking_tree.column("Pareggi", width=50, anchor="center")
        self.ranking_tree.column("Punti", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.ranking_tree.yview)
        self.ranking_tree.configure(yscrollcommand=scrollbar.set)

        self.ranking_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_tournament_selected(self, event):
        self.current_tournament = self.tournament_combobox.get()
        self._load_ranking_data()

    def _load_ranking_data(self):
        for item in self.ranking_tree.get_children():
            self.ranking_tree.delete(item)

        # Simula il caricamento della classifica dal DB per il torneo corrente
        # In un'applicazione reale, questa logica dovrebbe calcolare i punti
        # basandosi sui risultati delle partite nel DB.
        sample_ranking = []
        if self.current_tournament == "Torneo di Briscola 2026":
            sample_ranking = [
                (1, "Squadra Alpha", 3, 0, 0, 9),
                (2, "Squadra Gamma", 1, 1, 1, 4),
                (3, "Squadra Beta", 0, 2, 0, 0),
                (4, "Squadra Delta", 0, 1, 1, 1)
            ]
        elif self.current_tournament == "Torneo Estivo 2025":
            sample_ranking = [
                (1, "Vincitori Estate", 5, 0, 0, 15),
                (2, "Sole e Carte", 3, 2, 0, 9),
                (3, "Relax Players", 1, 4, 0, 3)
            ]

        for pos, team, wins, losses, draws, points in sample_ranking:
            self.ranking_tree.insert("", "end", values=(pos, team, wins, losses, draws, points))


# Nuovo Widget per la lista dei tornei e i loro dettagli
class TournamentListWidget(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#ecf0f1")
        self.style = ttk.Style()  # Inizializza lo stile per Treeview

        self.current_selected_tournament_name = None

        # Frames per gestire le due viste: lista e dettagli
        self.list_view_frame = tk.Frame(self, bg="#ecf0f1")
        self.details_view_frame = tk.Frame(self, bg="#ecf0f1")

        self._create_list_view_components()
        self._create_details_view_components()

        self.show_list_view()  # Mostra la lista dei tornei all'avvio

    def _create_list_view_components(self):
        # Titolo
        title_label = tk.Label(
            self.list_view_frame,
            text="📋 Lista Tornei",
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        title_label.pack(pady=20)

        # Form per aggiungere/modificare torneo (semplificato per nome)
        form_frame = tk.Frame(self.list_view_frame, bg="#ecf0f1", padx=10, pady=10, relief="groove", bd=1)
        form_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(form_frame, text="Nome Torneo:", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e").grid(row=0,
                                                                                                           column=0,
                                                                                                           sticky="w",
                                                                                                           padx=5,
                                                                                                           pady=2)
        self.entry_tournament_name_list = tk.Entry(form_frame, font=("Helvetica", 12), bd=1, relief="solid",
                                                   highlightbackground="#bdc3c7", highlightcolor="#3498db")
        self.entry_tournament_name_list.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        form_frame.grid_columnconfigure(1, weight=1)

        # Lista dei tornei
        list_tree_frame = tk.Frame(self.list_view_frame, bg="#ecf0f1")
        list_tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tournament_tree = ttk.Treeview(
            list_tree_frame,
            columns=("Nome", "Tipo", "Data Inizio", "Data Fine"),
            show="headings",
            selectmode="browse"
        )
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 10), rowheight=25)
        self.style.map('Treeview', background=[('selected', '#3498db')])

        self.tournament_tree.heading("Nome", text="Nome Torneo", anchor="w")
        self.tournament_tree.heading("Tipo", text="Tipo", anchor="center")
        self.tournament_tree.heading("Data Inizio", text="Data Inizio", anchor="center")
        self.tournament_tree.heading("Data Fine", text="Data Fine", anchor="center")

        self.tournament_tree.column("Nome", width=200)
        self.tournament_tree.column("Tipo", width=100, anchor="center")
        self.tournament_tree.column("Data Inizio", width=120, anchor="center")
        self.tournament_tree.column("Data Fine", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(list_tree_frame, orient="vertical", command=self.tournament_tree.yview)
        self.tournament_tree.configure(yscrollcommand=scrollbar.set)

        self.tournament_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tournament_tree.bind("<<TreeviewSelect>>", self._load_selected_tournament_to_form)
        self.tournament_tree.bind("<Double-1>", self._on_double_click_tournament)

        # Pulsanti di azione
        button_frame = tk.Frame(self.list_view_frame, bg="#ecf0f1")
        button_frame.pack(pady=10)

        btn_style = {
            "font": ("Helvetica", 12, "bold"),
            "fg": "white",
            "bd": 0,
            "height": 2,
            "width": 15,
            "cursor": "hand2",
            "relief": "flat"
        }

        tk.Button(button_frame, text="Aggiungi", command=self._add_tournament_action, bg="#1abc9c", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Modifica", command=self._edit_tournament_action, bg="#3498db", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Elimina", command=self._delete_tournament_action, bg="#e74c3c", **btn_style).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Pulisci Campi", command=self._clear_list_form, bg="#95a5a6", **btn_style).pack(
            side="left", padx=5)

    def _create_details_view_components(self):
        # Titolo Dettagli Torneo
        self.details_title_label = tk.Label(
            self.details_view_frame,
            text="Dettagli Torneo: [Nome Torneo]",  # Placeholder
            font=("Helvetica", 20, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        self.details_title_label.pack(pady=20)

        # Frame per le info del torneo
        info_frame = tk.Frame(self.details_view_frame, bg="#ecf0f1", padx=10, pady=10, relief="groove", bd=1)
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(info_frame, text="Tipo:", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e").grid(row=0, column=0,
                                                                                                    sticky="w", padx=5,
                                                                                                    pady=2)
        self.info_tipo_label = tk.Label(info_frame, text="", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e")
        self.info_tipo_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        tk.Label(info_frame, text="Inizio:", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e").grid(row=1, column=0,
                                                                                                      sticky="w",
                                                                                                      padx=5, pady=2)
        self.info_data_inizio_label = tk.Label(info_frame, text="", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e")
        self.info_data_inizio_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        tk.Label(info_frame, text="Fine:", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e").grid(row=2, column=0,
                                                                                                    sticky="w", padx=5,
                                                                                                    pady=2)
        self.info_data_fine_label = tk.Label(info_frame, text="", font=("Helvetica", 12), bg="#ecf0f1", fg="#34495e")
        self.info_data_fine_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        info_frame.grid_columnconfigure(1, weight=1)

        # Partecipanti/Squadre del torneo
        tk.Label(self.details_view_frame, text="Partecipanti/Squadre Iscritte:", font=("Helvetica", 16, "bold"),
                 bg="#ecf0f1", fg="#2c3e50").pack(pady=15)

        participants_frame = tk.Frame(self.details_view_frame, bg="#ecf0f1")
        participants_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.details_participants_tree = ttk.Treeview(
            participants_frame,
            columns=("Nome", "Membri"),  # Adattare per singolo/doppio
            show="headings",
            selectmode="none"
        )
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#34495e",
                             foreground="white")
        self.style.configure("Treeview", font=("Helvetica", 9), rowheight=20)

        self.details_participants_tree.heading("Nome", text="Nome (Squadra/Partecipante)", anchor="w")
        self.details_participants_tree.heading("Membri", text="Membri (se squadra)", anchor="w")
        self.details_participants_tree.column("Nome", width=250)
        self.details_participants_tree.column("Membri", width=350)

        part_scrollbar = ttk.Scrollbar(participants_frame, orient="vertical",
                                       command=self.details_participants_tree.yview)
        self.details_participants_tree.configure(yscrollcommand=part_scrollbar.set)
        self.details_participants_tree.pack(side="left", fill="both", expand=True)
        part_scrollbar.pack(side="right", fill="y")

        # Pulsante Indietro
        back_button = tk.Button(
            self.details_view_frame,
            text="← Torna alla Lista",
            command=self.show_list_view,
            font=("Helvetica", 12, "bold"),
            bg="#34495e",
            fg="white",
            bd=0,
            height=2,
            width=20,
            cursor="hand2"
        )
        back_button.pack(pady=20)

    def show_list_view(self):
        self.details_view_frame.pack_forget()
        self.list_view_frame.pack(fill="both", expand=True)
        self._load_tournaments_data()  # Ricarica la lista quando si torna

    def _show_tournament_details(self, tournament_name):
        self.list_view_frame.pack_forget()
        self.details_view_frame.pack(fill="both", expand=True)

        # Aggiorna il titolo e le informazioni del torneo
        self.details_title_label.config(text=f"Dettagli Torneo: {tournament_name}")

        # Simula il recupero dei dettagli del torneo (in un'app reale verrebbe dal DB)
        tournaments_data = self._get_sample_tournaments_data()
        selected_tournament = next((t for t in tournaments_data if t[0] == tournament_name), None)

        if selected_tournament:
            self.info_tipo_label.config(text=selected_tournament[1])
            self.info_data_inizio_label.config(text=selected_tournament[2])
            self.info_data_fine_label.config(text=selected_tournament[3])
            self._load_tournament_participants_data(tournament_name)
        else:
            self.info_tipo_label.config(text="N/D")
            self.info_data_inizio_label.config(text="N/D")
            self.info_data_fine_label.config(text="N/D")
            messagebox.showerror("Errore", f"Dettagli per il torneo '{tournament_name}' non trovati.")
            self._clear_participants_tree()

    def _get_sample_tournaments_data(self):
        # Questa funzione dovrebbe recuperare i dati reali dal tuo DB
        # Per ora, restituisce dati di esempio
        return [
            ("Torneo di Briscola 2026", "Singolo", "2026-02-01", "2026-03-31"),
            ("Torneo Estivo 2025", "Doppio/Squadre", "2025-07-15", "2025-08-30"),
            ("Campionato Invernale", "Singolo", "2025-11-01", "2026-01-15")
        ]

    def _load_tournaments_data(self):
        for item in self.tournament_tree.get_children():
            self.tournament_tree.delete(item)

        # Carica i dati di esempio (sostituire con dati reali dal DB)
        sample_tournaments = self._get_sample_tournaments_data()
        for tournament in sample_tournaments:
            self.tournament_tree.insert("", "end", values=tournament)

    def _load_tournament_participants_data(self, tournament_name):
        self._clear_participants_tree()
        # Simula il caricamento di partecipanti/squadre per il torneo specifico
        # Questa logica dovrebbe interrogare il tuo DB usando il `tournament_name`

        if tournament_name == "Torneo di Briscola 2026":
            self.details_participants_tree.insert("", "end", values=("Mario Rossi", "N/A"))
            self.details_participants_tree.insert("", "end", values=("Luigi Verdi", "N/A"))
            self.details_participants_tree.insert("", "end", values=("Anna Bianchi", "N/A"))
        elif tournament_name == "Torneo Estivo 2025":
            self.details_participants_tree.insert("", "end", values=("Squadra Sole", "Marco, Laura"))
            self.details_participants_tree.insert("", "end", values=("Squadra Luna", "Paolo, Sara"))
        else:
            self.details_participants_tree.insert("", "end",
                                                  values=("Nessun partecipante/squadra trovata per questo torneo.", ""))

    def _clear_participants_tree(self):
        for item in self.details_participants_tree.get_children():
            self.details_participants_tree.delete(item)

    def _clear_list_form(self):
        self.entry_tournament_name_list.delete(0, tk.END)
        self.tournament_tree.selection_remove(self.tournament_tree.selection())
        self.current_selected_tournament_name = None

    def _load_selected_tournament_to_form(self, event):
        selected_item = self.tournament_tree.focus()
        if not selected_item:
            return
        values = self.tournament_tree.item(selected_item, 'values')
        self.current_selected_tournament_name = values[0]  # Il nome è la PK

        self._clear_list_form()
        self.entry_tournament_name_list.insert(0, values[0])

    def _on_double_click_tournament(self, event):
        selected_item = self.tournament_tree.focus()
        if not selected_item:
            return
        values = self.tournament_tree.item(selected_item, 'values')
        tournament_name = values[0]
        self._show_tournament_details(tournament_name)

    def _add_tournament_action(self):
        nome_torneo = self.entry_tournament_name_list.get()
        if not nome_torneo:
            messagebox.showerror("Errore", "Il nome del torneo è obbligatorio.")
            return
        # Qui potresti voler aprire un popup per inserire tutti i dettagli del torneo
        # o reindirizzare al widget TournamentCreationWidget.
        messagebox.showinfo("Successo",
                            f"Aggiungi torneo '{nome_torneo}' (simulato). Dovresti usare il 'Crea Torneo' per i dettagli completi.")
        self._load_tournaments_data()
        self._clear_list_form()

    def _edit_tournament_action(self):
        if not self.current_selected_tournament_name:
            messagebox.showerror("Errore", "Seleziona un torneo da modificare.")
            return
        new_name = self.entry_tournament_name_list.get()
        if not new_name:
            messagebox.showerror("Errore", "Il nome del torneo non può essere vuoto.")
            return
        messagebox.showinfo("Successo",
                            f"Modifica torneo '{self.current_selected_tournament_name}' a '{new_name}' (simulato).")
        # In un'app reale, qui aprirai una finestra per modificare tutti i campi del torneo
        self._load_tournaments_data()
        self._clear_list_form()

    def _delete_tournament_action(self):
        if not self.current_selected_tournament_name:
            messagebox.showerror("Errore", "Seleziona un torneo da eliminare.")
            return
        if messagebox.askyesno("Conferma Eliminazione",
                               f"Sei sicuro di voler eliminare il torneo '{self.current_selected_tournament_name}'?"):
            messagebox.showinfo("Successo", f"Torneo '{self.current_selected_tournament_name}' eliminato (simulato).")
            self._load_tournaments_data()
            self._clear_list_form()


# =====================================================================
# Funzione per avviare la demo dell'interfaccia utente
# =====================================================================

def run_tournament_ui_demo():
    root = tk.Tk()
    root.title("🂡 Briscola Tournament Manager Demo")
    root.geometry("1000x700")
    root.resizable(True, True)

    # Title Frame
    frame_title = tk.Frame(root, bg="#2c3e50", height=80)
    frame_title.pack(fill="x")
    title_label = tk.Label(
        frame_title,
        text="Briscola Tournament Manager Demo",
        bg="#2c3e50",
        fg="white",
        font=("Helvetica", 22, "bold")
    )
    title_label.pack(pady=20)

    # Menu Frame
    frame_menu = tk.Frame(root, bg="#34495e", width=200)
    frame_menu.pack(side="left", fill="y")

    # Content Frame (where widgets will be shown)
    frame_content = tk.Frame(root, bg="#ecf0f1")
    frame_content.pack(side="right", expand=True, fill="both")

    # Dictionary to hold the content widgets
    content_widgets = {}
    current_visible_widget = None

    def clear_content():
        nonlocal current_visible_widget
        if current_visible_widget:
            current_visible_widget.pack_forget()

    def show_widget(widget_instance):
        nonlocal current_visible_widget
        clear_content()
        widget_instance.pack(expand=True, fill="both")
        current_visible_widget = widget_instance

    # Home Widget (static, but still a "widget" in concept)
    home_frame = tk.Frame(frame_content, bg="#ecf0f1")
    home_label = tk.Label(
        home_frame,
        text="Benvenuto nel Briscola Tournament Manager!\n\nSeleziona un'opzione dal menu.",
        font=("Helvetica", 16),
        bg="#ecf0f1",
        fg="#2c3e50"
    )
    home_label.pack(expand=True)
    content_widgets["home"] = home_frame

    # Instantiate all dynamic content widgets
    content_widgets["create_tournament"] = TournamentCreationWidget(frame_content)
    content_widgets["list_tournaments"] = TournamentListWidget(frame_content)  # Nuovo widget
    content_widgets["manage_players"] = PlayerManagementWidget(frame_content)
    content_widgets["manage_teams"] = TeamManagementWidget(frame_content)
    content_widgets["manage_matches"] = MatchManagementWidget(frame_content)
    content_widgets["show_ranking"] = RankingWidget(frame_content)

    # Menu Buttons setup
    btn_style = {
        "font": ("Helvetica", 12),
        "bg": "#1abc9c",
        "fg": "white",
        "bd": 0,
        "height": 2,
        "activebackground": "#16a085",  # Colore al click
        "activeforeground": "white",
        "cursor": "hand2"  # Cambia il cursore
    }

    tk.Button(frame_menu, text="🏆 Crea Torneo", command=lambda: show_widget(content_widgets["create_tournament"]),
              **btn_style).pack(fill="x", padx=10, pady=5)
    tk.Button(frame_menu, text="📋 Lista Tornei", command=lambda: show_widget(content_widgets["list_tournaments"]),
              **btn_style).pack(fill="x", padx=10, pady=5)  # Nuovo pulsante
    tk.Button(frame_menu, text="👥 Partecipanti", command=lambda: show_widget(content_widgets["manage_players"]),
              **btn_style).pack(fill="x", padx=10, pady=5)
    tk.Button(frame_menu, text="🤝 Squadre", command=lambda: show_widget(content_widgets["manage_teams"]),
              **btn_style).pack(fill="x", padx=10, pady=5)
    tk.Button(frame_menu, text="🃏 Partite", command=lambda: show_widget(content_widgets["manage_matches"]),
              **btn_style).pack(fill="x", padx=10, pady=5)
    tk.Button(frame_menu, text="📊 Classifica", command=lambda: show_widget(content_widgets["show_ranking"]),
              **btn_style).pack(fill="x", padx=10, pady=5)

    def exit_app():
        if messagebox.askyesno("Conferma", "Vuoi davvero uscire?"):
            root.destroy()

    tk.Button(
        frame_menu,
        text="❌ Esci",
        command=exit_app,
        bg="#e74c3c",
        fg="white",
        bd=0,
        height=2,
        activebackground="#c0392b",
        activeforeground="white",
        cursor="hand2"
    ).pack(fill="x", padx=10, pady=30)

    # Show home screen initially
    show_widget(content_widgets["home"])

    root.mainloop()

