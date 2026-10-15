from database.db import init_db, seed_enterprise_data

if __name__ == "__main__":
    init_db(force_recreate=True)
    seed_enterprise_data()
    print("Enterprise database successfully reset and seeded!")
