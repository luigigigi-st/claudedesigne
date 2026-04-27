from datetime import date
from typing import List, TypeVar


class Strings:

    def conta_carattere(stringa: str, carattere: str) -> int:
        conta = 0
        for c in stringa:
            if c == carattere:
                conta += 1
        return conta

    def aggiorna_carattere(stringa: str, carattere: str, carattere1: str) -> str:
        return stringa.replace(carattere, carattere1)

    def conta_vocali(stringa: str) -> int:
        vocali = "aeiouAEIOU"
        conta = 0
        for c in stringa:
            if c in vocali:
                conta += 1
        return conta

    def conta_consonanti(stringa: str) -> int:
        vocali = "aeiouAEIOU"
        conta = 0
        for c in stringa:
            if c.isalpha() and c not in vocali:
                conta += 1
        return conta

    def conta_minuscole(stringa: str) -> int:
        conta = 0
        for c in stringa:
            if c.islower():
                conta += 1
        return conta

    def conta_maiuscole(stringa: str) -> int:
        conta = 0
        for c in stringa:
            if c.isupper():
                conta += 1
        return conta

    def conta_cifre(stringa: str) -> int:
        conta = 0
        for c in stringa:
            if c.isdigit():
                conta += 1
        return conta

    def inizio_maiuscolo(stringa: str) -> str:
        if not stringa:
            return stringa
        return stringa[0].upper() + stringa[1:].lower()

    def ricorda_pos_carattere(stringa: str, carattere: str) -> int:
        for i, c in enumerate(stringa):
            if c == carattere:
                return i
        return -1

    def ricava_data(str_data: str) -> date:
        # formato: yyyy-MM-dd
        anno, mese, giorno = str_data.split("-")
        return date(int(anno), int(mese), int(giorno))

    def join_and_add(str_canghe: str, str_add: str, separatore: str = "") -> str:
            return str_add + " " + str_canghe + separatore + " "



