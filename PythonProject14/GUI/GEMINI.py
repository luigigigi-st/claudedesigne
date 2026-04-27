import tkinter as tk
from tkinter import messagebox
import datetime  # Per la gestione di data e ora delle partite

# --- Database Placeholder (simulato con una lista per questo frame) ---
# In un'applicazione reale, qui ci sarebbe l'interazione con un DB relazionale
tournaments_db = []
players_db = []
teams_db = []
matches_db = []
results_db = []
current_tournament_id = None  # ID del torneo attualmente selezionato


def db_create_tournament(name, mode):
    global current_tournament_id
    tournament_id = len(tournaments_db) + 1
    tournaments_db.append({"id": tournament_id, "name": name, "mode": mode, "status": "Active"})
    current_tournament_id = tournament_id
    print(f"🎉 Database: Torneo '{name}' ({mode}) creato con ID {tournament_id}!")
    return tournament_id


def db_register_player(cf, name):
    if any(p['cf'] == cf for p in players_db):
        print(f"⚠️ Database: Giocatore con CF '{cf}' già esistente!")
        return None
    player_id = len(players_db) + 1
    players_db.append({"id": player_id, "cf": cf, "name": name})
    print(f"👤 Database: Giocatore '{name}' (CF: {cf}) registrato con ID {player_id}!")
    return player_id


def db_register_team(name, player_ids):
    if any(t['name'] == name for t in teams_db):
        print(f"⚠️ Database: Squadra con nome '{name}' già esistente!")
        return None
    team_id = len(teams_db) + 1
    teams_db.append({"id": team_id, "name": name, "players": player_ids})
    print(f"🤝 Database: Squadra '{name}' (giocatori: {player_ids}) registrata con ID {team_id}!")
    return team_id


def db_schedule_match(tournament_id, location, date_str, time_str, participants, mode):
    match_id = len(matches_db) + 1
    matches_db.append({
        "id": match_id,
        "tournament_id": tournament_id,
        "location": location,
        "date": date_str,
        "time": time_str,
        "participants": participants,  # E.g., [player1_id, player2_id] or [team1_id, team2_id]
        "mode": mode,
        "status": "Scheduled"
    })
    print(
        f"🗓️ Database: Partita {match_id} programmata per il torneo {tournament_id} a '{location}' il {date_str} alle {time_str}!")
    return match_id


def db_record_result(match_id, winner_id, loser_id=None, is_draw=False):
    # Logica semplificata per i punti
    points_per_match = 100
    winner_points = points_per_match
    loser_points = 0
    draw_points = points_per_match / 2

    if is_draw:
        results_db.append({"match_id": match_id, "participant_id": winner_id,
                           "points": draw_points})  # winner_id qui sarebbe il primo partecipante
        results_db.append({"match_id": match_id, "participant_id": loser_id,
                           "points": draw_points})  # loser_id qui sarebbe il secondo partecipante
        print(f"↔️ Database: Risultato partita {match_id}: Pareggio! Entrambi ottengono {draw_points} punti.")
    else:
        results_db.append({"match_id": match_id, "participant_id": winner_id, "points": winner_points})
        if loser_id:
            results_db.append({"match_id": match_id, "participant_id": loser_id, "points": loser_points})
        print(
            f"🏆 Database: Risultato partita {match_id}: Vincitore {winner_id} (+{winner_points} punti), Sconfitto {loser_id} (+{loser_points} punti).")

    # Aggiorna lo stato della partita
    for match in matches_db:
        if match['id'] == match_id:
            match['status'] = "Completed"
            break


def db_get_rankings(tournament_id):
    # Calcolo classifica simulato
    rankings = {}
    for result in results_db:
        # Assicurati che il match appartenga al torneo corretto
        match = next((m for m in matches_db if m['id'] == result['match_id']), None)
        if match and match['tournament_id'] == tournament_id:
            participant_id = result['participant_id']
            rankings[participant_id] = rankings.get(participant_id, 0) + result['points']

    # Ordina per punteggio decrescente
    sorted_rankings = sorted(rankings.items(), key=lambda item: item[1], reverse=True)

    # Converti ID in nomi per la visualizzazione
    display_rankings = []
    for participant_id, score in sorted_rankings:
        name = "Sconosciuto"
        player = next((p for p in players_db if p['id'] == participant_id), None)
        if player:
            name = player['name']
        else:
            team = next((t for t in teams_db if t['id'] == participant_id), None)
            if team:
                name = team['name']
        display_rankings.append((name, score))

    print(f"📊 Database: Classifica del Torneo ID {tournament_id}: {display_rankings}")
    return display_rankings


def db_modify_data(data_type, item_id, new_data):
    print(f"✏️ Database: Modifica {data_type} con ID {item_id}, nuovi dati: {new_data}")


def db_delete_data(data_type, item_id, password):
    if password == "FALCONERO":  # Password semplice per dimostrazione
        print(f"🗑️ Database: Eliminazione {data_type} con ID {item_id}. Password corretta.")
    else:
        print(f"❌ Database: Errore eliminazione. Password errata per {data_type} con ID {item_id}.")


# --- Main Application Class ---
class BriscolaTournamentApp:
    def __init__(self, master):
        self.master = master
        master.title("🎮 Briscola Tournament Manager: Edizione FALCONERO! 🦅")
        master.geometry("800x600")
        master.config(bg="#E0FFFF")  # Un bel colore azzurrino chiaro

        self.frames = {}
        self._setup_frames()
        self._create_navigation_menu()
        self.show_frame("Welcome")

    def _setup_frames(self):
        # Frame di Benvenuto
        self.frames["Welcome"] = WelcomeFrame(self.master, self)
        self.frames["Welcome"].grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame Gestione Tornei
        self.frames["TournamentManager"] = TournamentManagerFrame(self.master, self)
        self.frames["TournamentManager"].grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame Gestione Partecipanti
        self.frames["ParticipantManager"] = ParticipantManagerFrame(self.master, self)
        self.frames["ParticipantManager"].grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame Gestione Partite
        self.frames["MatchManager"] = MatchManagerFrame(self.master, self)
        self.frames["MatchManager"].grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame Classifica
        self.frames["RankingDisplay"] = RankingDisplayFrame(self.master, self)
        self.frames["RankingDisplay"].grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame Modifica/Elimina Dati
        self.frames["DataEditor"] = DataEditorFrame(self.master, self)
        self.frames["DataEditor"].grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

    def _create_navigation_menu(self):
        # Un menu carino in alto
        menu_bar = tk.Menu(self.master, bg="#ADD8E6", fg="black")  # Azzurro chiaro per il menu
        self.master.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0, bg="#F0F8FF")
        menu_bar.add_cascade(label="🏠 Home", menu=file_menu)
        file_menu.add_command(label="Benvenuto!", command=lambda: self.show_frame("Welcome"))
        file_menu.add_separator()
        file_menu.add_command(label="Esci 🏃‍♂️", command=self.master.quit)

        tournament_menu = tk.Menu(menu_bar, tearoff=0, bg="#F0F8FF")
        menu_bar.add_cascade(label="🏆 Tornei", menu=tournament_menu)
        tournament_menu.add_command(label="Gestisci Tornei ✨", command=lambda: self.show_frame("TournamentManager"))
        tournament_menu.add_command(label="Registra Partecipanti 🧑‍🤝‍🧑",
                                    command=lambda: self.show_frame("ParticipantManager"))

        match_menu = tk.Menu(menu_bar, tearoff=0, bg="#F0F8FF")
        menu_bar.add_cascade(label="🃏 Partite", menu=match_menu)
        match_menu.add_command(label="Programma Partite 🗓️", command=lambda: self.show_frame("MatchManager"))
        match_menu.add_command(label="Registra Risultati ✅",
                               command=lambda: self.show_frame("MatchManager"))  # Stesso frame per ora

        data_menu = tk.Menu(menu_bar, tearoff=0, bg="#F0F8FF")
        menu_bar.add_cascade(label="🗄️ Dati & Classifiche", menu=data_menu)
        data_menu.add_command(label="Visualizza Classifica 🥇", command=lambda: self.show_frame("RankingDisplay"))
        data_menu.add_command(label="Modifica/Cancella Dati ✏️🗑️", command=lambda: self.show_frame("DataEditor"))

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def get_current_tournament_id(self):
        return current_tournament_id

    def get_current_tournament_mode(self):
        if current_tournament_id:
            tournament = next((t for t in tournaments_db if t['id'] == current_tournament_id), None)
            if tournament:
                return tournament['mode']
        return None


# --- Welcome Frame ---
class WelcomeFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#FFFACD")  # Giallo chiaro accogliente
        self.controller = controller

        label = tk.Label(self, text="🌟 Benvenuto nel Briscola Tournament Manager! 🌟",
                         font=("Arial", 24, "bold"), bg="#FFFACD", fg="#FF4500")  # Arancione brillante
        label.pack(pady=50)

        description = tk.Label(self,
                               text="Organizza i tuoi tornei di Briscola con facilità! \n Che l'avventura abbia inizio! 🚀",
                               font=("Arial", 14), bg="#FFFACD", fg="#4682B4")  # Blu acciaio
        description.pack(pady=20)

        start_button = tk.Button(self, text="Inizia a gestire i Tornei! 🏆",
                                 font=("Arial", 16, "bold"), bg="#90EE90", fg="black",  # Verde chiaro
                                 command=lambda: controller.show_frame("TournamentManager"),
                                 relief="raised", borderwidth=3)
        start_button.pack(pady=30)

        info_label = tk.Label(self, text="Progetto FALCONERO 🦅",
                              font=("Arial", 10, "italic"), bg="#FFFACD", fg="grey")
        info_label.pack(side="bottom", pady=10)


# --- Tournament Manager Frame ---
class TournamentManagerFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#F0F8FF")  # AliceBlue
        self.controller = controller

        tk.Label(self, text="🏆 Gestione Tornei ✨", font=("Arial", 20, "bold"), bg="#F0F8FF", fg="#4169E1").pack(pady=20)

        # Creazione Nuovo Torneo
        tk.Label(self, text="Crea un nuovo Torneo:", font=("Arial", 14, "bold"), bg="#F0F8FF").pack(pady=10)
        self.tournament_name_label = tk.Label(self, text="Nome Torneo:", bg="#F0F8FF")
        self.tournament_name_label.pack()
        self.tournament_name_entry = tk.Entry(self, width=40)
        self.tournament_name_entry.pack(pady=5)

        tk.Label(self, text="Modalità di Gioco:", bg="#F0F8FF").pack()
        self.mode_var = tk.StringVar(self)
        self.mode_var.set("singolo")  # default value
        self.mode_options = ["singolo", "coppie"]
        self.mode_menu = tk.OptionMenu(self, self.mode_var, *self.mode_options)
        self.mode_menu.config(bg="#B0E0E6")  # PowderBlue
        self.mode_menu.pack(pady=5)

        create_button = tk.Button(self, text="Crea Torneo! 🎉", command=self.create_tournament, bg="#87CEFA", fg="white",
                                  font=("Arial", 12))  # LightSkyBlue
        create_button.pack(pady=10)

        tk.Label(self, text="---", bg="#F0F8FF").pack(pady=10)

        # Selezione Torneo Esistente
        tk.Label(self, text="Seleziona un Torneo Esistente:", font=("Arial", 14, "bold"), bg="#F0F8FF").pack(pady=10)

        self.selected_tournament_var = tk.StringVar(self)
        self.selected_tournament_var.set("Nessun Torneo Selezionato")  # Default
        self.tournament_options_menu = tk.OptionMenu(self, self.selected_tournament_var, "Nessun Torneo Selezionato")
        self.tournament_options_menu.config(bg="#B0C4DE")  # LightSteelBlue
        self.tournament_options_menu.pack(pady=5)
        self.update_tournament_list_menu()  # Aggiorna la lista all'avvio

        select_button = tk.Button(self, text="Seleziona Torneo ✅", command=self.select_tournament, bg="#6495ED",
                                  fg="white", font=("Arial", 12))  # CornflowerBlue
        select_button.pack(pady=10)

        self.current_selection_label = tk.Label(self, text=f"Torneo Attivo: Nessuno", font=("Arial", 12), bg="#F0F8FF",
                                                fg="green")
        self.current_selection_label.pack(pady=10)

        # Bind per aggiornare il menu ogni volta che il frame viene mostrato
        self.bind("<Visibility>", self.on_frame_visible)

    def on_frame_visible(self, event):
        self.update_tournament_list_menu()
        self.update_current_selection_label()

    def update_tournament_list_menu(self):
        menu = self.tournament_options_menu["menu"]
        menu.delete(0, "end")
        if not tournaments_db:
            menu.add_command(label="Nessun Torneo Disponibile",
                             command=tk._setit(self.selected_tournament_var, "Nessun Torneo Disponibile"))
            self.selected_tournament_var.set("Nessun Torneo Disponibile")
        else:
            for t in tournaments_db:
                menu.add_command(label=f"{t['name']} ({t['mode']})",
                                 command=tk._setit(self.selected_tournament_var, f"{t['name']} (ID: {t['id']})"))

            # Se un torneo è già selezionato, assicurati che sia quello visualizzato
            if current_tournament_id:
                current_t = next((t for t in tournaments_db if t['id'] == current_tournament_id), None)
                if current_t:
                    self.selected_tournament_var.set(f"{current_t['name']} (ID: {current_t['id']})")
                else:
                    self.selected_tournament_var.set("Nessun Torneo Selezionato")

    def create_tournament(self):
        name = self.tournament_name_entry.get().strip()
        mode = self.mode_var.get()
        if name:
            tournament_id = db_create_tournament(name, mode)
            messagebox.showinfo("Successo! 🎉", f"Torneo '{name}' ({mode}) creato! ID: {tournament_id}")
            self.tournament_name_entry.delete(0, tk.END)
            self.update_tournament_list_menu()
            self.update_current_selection_label()
        else:
            messagebox.showerror("Errore! ❌", "Per favore, inserisci un nome per il torneo!")

    def select_tournament(self):
        selected_text = self.selected_tournament_var.get()
        if "Nessun Torneo" in selected_text:
            messagebox.showwarning("Attenzione! ⚠️", "Per favore, seleziona un torneo valido dalla lista.")
            return

        try:
            # Estrai l'ID del torneo dalla stringa "(ID: X)"
            tournament_id_str = selected_text.split("(ID: ")[1].replace(")", "")
            global current_tournament_id
            current_tournament_id = int(tournament_id_str)

            tournament = next((t for t in tournaments_db if t['id'] == current_tournament_id), None)
            if tournament:
                messagebox.showinfo("Torneo Selezionato! ✅",
                                    f"Hai selezionato il torneo '{tournament['name']}' (ID: {current_tournament_id}).")
                self.update_current_selection_label()
            else:
                messagebox.showerror("Errore! ❌", "Torneo non trovato.")

        except (IndexError, ValueError):
            messagebox.showerror("Errore! ❌", "Impossibile recuperare l'ID del torneo selezionato. Formato non valido.")
            current_tournament_id = None
            self.update_current_selection_label()

    def update_current_selection_label(self):
        if current_tournament_id:
            tournament = next((t for t in tournaments_db if t['id'] == current_tournament_id), None)
            if tournament:
                self.current_selection_label.config(
                    text=f"Torneo Attivo: {tournament['name']} (ID: {current_tournament_id}, Modalità: {tournament['mode']})")
            else:
                self.current_selection_label.config(text=f"Torneo Attivo: ID {current_tournament_id} (non trovato)")
        else:
            self.current_selection_label.config(text=f"Torneo Attivo: Nessuno")


# --- Participant Manager Frame ---
class ParticipantManagerFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#FAFAD2")  # LightGoldenrodYellow
        self.controller = controller

        tk.Label(self, text="🧑‍🤝‍🧑 Gestione Partecipanti & Squadre 🤝", font=("Arial", 20, "bold"), bg="#FAFAD2",
                 fg="#DAA520").pack(pady=20)

        # Registra Giocatore
        tk.Label(self, text="Registra un nuovo Giocatore:", font=("Arial", 14, "bold"), bg="#FAFAD2").pack(pady=10)
        tk.Label(self, text="Nome Completo:", bg="#FAFAD2").pack()
        self.player_name_entry = tk.Entry(self, width=40)
        self.player_name_entry.pack(pady=2)
        tk.Label(self, text="Codice Fiscale (CF):", bg="#FAFAD2").pack()
        self.player_cf_entry = tk.Entry(self, width=40)
        self.player_cf_entry.pack(pady=2)
        player_button = tk.Button(self, text="Registra Giocatore 👤", command=self.register_player, bg="#ADFF2F",
                                  fg="black", font=("Arial", 12))  # GreenYellow
        player_button.pack(pady=10)

        tk.Label(self, text="---", bg="#FAFAD2").pack(pady=10)

        # Registra Squadra
        tk.Label(self, text="Registra una nuova Squadra (per modalità 'coppie'):", font=("Arial", 14, "bold"),
                 bg="#FAFAD2").pack(pady=10)
        tk.Label(self, text="Nome Squadra:", bg="#FAFAD2").pack()
        self.team_name_entry = tk.Entry(self, width=40)
        self.team_name_entry.pack(pady=2)
        tk.Label(self, text="CF Giocatore 1:", bg="#FAFAD2").pack()
        self.team_player1_cf_entry = tk.Entry(self, width=40)
        self.team_player1_cf_entry.pack(pady=2)
        tk.Label(self, text="CF Giocatore 2:", bg="#FAFAD2").pack()
        self.team_player2_cf_entry = tk.Entry(self, width=40)
        self.team_player2_cf_entry.pack(pady=2)
        team_button = tk.Button(self, text="Registra Squadra 🤝", command=self.register_team, bg="#FFD700", fg="black",
                                font=("Arial", 12))  # Gold
        team_button.pack(pady=10)

    def register_player(self):
        name = self.player_name_entry.get().strip()
        cf = self.player_cf_entry.get().strip().upper()  # CF in maiuscolo per coerenza

        if not name or not cf:
            messagebox.showerror("Errore! ❌", "Nome e CF sono obbligatori per registrare un giocatore.")
            return

        if len(cf) != 16:  # Controllo basilare per la lunghezza del CF
            messagebox.showerror("Errore! ❌", "Il Codice Fiscale deve essere di 16 caratteri.")
            return

        player_id = db_register_player(cf, name)
        if player_id:
            messagebox.showinfo("Successo! 🎉", f"Giocatore '{name}' registrato con ID: {player_id}.")
            self.player_name_entry.delete(0, tk.END)
            self.player_cf_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Attenzione! ⚠️", f"Il giocatore con CF '{cf}' potrebbe essere già registrato.")

    def register_team(self):
        if self.controller.get_current_tournament_mode() != "coppie":
            messagebox.showwarning("Attenzione! ⚠️",
                                   "Le squadre possono essere registrate solo per tornei in modalità 'coppie'.")
            return

        team_name = self.team_name_entry.get().strip()
        cf1 = self.team_player1_cf_entry.get().strip().upper()
        cf2 = self.team_player2_cf_entry.get().strip().upper()

        if not team_name or not cf1 or not cf2:
            messagebox.showerror("Errore! ❌", "Nome squadra e CF dei due giocatori sono obbligatori.")
            return
        if cf1 == cf2:
            messagebox.showerror("Errore! ❌", "Un giocatore non può far parte di una squadra con se stesso!")
            return

        # Recupera gli ID dei giocatori dai CF
        player1 = next((p for p in players_db if p['cf'] == cf1), None)
        player2 = next((p for p in players_db if p['cf'] == cf2), None)

        if not player1:
            messagebox.showerror("Errore! ❌", f"Giocatore con CF '{cf1}' non trovato. Registralo prima!")
            return
        if not player2:
            messagebox.showerror("Errore! ❌", f"Giocatore con CF '{cf2}' non trovato. Registralo prima!")
            return

        team_id = db_register_team(team_name, [player1['id'], player2['id']])
        if team_id:
            messagebox.showinfo("Successo! 🎉", f"Squadra '{team_name}' registrata con ID: {team_id}.")
            self.team_name_entry.delete(0, tk.END)
            self.team_player1_cf_entry.delete(0, tk.END)
            self.team_player2_cf_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Attenzione! ⚠️", f"La squadra '{team_name}' potrebbe essere già registrata.")


# --- Match Manager Frame ---
class MatchManagerFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#E6E6FA")  # Lavender
        self.controller = controller

        tk.Label(self, text="🃏 Programmazione & Risultati Partite ✅", font=("Arial", 20, "bold"), bg="#E6E6FA",
                 fg="#8A2BE2").pack(pady=20)

        # Programma Partita
        tk.Label(self, text="Programma una nuova Partita:", font=("Arial", 14, "bold"), bg="#E6E6FA").pack(pady=10)
        tk.Label(self, text="Luogo:", bg="#E6E6FA").pack()
        self.location_entry = tk.Entry(self, width=40)
        self.location_entry.pack(pady=2)
        tk.Label(self, text="Data (AAAA-MM-GG):", bg="#E6E6FA").pack()
        self.date_entry = tk.Entry(self, width=40)
        self.date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))  # Data odierna di default
        self.date_entry.pack(pady=2)
        tk.Label(self, text="Ora (HH:MM):", bg="#E6E6FA").pack()
        self.time_entry = tk.Entry(self, width=40)
        self.time_entry.insert(0, datetime.datetime.now().strftime("%H:%M"))  # Ora attuale di default
        self.time_entry.pack(pady=2)

        tk.Label(self, text="Partecipante 1 (CF/Nome Squadra):", bg="#E6E6FA").pack()
        self.p1_entry = tk.Entry(self, width=40)
        self.p1_entry.pack(pady=2)
        tk.Label(self, text="Partecipante 2 (CF/Nome Squadra):", bg="#E6E6FA").pack()
        self.p2_entry = tk.Entry(self, width=40)
        self.p2_entry.pack(pady=2)

        schedule_button = tk.Button(self, text="Programma Partita 🗓️", command=self.schedule_match, bg="#BA55D3",
                                    fg="white", font=("Arial", 12))  # MediumPurple
        schedule_button.pack(pady=10)

        tk.Label(self, text="---", bg="#E6E6FA").pack(pady=10)

        # Registra Risultato
        tk.Label(self, text="Registra il Risultato di una Partita:", font=("Arial", 14, "bold"), bg="#E6E6FA").pack(
            pady=10)

        tk.Label(self, text="ID Partita:", bg="#E6E6FA").pack()
        self.match_id_entry = tk.Entry(self, width=20)
        self.match_id_entry.pack(pady=2)

        tk.Label(self, text="Vincitore (CF/Nome Squadra):", bg="#E6E6FA").pack()
        self.winner_entry = tk.Entry(self, width=40)
        self.winner_entry.pack(pady=2)
        tk.Label(self, text="Perdente (CF/Nome Squadra) / Lascia vuoto per pareggio:", bg="#E6E6FA").pack()
        self.loser_entry = tk.Entry(self, width=40)
        self.loser_entry.pack(pady=2)

        record_button = tk.Button(self, text="Registra Risultato ✅", command=self.record_match_result, bg="#9370DB",
                                  fg="white", font=("Arial", 12))  # MediumPurple
        record_button.pack(pady=10)

    def _get_participant_id(self, identifier, mode):
        # Cerca per CF se modalità singolo, per nome squadra se modalità coppie
        if mode == "singolo":
            player = next((p for p in players_db if p['cf'] == identifier.upper()), None)
            return player['id'] if player else None
        elif mode == "coppie":
            team = next((t for t in teams_db if t['name'].lower() == identifier.lower()), None)
            return team['id'] if team else None
        return None

    def schedule_match(self):
        tournament_id = self.controller.get_current_tournament_id()
        if not tournament_id:
            messagebox.showwarning("Attenzione! ⚠️",
                                   "Per favore, seleziona prima un torneo nella sezione 'Gestione Tornei'.")
            return

        location = self.location_entry.get().strip()
        date_str = self.date_entry.get().strip()
        time_str = self.time_entry.get().strip()
        p1_id_str = self.p1_entry.get().strip()
        p2_id_str = self.p2_entry.get().strip()
        tournament_mode = self.controller.get_current_tournament_mode()

        if not all([location, date_str, time_str, p1_id_str, p2_id_str]):
            messagebox.showerror("Errore! ❌", "Tutti i campi sono obbligatori per programmare una partita.")
            return

        if p1_id_str.lower() == p2_id_str.lower():
            messagebox.showerror("Errore! ❌", "Un partecipante non può sfidare se stesso!")
            return

        try:
            # Controllo formato data e ora
            match_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            datetime.datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            messagebox.showerror("Errore! ❌", "Formato data (AAAA-MM-GG) o ora (HH:MM) non valido.")
            return

        today = datetime.date.today()
        if match_date < today:
            messagebox.showwarning("Attenzione! ⚠️",
                                   "Stai programmando una partita in data passata. Assicurati di inserire subito il risultato.")

        participant1_id = self._get_participant_id(p1_id_str, tournament_mode)
        participant2_id = self._get_participant_id(p2_id_str, tournament_mode)

        if not participant1_id or not participant2_id:
            messagebox.showerror("Errore! ❌",
                                 "Uno o entrambi i partecipanti non sono stati trovati. Assicurati di averli registrati correttamente (CF per giocatori, Nome per squadre).")
            return

        match_id = db_schedule_match(tournament_id, location, date_str, time_str, [participant1_id, participant2_id],
                                     tournament_mode)
        messagebox.showinfo("Successo! 🎉", f"Partita ID {match_id} programmata!")
        self.location_entry.delete(0, tk.END)
        self.p1_entry.delete(0, tk.END)
        self.p2_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, datetime.datetime.now().strftime("%H:%M"))

    def record_match_result(self):
        match_id_str = self.match_id_entry.get().strip()
        winner_identifier = self.winner_entry.get().strip()
        loser_identifier = self.loser_entry.get().strip()

        if not match_id_str or not winner_identifier:
            messagebox.showerror("Errore! ❌", "ID Partita e Vincitore sono obbligatori per registrare un risultato.")
            return

        try:
            match_id = int(match_id_str)
        except ValueError:
            messagebox.showerror("Errore! ❌", "ID Partita deve essere un numero intero.")
            return

        match = next((m for m in matches_db if m['id'] == match_id), None)
        if not match:
            messagebox.showerror("Errore! ❌", "Partita non trovata con l'ID specificato.")
            return

        if match['status'] == "Completed":
            messagebox.showwarning("Attenzione! ⚠️",
                                   f"La partita ID {match_id} è già stata completata. Non puoi registrarne nuovamente il risultato.")
            return

        tournament_mode = match['mode']  # Prendi la modalità dalla partita stessa

        winner_id = self._get_participant_id(winner_identifier, tournament_mode)
        loser_id = None
        is_draw = False

        if not winner_id:
            messagebox.showerror("Errore! ❌",
                                 f"Vincitore '{winner_identifier}' non trovato tra i partecipanti del torneo in modalità '{tournament_mode}'.")
            return

        if loser_identifier:
            loser_id = self._get_participant_id(loser_identifier, tournament_mode)
            if not loser_id:
                messagebox.showerror("Errore! ❌",
                                     f"Perdente '{loser_identifier}' non trovato tra i partecipanti del torneo in modalità '{tournament_mode}'.")
                return
            if winner_id == loser_id:
                messagebox.showerror("Errore! ❌", "Vincitore e Perdente non possono essere lo stesso partecipante!")
                return
        else:
            # Se il perdente non è specificato, è un pareggio. Serve l'altro partecipante.
            other_participant_id = next((p for p in match['participants'] if p != winner_id), None)
            if other_participant_id:
                loser_id = other_participant_id  # In caso di pareggio, lo usiamo come "secondo" partecipante
                is_draw = True
            else:
                messagebox.showerror("Errore! ❌",
                                     "Partita singola o con un solo partecipante? Impossibile registrare il risultato.")
                return

        db_record_result(match_id, winner_id, loser_id, is_draw)
        messagebox.showinfo("Successo! 🎉", f"Risultato registrato per la Partita ID {match_id}!")
        self.match_id_entry.delete(0, tk.END)
        self.winner_entry.delete(0, tk.END)
        self.loser_entry.delete(0, tk.END)


# --- Ranking Display Frame ---
class RankingDisplayFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#FFE4E1")  # MistyRose
        self.controller = controller

        tk.Label(self, text="🥇 Classifica del Torneo 📊", font=("Arial", 20, "bold"), bg="#FFE4E1", fg="#FF6347").pack(
            pady=20)

        self.ranking_label = tk.Label(self, text="Seleziona un torneo per visualizzare la classifica.",
                                      font=("Arial", 14), bg="#FFE4E1", fg="#CD5C5C")
        self.ranking_label.pack(pady=20)

        show_ranking_button = tk.Button(self, text="Mostra Classifica 🏆", command=self.display_rankings, bg="#FA8072",
                                        fg="white", font=("Arial", 12))  # Salmon
        show_ranking_button.pack(pady=10)

        self.rank_text = tk.Text(self, height=15, width=60, font=("Courier", 12), bg="#FFF0F5",
                                 fg="black")  # LavenderBlush
        self.rank_text.pack(pady=10)
        self.rank_text.config(state=tk.DISABLED)  # Rendi il testo non modificabile

        # Bind per aggiornare la classifica ogni volta che il frame viene mostrato
        self.bind("<Visibility>", self.on_frame_visible)

    def on_frame_visible(self, event):
        self.display_rankings()

    def display_rankings(self):
        tournament_id = self.controller.get_current_tournament_id()
        if not tournament_id:
            self.ranking_label.config(text="Seleziona un torneo per visualizzare la classifica.")
            self.rank_text.config(state=tk.NORMAL)
            self.rank_text.delete(1.0, tk.END)
            self.rank_text.insert(tk.END, "Nessun torneo selezionato. 😟")
            self.rank_text.config(state=tk.DISABLED)
            return

        tournament_name = "Sconosciuto"
        current_tournament = next((t for t in tournaments_db if t['id'] == tournament_id), None)
        if current_tournament:
            tournament_name = current_tournament['name']

        self.ranking_label.config(text=f"Classifica per il torneo '{tournament_name}':")
        rankings = db_get_rankings(tournament_id)

        self.rank_text.config(state=tk.NORMAL)
        self.rank_text.delete(1.0, tk.END)

        if not rankings:
            self.rank_text.insert(tk.END, "Ancora nessun risultato registrato per questo torneo. 😔")
        else:
            self.rank_text.insert(tk.END, f"Classifica del Torneo '{tournament_name}'\n")
            self.rank_text.insert(tk.END, "-----------------------------------\n")
            for i, (name, score) in enumerate(rankings):
                self.rank_text.insert(tk.END, f"{i + 1}. {name}: {int(score)} punti\n")
            self.rank_text.insert(tk.END, "-----------------------------------\n")

        self.rank_text.config(state=tk.DISABLED)


# --- Data Editor Frame (Modify/Delete) ---
class DataEditorFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#F0FFF0")  # Honeydew
        self.controller = controller

        tk.Label(self, text="✏️🗑️ Modifica o Cancella Dati 🛠️", font=("Arial", 20, "bold"), bg="#F0FFF0",
                 fg="#228B22").pack(pady=20)

        # Modifica Dati (Semplificato)
        tk.Label(self, text="Modifica un dato esistente:", font=("Arial", 14, "bold"), bg="#F0FFF0").pack(pady=10)
        tk.Label(self, text="Tipo di Dato (Player/Team/Match/Tournament):", bg="#F0FFF0").pack()
        self.modify_type_entry = tk.Entry(self, width=40)
        self.modify_type_entry.pack(pady=2)
        tk.Label(self, text="ID dell'elemento:", bg="#F0FFF0").pack()
        self.modify_id_entry = tk.Entry(self, width=40)
        self.modify_id_entry.pack(pady=2)
        tk.Label(self, text="Nuovi Dati (es. 'name=NuovoNome'):", bg="#F0FFF0").pack()
        self.modify_data_entry = tk.Entry(self, width=40)
        self.modify_data_entry.pack(pady=2)
        modify_button = tk.Button(self, text="Modifica Dati ✏️", command=self.modify_data, bg="#8FBC8F", fg="white",
                                  font=("Arial", 12))  # DarkSeaGreen
        modify_button.pack(pady=10)

        tk.Label(self, text="---", bg="#F0FFF0").pack(pady=10)

        # Cancella Dati
        tk.Label(self, text="Cancella un dato esistente:", font=("Arial", 14, "bold"), bg="#F0FFF0").pack(pady=10)
        tk.Label(self, text="Tipo di Dato (Player/Team/Match/Tournament):", bg="#F0FFF0").pack()
        self.delete_type_entry = tk.Entry(self, width=40)
        self.delete_type_entry.pack(pady=2)
        tk.Label(self, text="ID dell'elemento:", bg="#F0FFF0").pack()
        self.delete_id_entry = tk.Entry(self, width=40)
        self.delete_id_entry.pack(pady=2)
        tk.Label(self, text="Password Amministratore:", bg="#F0FFF0").pack()
        self.delete_password_entry = tk.Entry(self, width=40, show="*")  # Mostra * per la password
        self.delete_password_entry.pack(pady=2)
        delete_button = tk.Button(self, text="Cancella Dati 🗑️", command=self.delete_data, bg="#FF6347", fg="white",
                                  font=("Arial", 12))  # Tomato
        delete_button.pack(pady=10)

    def modify_data(self):
        data_type = self.modify_type_entry.get().strip().capitalize()
        item_id_str = self.modify_id_entry.get().strip()
        new_data_str = self.modify_data_entry.get().strip()

        if not all([data_type, item_id_str, new_data_str]):
            messagebox.showerror("Errore! ❌", "Tutti i campi sono obbligatori per modificare un dato.")
            return

        try:
            item_id = int(item_id_str)
        except ValueError:
            messagebox.showerror("Errore! ❌", "L'ID dell'elemento deve essere un numero.")
            return

        # Parsing semplificato di new_data_str
        new_data = {}
        try:
            key, value = new_data_str.split('=', 1)
            new_data[key.strip()] = value.strip()
        except ValueError:
            messagebox.showerror("Errore! ❌", "Formato 'Nuovi Dati' non valido. Usa 'chiave=valore'.")
            return

        db_modify_data(data_type, item_id, new_data)  # Chiamata al placeholder del DB
        messagebox.showinfo("Successo! 🎉", f"Richiesta di modifica per '{data_type}' ID {item_id} inviata.")
        self.modify_type_entry.delete(0, tk.END)
        self.modify_id_entry.delete(0, tk.END)
        self.modify_data_entry.delete(0, tk.END)

    def delete_data(self):
        data_type = self.delete_type_entry.get().strip().capitalize()
        item_id_str = self.delete_id_entry.get().strip()
        password = self.delete_password_entry.get()

        if not all([data_type, item_id_str, password]):
            messagebox.showerror("Errore! ❌", "Tutti i campi sono obbligatori per cancellare un dato.")
            return

        try:
            item_id = int(item_id_str)
        except ValueError:
            messagebox.showerror("Errore! ❌", "L'ID dell'elemento deve essere un numero.")
            return

        if password != "FALCONERO":  # Controlla la password
            messagebox.showerror("Errore! ❌", "Password amministratore errata!")
            return

        # Conferma di sicurezza
        if messagebox.askyesno("Conferma Cancellazione ⚠️",
                               f"Sei sicuro di voler cancellare {data_type} con ID {item_id}? Questa azione è irreversibile!"):
            db_delete_data(data_type, item_id, password)  # Chiamata al placeholder del DB
            messagebox.showinfo("Successo! 🎉", f"Richiesta di cancellazione per '{data_type}' ID {item_id} inviata.")
            self.delete_type_entry.delete(0, tk.END)
            self.delete_id_entry.delete(0, tk.END)
            self.delete_password_entry.delete(0, tk.END)
        else:
            messagebox.showinfo("Annullato", "Cancellazione annullata. 😉")

def frame_gemini():
    root = tk.Tk()
    app = BriscolaTournamentApp(root)
    root.mainloop()