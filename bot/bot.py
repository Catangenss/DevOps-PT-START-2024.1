import logging
import re
import paramiko
import os
import psycopg2
import subprocess
from psycopg2 import Error
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

# Подключаем логирование
logging.basicConfig(filename='PT_tgbot.txt', level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s', encoding="utf-8")
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv('TOKEN')
host = os.getenv('RM_HOST')
port = os.getenv('RM_PORT')
username = os.getenv('RM_USER')
password = os.getenv('RM_PASSWORD')
host_db = os.getenv('DB_HOST')
username_db = os.getenv('DB_USER')
password_db = os.getenv('DB_PASSWORD')
port_db = os.getenv('DB_PORT')
database = os.getenv('DB_DATABASE')


def connect_postgres(update: Update, context, table):
    try:
        connection = psycopg2.connect(user=username_db,
                                      password=password_db,
                                      host=host_db,
                                      port=port_db,
                                      database=database)

        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {table};")
        data = cursor.fetchall()

        # Собираем все строки в одну строку
        result_str = "\n".join(" \t ".join(str(item) for item in row) for row in data)

        update.message.reply_text(result_str)  # Отправляем все строки одним сообщением в Telegram
        logging.info("Команда успешно выполнена")
    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')

def helpCommand(update: Update, context):
    update.message.reply_text('Help!')

def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    return 'findPhoneNumbers'


def findPhoneNumbers(update, context):
    user_input = update.message.text  # Получаем текст, содержащий(или нет) номера телефонов

    # Паттерны для каждого из форматов номеров телефонов
    patterns = [
        r'(?:\+7|8)(\d{3})(\d{3})(\d{2})(\d{2})',  # +7XXXXXXXXXX, 8XXXXXXXXXX
        r'(?:\+7|8)\s(\d{3})\s(\d{3})\s(\d{2})\s(\d{2})',  # +7 XXX XXX XX XX, 8 XXX XXX XX XX
        r'(?:\+7|8)\s\((\d{3})\)\s(\d{3})\s(\d{2})\s(\d{2})',  # +7 (XXX) XXX XX XX, 8 (XXX) XXX XX XX
        r'(?:\+7|8)-(\d{3})-(\d{3})-(\d{2})-(\d{2})',  # +7-XXX-XXX-XX-XX, 8-XXX-XXX-XX-XX
        r'(?:\+7|8)\((\d{3})\)(\d{3})(\d{2})(\d{2})'  # +7(XXX)XXXXXXX
    ]

    phone_numbers = {}  # Создаем словарь для хранения номеров телефонов и их позиций в тексте

    # Проверяем каждый паттерн
    for pattern in patterns:
        phoneNumRegex = re.compile(pattern)
        matches = phoneNumRegex.finditer(user_input)
        for match in matches:
            phone_number = f"+7 ({match.group(1)}) {match.group(2)} {match.group(3)} {match.group(4)}"
            phone_numbers[match.start()] = phone_number  # Сохраняем номер телефона и его позицию в тексте

    # Сортируем номера телефонов по их позиции в тексте
    sorted_phone_numbers = [phone_numbers[pos] for pos in sorted(phone_numbers.keys())]

    if not sorted_phone_numbers:  # Обрабатываем случай, когда номеров телефонов нет
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phoneNumbers = ''  # Создаем строку, в которую будем записывать номера телефонов
    for i, phone_number in enumerate(sorted_phone_numbers):
        phoneNumbers += f'{i + 1}. {phone_number}\n'  # Записываем очередной номер
    context.user_data['phone_numbers'] = sorted_phone_numbers
    question_message = 'Хотите добавить номера телефонов в базу данных? (да/нет)'
    update.message.reply_text(f"{phoneNumbers}\n{question_message}")

    return 'confirm_to_add_phone'

def confirmAddInDB_phone(update, context):
    user_reply = update.message.text.lower()
    phone_numbers = context.user_data.get('phone_numbers')
    if user_reply == 'да' and phone_numbers:
        # Запрашиваем у пользователя имя контакта для каждого номера телефона
        context.user_data['contacts'] = {}
#        for i, phone_number in enumerate(phone_numbers):
        update.message.reply_text(f"Введите имя контакта для телефона {phone_numbers[0]}:")
        return 'get_contact_name_phone'
    else:
        update.message.reply_text("Номера не добавлены в базу данных.")
        return ConversationHandler.END

def getContactName_phone(update, context):
    phone_numbers = context.user_data.get('phone_numbers')
    phone_number = phone_numbers.pop(0)
    contact_name = update.message.text
    context.user_data['contacts'][phone_number] = contact_name
    # Если есть еще номера телефонов, запрашиваем следующее имя контакта
    if phone_numbers:
        update.message.reply_text(f"Введите имя контакта для телефона {phone_numbers[0]}:")
        return 'get_contact_name_phone'
    else:
        # Если больше нет номеров телефонов, вызываем функцию add_in_db
        add_in_db(update, context, context.user_data['contacts'], 'tel_numbers')
        return ConversationHandler.END

def add_in_db(update, context, data, table):
    try:
        connection = psycopg2.connect(user=username_db,
                                      password=password_db,
                                      host=host_db,
                                      port=port_db,
                                      database=database)
        cursor = connection.cursor()
        for key, value in data.items():
            if table == 'tel_numbers':
                cursor.execute(f"INSERT INTO tel_numbers (username, tel_number) VALUES (%s, %s);", (value, key))
            elif table == 'emails':
                cursor.execute(f"INSERT INTO emails (username, email) VALUES (%s, %s);", (value, key))
        connection.commit()
        update.message.reply_text(f'Контакты записаны в базу данных {table}')
        logging.info("Команда успешно выполнена")
    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

def findEmailsCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска E-mail адресов: ')
    return 'findEmails'

def findEmails(update: Update, context):
    user_input = update.message.text  # Получаем текст

    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    email_List = email_pattern.findall(user_input)

    if not email_List:
        update.message.reply_text('Email адреса не найдены')
        return

    emails = ''
    for i in range(len(email_List)):
        emails += f'{i + 1}. {email_List[i]}\n'  # Записываем очередной номер

    context.user_data['emails'] = email_List
    question_message = 'Хотите добавить адреса email в базу данных? (да/нет)'
    update.message.reply_text(f"{emails}\n{question_message}")
    return 'confirm_to_add_email'

def confirmAddInDB_email(update, context):
    user_reply = update.message.text.lower()
    email_list = context.user_data.get('emails')
    if user_reply == 'да' and email_list:
        # Запрашиваем у пользователя имя контакта для каждого адреса email
        context.user_data['contacts'] = {}
        for i, email in enumerate(email_list):
            update.message.reply_text(f"Введите имя контакта для адерса {email}:")
            return 'get_contact_name_email'
    else:
        update.message.reply_text("Адреса email не добавлены в базу данных.")
        return ConversationHandler.END

def getContactName_email(update, context):
    email_list = context.user_data.get('emails')
    email = email_list.pop(0)
    contact_name = update.message.text
    context.user_data['contacts'][email] = contact_name
    # Если есть еще адреса, запрашиваем следующее имя контакта
    if email_list:
        update.message.reply_text(f"Введите имя контакта для адерса {email_list[0]}:")
        return 'get_contact_name_email'
    else:
        # Если больше нет номеров телефонов, вызываем функцию add_in_db
        add_in_db(update, context, context.user_data['contacts'], 'emails')
        return ConversationHandler.END

def verifyPasswordCommand(update: Update, context):
    update.message.reply_text('Введите пароль: ')
    return 'verifyPassword'

def verifyPassword(update: Update, context):
    user_input = update.message.text  # Получаем текст
    if not user_input:
        update.message.reply_text('Пароль пустой')
        return
    if len(user_input.split()) > 1:
        update.message.reply_text('Введено больше одного пароля')
        return

    hardpassword_pattern = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$')

    hardpassword_List = hardpassword_pattern.findall(user_input)

    if len(hardpassword_List) == 0 :
        update.message.reply_text('Пароль простой')
    elif len(hardpassword_List) == 1 :
        update.message.reply_text('Пароль сложный')
    return ConversationHandler.END  # Завершаем работу обработчика диалога

def command(update: Update, context, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, port=port)
    stdin, stdout, stderr = client.exec_command(command)
    data = stdout.read() + stderr.read()
    client.close()
    packages = data.decode('utf-8').split('\n')
    current_chunk = ""

    for package in packages:
        if len(current_chunk + package + "\n") > 4096:  # Проверяем, не превышает ли текущая часть максимальный размер сообщения
            update.message.reply_text(current_chunk)  # Отправляем текущий чанк
            current_chunk = ""  # Обнуляем текущий кусок для следующей порции
        current_chunk += package + "\n"

    # Отправляем чанк, если он не пустой
    if current_chunk:
        update.message.reply_text(current_chunk)

def command_replica(update: Update, context):
    command = "grep -E -i 'replica|checkpoint' /var/log/postgresql/postgresql-16-main.log | tail -n 20"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        update.message.reply_text("Ошибка при выполнении команды: " + error.decode())
    else:
        update.message.reply_text(output.decode())

def AptList_request(update: Update, context):
    update.message.reply_text('Введите название пакета или "all", если хотите вывести все пакеты')
    return 'AptList_response'

def AptList_response(update: Update, context):
    user_input = update.message.text  # Получаем текст
    com = user_input.split()
    if com[0] == "all" and len(com) == 1:
        command(update, context, "apt list --installed")
    elif len(com) == 1:
        command(update, context, f"apt show {com[0]}")
    else:
        update.message.reply_text('Неверный ввод')
    return ConversationHandler.END
# Следует добавить проверку корректности ввода пакета и наличия пакета на машине

def Service_request(update: Update, context):
    update.message.reply_text('Введите название службы')
    return 'Service_response'

def Service_response(update: Update, context):
    user_input = update.message.text  # Получаем текст
    service = user_input.split()
    if len(service) == 1:
        command(update, context, f"systemctl status {service[0]}")
    else:
        update.message.reply_text('Неверный ввод')
    return ConversationHandler.END

def echo(update: Update, context):
    update.message.reply_text(update.message.text)

def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'confirm_to_add_phone': [MessageHandler(Filters.text & ~Filters.command, confirmAddInDB_phone)],
            'get_contact_name_phone': [MessageHandler(Filters.text & ~Filters.command, getContactName_phone)]
        },
        fallbacks=[]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailsCommand)],
        states={
            'findEmails': [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            'confirm_to_add_email': [MessageHandler(Filters.text & ~Filters.command, confirmAddInDB_email)],
            'get_contact_name_email': [MessageHandler(Filters.text & ~Filters.command, getContactName_email)]
        },
        fallbacks=[]
    )

    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            'verifyPassword': [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[]
    )

    convHandlerAptList = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', AptList_request)],
        states={
            'AptList_response': [MessageHandler(Filters.text & ~Filters.command, AptList_response)],
        },
        fallbacks=[]
    )

    convHandlerServices = ConversationHandler(
        entry_points=[CommandHandler('get_services', Service_request)],
        states={
            'Service_response': [MessageHandler(Filters.text & ~Filters.command, Service_response)],
        },
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmails)
    dp.add_handler(convHandlerVerifyPassword)
    dp.add_handler(convHandlerAptList)
    dp.add_handler(convHandlerServices)
    dp.add_handler(CommandHandler('get_uname', lambda update, context: command(update, context, "uname -a")))
    dp.add_handler(CommandHandler('get_release', lambda update, context: command(update, context, "lsb_release -a")))
    dp.add_handler(CommandHandler('get_uptime', lambda update, context: command(update, context, "uptime")))
    dp.add_handler(CommandHandler('get_df', lambda update, context: command(update, context, "df -h")))
    dp.add_handler(CommandHandler('get_free', lambda update, context: command(update, context, "free -h")))
    dp.add_handler(CommandHandler('get_mpstat', lambda update, context: command(update, context, "mpstat")))
    dp.add_handler(CommandHandler('get_w', lambda update, context: command(update, context, "w")))
    dp.add_handler(CommandHandler('get_auths', lambda update, context: command(update, context, "last -10")))
    dp.add_handler(CommandHandler('get_critical', lambda update, context: command(update, context, "journalctl -r -p crit -n 5")))
    dp.add_handler(CommandHandler('get_ps', lambda update, context: command(update, context, "ps aux")))
    dp.add_handler(CommandHandler('get_ss', lambda update, context: command(update, context, "ss -tuln")))
    dp.add_handler(CommandHandler('get_repl_logs', command_replica))
    dp.add_handler(CommandHandler('get_emails', lambda update, context: connect_postgres(update, context, "emails")))
    dp.add_handler(CommandHandler('get_phone_numbers', lambda update, context: connect_postgres(update, context, "tel_numbers")))

    # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Запускаем бота
    updater.start_polling()

    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()