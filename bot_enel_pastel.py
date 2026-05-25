import telebot
import pymysql
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# PAUSAR BOT
if os.getenv("BOT_PAUSADO") == "true":
    print("Bot pausado")
    sys.exit()

TOKEN = os.getenv("telegram_token_enel_consultas_bot")

bot = telebot.TeleBot(TOKEN)

# CONTROL ANTI SPAM
ultimo_uso = {}

# FUNCIÓN CONEXIÓN MYSQL
def obtener_conexion():

    return pymysql.connect(
        host=os.getenv("host_enel"),
        user=os.getenv("user_enel"),
        password=os.getenv("password_enel"),
        database=os.getenv("db_enel"),
        port=int(os.getenv("port_enel")),
        connect_timeout=10
    )

@bot.message_handler(commands=['start'])
def inicio(message):
    texto = """
Buen día 👋
Bot de consultas Enel

Comandos disponibles:
/orden número_orden

Ejemplo:
/orden 1994287

Consulta el último estado de una orden.
"""
    bot.reply_to(message, texto)

# COMANDO /orden
@bot.message_handler(commands=['orden'])
def buscar_cliente(message):

    conexion = None
    cursor = None

    try:
        user_id = message.from_user.id
        ahora = time.time()

        # ANTI SPAM
        if user_id in ultimo_uso:
            diferencia = ahora - ultimo_uso[user_id]
            if diferencia < 2:
                bot.reply_to(
                    message,
                    "Espera 2 segundos entre consultas"
                )
                return

        ultimo_uso[user_id] = ahora
        # VALIDAR PARÁMETRO
        partes = message.text.split()
        if len(partes) < 2:
            bot.reply_to(
                message,
                "Uso correcto:\n/orden 1994287"
            )
            return
        orden = partes[1]

        # NUEVA CONEXIÓN MYSQL
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        sql = """
        SELECT 
            ORDEN,
            ROTULO,
            ESTADO,
            FECHA_ESTADO,
            LOCALIDAD,
            TIPO_MOVIL
        FROM vw_ordenes
        WHERE ORDEN = %s
        ORDER BY FECHA_ESTADO DESC
        LIMIT 1
        """
        sql_baremos = """
        SELECT 
            Id_Item_3,
            Cantidad_Instalada,
            Descripción
        FROM vw_baremos
        WHERE orden = %s
        """

        cursor.execute(sql, (orden,))
        resultado = cursor.fetchone()
        
        cursor.execute(sql_baremos, (orden,))
        resultado_baremos = cursor.fetchall()

        # RESPUESTA
        if resultado:

            ORDEN, ROTULO, ESTADO, FECHA_ESTADO, LOCALIDAD, TIPO_MOVIL = resultado

            respuesta = f"""
        Orden: {ORDEN}
        Rotulo: {ROTULO}
        Estado: {ESTADO}
        Fecha estado: {FECHA_ESTADO}
        Localidad: {LOCALIDAD}
        Tipo móvil: {TIPO_MOVIL}

        Baremos:
        """
            if resultado_baremos:
                for fila in resultado_baremos:
                    item, cantidad, descripcion = fila
                    respuesta += (
                        f"\n• {item}"
                        f"\nCantidad: {cantidad}"
                        f"\n{descripcion}\n"
                    )
            else:
                respuesta += "\nNo se encontraron baremos"
        else:
            respuesta = "Orden no encontrada"
        bot.reply_to(message, respuesta)
    except pymysql.MySQLError as e:
        bot.reply_to(
            message,
            f"Error de base de datos:\n{e}"
        )
    except Exception as e:
        bot.reply_to(
            message,
            f"Error:\n{e}"
        )

    finally:
        # CERRAR CONEXIONES
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

# INICIAR BOT
print("Bot iniciado...")

while True:
    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60
        )
    except Exception as e:
        print(f"Error polling: {e}")
        time.sleep(5)