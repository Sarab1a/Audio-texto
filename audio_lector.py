# AudioTexto: v1 - 15/02/26
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
import re
import sys

class AudioTextoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AudioTexto v2 - Carolina Edition")
        self.root.geometry("750x550")
        self.root.configure(bg="#f8fafc")
        
        # Variables de control
        self.is_playing = False
        self.texto_completo = ""
        self.voces_dict = {}
        
        self.crear_interfaz()
        self.cargar_voces()

    def crear_interfaz(self):
        # --- Marco superior (Controles) ---
        top_frame = tk.Frame(self.root, pady=10, bg="#f8fafc")
        top_frame.pack(fill=tk.X, padx=15)

        # Botón Cargar
        btn_cargar = tk.Button(top_frame, text="📁 Abrir Archivo (PDF/TXT)", command=self.cargar_archivo, 
                               bg="#6366f1", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=10)
        btn_cargar.pack(side=tk.LEFT, padx=5)

        # Selector de Voz
        tk.Label(top_frame, text="Voz:", bg="#f8fafc", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        self.combo_voces = ttk.Combobox(top_frame, state="readonly", width=35, font=("Segoe UI", 10))
        self.combo_voces.pack(side=tk.LEFT, padx=5)
        
        # Botones de Reproducción
        self.btn_play = tk.Button(top_frame, text="▶ Leer", command=self.iniciar_lectura, 
                                  bg="#10b981", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=8)
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(top_frame, text="■ Detener", command=self.detener_lectura, 
                                  bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=8)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # --- Área de Texto Principal ---
        text_frame = tk.Frame(self.root)
        text_frame.pack(expand=True, fill=tk.BOTH, padx=15, pady=5)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_area = tk.Text(text_frame, wrap=tk.WORD, font=("Georgia", 13), 
                                 yscrollcommand=scrollbar.set, relief="flat", padx=10, pady=10)
        self.text_area.pack(expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.text_area.yview)

        # --- Marco inferior (Mensaje especial) ---
        bottom_frame = tk.Frame(self.root, bg="#f8fafc")
        bottom_frame.pack(fill=tk.X, padx=15, pady=5)
        
        lbl_dedicatoria = tk.Label(bottom_frame, text="Creado con amor para Carolina ❤️", 
                                   bg="#f8fafc", fg="#ec4899", font=("Segoe UI", 10, "italic"))
        lbl_dedicatoria.pack(side=tk.RIGHT)
        
        lbl_autor = tk.Label(bottom_frame, text="Atte: Flavio", 
                                   bg="#f8fafc", fg="#64748b", font=("Segoe UI", 9))
        lbl_autor.pack(side=tk.LEFT)

    def cargar_voces(self):
        """Carga las voces y renombra las femeninas a Carolina y masculinas a Flavio"""
        engine_temp = pyttsx3.init()
        voces = engine_temp.getProperty('voices')
        
        for voz in voces:
            nombre_original = voz.name
            nombre_mostrar = nombre_original
            
            # Detectar si es voz femenina para llamarla Carolina
            if any(x in nombre_original.lower() for x in ['zira', 'helena', 'sabina', 'female', 'mujer']):
                nombre_mostrar = f"Carolina ({nombre_original})"
            # Detectar si es voz masculina para llamarla Flavio
            elif any(x in nombre_original.lower() for x in ['david', 'pablo', 'male', 'hombre']):
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

    def cargar_archivo(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Archivos de Texto y PDF", "*.txt *.pdf"), ("Todos los archivos", "*.*")]
        )
        if not filepath:
            return

        self.detener_lectura()
        self.text_area.delete(1.0, tk.END)

        try:
            if filepath.lower().endswith('.pdf'):
                # Extraer texto de PDF
                with open(filepath, 'rb') as file:
                    lector_pdf = PyPDF2.PdfReader(file)
                    texto_completo = ""
                    for pagina in lector_pdf.pages:
                        if pagina.extract_text():
                            texto_completo += pagina.extract_text() + "\n\n"
                self.text_area.insert(tk.END, texto_completo)
            else:
                # Extraer texto de TXT (Manejo robusto de errores de codificación de Windows)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        texto = file.read()
                except UnicodeDecodeError:
                    # Si falla el utf-8, intentamos con la codificación estándar de Windows
                    with open(filepath, 'r', encoding='cp1252') as file:
                        texto = file.read()
                
                self.text_area.insert(tk.END, texto)
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{str(e)}")

    def iniciar_lectura(self):
        if self.is_playing:
            return

        texto_crudo = self.text_area.get(1.0, tk.END).strip()
        if not texto_crudo:
            messagebox.showwarning("Aviso", "No hay texto para leer.")
            return

        # Limpiar enlaces (URLs) para que no los lea
        self.texto_completo = re.sub(r'http\S+|www.\S+', '', texto_crudo)

        self.is_playing = True
        self.btn_play.config(state=tk.DISABLED, bg="#94a3b8") 
        
        nombre_voz = self.combo_voces.get()
        voz_id = self.voces_dict.get(nombre_voz)

        # Iniciar hilo de lectura
        threading.Thread(target=self._bucle_lectura_fluido, args=(voz_id,), daemon=True).start()

    def _bucle_lectura_fluido(self, voz_id):
        """
        Lee el texto de corrido para evitar bloqueos en los puntos finales.
        Usa un evento interno del motor para abortar cuando presionas Detener.
        """
        # Requerido en Windows para inicializar COM en un hilo secundario de forma segura
        if sys.platform == 'win32':
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pass 
        
        try:
            engine = pyttsx3.init()
            if voz_id:
                engine.setProperty('voice', voz_id)
            engine.setProperty('rate', 160)

            # Este "sensor" se activa antes de que el motor diga cada palabra.
            # Si detecta que apretaste "Detener" (is_playing = False), aborta el motor.
            def on_word(name, location, length):
                if not self.is_playing:
                    engine.stop()

            engine.connect('started-word', on_word)
            
            # Le pasamos TODO el texto de un golpe. Así lee sin pausas raras.
            engine.say(self.texto_completo)
            engine.runAndWait()
            
        except Exception as e:
            print("Error en el motor de voz:", e)
            
        finally:
            self.is_playing = False
            
            if sys.platform == 'win32':
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except ImportError:
                    pass

            # Reactivar el botón Play al terminar
            self.root.after(0, lambda: self.btn_play.config(state=tk.NORMAL, bg="#10b981"))

    def detener_lectura(self):
        # Al cambiar esto a False, el "sensor" en _bucle_lectura_fluido detendrá el audio.
        self.is_playing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioTextoApp(root)
    root.mainloop()