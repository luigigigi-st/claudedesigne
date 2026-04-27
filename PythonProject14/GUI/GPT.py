import tkinter as tk
from tkinter import messagebox


class BriscolaTournamentManager(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("🂡 Briscola Tournament Manager")
        self.geometry("800x500")
        self.resizable(False, False)

        self.create_widgets()

    # -------------------------
    # CREAZIONE FRAME
    # -------------------------
    def create_widgets(self):
        # Titolo
        self.frame_title = tk.Frame(self, bg="#2c3e50", height=80)
        self.frame_title.pack(fill="x")

        title_label = tk.Label(
            self.frame_title,
            text="Briscola Tournament Manager",
            bg="#2c3e50",
            fg="white",
            font=("Helvetica", 22, "bold")
        )
        title_label.pack(pady=20)

        # Menu laterale
        self.frame_menu = tk.Frame(self, bg="#34495e", width=200)
        self.frame_menu.pack(side="left", fill="y")

        # Contenuto
        self.frame_content = tk.Frame(self, bg="#ecf0f1")
        self.frame_content.pack(side="right", expand=True, fill="both")

        self.create_menu_buttons()
        self.show_home()

    # -------------------------
    # PULSANTI MENU
    # -------------------------
    def create_menu_buttons(self):
        btn_style = {
            "font": ("Helvetica", 12),
            "bg": "#1abc9c",
            "fg": "white",
            "bd": 0,
            "height": 2
        }

        tk.Button(
            self.frame_menu,
            text="🏆 Crea Torneo",
            command=self.event_create_tournament,
            **btn_style
        ).pack(fill="x", padx=10, pady=5)

        tk.Button(
            self.frame_menu,
            text="👥 Partecipanti",
            command=self.event_manage_players,
            **btn_style
        ).pack(fill="x", padx=10, pady=5)

        tk.Button(
            self.frame_menu,
            text="🃏 Partite",
            command=self.event_manage_matches,
            **btn_style
        ).pack(fill="x", padx=10, pady=5)

        tk.Button(
            self.frame_menu,
            text="📊 Classifica",
            command=self.event_show_ranking,
            **btn_style
        ).pack(fill="x", padx=10, pady=5)

        tk.Button(
            self.frame_menu,
            text="❌ Esci",
            command=self.event_exit,
            bg="#e74c3c",
            fg="white",
            bd=0,
            height=2
        ).pack(fill="x", padx=10, pady=30)

    # -------------------------
    # SCHERMATE
    # -------------------------
    def clear_content(self):
        for widget in self.frame_content.winfo_children():
            widget.destroy()

    def show_home(self):
        self.clear_content()
        label = tk.Label(
            self.frame_content,
            text="Benvenuto nel Briscola Tournament Manager!\n\nSeleziona un'opzione dal menu.",
            font=("Helvetica", 16),
            bg="#ecf0f1"
        )
        label.pack(expand=True)

    # -------------------------
    # EVENTI (PLACEHOLDER)
    # -------------------------
    def event_create_tournament(self):
        print("Evento: Crea Torneo")
        self.clear_content()
        tk.Label(
            self.frame_content,
            text="Creazione Torneo (work in progress)",
            font=("Helvetica", 16),
            bg="#ecf0f1"
        ).pack(pady=50)

    def event_manage_players(self):
        print("Evento: Gestione Partecipanti")
        self.clear_content()
        tk.Label(
            self.frame_content,
            text="Gestione Partecipanti (work in progress)",
            font=("Helvetica", 16),
            bg="#ecf0f1"
        ).pack(pady=50)

    def event_manage_matches(self):
        print("Evento: Gestione Partite")
        self.clear_content()
        tk.Label(
            self.frame_content,
            text="Gestione Partite (work in progress)",
            font=("Helvetica", 16),
            bg="#ecf0f1"
        ).pack(pady=50)

    def event_show_ranking(self):
        print("Evento: Visualizza Classifica")
        self.clear_content()
        tk.Label(
            self.frame_content,
            text="Classifica Torneo (work in progress)",
            font=("Helvetica", 16),
            bg="#ecf0f1"
        ).pack(pady=50)

    def event_exit(self):
        print("Evento: Uscita dal programma")
        if messagebox.askyesno("Conferma", "Vuoi davvero uscire?"):
            self.destroy()




def frame_gpt():
    app = BriscolaTournamentManager()
    app.mainloop()


