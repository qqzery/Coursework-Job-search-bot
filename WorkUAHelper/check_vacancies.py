# check_vacancies.py
from database import Session, Vacancy

def check_vacancies():
    """Перевірити всі вакансії в базі"""
    db_session = Session()
    
    vacancies = db_session.query(Vacancy).all()
    
    print(f"📊 Всього вакансій в базі: {len(vacancies)}")
    print("\n" + "="*50)
    
    for i, vacancy in enumerate(vacancies, 1):
        print(f"\n{i}. 🏢 {vacancy.title}")
        print(f"   🏭 Компанія: {vacancy.company}")
        print(f"   💰 Зарплата: {vacancy.salary}")
        print(f"   👤 Employer ID: {vacancy.employer_id}")
        print(f"   ✅ Active: {vacancy.is_active}")
        print(f"   📅 Створено: {vacancy.created_at}")
        print(f"   📝 Опис: {vacancy.description[:80]}...")
        print("-" * 50)
    
    db_session.close()

if __name__ == '__main__':
    check_vacancies()