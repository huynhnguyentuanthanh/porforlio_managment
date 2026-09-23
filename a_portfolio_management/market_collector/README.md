\# Market Collector



A unified Dockerized Python 3.12 collector for:



\- local-market crawlers

\- FRED macro/market series

\- weekly Monday-based CSV outputs



This README documents the \*\*collector architecture\*\*, \*\*weekly behavior\*\*, and the \*\*full contents of all key files\*\* in `market\_collector/`.



\---



\# Part 1 — Collector Responsibilities



The collector handles:



\## Crawl sources

\- `imir`

\- `vn30`

\- `sjc`



\## Derived/current-price output collected with `sjc`

\- `gold`



\## FRED sources

\- `dxy`

\- `vix`

\- `wti`

\- `sp500`

\- `us3m`

\- `us2y`

\- `us10y`

\- `us30y`



Each dataset/series is stored in its own CSV under:



```bash

outputs/

```



Examples:



\- `outputs/imir.csv`

\- `outputs/vn30.csv`

\- `outputs/sjc.csv`

\- `outputs/gold.csv`

\- `outputs/us10y.csv`



\---



\# Part 2 — Weekly Collector Design



\## Output behavior



Each dataset/series is stored in its own CSV file under:



```bash

outputs/

```



Each CSV contains \*\*weekly rows\*\*.



This means:



\- `gold.csv` contains weekly gold rows

\- `sjc.csv` contains weekly SJC rows

\- `vn30.csv` contains weekly VN30 rows

\- and so on



\## Weekly standard



All collector outputs use:



\- \*\*one row per week\*\*

\- `date` = \*\*Monday of the week\*\* for that dataset



\## Final weekly standard used by this project



This project uses the following weekly setup:



\- `imir` uses \*\*week-start Monday\*\*

\- `vn30` uses \*\*week-start Monday\*\*

\- `sjc` daily values are grouped into \*\*week-start Monday\*\* buckets

\- `gold` values collected in `sjc.py` are normalized into \*\*weekly Monday rows\*\*

\- `fredapi` data is fetched and normalized into \*\*weekly Monday rows\*\*

\- saved `date` for all outputs is the \*\*Monday of the week\*\*



\### FRED weekly standard



For FRED series:



\- data is fetched from FRED using `fredapi`

\- the saved output is normalized to \*\*one weekly row per Monday\*\*

\- if source observations are daily or business-daily, they are grouped into \*\*Monday-based weekly buckets\*\*

\- the final saved `date` is always the \*\*Monday of that week\*\*

\- the last available observation within each Monday-based week bucket is kept



\### Snapshot collector weekly standard



For snapshot-based collectors such as `imir` and `vn30`:



\- the current snapshot is mapped to the \*\*Monday of the current week\*\*

\- repeated runs within the same week overwrite the same Monday row

\- Monday through Sunday runs all map to the same week’s Monday

\- snapshot collectors therefore use a \*\*Monday-anchored weekly date\*\*



\### SJC weekly standard



For `sjc`:



\- daily SJC observations are collected

\- each observation is mapped to the \*\*Monday of its week\*\*

\- the last available daily observation in each Monday-based week bucket is kept

\- final saved output is therefore \*\*weekly Monday-based data\*\*



\### Gold weekly standard



For `gold`:



\- `gold` is collected inside `sjc.py`, not from FRED

\- the current gold value is extracted from the same source page used by `sjc`

\- the collected observation is mapped to the \*\*Monday of its week\*\*

\- repeated runs within the same week overwrite the same Monday row

\- final saved output is therefore \*\*weekly Monday-based data\*\*



\### Monday mapping rule



For Monday-based weekly collectors:



\- if the source date is Monday, use that same Monday

\- if the source date is Tuesday through Sunday, map back to the most recent Monday

\- do not map to a future date



\---



\# Part 3 — FRED Mapping



| Output name | FRED series id |

|---|---|

| `dxy` | `DTWEXBGS` |

| `vix` | `VIXCLS` |

| `wti` | `DCOILWTICO` |

| `sp500` | `SP500` |

| `us3m` | `DGS3MO` |

| `us2y` | `DGS2` |

| `us10y` | `DGS10` |

| `us30y` | `DGS30` |

| `us\_headline\_cpi` | `CPIAUCSL` |

| `us\_core\_cpi` | `CPILFESL` |

| `us\_real\_gdp` | `GDPC1` |



\## Treasury normalization



Treasury yield series are normalized as raw percentage values already supplied by FRED, so:



\- `us3m`

\- `us2y`

\- `us10y`

\- `us30y`



do \*\*not\*\* require the Yahoo-style divide-by-10 normalization.



\---



\# Part 4 — FRED Operating Model



`fredapi` is used to fetch official macro/market series from FRED.



Compared with unofficial Yahoo access, this approach is more stable for programmatic collection of macro and rate data.



\## Recommended rule



For FRED series, run \*\*one series at a time\*\* if desired for operational simplicity, but the collector logic can support individual or selected runs safely.



\## CLI behavior used by this project



\- `--all` runs all crawl collectors:

&#x20; - `imir`

&#x20; - `vn30`

&#x20; - `sjc`

\- when `sjc` runs, it also updates `gold`

\- FRED tasks must be run with `--only`



\### Recommended full-history pattern



```bash

python market\_collector.py --only dxy --fred-mode full

python market\_collector.py --only wti --fred-mode full

python market\_collector.py --only us10y --fred-mode full

```



\### Recommended incremental pattern



```bash

python market\_collector.py --only dxy --fred-mode incremental

python market\_collector.py --only wti --fred-mode incremental

python market\_collector.py --only us10y --fred-mode incremental

```



\## Production recommendation



\- run crawl tasks together using `--all` if desired

\- run FRED series individually using `--only`

\- schedule periodic incremental refreshes



This keeps the collection model simple and consistent.



\---



\# Part 5 — File Contents



\## 5.1 `requirements.txt`



```txt

pandas==2.2.2

requests==2.32.3

fredapi==0.5.2

beautifulsoup4==4.12.3

selenium==4.24.0

```



\---



\## 5.2 `Dockerfile`



```dockerfile

FROM python:3.12-slim



ENV DEBIAN\_FRONTEND=noninteractive

ENV SSL\_CERT\_FILE=/etc/ssl/certs/ca-certificates.crt

ENV REQUESTS\_CA\_BUNDLE=/etc/ssl/certs/ca-certificates.crt



WORKDIR /app



RUN apt-get update \&\& apt-get install -y \\

&#x20;   chromium \\

&#x20;   chromium-driver \\

&#x20;   fonts-liberation \\

&#x20;   ca-certificates \\

&#x20;   openssl \\

&#x20;   \&\& rm -rf /var/lib/apt/lists/\*



COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt



COPY . /app



CMD \["python", "market\_collector.py", "--all"]

```



\---



\## 5.3 `docker-compose.yml`



```yaml

services:

&#x20; market-collector:

&#x20;   build: .

&#x20;   container\_name: market-collector

&#x20;   working\_dir: /app

&#x20;   volumes:

&#x20;     - .:/app

&#x20;   environment:

&#x20;     - FRED\_API\_KEY=${FRED\_API\_KEY}

&#x20;   command: python market\_collector.py --all

```



\---



\## 5.4 `collectors/common.py`



```python

from pathlib import Path

import pandas as pd





OUTPUT\_DIR = Path("outputs")

ERROR\_DIR = Path("errors")





def ensure\_directories():

&#x20;   OUTPUT\_DIR.mkdir(parents=True, exist\_ok=True)

&#x20;   ERROR\_DIR.mkdir(parents=True, exist\_ok=True)





def load\_existing\_single\_value\_csv(path: Path, output\_name: str) -> pd.DataFrame:

&#x20;   if not path.exists() or path.stat().st\_size == 0:

&#x20;       return pd.DataFrame(columns=\["date", output\_name])



&#x20;   df = pd.read\_csv(path)



&#x20;   required\_cols = \["date", output\_name]

&#x20;   missing = \[col for col in required\_cols if col not in df.columns]

&#x20;   if missing:

&#x20;       raise ValueError(f"{path} must include columns {required\_cols}, got {df.columns.tolist()}")



&#x20;   df = df\[required\_cols].copy()

&#x20;   df\["date"] = pd.to\_datetime(df\["date"], errors="coerce")

&#x20;   df\[output\_name] = pd.to\_numeric(df\[output\_name], errors="coerce")



&#x20;   df = df.dropna(subset=\["date", output\_name]).sort\_values("date")

&#x20;   df\["date"] = df\["date"].dt.strftime("%Y-%m-%d")

&#x20;   return df





def merge\_and\_save\_single\_value(existing\_df: pd.DataFrame, new\_df: pd.DataFrame, path: Path, output\_name: str) -> pd.DataFrame:

&#x20;   combined = pd.concat(\[existing\_df, new\_df], ignore\_index=True)

&#x20;   combined\["date"] = pd.to\_datetime(combined\["date"], errors="coerce")

&#x20;   combined\[output\_name] = pd.to\_numeric(combined\[output\_name], errors="coerce")



&#x20;   combined = combined.dropna(subset=\["date", output\_name])

&#x20;   combined = combined.drop\_duplicates(subset=\["date"], keep="last").sort\_values("date")

&#x20;   combined\["date"] = combined\["date"].dt.strftime("%Y-%m-%d")



&#x20;   combined.to\_csv(path, index=False)

&#x20;   return combined





def load\_existing\_multi\_value\_csv(path: Path, value\_columns: list\[str]) -> pd.DataFrame:

&#x20;   expected\_cols = \["date"] + value\_columns



&#x20;   if not path.exists() or path.stat().st\_size == 0:

&#x20;       return pd.DataFrame(columns=expected\_cols)



&#x20;   df = pd.read\_csv(path)



&#x20;   missing = \[col for col in expected\_cols if col not in df.columns]

&#x20;   if missing:

&#x20;       raise ValueError(f"{path} must include columns {expected\_cols}, got {df.columns.tolist()}")



&#x20;   df = df\[expected\_cols].copy()

&#x20;   df\["date"] = pd.to\_datetime(df\["date"], errors="coerce")



&#x20;   for col in value\_columns:

&#x20;       df\[col] = pd.to\_numeric(df\[col], errors="coerce")



&#x20;   df = df.dropna(subset=\["date"]).sort\_values("date")

&#x20;   df\["date"] = df\["date"].dt.strftime("%Y-%m-%d")

&#x20;   return df





def merge\_and\_save\_multi\_value(existing\_df: pd.DataFrame, new\_df: pd.DataFrame, path: Path, value\_columns: list\[str]) -> pd.DataFrame:

&#x20;   expected\_cols = \["date"] + value\_columns



&#x20;   combined = pd.concat(\[existing\_df, new\_df], ignore\_index=True)

&#x20;   combined = combined\[expected\_cols].copy()

&#x20;   combined\["date"] = pd.to\_datetime(combined\["date"], errors="coerce")



&#x20;   for col in value\_columns:

&#x20;       combined\[col] = pd.to\_numeric(combined\[col], errors="coerce")



&#x20;   combined = combined.dropna(subset=\["date"])

&#x20;   combined = combined.drop\_duplicates(subset=\["date"], keep="last").sort\_values("date")

&#x20;   combined\["date"] = combined\["date"].dt.strftime("%Y-%m-%d")



&#x20;   combined.to\_csv(path, index=False)

&#x20;   return combined





def get\_week\_monday(target\_date) -> pd.Timestamp:

&#x20;   ts = pd.to\_datetime(target\_date)

&#x20;   return ts - pd.Timedelta(days=ts.weekday())





def map\_single\_value\_to\_weekly\_monday(df: pd.DataFrame, output\_name: str) -> pd.DataFrame:

&#x20;   if df.empty:

&#x20;       return pd.DataFrame(columns=\["date", output\_name])



&#x20;   data = df.copy()

&#x20;   data\["date"] = pd.to\_datetime(data\["date"], errors="coerce")

&#x20;   data\[output\_name] = pd.to\_numeric(data\[output\_name], errors="coerce")

&#x20;   data = data.dropna(subset=\["date", output\_name]).sort\_values("date")



&#x20;   data\["date"] = data\["date"].apply(get\_week\_monday)



&#x20;   weekly = (

&#x20;       data.groupby("date", as\_index=False)\[output\_name]

&#x20;       .last()

&#x20;       .sort\_values("date")

&#x20;   )



&#x20;   weekly\["date"] = weekly\["date"].dt.strftime("%Y-%m-%d")

&#x20;   return weekly\[\["date", output\_name]]

```



\---



\## 5.5 `collectors/fred\_collector.py`



```python

from datetime import date

import os



import pandas as pd

from fredapi import Fred



from collectors.common import (

&#x20;   OUTPUT\_DIR,

&#x20;   ensure\_directories,

&#x20;   load\_existing\_single\_value\_csv,

&#x20;   merge\_and\_save\_single\_value,

&#x20;   map\_single\_value\_to\_weekly\_monday,

)





FRED\_SERIES = {

&#x20;   "dxy": "DTWEXBGS",

&#x20;   "vix": "VIXCLS",

&#x20;   "wti": "DCOILWTICO",

&#x20;   "sp500": "SP500",

&#x20;   "us3m": "DGS3MO",

&#x20;   "us2y": "DGS2",

&#x20;   "us10y": "DGS10",

&#x20;   "us30y": "DGS30",

&#x20;   "us\_headline\_cpi": "CPIAUCSL",

&#x20;   "us\_core\_cpi": "CPILFESL",

&#x20;   "us\_real\_gdp": "GDPC1",

}



FALLBACK\_START\_DATES = {

&#x20;   "dxy": "2000-01-01",

&#x20;   "vix": "1990-01-01",

&#x20;   "wti": "2000-01-01",

&#x20;   "sp500": "1971-01-01",

&#x20;   "us3m": "1971-01-01",

&#x20;   "us2y": "1971-01-01",

&#x20;   "us10y": "1971-01-01",

&#x20;   "us30y": "1977-01-01",

&#x20;   "us\_headline\_cpi": "1947-01-01",

&#x20;   "us\_core\_cpi": "1957-01-01",

&#x20;   "us\_real\_gdp": "1947-01-01",

}





def get\_fred\_client() -> Fred:

&#x20;   api\_key = os.getenv("FRED\_API\_KEY")

&#x20;   if not api\_key:

&#x20;       raise RuntimeError("FRED\_API\_KEY is not set")

&#x20;   return Fred(api\_key=api\_key)





def normalize\_history(series: pd.Series, output\_name: str) -> pd.DataFrame:

&#x20;   if series.empty:

&#x20;       return pd.DataFrame(columns=\["date", output\_name])



&#x20;   df = series.reset\_index()

&#x20;   df.columns = \["date", output\_name]



&#x20;   df\["date"] = pd.to\_datetime(df\["date"], errors="coerce")

&#x20;   df\[output\_name] = pd.to\_numeric(df\[output\_name], errors="coerce")



&#x20;   df = df.dropna(subset=\["date", output\_name]).sort\_values("date")



&#x20;   weekly = map\_single\_value\_to\_weekly\_monday(df, output\_name)

&#x20;   return weekly





def fetch\_fred\_history(series\_id: str, output\_name: str, start\_date: str, end\_date: str) -> pd.DataFrame:

&#x20;   fred = get\_fred\_client()

&#x20;   series = fred.get\_series(series\_id, observation\_start=start\_date, observation\_end=end\_date)



&#x20;   print(f"\[{output\_name}] Raw FRED rows fetched: {len(series)} for series\_id={series\_id}")



&#x20;   if series.empty:

&#x20;       raise RuntimeError(

&#x20;           f"\[{output\_name}] No data returned from FRED for series\_id={series\_id}, "

&#x20;           f"start\_date={start\_date}, end\_date={end\_date}."

&#x20;       )



&#x20;   normalized = normalize\_history(series, output\_name)



&#x20;   print(f"\[{output\_name}] Weekly Monday rows after normalization: {len(normalized)}")



&#x20;   if normalized.empty:

&#x20;       raise RuntimeError(

&#x20;           f"\[{output\_name}] FRED returned data for series\_id={series\_id}, but no normalized weekly rows remained after processing."

&#x20;       )



&#x20;   return normalized





def run\_fred\_series(output\_name: str, mode: str = "incremental") -> pd.DataFrame:

&#x20;   ensure\_directories()



&#x20;   if output\_name not in FRED\_SERIES:

&#x20;       raise ValueError(f"Unknown FRED output\_name: {output\_name}")



&#x20;   series\_id = FRED\_SERIES\[output\_name]

&#x20;   fallback\_start = FALLBACK\_START\_DATES\[output\_name]

&#x20;   output\_path = OUTPUT\_DIR / f"{output\_name}.csv"



&#x20;   existing\_df = load\_existing\_single\_value\_csv(output\_path, output\_name)

&#x20;   today = pd.Timestamp(date.today())



&#x20;   if mode not in {"full", "incremental"}:

&#x20;       raise ValueError("mode must be 'full' or 'incremental'")



&#x20;   if mode == "full":

&#x20;       fetch\_start = pd.Timestamp(fallback\_start)

&#x20;       print(

&#x20;           f"\[{output\_name}] FRED mode = full. "

&#x20;           f"Fetching full history from {fetch\_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}."

&#x20;       )

&#x20;   else:

&#x20;       if existing\_df.empty:

&#x20;           fetch\_start = pd.Timestamp(fallback\_start)

&#x20;           print(

&#x20;               f"\[{output\_name}] FRED mode = incremental. "

&#x20;               f"No existing CSV. Using fallback start date {fetch\_start.strftime('%Y-%m-%d')}."

&#x20;           )

&#x20;       else:

&#x20;           last\_record\_date = pd.to\_datetime(existing\_df\["date"], errors="coerce").max()

&#x20;           fetch\_start = last\_record\_date

&#x20;           print(

&#x20;               f"\[{output\_name}] FRED mode = incremental. "

&#x20;               f"Existing last\_record\_date = {last\_record\_date.strftime('%Y-%m-%d')}. "

&#x20;               f"Fetching through {today.strftime('%Y-%m-%d')}."

&#x20;           )



&#x20;       if not existing\_df.empty and fetch\_start >= today:

&#x20;           print(f"\[{output\_name}] Existing data already reaches today. No new fetch needed.")

&#x20;           return existing\_df



&#x20;   new\_df = fetch\_fred\_history(

&#x20;       series\_id=series\_id,

&#x20;       output\_name=output\_name,

&#x20;       start\_date=fetch\_start.strftime("%Y-%m-%d"),

&#x20;       end\_date=today.strftime("%Y-%m-%d"),

&#x20;   )



&#x20;   if new\_df.empty:

&#x20;       raise RuntimeError(f"\[{output\_name}] No rows fetched from FRED; refusing to overwrite existing CSV.")



&#x20;   if mode == "full":

&#x20;       final\_df = merge\_and\_save\_single\_value(

&#x20;           existing\_df=pd.DataFrame(columns=\["date", output\_name]),

&#x20;           new\_df=new\_df,

&#x20;           path=output\_path,

&#x20;           output\_name=output\_name,

&#x20;       )

&#x20;   else:

&#x20;       final\_df = merge\_and\_save\_single\_value(

&#x20;           existing\_df=existing\_df,

&#x20;           new\_df=new\_df,

&#x20;           path=output\_path,

&#x20;           output\_name=output\_name,

&#x20;       )



&#x20;   final\_df = final\_df.drop\_duplicates(subset=\["date"], keep="last").sort\_values("date").reset\_index(drop=True)

&#x20;   final\_df.to\_csv(output\_path, index=False)



&#x20;   print(f"\[{output\_name}] Saved weekly Monday FRED data to {output\_path}")

&#x20;   print(final\_df.tail())

&#x20;   return final\_df

```



\---



\## 5.6 `collectors/imir.py`



```python

import time

from datetime import date, timedelta



import pandas as pd

from bs4 import BeautifulSoup

from selenium import webdriver

from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service



from collectors.common import (

&#x20;   OUTPUT\_DIR,

&#x20;   ERROR\_DIR,

&#x20;   ensure\_directories,

&#x20;   load\_existing\_multi\_value\_csv,

&#x20;   merge\_and\_save\_multi\_value,

)





URL = "https://sbv.gov.vn/vi/l%C3%A3i-su%E1%BA%A5t-th%E1%BB%8B-tr%C6%B0%E1%BB%9Dng-li%C3%AAn-ng%C3%A2n-h%C3%A0ng"

CSV\_FILE = OUTPUT\_DIR / "imir.csv"

ERROR\_HTML\_FILE = ERROR\_DIR / "imir\_error.html"



mapping = {

&#x20;   "Qua đêm": "overnight",

&#x20;   "1 Tuần": "1w",

&#x20;   "2 Tuần": "2w",

&#x20;   "1 Tháng": "1m",

&#x20;   "3 Tháng": "3m",

&#x20;   "6 Tháng": "6m",

&#x20;   "9 Tháng": "9m",

}



VALUE\_COLUMNS = \["overnight", "1w", "2w", "1m", "3m", "6m", "9m"]





def save\_error\_html(content: str) -> None:

&#x20;   ERROR\_HTML\_FILE.write\_text(content, encoding="utf-8")





def get\_driver():

&#x20;   chrome\_options = Options()

&#x20;   chrome\_options.binary\_location = "/usr/bin/chromium"



&#x20;   chrome\_options.add\_argument("--headless=new")

&#x20;   chrome\_options.add\_argument("--no-sandbox")

&#x20;   chrome\_options.add\_argument("--disable-dev-shm-usage")

&#x20;   chrome\_options.add\_argument("--disable-blink-features=AutomationControlled")

&#x20;   chrome\_options.add\_argument("--window-size=1920,1080")

&#x20;   chrome\_options.add\_argument("--lang=vi-VN")

&#x20;   chrome\_options.add\_argument(

&#x20;       "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

&#x20;       "AppleWebKit/537.36 (KHTML, like Gecko) "

&#x20;       "Chrome/125.0.0.0 Safari/537.36"

&#x20;   )



&#x20;   service = Service("/usr/bin/chromedriver")

&#x20;   return webdriver.Chrome(service=service, options=chrome\_options)





def fetch\_current\_rates() -> dict:

&#x20;   today = date.today().strftime("%Y-%m-%d")

&#x20;   driver = get\_driver()



&#x20;   try:

&#x20;       driver.get(URL)

&#x20;       time.sleep(8)



&#x20;       html = driver.page\_source



&#x20;       if "The requested URL was rejected" in html:

&#x20;           save\_error\_html(html)

&#x20;           raise RuntimeError("Request was rejected by target website")



&#x20;       soup = BeautifulSoup(html, "html.parser")

&#x20;       table = soup.find("table", id="new-information-view")



&#x20;       if not table:

&#x20;           save\_error\_html(html)

&#x20;           raise ValueError("Table with id 'new-information-view' not found")



&#x20;       tbody = table.find("tbody")

&#x20;       if not tbody:

&#x20;           save\_error\_html(html)

&#x20;           raise ValueError("Table body not found")



&#x20;       rates = {

&#x20;           "date": today,

&#x20;           "overnight": None,

&#x20;           "1w": None,

&#x20;           "2w": None,

&#x20;           "1m": None,

&#x20;           "3m": None,

&#x20;           "6m": None,

&#x20;           "9m": None,

&#x20;       }



&#x20;       for tr in tbody.find\_all("tr"):

&#x20;           tds = tr.find\_all("td")

&#x20;           if len(tds) < 2:

&#x20;               continue



&#x20;           term = tds\[0].get\_text(strip=True)

&#x20;           rate = tds\[1].get\_text(strip=True).replace(",", ".")



&#x20;           if term in mapping:

&#x20;               rates\[mapping\[term]] = float(rate)



&#x20;       if not any(rates\[k] is not None for k in VALUE\_COLUMNS):

&#x20;           save\_error\_html(html)

&#x20;           raise ValueError("No rate values were extracted from the table")



&#x20;       return rates



&#x20;   except Exception:

&#x20;       try:

&#x20;           save\_error\_html(driver.page\_source)

&#x20;       except Exception:

&#x20;           pass

&#x20;       raise

&#x20;   finally:

&#x20;       driver.quit()





def get\_week\_monday(target\_date: date) -> date:

&#x20;   return target\_date - timedelta(days=target\_date.weekday())





def run\_imir():

&#x20;   ensure\_directories()



&#x20;   current\_rates = fetch\_current\_rates()

&#x20;   existing\_df = load\_existing\_multi\_value\_csv(CSV\_FILE, VALUE\_COLUMNS)



&#x20;   current\_date = pd.to\_datetime(current\_rates\["date"]).date()

&#x20;   monday\_date = get\_week\_monday(current\_date)



&#x20;   weekly\_row = {

&#x20;       "date": monday\_date.isoformat(),

&#x20;       \*\*{col: current\_rates.get(col) for col in VALUE\_COLUMNS}

&#x20;   }



&#x20;   new\_df = pd.DataFrame(\[weekly\_row], columns=\["date"] + VALUE\_COLUMNS)



&#x20;   final\_df = merge\_and\_save\_multi\_value(existing\_df, new\_df, CSV\_FILE, VALUE\_COLUMNS)

&#x20;   final\_df.to\_csv(CSV\_FILE, index=False)



&#x20;   print(f"\[imir] Saved weekly-only row for week-start Monday {weekly\_row\['date']} in {CSV\_FILE}")

&#x20;   print(weekly\_row)

```



\---



\## 5.7 `collectors/vn30.py`



```python

import csv

import re

import time

from datetime import date, timedelta



from bs4 import BeautifulSoup

from selenium import webdriver

from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service



from collectors.common import OUTPUT\_DIR, ERROR\_DIR, ensure\_directories





URL = "https://cafef.vn/du-lieu/lich-su-giao-dich/vn30/all-1.chn"

CSV\_FILE = OUTPUT\_DIR / "vn30.csv"

ERROR\_HTML\_FILE = ERROR\_DIR / "vn30\_error.html"



fieldnames = \["date", "vn30"]





def save\_error\_html(content: str) -> None:

&#x20;   ERROR\_HTML\_FILE.write\_text(content, encoding="utf-8")





def get\_driver():

&#x20;   chrome\_options = Options()

&#x20;   chrome\_options.binary\_location = "/usr/bin/chromium"



&#x20;   chrome\_options.add\_argument("--headless=new")

&#x20;   chrome\_options.add\_argument("--no-sandbox")

&#x20;   chrome\_options.add\_argument("--disable-dev-shm-usage")

&#x20;   chrome\_options.add\_argument("--disable-blink-features=AutomationControlled")

&#x20;   chrome\_options.add\_argument("--window-size=1920,1080")

&#x20;   chrome\_options.add\_argument("--lang=vi-VN")

&#x20;   chrome\_options.add\_argument(

&#x20;       "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

&#x20;       "AppleWebKit/537.36 (KHTML, like Gecko) "

&#x20;       "Chrome/125.0.0.0 Safari/537.36"

&#x20;   )



&#x20;   service = Service("/usr/bin/chromedriver")

&#x20;   return webdriver.Chrome(service=service, options=chrome\_options)





def normalize\_vn30\_value(raw\_value: str) -> str:

&#x20;   value = raw\_value.strip()

&#x20;   value = value.replace("điểm", "").replace("Điểm", "").strip()

&#x20;   value = value.replace(",", "")



&#x20;   if not re.fullmatch(r"\\d+(\\.\\d+)?", value):

&#x20;       raise ValueError(f"Invalid VN30 value format: {raw\_value}")



&#x20;   return value





def extract\_vn30\_from\_html(html: str) -> str:

&#x20;   soup = BeautifulSoup(html, "html.parser")



&#x20;   table = soup.find("table", id="index-summary-table")

&#x20;   if table:

&#x20;       for tr in table.find\_all("tr"):

&#x20;           cells = tr.find\_all("td")

&#x20;           if len(cells) >= 2:

&#x20;               label = cells\[0].get\_text(" ", strip=True).upper()

&#x20;               if label == "VN30INDEX":

&#x20;                   value\_text = cells\[1].get\_text(" ", strip=True)

&#x20;                   return normalize\_vn30\_value(value\_text)



&#x20;   for tr in soup.find\_all("tr"):

&#x20;       cells = tr.find\_all("td")

&#x20;       if len(cells) >= 2:

&#x20;           label = cells\[0].get\_text(" ", strip=True).upper()

&#x20;           if label == "VN30INDEX":

&#x20;               value\_text = cells\[1].get\_text(" ", strip=True)

&#x20;               return normalize\_vn30\_value(value\_text)



&#x20;   text = soup.get\_text("\\n", strip=True)

&#x20;   match = re.search(r"VN30INDEX\\s+(\[\\d,]+\\.\\d+)\\s\*điểm", text, flags=re.IGNORECASE)

&#x20;   if match:

&#x20;       return normalize\_vn30\_value(match.group(1))



&#x20;   save\_error\_html(html)

&#x20;   raise ValueError("VN30INDEX value not found in page")





def fetch\_current\_vn30() -> dict:

&#x20;   today = date.today().strftime("%Y-%m-%d")

&#x20;   driver = get\_driver()



&#x20;   try:

&#x20;       driver.get(URL)

&#x20;       time.sleep(8)



&#x20;       html = driver.page\_source



&#x20;       if "The requested URL was rejected" in html:

&#x20;           save\_error\_html(html)

&#x20;           raise RuntimeError("Request was rejected by target website")



&#x20;       vn30\_value = extract\_vn30\_from\_html(html)



&#x20;       return {

&#x20;           "date": today,

&#x20;           "vn30": vn30\_value,

&#x20;       }



&#x20;   except Exception:

&#x20;       try:

&#x20;           save\_error\_html(driver.page\_source)

&#x20;       except Exception:

&#x20;           pass

&#x20;       raise

&#x20;   finally:

&#x20;       driver.quit()





def load\_existing\_rows(file\_path):

&#x20;   rows = \[]



&#x20;   if not file\_path.exists() or file\_path.stat().st\_size == 0:

&#x20;       return rows



&#x20;   with file\_path.open("r", newline="", encoding="utf-8") as f:

&#x20;       reader = csv.DictReader(f)

&#x20;       for row in reader:

&#x20;           rows.append({

&#x20;               "date": (row.get("date") or "").strip(),

&#x20;               "vn30": (row.get("vn30") or "").strip(),

&#x20;           })



&#x20;   return rows





def save\_rows(file\_path, rows: list\[dict]) -> None:

&#x20;   with file\_path.open("w", newline="", encoding="utf-8") as f:

&#x20;       writer = csv.DictWriter(f, fieldnames=fieldnames)

&#x20;       writer.writeheader()

&#x20;       writer.writerows(rows)





def get\_week\_monday(target\_date: date) -> date:

&#x20;   return target\_date - timedelta(days=target\_date.weekday())





def run\_vn30():

&#x20;   ensure\_directories()

&#x20;   current\_row = fetch\_current\_vn30()

&#x20;   rows = load\_existing\_rows(CSV\_FILE)



&#x20;   current\_date = date.fromisoformat(current\_row\["date"])

&#x20;   monday\_date = get\_week\_monday(current\_date)



&#x20;   weekly\_row = {

&#x20;       "date": monday\_date.isoformat(),

&#x20;       "vn30": current\_row\["vn30"],

&#x20;   }



&#x20;   existing\_index = next((i for i, row in enumerate(rows) if row\["date"] == weekly\_row\["date"]), None)

&#x20;   if existing\_index is not None:

&#x20;       rows\[existing\_index] = weekly\_row

&#x20;       action = "updated"

&#x20;   else:

&#x20;       rows.append(weekly\_row)

&#x20;       rows.sort(key=lambda x: x\["date"])

&#x20;       action = "appended"



&#x20;   save\_rows(CSV\_FILE, rows)



&#x20;   print(f"\[vn30] Successfully {action} weekly-only row for week-start Monday {weekly\_row\['date']} in {CSV\_FILE}")

&#x20;   print(weekly\_row)

```



\---



\## 5.8 `collectors/sjc.py`



```python

import re

from datetime import date, timedelta, datetime



import pandas as pd

import requests

from bs4 import BeautifulSoup



from collectors.common import (

&#x20;   OUTPUT\_DIR,

&#x20;   ensure\_directories,

&#x20;   load\_existing\_single\_value\_csv,

&#x20;   merge\_and\_save\_single\_value,

&#x20;   map\_single\_value\_to\_weekly\_monday,

)





OUTPUT\_FILE = OUTPUT\_DIR / "sjc.csv"

OUTPUT\_NAME = "sjc"

FALLBACK\_START\_DATE = "2009-01-01"



BASE\_URL = "https://webgia.com/gia-vang/sjc/"

HEADERS = {

&#x20;   "User-Agent": "Mozilla/5.0 (compatible; SJCCollector/1.0)"

}

TIMEOUT = 30





def parse\_int\_number(text: str) -> int:

&#x20;   digits = re.sub(r"\[^\\d]", "", text or "")

&#x20;   if not digits:

&#x20;       raise ValueError(f"Cannot parse integer from: {text!r}")

&#x20;   return int(digits)





def fetch\_page(url: str) -> BeautifulSoup:

&#x20;   response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

&#x20;   response.raise\_for\_status()

&#x20;   return BeautifulSoup(response.text, "html.parser")





def extract\_sjc\_sell\_from\_main\_table(soup: BeautifulSoup) -> int:

&#x20;   target\_sjc = None



&#x20;   tables = soup.find\_all("table")

&#x20;   for table in tables:

&#x20;       for tr in table.select("tbody tr"):

&#x20;           cells = tr.find\_all(\["th", "td"])

&#x20;           if len(cells) < 4:

&#x20;               continue



&#x20;           area = cells\[0].get\_text(" ", strip=True)

&#x20;           gold\_type = cells\[1].get\_text(" ", strip=True)



&#x20;           if area == "Hồ Chí Minh" and gold\_type == "Vàng SJC 1L, 10L, 1KG":

&#x20;               sell\_per\_chi = parse\_int\_number(cells\[3].get\_text(" ", strip=True))

&#x20;               target\_sjc = sell\_per\_chi \* 10

&#x20;               break

&#x20;       if target\_sjc is not None:

&#x20;           break



&#x20;   if target\_sjc is None:

&#x20;       raise RuntimeError("Cannot find Hồ Chí Minh / Vàng SJC 1L, 10L, 1KG row")



&#x20;   return target\_sjc





def extract\_sjc\_from\_current\_page() -> dict:

&#x20;   soup = fetch\_page(BASE\_URL)



&#x20;   h1 = soup.find("h1", class\_="h-head")

&#x20;   if not h1:

&#x20;       raise RuntimeError("Cannot find page header")



&#x20;   h1\_text = h1.get\_text(" ", strip=True)

&#x20;   m = re.search(r"(\\d{2}:\\d{2}:\\d{2})\\s+(\\d{2}/\\d{2}/\\d{4})", h1\_text)

&#x20;   if not m:

&#x20;       raise RuntimeError("Cannot parse update datetime from current page")



&#x20;   updated\_date = datetime.strptime(m.group(2), "%d/%m/%Y").date()

&#x20;   sjc = extract\_sjc\_sell\_from\_main\_table(soup)



&#x20;   return {

&#x20;       "date": updated\_date.isoformat(),

&#x20;       OUTPUT\_NAME: sjc,

&#x20;   }





def extract\_sjc\_from\_daily\_page(target\_date: date) -> dict:

&#x20;   url = f"{BASE\_URL}{target\_date.strftime('%d-%m-%Y')}.html"

&#x20;   soup = fetch\_page(url)



&#x20;   h1 = soup.find("h1", class\_="h-head")

&#x20;   if not h1:

&#x20;       raise RuntimeError(f"Cannot find page header for {target\_date.isoformat()}")



&#x20;   table = soup.find("table", class\_=lambda c: c and "table" in c)

&#x20;   if not table:

&#x20;       raise RuntimeError(f"Cannot find history table for {target\_date.isoformat()}")



&#x20;   data\_rows = \[]

&#x20;   for tr in table.select("tbody tr"):

&#x20;       tds = tr.find\_all("td")

&#x20;       if len(tds) < 4:

&#x20;           continue



&#x20;       time\_text = tds\[1].get\_text(" ", strip=True)

&#x20;       sell\_text = tds\[3].get\_text(" ", strip=True)



&#x20;       if not re.match(r"^\\d{2}:\\d{2}$", time\_text):

&#x20;           continue



&#x20;       sell\_million = float(re.sub(r"\[^\\d.]", "", sell\_text))

&#x20;       sjc = int(round(sell\_million \* 1\_000\_000))

&#x20;       data\_rows.append((time\_text, sjc))



&#x20;   if not data\_rows:

&#x20;       raise RuntimeError(f"No daily price rows found for {target\_date.isoformat()}")



&#x20;   \_, sjc = data\_rows\[-1]



&#x20;   return {

&#x20;       "date": target\_date.isoformat(),

&#x20;       OUTPUT\_NAME: sjc,

&#x20;   }





def fetch\_sjc\_incremental(existing\_df: pd.DataFrame) -> pd.DataFrame:

&#x20;   target\_date = pd.Timestamp(date.today())

&#x20;   fallback\_start = pd.Timestamp(FALLBACK\_START\_DATE)



&#x20;   print(f"\[sjc] Target date: {target\_date.strftime('%Y-%m-%d')}")



&#x20;   if existing\_df.empty:

&#x20;       fetch\_start\_ts = fallback\_start

&#x20;       print(f"\[sjc] No existing CSV. Starting from fallback start date: {fetch\_start\_ts.strftime('%Y-%m-%d')}")

&#x20;   else:

&#x20;       last\_record\_date = pd.to\_datetime(existing\_df\["date"]).max()

&#x20;       print(f"\[sjc] Last record in {OUTPUT\_FILE}: {last\_record\_date.strftime('%Y-%m-%d')}")



&#x20;       if last\_record\_date >= target\_date:

&#x20;           print("\[sjc] Existing data already reaches today. No new fetch needed.")

&#x20;           return pd.DataFrame(columns=\["date", OUTPUT\_NAME])



&#x20;       fetch\_start\_ts = last\_record\_date

&#x20;       print(f"\[sjc] Using last record date as fetch start: {fetch\_start\_ts.strftime('%Y-%m-%d')}")



&#x20;   rows = \[]

&#x20;   current\_day = fetch\_start\_ts.date()

&#x20;   end\_day = target\_date.date()



&#x20;   while current\_day <= end\_day:

&#x20;       try:

&#x20;           if current\_day == date.today():

&#x20;               row = extract\_sjc\_from\_current\_page()

&#x20;           else:

&#x20;               row = extract\_sjc\_from\_daily\_page(current\_day)



&#x20;           rows.append({

&#x20;               "date": row\["date"],

&#x20;               OUTPUT\_NAME: row\[OUTPUT\_NAME],

&#x20;           })

&#x20;           print(f"\[sjc] Fetched {row\['date']} {OUTPUT\_NAME}={row\[OUTPUT\_NAME]}")

&#x20;       except Exception as e:

&#x20;           print(f"\[sjc] Skipped {current\_day.isoformat()}: {e}")



&#x20;       current\_day += timedelta(days=1)



&#x20;   if not rows:

&#x20;       return pd.DataFrame(columns=\["date", OUTPUT\_NAME])



&#x20;   daily\_df = pd.DataFrame(rows, columns=\["date", OUTPUT\_NAME])

&#x20;   return map\_single\_value\_to\_weekly\_monday(daily\_df, OUTPUT\_NAME)





def run\_sjc():

&#x20;   ensure\_directories()

&#x20;   existing\_df = load\_existing\_single\_value\_csv(OUTPUT\_FILE, OUTPUT\_NAME)

&#x20;   new\_df = fetch\_sjc\_incremental(existing\_df)



&#x20;   if new\_df.empty and not existing\_df.empty:

&#x20;       print("\[sjc] No changes detected. Existing file remains current.")

&#x20;       print(existing\_df.tail())

&#x20;       return existing\_df



&#x20;   final\_df = merge\_and\_save\_single\_value(existing\_df, new\_df, OUTPUT\_FILE, OUTPUT\_NAME)

&#x20;   final\_df = map\_single\_value\_to\_weekly\_monday(final\_df, OUTPUT\_NAME)

&#x20;   final\_df.to\_csv(OUTPUT\_FILE, index=False)



&#x20;   print(f"\[sjc] Saved weekly Monday-based data to {OUTPUT\_FILE}")

&#x20;   print(final\_df.tail())

&#x20;   return final\_df

```



\---

\## 5.9 `collectors/gold.py`



```python

import re

from datetime import date, timedelta, datetime



import pandas as pd

import requests

from bs4 import BeautifulSoup



from collectors.common import (

&#x20;   OUTPUT\_DIR,

&#x20;   ensure\_directories,

&#x20;   load\_existing\_single\_value\_csv,

&#x20;   merge\_and\_save\_single\_value,

&#x20;   map\_single\_value\_to\_weekly\_monday,

)





OUTPUT\_FILE = OUTPUT\_DIR / "gold.csv"

OUTPUT\_NAME = "gold"

FALLBACK\_START\_DATE = "2009-01-01"



BASE\_URL = "https://giavang.org/the-gioi/"

HEADERS = {

&#x20;   "User-Agent": "Mozilla/5.0 (compatible; GoldCollector/1.0)"

}

TIMEOUT = 30





def parse\_float\_number(text: str) -> float:

&#x20;   cleaned = re.sub(r"\[^\\d.,]", "", text or "").replace(",", "")

&#x20;   if not cleaned:

&#x20;       raise ValueError(f"Cannot parse float from: {text!r}")

&#x20;   return float(cleaned)





def fetch\_page(url: str) -> BeautifulSoup:

&#x20;   response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

&#x20;   response.raise\_for\_status()

&#x20;   return BeautifulSoup(response.text, "html.parser")





def extract\_gold\_from\_current\_page() -> dict:

&#x20;   soup = fetch\_page(BASE\_URL)



&#x20;   h1 = soup.find("h1", class\_="box-headline")

&#x20;   if not h1:

&#x20;       raise RuntimeError("Cannot find page header")



&#x20;   h1\_text = h1.get\_text(" ", strip=True)

&#x20;   m = re.search(r"(\\d{2}:\\d{2}:\\d{2})\\s+(\\d{2}/\\d{2}/\\d{4})", h1\_text)

&#x20;   if not m:

&#x20;       raise RuntimeError("Cannot parse update datetime from current page")



&#x20;   updated\_date = datetime.strptime(m.group(2), "%d/%m/%Y").date()



&#x20;   price\_span = soup.find("span", class\_="crypto-price")

&#x20;   if not price\_span:

&#x20;       raise RuntimeError("Cannot find gold price span")



&#x20;   gold = parse\_float\_number(price\_span.get\_text(" ", strip=True))



&#x20;   return {

&#x20;       "date": updated\_date.isoformat(),

&#x20;       OUTPUT\_NAME: gold,

&#x20;   }





def extract\_gold\_from\_daily\_page(target\_date: date) -> dict:

&#x20;   url = f"{BASE\_URL}{target\_date.strftime('%d-%m-%Y')}.html"

&#x20;   soup = fetch\_page(url)



&#x20;   h1 = soup.find("h1", class\_="box-headline")

&#x20;   if not h1:

&#x20;       raise RuntimeError(f"Cannot find page header for {target\_date.isoformat()}")



&#x20;   price\_span = soup.find("span", class\_="crypto-price")

&#x20;   if not price\_span:

&#x20;       raise RuntimeError(f"Cannot find gold price span for {target\_date.isoformat()}")



&#x20;   gold = parse\_float\_number(price\_span.get\_text(" ", strip=True))



&#x20;   return {

&#x20;       "date": target\_date.isoformat(),

&#x20;       OUTPUT\_NAME: gold,

&#x20;   }





def fetch\_gold\_incremental(existing\_df: pd.DataFrame) -> pd.DataFrame:

&#x20;   target\_date = pd.Timestamp(date.today())

&#x20;   fallback\_start = pd.Timestamp(FALLBACK\_START\_DATE)



&#x20;   print(f"\[gold] Target date: {target\_date.strftime('%Y-%m-%d')}")



&#x20;   if existing\_df.empty:

&#x20;       fetch\_start\_ts = fallback\_start

&#x20;       print(f"\[gold] No existing CSV. Starting from fallback start date: {fetch\_start\_ts.strftime('%Y-%m-%d')}")

&#x20;   else:

&#x20;       last\_record\_date = pd.to\_datetime(existing\_df\["date"]).max()

&#x20;       print(f"\[gold] Last record in {OUTPUT\_FILE}: {last\_record\_date.strftime('%Y-%m-%d')}")



&#x20;       if last\_record\_date >= target\_date:

&#x20;           print("\[gold] Existing data already reaches today. No new fetch needed.")

&#x20;           return pd.DataFrame(columns=\["date", OUTPUT\_NAME])



&#x20;       fetch\_start\_ts = last\_record\_date

&#x20;       print(f"\[gold] Using last record date as fetch start: {fetch\_start\_ts.strftime('%Y-%m-%d')}")



&#x20;   rows = \[]

&#x20;   current\_day = fetch\_start\_ts.date()

&#x20;   end\_day = target\_date.date()



&#x20;   while current\_day <= end\_day:

&#x20;       try:

&#x20;           if current\_day == date.today():

&#x20;               row = extract\_gold\_from\_current\_page()

&#x20;           else:

&#x20;               row = extract\_gold\_from\_daily\_page(current\_day)



&#x20;           rows.append({

&#x20;               "date": row\["date"],

&#x20;               OUTPUT\_NAME: row\[OUTPUT\_NAME],

&#x20;           })

&#x20;           print(f"\[gold] Fetched {row\['date']} {OUTPUT\_NAME}={row\[OUTPUT\_NAME]}")

&#x20;       except Exception as e:

&#x20;           print(f"\[gold] Skipped {current\_day.isoformat()}: {e}")



&#x20;       current\_day += timedelta(days=1)



&#x20;   if not rows:

&#x20;       return pd.DataFrame(columns=\["date", OUTPUT\_NAME])



&#x20;   daily\_df = pd.DataFrame(rows, columns=\["date", OUTPUT\_NAME])

&#x20;   return map\_single\_value\_to\_weekly\_monday(daily\_df, OUTPUT\_NAME)





def run\_gold():

&#x20;   ensure\_directories()

&#x20;   existing\_df = load\_existing\_single\_value\_csv(OUTPUT\_FILE, OUTPUT\_NAME)

&#x20;   new\_df = fetch\_gold\_incremental(existing\_df)



&#x20;   if new\_df.empty and not existing\_df.empty:

&#x20;       print("\[gold] No changes detected. Existing file remains current.")

&#x20;       print(existing\_df.tail())

&#x20;       return existing\_df



&#x20;   final\_df = merge\_and\_save\_single\_value(existing\_df, new\_df, OUTPUT\_FILE, OUTPUT\_NAME)

&#x20;   final\_df = map\_single\_value\_to\_weekly\_monday(final\_df, OUTPUT\_NAME)

&#x20;   final\_df.to\_csv(OUTPUT\_FILE, index=False)



&#x20;   print(f"\[gold] Saved weekly Monday-based data to {OUTPUT\_FILE}")

&#x20;   print(final\_df.tail())

&#x20;   return final\_df

```



\---



\## 5.10 `market\_collector.py`



```python

import argparse

import traceback



from collectors.imir import run\_imir

from collectors.vn30 import run\_vn30

from collectors.sjc import run\_sjc

from collectors.gold import run\_gold

from collectors.fred\_collector import run\_fred\_series, FRED\_SERIES





CRAWL\_TASKS = {

&#x20;   "imir": run\_imir,

&#x20;   "vn30": run\_vn30,

&#x20;   "sjc": run\_sjc,

&#x20;   "gold": run\_gold,

}



ALL\_CRAWL\_TASK\_NAMES = list(CRAWL\_TASKS.keys())

ALL\_TASK\_NAMES = ALL\_CRAWL\_TASK\_NAMES + list(FRED\_SERIES.keys())





def build\_parser():

&#x20;   parser = argparse.ArgumentParser(description="Unified market collector")



&#x20;   parser.add\_argument(

&#x20;       "--all",

&#x20;       action="store\_true",

&#x20;       help="Run all crawl collectors only: imir, vn30, sjc, gold"

&#x20;   )



&#x20;   parser.add\_argument(

&#x20;       "--only",

&#x20;       nargs="+",

&#x20;       help=f"Run only selected task names. Available: {', '.join(ALL\_TASK\_NAMES)}"

&#x20;   )



&#x20;   parser.add\_argument(

&#x20;       "--fred-mode",

&#x20;       choices=\["full", "incremental"],

&#x20;       default="incremental",

&#x20;       help="FRED fetch mode: full history or incremental from last record date to today"

&#x20;   )



&#x20;   return parser





def resolve\_tasks(args):

&#x20;   if args.all and args.only:

&#x20;       raise ValueError("Use either --all or --only, not both.")



&#x20;   if args.fred\_mode == "full" and args.all:

&#x20;       raise ValueError(

&#x20;           "--fred-mode full cannot be used with --all. "

&#x20;           "Please specify exactly one FRED series with --only."

&#x20;       )



&#x20;   if args.all:

&#x20;       selected = ALL\_CRAWL\_TASK\_NAMES

&#x20;   elif args.only:

&#x20;       selected = args.only

&#x20;   else:

&#x20;       selected = ALL\_CRAWL\_TASK\_NAMES



&#x20;   unknown = \[name for name in selected if name not in ALL\_TASK\_NAMES]

&#x20;   if unknown:

&#x20;       raise ValueError(f"Unknown task names: {unknown}")



&#x20;   fred\_selected = \[name for name in selected if name in FRED\_SERIES]



&#x20;   if args.fred\_mode == "full":

&#x20;       if len(fred\_selected) != 1:

&#x20;           raise ValueError(

&#x20;               "--fred-mode full requires --only with exactly one explicit FRED series."

&#x20;           )



&#x20;   return selected





def run\_selected\_tasks(task\_names, fred\_mode):

&#x20;   success = \[]

&#x20;   failed = \[]



&#x20;   for name in task\_names:

&#x20;       print("=" \* 80)

&#x20;       print(f"Running task: {name}")



&#x20;       try:

&#x20;           if name in CRAWL\_TASKS:

&#x20;               CRAWL\_TASKS\[name]()

&#x20;           elif name in FRED\_SERIES:

&#x20;               run\_fred\_series(name, mode=fred\_mode)

&#x20;           else:

&#x20;               raise ValueError(f"Task not configured: {name}")



&#x20;           success.append(name)

&#x20;           print(f"Task completed successfully: {name}")



&#x20;       except Exception as e:

&#x20;           failed.append(name)

&#x20;           print(f"Task failed: {name}")

&#x20;           print(f"Error: {e}")

&#x20;           traceback.print\_exc()



&#x20;   print("=" \* 80)

&#x20;   print("Run summary")

&#x20;   print(f"Successful tasks: {success}")

&#x20;   print(f"Failed tasks: {failed}")





def main():

&#x20;   parser = build\_parser()

&#x20;   args = parser.parse\_args()



&#x20;   selected = resolve\_tasks(args)

&#x20;   run\_selected\_tasks(selected, fred\_mode=args.fred\_mode)





if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   main()

```



\---



\# Part 6 — Run Instructions



\## Run default collector



From inside the `market\_collector/` folder:



```bash

docker compose up --build

```



This default command runs:



```bash

python market\_collector.py --all

```



which means:



\- `imir`

\- `vn30`

\- `sjc`

\- `gold`



\## Run all crawl tasks manually



```bash

docker compose run --rm market-collector python market\_collector.py --all

```



\## Run selected crawl task



```bash

docker compose run --rm market-collector python market\_collector.py --only imir

docker compose run --rm market-collector python market\_collector.py --only vn30

docker compose run --rm market-collector python market\_collector.py --only sjc

```



\## Run FRED incremental



```bash

docker compose run --rm market-collector python market\_collector.py --only dxy --fred-mode incremental

docker compose run --rm market-collector python market\_collector.py --only wti --fred-mode incremental

docker compose run --rm market-collector python market\_collector.py --only us10y --fred-mode incremental

```



\## Run FRED full-history rebuild



```bash

docker compose run --rm market-collector python market\_collector.py --only dxy --fred-mode full

docker compose run --rm market-collector python market\_collector.py --only wti --fred-mode full

docker compose run --rm market-collector python market\_collector.py --only us10y --fred-mode full

```



\## Required environment variable



Set your FRED API key before running FRED-based collection:



```bash

export FRED\_API\_KEY=your\_fred\_api\_key\_here

```



Or place it in a `.env` file used by Docker Compose.



\---



\# Part 7 — Notes



\- each dataset/series writes to its own CSV file

\- each output CSV contains weekly rows

\- all weekly outputs use \*\*Monday of the week\*\* as `date`

\- FRED data is fetched using `fredapi`

\- FRED observations are normalized into weekly Monday rows

\- snapshot collectors `imir` and `vn30` are mapped to the week-start Monday

\- `sjc` is aggregated into week-start Monday rows

\- `gold` is collected together with `sjc` in `sjc.py`

\- `--all` runs crawl tasks only

\- FRED tasks must be run using `--only`

\- `--fred-mode full` requires exactly one explicit FRED series via `--only`

\- Treasury yield FRED values are used directly without Yahoo-style divide-by-10 normalization



\---



\# License



Personal/internal use.



