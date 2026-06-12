# Sean Trades — Metodo Completo ("Back to Basics")

> **Documento di riferimento self-contained.** Raccoglie tutto il metodo estratto dai 3 video
> della serie "Back to Basics" di Sean Trades + dal profilo X. Pensato per essere dato in pasto
> a un altro progetto/AI per ricostruire uno scanner o un sistema di trading.
> **Non è un consiglio finanziario.** È la sintesi di un metodo discrezionale di un creator.

---

## 0. Identità dell'autore

| Campo | Valore |
|---|---|
| Nome | Sean Trades |
| YouTube | Canale "Sean Trades" (ID: UC7Ay4F2gW14aYJhvJQRYkDw) |
| X / Twitter | [@SRxTrades](https://x.com/SRxTrades) |
| Stile | Swing trading di momentum su **opzioni** (principalmente call su breakout) |
| Strumenti citati | Finviz (Groups + Screener), TradingView |
| Claim | ~6-7 cifre/anno; ex trader non profittevole per 2 anni |
| Serie | "Back to Basics" — 3 episodi (EP1 setup, EP2 volume, EP3 psicologia) |

### Citazioni chiave dal profilo X (@SRxTrades)
- "find leading themes and sectors" — scansiona una watchlist di tutti i settori/industrie
- "best momentum screener to find leading small caps" su TradingView
- Volume letto "the RIGHT way" → raddoppio del win rate
- Focus: price action + volume, niente segnali di terzi

---

## 1. Filosofia di fondo

1. **Il prezzo è la verità.** Reagire al prezzo, non predire. Seguire il trend, non combatterlo.
2. **Le azioni salgono a scala** (staircase): salita → consolidamento laterale → breakout → ripeti.
   Mai inseguire ("chasing"), mai FOMO: arriva sempre un nuovo setup.
3. **Compressione = espansione.** Più stretta è la base, più grande il movimento successivo.
4. **Si scommette sull'innovazione USA.** I leader sono temi nuovi (AI, semiconduttori, aerospazio, quantum).
5. **Essere il "miglior perdente":** accettare le perdite velocemente. La gestione del rischio è tutto.

---

## 2. EP1 — Trovare i setup (imbuto a 3 livelli)

### Livello 1 — Settore
- Strumento: **Finviz → Groups** (https://finviz.com/groups.ashx)
- Guardare performance **1 giorno + 1 settimana + 1 mese** (+ contesto 3 mesi)
- Cercare il settore che guida su **tutti** gli orizzonti = forza reale
- Temi/narrative contano: AI, aerospazio, quantum, robotaxi, semiconduttori

### Livello 2 — Industria (sotto-settore)
- Finviz → Groups → menu **"Industry"** (~145 industrie) oppure "Sector+Industry"
- TradingView → Markets → Stocks → Sectors and Industries
- Dentro il settore-leader, isolare l'**industria** che guida (es. Semiconductors dentro Tech)

### Livello 3 — Leader (titoli)
- Screener Finviz con questi filtri:
  | Filtro | Valore | Motivo |
  |---|---|---|
  | Market Cap | > $2B | No micro-cap |
  | Price | > $3 | No penny stock |
  | Avg Volume | > 500K | Liquidità |
  | Relative Volume | > 1 | Attività inusuale |
- Ordinare per **volume / relative volume** → i nomi più liquidi e attivi
- Verificare il setup su TradingView

### Formula composita usata nello scanner (replica del giudizio di Sean)
```
RelativeStrength_score = perf_1settimana × 0.40
                       + perf_1mese      × 0.35
                       + perf_3mesi      × 0.25
```
- 1 sett (40%): momentum recente — dove ruotano i soldi ORA
- 1 mese (35%): la forza dura, non è rimbalzo di un giorno
- 3 mesi (25%): contesto di fondo, filtra i falsi leader
- **Nota dati Finviz:** "Perf Week" arriva come stringa `%` (es. `2.93%`),
  "Perf Month/Quart" come decimali (`0.0152`) → normalizzare alla stessa scala (÷100 la settimana).

---

## 3. EP1 — Price action e candele

- **Timeframe del setup: SEMPRE il daily.** Partire da weekly (il più grande possibile) poi daily.
  Timeframe piccoli = troppi setup rumorosi. Le basi daily/weekly = i movimenti più grandi.
- **La chiusura della candela è la parte più importante.** L'apertura non conta.
  - Chiude sui massimi del range → molto bullish
  - Chiude sui minimi → molto bearish

### Pattern di candela usati
| Pattern | Significato | Uso |
|---|---|---|
| **Hammer** | corpo piccolo, lunga ombra inferiore (≥2× corpo), chiude in alto | Reversal / retest su livello chiave o EMA → venditori intrappolati |
| **Bullish Engulfing** | candela verde che ingloba corpo+ombra della precedente rossa | Conferma forte su retest/continuazione |
| **Doji** | corpo minuscolo, indecisione | Il break del max/min del doji = ottimo breakout |
| **Shooting Star** | inverso dell'hammer, chiude sui minimi | Bearish — evitare long / reversal short |
| **Bearish Engulfing** | candela rossa che ingloba la precedente verde, chiude sui minimi | Bearish |

### Pattern di base / consolidamento (tutti = compressione)
- Bull flag, wedge, pennant, tight consolidation
- Non conta tanto il "nome" del pattern, conta che ci sia **compressione**
- Domanda chiave prima di entrare: *"c'è abbastanza compressione?"* Se sì → buona entry. Se no → stai inseguendo.

---

## 4. EP1 — Trend & medie mobili

- **EMA usate: 8, 21, 50** (esponenziali)
- Prezzo sopra tutte e 3 = uptrend forte. Le EMA agiscono da supporto/resistenza dinamici.
- "Smart money" compra al prezzo medio → ogni retest dell'EMA in uptrend = possibile rimbalzo
- Comprare il **breakout** è il momento migliore (specie con volume), non sull'estensione
- Prezzo sotto le EMA → stare fuori o valutare put

### Confluenza per evitare breakout falliti (3 regole)
1. Tradare **leader** in settori forti, in uptrend
2. Mercato generale in uptrend (S&P / NASDAQ)
3. **Volume alto sul breakout** + chiusura vicino ai massimi sopra il livello

---

## 5. EP2 — Volume (il cuore del metodo)

### Pattern di volume FORTE (accumulo)
```
Movimento su (alto volume) → consolidamento laterale (BASSO volume) → breakout (alto volume)
```
- Volume basso in consolidamento = istituzioni NON stanno vendendo → continuazione probabile
- Volume alto in consolidamento / sui ribassi = distribuzione → evitare
- Strumento: **Volume MA** su TradingView (style → cloud area). Sopra la "nuvola" = sopra media.

### Accumulo vs Distribuzione
- **Accumulo:** dopo grande discesa, capitolazione (selling climax) con volume enorme sui minimi,
  spesso candela hammer/bullish; poi volume cala nella base; le candele verdi hanno volume alto,
  le rosse quasi nullo → istituzioni comprano. Entry sul breakout della base, su alto volume.
- **Distribuzione:** opposto. Volume alto di vendita sui pop, le candele rosse hanno il volume più alto.
  Su weekly/daily. Per giocare put sul breakdown.

### Concetto guida
> "Il volume è il carburante." Un titolo non può salire su volume basso. Il volume mostra
> l'aggressività di compratori/venditori.

---

## 6. EP2 — Setup operativo completo (checklist A+)

Esempio reali citati: SMCI ($35→$84), AMD, Roblox, Tesla, Uber.

Checklist per un setup A+:
1. ☑️ Grande **base sul daily** (settimane/mesi di consolidamento, non nuovi massimi né minimi)
2. ☑️ Settore/industria **forte** con tema/narrativa (es. AI)
3. ☑️ Prezzo **sopra le EMA** in uptrend pulito (no choppy sotto le medie)
4. ☑️ **Pattern stretto** (bull flag/wedge) verso le EMA
5. ☑️ **Pattern di volume**: alto sulla salita → basso in consolidamento → alto sul breakout
6. ☑️ Entry sul **break del massimo**; stop al **minimo del giorno**
7. ☑️ Target = **livelli chiave** / Fibonacci / massimi precedenti

---

## 7. EP1/EP2 — Selezione opzioni

- **Measuring the move:** misurare la lunghezza della base, dividere per ~2 → tempo minimo necessario.
  Base ~400 giorni → ~200 giorni di scadenza (~6 mesi). Base ~10 giorni → ~2-3 settimane.
- Preferire **swing** (settimane/mesi), MAI 0DTE su questi setup.
- **Scadenze OPEX** (terzo venerdì del mese, NO settimanali "W") = massima liquidità / open interest.
  Tipicamente la prossima OPEX a ~2 settimane di distanza.
- **Strike via ADR** (Average Daily Range): comprare ~1 ADR out-of-the-money.
  Non troppo ITM (delta alto, si muove come l'azione), si vuole leva ma con liquidità.
  Scegliere lo strike vicino all'ADR con il **maggiore open interest**.

---

## 8. EP3 — Psicologia & gestione del rischio

### Mindset
- Un trade è "buono" se hai **seguito il piano** (entry, stop, target, risk), NON se hai fatto soldi.
- Premiarsi per la disciplina, non per il profitto. Essere il "miglior perdente": sbagliare in fretta.

### 4 trappole psicologiche
1. **Overtrading** (noia / fretta) → meno trade di qualità rendono di più.
2. **Revenge trading** → pensa a settimane/mesi, non al singolo giorno.
3. **Oversizing / averaging down** → aumentare size solo gradualmente e solo in profitto.
   **MAI mediare al ribasso su opzioni** (possono andare a zero).
4. **FOMO / chasing** → usare l'estensione dall'EMA come filtro (vedi sotto).

### Anti-overtrading pratici
- **Checklist** obbligatoria prima di ogni trade (momentum + settore forte + mercato sopra EMA + parametri)
- **Staccare dagli schermi** nelle ore a basso volume (~11:30–12:00 ET, lunch). Rientrare in power hour (2–4 PM ET).

### Filtro anti-FOMO (regola dell'ADR)
```
Se distanza(prezzo, EMA8 daily) > 2 × ADR  →  NON tradare (troppo esteso)
```
Esempio: ADR 5%, se il prezzo è >10% sopra l'EMA8 daily → skip. Più vicino all'EMA = meglio.

### 3 regole core
1. **Fissa la size** (size emotivamente sostenibile)
2. **Piano prima di entrare** (sai dove entri e dove esci)
3. **Review ogni sera** (journaling di trade e stato mentale)

### Regole di rischio
- **Mai rischiare più del 5% per trade** (no full-port: un gap down brucia >50%)
- **Size più piccola se il mercato non è favorevole**
- **Aggiungere solo in profitto, mai mediare al ribasso**
- **Misurare sempre il rischio prima** (sapere la perdita max in $ in anticipo)
- **Weekly review**

---

## 9. Pseudo-algoritmo (per implementazione)

```
1. MARKET CONTEXT
   bullish = SPY.close > SPY.EMA21  AND  QQQ.close > QQQ.EMA21
   se non bullish → solo setup A+, size ridotta

2. SECTOR (Finviz Groups, group=Sector)
   per ogni settore: score = perfW*0.40 + perfM*0.35 + perfQ*0.25   (scala decimale!)
   top_sectors = top 3 per score

3. INDUSTRY (Finviz Groups, group=Industry)
   per ogni top_sector: rank industrie presenti con stessa formula
   top_industries = top 3 per settore

4. SCREEN (Finviz Screener) — solo titoli nelle top_industries
   filtri: mktcap>2B, price>3, avgvol>500K, relvol>1, USA

5. TECHNICAL SCORE (daily, ~6 mesi OHLCV) — totale 16 punti
   - market trend            (0-2)
   - EMA stack 8/21/50        (0-3)  +1 per EMA sopra cui sta il prezzo
   - compressione            (0-3)  ATR5/ATR20 basso + range 10gg stretto
   - volume pattern          (0-4)  alto→basso→alto (accumulo)
   - candela                 (0-2)  hammer / bullish engulfing / doji
   - vicinanza breakout      (0-2)  entro 2% del max 10gg o break del max ieri
   grade: A+ ≥85%, A ≥70%, B ≥55%, C ≥40%

6. FILTRO ANTI-CHASING (opzionale, da EP3)
   escludi se distanza(price, EMA8) > 2 × ADR

7. OUTPUT: ranking per score, raggruppato per settore/industria
```

---

## 10. Parametri configurabili (default usati)

| Parametro | Default | Dove |
|---|---|---|
| Pesi RS score | 40/35/25 (1w/1m/3m) | `finviz_sectors.WEIGHTS` |
| Settori top | 3 | scanner |
| Industrie per settore | 3 | `TOP_INDUSTRIES_PER_SECTOR` |
| Titoli per industria | 25 | `MAX_PER_INDUSTRY` |
| EMA | 8, 21, 50 | `technical_analysis` |
| Grade minimo report | B | `MIN_GRADE` |
| Rischio max/trade | 5% | regola EP3 (non automatizzata) |
| Filtro estensione | 2 × ADR dall'EMA8 | regola EP3 |

---

## 11. Fonti

- EP1: "The Exact Process I Use To Find Trades" — https://www.youtube.com/watch?v=Re_v6fqxoPE
- EP2: "3 Things That Forever Changed How I Trade" — https://www.youtube.com/watch?v=Gap6i_WDcjc
- EP3: "The real reason why you're still an unprofitable trader" — https://www.youtube.com/watch?v=JBcHk-CX0g4
- X: https://x.com/SRxTrades
- Trascrizioni complete: `.tmp/transcript.txt`, `.tmp/transcript_EP2.txt`, `.tmp/transcript_EP3.txt`
