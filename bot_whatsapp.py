import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# Configuração do logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Carregar variáveis de ambiente do arquivo .env (opcional)
load_dotenv()

# Obter credenciais e tokens das variáveis de ambiente
EMAIL = os.getenv('EMAIL_CONTROL_SERVICES')
PASSWORD = os.getenv('PASSWORD_CONTROL_SERVICES')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Verificar se as variáveis de ambiente estão definidas
if not all([EMAIL, PASSWORD, TELEGRAM_TOKEN]):
    print("Erro: Uma ou mais variáveis de ambiente não estão definidas.")
    sys.exit(1)

# Lista de BASES atualizada
BASES = [
    {"value": "-1", "name": "TODAS"},
    {"value": "1", "name": "BASE BAURU"},
    {"value": "11", "name": "DESCONEXAO"},
    {"value": "12", "name": "BASE PIRACICABA"},
    {"value": "13", "name": "BASE PAULINIA"},
    {"value": "14", "name": "BASE RIBEIRAO PRETO"},
    {"value": "15", "name": "BASE JAGUARIUNA"},
    {"value": "18", "name": "BASE BATATAIS"},
    {"value": "19", "name": "DESCONEXAO GPON"},
    {"value": "20", "name": "BASE SUMARE VT"},
    {"value": "21", "name": "BASE ESTOQUE"},
    {"value": "22", "name": "BASE PIRACICABA VT"},
    {"value": "23", "name": "BASE RIBEIRÃO VT"},
    {"value": "25", "name": "GPON BAURU"},
    {"value": "26", "name": "BASE ARARAS VT"},
    {"value": "27", "name": "BASE LIMEIRA"},
    {"value": "29", "name": "BASE SUMARE"},
    {"value": "31", "name": "BASE BAURU VT"},
    {"value": "32", "name": "BASE BOTUCATU VT"},
    {"value": "33", "name": "BASE BOTUCATU"},
    {"value": "34", "name": "DESCONEXÃO BOTUCATU"},
    {"value": "35", "name": "GPON RIBEIRAO PRETO"},
    {"value": "37", "name": "BASE SOROCABA"},
    {"value": "39", "name": "DESCONEXAO RIBEIRAO PRETO"},
    {"value": "40", "name": "BASE SAO JOSE DO RIO PRETO"},
    {"value": "41", "name": "BASE SERTAOZINHO VT"},
    {"value": "42", "name": "BASE VAR PIRACICABA"},
    {"value": "43", "name": "BASE VAR ARARAS"},
    {"value": "44", "name": "BASE VAR SUMARE"},
    {"value": "45", "name": "BASE VAR BAURU"},
    {"value": "46", "name": "BASE MDU PIRACICABA"},
    {"value": "47", "name": "BASE MDU ARARAS"},
    {"value": "48", "name": "BASE MDU MOGI"},
    {"value": "49", "name": "BASE MDU BAURU"},
    {"value": "50", "name": "BASE MDU RIBEIRÃO PRETO"},
    {"value": "51", "name": "BASE MDU SJRP"},
    {"value": "52", "name": "BASE CAMPINAS"},
    {"value": "54", "name": "DESCONEXÃO CAMPINAS"}
]

# Estados da conversa
BASE_SELECTION, DATE_START, DATE_END = range(3)

def gerar_relatorio_pdf(base_name, data_ini, data_fim):
    logging.info(f"Iniciando a geração do relatório PDF para a base '{base_name}', de {data_ini} até {data_fim}.")
    # Configurações do Selenium e ChromeDriver
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument('--headless')  # Mantenha comentado para visualizar o navegador
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument('start-maximized')
    chrome_options.add_argument('--lang=pt-BR')  # Definir o idioma do navegador para português do Brasil

    # Configurações para permitir downloads
    prefs = {
        "download.default_directory": "/Users/marcosgallo/Documents/Boot/downloads",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,  # Forçar download de PDFs
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Caminho do ChromeDriver
    servico = Service('/Users/marcosgallo/Documents/Boot/drive/chromedriver')
    driver = webdriver.Chrome(service=servico, options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        logging.info("Acessando a página de login.")
        driver.get('https://basic.controlservices.com.br/login')

        logging.info("Realizando login.")
        email_field = wait.until(EC.presence_of_element_located((By.NAME, 'email')))
        email_field.send_keys(EMAIL)

        senha_field = driver.find_element(By.NAME, 'password')
        senha_field.send_keys(PASSWORD)

        entrar_button = driver.find_element(By.XPATH, '//button[@type="submit"]')
        entrar_button.click()

        logging.info("Aguardando redirecionamento após login.")
        wait.until(EC.url_contains('/home'))
        wait.until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/financeiro")]')))

        logging.info("Navegando diretamente para a página de relatórios.")
        driver.get('https://basic.controlservices.com.br/financeiro/relatorio')

        logging.info("Preenchendo o formulário do relatório.")

        # Selecionando o modelo
        modelo_select_element = wait.until(EC.element_to_be_clickable((By.NAME, 'tipoRelat')))
        modelo_select = Select(modelo_select_element)
        modelo_select.select_by_visible_text("Previsão")

        # Interagindo com o Select2 do campo 'BASE'
        logging.info(f"Selecionando a base '{base_name}'.")

        # Clique no campo Select2 para abrir o dropdown
        base_select_container = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.select2-container')))
        base_select_container.click()

        base_search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.select2-search__field')))
        base_search_box.send_keys(base_name)

        desired_option = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//li[contains(@class, 'select2-results__option') and normalize-space(text())='{base_name}']")))
        desired_option.click()

        # Preenchendo as datas
        logging.info("Preenchendo as datas.")
        # data_ini e data_fim são recebidas como parâmetros

        # Encontrar os elementos dos campos de data
        data_ini_field = driver.find_element(By.NAME, 'data_ini')
        data_fim_field = driver.find_element(By.NAME, 'data_fim')

        # Definir os valores das datas usando JavaScript
        driver.execute_script("arguments[0].value = arguments[1];", data_ini_field, data_ini)
        driver.execute_script("arguments[0].value = arguments[1];", data_fim_field, data_fim)

        logging.info("Enviando o formulário para gerar o relatório.")
        submit_button = driver.find_element(By.XPATH, '//button[contains(text(), "BUSCAR")]')
        submit_button.click()

        # Verificar se o relatório foi baixado
        logging.info("Verificando se o relatório foi baixado.")
        caminho_diretorio = '/Users/marcosgallo/Documents/Boot/downloads'
        arquivo_pdf = esperar_download_concluir(caminho_diretorio)
        if not arquivo_pdf:
            raise Exception("O relatório não foi encontrado no diretório de downloads.")

        logging.info("Relatório PDF gerado com sucesso.")

    except Exception as e:
        logging.error("Ocorreu um erro na geração do relatório PDF:")
        logging.error(str(e))
        import traceback
        logging.error(traceback.format_exc())
        raise
    finally:
        driver.quit()

    return arquivo_pdf

def esperar_download_concluir(caminho_diretorio, timeout=60):
    logging.info(f"Esperando o arquivo PDF ser baixado no diretório: {caminho_diretorio}")
    arquivos_antes = set(os.listdir(caminho_diretorio))
    end_time = time.time() + timeout

    while time.time() < end_time:
        arquivos_depois = set(os.listdir(caminho_diretorio))
        novos_arquivos = arquivos_depois - arquivos_antes
        for arquivo in novos_arquivos:
            if arquivo.endswith('.pdf') and not arquivo.endswith('.crdownload'):
                arquivo_pdf = os.path.join(caminho_diretorio, arquivo)
                logging.info(f"Novo arquivo PDF encontrado: {arquivo_pdf}")
                return arquivo_pdf
        time.sleep(1)
    logging.error("Tempo de espera esgotado. O arquivo PDF não foi encontrado.")
    return None

async def start_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for idx, base in enumerate(BASES, start=1):
        button = InlineKeyboardButton(base["name"], callback_data=base["name"])
        row.append(button)
        if idx % 2 == 0:  # Ajuste o número de botões por linha conforme necessário
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Selecione a BASE desejada:', reply_markup=reply_markup)
    return BASE_SELECTION

async def base_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    base_selecionada = query.data
    context.user_data['base_selecionada'] = base_selecionada
    await query.answer()
    await query.edit_message_text(text=f"Base '{base_selecionada}' selecionada.")
    await update.effective_chat.send_message("Por favor, forneça a data inicial no formato DD/MM/YYYY:")
    return DATE_START

async def receive_date_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    try:
        # Validar a data no formato DD/MM/YYYY
        date_obj = datetime.strptime(date_text, '%d/%m/%Y')
        # Converter para o formato YYYY-MM-DD
        date_formatted = date_obj.strftime('%Y-%m-%d')
        context.user_data['data_ini'] = date_formatted
        await update.message.reply_text("Agora, por favor, forneça a data final no formato DD/MM/YYYY:")
        return DATE_END
    except ValueError:
        await update.message.reply_text("Data inválida. Por favor, forneça a data inicial no formato DD/MM/YYYY:")
        return DATE_START

async def receive_date_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    try:
        # Validar a data no formato DD/MM/YYYY
        date_obj = datetime.strptime(date_text, '%d/%m/%Y')
        # Converter para o formato YYYY-MM-DD
        date_formatted = date_obj.strftime('%Y-%m-%d')
        context.user_data['data_fim'] = date_formatted
        await update.message.reply_text("Gerando relatório, por favor aguarde...")

        base_selecionada = context.user_data['base_selecionada']
        data_ini = context.user_data['data_ini']
        data_fim = context.user_data['data_fim']

        try:
            # Executa a função bloqueante em um executor
            loop = asyncio.get_event_loop()
            caminho_pdf = await loop.run_in_executor(None, gerar_relatorio_pdf, base_selecionada, data_ini, data_fim)

            # Envia o PDF
            with open(caminho_pdf, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf_file,
                    filename='relatorio.pdf'
                )
        except Exception as e:
            logging.error(f"Erro ao enviar relatório: {e}")
            import traceback
            logging.error(traceback.format_exc())
            await update.message.reply_text("Ocorreu um erro ao gerar o relatório.")

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Data inválida. Por favor, forneça a data final no formato DD/MM/YYYY:")
        return DATE_END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

def main():
    # Inicializar o aplicativo do Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Definir o ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('relatorio', start_relatorio)],
        states={
            BASE_SELECTION: [CallbackQueryHandler(base_selected)],
            DATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date_start)],
            DATE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Adicionar o ConversationHandler ao aplicativo
    application.add_handler(conv_handler)

    # Iniciar o bot
    application.run_polling()

if __name__ == '__main__':
    main()