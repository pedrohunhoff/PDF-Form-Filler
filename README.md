<<<<<<< HEAD
# 🏠 Ibiti Visitors
### Automatic Access Request — Parque Ibiti do Paço

---

## 📋 What this application does

- Registers your data as a resident (saved permanently)
- Registers frequent visitors with all form data
- Generates the filled PDF request automatically with one click
- Support for single day or period up to 3 days
- Up to 5 visitors per request

---

## 🚀 Installation (one time only)

### Prerequisite: Python 3.8 or higher

Check if Python is installed by opening the **Terminal** (or **Command Prompt** on Windows) and typing:

```
py --version
```

### Step 1 — Install dependencies

Open the terminal in the application folder and run:

```
pip install -r requirements.txt
```

---

### Step 2 — Start the application

In the terminal, inside the application folder:

```
py app.py
```

You will see the message:
```
🏠 Ibiti Visitors - Starting...
👉 Open in browser: http://localhost:5000
```

---

### Step 3 — Open in browser

Open your browser (Chrome, Firefox, Edge...) and access:

**http://localhost:5000**

---

## 📱 How to use

1. **My Data** → Fill in your resident data (done only once)
2. **Visitors** → Register people who visit your house
3. **Generate PDF** → Select visitors, choose the date and click "Generate PDF"
4. The filled PDF will be downloaded automatically — just print and sign!

---

## 📁 Important files

- `app.py` — The main application
- `Requerimento_Visitante_Vazio.pdf` — The blank form (don't delete!)
- `data/owner.json` — Your saved data
- `data/visitors.json` — Registered visitors
- `output/` — Generated PDFs

---

## ❓ Frequently asked questions

**Does the application close by itself?**  
Leave the terminal open while using the application.

**How to stop the application?**  
In the terminal, press `Ctrl + C`.

**Can I use it on mobile?**  
Yes! With the app running on the computer, access from mobile using your computer's IP instead of `localhost`.
