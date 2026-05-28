import telebot
import pymysql
import hashlib
import os

from dotenv import load_dotenv

# ======================================
# VARIABLES ENTORNO
# ======================================

load_dotenv()

TOKEN = os.getenv("telegram_token_enel_consultas_bot")


import hashlib
print(hashlib.sha256("1234567".encode()).hexdigest())
# ======================================
# BOT
# ======================================

bot = telebot.TeleBot(TOKEN)

# ======================================
# CONEXION MYSQL
# ======================================

conexion = pymysql.connect(
    host=os.getenv("host_railway"),
    user=os.getenv("user_railway"),
    password=os.getenv("password_railway"),
    database=os.getenv("db_railway_aplicativos"),
    port=int(os.getenv("port_railway")),
    autocommit=True
)

# ======================================
# FUNCION AUTENTICACION
# ======================================

def obtener_usuario(chat_id):

    cursor = conexion.cursor(pymysql.cursors.DictCursor)

    sql = """
    SELECT *
    FROM usuarios
    WHERE telegram_chat_id = %s
    AND autorizado = 1
    """

    cursor.execute(sql, (chat_id,))

    return cursor.fetchone()

# ======================================
# START
# ======================================

@bot.message_handler(commands=['start'])
def start(message):

    usuario = obtener_usuario(message.chat.id)

    if usuario:

        texto = f"""
✅ Ya tienes sesión iniciada

👤 {usuario['nombre']}
🧑 Usuario: {usuario['usuario']}
        """

    else:

        texto = """
👋 Bienvenido

Debes iniciar sesión:

/login usuario contraseña
        """

    bot.reply_to(message, texto)

# ======================================
# LOGIN
# ======================================

@bot.message_handler(commands=['login'])
def login(message):

    try:

        partes = message.text.split()

        if len(partes) != 3:

            bot.reply_to(
                message,
                "❌ Uso correcto:\n/login usuario contraseña"
            )
            return

        usuario_input = partes[1]
        password_input = partes[2]

        password_hash = hashlib.sha256(
            password_input.encode()
        ).hexdigest()

        cursor = conexion.cursor(
            pymysql.cursors.DictCursor
        )

        sql = """
        SELECT *
        FROM usuarios
        WHERE usuario = %s
        AND password = %s
        AND autorizado = 1
        """

        cursor.execute(
            sql,
            (
                usuario_input,
                password_hash
            )
        )

        usuario = cursor.fetchone()

        if usuario:

            # Guardar chat_id persistente

            sql_update = """
            UPDATE usuarios
            SET telegram_chat_id = %s,
                fecha_login = NOW()
            WHERE id = %s
            """

            cursor.execute(
                sql_update,
                (
                    message.chat.id,
                    usuario["id"]
                )
            )

            respuesta = f"""
✅ Login exitoso

👤 Nombre: {usuario['nombre']}
🧑 Usuario: {usuario['usuario']}
            """

            bot.reply_to(message, respuesta)

        else:

            bot.reply_to(
                message,
                "❌ Usuario o contraseña incorrectos"
            )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Error:\n{e}"
        )

# ======================================
# LOGOUT
# ======================================

@bot.message_handler(commands=['logout'])
def logout(message):

    cursor = conexion.cursor()

    sql = """
    UPDATE usuarios
    SET telegram_chat_id = NULL
    WHERE telegram_chat_id = %s
    """

    cursor.execute(
        sql,
        (message.chat.id,)
    )

    bot.reply_to(
        message,
        "✅ Sesión cerrada con exito"
    )

# ======================================
# COMANDO PROTEGIDO
# ======================================

@bot.message_handler(commands=['orden'])
def orden(message):

    usuario = obtener_usuario(message.chat.id)

    if not usuario:

        bot.reply_to(
            message,
            "🔒 Debes iniciar sesión"
        )
        return

    respuesta = f"""
✅ Acceso autorizado

👤 {usuario['nombre']}
📦 Consultando órdenes...
    """

    bot.reply_to(message, respuesta)

# ======================================
# BOT
# ======================================

print("BOT INICIADO...")

bot.infinity_polling()