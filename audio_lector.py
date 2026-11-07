# AudioTexto: v2 - 07/11/26
# Este código fue escrito a fin de solucionar un problema de pereza con el cual sé
# me es muy aburrido en ciertos puntos, el leer tanto texto. El enfoque inicial de
# este proyecto es para textos comunes, aunque con el paso del tiempo deseo que este
# pueda leer y generar audio de textos de economía, y de química. Este proyecto se
# hace también con mucho cariño e inspiración hacía Carolina, feliz 14 de febrero
# amor, espero el día que yo me sienta seguro de mostrar este proyecto, tú seas la
# primera en utilizarlo. Te amo. Atte: Flavio.

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pyttsx3
import PyPDF2
import threading
import shutil
import os
import re
import sys

# --- OCR opcional (para PDF escaneados) ---
# Requiere: pip install pymupdf pytesseract  +  el programa Tesseract-OCR instalado.
try:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    import pytesseract
    from PIL import Image
    OCR_LIBRERIAS = True
except ImportError:
    OCR_LIBRERIAS = False

# Rutas comunes de Tesseract en Windows y macOS, por si no está en el PATH
RUTAS_TESSERACT = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
]

PATRON_URL = re.compile(r'https?://\S+|www\.\S+')

COLOR_FONDO = "#f8fafc"
COLOR_LEER = "#10b981"
COLOR_PAUSA = "#f59e0b"


def verificar_ocr():
    """Devuelve (disponible, mensaje). Configura la ruta de Tesseract si hace falta."""
    if not OCR_LIBRERIAS:
        return False, ("Faltan librerías para OCR. Instálalas con:\n"
                       "pip install pymupdf pytesseract")
    comando = pytesseract.pytesseract.tesseract_cmd
    if shutil.which(comando):
        return True, ""
    for ruta in RUTAS_TESSERACT:
        if os.path.exists(ruta):
            pytesseract.pytesseract.tesseract_cmd = ruta
            return True, ""
    return False, ("No se encontró el programa Tesseract-OCR.\n"
                   "Descárgalo e instálalo (incluyendo el idioma español) para leer PDF escaneados.")


def idioma_ocr():
    """Usa español (y también inglés) si Tesseract los tiene instalados."""
    try:
        idiomas = pytesseract.get_languages(config='')
    except Exception:
        return None
    elegidos = [i for i in ("spa", "eng") if i in idiomas]
    return "+".join(elegidos) if elegidos else None


def limites_palabra(texto, posicion):
    """
    Devuelve (inicio, largo) de la palabra completa en esa posición.
    Cada motor de voz reporta la posición un poco distinto (en Linux llega
    desfasada un carácter), así que ajustamos siempre a la palabra entera.
    """
    posicion = min(max(posicion, 0), len(texto))
    # Si cae justo después de una palabra (en un espacio o signo), retroceder a ella
    if (posicion == len(texto) or not texto[posicion].isalnum()) and posicion > 0 and texto[posicion - 1].isalnum():
        posicion -= 1
    if posicion >= len(texto) or not texto[posicion].isalnum():
        return posicion, 0
    inicio = posicion
    while inicio > 0 and texto[inicio - 1].isalnum():
        inicio -= 1
    fin = posicion
    while fin < len(texto) and texto[fin].isalnum():
        fin += 1
    return inicio, fin - inicio


class AudioTextoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AudioTexto v2 - Carolina Edition")
        self.root.geometry("800x600")
        self.root.configure(bg=COLOR_FONDO)

        # Variables de control
        self.is_playing = False      # True mientras se está leyendo
        self.hilo_activo = False     # True hasta que el hilo de lectura termina por completo
        self.accion = None           # Qué pidió el usuario al cortar: 'pausa', 'detener' o 'reiniciar'
        self.pos_actual = 0          # Posición (en caracteres) de la palabra que se está leyendo
        self.voces_dict = {}

        self.crear_interfaz()
        self.cargar_voces()

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def crear_interfaz(self):
        # --- Marco superior (Controles) ---
        top_frame = tk.Frame(self.root, pady=10, bg=COLOR_FONDO)
        top_frame.pack(fill=tk.X, padx=15)

        # Botón Cargar
        self.btn_cargar = tk.Button(top_frame, text="📁 Abrir Archivo (PDF/TXT)", command=self.cargar_archivo,
                                    bg="#6366f1", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=10)
        self.btn_cargar.pack(side=tk.LEFT, padx=5)

        # Selector de Voz
        tk.Label(top_frame, text="Voz:", bg=COLOR_FONDO, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        self.combo_voces = ttk.Combobox(top_frame, state="readonly", width=35, font=("Segoe UI", 10))
        self.combo_voces.pack(side=tk.LEFT, padx=5)
        # Si cambias de voz mientras lee, continúa con la nueva voz
        self.combo_voces.bind("<<ComboboxSelected>>", lambda e: self._reiniciar_si_lee())

        # Botones de Reproducción
        self.btn_play = tk.Button(top_frame, text="▶ Leer", command=self.alternar_lectura,
                                  bg=COLOR_LEER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=9)
        self.btn_play.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(top_frame, text="■ Detener", command=self.detener_lectura,
                                  bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=9)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # --- Segunda fila: velocidad ---
        speed_frame = tk.Frame(self.root, bg=COLOR_FONDO)
        speed_frame.pack(fill=tk.X, padx=15)

        tk.Label(speed_frame, text="Velocidad:", bg=COLOR_FONDO, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        self.velocidad = tk.IntVar(value=160)
        self.scale_velocidad = tk.Scale(speed_frame, from_=80, to=300, resolution=10, orient=tk.HORIZONTAL,
                                        variable=self.velocidad, length=220, showvalue=True,
                                        bg=COLOR_FONDO, highlightthickness=0, font=("Segoe UI", 9))
        self.scale_velocidad.pack(side=tk.LEFT, padx=5)
        # Al soltar el deslizador mientras lee, continúa con la nueva velocidad
        self.scale_velocidad.bind("<ButtonRelease-1>", lambda e: self._reiniciar_si_lee())
        self.scale_velocidad.bind("<KeyRelease>", lambda e: self._reiniciar_si_lee())

        tk.Label(speed_frame, text="Tip: haz clic en el texto para empezar a leer desde ahí.",
                 bg=COLOR_FONDO, fg="#64748b", font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=5)

        # --- Área de Texto Principal ---
        text_frame = tk.Frame(self.root)
        text_frame.pack(expand=True, fill=tk.BOTH, padx=15, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(text_frame, wrap=tk.WORD, font=("Georgia", 13),
                                 yscrollcommand=scrollbar.set, relief="flat", padx=10, pady=10)
        self.text_area.pack(expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.text_area.yview)

        # Estilo para la palabra que se está leyendo
        self.text_area.tag_configure("leyendo", background="#fde68a", foreground="#1e293b")

        # --- Marco inferior (Estado y mensaje especial) ---
        bottom_frame = tk.Frame(self.root, bg=COLOR_FONDO)
        bottom_frame.pack(fill=tk.X, padx=15, pady=5)

        lbl_dedicatoria = tk.Label(bottom_frame, text="Creado con amor para Carolina ❤️",
                                   bg=COLOR_FONDO, fg="#ec4899", font=("Segoe UI", 10, "italic"))
        lbl_dedicatoria.pack(side=tk.RIGHT)

        lbl_autor = tk.Label(bottom_frame, text="Atte: Flavio",
                                   bg=COLOR_FONDO, fg="#64748b", font=("Segoe UI", 9))
        lbl_autor.pack(side=tk.LEFT)

        self.lbl_estado = tk.Label(bottom_frame, text="", bg=COLOR_FONDO, fg="#334155", font=("Segoe UI", 9))
        self.lbl_estado.pack(side=tk.LEFT, padx=20)

    def _estado(self, texto):
        self.lbl_estado.config(text=texto)

    # ------------------------------------------------------------------
    # Voces
    # ------------------------------------------------------------------
    def cargar_voces(self):
        """Carga las voces y renombra las femeninas a Carolina y masculinas a Flavio"""
        engine_temp = pyttsx3.init()
        voces = engine_temp.getProperty('voices')

        # Nombres de voces comunes en Windows, macOS y Linux (eSpeak)
        femeninas = ['zira', 'helena', 'sabina', 'paulina', 'monica', 'mónica', 'laura', 'dalia', 'female', 'mujer']
        masculinas = ['david', 'pablo', 'jorge', 'juan', 'diego', 'raul', 'raúl', 'male', 'hombre']

        for voz in voces:
            nombre_original = voz.name
            nombre_mostrar = nombre_original
            nombre_min = nombre_original.lower()
            genero = (getattr(voz, 'gender', None) or '').lower()

            # Detectar si es voz femenina para llamarla Carolina
            if genero == 'female' or any(x in nombre_min for x in femeninas):
                nombre_mostrar = f"Carolina ({nombre_original})"
            # Detectar si es voz masculina para llamarla Flavio
            elif genero == 'male' or any(x in nombre_min for x in masculinas):
                nombre_mostrar = f"Flavio ({nombre_original})"

            self.voces_dict[nombre_mostrar] = voz.id

        self.combo_voces['values'] = list(self.voces_dict.keys())

        # Seleccionar a "Carolina" por defecto si existe
        for nombre in self.voces_dict.keys():
            if "Carolina" in nombre:
                self.combo_voces.set(nombre)
                break

        # Si no hay Carolina, seleccionar la primera disponible
        if not self.combo_voces.get() and self.combo_voces['values']:
            self.combo_voces.set(self.combo_voces['values'][0])

    # ------------------------------------------------------------------
    # Carga de archivos
    # ------------------------------------------------------------------
    def cargar_archivo(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Archivos de Texto y PDF", "*.txt *.pdf"), ("Todos los archivos", "*.*")]
        )
        if not filepath:
            return

        self.detener_lectura()
        self.text_area.delete(1.0, tk.END)

        if filepath.lower().endswith('.pdf'):
            # Los PDF se procesan en segundo plano porque el OCR puede tardar
            self.btn_cargar.config(state=tk.DISABLED)
            self._estado("Cargando PDF...")
            threading.Thread(target=self._cargar_pdf, args=(filepath,), daemon=True).start()
            return

        try:
            # Extraer texto de TXT (Manejo robusto de errores de codificación de Windows)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    texto = file.read()
            except UnicodeDecodeError:
                # Si falla el utf-8, intentamos con la codificación estándar de Windows
                with open(filepath, 'r', encoding='cp1252') as file:
                    texto = file.read()
            self._mostrar_texto(texto)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{str(e)}")

    def _cargar_pdf(self, filepath):
        """Extrae el texto del PDF. Las páginas sin texto (escaneadas) pasan por OCR."""
        try:
            lector_pdf = PyPDF2.PdfReader(filepath)
            paginas = []
            sin_texto = []
            for i, pagina in enumerate(lector_pdf.pages):
                texto = (pagina.extract_text() or "").strip()
                paginas.append(texto)
                if not texto:
                    sin_texto.append(i)

            aviso = None
            if sin_texto:
                disponible, mensaje = verificar_ocr()
                if disponible:
                    idioma = idioma_ocr()
                    with fitz.open(filepath) as doc:
                        for n, i in enumerate(sin_texto, start=1):
                            self.root.after(0, self._estado,
                                            f"Reconociendo texto (OCR): página {n} de {len(sin_texto)}...")
                            imagen = doc[i].get_pixmap(dpi=300)
                            img = Image.frombytes("RGB", (imagen.width, imagen.height), imagen.samples)
                            paginas[i] = pytesseract.image_to_string(img, lang=idioma).strip()
                else:
                    aviso = (f"{len(sin_texto)} página(s) parecen escaneadas y no se pudieron leer.\n\n"
                             f"{mensaje}")

            texto_completo = "\n\n".join(p for p in paginas if p)
            self.root.after(0, self._mostrar_texto, texto_completo, aviso)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo leer el archivo:\n{str(e)}"))
            self.root.after(0, self._estado, "")
        finally:
            self.root.after(0, lambda: self.btn_cargar.config(state=tk.NORMAL))

    def _mostrar_texto(self, texto, aviso=None):
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, texto)
        self.text_area.mark_set(tk.INSERT, "1.0")
        self.text_area.see("1.0")
        self._estado("Archivo cargado.")
        if aviso:
            messagebox.showwarning("Aviso", aviso)

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def alternar_lectura(self):
        """El mismo botón sirve para Leer y para Pausar."""
        if self.is_playing:
            self.pausar_lectura()
        else:
            self.iniciar_lectura()

    def iniciar_lectura(self):
        # Esperar a que el hilo anterior termine antes de empezar otro
        if self.is_playing or self.hilo_activo:
            return

        texto = self.text_area.get("1.0", "end-1c")
        if not texto.strip():
            messagebox.showwarning("Aviso", "No hay texto para leer.")
            return

        # Cambiamos los enlaces (URLs) por espacios para que no los lea,
        # sin mover las posiciones del resto del texto (necesario para el resaltado).
        texto = PATRON_URL.sub(lambda m: " " * len(m.group()), texto)

        # Empezar desde el cursor (donde hiciste clic o donde se pausó)
        inicio = self.text_area.count("1.0", tk.INSERT, "chars")
        inicio = inicio[0] if inicio else 0
        # Si el cursor quedó en medio de una palabra, empezar desde su inicio
        while 0 < inicio < len(texto) and texto[inicio - 1].isalnum():
            inicio -= 1
        # Si no queda nada por leer desde ahí, empezar desde el principio
        if not texto[inicio:].strip():
            inicio = 0

        self.is_playing = True
        self.hilo_activo = True
        self.accion = None
        self.pos_actual = inicio

        # Bloquear la edición mientras lee para que el resaltado no se desfase
        self.text_area.config(state=tk.DISABLED)
        self.btn_play.config(text="⏸ Pausar", bg=COLOR_PAUSA)
        self._estado("Leyendo...")

        nombre_voz = self.combo_voces.get()
        voz_id = self.voces_dict.get(nombre_voz)
        velocidad = self.velocidad.get()

        # Iniciar hilo de lectura
        threading.Thread(target=self._bucle_lectura_fluido,
                         args=(voz_id, velocidad, texto, inicio), daemon=True).start()

    def _bucle_lectura_fluido(self, voz_id, velocidad, texto, inicio):
        """
        Lee el texto de corrido para evitar bloqueos en los puntos finales.
        Usa un evento interno del motor para resaltar cada palabra y para
        abortar cuando presionas Pausar o Detener.
        """
        # Requerido en Windows para inicializar COM en un hilo secundario de forma segura
        if sys.platform == 'win32':
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pass

        engine = None
        token = None
        try:
            engine = pyttsx3.init()
            if voz_id:
                engine.setProperty('voice', voz_id)
            engine.setProperty('rate', velocidad)

            # Este "sensor" se activa antes de que el motor diga cada palabra.
            # Resalta la palabra y, si apretaste Pausar/Detener, aborta el motor.
            def on_word(name, location, length):
                if not self.is_playing:
                    engine.stop()
                    return
                posicion, largo = limites_palabra(texto, inicio + location)
                if largo:
                    self.pos_actual = posicion
                    self.root.after(0, self._resaltar, posicion, largo)

            token = engine.connect('started-word', on_word)

            # Le pasamos TODO el texto restante de un golpe. Así lee sin pausas raras.
            engine.say(texto[inicio:])
            engine.runAndWait()

        except Exception as e:
            print("Error en el motor de voz:", e)

        finally:
            if engine is not None and token is not None:
                try:
                    engine.disconnect(token)
                except Exception:
                    pass

            if sys.platform == 'win32':
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except ImportError:
                    pass

            self.root.after(0, self._al_terminar)

    def _resaltar(self, posicion, largo):
        if not self.is_playing:
            return
        inicio = f"1.0 + {posicion} chars"
        fin = f"1.0 + {posicion + max(largo, 1)} chars"
        self.text_area.tag_remove("leyendo", "1.0", tk.END)
        self.text_area.tag_add("leyendo", inicio, fin)
        self.text_area.see(inicio)

    def _al_terminar(self):
        """Se ejecuta en la ventana principal cuando el hilo de lectura termina."""
        accion = self.accion
        self.is_playing = False
        self.hilo_activo = False
        self.accion = None

        self.text_area.config(state=tk.NORMAL)
        self.text_area.tag_remove("leyendo", "1.0", tk.END)
        self.btn_play.config(text="▶ Leer", bg=COLOR_LEER)

        if accion == 'reiniciar':
            # Continuar desde la palabra actual con la nueva voz o velocidad
            self.text_area.mark_set(tk.INSERT, f"1.0 + {self.pos_actual} chars")
            self.iniciar_lectura()
        elif accion == 'pausa':
            # Dejar el cursor donde se quedó para continuar desde ahí
            self.text_area.mark_set(tk.INSERT, f"1.0 + {self.pos_actual} chars")
            self.text_area.see(tk.INSERT)
            self._estado("En pausa. Presiona Leer para continuar.")
        elif accion == 'detener':
            self.text_area.mark_set(tk.INSERT, "1.0")
            self._estado("Lectura detenida.")
        else:
            # Terminó de leer todo el texto
            self.text_area.mark_set(tk.INSERT, "1.0")
            self._estado("Lectura terminada.")

    def pausar_lectura(self):
        if self.is_playing:
            self.accion = 'pausa'
            self.is_playing = False
            self._estado("Pausando...")

    def detener_lectura(self):
        # Al cambiar esto a False, el "sensor" en _bucle_lectura_fluido detendrá el audio.
        if self.is_playing:
            self.accion = 'detener'
            self.is_playing = False
        elif not self.hilo_activo:
            # Si estaba en pausa, volver al inicio del texto
            self.text_area.mark_set(tk.INSERT, "1.0")
            self._estado("")

    def _reiniciar_si_lee(self):
        """Aplica un cambio de voz o velocidad sin perder la posición de lectura."""
        if self.is_playing:
            self.accion = 'reiniciar'
            self.is_playing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioTextoApp(root)
    root.mainloop()
