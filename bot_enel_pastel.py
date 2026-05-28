import telebot
import pymysql
import time
import os
import sys
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# PAUSAR BOT
if os.getenv("BOT_PAUSADO") == "true":
    print("Bot pausado")
    sys.exit()

TOKEN = os.getenv("telegram_token_enel_consultas_bot")

bot = telebot.TeleBot(TOKEN)

# COMANDOS DEL BOT (Menus persistente)
bot.set_my_commands([
    telebot.types.BotCommand("start", "Iniciar bot"),
    telebot.types.BotCommand("menu", "Mostrar menú") 
])

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

# MENU PRINCIPAL
def mostrar_menu(chat_id):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
        one_time_keyboard=False,
        selective=False
    )

    btn_orden = types.KeyboardButton("📌 Consultar Orden")
    btn_rotulo = types.KeyboardButton("🏷️ Consultar Rótulo")

    markup.add(btn_orden, btn_rotulo)

    bot.send_message(
        chat_id,
        "📝 Selecciona una opción en el menú en el borde inferior de su pantalla (Tambien puede acceder a el desde ☰):",
        reply_markup=markup
    )


@bot.message_handler(commands=['start'])
def inicio(message):

    nombre = message.from_user.first_name
    username = message.from_user.username

    if username:
        saludo = f"{nombre} (@{username})"
    else:
        saludo = nombre

    texto = f"""
Buen día {saludo} 👋

Soy tu asistente de consultas 🦜

Puedo ayudarte a consultar:

📌 Órdenes
🏷️ Rótulos

Selecciona una opción del menú 👇
"""

    bot.send_message(
        message.chat.id,
        texto
    )

    mostrar_menu(message.chat.id)




# =========================================
# PROCESAR ORDEN MENU
# =========================================
def procesar_orden_menu(message):

    orden = message.text

    # SIMULAR COMANDO
    message.text = f"/orden {orden}"

    buscar_cliente(message)


# =========================================
# PROCESAR ROTULO MENU
# =========================================
def procesar_rotulo_menu(message):

    rotulo = message.text

    # SIMULAR COMANDO
    message.text = f"/rotulo {rotulo}"

    buscar_rotulo(message)

#-------------------------------------------------------
#Comandos
#-------------------------------------------------------
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
            amap,
            Item
        FROM vw_baremos
        WHERE orden = %s
        """
        sql_material = """
        SELECT 
            Id_Item_3,
            Cantidad_Instalada,
            Item
        FROM vw_material_instalado
        WHERE orden = %s
        AND Id_Item_3 <> 0
        """

        cursor.execute(sql, (orden,))
        resultado = cursor.fetchone()
        
        cursor.execute(sql_baremos, (orden,))
        resultado_baremos = cursor.fetchall()

        cursor.execute(sql_material, (orden,))
        resultado_material = cursor.fetchall()

        # RESPUESTA
        if resultado:

            ORDEN, ROTULO, ESTADO, FECHA_ESTADO, LOCALIDAD, TIPO_MOVIL = resultado

            respuesta = (
                f"📌 <b>Orden:</b> {ORDEN}\n"
                f"🏷️ <b>Rotulo:</b> {ROTULO}\n"
                f"📄 <b>Estado:</b> {ESTADO}\n"
                f"📅 <b>Fecha estado:</b> {FECHA_ESTADO}\n"
                f"📍 <b>Localidad:</b> {LOCALIDAD}\n"
                f"🚛 <b>Tipo móvil:</b> {TIPO_MOVIL}\n\n"
            )

            if resultado_baremos:
                respuesta += "📋 <b>Baremos:</b>\n"
                for fila in resultado_baremos:
                    item, cantidad, amap, Item = fila
                    respuesta += (
                        f"\n• <b>Item:</b> {item} - {Item}"
                        f"\n• <b>Cantidad:</b> {cantidad}"
                        f"\n• <b>Amap:</b> {amap}\n"
                    )
            else:
                respuesta += "\n<b>Baremos:</b> Sin baremos"

            if resultado_material:
                respuesta += "\n💡 <b>Material:</b>\n"
                for fila in resultado_material:
                    item, cantidad, Item = fila
                    respuesta += (
                        f"\n• <b>Item</b> {item} - {Item}"
                        f"\n• <b>Cantidad:</b> {cantidad}\n"
                    )
            else:
                respuesta += "\n<b>Material:</b> Sin material"
        else:
            respuesta = "Favor validar con centro de control"
        bot.reply_to(message, respuesta, parse_mode='HTML')
        mostrar_menu(message.chat.id)
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

# COMANDO /rotulo
@bot.message_handler(commands=['rotulo'])
def buscar_rotulo(message):

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
                "Uso correcto:\n/rotulo ABC123"
            )
            return

        rotulo = partes[1]

        # CONEXIÓN
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # TODAS LAS ÓRDENES DEL RÓTULO
        sql_ordenes = """
        SELECT DISTINCT ORDEN
        FROM vw_ordenes
        WHERE ROTULO = %s
        """

        cursor.execute(sql_ordenes, (rotulo,))
        ordenes = cursor.fetchall()

        if not ordenes:
            bot.reply_to(
                message,
                "Favor validar con centro de control"
            )
            return
        
        cantidad_ordenes = len(ordenes)

        respuesta = (
            f"Aquí tienes información del rotulo:\n"
            f"\n🔎 <b>Rótulo:</b> {rotulo}\n"
            f"🚐 <b>Atenciones registradas:</b> {cantidad_ordenes}\n"
        )
        # CONSULTAS
        sql_detalle = """
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
            amap,
            Item
        FROM vw_baremos
        WHERE orden = %s
        """

        sql_material = """
        SELECT 
            Id_Item_3,
            Cantidad_Instalada,
            Item
        FROM vw_material_instalado
        WHERE orden = %s
        AND Id_Item_3 <> 0
        """

        # RECORRER ÓRDENES
        for fila_orden in ordenes:

            orden = fila_orden[0]

            # DETALLE
            cursor.execute(sql_detalle, (orden,))
            resultado = cursor.fetchone()

            if not resultado:
                continue

            ORDEN, ROTULO, ESTADO, FECHA_ESTADO, LOCALIDAD, TIPO_MOVIL = resultado
            respuesta += (
                f"\n\n\n"
                f"📌 <b>Orden:</b> {ORDEN}\n"
                f"\n"
                f"📄 <b>Estado:</b> {ESTADO}\n"
                f"📅 <b>Fecha:</b> {FECHA_ESTADO}\n"
                f"📍 <b>Localidad:</b> {LOCALIDAD}\n"
                f"🚛 <b>Tipo móvil:</b> {TIPO_MOVIL}\n\n"
            )
            
            # BAREMOS
            cursor.execute(sql_baremos, (orden,))
            resultado_baremos = cursor.fetchall()

            if resultado_baremos:

                respuesta += "📋 <b>Baremos:</b>\n"
                for fila in resultado_baremos:

                    item, cantidad, amap, Item = fila

                    respuesta += (
                        f"\n• <b>Item:</b> {item} - {Item}"
                        f"\n• <b>Amap:</b> {amap}"
                        f"\n• <b>Cantidad:</b> {cantidad}\n"
                    )

            else:
                respuesta += "📋 <b>Baremos:</b> Sin baremos\n"

            # MATERIAL
            cursor.execute(sql_material, (orden,))
            resultado_material = cursor.fetchall()

            if resultado_material:

                respuesta += "\n💡 <b>Material:</b>\n"
                for fila in resultado_material:

                    item, cantidad, Item = fila

                    respuesta += (
                        f"\n• <b>Item:</b> {item} - {Item}"
                        f"\n• <b>Cantidad:</b>  {cantidad}\n"
                    )

            else:
                respuesta += "\n💡 <b>Material:</b> Sin material\n"

        bot.reply_to(message, respuesta, parse_mode='HTML')
        mostrar_menu(message.chat.id)

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

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

# =========================================
# MENU INTERACTIVO
# =========================================
@bot.message_handler(func=lambda message: True)
def menu_botones(message):

    texto = message.text

    # CONSULTAR ORDEN
    if texto == "📌 Consultar Orden":

        msg = bot.send_message(
            message.chat.id,
            "Escribe el número de orden:"
        )

        bot.register_next_step_handler(
            msg,
            procesar_orden_menu
        )

    # CONSULTAR ROTULO
    elif texto == "🏷️ Consultar Rótulo":

        msg = bot.send_message(
            message.chat.id,
            "Escribe el número de rótulo:"
        )

        bot.register_next_step_handler(
            msg,
            procesar_rotulo_menu
        )

    # MENU
    elif texto == "🏠 Menú":

        mostrar_menu(message.chat.id)

    # CUALQUIER OTRO MENSAJE
    else:

        bot.send_message(
            message.chat.id,
            "📋 Menú principal"
        )

        mostrar_menu(message.chat.id)

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