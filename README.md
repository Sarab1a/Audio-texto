# AudioTexto v2

Lector de texto en voz alta. Abre archivos PDF o TXT (o pega tu propio texto) y el programa lo lee con las voces instaladas en tu computadora.

![Demostración de AudioTexto](Foto%20de%20demostraci%C3%B3n..png)

## Funciones

- **Abrir PDF y TXT**, o pegar texto directamente en la ventana.
- **Leer, pausar y reanudar**: al pausar, la lectura continúa desde la misma palabra. "Detener" regresa al inicio.
- **Leer desde cualquier punto**: haz clic en el texto y presiona "Leer".
- **Control de velocidad**: deslizador de 80 a 300. Puedes cambiarlo mientras lee.
- **Selección de voz**: las voces femeninas aparecen como "Carolina" y las masculinas como "Flavio".
- **Resaltado**: la palabra que se está leyendo se marca en amarillo y la vista la sigue.
- **PDF escaneados (OCR)**: reconoce el texto de páginas que son imágenes (requiere instalación adicional, ver abajo).
- Omite los enlaces web para no leerlos.

## Requisitos

- Python 3.
- Windows, macOS o Linux. Android e iOS aún no tienen soporte; espero agregarlo en la v3.

## Instalación

1. Descarga los archivos en una carpeta.
2. Abre tu terminal (CMD en Windows) o Visual Studio Code.
3. Instala las dependencias con este comando:

   ```
   pip install pyttsx3 PyPDF2 pywin32
   ```

   En macOS y Linux no hace falta `pywin32`:

   ```
   pip install pyttsx3 PyPDF2
   ```

4. **Solo Linux:** instala el motor de voz y el reproductor de audio:

   ```
   sudo apt install espeak-ng alsa-utils
   ```

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
