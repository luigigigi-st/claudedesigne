def check_int(valore: str) -> bool:
    try:
        int(valore)
        return True
    except:
        return False

def check_int_positivo(valore: str) -> bool:
    try:
        return int(valore) > 0
    except:
        return False

def check_int_positivo_or_neutro(valore: str) -> bool:
    try:
        return int(valore) >= 0
    except:
        return False

def check_float(valore: str) -> bool:
    try:
        float(valore)
        return True
    except:
        return False

def check_float_positivo(valore: str) -> bool:
    try:
        return float(valore) > 0
    except:
        return False

def check_boolean(valore: str) -> bool:
    return valore.lower() in ['true', 'false']

def check_string(valore: str) -> bool:
    return not (check_int(valore) or check_float(valore) or check_boolean(valore))

def check_binario(stringa: str) -> bool:
    return all(c in '01' for c in stringa) and len(stringa) > 0

def check_parola(stringa: str) -> bool:
    return stringa.isalpha()

def check_parole(stringa: str) -> bool:
    return all(parola.isalpha() for parola in stringa.split())

def check_yes_or_no(stringa: str) -> bool:
    return stringa.lower() in ['si', 'no']

def check_yes_or_no_or_another(stringa: str, another: str) -> bool:
    return stringa.lower() in ['si', 'no'] or stringa.lower() == another.lower()

def check_n_telefono(numero: str) -> bool:
    return numero.isdigit() and len(numero) == 10

def check_time(ore: int, minuti: int, sec: int) -> bool:
    return ore >= 0 and 0 <= minuti < 60 and 0 <= sec < 60

def check_vocale(c: str) -> bool:
    return c.lower() in 'aeiou'

def check_consonante(c: str) -> bool:
    return c.isalpha() and not check_vocale(c)