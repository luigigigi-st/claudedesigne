# classe risultato. mi serve per gestire l'errore
class Risultato:

    def __init__(self, successo=True, error=None):
        self.successo = successo
        self.error = error

    def fallito(self, e : Exception | str):
        self.successo = False
        if isinstance(e, str):
            self.error = Exception(e)
        elif isinstance(e, Exception):
            print("ci diamo")
            self.error = e



    def get_msg(self):
        return str(self.error)
