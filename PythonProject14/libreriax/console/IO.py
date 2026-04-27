import random
import threading
from datetime import time
from typing import List, Any

import pyttsx3

from libreriax.utils import Truth



def int_input(messaggio: str, errore: str) -> int:
    while True:
        n = input(messaggio).strip()
        if Truth.check_int(n):
            return int(n)
        print(errore)

def int_positivo_input(messaggio: str, errore: str) -> int:
    while True:
        n = input(messaggio).strip()
        if Truth.check_int_positivo(n):
            return int(n)
        print(errore)

def int_positivo_or_neutro_input(messaggio: str, errore: str) -> int:
    while True:
        n = input(messaggio).strip()
        if Truth.check_int_positivo_or_neutro(n):
            return int(n)
        print(errore)

def int_str_positivo_or_neutro_input(messaggio: str, errore: str) -> str:
    while True:
        n = input(messaggio).strip()
        if Truth.check_int_positivo_or_neutro(n):
            return n
        print(errore)

def float_input(messaggio: str, errore: str) -> float:
    while True:
        n = input(messaggio).strip()
        if Truth.check_float(n):
            return float(n)
        print(errore)

def float_positivo_input(messaggio: str, errore: str) -> float:
    while True:
        n = input(messaggio).strip()
        if Truth.check_float_positivo(n):
            return float(n)
        print(errore)


def string_trim_input(messaggio: str) -> str:
    return input(messaggio).strip()

def yes_or_no_input(messaggio: str, errore: str) -> str:
    while True:
        s = input(messaggio).strip()
        if Truth.check_yes_or_no(s):
            return s.lower()
        print(errore)

def yes_or_no_or_another_input(messaggio: str, errore: str, another: str) -> str:
    while True:
        s = input(messaggio).strip()
        if Truth.check_yes_or_no_or_another(s, another):
            return s
        print(errore)

def char_input(messaggio: str, errore: str) -> str:
    while True:
        s = input(messaggio)
        if len(s) == 1:
            return s
        print(errore)

def parola_input(messaggio: str, errore: str) -> str:
    while True:
        s = input(messaggio)
        if Truth.check_parola(s):
            return s
        print(errore)

def parole_input(messaggio: str, errore: str) -> str:
    while True:
        s = input(messaggio)
        if Truth.check_parole(s):
            return s
        print(errore)

def numero_telefono_input(messaggio: str, errore: str) -> str:
    while True:
        s = input(messaggio).strip()
        if Truth.check_n_telefono(s):
            return s
        print(errore)

def get_localtime_from_input(messaggio: str = "", messaggio_errore: str = "") -> time:
    """Chiede un orario da console e restituisce un oggetto time"""
    print(messaggio)

    while True:
        try:
            ore = int(input("Inserisci le ore: "))
            minuti = int(input("Inserisci i minuti: "))
            secondi = int(input("Inserisci i secondi: "))

            # controllo logico (range time)
            if not (0 <= ore <= 23 and 0 <= minuti <= 59 and 0 <= secondi <= 59):
                print(messaggio_errore)
                continue

            return time(ore, minuti, secondi)

        except ValueError:
            print("Devi inserire numeri interi e sensati. Reinserisci.")

def input_n(vettore: List[int], messaggio: str, errore: str) -> None:
    for i in range(len(vettore)):
        vettore[i] = int_input(messaggio, errore)

def input_string_n(vettore: List[str], messaggio: str) -> None:
    for i in range(len(vettore)):
        vettore[i] = input(messaggio)

def input_num_random(vettore: List[int], estremo_min: int, estremo_max: int) -> None:
    for i in range(len(vettore)):
        vettore[i] = random.randint(estremo_min, estremo_max)

def input_num_random_matrix(matrice: List[List[int]], estremo_min: int, estremo_max: int) -> None:
    for i in range(len(matrice)):
        for j in range(len(matrice[0])):
            matrice[i][j] = random.randint(estremo_min, estremo_max)


def not_that_thing_strip(msg :str,err : str,non_la_cosa = ""):
    cf = input(msg)

    while cf.strip() == non_la_cosa:
        cf = input(err)

    return cf


def stampa(lista : list | tuple):

    if not isinstance(lista,(list, tuple)):
        return

    stringa = ""

    for i in range(len(lista)):
        if i != len(lista) - 1:
            stringa += str(lista[i]) + ","
        else:
            stringa += str(lista[i]) + "."

def stampa_tabella(dati: list[dict], colonne: list[str] | None = None) -> None:
    if not dati:
        print("Nessun dato da mostrare.")
        return

    # se colonne è None, uso tutte le chiavi del primo record
    if colonne is None:
        colonne = list(dati[0].keys())

    # calcola la larghezza di ogni colonna
    larghezze = {}
    for col in colonne:
        max_lung = max(len(str(r.get(col, ""))) for r in dati)
        larghezze[col] = max(max_lung, len(col))

    # stampa bordo superiore
    bordi = "+".join("-" * (larghezze[col] + 2) for col in colonne)
    print(f"+{bordi}+")

    # stampa header
    header = "| " + " | ".join(col.ljust(larghezze[col]) for col in colonne) + " |"
    print(header)

    # bordo sotto header
    print(f"+{bordi}+")

    # stampa righe
    for r in dati:
        riga = "| " + " | ".join(str(r.get(col, "")).ljust(larghezze[col]) for col in colonne) + " |"
        print(riga)

    # bordo finale
    print(f"+{bordi}+")


def input_choice(opzioni : list[str],messaggio : str = "",errore : str = "" ) -> str:
    while True:
        s = input(messaggio).strip()
        if s in opzioni:
            return s
        print(errore)




@staticmethod


def parla(testo: str) :
    def p(testo: str):
        engine = pyttsx3.init()
        engine.say(testo)
        engine.runAndWait()
        engine.stop()
    threading.Thread(target=p,args=(testo,),daemon=True).start()


COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "reset": "\033[0m"
}


@staticmethod
def color(text: str, color_name: str) -> str:
    return f"{COLORS.get(color_name, '')}{text}{COLORS['reset']}"


