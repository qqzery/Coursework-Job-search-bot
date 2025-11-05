from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    is_employer = Column(Boolean, default=False)
    registration_date = Column(DateTime, default=datetime.utcnow)
    
    vacancies = relationship("Vacancy", back_populates="employer")
    resumes = relationship("Resume", back_populates="user")
    applications = relationship("Application", back_populates="user")

class Vacancy(Base):
    __tablename__ = 'vacancies'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    company = Column(String(100))
    salary = Column(String(50))
    description = Column(Text)
    requirements = Column(Text)
    contacts = Column(String(200))
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    employer_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    employer = relationship("User", back_populates="vacancies")
    applications = relationship("Application", back_populates="vacancy")

class Resume(Base):
    __tablename__ = 'resumes'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    position = Column(String(100))
    salary = Column(String(100))
    experience = Column(Text, nullable=False)
    education = Column(Text, nullable=False)
    skills = Column(Text, nullable=False)
    about = Column(Text)
    contacts = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")

class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    vacancy_id = Column(Integer, ForeignKey('vacancies.id'), nullable=False)
    employer_id = Column(BigInteger, nullable=False)
    resume_data = Column(Text)
    user_contacts = Column(String(500))
    status = Column(String(20), default="нова")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="applications")
    vacancy = relationship("Vacancy", back_populates="applications")

engine = create_engine('sqlite:///workua.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def add_sample_vacancies():
    """Додати тестові вакансії при створенні бази"""
    session = Session()
    
    existing_vacancies = session.query(Vacancy).count()
    if existing_vacancies > 0:
        print("✅ Вакансії вже додані раніше")
        session.close()
        return
    
    sample_vacancies = [
        {
            "title": "Python Developer",
            "company": "TechSoft Ukraine",
            "salary": "2500$",
            "description": "Шукаємо досвідченого Python розробника для роботи над масштабними веб-проектами. Обов'язки: розробка бекенду, інтеграція API, оптимізація продуктивності. Проект: розробка CRM системи для великої компанії.",
            "requirements": "Досвід роботи з Python 3+ 2+ роки, знання Django/Flask, PostgreSQL, Docker, Git. Англійська - Intermediate+. Знання REST API, ООП, алгоритмів.",
            "contacts": "HR TechSoft, +380501234567, hr@techsoft.ua",
            "category": "IT",
            "employer_id": 999999999,
            "is_active": True
        },
        {
            "title": "Frontend Developer (React)",
            "company": "WebInnovations",
            "salary": "2000$",
            "description": "Розробка сучасних веб-додатків з використанням React. Участь у створенні UI/UX, робота в команді з дизайнерами та бекенд-розробниками. Робота над міжнародними проектами.",
            "requirements": "Досвід з React 2+ роки, знання JavaScript/TypeScript, Redux, HTML5/CSS3, SASS. Досвід роботи з REST API, Git. Розуміння принципів адаптивного дизайну.",
            "contacts": "Recruiter WebInnovations, +380671234567, jobs@webinnovations.com",
            "category": "IT",
            "employer_id": 999999999,
            "is_active": True
        },
        {
            "title": "Full Stack Developer",
            "company": "StartUpHub",
            "salary": "3000$",
            "description": "Повний цикл розробки від ідеї до реалізації. Робота над стартап-проектами в сфері фінтеху. Швидке навчання та кар'єрне зростання. Гнучкий графік, можливість віддаленої роботи.",
            "requirements": "Python/Django, React/Node.js, бази даних (SQL/NoSQL), Docker, AWS/GCP. Досвід 3+ роки. Здатність працювати в команді, самостійність, креативне мислення.",
            "contacts": "CEO StartUpHub, +380631234567, founder@starthub.tech",
            "category": "IT",
            "employer_id": 999999999,
            "is_active": True
        },
        {
            "title": "Junior Java Developer",
            "company": "BankSolutions",
            "salary": "1200$",
            "description": "Ідеальна позиція для початківців розробників. Навчання, менторство, робота над банківськими системами. Стабільна компанія, соціальний пакет, корпоративні бенефіти.",
            "requirements": "Базові знання Java, OOP, SQL, Spring Framework. Бажання вчитися та розвиватися. Англійська - Pre-Intermediate. Логічне мислення, увага до деталей.",
            "contacts": "HR BankSolutions, +380501112233, career@banksolutions.ua",
            "category": "IT",
            "employer_id": 999999999,
            "is_active": True
        },
        {
            "title": "DevOps Engineer",
            "company": "CloudSystems",
            "salary": "3500$",
            "description": "Робота з хмарною інфраструктурою, автоматизація процесів, CI/CD. Відповідальність за стабільність та безпеку систем. Робота з високонавантаженими системами.",
            "requirements": "Docker, Kubernetes, AWS/Azure/GCP, Jenkins, Terraform, Ansible. Досвід 3+ роки. Знання Linux адміністрування, мережевих технологій, моніторингу (Prometheus, Grafana).",
            "contacts": "CTO CloudSystems, +380501234568, tech@cloudsystems.com",
            "category": "IT",
            "employer_id": 999999999,
            "is_active": True
        },
        {
            "title": "Менеджер з продажу",
            "company": "SalesPro Ukraine",
            "salary": "15000 грн + бонуси",
            "description": "Робота з клієнтською базою, пошук нових клієнтів, проведення переговорів, укладання договорів. Робота в дружній команді, корпоративні тренінги.",
            "requirements": "Досвід роботи в продажах 1+ рік, комунікабельність, цілеспрямованість. Бажання заробляти та розвиватися. Навички ведення переговорів.",
            "contacts": "HR SalesPro, +380501234569, hr@salespro.ua",
            "category": "Sales",
            "employer_id": 999999999,
            "is_active": True
        },
        {
            "title": "Маркетолог",
            "company": "DigitalAgency",
            "salary": "18000 грн",
            "description": "Розробка маркетингових стратегій, ведення соціальних мереж, створення контент-планів, аналітика ефективності кампаній. Робота з різноманітними клієнтами.",
            "requirements": "Досвід у маркетингу 1+ рік, знання SMM, Google Analytics, Facebook Ads. Креативність, аналітичне мислення, вміння працювати в команді.",
            "contacts": "HR DigitalAgency, +380501234570, career@digitalagency.ua",
            "category": "Marketing",
            "employer_id": 999999999,
            "is_active": True
        }
    ]
    
    for vacancy_data in sample_vacancies:
        vacancy = Vacancy(
            title=vacancy_data["title"],
            company=vacancy_data["company"],
            salary=vacancy_data["salary"],
            description=vacancy_data["description"],
            requirements=vacancy_data["requirements"],
            contacts=vacancy_data["contacts"],
            category=vacancy_data["category"],
            employer_id=vacancy_data["employer_id"],
            is_active=vacancy_data["is_active"],
            created_at=datetime.utcnow()
        )
        session.add(vacancy)
    
    session.commit()
    session.close()
    print(f"✅ {len(sample_vacancies)} тестових вакансій успішно додано до бази!")

add_sample_vacancies()