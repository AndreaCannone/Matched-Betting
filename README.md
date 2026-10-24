# Punta-Punta — web app prototipo

Web app Streamlit per analizzare surebet punta-punta nel calcio, senza exchange. Non richiede installazione sul computer se pubblicata su Streamlit Community Cloud.

## Pubblicazione senza installare programmi

1. Crea un account GitHub, se non ne hai già uno.
2. Dal sito GitHub crea un nuovo repository, ad esempio `punta-punta-webapp`.
3. Carica `app.py`, `requirements.txt` e questo `README.md` usando l'interfaccia web di GitHub (**Add file → Upload files**).
4. Apri https://share.streamlit.io/ e accedi con GitHub.
5. Seleziona **Create app**, scegli il repository e il branch, e imposta `app.py` come Main file path.
6. Premi **Deploy**. Una volta completato il deploy, Streamlit fornirà un URL pubblico per aprire la web app dal browser.

I nomi delle voci dell'interfaccia possono cambiare leggermente nel tempo.

## Uso

- Apri la scheda **Quote**.
- Scarica il CSV modello, compilalo e importalo.
- Vai su **Scanner** per visualizzare le combinazioni trovate.
- Modifica il capitale totale e il rendimento minimo nella barra laterale.
- La scheda **Bonus** permette di tenere un registro delle promozioni.

## Schema CSV

Colonne obbligatorie:
`sport, evento, inizio, mercato, esito, bookmaker, quota`

Colonna facoltativa:
`aggiornata_utc`

Mercati supportati:
- `1X2`: esiti `1`, `X`, `2`
- `Over/Under 2.5`: esiti `Over 2.5`, `Under 2.5`
- `Goal/No Goal`: esiti `Goal`, `No Goal`

Per timestamp UTC, preferire ISO 8601, ad esempio `2026-10-24T10:30:00Z`.

## Dati automatici

Questa versione non contiene API key né connettori live configurati. Prima di collegare un feed:
- verifica che il provider copra bet365, StarYes, BetFlag, SNAI e Sisal, nei mercati e nelle modalità desiderate;
- verifica termini, licenza, limiti di chiamata, latenza e costi;
- conserva le chiavi API nei **Secrets** dell'hosting, mai nel codice pubblico;
- controlla la freschezza delle quote e la corrispondenza esatta degli eventi/mercati.

Non tentare di aggirare login, CAPTCHA o controlli di accesso. Usa solo modalità di accesso consentite dal provider e dai siti interessati.

## Limiti e avvertenze

- Le quote di esempio sono fittizie.
- Le surebet sono stime matematiche, non garanzie: quote mutate, puntate rifiutate, limiti, mercati annullati o regole di liquidazione diverse possono generare perdite.
- Nessuna scommessa viene piazzata dall'app.
- Il prototipo non calcola ancora il valore netto dei bonus.
- La corrispondenza degli eventi usa il nome esatto: un futuro modulo di normalizzazione dovrà unificare nomi diversi dello stesso evento.
