import telebot
import pymysql
import time
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("telegram_token_enel_consultas_bot")
bot = telebot.TeleBot(TOKEN)

conexion = pymysql.connect(
    host=os.getenv("host_enel"),
    user=os.getenv("user_enel"),
    password=os.getenv("password_enel"),
    database=os.getenv("db_enel"),
    port=int(os.getenv("port_enel"))
)

ultimo_uso = {}

@bot.message_handler(commands=['orden'])
def buscar_cliente(message):

    try:

        user_id = message.from_user.id
        ahora = time.time()

        # Anti spam
        if user_id in ultimo_uso:

            diferencia = ahora - ultimo_uso[user_id]

            if diferencia < 2:

                bot.reply_to(
                    message,
                    "Espera 2 segundos entre consultas"
                )

                return

        ultimo_uso[user_id] = ahora

        # Validar parámetro
        partes = message.text.split()

        if len(partes) < 2:

            bot.reply_to(
                message,
                "Uso correcto:\n/orden 1994287"
            )

            return

        orden = partes[1]

        cursor = conexion.cursor()

        sql = """
        SELECT ORDEN, ESTADO, FECHA_ESTADO, LOCALIDAD, TIPO_MOVIL
        FROM vw_ordenes
        WHERE ORDEN = %s
        ORDER BY FECHA_ESTADO DESC
        LIMIT 1
        """

        cursor.execute(sql, (orden,))

        resultado = cursor.fetchone()

        cursor.close()

        if resultado:

            ORDEN, ESTADO, FECHA_ESTADO, LOCALIDAD, TIPO_MOVIL = resultado

            respuesta = f"""
Orden: {ORDEN}
Estado: {ESTADO}
Fecha estado: {FECHA_ESTADO}
Localidad: {LOCALIDAD}
Tipo móvil: {TIPO_MOVIL}
"""

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

print("Bot iniciado...")

while True:
    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60
        )
    except Exception as e:
        print(e)
        time.sleep(5)