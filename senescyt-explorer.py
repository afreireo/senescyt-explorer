from playwright.sync_api import sync_playwright
from pytesseract import image_to_string
from PIL import Image, ImageFilter
import csv
import os
from time import sleep

def preprocesar_imagen(captcha_path, output_path="captcha_preprocesado.png"):
    """
    Preprocesa la imagen del CAPTCHA: escala de grises, mejora del enfoque y umbral binario.
    """
    imagen = Image.open(captcha_path).convert("L")  # Convertir a escala de grises
    imagen = imagen.filter(ImageFilter.SHARPEN)  # Mejorar el enfoque
    umbral = 128
    imagen = imagen.point(lambda x: 255 if x > umbral else 0)  # Umbral binario
    imagen.save(output_path)
    return output_path

def resolver_captcha(captcha_path):
    """
    Resuelve el CAPTCHA utilizando Tesseract OCR.
    """
    return image_to_string(
        Image.open(captcha_path),
        config="--psm 7 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyz"
    ).strip()

def es_texto_valido(texto):
    """
    Valida si el texto extraído cumple con los requisitos (4 caracteres alfanuméricos).
    """
    return len(texto) == 4 and texto.isalnum()

def verificar_resultado(page):
    """
    Verifica si la respuesta del formulario indica:
    - CAPTCHA incorrecto.
    - Cédula inválida.
    - Resultados disponibles.
    """
    try:
        # Buscar mensajes de error
        mensaje_error = page.locator('div#formPrincipal\\:messages div.ui-messages-error').inner_text(timeout=2000)
        if "Caracteres incorrectos" in mensaje_error:
            print("CAPTCHA incorrecto.")
            return "CAPTCHA_INCORRECTO"
        elif "No se encontraron resultados" in mensaje_error:
            print("Cédula no válida.")
            return "CEDULA_INVALIDA"
    except:
        pass

    try:
        # Verificar si la tabla de resultados está presente
        if page.locator("table[id^='formPrincipal:j_idt']").count() > 0:
            print("Cédula válida: resultados encontrados.")
            return "RESULTADO_OK"
    except:
        pass

    print("No se encontraron resultados para la cédula.")
    return "CEDULA_INVALIDA"

def extraer_informacion(page):
    """
    Extrae la información de todas las tablas de resultados que contengan las columnas específicas
    y devuelve los datos en formato de lista.
    """
    columnas_requeridas = [
        "Título", "Institución de Educación Superior", "Tipo",
        "Reconocido Por", "Número de Registro", "Fecha de Registro",
        "Área o Campo de Conocimiento", "Observación"
    ]
    resultados = []

    try:
        # Buscar todas las tablas de resultados en la página
        tablas = page.locator("table").all()
        
        for tabla in tablas:
            # Obtener los encabezados de la tabla
            encabezados = [th.inner_text().strip() for th in tabla.locator("th").all()]
            
            # Validar si la tabla contiene las columnas requeridas
            if all(col in encabezados for col in columnas_requeridas):
                # Extraer filas de la tabla
                filas = tabla.locator("tbody tr").all()
                for fila in filas:
                    celdas = [td.inner_text().strip() for td in fila.locator("td").all()]
                    resultados.append(celdas)
        
        print(f"\nInformación extraída:")
        for a,b in zip(columnas_requeridas, resultados[0]):
            print(f"{a}: {b}")

    except Exception as e:
        print(f"Error al extraer información: {e}")

    return resultados  # Devolver la lista de resultados

def intentar_resolver_captcha(page, cedula, captcha_selector):
    """
    Intenta resolver el CAPTCHA indefinidamente hasta que lo logre,
    asegurándose de que cada CAPTCHA sea diferente.
    """
    intento = 1
    captcha_anterior = None  # Para guardar la imagen del CAPTCHA anterior

    while True:
        print(f"Intento {intento} para resolver el CAPTCHA.")
        
        # Volver a llenar el campo de cédula
        page.fill('input#formPrincipal\\:identificacion', cedula)

        # Capturar la imagen del CAPTCHA
        captcha_path = f"captcha_intento_{intento}.png"
        page.locator(captcha_selector).screenshot(path=captcha_path)

        # Leer la nueva imagen y compararla con la anterior
        with open(captcha_path, "rb") as f:
            captcha_actual = f.read()

        if captcha_anterior == captcha_actual:
            print("El CAPTCHA no se actualizó. Recargando página...")
            page.reload()
            sleep(2)  # Dar tiempo para recargar la página
            continue
        else:
            captcha_anterior = captcha_actual

        # Preprocesar y resolver el CAPTCHA
        captcha_preprocesado = preprocesar_imagen(captcha_path)
        texto_captcha = resolver_captcha(captcha_preprocesado)
        print(f"Texto extraído: {texto_captcha}")

        # Eliminar la imagen después de resolver
        if os.path.exists(captcha_path):
            os.remove(captcha_path)
        if os.path.exists(captcha_preprocesado):
            os.remove(captcha_preprocesado)

        if es_texto_valido(texto_captcha):
            # Ingresar el texto en el formulario
            page.fill('input#formPrincipal\\:captchaSellerInput', texto_captcha)
            page.click('button#formPrincipal\\:boton-buscar')

            # Verificar el resultado
            resultado = verificar_resultado(page)
            if resultado == "RESULTADO_OK":
                print("CAPTCHA resuelto correctamente.")
                return True
            elif resultado == "CAPTCHA_INCORRECTO":
                print("CAPTCHA incorrecto, intentando con uno nuevo.")
            elif resultado == "CEDULA_INVALIDA":
                print("Cédula no válida.")
                return False
        else:
            print("Texto extraído no válido, intentando con un nuevo CAPTCHA.")
        
        # Incrementar el contador de intentos
        intento += 1

def llenar_formulario(cedula):
    """
    Automatiza el llenado del formulario con Playwright y guarda los resultados.
    """
    with sync_playwright() as p:
        # Inicia el navegador
        browser = p.chromium.launch(headless=True)  # Cambia a False para ver el navegador
        page = browser.new_page()

        # Navega a la página
        page.goto("https://www.senescyt.gob.ec/consulta-titulos-web/faces/vista/consulta/consulta.xhtml")

        # Resolver el CAPTCHA con intentos
        captcha_selector = 'img#formPrincipal\\:capimg'
        if not intentar_resolver_captcha(page, cedula, captcha_selector):
            print(f"No se pudo resolver el CAPTCHA para la cédula {cedula}.")
            browser.close()
            return

        # Extraer información
        informacion = extraer_informacion(page)
        if not informacion:
            print(f"No se encontró información para la cédula {cedula}.")

        browser.close()

def procesar_cedula():
    cedula = input("Ingrese cedula: ")
    llenar_formulario(cedula)

if __name__ == "__main__":
    # Procesar cédulas desde un archivo CSV
    procesar_cedula()
