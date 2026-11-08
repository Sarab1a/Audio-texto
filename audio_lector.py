# AudioTexto: v3 - 08/11/26
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
import concurrent.futures
import asyncio
import shutil
import locale
import time
import io
import os
import re
import sys

# --- Voces en línea (opcional) ---
# Requiere: pip install edge-tts pygame-ce  y conexión a internet.
# Si no hay internet (o faltan estas librerías) se usan las voces de la computadora.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import edge_tts
    import pygame
    EN_LINEA_LIBRERIAS = True
except ImportError:
    EN_LINEA_LIBRERIAS = False

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


# --- Voces ---
# Windows guarda las voces en dos lugares. pyttsx3 solo ve el antiguo (normalmente
# solo voces en inglés); las voces en español suelen estar en el moderno ("OneCore").
VOCES_ONECORE = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices"

NOMBRES_FEMENINOS = ['zira', 'helena', 'sabina', 'paulina', 'monica', 'mónica', 'laura', 'dalia',
                     'elvira', 'hazel', 'susan', 'female', 'mujer']
NOMBRES_MASCULINOS = ['david', 'pablo', 'jorge', 'juan', 'diego', 'raul', 'raúl', 'mark', 'george',
                      'male', 'hombre']

PAISES = {'mx': 'México', 'es': 'España', '419': 'Latinoamérica', 'us': 'EE. UU.', 'gb': 'Reino Unido',
          'ar': 'Argentina', 'co': 'Colombia', 'cl': 'Chile', 'ca': 'Canadá', 'au': 'Australia', 'in': 'India'}


def lcid_a_codigo(lcid):
    """Convierte el código de idioma de Windows (ej. '80A') a texto (ej. 'es-MX')."""
    try:
        return locale.windows_locale[int(str(lcid).split(';')[0], 16)].replace('_', '-')
    except (ValueError, KeyError):
        return ''


def voces_onecore():
    """Lista las voces modernas de Windows (ahí suelen estar las voces en español)."""
    if sys.platform != 'win32':
        return []
    voces = []
    try:
        import comtypes.client
        categoria = comtypes.client.CreateObject("SAPI.SpObjectTokenCategory")
        categoria.SetId(VOCES_ONECORE, False)
        tokens = categoria.EnumerateTokens()
        for i in range(tokens.Count):
            try:
                token = tokens.Item(i)
                voces.append({
                    'id': token.Id,
                    'nombre': token.GetDescription(),
                    'genero': token.GetAttribute("Gender"),
                    'idioma': lcid_a_codigo(token.GetAttribute("Language")),
                })
            except Exception:
                continue
    except Exception as e:
        print("No se pudieron leer las voces modernas de Windows:", e)
    return voces


def asignar_voz(engine, voz_id):
    """Selecciona la voz en el motor. Las voces modernas de Windows se asignan directo a SAPI."""
    if 'Speech_OneCore' not in voz_id:
        engine.setProperty('voice', voz_id)
        return
    import comtypes.client
    categoria = comtypes.client.CreateObject("SAPI.SpObjectTokenCategory")
    categoria.SetId(voz_id.split('\\Tokens\\')[0], False)
    tokens = categoria.EnumerateTokens()
    for i in range(tokens.Count):
        token = tokens.Item(i)
        if token.Id == voz_id:
            engine.proxy._driver._tts.Voice = token
            return
    raise ValueError(f"No se encontró la voz {voz_id}")


def idioma_legible(codigo, nombre):
    """Devuelve 'Español (México)', 'Inglés (EE. UU.)', etc. None si es otro idioma."""
    if isinstance(codigo, bytes):
        codigo = codigo.decode('utf-8', 'ignore')
    codigo = re.sub(r'[^\w-]', '', str(codigo or '')).lower().replace('_', '-')
    nombre_min = nombre.lower()
    base = codigo.split('-')[0]
    if base == 'es' or 'spanish' in nombre_min or 'español' in nombre_min:
        idioma = "Español"
    elif base == 'en' or 'english' in nombre_min:
        idioma = "Inglés"
    else:
        return None
    region = codigo.split('-')[1] if '-' in codigo else ''
    if not region and 'mexico' in nombre_min:
        region = 'mx'
    if region in PAISES:
        idioma += f" ({PAISES[region]})"
    return idioma


def persona_de_voz(genero, nombre):
    """'Carolina' para voces femeninas, 'Flavio' para masculinas, None si no se sabe."""
    genero = (genero or '').lower()
    nombre_min = nombre.lower()
    if genero == 'female' or any(x in nombre_min for x in NOMBRES_FEMENINOS):
        return "Carolina"
    if genero == 'male' or any(x in nombre_min for x in NOMBRES_MASCULINOS):
        return "Flavio"
    return None


def nombre_corto(nombre):
    """'Microsoft Sabina Desktop - Spanish (Mexico)' -> 'Sabina'"""
    corto = nombre.split(' - ')[0].replace('Microsoft ', '').replace(' Desktop', '').strip()
    return corto or nombre


# --- Voces en línea ---
PREFIJO_EN_LINEA = "en_linea:"
VOCES_EN_LINEA = [
    ("Carolina · Español (México) – Dalia (en línea)", "es-MX-DaliaNeural"),
    ("Flavio · Español (México) – Jorge (en línea)", "es-MX-JorgeNeural"),
    ("Carolina · Inglés (EE. UU.) – Jenny (en línea)", "en-US-JennyNeural"),
    ("Flavio · Inglés (EE. UU.) – Guy (en línea)", "en-US-GuyNeural"),
]
# Respeta el proxy del sistema si existe (redes de escuela u oficina)
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or None


def hay_conexion():
    """Comprueba si el servidor de voces en línea responde."""
    async def _probar():
        await asyncio.wait_for(edge_tts.list_voices(proxy=PROXY), timeout=8)
    try:
        asyncio.run(_probar())
        return True
    except Exception:
        return False


def velocidad_a_porcentaje(velocidad):
    """El deslizador va de 80 a 300 (160 = normal). Las voces en línea usan porcentaje."""
    return f"{round((velocidad / 160 - 1) * 100):+d}%"


def sintetizar_en_linea(texto, voz, velocidad):
    """
    Genera el audio de un fragmento con una voz en línea.
    Devuelve (audio_mp3, palabras), donde palabras = [(milisegundo, palabra), ...].
    """
    async def _generar():
        comunicador = edge_tts.Communicate(texto, voz, rate=velocidad_a_porcentaje(velocidad),
                                           boundary="WordBoundary", proxy=PROXY,
                                           connect_timeout=8, receive_timeout=30)
        audio = bytearray()
        palabras = []
        async for parte in comunicador.stream():
            if parte["type"] == "audio":
                audio.extend(parte["data"])
            elif parte["type"] == "WordBoundary":
                # El tiempo viene en unidades de 100 nanosegundos
                palabras.append((parte["offset"] / 10000, parte["text"]))
        return bytes(audio), palabras
    return asyncio.run(_generar())


def dividir_en_fragmentos(texto, inicio, primero=300, resto=1500):
    """
    Divide el texto (desde 'inicio') en fragmentos que terminan en fin de oración o de línea.
    El primero es corto para que la lectura empiece rápido; mientras suena uno, se prepara el siguiente.
    Devuelve una lista de (inicio, fin).
    """
    fragmentos = []
    pos = inicio
    limite = primero
    while pos < len(texto):
        fin = min(pos + limite, len(texto))
        if fin < len(texto):
            corte = max(texto.rfind(sep, pos, fin) for sep in (". ", "? ", "! ", "\n", "; ", ": "))
            if corte <= pos:
                corte = texto.rfind(" ", pos, fin)
            if corte > pos:
                fin = corte + 1
        if any(c.isalnum() for c in texto[pos:fin]):
            fragmentos.append((pos, fin))
        pos = fin
        limite = resto
    return fragmentos


def ubicar_palabras(texto, inicio, fin, palabras):
    """Convierte [(ms, palabra)] en [(ms, posición, largo)] buscando cada palabra en el texto."""
    resultado = []
    cursor = inicio
    for ms, palabra in palabras:
        idx = texto.find(palabra, cursor, fin)
        if idx == -1:
            continue
        resultado.append((ms, idx, len(palabra)))
        cursor = idx + len(palabra)
    return resultado


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
        self.root.title("AudioTexto v3 - Carolina Edition")
        self.root.geometry("960x640")
        self.root.configure(bg=COLOR_FONDO)

        # Variables de control
        self.is_playing = False      # True mientras se está leyendo
        self.hilo_activo = False     # True hasta que el hilo de lectura termina por completo
        self.accion = None           # Qué pidió el usuario al cortar: 'pausa', 'detener' o 'reiniciar'
        self.pos_actual = 0          # Posición (en caracteres) de la palabra que se está leyendo
        self.voces_dict = {}
        self.aviso_voces = ""             # Aviso si no hay voces en español en la computadora
        self.voz_elegida_por_usuario = False

        self.crear_interfaz()
        self.cargar_voces()
        self._buscar_voces_en_linea()

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
        self.combo_voces = ttk.Combobox(top_frame, state="readonly", width=44, font=("Segoe UI", 10))
        self.combo_voces.pack(side=tk.LEFT, padx=5)
        # Si cambias de voz mientras lee, continúa con la nueva voz
        self.combo_voces.bind("<<ComboboxSelected>>", lambda e: self._al_elegir_voz())

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

        # --- Marco inferior (Estado y mensaje especial) ---
        bottom_frame = tk.Frame(self.root, bg=COLOR_FONDO)
        # Se coloca antes del área de texto para que siempre quede visible
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=5)

        lbl_dedicatoria = tk.Label(bottom_frame, text=".....",
                                   bg=COLOR_FONDO, fg="#ec4899", font=("Segoe UI", 10, "italic"))
        lbl_dedicatoria.pack(side=tk.RIGHT)

        lbl_autor = tk.Label(bottom_frame, text="By: Flavio and support of Opus",
                                   bg=COLOR_FONDO, fg="#64748b", font=("Segoe UI", 9))
        lbl_autor.pack(side=tk.LEFT)

        self.lbl_estado = tk.Label(bottom_frame, text="", bg=COLOR_FONDO, fg="#334155", font=("Segoe UI", 9))
        self.lbl_estado.pack(side=tk.LEFT, padx=20)

        # --- Área de Texto Principal ---
        text_frame = tk.Frame(self.root)
        text_frame.pack(expand=True, fill=tk.BOTH, padx=15, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(text_frame, wrap=tk.WORD, font=("Georgia", 13),
                                 yscrollcommand=scrollbar.set, relief="flat", padx=10, pady=10, height=10)
        self.text_area.pack(expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.text_area.yview)

        # Estilo para la palabra que se está leyendo
        self.text_area.tag_configure("leyendo", background="#fde68a", foreground="#1e293b")

    def _estado(self, texto):
        self.lbl_estado.config(text=texto)

    # ------------------------------------------------------------------
    # Voces
    # ------------------------------------------------------------------
    def cargar_voces(self):
        """
        Carga las voces y las nombra por género e idioma:
        Carolina (femeninas) y Flavio (masculinas), en español o inglés.
        """
        engine_temp = pyttsx3.init()
        candidatas = []
        for voz in engine_temp.getProperty('voices'):
            idiomas = getattr(voz, 'languages', None) or ['']
            candidatas.append({'id': voz.id, 'nombre': voz.name,
                               'genero': getattr(voz, 'gender', None), 'idioma': idiomas[0]})
        # En Windows, sumar las voces modernas (donde suelen estar las de español)
        candidatas += voces_onecore()

        orden_idioma = {"Español": 0, "Inglés": 1}
        orden_persona = {"Carolina": 0, "Flavio": 1}
        entradas = []
        vistas = set()
        for voz in candidatas:
            corto = nombre_corto(voz['nombre'])
            idioma = idioma_legible(voz['idioma'], voz['nombre'])
            persona = persona_de_voz(voz['genero'], voz['nombre'])

            if persona and idioma:
                nombre_mostrar = f"{persona} · {idioma} – {corto}"
            elif persona:
                nombre_mostrar = f"{persona} – {voz['nombre']}"
            else:
                nombre_mostrar = voz['nombre']

            # La misma voz puede aparecer en los dos lugares de Windows: dejar solo una
            if nombre_mostrar in vistas:
                continue
            vistas.add(nombre_mostrar)
            clave = (orden_idioma.get((idioma or '').split(' ')[0], 2), orden_persona.get(persona, 2), nombre_mostrar)
            entradas.append((clave, nombre_mostrar, voz['id']))

        for _, nombre_mostrar, voz_id in sorted(entradas):
            self.voces_dict[nombre_mostrar] = voz_id
        self.combo_voces['values'] = list(self.voces_dict.keys())

        # Por defecto: Carolina en español; si no hay, cualquier Carolina; si no, la primera
        nombres = list(self.voces_dict.keys())
        preferida = (next((n for n in nombres if n.startswith("Carolina · Español")), None)
                     or next((n for n in nombres if n.startswith("Carolina")), None)
                     or (nombres[0] if nombres else None))
        if preferida:
            self.combo_voces.set(preferida)

        if not any("· Español" in n for n in nombres):
            if sys.platform == 'win32':
                self.aviso_voces = "No hay voces en español en Windows (Configuración → Hora e idioma → Voz → Agregar voces)."
            else:
                self.aviso_voces = "No se encontraron voces en español en este equipo."
        self._estado(self.aviso_voces)

    def _al_elegir_voz(self):
        self.voz_elegida_por_usuario = True
        self._reiniciar_si_lee()

    def _buscar_voces_en_linea(self):
        """Revisa en segundo plano si hay internet para agregar las voces en línea."""
        if not EN_LINEA_LIBRERIAS:
            self._estado("Para voces en línea instala: pip install edge-tts pygame-ce")
            return
        self._estado("Buscando voces en línea...")

        def _revisar():
            conectado = hay_conexion()
            try:
                self.root.after(0, self._al_revisar_conexion, conectado)
            except RuntimeError:
                pass  # La ventana ya se cerró
        threading.Thread(target=_revisar, daemon=True).start()

    def _al_revisar_conexion(self, conectado):
        if conectado:
            # Voces en línea arriba, las de la computadora debajo
            voces = {nombre: PREFIJO_EN_LINEA + voz for nombre, voz in VOCES_EN_LINEA}
            voces.update(self.voces_dict)
            self.voces_dict = voces
            self.combo_voces['values'] = list(voces.keys())
            if not self.voz_elegida_por_usuario and not self.hilo_activo:
                self.combo_voces.set(VOCES_EN_LINEA[0][0])
            mensaje = "Voces en línea disponibles."
        else:
            mensaje = f"Sin conexión: se usan las voces de la computadora. {self.aviso_voces}".strip()
        if not self.hilo_activo:
            self._estado(mensaje)

    def _voz_de_respaldo(self, voz_id):
        """Busca una voz de la computadora parecida (misma persona e idioma) a la voz en línea."""
        nombre_en_linea = next((n for n, v in self.voces_dict.items() if v == voz_id), "")
        locales = [(n, v) for n, v in self.voces_dict.items() if not v.startswith(PREFIJO_EN_LINEA)]
        if not locales:
            return None
        persona = nombre_en_linea.split(" · ")[0]
        idioma = nombre_en_linea.split(" · ")[1].split(" ")[0] if " · " in nombre_en_linea else ""
        for prefijo in (f"{persona} · {idioma}", persona, ""):
            for n, v in locales:
                if n.startswith(prefijo):
                    return n, v
        return None

    def _usar_respaldo(self, nombre):
        self.combo_voces.set(nombre)
        self._estado("No se pudo usar la voz en línea (¿sin internet?). Se usa una voz de la computadora.")

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
        threading.Thread(target=self._bucle_lectura,
                         args=(voz_id, velocidad, texto, inicio), daemon=True).start()

    def _bucle_lectura(self, voz_id, velocidad, texto, inicio):
        """
        Hilo de lectura. Usa la voz en línea si se eligió una; si falla (por ejemplo,
        sin internet), sigue leyendo desde la misma palabra con una voz de la computadora.
        """
        # Requerido en Windows para inicializar COM en un hilo secundario de forma segura
        if sys.platform == 'win32':
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pass

        try:
            if voz_id and voz_id.startswith(PREFIJO_EN_LINEA):
                try:
                    self._leer_en_linea(voz_id[len(PREFIJO_EN_LINEA):], velocidad, texto, inicio)
                    return
                except Exception as e:
                    print("No se pudo usar la voz en línea:", e)
                    if not self.is_playing:
                        return
                    respaldo = self._voz_de_respaldo(voz_id)
                    if not respaldo:
                        raise
                    nombre, voz_id = respaldo
                    self.root.after(0, self._usar_respaldo, nombre)
                    inicio = self.pos_actual
            self._leer_con_voz_local(voz_id, velocidad, texto, inicio)

        except Exception as e:
            print("Error en el motor de voz:", e)

        finally:
            if sys.platform == 'win32':
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except ImportError:
                    pass

            self.root.after(0, self._al_terminar)

    def _leer_en_linea(self, voz, velocidad, texto, inicio):
        """
        Lee con una voz en línea, fragmento por fragmento.
        Mientras suena un fragmento, el siguiente se descarga en segundo plano.
        """
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        fragmentos = dividir_en_fragmentos(texto, inicio)
        if not fragmentos:
            return
        descargas = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            a, b = fragmentos[0]
            siguiente = descargas.submit(sintetizar_en_linea, texto[a:b], voz, velocidad)
            for i, (a, b) in enumerate(fragmentos):
                self.pos_actual = a
                # Esperar el audio, pero sin dejar de atender Pausar/Detener
                while True:
                    if not self.is_playing:
                        return
                    try:
                        audio, palabras = siguiente.result(timeout=0.1)
                        break
                    except concurrent.futures.TimeoutError:
                        continue
                if i + 1 < len(fragmentos):
                    a2, b2 = fragmentos[i + 1]
                    siguiente = descargas.submit(sintetizar_en_linea, texto[a2:b2], voz, velocidad)
                self._reproducir(audio, ubicar_palabras(texto, a, b, palabras))
                if not self.is_playing:
                    return
        finally:
            descargas.shutdown(wait=False, cancel_futures=True)

    def _reproducir(self, audio, marcas):
        """Reproduce un fragmento y resalta cada palabra en su momento."""
        pygame.mixer.music.load(io.BytesIO(audio), "mp3")
        pygame.mixer.music.play()
        siguiente_marca = 0
        try:
            while pygame.mixer.music.get_busy():
                if not self.is_playing:
                    return
                ms = pygame.mixer.music.get_pos()
                while siguiente_marca < len(marcas) and marcas[siguiente_marca][0] <= ms:
                    _, posicion, largo = marcas[siguiente_marca]
                    siguiente_marca += 1
                    self.pos_actual = posicion
                    self.root.after(0, self._resaltar, posicion, largo)
                time.sleep(0.03)
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

    def _leer_con_voz_local(self, voz_id, velocidad, texto, inicio):
        """
        Lee con una voz de la computadora, de corrido para evitar bloqueos en los puntos finales.
        Usa un evento interno del motor para resaltar cada palabra y para
        abortar cuando presionas Pausar o Detener.
        """
        engine = pyttsx3.init()
        token = None
        try:
            if voz_id:
                try:
                    asignar_voz(engine, voz_id)
                except Exception as e:
                    print("No se pudo usar la voz elegida:", e)
                    self.root.after(0, self._estado, "No se pudo usar esa voz; se usa la predeterminada.")
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
        finally:
            if token is not None:
                try:
                    engine.disconnect(token)
                except Exception:
                    pass

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
