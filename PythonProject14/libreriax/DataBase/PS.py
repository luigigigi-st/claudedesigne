import pymysql.cursors # Import per i tipi di cursore, come DictCursor
import pymysql         # Import principale per la connessione PyMySQL

from libreriax.console import IO
from libreriax.utils.Risultato import Risultato

class Risulato_DB(Risultato):
    def __init__(self, successo=True, error=None):
        super().__init__(successo, error)

    def is_duplicate_error(self):
        if self.error is None:
            return False
        # PyMySQL Errors have different attributes, e.g., 'args' for error code
        # For PyMySQL, duplicate entry error is often 1062
        errno = getattr(self.error, 'args', (None, None))[0] if isinstance(self.error, pymysql.Error) else None
        return errno == 1062 or "1062" in str(self.error)

    def is_fk_error(self):
        if self.error is None:
            return False
        # For PyMySQL, FK errors are often 1451, 1452
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
    def __init__(self, database, host='localhost', port=3306, user="root", password=''):
        self.risultato = Risulato_DB()
        self.database = database
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def __str__(self):
        return f"database:{self.database}\nhost:{self.host}\nport:{self.port}\nuser:{self.user}\npassword:{self.password}"

    def CONNECT(self):
        self.risultato.reset()
        try:
            # Usa pymysql.connect per stabilire la connessione
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database if self.database else None,
                # PyMySQL è già in puro Python, non necessita di 'use_pure'
                # Un charset comune è 'utf8mb4' per la piena compatibilità con emoji e caratteri speciali
                # charset='utf8mb4'
            )
            self.risultato.successo = True
            return conn
        except pymysql.Error as e: # Cattura errori specifici di PyMySQL
            self.risultato.fallito(e)
            return None
        except Exception as e: # Per altri tipi di errori
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

    def execute_select(self, query: str):
        self.risultato.reset()
        conn = self.CONNECT()
        if not conn:
            return None
        cursor = None # Inizializza cursor a None per gestione nel finally
        try:
            # Crea cursore usando pymysql.cursors.DictCursor per risultati come dizionari
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query)
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
                # 'nextset()' non è generalmente usato/necessario con PyMySQL per query SELECT singole
                cursor.close()
            if conn:
                conn.close()

    def execute_alt(self, query: str):
        self.risultato.reset()
        conn = self.CONNECT()
        if not conn:
            return None
        cursor = conn.cursor() # Cursore semplice per operazioni non SELECT
        try:
            cursor.execute(query)
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
            if conn:
                conn.close()

    def insert(self, nome_tabella: str, colonne: list | tuple, valori: list | tuple):
        self.risultato.reset()
        conn = self.CONNECT()
        if not conn:
            return None
        cursor = conn.cursor() # Anche per INSERT un cursore semplice è sufficiente
        try:
            if not isinstance(colonne, (list, tuple)) or not isinstance(valori, (list, tuple)):
                raise TypeError("Colonne e valori devono essere liste o tuple")
            colonne_str = ", ".join(colonne)
            valori_str = ", ".join(["%s"] * len(valori))
            query = f"INSERT INTO {nome_tabella} ({colonne_str}) VALUES ({valori_str})"
            cursor.execute(query, valori)
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
            if conn:
                conn.close()

    @staticmethod
    def create_select(nome_tabella: str,
                      colonne: list[str] | tuple[str] = None,
                      join: str = "",
                      condizione: str = '',
                      distinct: bool = False,
                      group_by: list[str] | tuple[str] = None,
                      having: str = '',
                      order_by: list[tuple[str, str]] = None,
                      limit: int = None,
                      offset: int = None) -> str:
        """
        Crea una SELECT flessibile con supporto a:
        - colonne
        - DISTINCT
        - JOIN
        - WHERE
        - GROUP BY / HAVING
        - ORDER BY
        - LIMIT / OFFSET
        """
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
            order_strs = [f"{col} {dir.upper() if dir.upper() in ('ASC','DESC') else 'ASC'}"
                          for col, dir in order_by]
            query += " ORDER BY " + ", ".join(order_strs)
        if limit is not None:
            query += f" LIMIT {limit}"
            if offset is not None:
                query += f" OFFSET {offset}"

        return query

    def select_as_dict(self, nome_tabella: str,
                       colonne: list[str] | tuple[str] = None,
                       join: str = "",
                       condizione: str = '',
                       distinct: bool = False,
                       group_by: list[str] | tuple[str] = None,
                       having: str = '',
                       order_by: list[tuple[str, str]] = None,
                       limit: int = None,
                       offset: int = None) -> list[dict] | None:
        self.risultato.reset()
        conn = self.CONNECT()
        if not conn:
            return None

        cursor = None
        try:
            # Crea cursore usando pymysql.cursors.DictCursor
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = self.create_select(nome_tabella, colonne, join, condizione,
                                       distinct, group_by, having, order_by,
                                       limit, offset)
            cursor.execute(query)
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
                # 'nextset()' non è generalmente usato/necessario con PyMySQL
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def create_delete(nome_tabella: str, condizione: str = "") -> str:
        query = f"DELETE FROM {nome_tabella}"
        if condizione.strip():
            query += f" WHERE {condizione}"
        return query

    def delete(self, tabella: str, condizione: str = "") -> int:
        self.risultato.reset()
        query = self.create_delete(tabella, condizione)
        result = self.execute_alt(query)
        return -1 if not self.risultato.successo else result

    def get_tables_names(self) -> list:
        self.risultato.reset()
        conn = self.CONNECT()
        if not conn:
            return []
        cursor = conn.cursor() # Cursore semplice per SHOW TABLES
        try:
            cursor.execute("SHOW TABLES")
            self.risultato.successo = True
            # PyMySQL fetchall con cursore semplice restituisce tuple
            # Quindi dobbiamo estrarre il primo elemento di ogni tupla
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
            if conn:
                conn.close()

    def get_as_dict_all_tables(self) -> list[dict] | None:
        self.risultato.reset()
        try:
            all_data = []
            tables = self.get_tables_names()
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
                      colonne: list[str] | tuple[str] = None,
                      join: str = "",
                      condizione: str = '',
                      distinct: bool = False,
                      group_by: list[str] | tuple[str] = None,
                      having: str = '',
                      order_by: list[tuple[str, str]] = None,
                      limit: int = None,
                      offset: int = None) -> None:
        self.risultato.reset()
        dati = self.select_as_dict(nome_tabella, colonne, join, condizione,
                                   distinct, group_by, having, order_by,
                                   limit, offset)
        if dati is not None:
            IO.stampa_tabella(dati)