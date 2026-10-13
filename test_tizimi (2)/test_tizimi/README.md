# 🎓 Test Platformasi — Aqlli Test va Imtihon Nazorati Tizimi (FastAPI & Gemini AI)

Sun'iy intellekt (Google Gemini AI) integratsiyalangan, zamonaviy va to'liq avtomatlashtirilgan onlayn test platformasi.

---

## 🚀 Tizim Imkoniyatlari

### 1. 👨‍🎓 O'quvchi Portali (`/`)
* **Oson kirish:** Ism, familiya va guruhni tanlab, faol testlardan birini boshlash.
* **Test topshirish jarayoni (`/test/{id}`):**
  * Real-vaqtli orqaga hisoblovchi **taymer** (vaqt tugaganda avtomatik topshirish).
  * **Savollar palitrasi (Question Palette):** Har bir savolga bitta bosishda o'tish, javob berilgan (yashil) va berilmagan savollarni ajratib ko'rsatish.
  * **Anti-Cheat nazorati:**
    * Boshqa brauzer tabi yoki dasturga o'tishni (Tab switch / blur) aniqlash va hisoblash.
    * Ekrandan chiqish vaqtida qat'iy modal ogohlantirish.
    * Katta ekran (Fullscreen) rejimi.
    * Nusxa ko'chirish (`Ctrl+C`, `Ctrl+V`), kod ko'rish (`Ctrl+U`, `F12`) va sichqoncha o'ng tugmasini taqiqlash.
  * Testni yakunlashdan oldin javobsiz qolgan savollar bo'yicha ogohlantirish.
* **Batafsil natijalar va tahlil sahifasi (`/result/{attempt_id}`):**
  * Umumiy foiz, baho (A'lo, Yaxshi, Qoniqarli, Qoniqarsiz), to'g'ri va noto'g'ri javoblar soni.
  * **Mavzular bo'yicha o'zlashtirish foizlari** va **Chart.js interaktiv grafigi**.
  * **Gemini AI Pedagogik Tahlili:** O'quvchining kuchli va zaif tomonlari, qaysi mavzularda oqsagani va bilimlarni oshirish uchun aniq amaliy tavsiyalar.
  * Har bir savolning to'liq tahlili (o'quvchi tanlagan javob vs to'g'ri javob va tushuntirish).
  * **Natijani chop etish / PDF formatida saqlash** tugmasi.

---

### 2. 👩‍🏫 O'qituvchi va Admin Boshqaruv Paneli (`/admin`)
* **Dashboard:**
  * Jami o'quvchilar, testlar, savollar, o'rtacha ball statistikasi.
  * So'nggi topshirilgan testlar jadvali.
  * Guruhlar bo'yicha o'zlashtirish reytingi.
* **Guruhlar boshqaruvi:** Guruh qo'shish, tahrirlash, o'chirish va undagi o'quvchilar sonini ko'rish.
* **Mavzular boshqaruvi:** Test mavzularini yaratish va savollar sonini nazorat qilish.
* **Testlar boshqaruvi:** Yangi test yaratish, davomiyligi (daqiqa), o'tish bali, savollarni aralashtirish (shuffle) va faollashtirish sozlamalari.
* **Savollar va Gemini AI Generator:**
  * Qo'lda savol kiritish (mavzu, qiyinlik darajasi, 4 ta variant, to'g'ri javobni tanlash, izoh).
  * **🤖 Gemini AI Test Savollari Generatori:** Mavzu va savollar sonini (1 tadan 30 tagacha) tanlasangiz, AI birdaniga savollarni variantlari va izohlari bilan generatsiya qiladi. Jonli ko'rib chiqib, 1 ta tugma bilan testga qo'shish mumkin.
* **Natijalar va AI Guruh Tahlili:**
  * Barcha natijalarni guruh, test va o'quvchi ismi bo'yicha filtrlash.
  * Natijalarni **CSV formatida yuklab olish**.
  * **🧠 Guruh bo'yicha Gemini AI tahlili:** Butun guruh xatolarini umumlashtirib, o'qituvchiga dars rejasiga o'zgartirish kiritish bo'yicha metodik tavsiyalar berish.
* **Gemini AI Kaliti Sozlamalari:**
  * Interfeysning o'zidan turib Google Gemini API kalitini kiritish va faollashtirish.

---

## 🛠 Ishga Tushirish Qo'llanmasi

### 1-usul: `start_server.bat` orqali (Eng oson)
Loyihaning asosiy papkasidagi `start_server.bat` faylini ikki marta bosing.

### 2-usul: Terminal orqali
```bash
# Virtual muhitni ishga tushirish
.\venv\Scripts\python.exe main.py
```

Server ishga tushgach:
* **O'quvchi portali:** [http://127.0.0.1:8008/](http://127.0.0.1:8008/)
* **O'qituvchi / Admin paneli:** [http://127.0.0.1:8008/admin](http://127.0.0.1:8008/admin)
* **Interaktiv API hujjatlari (Swagger):** [http://127.0.0.1:8008/docs](http://127.0.0.1:8008/docs)

*(Eslatma: Agar 8000-port boshqa dastur tomonidan band bo'lsa, tizim avtomatik tarzda 8008-portda ishga tushadi).*

---

## 🔑 Gemini AI API Kalitini O'rnatish
API kalitni ikki xil usulda ulashingiz mumkin:
1. **Admin paneli orqali:** [http://127.0.0.1:8008/admin](http://127.0.0.1:8008/admin) sahifasiga kirib, **Gemini AI Kaliti** bo'limiga kalitni joylashtirib "Saqlash" tugmasini bosing.
2. **`.env` fayli orqali:** Loyiha papkasidagi `.env` faylini ochib, quyidagicha yozing:
   ```env
   GEMINI_API_KEY=sizning_gemini_api_kalitingiz
   ```

---

## 📂 Loyiha Strukturasi

```
test_tizimi/
│
├── main.py                     # FastAPI asosiy ilovasi va marshrutlar
├── requirements.txt            # Python kutubxonalari
├── start_server.bat            # Windows uchun 1-bosishda ishga tushirish skripti
├── test_verification.py        # Tizimni to'liq tekshiruvchi test skripti
├── .env                        # Maxfiy kalitlar va sozlamalar
│
├── database/
│   ├── database.db             # SQLite ma'lumotlar bazasi
│   ├── schema.sql              # Baza jadvallari sxemasi
│   └── db.py                   # Baza ulanishi va boshlang'ich namunaviy ma'lumotlar
│
├── api/
│   ├── groups.py               # Guruhlar API (CRUD)
│   ├── topics.py               # Mavzular API (CRUD)
│   ├── tests.py                # Testlar API
│   ├── questions.py            # Savollar va variantlar API
│   ├── results.py              # Test topshirish va natijalar statistikasi
│   └── ai.py                   # Gemini AI tahlil va generator API
│
├── services/
│   ├── test_service.py         # Test va savollar mantiqiy xizmati
│   ├── result_service.py       # Ballar va mavzu statistikasini hisoblash
│   └── gemini_service.py       # Gemini AI pedagogik tahlil va test generatsiyasi
│
├── templates/
│   ├── index.html              # O'quvchi boshlang'ich sahifasi
│   ├── test.html               # Test topshirish oynasi (anti-cheat, taymer)
│   ├── result.html             # Natija va AI xulosa sahifasi
│   └── admin.html              # O'qituvchi / Admin to'liq boshqaruv paneli
│
└── static/
    ├── css/
    │   ├── style.css           # O'quvchi va umumiy UI stillari
    │   └── admin.css           # Admin boshqaruv paneli stillari
    └── js/
        ├── main.js             # Bosh sahifa logikasi
        ├── test.js             # Test yechish va anti-cheat nazorati
        ├── result.js           # Natijalar, grafiklar va AI xulosasi
        └── admin.js            # Admin panel va AI generator boshqaruvi
```
