import uuid # Para generar identificadores únicos de solicitud.
import io # Para trabajar con streams de bytes y texto en memoria.
import pandas as pd # Para la manipulación y exportación de datos a formatos como Excel y CSV.
import matplotlib # Librería para la creación de gráficos.
matplotlib.use('Agg') # Configura Matplotlib para trabajar en entornos sin interfaz gráfica.
import matplotlib.pyplot as plt # Módulo de Matplotlib para la creación de gráficos.
import base64 # Para codificar imágenes a Base64 y mostrarlas en HTML.
from flask import Flask, render_template, request, send_file, flash, redirect, url_for # Clases y funciones de Flask para la aplicación web.
import logging # Para el manejo de logs.
import os # Para acceder a variables de entorno.
import threading # Para la limpieza de datos temporales en segundo plano.
import time # Para pausas en el hilo de limpieza.

# Importa los módulos personalizados que contienen la lógica de negocio.
from generadores import GeneradorExponencial, GeneradorUniforme, GeneradorPoisson, GeneradorNormal
from prueba_chi_cuadrado import PruebaChiCuadrado
from prueba_ks import PruebaKS # Importar la clase PruebaKS
from distribuciones import Uniforme, Normal, Exponencial, Poisson

app = Flask(__name__) # Inicializa la aplicación Flask.

# --- Configuración para Producción ---
# La clave secreta es esencial para la seguridad de las sesiones de Flask (por ejemplo, para flash messages).
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'una_clave_secreta_muy_segura_y_aleatoria_para_desarrollo')

# Configuración de logging para producción.
# Se recomienda enviar logs a un sistema centralizado como ELK Stack, Splunk, CloudWatch, etc.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Almacenamiento temporal para los números generados.
# En un entorno de producción con múltiples instancias o procesos, esto debería ser una base de datos (Redis, PostgreSQL)
# o un sistema de almacenamiento de archivos con un mecanismo de expiración.
# Para esta optimización, se implementa una limpieza básica en memoria.
temp_data_store = {}
DATA_EXPIRATION_TIME = 3600 # 1 hora en segundos para que los datos temporales expiren.

# --- Constantes para validación de entrada ---
MIN_CANTIDAD = 1
MAX_CANTIDAD = 50000
MIN_DECIMALES = 0 # Permitir 0 decimales para números enteros
MAX_DECIMALES = 16
MIN_CONFIANZA = 1.0
MAX_CONFIANZA = 99.95
MIN_INTERVALOS_HISTOGRAMA = 1

# Función para limpiar datos temporales antiguos.
def cleanup_temp_data():
    """Elimina datos antiguos del almacenamiento temporal."""
    while True:
        current_time = time.time()
        keys_to_delete = [
            request_id for request_id, data in temp_data_store.items()
            if current_time - data['timestamp'] > DATA_EXPIRATION_TIME
        ]
        for key in keys_to_delete:
            del temp_data_store[key]
            logging.info(f"Datos temporales para request_id {key} eliminados.")
        time.sleep(300) # Ejecuta la limpieza cada 5 minutos.

# Inicia el hilo de limpieza al iniciar la aplicación.
cleanup_thread = threading.Thread(target=cleanup_temp_data, daemon=True)
cleanup_thread.start()

# Función auxiliar para validar y convertir una cadena a un entero dentro de un rango.
def obtener_entero_entre(valor_str, min_val, max_val):
    try:
        valor = int(valor_str)
        if min_val <= valor <= max_val:
            return valor
        else:
            return None # Retorna None si el valor está fuera del rango.
    except (ValueError, TypeError):
        return None # Retorna None si la conversión falla.

# Función auxiliar para validar y convertir una cadena a un número flotante.
def obtener_float(valor_str):
    try:
        valor = float(valor_str)
        return valor
    except (ValueError, TypeError):
        return None # Retorna None si la conversión falla.

@app.route('/')
def index():
    # Renderiza la plantilla principal (formulario de entrada).
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Obtiene el tipo de distribución y la cantidad de números desde el formulario.
    distribution_type = request.form.get('distribution_type')
    cantidad = obtener_entero_entre(request.form.get('cantidad'), MIN_CANTIDAD, MAX_CANTIDAD)
    
    # Valida la cantidad de números.
    if cantidad is None:
        flash("Cantidad inválida. Por favor, ingrese un número entero entre 1 y 50000.", 'danger')
        logging.warning(f"Intento de generación con cantidad inválida: {request.form.get('cantidad')}")
        return redirect(url_for('index'))

    # Obtiene y valida la cantidad de decimales para truncar.
    decimales_truncar_str = request.form.get('decimales_truncar', '2') 
    decimales_truncar = obtener_entero_entre(decimales_truncar_str, MIN_DECIMALES, MAX_DECIMALES)
    if decimales_truncar is None:
        flash("Cantidad de decimales inválida. Por favor, ingrese un número entero entre 0 y 16.", 'danger')
        logging.warning(f"Intento de generación con decimales_truncar inválidos: {decimales_truncar_str}")
        return redirect(url_for('index'))

    numeros = []
    distribution = None
    nombre_distribucion = ""
    error_message = None

    # Lógica para generar números según el tipo de distribución seleccionada.
    if distribution_type == 'uniforme':
        a = obtener_float(request.form.get('uniforme_a'))
        b = obtener_float(request.form.get('uniforme_b'))
        if a is None or b is None or b <= a:
            error_message = "Parámetros de la distribución Uniforme inválidos. 'b' debe ser mayor que 'a'."
        else:
            generador = GeneradorUniforme(a, b)
            numeros = generador.generar_numeros(cantidad)
            distribution = Uniforme(a, b)
            nombre_distribucion = f"U({a:.2f}, {b:.2f})"

    elif distribution_type == 'exponencial':
        media = obtener_float(request.form.get('exponencial_media'))
        if media is None or media <= 0:
            error_message = "Media de la distribución Exponencial inválida. Debe ser un valor positivo."
        else:
            generador = GeneradorExponencial(media)
            numeros = generador.generar_numeros(cantidad)
            distribution = Exponencial(media)
            nombre_distribucion = f"Exp({media:.2f})"

    elif distribution_type == 'normal':
        media = obtener_float(request.form.get('normal_media'))
        desviacion_estandar = obtener_float(request.form.get('normal_desviacion'))
        if media is None or desviacion_estandar is None or desviacion_estandar <= 0:
            error_message = "Parámetros de la distribución Normal inválidos. La desviación estándar debe ser positiva."
        else:
            generador = GeneradorNormal(media, desviacion_estandar)
            numeros = generador.generar_numeros(cantidad)
            distribution = Normal(media, desviacion_estandar)
            nombre_distribucion = f"N({media:.2f}, {desviacion_estandar:.2f})"

    elif distribution_type == 'poisson':
        media = obtener_float(request.form.get('poisson_media'))
        if media is None or media <= 0:
            error_message = "Media de la distribución Poisson inválida. Debe ser un valor positivo."
        else:
            generador = GeneradorPoisson(media)
            numeros = generador.generar_numeros(cantidad)
            distribution = Poisson(media)
            nombre_distribucion = f"P({media:.2f})"
    else:
        error_message = "Tipo de distribución no válido."

    # Si hay un error en los parámetros, vuelve a la página inicial con el mensaje de error.
    if error_message:
        flash(error_message, 'danger')
        logging.warning(f"Error en parámetros de distribución para {distribution_type}: {error_message}")
        return redirect(url_for('index'))

    # Preparación y ejecución de las Pruebas.
    confianza_str = request.form.get('confianza')
    intervalo_prueba_str = request.form.get('intervalo_prueba') 
    intervalo_grafico_str = request.form.get('intervalo_grafico')

    confianza = obtener_float(confianza_str)
    intervalo_grafico = obtener_entero_entre(intervalo_grafico_str, MIN_INTERVALOS_HISTOGRAMA, cantidad)

    # Validación de parámetros para la prueba y el histograma.
    if confianza is None or not (MIN_CONFIANZA <= confianza <= MAX_CONFIANZA):
        flash(f"Nivel de confianza inválido. Por favor, ingrese un número entre {MIN_CONFIANZA} y {MAX_CONFIANZA}.", 'danger')
        logging.warning(f"Nivel de confianza inválido: {confianza_str}")
        return redirect(url_for('index'))
    if intervalo_grafico is None:
        flash("Cantidad de intervalos para el histograma inválida. Debe ser un número entero positivo.", 'danger')
        logging.warning(f"Cantidad de intervalos para histograma inválida: {intervalo_grafico_str}")
        return redirect(url_for('index'))

    intervalo_prueba = None
    es_poisson = isinstance(distribution, Poisson) # Verifica si la distribución es Poisson (discreta).
    # Flags para controlar la visibilidad de la prueba KS en el template
    es_uniforme = isinstance(distribution, Uniforme)
    es_normal = isinstance(distribution, Normal)
    es_exponencial = isinstance(distribution, Exponencial)

    # Configura el número de intervalos para la prueba de Chi-Cuadrado (opcional para continuas).
    if not es_poisson and intervalo_prueba_str:
        intervalo_prueba_usuario = obtener_entero_entre(intervalo_prueba_str, 1, cantidad)
        if intervalo_prueba_usuario is None:
            flash("Cantidad de intervalos para la prueba de Chi Cuadrado inválida. Debe ser un número entero positivo.", 'danger')
            logging.warning(f"Cantidad de intervalos para Chi Cuadrado inválida: {intervalo_prueba_str}")
            return redirect(url_for('index'))
        intervalo_prueba = intervalo_prueba_usuario
    
    # --- Prueba de Kolmogorov-Smirnov (KS) ---
    prueba_ks_result = None
    tabla_data_ks = []
    if not es_poisson: # La prueba KS no se aplica a la distribución de Poisson
        try:
            prueba_ks = PruebaKS(distribution, confianza)
            prueba_ks_result = prueba_ks.realizar_prueba(numeros, cant_intervalos=intervalo_prueba)

            if prueba_ks_result and "intervalos" in prueba_ks_result:
                ultimo_intervalo_ks = list(prueba_ks_result['intervalos'].keys())[-1] if prueba_ks_result['intervalos'] else None
                for intervalo, datos in prueba_ks_result['intervalos'].items():
                    if isinstance(intervalo, (int, str)):
                        etiqueta_intervalo_ks = str(intervalo)
                    else:
                        lim_inf_ks = f"{intervalo[0]:.{decimales_truncar}f}" if isinstance(intervalo[0], float) else str(intervalo[0])
                        lim_sup_ks = f"{intervalo[1]:.{decimales_truncar}f}" if isinstance(intervalo[1], float) else str(intervalo[1])
                        if intervalo == ultimo_intervalo_ks:
                            etiqueta_intervalo_ks = f"[{lim_inf_ks}, {lim_sup_ks}]"
                        else:
                            etiqueta_intervalo_ks = f"[{lim_inf_ks}, {lim_sup_ks})"
                    
                    tabla_data_ks.append({
                        'intervalo': etiqueta_intervalo_ks,
                        'fo': f"{datos['frecuencia_observada']:.2f}", 
                        'fe': f"{datos['frecuencia_esperada']:.2f}",
                        'for': f"{datos['frecuencia_observada_relativa']:.4f}", # Formato a 4 decimales
                        'fer': f"{datos['frecuencia_esperada_relativa']:.4f}", # Formato a 4 decimales
                        'estadistico_ks': f"{datos['estadistico_ks']:.4f}" # Formato a 4 decimales
                    })
        except Exception as e:
            logging.error(f"Error al realizar la prueba KS: {e}")
            flash("Ocurrió un error al calcular la prueba de Kolmogorov-Smirnov.", 'danger')
            prueba_ks_result = None # Asegura que no se muestre información parcial o incorrecta

    # --- Prueba de Chi-Cuadrado ---
    prueba_chi = PruebaChiCuadrado(distribution, confianza)
    resultado_prueba_chi = None
    tabla_data_chi = []

    try:
        # Realiza la prueba de Chi-Cuadrado según si la distribución es discreta o continua.
        if es_poisson:
            resultado_prueba_chi = prueba_chi.realizar_prueba_discreta_poisson(numeros, cant_intervalos=intervalo_prueba)
        else:
            resultado_prueba_chi = prueba_chi.realizar_prueba(numeros, cant_intervalos=intervalo_prueba)

        # Prepara los datos para mostrar en la tabla HTML de resultados de la prueba de Chi-Cuadrado.
        if resultado_prueba_chi and "intervalos" in resultado_prueba_chi:
            ultimo_intervalo_chi = list(resultado_prueba_chi['intervalos'].keys())[-1] if resultado_prueba_chi['intervalos'] else None
            for intervalo, datos in resultado_prueba_chi['intervalos'].items():
                if isinstance(intervalo, (int, str)):
                    etiqueta_intervalo_chi = str(intervalo)
                else:
                    # Formatea los límites del intervalo según la cantidad de decimales especificada por el usuario.
                    lim_inf_chi = f"{intervalo[0]:.{decimales_truncar}f}" if isinstance(intervalo[0], float) else str(intervalo[0])
                    lim_sup_chi = f"{intervalo[1]:.{decimales_truncar}f}" if isinstance(intervalo[1], float) else str(intervalo[1])
                    if intervalo == ultimo_intervalo_chi:
                        etiqueta_intervalo_chi = f"[{lim_inf_chi}, {lim_sup_chi}]"
                    else:
                        etiqueta_intervalo_chi = f"[{lim_inf_chi}, {lim_sup_chi})"
                
                tabla_data_chi.append({
                    'intervalo': etiqueta_intervalo_chi,
                    'fo': f"{datos['frecuencia_observada']:.2f}", 
                    'fe': f"{datos['frecuencia_esperada']:.2f}",
                    'chi_cuadrado_intervalo': f"{datos['estadistico_chi_cuadrado']:.2f}"
                })
    except Exception as e:
        logging.error(f"Error al realizar la prueba Chi-Cuadrado: {e}")
        flash("Ocurrió un error al calcular la prueba de Chi-Cuadrado.", 'danger')
        resultado_prueba_chi = None # Asegura que no se muestre información parcial o incorrecta


    # Generación del Histograma.
    histogram_img = None
    if numeros:
        try:
            plt.figure(figsize=(10, 6))
            # Crea el histograma con el color especificado
            n, bins, patches = plt.hist(numeros, bins=intervalo_grafico, rwidth=1, edgecolor='black', alpha=0.7, color='#0a58ca')
            plt.title('Distribución de Frecuencias')
            plt.xlabel('Valores')
            plt.ylabel('Frecuencia')

            # Muestra las marcas de los límites de los intervalos en el eje X.
            plt.xticks(bins)

            plt.grid(axis='y', linestyle='--', alpha=0.6)
            plt.tight_layout()

            # Guarda el gráfico en un buffer en memoria con mayor DPI
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=500) # Aumenta el DPI para mejor calidad
            img_buffer.seek(0)
            histogram_img = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            plt.close() # Cierra el gráfico para liberar memoria.
        except Exception as e:
            logging.error(f"Error al generar el histograma: {e}")
            flash("Ocurrió un error al generar el histograma.", 'danger')
            histogram_img = None

    # Almacena los números generados y la preferencia de decimales temporalmente para futuras descargas.
    request_id = str(uuid.uuid4()) # Genera un ID único para esta solicitud.
    temp_data_store[request_id] = {
        'numbers': numeros,
        'decimales': decimales_truncar,
        'timestamp': time.time() # Registra el tiempo para la limpieza.
    }

    # Formatea y selecciona los primeros 100 números para mostrar en la página.
    display_numbers = [f"{num:.{decimales_truncar}f}" if isinstance(num, float) else str(num) for num in numeros[:100]]
    
    # Renderiza la plantilla de resultados con todos los datos procesados.
    return render_template('results.html',
                           numeros=display_numbers,
                           request_id=request_id, # Pasa el ID de la solicitud para las descargas.
                           nombre_distribucion=nombre_distribucion,
                           resultado_prueba_chi=resultado_prueba_chi, # Cambiado a resultado_prueba_chi
                           tabla_data_chi=tabla_data_chi, # Cambiado a tabla_data_chi
                           prueba_ks_result=prueba_ks_result, # Resultados de la prueba KS
                           tabla_data_ks=tabla_data_ks, # Datos de la tabla KS
                           histogram_img=histogram_img,
                           es_poisson=es_poisson,
                           es_uniforme=es_uniforme, # Pasa el flag para la visibilidad de KS
                           es_normal=es_normal,     # Pasa el flag para la visibilidad de KS
                           es_exponencial=es_exponencial) # Pasa el flag para la visibilidad de KS

@app.route('/download/<file_format>', methods=['POST'])
def download(file_format):
    # Obtiene el ID de la solicitud desde el formulario.
    request_id = request.form.get('request_id')
    # Verifica si el ID es válido y si los datos existen en el almacenamiento temporal.
    if not request_id or request_id not in temp_data_store:
        flash("No hay datos para descargar o la sesión ha expirado. Por favor, genere nuevos números.", 'warning')
        logging.warning(f"Intento de descarga de datos expirados o inexistentes para request_id: {request_id}")
        return redirect(url_for('index'))
    
    # Recupera los números y la preferencia de decimales.
    data = temp_data_store[request_id]
    numbers = data['numbers']
    decimales = data['decimales']

    # Formatea los números con la cantidad de decimales especificada antes de crear el DataFrame.
    # Se usa round() para asegurar que los flotantes tengan el número correcto de decimales
    # antes de ser convertidos a DataFrame.
    formatted_numbers_for_df = [round(num, decimales) if isinstance(num, float) else num for num in numbers]
    
    # Lógica para descargar el archivo en el formato solicitado.
    try:
        if file_format == 'csv':
            buffer = io.StringIO()
            pd.DataFrame(formatted_numbers_for_df, columns=['Numero Aleatorio']).to_csv(buffer, index=False)
            buffer.seek(0)
            return send_file(io.BytesIO(buffer.getvalue().encode('utf-8')),
                             mimetype='text/csv',
                             as_attachment=True,
                             download_name='numeros.csv')
        elif file_format == 'excel':
            buffer = io.BytesIO()
            # Exporta a Excel usando xlsxwriter como motor.
            pd.DataFrame(formatted_numbers_for_df, columns=['Numero Aleatorio']).to_excel(buffer, index=False, engine='xlsxwriter') 
            buffer.seek(0)
            return send_file(buffer,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             as_attachment=True,
                             download_name='numeros.xlsx')
        elif file_format == 'txt':
            # Formatea los números para un archivo de texto, uno por línea.
            txt_content = "\n".join([f"{num:.{decimales}f}" if isinstance(num, float) else str(num) for num in numbers])
            buffer = io.BytesIO(txt_content.encode('utf-8'))
            buffer.seek(0)
            return send_file(buffer,
                             mimetype='text/plain',
                             as_attachment=True,
                             download_name='numeros.txt')
        else:
            flash("Formato de archivo no soportado.", 'danger')
            logging.warning(f"Intento de descarga con formato no soportado: {file_format}")
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error al descargar el archivo {file_format}: {e}")
        flash("Ocurrió un error al intentar descargar el archivo.", 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Para producción, use un servidor WSGI como Gunicorn o uWSGI.
    # Ejemplo: gunicorn -w 4 app:app
    app.run(debug=False) # Nunca usar debug=True en producción.
    app.run(host='0.0.0.0', port=5000) # Escucha en todas las interfaces, puerto 5000.
