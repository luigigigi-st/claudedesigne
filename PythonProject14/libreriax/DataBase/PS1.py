import pymysql.cursors
import pymysql

from libreriax.console import IO
from libreriax.utils.Risultato import Risultato


class Risulato_DB(Risultato):
    def __init__(self, successo=True, error=None):
        super().__init__(successo, error)

    def is_duplicate_error(self):
        if self.error is None:
            return False
        errno = getattr(self.error, 'args', (None, None))[0] if isinstance(self.error, pymysql.Error) else None
        return errno == 1062 or "1062" in str(self.error)

    def is_fk_error(self):
        if self.error is None:
            return False
        errno = getattr(self.error, 'args', (None, None))[0] if isinstance(self.error, pymysql.Error) else None
        return errno in (1451, 1452) or "1451" in str(self.error) or "1452" in str(self.error)

    def log_error(self, filename="db_errors.log"):
        if self.error:
            with open(filename, "a") as f:
                f.write(f"{self.error}\n")

    def reset(self):
        self.successo = True
        self.error = None


class DB:
    """
    Wrapper PyMySQL con query parametrizzate.

    Tutte le operazioni che accettano valori forniti dall'utente (insert, update,
    delete, select_as_dict, execute_select) usano placeholder %s — mai
    interpolazione di stringhe — per prevenire SQL injection.

    Le query raw in execute_select/execute_alt accettano un parametro `params`
    opzionale (tuple/list) da passare direttamente al cursore.

    Transazioni manuali:
        db.start_transaction()   → apre connessione, disabilita autocommit
        db.commit_transaction()  → commit + chiude
        db.rollback_transaction()→ rollback + chiude
    """

    def __init__(self, database, host='localhost', port=3306, user="root", password=''):
        self.risultato = Risulato_DB()
        self.database  = database
        self.host      = host
        self.port      = port
        self.user      = user
        self.password  = password

        # Stato transazione manuale
        self._tx_conn   = None
        self._tx_cursor = None

    def __str__(self):
        return (f"database:{self.database}\nhost:{self.host}\n"
                f"port:{self.port}\nuser:{self.user}\npassword:{self.password}")

    # ------------------------------------------------------------------ #
    #  Connessione                                                         #
    # ------------------------------------------------------------------ #

    def _connect(self):
        """Apre e restituisce una nuova connessione. Non tocca self.risultato."""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database if self.database else None,
            charset='utf8mb4',
        )

    def CONNECT(self):
        """Compatibilità con il codice esistente."""
        self.risultato.reset()
        try:
            conn = self._connect()
            self.risultato.successo = True
            return conn
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return None
        except Exception as e:
            self.risultato.fallito(e)
            return None

    def can_connect(self) -> bool:
        self.risultato.reset()
        conn = self.CONNECT()
        if conn:
            conn.close()
            self.risultato.successo = True
            return True
        return False

    # ------------------------------------------------------------------ #
    #  Transazioni manuali                                                 #
    # ------------------------------------------------------------------ #

    def start_transaction(self):
        """
        Apre una connessione dedicata con autocommit=False.
        Tutte le operazioni successive useranno questa connessione
        fino a commit_transaction() o rollback_transaction().
        """
        self.risultato.reset()
        try:
            if self._tx_conn is not None:
                # Transazione già aperta: non fare nulla
                return
            self._tx_conn = self._connect()
            self._tx_conn.autocommit(False)
            self._tx_cursor = self._tx_conn.cursor(pymysql.cursors.DictCursor)
            self.risultato.successo = True
        except Exception as e:
            self.risultato.fallito(e)
            self._tx_conn   = None
            self._tx_cursor = None

    def commit_transaction(self):
        self.risultato.reset()
        try:
            if self._tx_conn:
                self._tx_conn.commit()
            self.risultato.successo = True
        except Exception as e:
            self.risultato.fallito(e)
        finally:
            self._close_transaction()

    def rollback_transaction(self):
        self.risultato.reset()
        try:
            if self._tx_conn:
                self._tx_conn.rollback()
            self.risultato.successo = True
        except Exception as e:
            self.risultato.fallito(e)
        finally:
            self._close_transaction()

    def _close_transaction(self):
        try:
            if self._tx_cursor:
                self._tx_cursor.close()
        except Exception:
            pass
        try:
            if self._tx_conn:
                self._tx_conn.close()
        except Exception:
            pass
        self._tx_conn   = None
        self._tx_cursor = None

    # ------------------------------------------------------------------ #
    #  SELECT parametrizzata                                               #
    # ------------------------------------------------------------------ #

    def execute_select(self, query: str, params: tuple | list = None):
        """
        Esegue una SELECT raw.
        Usa params=(val1, val2, ...) per i placeholder %s nella query —
        non concatenare mai valori utente direttamente nella stringa.

        Se è aperta una transazione manuale la usa, altrimenti apre
        una connessione temporanea.
        """
        self.risultato.reset()

        # Usa connessione transazionale se disponibile
        if self._tx_conn is not None:
            try:
                self._tx_cursor.execute(query, params or ())
                self.risultato.successo = True
                return self._tx_cursor.fetchall()
            except Exception as e:
                self.risultato.fallito(e)
                return None

        conn   = self.CONNECT()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, params or ())
            self.risultato.successo = True
            return cursor.fetchall()
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return None
        except Exception as e:
            self.risultato.fallito(e)
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def execute_alt(self, query: str, params: tuple | list = None):
        """
        Esegue una query non-SELECT (INSERT/UPDATE/DELETE) raw.
        Usa params per i placeholder %s.
        Se è aperta una transazione manuale la usa (senza commit interno).
        """
        self.risultato.reset()

        if self._tx_conn is not None:
            try:
                self._tx_cursor.execute(query, params or ())
                self.risultato.successo = True
                return self._tx_cursor.rowcount
            except Exception as e:
                self.risultato.fallito(e)
                return None

        conn = self.CONNECT()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            self.risultato.successo = True
            return cursor.rowcount
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return None
        except Exception as e:
            self.risultato.fallito(e)
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    # ------------------------------------------------------------------ #
    #  INSERT parametrizzato                                               #
    # ------------------------------------------------------------------ #

    def insert(self, nome_tabella: str, colonne: list | tuple, valori: list | tuple):
        """
        INSERT parametrizzato — valori non vengono mai interpolati nella query.
        Restituisce l'id dell'ultima riga inserita, oppure None in caso di errore.
        """
        self.risultato.reset()

        if not isinstance(colonne, (list, tuple)) or not isinstance(valori, (list, tuple)):
            self.risultato.fallito(TypeError("Colonne e valori devono essere liste o tuple"))
            return None

        colonne_str = ", ".join(colonne)
        placeholder = ", ".join(["%s"] * len(valori))
        query       = f"INSERT INTO {nome_tabella} ({colonne_str}) VALUES ({placeholder})"

        if self._tx_conn is not None:
            try:
                self._tx_cursor.execute(query, tuple(valori))
                self.risultato.successo = True
                return self._tx_cursor.lastrowid
            except Exception as e:
                self.risultato.fallito(e)
                return None

        conn   = self.CONNECT()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(valori))
            conn.commit()
            self.risultato.successo = True
            return cursor.lastrowid
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return None
        except Exception as e:
            self.risultato.fallito(e)
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    # ------------------------------------------------------------------ #
    #  UPDATE parametrizzato                                               #
    # ------------------------------------------------------------------ #

    def update(self, nome_tabella: str, valori: dict, condizione: str,
               cond_params: tuple | list = None) -> int:
        """
        UPDATE parametrizzato.

        Esempio:
            db.update("partecipante", {"nome": "Mario", "cognome": "Rossi"},
                      "id_partecipante = %s", (42,))

        condizione può ancora contenere valori letterali sicuri (es. ID interi),
        ma per input utente usare sempre placeholder %s e cond_params.
        Restituisce rowcount o -1 in caso di errore.
        """
        self.risultato.reset()

        if not valori:
            self.risultato.fallito(ValueError("Il dizionario valori è vuoto"))
            return -1

        set_clause  = ", ".join(f"{col} = %s" for col in valori.keys())
        set_values  = list(valori.values())
        cond_values = list(cond_params) if cond_params else []
        params      = tuple(set_values + cond_values)
        query       = f"UPDATE {nome_tabella} SET {set_clause} WHERE {condizione}"

        if self._tx_conn is not None:
            try:
                self._tx_cursor.execute(query, params)
                self.risultato.successo = True
                return self._tx_cursor.rowcount
            except Exception as e:
                self.risultato.fallito(e)
                return -1

        conn   = self.CONNECT()
        if not conn:
            return -1
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            self.risultato.successo = True
            return cursor.rowcount
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return -1
        except Exception as e:
            self.risultato.fallito(e)
            return -1
        finally:
            if cursor:
                cursor.close()
            conn.close()

    # ------------------------------------------------------------------ #
    #  SELECT builder + select_as_dict parametrizzato                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_select(nome_tabella: str,
                      colonne:    list[str] | tuple[str] = None,
                      join:       str = "",
                      condizione: str = '',
                      distinct:   bool = False,
                      group_by:   list[str] | tuple[str] = None,
                      having:     str = '',
                      order_by:   list[tuple[str, str]] = None,
                      limit:      int = None,
                      offset:     int = None) -> str:
        if colonne is None:
            colonne = []
        if group_by is None:
            group_by = []

        select_str = "*"
        if colonne:
            select_str = ", ".join(colonne)
        if distinct:
            select_str = "DISTINCT " + select_str

        query = f"SELECT {select_str} FROM {nome_tabella} {join}"
        if condizione.strip():
            query += f" WHERE {condizione.strip()}"
        if group_by:
            query += f" GROUP BY {', '.join(group_by)}"
        if having.strip():
            query += f" HAVING {having.strip()}"
        if order_by:
            order_strs = [
                f"{col} {dir_.upper() if dir_.upper() in ('ASC', 'DESC') else 'ASC'}"
                for col, dir_ in order_by
            ]
            query += " ORDER BY " + ", ".join(order_strs)
        if limit is not None:
            query += f" LIMIT {limit}"
            if offset is not None:
                query += f" OFFSET {offset}"

        return query

    def select_as_dict(self, nome_tabella: str,
                       colonne:    list[str] | tuple[str] = None,
                       join:       str = "",
                       condizione: str = '',
                       distinct:   bool = False,
                       group_by:   list[str] | tuple[str] = None,
                       having:     str = '',
                       order_by:   list[tuple[str, str]] = None,
                       limit:      int = None,
                       offset:     int = None,
                       params:     tuple | list = None) -> list[dict] | None:
        """
        SELECT builder con supporto parametri.

        Per input utente nei filtri, usa placeholder %s nella condizione
        e passa i valori in params:

            db.select_as_dict("partecipante",
                              condizione="codice_fiscale = %s",
                              params=(cf,))
        """
        self.risultato.reset()
        query = self.create_select(nome_tabella, colonne, join, condizione,
                                   distinct, group_by, having, order_by,
                                   limit, offset)

        if self._tx_conn is not None:
            try:
                self._tx_cursor.execute(query, params or ())
                self.risultato.successo = True
                return self._tx_cursor.fetchall()
            except Exception as e:
                self.risultato.fallito(e)
                return None

        conn   = self.CONNECT()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, params or ())
            self.risultato.successo = True
            return cursor.fetchall()
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return None
        except Exception as e:
            self.risultato.fallito(e)
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    # ------------------------------------------------------------------ #
    #  DELETE parametrizzato                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_delete(nome_tabella: str, condizione: str = "") -> str:
        query = f"DELETE FROM {nome_tabella}"
        if condizione.strip():
            query += f" WHERE {condizione}"
        return query

    def delete(self, tabella: str, condizione: str = "",
               params: tuple | list = None) -> int:
        """
        DELETE parametrizzato.

        Esempio:
            db.delete("partecipante", "codice_fiscale = %s", (cf,))

        Restituisce rowcount o -1 in caso di errore.
        """
        self.risultato.reset()
        query  = self.create_delete(tabella, condizione)
        result = self.execute_alt(query, params)
        return -1 if not self.risultato.successo else result

    # ------------------------------------------------------------------ #
    #  Utilità                                                             #
    # ------------------------------------------------------------------ #

    def get_tables_names(self) -> list:
        self.risultato.reset()
        conn = self.CONNECT()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            self.risultato.successo = True
            return [r[0] for r in cursor.fetchall()]
        except pymysql.Error as e:
            self.risultato.fallito(e)
            return []
        except Exception as e:
            self.risultato.fallito(e)
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def get_as_dict_all_tables(self) -> list[dict] | None:
        self.risultato.reset()
        try:
            all_data = []
            tables   = self.get_tables_names()
            if not self.risultato.successo:
                return None
            for t in tables:
                data = self.select_as_dict(t)
                if not self.risultato.successo:
                    return None
                all_data.append({t: data})
            self.risultato.successo = True
            return all_data
        except Exception as e:
            self.risultato.fallito(e)
            return None

    def stampa_select(self, nome_tabella: str,
                      colonne:    list[str] | tuple[str] = None,
                      join:       str = "",
                      condizione: str = '',
                      distinct:   bool = False,
                      group_by:   list[str] | tuple[str] = None,
                      having:     str = '',
                      order_by:   list[tuple[str, str]] = None,
                      limit:      int = None,
                      offset:     int = None) -> None:
        self.risultato.reset()
        dati = self.select_as_dict(nome_tabella, colonne, join, condizione,
                                   distinct, group_by, having, order_by,
                                   limit, offset)
        if dati is not None:
            IO.stampa_tabella(dati)