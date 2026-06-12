# Deploy — Sean Trades Scanner Dashboard

## Architettura cloud

```
GitHub repo (codice)  ──►  Streamlit Community Cloud  ──►  URL pubblico
                                    │
                                    ├─ esegue lo scan live (finvizfinance + yfinance, no API key)
                                    └─ risultati salvati nell'istanza (effimeri)
```

**Nessuna chiave API richiesta:** Finviz e Yahoo Finance sono gratuiti e pubblici.
Quindi non servono "secrets" su Streamlit Cloud.

## Passi per il deploy

### 1. Push del codice su GitHub
```bash
cd /Users/dodomac/Desktop/dodosean
git add .
git commit -m "Sean Trades scanner + Streamlit dashboard"
gh repo create sean-trades-scanner --private --source=. --push
```
(`--private` tiene il repo privato; Streamlit Cloud può comunque accedervi
dopo che autorizzi l'app su GitHub.)

### 2. Crea l'app su Streamlit Cloud
1. Vai su https://share.streamlit.io
2. Login con lo stesso account GitHub (**zlatandodo**)
3. **New app** → seleziona il repo `sean-trades-scanner`
4. **Main file path:** `app.py`
5. **Branch:** `main`
6. Click **Deploy**

In ~2 minuti l'app è online a un URL tipo:
`https://sean-trades-scanner.streamlit.app`

### 3. Accesso da telefono
Apri l'URL dal browser del telefono → la dashboard è responsive.
Puoi salvarla come icona sulla home (Aggiungi a schermata Home).

## Note importanti

### Storico scan sul cloud
Su Streamlit Cloud il filesystem è **effimero** (si resetta a ogni riavvio).
Lo "Storico" mostrerà solo gli scan fatti dall'istanza corrente.
- Per **storico persistente** servono opzioni extra (DB o commit CSV su repo).
- Il cron settimanale sul Mac salva comunque lo storico **in locale**.

### App che "dorme"
Le app gratuite di Streamlit Cloud vanno in sleep dopo inattività.
Al primo accesso si risvegliano in ~30s. Normale.

### Aggiornare l'app
Ogni `git push` aggiorna automaticamente l'app sul cloud.

## Alternativa: tutto in locale
Se preferisci non usare il cloud:
```bash
cd /Users/dodomac/Desktop/dodosean
streamlit run app.py
```
Apri http://localhost:8501
