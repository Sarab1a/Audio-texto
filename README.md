# AudioTexto v3

Lector de texto en voz alta. Abre archivos PDF o TXT (o pega tu propio texto) y el programa lo lee en español o en inglés, con voces en línea o con las voces instaladas en tu computadora.

![Demostración de AudioTexto](Foto%20de%20demostraci%C3%B3n..png)

## Funciones

- **Abrir PDF y TXT**, o pegar texto directamente en la ventana.
- **Voces en español e inglés**: las voces femeninas aparecen como "Carolina" y las masculinas como "Flavio", con su idioma.
- **Voces en línea (con internet)**: voces naturales disponibles en cualquier computadora, sin instalar nada en Windows:
  - Carolina · Español (México) – Dalia
  - Flavio · Español (México) – Jorge
  - Carolina · Inglés (EE. UU.) – Jenny
  - Flavio · Inglés (EE. UU.) – Guy
- **Respaldo sin internet**: si no hay conexión, se usan las voces de tu computadora. Si el internet se corta mientras lee, cambia sola a una voz de la computadora y sigue desde la misma palabra.
- **Leer, pausar y reanudar**: al pausar, la lectura continúa desde la misma palabra. "Detener" regresa al inicio.
- **Leer desde cualquier punto**: haz clic en el texto y presiona "Leer".
- **Control de velocidad**: deslizador de 80 a 300. Puedes cambiarlo mientras lee.
- **Resaltado**: la palabra que se está leyendo se marca en amarillo y la vista la sigue.
- **PDF escaneados (OCR)**: reconoce el texto de páginas que son imágenes (requiere instalación adicional, ver abajo).
- **Mensajes de estado** en la parte inferior: conexión, lectura, pausa, etc.
- Omite los enlaces web para no leerlos.

## Requisitos

- Python 3.
- Windows, macOS o Linux. Android e iOS aún no tienen soporte; espero agregarlo en una próxima versión.
- Conexión a internet para las voces en línea (sin internet funciona con las voces de la computadora).

## Instalación

1. Descarga los archivos en una carpeta.
2. Abre tu terminal (CMD en Windows) o Visual Studio Code.
3. Instala las dependencias con este comando:

   ```
   pip install pyttsx3 PyPDF2 pywin32 edge-tts pygame-ce
   ```

   En macOS y Linux no hace falta `pywin32`:

   ```
   pip install pyttsx3 PyPDF2 edge-tts pygame-ce
   ```

4. **Solo Linux:** instala el motor de voz y el reproductor de audio:

   ```
   sudo apt install espeak-ng alsa-utils
   ```

### Opcional: voces en español sin internet (Windows)

Las voces en línea ya incluyen español. Si también quieres voces en español cuando no hay internet, instálalas en Windows:

1. Abre **Configuración → Hora e idioma → Voz**.
2. En **Administrar voces**, da clic en **Agregar voces**.
3. Elige **Español (México)** y da clic en **Agregar**.

Al abrir AudioTexto de nuevo aparecerán en la lista (por ejemplo, Carolina · Español (México) – Sabina).

### Opcional: leer PDF escaneados (OCR)

Sin esto el programa funciona igual; solo no podrá leer páginas escaneadas.

1. Instala las librerías:

   ```
   pip install pymupdf pytesseract
   ```

2. Instala el programa **Tesseract-OCR** con el idioma **español**:
   - Windows: descarga el instalador de Tesseract y, durante la instalación, marca el idioma "Spanish".
   - macOS: `brew install tesseract tesseract-lang`
   - Linux: `sudo apt install tesseract-ocr tesseract-ocr-spa`

## Uso

Ejecuta el programa con:

```
python audio_lector.py
```

**Nota:** en la terminal, primero ubícate en la carpeta donde está el archivo `.py`. Por ejemplo:

```
cd C:\Users\TuUsuario\Descargas\Audio-texto
```

Al abrir, el programa revisa la conexión en unos segundos. Si hay internet, las voces en línea aparecen al inicio de la lista y se selecciona Carolina en español.

## Problemas comunes

- **"Python was not found"**: Python no está instalado o no está en el PATH. Descárgalo de python.org y, en el instalador, marca **"Add python.exe to PATH"**. También puedes probar con `py audio_lector.py`.
- **No aparecen las voces en línea**: revisa tu conexión a internet y que hayas instalado `edge-tts` y `pygame-ce`. La parte inferior de la ventana indica qué ocurre.
- **Solo hay voces en inglés sin internet**: instala las voces en español de Windows (ver "Voces en español sin internet").
