# Wedding Photo App — 26 Ottobre 2026 · Triggiano (BA)

Web app leggera per ~80 invitati: dal viaggio Veglie / Campi Salentina → Triggiano alla festa.
Accesso via QR code, nessuna registrazione, solo password evento.

## 1. Test in locale

```powershell
Set-Location "C:\Users\ingro\Desktop\wedding-photo-app"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Apri poi:
- http://127.0.0.1:5000/ → landing
- http://127.0.0.1:5000/upload → password evento `26ottobre2026`
- http://127.0.0.1:5000/gallery → galleria
- http://127.0.0.1:5000/qr → pagina QR stampabile
- http://127.0.0.1:5000/admin → password admin `admin26ottobre`

Per cambiare nomi/password in locale modifica `config.py` oppure usa env:
```powershell
$env:COUPLE_NAMES="Francesco e Marta"; $env:EVENT_PASSWORD="26ottobre2026"; python app.py
```

## 2. Deploy su Render (piano free)

1. Crea repo GitHub con questa cartella, oppure collega la cartella.
2. Su https://dashboard.render.com → New → Web Service → seleziona il repo.
3. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment: Python 3
4. Environment Variables:
   - `SECRET_KEY` = stringa lunga casuale
   - `EVENT_PASSWORD` = `26ottobre2026`
   - `ADMIN_PASSWORD` = password segreta solo sposi
   - `PUBLIC_URL` = URL pubblico Render (es. `https://wedding-photo-app.onrender.com`)
   - `COUPLE_NAMES` = `Francesco e Marta`
5. Deploy. In alternativa il `render.yaml` già incluso configura tutto.
6. Dopo il primo deploy: apri `/admin` → imposta il `PUBLIC_URL` reale → Rigenera QR.

> ⚠️ Piano free = filesystem effimero: a ogni riavvio/deploy gli upload si cancellano.
> Durante la festa scarica spesso lo ZIP da `/admin/download`.

## 3. QR code per i tavoli

1. Apri `https://TUO-APP.onrender.com/qr` da PC.
2. Verifica che il link sotto il QR sia `.../upload`.
3. Clicca "Scarica QR code in PNG" → stampa in alta qualità (min 6×6 cm, border 4 già incluso).
4. Testa la scansione con 2-3 telefoni diversi (iPhone + Android).
5. Stampa e metti un QR per tavolo + uno all'ingresso. Aggiungi sotto il link in chiaro come fallback.

## 4. Checklist giorno del matrimonio

- [ ] Render attivo (apri landing da cellulare con 4G, no Wi-Fi casa).
- [ ] Password evento comunicata via WhatsApp agli invitati.
- [ ] QR stampato e testato, link fallback leggibile.
- [ ] Prova upload reale: 3 foto da 2 telefoni → verifica compressione, galleria, filtro Momento.
- [ ] Spazio e contatore visibili in `/admin`.
- [ ] Primo backup ZIP scaricato prima della cerimonia, poi ogni 1-2 ore.
- [ ] Telefono organizzatore con login admin attivo + password salvata.
- [ ] Avvisa gli invitati: "Inquadrate il QR sul tavolo e caricate dal viaggio alla festa!".
- [ ] A fine serata: ultimo ZIP + copia `photos.json`.

## 5. Dopo il 26-10-2026

1. Scarica ZIP finale + `photos.json`.
2. Copia tutto su PC/hard disk degli sposi.
3. Su Render: Settings → Suspend Service (fermi le 500 ore free).
4. Nessun dato resta online: niente analytics, niente cookie terzi.
