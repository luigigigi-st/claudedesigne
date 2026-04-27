from datetime import datetime, date
from typing import Optional


# -------------------
# Funzioni di controllo
# -------------------

def check_bisestile(anno: int) -> bool:
    """Verifica se un anno è bisestile"""
    return anno % 400 == 0 or (anno % 4 == 0 and anno % 100 != 0)


def check_data(giorno: int, mese: int, anno: int) -> bool:
    """Verifica se una data è valida"""
    if giorno < 1 or giorno > 31 or mese < 1 or mese > 12:
        return False
    if mese in [4, 6, 9, 11] and giorno > 30:
        return False
    if mese == 2:
        if check_bisestile(anno) and giorno > 29:
            return False
        elif not check_bisestile(anno) and giorno > 28:
            return False
    return True


# -------------------
# Funzioni di input da console
# -------------------

def get_data_from_input(messaggio: str, messaggio_errore: str, separatore: str = "-") -> str:
    """Chiede una data da console e restituisce stringa formattata"""
    print(messaggio)
    while True:
        try:
            giorno = int(input("Inserisci il giorno: "))
            mese = int(input("Inserisci il mese: "))
            anno = int(input("Inserisci l'anno: "))
        except ValueError:
            print("Devi inserire numeri interi. Reinserisci.")
            continue

        if check_data(giorno, mese, anno):
            break
        else:
            print(messaggio_errore)

    return f"{giorno}{separatore}{mese}{separatore}{anno}"


def get_localdate_from_input(messaggio: str, messaggio_errore: str) -> date:
    """Chiede una data da console e restituisce oggetto date"""
    print(messaggio)
    data = None
    while True:
        try:
            giorno = int(input("Inserisci il giorno: "))
            mese = int(input("Inserisci il mese: "))
            anno = int(input("Inserisci l'anno: "))
            data = date(anno, mese, giorno)

        except ValueError:
            print("Devi inserire numeri interi e sensati. Reinserisci.")
            continue

        if check_data(giorno, mese, anno):
            break
        else:
            print(messaggio_errore)

    return data


def get_data_month_year_input(messaggio: str, messaggio_errore: str, separatore: str = "-") -> str:
    """Chiede solo mese e anno da console e restituisce stringa"""
    print(messaggio)
    while True:
        try:
            mese = int(input("Inserisci il mese: "))
            anno = int(input("Inserisci l'anno: "))
        except ValueError:
            print("Devi inserire numeri interi. Reinserisci.")
            continue

        if 1 <= mese <= 12:
            break
        else:
            print(messaggio_errore)

    return f"{mese}{separatore}{anno}"


# -------------------
# Funzioni di utilità sulle date
# -------------------

def check_today(data: date) -> bool:
    """Verifica se la data non è futura"""
    return data <= date.today()


def ricava_data(str_data: str) -> date:
    """Converte stringa 'YYYY-MM-DD' in oggetto date"""
    return datetime.strptime(str_data, "%Y-%m-%d").date()


def get_localdate(dt: Optional[datetime]) -> Optional[date]:
    """Converte datetime in date"""
    if dt is None:
        return None
    return dt.date()


from datetime import datetime

from datetime import datetime


def differenza_giorni(data1, data2, tipo: str = "day", formato="%Y-%m-%d"):
    """
    Calcola la differenza tra due date in giorni, mesi o anni (valore assoluto).

    data1, data2: stringhe o oggetti datetime/date
    tipo: "day", "month" o "year"
    formato: formato delle date se sono stringhe (default: "YYYY-MM-DD")
    """
    if isinstance(data1, str):
        data1 = datetime.strptime(data1, formato).date()
    if isinstance(data2, str):
        data2 = datetime.strptime(data2, formato).date()

    if tipo.lower() == "day":
        return (data2 - data1).days
    elif tipo.lower() == "month":
        # differenza assoluta dei mesi
        return abs((data2.year - data1.year) * 12 + (data2.month - data1.month))
    elif tipo.lower() == "year":
        # differenza assoluta degli anni
        return abs(data2.year - data1.year)
    else:
        return None


from datetime import datetime

def differenza_giorni_no_abs(data1, data2, tipo: str = "day", formato="%Y-%m-%d"):
    """
    Calcola la differenza tra due date in giorni, mesi o anni.
    Restituisce un valore con segno (positivo o negativo).
    """

    if isinstance(data1, str):
        data1 = datetime.strptime(data1, formato).date()
    if isinstance(data2, str):
        data2 = datetime.strptime(data2, formato).date()

    if tipo.lower() == "day":
        return (data2 - data1).days

    elif tipo.lower() == "month":
        return (data2.year - data1.year) * 12 + (data2.month - data1.month)

    elif tipo.lower() == "year":
        return data2.year - data1.year

    else:
        return None


def calcola_eta(data_nascita, data_riferimento):
    if isinstance(data_nascita, str):
        data_nascita = datetime.strptime(data_nascita, "%Y-%m-%d").date()
    if isinstance(data_riferimento, str):
        data_riferimento = datetime.strptime(data_riferimento, "%Y-%m-%d").date()

    eta = data_riferimento.year - data_nascita.year

    # Se non ha ancora fatto il compleanno quest'anno, togli 1
    if (data_riferimento.month, data_riferimento.day) < (data_nascita.month, data_nascita.day):
        eta -= 1

    return eta


def get_datetime(d: Optional[date]) -> Optional[datetime]:
    """Converte date in datetime"""
    if d is None:
        return None
    return datetime(d.year, d.month, d.day)
