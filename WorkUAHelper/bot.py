# bot.py
import logging
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, Filters
from database import Session, User, Vacancy, Resume, Application
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TITLE, COMPANY, SALARY, DESCRIPTION, REQUIREMENTS, CONFIRM = range(6)
REG_NAME, REG_PHONE, REG_EMAIL = range(6, 9)
RESUME_POSITION, RESUME_SALARY, RESUME_EXPERIENCE, RESUME_EDUCATION, RESUME_SKILLS, RESUME_ABOUT, RESUME_CONFIRM = range(9, 16)
UPDATE_RESUME_CHOICE, UPDATE_RESUME_FIELD, UPDATE_RESUME_VALUE = range(16, 19)

def show_job_seeker_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ["📋 Список вакансій", "🔍 Пошук вакансій"],
        ["📄 Моє резюме", "📨 Мої заявки"],
        ["👤 Мій профіль", "📞 Контакти"],
        ["ℹ️ Допомога", "↩️ Головне меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message:
        update.message.reply_text("Оберіть дію:", reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.reply_text("Оберіть дію:", reply_markup=reply_markup)

def show_employer_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ["📝 Додати вакансію", "📊 Мої вакансії"],
        ["📨 Заявки на вакансії", "🔍 Пошук кандидатів"],
        ["👤 Мій профіль", "📞 Контакти"],
        ["ℹ️ Допомога", "↩️ Головне меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message:
        update.message.reply_text("Оберіть дію:", reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.reply_text("Оберіть дію:", reply_markup=reply_markup)

def show_main_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ["📋 Знайти вакансії", "📝 Подати вакансію"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    welcome_text = (
        "Ласкаво просимо до WorkUA Helper!\n\n"
        "Оберіть вашу ціль:\n\n"
        "Знайти вакансії - якщо шукаєте роботу\n"
        "Подати вакансію - якщо шукаєте співробітників"
    )
    if update.message:
        update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup)

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    existing_user = db_session.query(User).filter_by(telegram_id=user.id).first()
    
    if not existing_user:
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_employer=False,
            registration_date=datetime.utcnow()
        )
        db_session.add(new_user)
        db_session.commit()
    
    db_session.close()
    show_main_menu(update, context)

def show_vacancies_list(update: Update, context: CallbackContext) -> None:
    db_session = Session()
    vacancies = db_session.query(Vacancy).filter_by(is_active=True).order_by(Vacancy.created_at.desc()).all()
    
    if not vacancies:
        update.message.reply_text("Наразі немає активних вакансій.")
        db_session.close()
        return

    context.user_data['vacancies'] = vacancies
    context.user_data['current_vacancy_index'] = 0
    
    show_single_vacancy(update, context)
    db_session.close()

def show_single_vacancy(update: Update, context: CallbackContext, edit_message: bool = False) -> None:
    vacancies = context.user_data.get('vacancies', [])
    current_index = context.user_data.get('current_vacancy_index', 0)
    
    if not vacancies:
        return
    
    vacancy = vacancies[current_index]
    total_vacancies = len(vacancies)
    
    is_test = vacancy.employer_id == 999999999
    test_marker = "🧪 " if is_test else ""
    
    keyboard_buttons = []
    
    if total_vacancies > 1:
        prev_button = InlineKeyboardButton("⬅️", callback_data=f"prev_vacancy")
        next_button = InlineKeyboardButton("➡️", callback_data=f"next_vacancy")
        page_info = InlineKeyboardButton(f"{current_index + 1}/{total_vacancies}", callback_data="page_info")
        keyboard_buttons.append([prev_button, page_info, next_button])
    
    apply_button = InlineKeyboardButton("📨 Подати заявку", callback_data=f"apply_{vacancy.id}")
    keyboard_buttons.append([apply_button])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    message = (
        f"{test_marker}🏢 {vacancy.title}\n"
        f"🏭 Компанія: {vacancy.company}\n"
        f"💰 Зарплата: {vacancy.salary or 'Не вказано'}\n"
        f"📝 Опис: {vacancy.description}\n"
        f"🎯 Вимоги: {vacancy.requirements}\n"
        f"────────────────────"
    )
    
    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    else:
        if update.callback_query:
            update.callback_query.message.reply_text(message, reply_markup=reply_markup)
        else:
            update.message.reply_text("📋 Список вакансій:")
            update.message.reply_text(message, reply_markup=reply_markup)

def handle_vacancy_navigation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    action = query.data
    current_index = context.user_data.get('current_vacancy_index', 0)
    vacancies = context.user_data.get('vacancies', [])
    total_vacancies = len(vacancies)
    
    if action == "prev_vacancy":
        new_index = (current_index - 1) % total_vacancies
    elif action == "next_vacancy":
        new_index = (current_index + 1) % total_vacancies
    else:
        return
    
    context.user_data['current_vacancy_index'] = new_index
    show_single_vacancy(update, context, edit_message=True)

def handle_application_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    vacancy_id = int(query.data.split('_')[1])
    user = query.from_user
    
    db_session = Session()
    
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    if not resume:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Для подачі заявки необхідно мати резюме.\n\nНатисніть '📄 Моє резюме' щоб створити ваше резюме."
        )
        db_session.close()
        return
    
    existing_application = db_session.query(Application).filter_by(user_id=user.id, vacancy_id=vacancy_id).first()
    if existing_application:
        context.bot.send_message(chat_id=query.message.chat_id, text="ℹ️ Ви вже подавали заявку на цю вакансію.")
        db_session.close()
        return
    
    vacancy = db_session.query(Vacancy).filter_by(id=vacancy_id).first()
    new_application = Application(
        user_id=user.id,
        vacancy_id=vacancy_id,
        employer_id=vacancy.employer_id,
        resume_data=f"{resume.position}|{resume.experience}|{resume.education}|{resume.skills}",
        user_contacts=resume.contacts,
        status="нова",
        created_at=datetime.utcnow()
    )
    
    db_session.add(new_application)
    db_session.commit()
    
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    user_name = user_data.full_name if user_data else user.first_name
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"✅ Заявку успішно подано на вакансію '{vacancy.title}'!\n\nРоботодавець перегляне ваше резюме та зв'яжеться з вами."
    )
    
    if vacancy.employer_id != 999999999:
        try:
            employer_message = (
                f"📨 Нова заявка на вакансію!\n\n"
                f"🏢 Вакансія: {vacancy.title}\n"
                f"👤 Кандидат: {user_name}\n"
                f"📄 Резюме: {resume.position}\n"
                f"📅 Заявка подана: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Перейдіть в '📨 Заявки на вакансії' для перегляду деталей."
            )
            context.bot.send_message(chat_id=vacancy.employer_id, text=employer_message)
        except Exception as e:
            logger.error(f"Не вдалося відправити сповіщення роботодавцю: {e}")
    
    db_session.close()

def show_my_applications(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    applications = db_session.query(Application).filter_by(user_id=user.id).order_by(Application.created_at.desc()).all()
    
    if not applications:
        update.message.reply_text("📨 У вас ще немає поданих заявок.\n\nПерегляньте вакансії та натискайте '📨 Подати заявку' на цікаві пропозиції!")
        db_session.close()
        return
    
    update.message.reply_text(f"📨 Ваші заявки ({len(applications)}):")
    
    for application in applications:
        vacancy = db_session.query(Vacancy).filter_by(id=application.vacancy_id).first()
        status_emoji = "🟢" if application.status == "нова" else "🟡" if application.status == "переглянута" else "🔴"
        
        is_test = vacancy.employer_id == 999999999 if vacancy else False
        test_marker = "🧪 " if is_test else ""
        
        message = (
            f"{test_marker}🏢 {vacancy.title if vacancy else 'Вакансія не знайдена'}\n"
            f"🏭 Компанія: {vacancy.company if vacancy else 'Невідомо'}\n"
            f"📅 Подана: {application.created_at.strftime('%d.%m.%Y')}\n"
            f"📊 Статус: {status_emoji} {application.status}\n"
            f"────────────────────"
        )
        update.message.reply_text(message)
    
    db_session.close()

def show_employer_applications(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    applications = db_session.query(Application).filter_by(employer_id=user.id).order_by(Application.created_at.desc()).all()
    
    if not applications:
        update.message.reply_text("📨 На ваши вакансії ще не надходило заявок.\n\nЗаявки з'являться тут, коли кандидати будуть подавати заявки на ваші вакансії.")
        db_session.close()
        return
    
    vacancies_applications = {}
    for application in applications:
        vacancy = db_session.query(Vacancy).filter_by(id=application.vacancy_id).first()
        if vacancy:
            if vacancy.id not in vacancies_applications:
                vacancies_applications[vacancy.id] = {'vacancy': vacancy, 'applications': []}
            vacancies_applications[vacancy.id]['applications'].append(application)
    
    update.message.reply_text(f"📨 Заявки на ваші вакансії ({len(applications)}):")
    
    for vacancy_id, data in vacancies_applications.items():
        vacancy = data['vacancy']
        vac_applications = data['applications']
        
        update.message.reply_text(f"🏢 Вакансія: {vacancy.title}\n📨 Кількість заявок: {len(vac_applications)}\n────────────────────")
        
        for application in vac_applications:
            applicant_data = db_session.query(User).filter_by(telegram_id=application.user_id).first()
            applicant_name = applicant_data.full_name if applicant_data else "Користувач"
            
            resume_parts = application.resume_data.split('|')
            position = resume_parts[0] if len(resume_parts) > 0 else "Не вказано"
            experience = resume_parts[1] if len(resume_parts) > 1 else "Не вказано"
            education = resume_parts[2] if len(resume_parts) > 2 else "Не вказано"
            skills = resume_parts[3] if len(resume_parts) > 3 else "Не вказано"
            
            status_emoji = "🟢" if application.status == "нова" else "🟡" if application.status == "переглянута" else "🔴"
            
            keyboard = [
                [InlineKeyboardButton("👀 Переглянуто", callback_data=f"viewed_{application.id}"), InlineKeyboardButton("📞 Зателефонувати", callback_data=f"call_{application.id}")],
                [InlineKeyboardButton("✉️ Написати", callback_data=f"message_{application.id}"), InlineKeyboardButton("❌ Відхилити", callback_data=f"reject_{application.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                f"👤 Кандидат: {applicant_name}\n"
                f"🎯 Бажана посада: {position}\n"
                f"💼 Досвід: {experience[:80]}...\n"
                f"🎓 Освіта: {education[:80]}...\n"
                f"🛠️ Навички: {skills[:80]}...\n"
                f"📞 Контакти: {application.user_contacts}\n"
                f"📅 Заявка подана: {application.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"📊 Статус: {status_emoji} {application.status}\n"
                f"────────────────────"
            )
            update.message.reply_text(message, reply_markup=reply_markup)
    
    db_session.close()

def handle_application_management(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    action, application_id = query.data.split('_')
    application_id = int(application_id)
    
    db_session = Session()
    application = db_session.query(Application).filter_by(id=application_id).first()
    
    if not application:
        context.bot.send_message(chat_id=query.message.chat_id, text="❌ Заявка не знайдена.")
        db_session.close()
        return
    
    if action == "viewed":
        application.status = "переглянута"
        db_session.commit()
        context.bot.send_message(chat_id=query.message.chat_id, text="✅ Статус заявки змінено на 'переглянута'")
        
    elif action == "call":
        application.status = "переглянута"
        db_session.commit()
        context.bot.send_message(chat_id=query.message.chat_id, text=f"📞 Контакти для дзвінка:\n{application.user_contacts}\n\nНе забудьте повідомити кандидата після розмови!")
        
    elif action == "message":
        application.status = "переглянута"
        db_session.commit()
        context.bot.send_message(chat_id=query.message.chat_id, text=f"✉️ Контакти для написання:\n{application.user_contacts}\n\nНапишіть кандидату та повідомте про подальші кроки!")
        
    elif action == "reject":
        application.status = "відхилена"
        db_session.commit()
        context.bot.send_message(chat_id=query.message.chat_id, text="❌ Заявку відхилено")
        
        try:
            vacancy = db_session.query(Vacancy).filter_by(id=application.vacancy_id).first()
            rejection_message = (
                f"ℹ️ Інформація про вашу заявку:\n\n"
                f"🏢 Вакансія: {vacancy.title if vacancy else 'Вакансія'}\n"
                f"🏭 Компанія: {vacancy.company if vacancy else 'Компанія'}\n"
                f"📊 Статус: ❌ Відхилено\n\n"
                f"Дякуємо за вашу заявку! На жаль, наразі ваша кандидатура не підходить для цієї позиції."
            )
            context.bot.send_message(chat_id=application.user_id, text=rejection_message)
        except Exception as e:
            logger.error(f"Не вдалося відправити сповіщення кандидату: {e}")
    
    applicant_data = db_session.query(User).filter_by(telegram_id=application.user_id).first()
    applicant_name = applicant_data.full_name if applicant_data else "Користувач"
    
    resume_parts = application.resume_data.split('|')
    position = resume_parts[0] if len(resume_parts) > 0 else "Не вказано"
    
    status_emoji = "🟢" if application.status == "нова" else "🟡" if application.status == "переглянута" else "🔴"
    
    keyboard = [
        [InlineKeyboardButton("👀 Переглянуто", callback_data=f"viewed_{application.id}"), InlineKeyboardButton("📞 Зателефонувати", callback_data=f"call_{application.id}")],
        [InlineKeyboardButton("✉️ Написати", callback_data=f"message_{application.id}"), InlineKeyboardButton("❌ Відхилити", callback_data=f"reject_{application.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    updated_message = (
        f"👤 Кандидат: {applicant_name}\n"
        f"🎯 Бажана посада: {position}\n"
        f"💼 Досвід: {resume_parts[1][:80] if len(resume_parts) > 1 else 'Не вказано'}...\n"
        f"🎓 Освіта: {resume_parts[2][:80] if len(resume_parts) > 2 else 'Не вказано'}...\n"
        f"🛠️ Навички: {resume_parts[3][:80] if len(resume_parts) > 3 else 'Не вказано'}...\n"
        f"📞 Контакти: {application.user_contacts}\n"
        f"📅 Заявка подана: {application.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Статус: {status_emoji} {application.status}\n"
        f"────────────────────"
    )
    
    query.edit_message_text(updated_message, reply_markup=reply_markup)
    db_session.close()

def show_my_vacancies(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    
    vacancies = db_session.query(Vacancy).filter_by(employer_id=user.id).order_by(Vacancy.created_at.desc()).all()
    
    if not vacancies:
        update.message.reply_text("У вас ще немає вакансій.\n\nНатисніть '📝 Додати вакансію' щоб створити першу вакансію!")
        db_session.close()
        return
    
    update.message.reply_text("📊 Ваші вакансії:")
    
    for vacancy in vacancies:
        applications_count = db_session.query(Application).filter_by(vacancy_id=vacancy.id).count()
        new_applications_count = db_session.query(Application).filter_by(vacancy_id=vacancy.id, status="нова").count()
        
        status = "✅ Активна" if vacancy.is_active else "❌ Неактивна"
        applications_info = f"📨 {applications_count} заявок"
        if new_applications_count > 0:
            applications_info += f" ({new_applications_count} нових)"
        
        keyboard = [[InlineKeyboardButton("🗑️ Видалити вакансію", callback_data=f"delete_vacancy_{vacancy.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"🏢 {vacancy.title}\n"
            f"🏭 Компанія: {vacancy.company}\n"
            f"💰 Зарплата: {vacancy.salary or 'Не вказано'}\n"
            f"📝 {vacancy.description[:100]}...\n"
            f"{applications_info}\n"
            f"📅 Створено: {vacancy.created_at.strftime('%d.%m.%Y')}\n"
            f"Статус: {status}\n"
            f"────────────────────"
        )
        update.message.reply_text(message, reply_markup=reply_markup)
    
    db_session.close()

def handle_delete_vacancy_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    vacancy_id = int(query.data.split('_')[2])
    user = query.from_user
    
    db_session = Session()
    vacancy = db_session.query(Vacancy).filter_by(id=vacancy_id, employer_id=user.id).first()
    
    if not vacancy:
        context.bot.send_message(chat_id=query.message.chat_id, text="❌ Вакансія не знайдена або у вас немає прав для її видалення.")
        db_session.close()
        return
    
    applications_count = db_session.query(Application).filter_by(vacancy_id=vacancy_id).count()
    
    if applications_count > 0:
        db_session.query(Application).filter_by(vacancy_id=vacancy_id).delete()
    
    db_session.delete(vacancy)
    db_session.commit()
    
    query.delete_message()
    
    success_message = f"✅ Вакансію '{vacancy.title}' успішно видалено!"
    if applications_count > 0:
        success_message += f"\n\nТакож видалено {applications_count} заявок на цю вакансію."
    
    context.bot.send_message(chat_id=query.message.chat_id, text=success_message)
    
    if applications_count > 0:
        applications = db_session.query(Application).filter_by(vacancy_id=vacancy_id).all()
        for application in applications:
            try:
                notification_message = (
                    f"ℹ️ Інформація про вашу заявку:\n\n"
                    f"🏢 Вакансія: {vacancy.title}\n"
                    f"🏭 Компанія: {vacancy.company}\n"
                    f"📊 Статус: ❌ Вакансію видалено\n\n"
                    f"Роботодавець видалив цю вакансію. Ваша заявка більше не розглядається."
                )
                context.bot.send_message(chat_id=application.user_id, text=notification_message)
            except Exception as e:
                logger.error(f"Не вдалося відправити сповіщення кандидату: {e}")
    
    db_session.close()

def show_user_profile(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    
    if not user_data:
        update.message.reply_text("Профіль не знайдено. Спробуйте /start")
        db_session.close()
        return
    
    user_type = "Роботодавець" if user_data.is_employer else "Шукач роботи"
    
    if user_data.is_employer:
        vacancies_count = db_session.query(Vacancy).filter_by(employer_id=user.id).count()
        applications_count = db_session.query(Application).filter_by(employer_id=user.id).count()
        profile_extra = f"Ваших вакансій: {vacancies_count}\nЗаявок на вакансії: {applications_count}"
    else:
        applications_count = db_session.query(Application).filter_by(user_id=user.id).count()
        profile_extra = f"Поданих заявок: {applications_count}"
    
    profile_text = (
        f"👤 Ваш профіль:\n\n"
        f"Ім'я: {user_data.full_name or 'Не вказано'}\n"
        f"Телефон: {user_data.phone or 'Не вказано'}\n"
        f"Email: {user_data.email or 'Не вказано'}\n"
        f"Тип: {user_type}\n"
        f"{profile_extra}\n"
        f"Дата реєстрації: {user_data.registration_date.strftime('%d.%m.%Y')}"
    )
    
    update.message.reply_text(profile_text)
    
    if user_data.is_employer:
        show_employer_menu(update, context)
    else:
        show_job_seeker_menu(update, context)
    
    db_session.close()

def start_contact_registration(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    if user_data:
        context.user_data['current_name'] = user_data.full_name or ''
        context.user_data['current_phone'] = user_data.phone or ''
        context.user_data['current_email'] = user_data.email or ''
    
    keyboard = [["❌ Скасувати реєстрацію"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    current_name = context.user_data.get('current_name', '')
    prompt_text = "📞 Давайте оновимо ваші контактні дані!\n\n"
    
    if current_name:
        prompt_text += f"Поточне ім'я: {current_name}\n"
    
    prompt_text += (
        "Введіть ваше повне ім'я:\n"
        "Наприклад: 'Іван Петренко'\n\n"
        "Або натисніть '❌ Скасувати реєстрацію' для виходу"
    )
    
    update.message.reply_text(prompt_text, reply_markup=reply_markup)
    
    return REG_NAME

def register_name(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати реєстрацію":
        return cancel_contact_registration(update, context)
    
    context.user_data['reg_name'] = update.message.text
    
    keyboard = [["❌ Скасувати реєстрацію"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    current_phone = context.user_data.get('current_phone', '')
    prompt_text = "📱 Введіть ваш номер телефону:\n"
    
    if current_phone:
        prompt_text += f"Поточний телефон: {current_phone}\n"
    
    prompt_text += (
        "Наприклад: '+380501234567' або '0501234567'\n\n"
        "Або натисніть '❌ Скасувати реєстрацію' для виходу"
    )
    
    update.message.reply_text(prompt_text, reply_markup=reply_markup)
    return REG_PHONE

def register_phone(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати реєстрацію":
        return cancel_contact_registration(update, context)
    
    phone = update.message.text
    
    if not re.match(r'^(\+?38)?0\d{9}$', phone.replace(' ', '')):
        update.message.reply_text("❌ Неправильний формат телефону. Спробуйте ще раз:\nНаприклад: '+380501234567' або '0501234567'")
        return REG_PHONE
    
    context.user_data['reg_phone'] = phone
    
    keyboard = [["❌ Скасувати реєстрацію"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    current_email = context.user_data.get('current_email', '')
    prompt_text = "📧 Введіть ваш email:\n"
    
    if current_email:
        prompt_text += f"Поточний email: {current_email}\n"
    
    prompt_text += (
        "Наприклад: 'ivan@gmail.com'\n\n"
        "Або натисніть '❌ Скасувати реєстрацію' для виходу"
    )
    
    update.message.reply_text(prompt_text, reply_markup=reply_markup)
    return REG_EMAIL

def register_email(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати реєстрацію":
        return cancel_contact_registration(update, context)
    
    email = update.message.text
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        update.message.reply_text("❌ Неправильний формат email. Спробуйте ще раз:\nНаприклад: 'ivan@gmail.com'")
        return REG_EMAIL
    
    context.user_data['reg_email'] = email
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    
    if user_data:
        user_data.full_name = context.user_data['reg_name']
        user_data.phone = context.user_data['reg_phone']
        user_data.email = context.user_data['reg_email']
        db_session.commit()
    
    db_session.close()
    
    context.user_data.pop('reg_name', None)
    context.user_data.pop('reg_phone', None)
    context.user_data.pop('reg_email', None)
    context.user_data.pop('current_name', None)
    context.user_data.pop('current_phone', None)
    context.user_data.pop('current_email', None)
    
    update.message.reply_text("✅ Контактні дані успішно оновлено!\n\nТепер ваші контакти будуть відображатись у вакансіях/резюме.")
    
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    if user_data and user_data.is_employer:
        show_employer_menu(update, context)
    else:
        show_job_seeker_menu(update, context)
        
    return ConversationHandler.END

def show_user_contacts(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    
    if not user_data:
        update.message.reply_text("Контактні дані не знайдені.")
        db_session.close()
        return
    
    contacts_text = (
        f"📞 Ваші контактні дані:\n\n"
        f"👤 Ім'я: {user_data.full_name or 'Не вказано'}\n"
        f"📱 Телефон: {user_data.phone or 'Не вказано'}\n"
        f"📧 Email: {user_data.email or 'Не вказано'}"
    )
    
    update.message.reply_text(contacts_text)
    
    if user_data.is_employer:
        show_employer_menu(update, context)
    else:
        show_job_seeker_menu(update, context)
    
    db_session.close()

def show_my_resume_menu(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    
    if not resume:
        keyboard = [["📝 Створити резюме"], ["↩️ Назад"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("📄 У вас ще немає створеного резюме.\n\nДавайте створимо ваше перше резюме!", reply_markup=reply_markup)
        db_session.close()
        return
    
    keyboard = [
        ["📝 Оновити резюме", "👀 Переглянути резюме"],
        ["❌ Видалити резюме", "↩️ Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "📄 Управління резюме\n\nОберіть дію:",
        reply_markup=reply_markup
    )
    db_session.close()

def show_my_resume(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    
    if not resume:
        update.message.reply_text("❌ Резюме не знайдено. Спочатку створіть резюме.")
        db_session.close()
        return
    
    resume_text = (
        f"📄 Ваше резюме:\n\n"
        f"🎯 Бажана посада: {resume.position}\n"
        f"💰 Бажана зарплата: {resume.salary or 'Не вказано'}\n"
        f"💼 Досвід роботи: {resume.experience}\n"
        f"🎓 Освіта: {resume.education}\n"
        f"🛠️ Навички: {resume.skills}\n"
        f"📝 Про себе: {resume.about or 'Не вказано'}\n"
        f"📞 Контакти: {resume.contacts}\n"
        f"📅 Створено: {resume.created_at.strftime('%d.%m.%Y')}\n"
        f"🔸 Статус: {'✅ Активне' if resume.is_active else '❌ Неактивне'}"
    )
    
    keyboard = [
        ["🔄 Оновити резюме", "❌ Видалити резюме"],
        ["↩️ Назад до меню резюме"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(resume_text, reply_markup=reply_markup)
    db_session.close()

def start_update_resume(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    db_session = Session()
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    db_session.close()
    
    if not resume:
        update.message.reply_text("❌ Резюме не знайдено. Спочатку створіть резюме.")
        return ConversationHandler.END
    
    context.user_data['current_resume'] = {
        'position': resume.position,
        'salary': resume.salary or '',
        'experience': resume.experience,
        'education': resume.education,
        'skills': resume.skills,
        'about': resume.about or ''
    }
    
    keyboard = [
        ["🎯 Бажану посаду", "💰 Бажану зарплату"],
        ["💼 Досвід роботи", "🎓 Освіту"],
        ["🛠️ Навички", "📝 Інформацію про себе"],
        ["❌ Скасувати оновлення"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "🔄 Оновлення резюме\n\n"
        "Оберіть, що ви хочете оновити:\n\n"
        f"🎯 Поточна посада: {resume.position[:50]}...\n"
        f"💰 Поточна зарплата: {resume.salary or 'Не вказано'}\n"
        f"💼 Поточний досвід: {resume.experience[:50]}...\n"
        f"🎓 Поточна освіта: {resume.education[:50]}...\n"
        f"🛠️ Поточні навички: {resume.skills[:50]}...\n"
        f"📝 Про себе: {resume.about[:50] + '...' if resume.about else 'Не вказано'}\n\n"
        "Або натисніть '❌ Скасувати оновлення' для виходу",
        reply_markup=reply_markup
    )
    
    return UPDATE_RESUME_CHOICE

def handle_update_resume_choice(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати оновлення":
        return cancel_resume_update(update, context)
    
    field_mapping = {
        "🎯 Бажану посаду": "position",
        "💰 Бажану зарплату": "salary",
        "💼 Досвід роботи": "experience", 
        "🎓 Освіту": "education",
        "🛠️ Навички": "skills",
        "📝 Інформацію про себе": "about"
    }
    
    if update.message.text not in field_mapping:
        update.message.reply_text("❌ Будь ласка, оберіть один з варіантів з клавіатури.")
        return UPDATE_RESUME_CHOICE
    
    context.user_data['update_resume_field'] = field_mapping[update.message.text]
    current_value = context.user_data['current_resume'][field_mapping[update.message.text]]
    
    field_prompts = {
        "position": "🎯 Введіть нову бажану посаду:\nНаприклад: 'Python розробник' або 'Менеджер з продажів'",
        "salary": "💰 Введіть нову бажану зарплату:\nНаприклад: '1000$' або '25000 грн' або 'Договірна'",
        "experience": "💼 Введіть новий досвід роботи:\nНаприклад: '3 роки в IT, 2 роки на посаді Python розробника'",
        "education": "🎓 Введіть нову освіту:\nНаприклад: 'Вища, КНУ ім. Шевченка, факультет кібернетики'",
        "skills": "🛠️ Введіть нові навички:\nНаприклад: 'Python, Django, PostgreSQL, Git, Docker'",
        "about": "📝 Введіть нову інформацію про себе:\nНаприклад: 'Відповідальний, цілеспрямований, швидко навчаюсь'"
    }
    
    prompt = field_prompts[field_mapping[update.message.text]]
    
    if current_value:
        prompt += f"\n\nПоточне значення: {current_value[:100]}{'...' if len(current_value) > 100 else ''}"
    
    keyboard = [["❌ Скасувати оновлення"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(prompt, reply_markup=reply_markup)
    
    return UPDATE_RESUME_VALUE

def handle_update_resume_value(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати оновлення":
        return cancel_resume_update(update, context)
    
    new_value = update.message.text
    field = context.user_data['update_resume_field']
    
    user = update.effective_user
    db_session = Session()
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    
    if resume:
        if field == "position":
            resume.position = new_value
        elif field == "salary":
            resume.salary = new_value
        elif field == "experience":
            resume.experience = new_value
        elif field == "education":
            resume.education = new_value
        elif field == "skills":
            resume.skills = new_value
        elif field == "about":
            resume.about = new_value
        
        db_session.commit()
        
        field_names = {
            "position": "бажану посаду",
            "salary": "бажану зарплату",
            "experience": "досвід роботи", 
            "education": "освіту",
            "skills": "навички",
            "about": "інформацію про себе"
        }
        
        update.message.reply_text(f"✅ {field_names[field].title()} успішно оновлено!")
    
    db_session.close()
    
    context.user_data.pop('update_resume_field', None)
    context.user_data.pop('current_resume', None)
    
    keyboard = [
        ["🔄 Оновити ще щось", "👀 Переглянути резюме"],
        ["↩️ Назад до меню резюме"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "Що бажаєте зробити далі?",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

def delete_resume(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    
    if not resume:
        update.message.reply_text("❌ Резюме не знайдено.")
        db_session.close()
        return
    
    applications_count = db_session.query(Application).filter_by(user_id=user.id).count()
    
    if applications_count > 0:
        keyboard = [
            ["✅ Так, видалити", "❌ Ні, скасувати"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        update.message.reply_text(
            f"⚠️ Увага! Ви маєте {applications_count} активних заявок, пов'язаних з цим резюме.\n\n"
            "При видаленні резюме всі ваші заявки також будуть видалені.\n\n"
            "Ви впевнені, що хочете видалити резюме?",
            reply_markup=reply_markup
        )
        context.user_data['pending_resume_deletion'] = True
    else:
        confirm_delete_resume(update, context)
    
    db_session.close()

def confirm_delete_resume(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    
    if context.user_data.get('pending_resume_deletion'):
        if update.message.text != "✅ Так, видалити":
            update.message.reply_text("❌ Видалення резюме скасовано.")
            context.user_data.pop('pending_resume_deletion', None)
            show_my_resume_menu(update, context)
            db_session.close()
            return
    
    resume = db_session.query(Resume).filter_by(user_id=user.id).first()
    
    if resume:
        applications_count = db_session.query(Application).filter_by(user_id=user.id).count()
        if applications_count > 0:
            db_session.query(Application).filter_by(user_id=user.id).delete()
        
        db_session.delete(resume)
        db_session.commit()
        
        success_message = "✅ Резюме успішно видалено!"
        if applications_count > 0:
            success_message += f"\n\nТакож видалено {applications_count} ваших заявок."
        
        update.message.reply_text(success_message)
    
    context.user_data.pop('pending_resume_deletion', None)
    db_session.close()
    
    show_job_seeker_menu(update, context)

def cancel_resume_update(update: Update, context: CallbackContext) -> int:
    context.user_data.pop('update_resume_field', None)
    context.user_data.pop('current_resume', None)
    update.message.reply_text("❌ Оновлення резюме скасовано.")
    show_my_resume_menu(update, context)
    return ConversationHandler.END

def start_create_resume(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    if not user_data or not user_data.phone:
        update.message.reply_text("📄 Перш ніж створювати резюме, будь ласка, заповніть ваші контактні дані.\n\nНатисніть '📞 Контакти' для додавання телефону та email.")
        return ConversationHandler.END
    
    context.user_data['resume'] = {}
    
    keyboard = [["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "📝 Давайте створимо ваше резюме!\n\nВведіть бажану посаду:\nНаприклад: 'Python розробник' або 'Менеджер з продажів'\n\n"
        "Або натисніть '❌ Скасувати створення резюме' для виходу",
        reply_markup=reply_markup
    )
    return RESUME_POSITION

def resume_position(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    context.user_data['resume']['position'] = update.message.text
    
    keyboard = [["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "💰 Введіть бажану зарплату (або 'Не вказано'):\nНаприклад: '1000$' або '25000 грн' або 'Договірна'\n\n"
        "Або натисніть '❌ Скасувати створення резюме' для виходу",
        reply_markup=reply_markup
    )
    return RESUME_SALARY

def resume_salary(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    context.user_data['resume']['salary'] = update.message.text
    
    keyboard = [["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "💼 Введіть ваш досвід роботи:\nНаприклад: '3 роки в IT, 2 роки на посаді Python розробника'\nАбо: 'Без досвіду, випускник університету'\n\n"
        "Або натисніть '❌ Скасувати створення резюме' для виходу",
        reply_markup=reply_markup
    )
    return RESUME_EXPERIENCE

def resume_experience(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    context.user_data['resume']['experience'] = update.message.text
    
    keyboard = [["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "🎓 Введіть вашу освіту:\nНаприклад: 'Вища, КНУ ім. Шевченка, факультет кібернетики'\nАбо: 'Студент 3 курсу, технічний університет'\n\n"
        "Або натисніть '❌ Скасувати створення резюме' для виходу",
        reply_markup=reply_markup
    )
    return RESUME_EDUCATION

def resume_education(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    context.user_data['resume']['education'] = update.message.text
    
    keyboard = [["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "🛠️ Введіть ваші навички:\nНаприклад: 'Python, Django, PostgreSQL, Git, Docker'\nАбо: 'Комунікабельність, робота в команді, англійська B1'\n\n"
        "Або натисніть '❌ Скасувати створення резюме' для виходу",
        reply_markup=reply_markup
    )
    return RESUME_SKILLS

def resume_skills(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    context.user_data['resume']['skills'] = update.message.text
    
    keyboard = [["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "📝 Введіть додаткову інформацію про себе:\nНаприклад: 'Відповідальний, цілеспрямований, швидко навчаюсь'\nАбо: 'Готовий до навчання, бажання розвиватись'\n\n"
        "Або натисніть '❌ Скасувати створення резюме' для виходу",
        reply_markup=reply_markup
    )
    return RESUME_ABOUT

def resume_about(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    context.user_data['resume']['about'] = update.message.text
    
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    contacts = f"{user_data.full_name}, {user_data.phone}, {user_data.email}"
    context.user_data['resume']['contacts'] = contacts
    
    resume_data = context.user_data['resume']
    summary = (
        "📋 Перевірте інформацію про ваше резюме:\n\n"
        f"🎯 Бажана посада: {resume_data['position']}\n"
        f"💰 Бажана зарплата: {resume_data['salary']}\n"
        f"💼 Досвід роботи: {resume_data['experience']}\n"
        f"🎓 Освіта: {resume_data['education']}\n"
        f"🛠️ Навички: {resume_data['skills']}\n"
        f"📝 Про себе: {resume_data['about']}\n"
        f"📞 Контакти: {resume_data['contacts']}\n\n"
        "Все вірно? Відправте 'Так' для підтвердження або 'Ні' для скасування."
    )
    
    keyboard = [["Так", "Ні"], ["❌ Скасувати створення резюме"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(summary, reply_markup=reply_markup)
    return RESUME_CONFIRM

def resume_confirm(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення резюме":
        return cancel_resume_creation(update, context)
    
    user_choice = update.message.text.lower()
    
    if user_choice in ['так', 'yes', 'ok', 'підтверджую']:
        user = update.effective_user
        resume_data = context.user_data['resume']
        
        db_session = Session()
        existing_resume = db_session.query(Resume).filter_by(user_id=user.id).first()
        
        if existing_resume:
            existing_resume.position = resume_data['position']
            existing_resume.salary = resume_data['salary']
            existing_resume.experience = resume_data['experience']
            existing_resume.education = resume_data['education']
            existing_resume.skills = resume_data['skills']
            existing_resume.about = resume_data['about']
            existing_resume.contacts = resume_data['contacts']
            existing_resume.is_active = True
        else:
            new_resume = Resume(
                user_id=user.id,
                position=resume_data['position'],
                salary=resume_data['salary'],
                experience=resume_data['experience'],
                education=resume_data['education'],
                skills=resume_data['skills'],
                about=resume_data['about'],
                contacts=resume_data['contacts'],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db_session.add(new_resume)
        
        db_session.commit()
        db_session.close()
        
        context.user_data.pop('resume', None)
        update.message.reply_text("✅ Резюме успішно створено/оновлено!\n\nТепер ви можете подавати заявки на вакансії.")
        
        show_my_resume_menu(update, context)
        return ConversationHandler.END
    
    elif user_choice in ['ні', 'no', 'cancel', 'скасувати']:
        context.user_data.pop('resume', None)
        update.message.reply_text("❌ Створення резюме скасовано.")
        show_job_seeker_menu(update, context)
        return ConversationHandler.END
    
    else:
        update.message.reply_text("Будь ласка, відправте 'Так' для підтвердження або 'Ні' для скасування.")
        return RESUME_CONFIRM

def cancel_resume_creation(update: Update, context: CallbackContext) -> int:
    context.user_data.pop('resume', None)
    update.message.reply_text("❌ Створення резюме скасовано.")
    show_job_seeker_menu(update, context)
    return ConversationHandler.END

def start_add_vacancy(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    if not user_data or not user_data.phone:
        update.message.reply_text("📝 Перш ніж додавати вакансію, будь ласка, заповніть ваші контактні дані.\n\nЦе потрібно для того, щоб кандидати могли з вами зв'язатись.")
        start_contact_registration(update, context)
        return ConversationHandler.END
    
    context.user_data['vacancy'] = {}
    
    keyboard = [["❌ Скасувати створення вакансії"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "📝 Давайте створимо нову вакансію!\n\nВведіть назву посади:\nНаприклад: 'Python розробник' або 'Менеджер з продажів'\n\n"
        "Або натисніть '❌ Скасувати створення вакансії' для виходу",
        reply_markup=reply_markup
    )
    return TITLE

def vacancy_title(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення вакансії":
        return cancel_add_vacancy(update, context)
    
    context.user_data['vacancy']['title'] = update.message.text
    
    keyboard = [["❌ Скасувати створення вакансії"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "🏭 Введіть назву компанії:\nНаприклад: 'IT Company' або 'ТОВ Торгова фірма'\n\n"
        "Або натисніть '❌ Скасувати створення вакансії' для виходу",
        reply_markup=reply_markup
    )
    return COMPANY

def vacancy_company(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення вакансії":
        return cancel_add_vacancy(update, context)
    
    context.user_data['vacancy']['company'] = update.message.text
    
    keyboard = [["❌ Скасувати створення вакансії"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "💰 Введіть зарплату (або 'Не вказано'):\nНаприклад: '1000$' або '25000 грн' або 'Договірна'\n\n"
        "Або натисніть '❌ Скасувати створення вакансії' для виходу",
        reply_markup=reply_markup
    )
    return SALARY

def vacancy_salary(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення вакансії":
        return cancel_add_vacancy(update, context)
    
    context.user_data['vacancy']['salary'] = update.message.text
    
    keyboard = [["❌ Скасувати створення вакансії"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "📝 Введіть опис вакансії:\nОпишіть обов'язки та завдання\nНаприклад: 'Розробка веб-додатків, участь у плануванні проектів...'\n\n"
        "Або натисніть '❌ Скасувати створення вакансії' для виходу",
        reply_markup=reply_markup
    )
    return DESCRIPTION

def vacancy_description(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення вакансії":
        return cancel_add_vacancy(update, context)
    
    context.user_data['vacancy']['description'] = update.message.text
    
    keyboard = [["❌ Скасувати створення вакансії"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "🎯 Введіть вимоги до кандидата:\nНаприклад: 'Досвід роботи 2+ роки, знання Python, SQL...'\n\n"
        "Або натисніть '❌ Скасувати створення вакансії' для виходу",
        reply_markup=reply_markup
    )
    return REQUIREMENTS

def vacancy_requirements(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення вакансії":
        return cancel_add_vacancy(update, context)
    
    context.user_data['vacancy']['requirements'] = update.message.text
    
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    contacts = f"{user_data.full_name}, {user_data.phone}, {user_data.email}"
    context.user_data['vacancy']['contacts'] = contacts
    
    vacancy = context.user_data['vacancy']
    summary = (
        "📋 Перевірте інформацію про вакансію:\n\n"
        f"🏢 Посада: {vacancy['title']}\n"
        f"🏭 Компанія: {vacancy['company']}\n"
        f"💰 Зарплата: {vacancy['salary']}\n"
        f"📝 Опис: {vacancy['description'][:100]}...\n"
        f"🎯 Вимоги: {vacancy['requirements'][:100]}...\n"
        f"📞 Контакти: {vacancy['contacts']}\n\n"
        "Все вірно? Відправте 'Так' для підтвердження або 'Ні' для скасування."
    )
    
    keyboard = [["Так", "Ні"], ["❌ Скасувати створення вакансії"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(summary, reply_markup=reply_markup)
    return CONFIRM

def vacancy_confirm(update: Update, context: CallbackContext) -> int:
    if update.message.text == "❌ Скасувати створення вакансії":
        return cancel_add_vacancy(update, context)
    
    user_choice = update.message.text.lower()
    
    if user_choice in ['так', 'yes', 'ok', 'підтверджую']:
        user = update.effective_user
        vacancy_data = context.user_data['vacancy']
        
        db_session = Session()
        new_vacancy = Vacancy(
            title=vacancy_data['title'],
            company=vacancy_data['company'],
            salary=vacancy_data['salary'],
            description=vacancy_data['description'],
            requirements=vacancy_data['requirements'],
            contacts=vacancy_data['contacts'],
            employer_id=user.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db_session.add(new_vacancy)
        db_session.commit()
        db_session.close()
        
        context.user_data.pop('vacancy', None)
        update.message.reply_text("✅ Вакансія успішно додана!\n\nТепер вона відображатиметься в списку вакансій для шукачів роботи.")
        show_employer_menu(update, context)
        return ConversationHandler.END
        
    elif user_choice in ['ні', 'no', 'cancel', 'скасувати']:
        context.user_data.pop('vacancy', None)
        update.message.reply_text("❌ Створення вакансії скасовано.")
        show_employer_menu(update, context)
        return ConversationHandler.END
    
    else:
        update.message.reply_text("Будь ласка, відправте 'Так' для підтвердження або 'Ні' для скасування.")
        return CONFIRM

def cancel_add_vacancy(update: Update, context: CallbackContext) -> int:
    context.user_data.pop('vacancy', None)
    update.message.reply_text("❌ Створення вакансії скасовано.")
    show_employer_menu(update, context)
    return ConversationHandler.END

def cancel_contact_registration(update: Update, context: CallbackContext) -> int:
    context.user_data.pop('reg_name', None)
    context.user_data.pop('reg_phone', None)
    context.user_data.pop('reg_email', None)
    context.user_data.pop('current_name', None)
    context.user_data.pop('current_phone', None)
    context.user_data.pop('current_email', None)
    
    update.message.reply_text("❌ Реєстрацію контактів скасовано.")
    
    user = update.effective_user
    db_session = Session()
    user_data = db_session.query(User).filter_by(telegram_id=user.id).first()
    db_session.close()
    
    if user_data and user_data.is_employer:
        show_employer_menu(update, context)
    else:
        show_job_seeker_menu(update, context)
    
    return ConversationHandler.END

def search_vacancies(update: Update, context: CallbackContext, search_term: str) -> None:
    db_session = Session()
    vacancies = db_session.query(Vacancy).filter(
        (Vacancy.title.ilike(f'%{search_term}%')) | 
        (Vacancy.description.ilike(f'%{search_term}%')) |
        (Vacancy.company.ilike(f'%{search_term}%')) |
        (Vacancy.requirements.ilike(f'%{search_term}%'))
    ).filter_by(is_active=True).all()
    
    if not vacancies:
        update.message.reply_text(f"❌ На жаль, вакансій за запитом '{search_term}' не знайдено.\n\nСпробуйте інші ключові слова або перегляньте 📋 Список вакансій.")
        db_session.close()
        return
    
    update.message.reply_text(f"🔍 Результати пошуку для '{search_term}':")
    
    for i, vacancy in enumerate(vacancies[:8], 1):
        keyboard = [[InlineKeyboardButton("📨 Подати заявку", callback_data=f"apply_{vacancy.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        is_test = vacancy.employer_id == 999999999
        test_marker = "🧪 " if is_test else ""
        
        message = (
            f"{test_marker}🏢 {vacancy.title}\n"
            f"🏭 Компанія: {vacancy.company}\n"
            f"💰 Зарплата: {vacancy.salary or 'Не вказано'}\n"
            f"📝 {vacancy.description[:120]}...\n"
            f"🎯 Вимоги: {vacancy.requirements[:100]}...\n"
            f"🔢 Результат {i} з {len(vacancies[:8])}\n"
            f"────────────────────"
        )
        update.message.reply_text(message, reply_markup=reply_markup)
    
    if len(vacancies) > 8:
        update.message.reply_text(f"📈 Знайдено {len(vacancies)} вакансій. Показано перші 8.")
    
    db_session.close()

def search_candidates(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("👥 Введіть ключове слово для пошуку кандидатів:\nНаприклад: 'Python' або 'менеджер' або 'Київ'")
    context.user_data['waiting_for_candidate_search'] = True

def handle_candidate_search(update: Update, context: CallbackContext, search_term: str) -> None:
    db_session = Session()
    resumes = db_session.query(Resume).filter(
        (Resume.position.ilike(f'%{search_term}%')) | 
        (Resume.skills.ilike(f'%{search_term}%')) |
        (Resume.experience.ilike(f'%{search_term}%')) |
        (Resume.education.ilike(f'%{search_term}%'))
    ).filter_by(is_active=True).all()
    
    if not resumes:
        update.message.reply_text(f"❌ На жаль, кандидатів за запитом '{search_term}' не знайдено.\n\nСпробуйте інші ключові слова.")
        db_session.close()
        return
    
    update.message.reply_text(f"👥 Результати пошуку кандидатів для '{search_term}':")
    
    for i, resume in enumerate(resumes[:6], 1):
        user_data = db_session.query(User).filter_by(telegram_id=resume.user_id).first()
        user_name = user_data.full_name if user_data else "Користувач"
        
        message = (
            f"👤 Кандидат: {user_name}\n"
            f"🎯 Бажана посада: {resume.position}\n"
            f"💰 Бажана зарплата: {resume.salary or 'Не вказано'}\n"
            f"💼 Досвід: {resume.experience[:80]}...\n"
            f"🎓 Освіта: {resume.education[:80]}...\n"
            f"🛠️ Навички: {resume.skills[:80]}...\n"
            f"📞 Контакти: {resume.contacts}\n"
            f"🔢 Кандидат {i} з {len(resumes[:6])}\n"
            f"────────────────────"
        )
        update.message.reply_text(message)
    
    if len(resumes) > 6:
        update.message.reply_text(f"📈 Знайдено {len(resumes)} кандидатів. Показано перші 6.")
    
    db_session.close()

def handle_job_seeker_registration(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    existing_user = db_session.query(User).filter_by(telegram_id=user.id).first()
    
    if not existing_user:
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_employer=False,
            registration_date=datetime.utcnow()
        )
        db_session.add(new_user)
        db_session.commit()
        update.message.reply_text(
            "🎉 Вітаємо! Ви успішно зареєстровані як шукач роботи!\n\n"
            "Тепер ви можете:\n"
            "• 📋 Переглядати всі вакансії\n"
            "• 🔍 Шукати роботу за ключовими словами\n"
            "• 📄 Створити професійне резюме\n"
            "• 📨 Подавати заявки на вакансії\n"
            "• 👤 Налаштувати ваш профіль"
        )
    else:
        existing_user.is_employer = False
        db_session.commit()
        update.message.reply_text("👋 Вітаємо з поверненням, шукачу роботи!")
    
    db_session.close()
    
    update.message.reply_text("📝 Для повноцінної роботи з ботом рекомендуємо заповнити ваші контактні дані.\n\nНатисніть '📞 Контакти' в меню щоб додати ваш телефон та email.")
    show_job_seeker_menu(update, context)

def handle_employer_registration(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    existing_user = db_session.query(User).filter_by(telegram_id=user.id).first()
    
    if not existing_user:
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_employer=True,
            registration_date=datetime.utcnow()
        )
        db_session.add(new_user)
        db_session.commit()
        update.message.reply_text(
            "🎉 Вітаємо! Ви успішно зареєстровані як роботодавець!\n\n"
            "Тепер ви можете:\n"
            "• 📝 Створювати та публікувати вакансії\n"
            "• 📊 Керувати вашими оголошеннями\n"
            "• 📨 Переглядати заявки кандидатів\n"
            "• 🔍 Шукати відповідних спеціалістів\n"
            "• 👤 Налаштувати ваш профіль"
        )
    else:
        existing_user.is_employer = True
        db_session.commit()
        update.message.reply_text("👋 Вітаємо з поверненням, роботодавче!")
    
    db_session.close()
    
    update.message.reply_text("📝 Для додавання вакансій необхідно заповнити ваші контактні дані.\n\nНатисніть '📞 Контакти' в меню щоб додати ваш телефон та email.")
    show_employer_menu(update, context)

def show_help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "ℹ️ Довідка WorkUA Helper\n\n"
        "Для шукачів роботи:\n"
        "• 📋 Список вакансій - перегляд всіх активних вакансій\n"
        "• 🔍 Пошук вакансій - пошук за ключовими словами\n"
        "• 📄 Моє резюме - створення та управління резюме\n"
        "• 📨 Мої заявки - перегляд статусів поданих заявок\n"
        "• 👤 Мій профіль - перегляд ваших даних\n"
        "• 📞 Контакти - оновлення контактної інформації\n\n"
        "Для роботодавців:\n"
        "• 📝 Додати вакансію - створення нової вакансії\n"
        "• 📊 Мої вакансії - управління вашими вакансіями\n"
        "• 📨 Заявки на вакансії - перегляд та управління заявками\n"
        "• 🔍 Пошук кандидатів - пошук за ключовими словами\n\n"
        "Зв'яжіться з нами для технічної підтримки!"
    )
    update.message.reply_text(help_text)

def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    
    if context.user_data.get('waiting_for_search'):
        search_vacancies(update, context, text)
        context.user_data['waiting_for_search'] = False
        return
    
    elif context.user_data.get('waiting_for_candidate_search'):
        handle_candidate_search(update, context, text)
        context.user_data['waiting_for_candidate_search'] = False
        return
    
    elif text == "📋 Список вакансій":
        show_vacancies_list(update, context)
    elif text == "🔍 Пошук вакансій":
        update.message.reply_text("🔍 Введіть ключове слово для пошуку вакансій:\nНаприклад: 'Python' або 'менеджер' або 'Київ'")
        context.user_data['waiting_for_search'] = True
    elif text == "📄 Моє резюме":
        show_my_resume_menu(update, context)
    elif text == "📨 Мої заявки":
        show_my_applications(update, context)
    elif text == "👤 Мій профіль":
        show_user_profile(update, context)
    elif text == "📞 Контакти":
        start_contact_registration(update, context)
    elif text == "ℹ️ Допомога":
        show_help(update, context)
    elif text == "↩️ Головне меню":
        show_main_menu(update, context)
    
    elif text == "📝 Додати вакансію":
        start_add_vacancy(update, context)
    elif text == "📊 Мої вакансії":
        show_my_vacancies(update, context)
    elif text == "📨 Заявки на вакансії":
        show_employer_applications(update, context)
    elif text == "🔍 Пошук кандидатів":
        search_candidates(update, context)
    
    elif text == "📋 Знайти вакансії":
        handle_job_seeker_registration(update, context)
    elif text == "📝 Подати вакансію":
        handle_employer_registration(update, context)
    
    elif text == "📝 Створити резюме":
        start_create_resume(update, context)
    elif text == "🔄 Оновити ще щось":
        start_update_resume(update, context)
    elif text == "👀 Переглянути резюме":
        show_my_resume(update, context)
    elif text == "↩️ Назад до меню резюме":
        show_my_resume_menu(update, context)
    elif text == "✅ Так, видалити":
        confirm_delete_resume(update, context)
    elif text == "❌ Ні, скасувати":
        update.message.reply_text("❌ Видалення скасовано.")
        show_my_resume_menu(update, context)
    elif text == "❌ Видалити резюме":
        delete_resume(update, context)
    elif text == "🔄 Оновити резюме":
        start_update_resume(update, context)
    
    elif text == "❌ Скасувати реєстрацію":
        cancel_contact_registration(update, context)
    elif text == "❌ Скасувати створення резюме":
        cancel_resume_creation(update, context)
    elif text == "❌ Скасувати оновлення":
        cancel_resume_update(update, context)
    elif text == "❌ Скасувати створення вакансії":
        cancel_add_vacancy(update, context)
    elif text == "↩️ Назад":
        show_job_seeker_menu(update, context)
    
    else:
        update.message.reply_text("Оберіть дію з меню 👆")

def reset(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_session = Session()
    
    db_session.query(Vacancy).filter_by(employer_id=user.id).delete()
    db_session.query(Resume).filter_by(user_id=user.id).delete()
    db_session.query(Application).filter_by(user_id=user.id).delete()
    db_session.query(Application).filter_by(employer_id=user.id).delete()
    
    existing_user = db_session.query(User).filter_by(telegram_id=user.id).first()
    if existing_user:
        db_session.delete(existing_user)
        db_session.commit()
    
    db_session.close()
    
    context.user_data.clear()
    update.message.reply_text("✅ Всі дані скинуті! Починаємо з початку.")
    show_main_menu(update, context)

def main():
    print("🤖 WorkUA Helper бот працює!")
    
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CallbackQueryHandler(handle_application_callback, pattern="^apply_"))
    dispatcher.add_handler(CallbackQueryHandler(handle_application_management, pattern="^(viewed_|call_|message_|reject_)"))
    dispatcher.add_handler(CallbackQueryHandler(handle_delete_vacancy_callback, pattern="^delete_vacancy_"))
    dispatcher.add_handler(CallbackQueryHandler(handle_vacancy_navigation, pattern="^(prev_vacancy|next_vacancy)$"))
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("reset", reset))
    
    vacancy_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^📝 Додати вакансію$"), start_add_vacancy)],
        states={
            TITLE: [
                MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy),
                MessageHandler(Filters.text & ~Filters.command, vacancy_title)
            ],
            COMPANY: [
                MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy),
                MessageHandler(Filters.text & ~Filters.command, vacancy_company)
            ],
            SALARY: [
                MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy),
                MessageHandler(Filters.text & ~Filters.command, vacancy_salary)
            ],
            DESCRIPTION: [
                MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy),
                MessageHandler(Filters.text & ~Filters.command, vacancy_description)
            ],
            REQUIREMENTS: [
                MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy),
                MessageHandler(Filters.text & ~Filters.command, vacancy_requirements)
            ],
            CONFIRM: [
                MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy),
                MessageHandler(Filters.text & ~Filters.command, vacancy_confirm)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex("^❌ Скасувати створення вакансії$"), cancel_add_vacancy)]
    )
    
    contact_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^📞 Контакти$"), start_contact_registration)],
        states={
            REG_NAME: [
                MessageHandler(Filters.regex("^❌ Скасувати реєстрацію$"), cancel_contact_registration),
                MessageHandler(Filters.text & ~Filters.command, register_name)
            ],
            REG_PHONE: [
                MessageHandler(Filters.regex("^❌ Скасувати реєстрацію$"), cancel_contact_registration),
                MessageHandler(Filters.text & ~Filters.command, register_phone)
            ],
            REG_EMAIL: [
                MessageHandler(Filters.regex("^❌ Скасувати реєстрацію$"), cancel_contact_registration),
                MessageHandler(Filters.text & ~Filters.command, register_email)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex("^❌ Скасувати реєстрацію$"), cancel_contact_registration)]
    )
    
    resume_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^📝 Створити резюме$"), start_create_resume)],
        states={
            RESUME_POSITION: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_position)
            ],
            RESUME_SALARY: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_salary)
            ],
            RESUME_EXPERIENCE: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_experience)
            ],
            RESUME_EDUCATION: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_education)
            ],
            RESUME_SKILLS: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_skills)
            ],
            RESUME_ABOUT: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_about)
            ],
            RESUME_CONFIRM: [
                MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation),
                MessageHandler(Filters.text & ~Filters.command, resume_confirm)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex("^❌ Скасувати створення резюме$"), cancel_resume_creation)]
    )
    
    update_resume_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^🔄 Оновити резюме$"), start_update_resume)],
        states={
            UPDATE_RESUME_CHOICE: [
                MessageHandler(Filters.regex("^❌ Скасувати оновлення$"), cancel_resume_update),
                MessageHandler(Filters.text & ~Filters.command, handle_update_resume_choice)
            ],
            UPDATE_RESUME_VALUE: [
                MessageHandler(Filters.regex("^❌ Скасувати оновлення$"), cancel_resume_update),
                MessageHandler(Filters.text & ~Filters.command, handle_update_resume_value)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex("^❌ Скасувати оновлення$"), cancel_resume_update)]
    )
    
    dispatcher.add_handler(vacancy_conv)
    dispatcher.add_handler(contact_conv)
    dispatcher.add_handler(resume_conv)
    dispatcher.add_handler(update_resume_conv)
    
    dispatcher.add_handler(MessageHandler(Filters.regex("^📋 Знайти вакансії$"), handle_job_seeker_registration))
    dispatcher.add_handler(MessageHandler(Filters.regex("^📝 Подати вакансію$"), handle_employer_registration))
    
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
