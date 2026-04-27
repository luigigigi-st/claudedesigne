import threading
import pyttsx3
import queue

class Speaker:
    def __init__(self):
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._engine = pyttsx3.init()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _new_engine(self):
        self._engine = pyttsx3.init()

    def _run(self):
        while True:
            testo = self._queue.get()
            if testo is None:
                break
            self._engine.say(testo)
            self._engine.runAndWait()

    def speak(self, testo: str):
        self.stop()
        self._queue.put(testo)

    def stop(self):
        with self._lock:
            # svuota coda
            with self._queue.mutex:
                self._queue.queue.clear()

            try:
                self._engine.stop()
            except:
                pass

            # 🔥 reset engine
            self._new_engine()
