import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from itertools import product
from io import StringIO

st.set_page_config(page_title="Punta-Punta | Scanner Surebet", page_icon="⚽", layout="wide")

BOOKMAKERS = ["bet365", "StarYes", "BetFlag", "SNAI", "Sisal"]
MARKETS = {
    "1X2": ["1", "X", "2"],
    "Over/Under 2.5": ["Over 2.5", "Under 2.5"],
    "Goal/No Goal": ["Goal", "No Goal"],
}
SAMPLE_ROWS = [
    {"sport":"Calcio","evento":"Esempio FC - Demo United","inizio":"2026-11-01 18:00","mercato":"1X2","esito":"1","bookmaker":"bet365","quota":2.15,"aggiornata_utc":""},
    {"sport":"Calcio","evento":"Esempio FC - Demo United","inizio":"2026-11-01 18:00","mercato":"1X2","esito":"X","bookmaker":"Sisal","quota":3.60,"aggiornata_utc":""},
    {"sport":"Calcio","evento":"Esempio FC - Demo United","inizio":"2026-11-01 18:00","mercato":"1X2","esito":"2","bookmaker":"SNAI","quota":4.10,"aggiornata_utc":""},
    {"sport":"Calcio","evento":"Esempio FC - Demo United","inizio":"2026-11-01 18:00","mercato":"Over/Under 2.5","esito":"Over 2.5","bookmaker":"BetFlag","quota":2.08,"aggiornata_utc":""},
    {"sport":"Calcio","evento":"Esempio FC - Demo United","inizio":"2026-11-01 18:00","mercato":"Over/Under 2.5","esito":"Under 2.5","bookmaker":"StarYes","quota":2.04,"aggiornata_utc":""},
]

st.title("⚽ Punta-Punta — Scanner Surebet")
st.caption("Prototipo web · calcio · senza exchange · quote manuali/importate finché non è configurata una fonte dati autorizzata")

with st.sidebar:
    st.header("Impostazioni")
    bankroll = st.number_input("Capitale totale per operazione (€)", min_value=1.0, max_value=1_000_000.0, value=100.0, step=10.0)
    min_roi = st.number_input("Rendimento minimo da mostrare (%)", min_value=0.0, max_value=100.0, value=0.1, step=0.1)
    max_age = st.number_input("Età massima quote (minuti; 0 = ignora)", min_value=0, max_value=10080, value=30, step=5)
    st.divider()
    st.subheader("Bookmaker")
    selected_books = st.multiselect("Considera questi siti", BOOKMAKERS, default=BOOKMAKERS)
    st.caption("Il filtro seleziona i bookmaker inclusi nei calcoli; non attiva da solo il recupero automatico.")

tab_scan, tab_quotes, tab_bonus, tab_help = st.tabs(["🔎 Scanner", "📥 Quote", "🎁 Bonus", "ℹ️ Guida"])

def parse_upload(uploaded):
    if uploaded is None:
        return pd.DataFrame(SAMPLE_ROWS)
    try:
        return pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Non riesco a leggere il CSV: {e}")
        return pd.DataFrame(columns=list(SAMPLE_ROWS[0].keys()))

def validate_quotes(df):
    required = ["sport","evento","inizio","mercato","esito","bookmaker","quota"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Mancano colonne obbligatorie: {', '.join(missing)}"
    out = df.copy()
    for c in required:
        out[c] = out[c].astype(str).str.strip()
    out["quota"] = pd.to_numeric(out["quota"], errors="coerce")
    out = out[(out["sport"].str.lower() == "calcio") & out["quota"].notna() & (out["quota"] > 1.0)]
    out = out[out["bookmaker"].isin(BOOKMAKERS)]
    if "aggiornata_utc" not in out.columns:
        out["aggiornata_utc"] = ""
    return out, None

def quote_age_minutes(value):
    if pd.isna(value) or not str(value).strip():
        return None
    try:
        ts = pd.to_datetime(value, utc=True)
        return max(0.0, (pd.Timestamp.now(tz="UTC") - ts).total_seconds()/60)
    except Exception:
        return None

def calculate_opportunities(df, capital, min_roi_pct, max_age_minutes, books):
    found = []
    if df.empty:
        return pd.DataFrame()
    df = df[df["bookmaker"].isin(books)].copy()
    if max_age_minutes > 0:
        ages = df["aggiornata_utc"].apply(quote_age_minutes)
        df = df[ages.isna() | (ages <= max_age_minutes)]
    group_cols = ["evento", "inizio", "mercato"]
    for keys, group in df.groupby(group_cols, dropna=False):
        event, kickoff, market = keys
        expected = MARKETS.get(market)
        if not expected:
            continue
        # For each outcome, take the best quote per bookmaker/outcome.
        best = {}
        for outcome in expected:
            rows = group[group["esito"] == outcome].sort_values("quota", ascending=False)
            if rows.empty:
                break
            best[outcome] = rows.iloc[0]
        if len(best) != len(expected):
            continue
        # Prevent duplicate selections from the same bookmaker where possible.
        chosen = [best[o] for o in expected]
        if len(set(r["bookmaker"] for r in chosen)) != len(chosen):
            # Search combinations of available quotes to ensure each outcome can be covered
            options = []
            for outcome in expected:
                rows = group[group["esito"] == outcome].sort_values("quota", ascending=False)
                if rows.empty:
                    options = []
                    break
                options.append([r for _, r in rows.iterrows()])
            valid = []
            if options:
                for combo in product(*options):
                    if len(set(r["bookmaker"] for r in combo)) == len(combo):
                        valid.append(combo)
                if valid:
                    chosen = max(valid, key=lambda combo: sum(1/float(r["quota"]) for r in combo))
                else:
                    continue
            else:
                continue
        odds = [float(r["quota"]) for r in chosen]
        inv_sum = sum(1/q for q in odds)
        roi = (1/inv_sum - 1) * 100
        if inv_sum >= 1 or roi < min_roi_pct:
            continue
        stakes = [capital * (1/q) / inv_sum for q in odds]
        returns = [stakes[i] * odds[i] for i in range(len(odds))]
        profit = min(returns) - capital
        # Require all outcomes in the market to be covered.
        row = {
            "Evento": event,
            "Inizio": kickoff,
            "Mercato": market,
            "Somma inversi": round(inv_sum, 5),
            "ROI teorico %": round(roi, 3),
            "Profitto teorico €": round(profit, 2),
            "Capitale €": round(capital, 2),
            "Dettaglio": " | ".join(f"{expected[i]}: {chosen[i]['bookmaker']} @ {odds[i]:.2f}, puntata {stakes[i]:.2f} €" for i in range(len(expected))),
            "Quote aggiornate UTC": " / ".join(str(chosen[i].get("aggiornata_utc","")) for i in range(len(expected))),
        }
        found.append(row)
    if not found:
        return pd.DataFrame(columns=["Evento","Inizio","Mercato","ROI teorico %","Profitto teorico €","Capitale €","Dettaglio"])
    return pd.DataFrame(found).sort_values("ROI teorico %", ascending=False)

with tab_quotes:
    st.subheader("Quote disponibili")
    st.write("Carica un CSV con le quote, oppure usa i dati dimostrativi. I dati dimostrativi non sono quote reali.")
    uploaded = st.file_uploader("Importa CSV", type=["csv"], key="quotes_csv")
    raw_df = parse_upload(uploaded)
    validated, err = validate_quotes(raw_df)
    if err:
        st.error(err)
        validated = pd.DataFrame(columns=list(SAMPLE_ROWS[0].keys()))
    if not validated.empty:
        st.dataframe(validated, use_container_width=True, hide_index=True)
    else:
        st.info("Non ci sono quote valide da mostrare.")
    st.download_button(
        "Scarica CSV modello",
        data=pd.DataFrame(SAMPLE_ROWS).to_csv(index=False).encode("utf-8"),
        file_name="modello_quote_calcio.csv",
        mime="text/csv"
    )
    st.caption("Formato colonne: sport, evento, inizio, mercato, esito, bookmaker, quota, aggiornata_utc. Per aggiornamenti automatici usare timestamp ISO 8601 UTC, ad esempio 2026-10-24T10:30:00Z.")

with tab_scan:
    st.subheader("Opportunità rilevate")
    if err:
        st.error(err)
    else:
        opportunities = calculate_opportunities(validated, bankroll, min_roi, max_age, selected_books)
        if opportunities.empty:
            st.info("Nessuna surebet rilevata nei dati attualmente caricati. Prova a importare quote aggiornate e mercati compatibili.")
        else:
            st.success(f"Trovate {len(opportunities)} combinazioni potenzialmente profittevoli.")
            st.dataframe(opportunities, use_container_width=True, hide_index=True)
            st.download_button("Esporta opportunità CSV", opportunities.to_csv(index=False).encode("utf-8"), "opportunita_surebet.csv", "text/csv")
        st.warning("I risultati sono teorici. Verifica che le quote siano ancora disponibili, che gli esiti siano esaustivi e che le regole di liquidazione siano compatibili. Il prototipo non piazza scommesse.")

with tab_bonus:
    st.subheader("Registro promozioni")
    st.write("Inserisci le promozioni manualmente. Il valore netto dipende dai termini specifici e non viene stimato automaticamente in questa prima versione.")
    if "bonus_df" not in st.session_state:
        st.session_state.bonus_df = pd.DataFrame([
            {"bookmaker":"bet365","promozione":"Esempio — sostituire con offerta reale","bonus_euro":0.0,"quota_minima":1.5,"requisiti":"Leggere termini e scadenza","scadenza":"","stato":"Da verificare"}
        ])
    edited = st.data_editor(
        st.session_state.bonus_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "bookmaker": st.column_config.SelectboxColumn(options=BOOKMAKERS),
            "bonus_euro": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
            "quota_minima": st.column_config.NumberColumn(min_value=1.01, format="%.2f"),
            "stato": st.column_config.SelectboxColumn(options=["Da verificare","Attiva","Completata","Scaduta"])
        }
    )
    st.session_state.bonus_df = edited
    st.download_button("Esporta registro bonus CSV", edited.to_csv(index=False).encode("utf-8"), "registro_bonus.csv", "text/csv")

with tab_help:
    st.subheader("Come usare il prototipo")
    st.markdown("""
1. Apri **Quote** e scarica il CSV modello.
2. Inserisci una riga per ogni quota disponibile: evento, mercato, esito, bookmaker e quota.
3. Per ogni mercato, usa gli stessi nomi di evento e lo stesso valore di mercato.
4. Per i mercati supportati usa esattamente:
   - `1X2`: `1`, `X`, `2`
   - `Over/Under 2.5`: `Over 2.5`, `Under 2.5`
   - `Goal/No Goal`: `Goal`, `No Goal`
5. Importa il CSV e apri **Scanner**.
6. Modifica il capitale dalla barra laterale.

### Limiti della prima versione
- Le righe di esempio sono dimostrative, non quote reali.
- Non c'è ancora un connettore live configurato per i cinque bookmaker.
- L'abbinamento degli eventi è basato sul nome esatto: nomi diversi dello stesso evento non vengono unificati.
- Non sono ancora modellate le regole specifiche dei bookmaker, i limiti di puntata, i mercati annullati, i pareggi in mercati a due esiti con regole particolari, né le imposte.
- Le promozioni sono registrate, ma il loro valore economico va analizzato in un modulo successivo.
- Non inserire credenziali dei bookmaker in questa app e non automatizzare accessi che violino i termini dei siti.
""")
    st.subheader("Stato integrazioni")
    st.dataframe(pd.DataFrame([
        {"Bookmaker": b, "Stato quote": "Da configurare/verificare", "Metodo": "API/feed autorizzato o importazione CSV"}
        for b in BOOKMAKERS
    ]), use_container_width=True, hide_index=True)

st.divider()
st.caption(f"Prototipo locale-web · sessione iniziata {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Nessuna scommessa viene piazzata automaticamente.")
