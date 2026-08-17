# Haryana Medical Reimbursement — Claim Generator (Streamlit)

Ek hospital bill PDF upload karo → app **Essentiality Certificate (.docx)**
aur **Working Out Sheet (.xlsx)** dono generate kar deta hai, Google Gemini
(ya Anthropic Claude) se data extract karke aur PGI rate-schedule files se
rates lookup karke.

---

## 📁 Is repo mein kya hai

```
haryana-medical-app/
├── app.py                     ← Streamlit app (yahi chalega)
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example   ← isko copy karke secrets.toml banao (local ke liye)
├── src/
│   ├── prompts.py             ← extraction instructions (dono AI providers ke liye common)
│   ├── llm_extract.py         ← Gemini + Claude dono call karne ka code
│   ├── rate_lookup.py         ← PGI rate files se lookup karne ka logic
│   ├── ec_builder.py          ← EC .docx banata hai
│   └── workout_builder.py     ← Workout .xlsx banata hai
└── data/                      ← saari template + reference files (already included)
    ├── MASTER_TEMPLATE.docx
    ├── REFERENCE_COMPLETED_EXAMPLE.docx
    ├── Working_Out_Sheet_BASE_TEMPLATE.xlsx
    ├── Fixed_Test_Remarks_REFERENCE.xlsx
    ├── PGI_Rate_Quick_Reference.xlsx
    ├── haryana_package_rates.xlsx
    ├── Approved_Example_Kamlesh_Kumari.xlsx
    └── Approved_Example_Ramavatar.xlsx
```

Saari zaroori files already `data/` folder mein daal di gayi hain — kuch
alag se upload nahi karna, seedha GitHub par push kar do.

---

## 🚀 Step-by-step: GitHub par daalna

1. **GitHub par naya repo banao** (github.com → New repository → naam do,
   e.g. `haryana-medical-claims` → Create, README/gitignore mat add karo,
   yeh sab already hai).
2. Is zip ko apne computer par extract karo.
3. Terminal mein extract ki hui folder mein jao aur yeh commands chalao:
   ```bash
   cd haryana-medical-app
   git init
   git add .
   git commit -m "Initial commit - EC + Workout Sheet generator"
   git branch -M main
   git remote add origin https://github.com/<your-username>/haryana-medical-claims.git
   git push -u origin main
   ```
   (`<your-username>` apne GitHub username se replace karo.)

> ⚠️ `.streamlit/secrets.toml` (agar banaya ho) `.gitignore` mein already hai
> — woh kabhi GitHub par push nahi hoga. Sirf `secrets.toml.example` push
> hoga, jisme koi real key nahi hai.

---

## 🌐 Step-by-step: Streamlit Community Cloud par deploy karna

1. [share.streamlit.io](https://share.streamlit.io) par jao, GitHub se login karo.
2. **"New app"** → apna repo (`haryana-medical-claims`) select karo → branch `main` → main file path: `app.py`.
3. **Deploy karne se pehle "Advanced settings" → Secrets** mein yeh paste karo:
   ```toml
   GEMINI_API_KEY = "AIzaSy...................."
   ANTHROPIC_API_KEY = ""
   ```
   (Claude abhi nahi chahiye to doosri line khali chhod do ya hata do.)
4. **Deploy** dabao. 2-3 minute mein app live ho jayega, ek public URL milega
   (e.g. `https://haryana-medical-claims.streamlit.app`).
5. Jab bhi templates/rules update karne hon, bas GitHub repo mein naya
   commit push karo — Streamlit Cloud khud redeploy kar dega.

---

## 🔑 Google Gemini API key kaise banayein

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) par jao (Google account se login).
2. **"Create API key"** dabao → key copy karo.
3. Yeh key kahin bhi paste kar sakte ho:
   - **Local testing:** `.streamlit/secrets.toml.example` ko copy karke
     `.streamlit/secrets.toml` banao, usme `GEMINI_API_KEY = "..."` daal do.
   - **Streamlit Cloud:** app ke **Settings → Secrets** panel mein daal do (upar dekha).

   ⚠️ **App ki UI mein kahin bhi API key type karne ka option jaan-bujh kar
   nahi rakha gaya** — key sirf backend Secrets se load hoti hai. UI mein
   sirf itna dikhata hai ki key configured hai ya nahi ("🔒 API key
   configured" / "❌ not configured"), key kabhi screen par nahi aati. Yeh
   isliye taaki public app use karne wala koi bhi tumhari ya apni key
   paste na kar sake, aur key kabhi accidentally screen-share/screenshot
   mein leak na ho.

Gemini free tier mein bhi reasonable daily quota milta hai — heavy/production
use ke liye Google Cloud billing enable karna better rahega.

---

## 🖱️ App kaise use karein (end-to-end)

1. **Hospital bill upload karo** — PDF ya photos (multiple images bhi upload
   kar sakte ho agar PDF nahi hai).
2. Form bharo:
   - **Claimant:**, **Designation:**, **Department:**
   - **Basic Pay (Rs.):** — agar pata nahi hai to "Leave Basic Pay blank / not
     known" checkbox tick kar do, field disable ho jayega aur Workout Sheet
     mein Room Rent rows "pending" mark ho jayengi.
3. Neeche 3 buttons hain:
   - **EC + WORKOUT** — dono documents ek saath
   - **EC** — sirf Essentiality Certificate
   - **WORKOUT** — sirf Working Out Sheet
4. Jo bhi button dabao, app khud bill padh kar data extract karega aur
   requested file(s) download button ke saath ready kar dega.
5. Neeche ek collapsed **"🔍 View extracted data"** section hai — agar
   double-check karna ho (invoice number sahi se padha gaya ya nahi, etc.)
   to wahan dekh sakte ho. PGI rate schedule mein match na hone wali rows
   ek warning list mein alag se dikhengi.

App ki UI mein AI provider/model/API-key jaisi koi cheez nahi dikhti —
yeh sab `app.py` ke top par admin config aur Secrets se control hoti hai
(neeche dekho).

---

## 🧠 Provider (Gemini/Claude) ya model badalna ho to

UI mein koi dropdown/option nahi hai — jaan-bujh kar, taaki interface
saaf rahe. Provider `app.py` ki shuru ki lines mein constants ke through
control hota hai:

```python
PROVIDER = "gemini"                 # "gemini" ya "claude" kar do
MODEL_NAME = "gemini-2.5-pro"       # e.g. "claude-sonnet-4-6"
```

Claude par switch karna ho:
1. [console.anthropic.com](https://console.anthropic.com) se API key banao.
2. Secrets mein `ANTHROPIC_API_KEY = "sk-ant-..."` add karo.
3. `app.py` mein `PROVIDER = "claude"` kar do, GitHub par push karo — Streamlit
   Cloud khud redeploy kar dega.

Dono providers same `src/prompts.py` instructions use karte hain, isliye
extraction behaviour dono mein consistent rahega — code kahin aur change
nahi karna padta.

---

## 💻 Local par test karna (deploy karne se pehle)

```bash
cd haryana-medical-app
python -m venv venv
source venv/bin/activate        # Windows par: venv\Scripts\activate
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# ab .streamlit/secrets.toml file kholo aur apni real GEMINI_API_KEY daal do

streamlit run app.py
```
Browser mein `http://localhost:8501` khul jayega.

---

## 🖱️ App kaise use karein — quick version

Upar "App kaise use karein (end-to-end)" section dekho.

---

## ⚠️ Known limitations (honest disclosure)

- **EC header block formatting:** original `MASTER_TEMPLATE.docx` ka header
  ek hi merged paragraph hai jisme sab labels tab-separated the (hand-filling
  ke liye design kiya gaya tha). App isse readable "Label: value" lines mein
  rewrite karta hai (same font/size/bold rakhte hue) — bilkul original tab
  positions nahi, par saaf aur professional dikhta hai aur Word mein
  editable hai.
- **Rate matching fuzzy hai:** procedure/test names bill aur government
  schedule mein hamesha exact match nahi karte (spelling variants). App
  `difflib` se fuzzy match karta hai — jo bhi confident match nahi hota,
  use warning list mein flag kar deta hai, guess nahi karta.
- **AI extraction verify zaroor karo** — khaaskar scanned/handwritten
  bills par OCR/vision galti kar sakta hai. Generate se pehle JSON review
  step isi liye diya gaya hai.
- Har naye case ke liye tumhe **Basic Pay** dena zaroori hai warna Room Rent
  rows "pending" mark ho jayengi.

---

## 🔒 Security note

- Kabhi bhi real API key GitHub par commit mat karo. `secrets.toml` hamesha
  `.gitignore` mein rehne do.
- Agar app public URL par live hai to koi bhi is API key se apne bills
  process kar sakta hai (aur tumhara Gemini/Claude quota use hoga) — agar
  sirf apne use ke liye chahiye to Streamlit Cloud app ko **private** rakho
  (Settings → General → App visibility → Private, sirf invited log-in
  wale access kar sakein) ya app mein simple password-gate add karwa lena.
