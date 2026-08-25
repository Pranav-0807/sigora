"""Universal bank-statement importer for Sigora.
Supports CSV, XLSX, XLS and PDF (including encrypted PDFs).
The importer normalizes many common bank export schemas into Sigora transactions.
"""
from __future__ import annotations
import csv, io, re
from datetime import datetime
from pathlib import Path

MAX_IMPORT_ROWS = int(__import__('os').getenv('IMPORT_MAX_ROWS', '10000'))

DATE_ALIASES={"date","transaction date","transaction_date","value date","value_date","posting date","posting_date","post date","entry date","trans date","date of transaction","transaction dt"}
DESC_ALIASES={"description","narration","particulars","details","transaction description","transaction_description","remarks","reference","memo","transaction details","merchant","merchant name","payee","name","narrative"}
AMOUNT_ALIASES={"amount","transaction amount","transaction_amount","value","sum","transaction value"}
DEBIT_ALIASES={"debit","debits","withdrawal","withdrawals","withdraw","debit amount","debit_amount","dr","debit transaction"}
CREDIT_ALIASES={"credit","credits","deposit","deposits","credit amount","credit_amount","cr","credit transaction"}
DATE_HINTS=("date","posted","posting","transaction","value","entry")
DESC_HINTS=("description","narration","particular","detail","memo","merchant","payee","remarks","narrative")
AMOUNT_HINTS=("amount","value","transaction value","transaction amount")


def norm(s):
    return " ".join(str(s or "").strip().lower().replace("_"," ").replace("-"," ").split())


def clean_amount(value):
    if value is None or str(value).strip()=="": return 0.0
    s=str(value).strip().replace(",","")
    s=re.sub(r"(?:₹|\$|€|£|¥|Rs\.?|INR|USD|EUR|GBP|CAD|AUD|CHF)\s*", "", s, flags=re.I)
    neg=s.startswith("(") and s.endswith(")")
    if neg: s=s[1:-1]
    marker=s.upper().strip()
    dr=marker.endswith("DR"); cr=marker.endswith("CR")
    if dr or cr: s=s[:-2].strip()
    s=re.sub(r"[^0-9.\-]", "", s)
    if not s or s in {"-","."}: return 0.0
    n=float(s)
    if neg or dr: n=-abs(n)
    elif cr: n=abs(n)
    return n


def clean_date(value):
    if isinstance(value, datetime): return value.date().isoformat()
    if hasattr(value, "isoformat") and not isinstance(value,str): return value.isoformat()[:10]
    s=str(value or "").strip()
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%d/%m/%Y","%d-%m-%Y","%m/%d/%Y","%m-%d-%Y","%d/%m/%y","%d-%m-%y","%m/%d/%y","%m-%d-%y","%d.%m.%Y","%d.%m.%y","%b %d, %Y","%d %b %Y","%d %B %Y"):
        try: return datetime.strptime(s,fmt).date().isoformat()
        except ValueError: pass
    try: return datetime.fromisoformat(s.replace("Z","")).date().isoformat()
    except Exception: raise ValueError(f"Unrecognized date: {s}")


def find_col(columns, aliases, hints=()):
    nmap={norm(c):c for c in columns if c is not None and str(c).strip()}
    for a in aliases:
        if norm(a) in nmap: return nmap[norm(a)]
    for c in columns:
        n=norm(c)
        if any(h in n for h in hints): return c
    return None


def _header_score(row):
    vals=[norm(x) for x in row if x is not None]
    if not vals: return -1
    score=0
    for v in vals:
        if v in DATE_ALIASES or any(h in v for h in DATE_HINTS): score+=3
        if v in DESC_ALIASES or any(h in v for h in DESC_HINTS): score+=3
        if v in AMOUNT_ALIASES or v in DEBIT_ALIASES or v in CREDIT_ALIASES or any(h in v for h in AMOUNT_HINTS): score+=2
    return score


def _dict_rows(raw_rows, header_index):
    headers=[str(x).strip() if x is not None else "" for x in raw_rows[header_index]]
    while headers and headers[-1]=="": headers.pop()
    if not any(headers): raise ValueError("Could not detect a usable header row.")
    rows=[]
    for vals in raw_rows[header_index+1:]:
        vals=list(vals)
        if not any(v not in (None, "") for v in vals): continue
        rows.append({headers[i]: (vals[i] if i<len(vals) else "") for i in range(len(headers))})
        if len(rows)>MAX_IMPORT_ROWS: raise ValueError(f"Statement contains more than {MAX_IMPORT_ROWS:,} rows. Please import a smaller date range.")
    return rows, headers


def rows_from_csv(fileobj):
    raw=fileobj.read()
    text=raw if isinstance(raw,str) else raw.decode("utf-8-sig", errors="replace")
    if not text.strip(): raise ValueError("CSV file is empty.")
    try: dialect=csv.Sniffer().sniff(text[:12000], delimiters=",;\t|")
    except Exception: dialect=csv.excel
    raw_rows=list(csv.reader(io.StringIO(text), dialect=dialect))
    if not raw_rows: raise ValueError("CSV file is empty.")
    scores=[_header_score(r) for r in raw_rows[:15]]
    header_index=max(range(len(scores)), key=lambda i: scores[i])
    if scores[header_index] < 5: raise ValueError("Could not identify the transaction header row in this CSV.")
    return (*_dict_rows(raw_rows, header_index), "csv")


def rows_from_excel(fileobj, filename):
    ext=Path(filename).suffix.lower()
    if ext==".xlsx":
        from openpyxl import load_workbook
        fileobj.seek(0); wb=load_workbook(fileobj, read_only=True, data_only=True); ws=wb.active
        raw_rows=[]
        for i,vals in enumerate(ws.iter_rows(values_only=True)):
            raw_rows.append(list(vals))
            if i>=14: break
        if not raw_rows: raise ValueError("Excel file is empty.")
        scores=[_header_score(r) for r in raw_rows]
        header_index=max(range(len(scores)), key=lambda i: scores[i])
        if scores[header_index]<5: raise ValueError("Could not identify the transaction header row in this Excel file.")
        headers=[str(x).strip() if x is not None else "" for x in raw_rows[header_index]]
        rows=[]
        for vals in ws.iter_rows(min_row=header_index+2, values_only=True):
            vals=list(vals)
            if not any(v not in (None,"") for v in vals): continue
            rows.append({headers[i]:(vals[i] if i<len(vals) else "") for i in range(len(headers))})
            if len(rows)>MAX_IMPORT_ROWS: raise ValueError(f"Statement contains more than {MAX_IMPORT_ROWS:,} rows. Please import a smaller date range.")
        wb.close(); return rows, headers, "xlsx"
    if ext==".xls":
        try: import xlrd
        except ImportError: raise ValueError("XLS support is not installed. Please run pip install -r requirements.txt.")
        fileobj.seek(0); book=xlrd.open_workbook(file_contents=fileobj.read(), on_demand=True); sheet=book.sheet_by_index(0)
        raw_rows=[sheet.row_values(i) for i in range(min(sheet.nrows,15))]
        if not raw_rows: raise ValueError("Excel file is empty.")
        scores=[_header_score(r) for r in raw_rows]; header_index=max(range(len(scores)), key=lambda i: scores[i])
        if scores[header_index]<5: raise ValueError("Could not identify the transaction header row in this Excel file.")
        headers=[str(x).strip() if x is not None else "" for x in raw_rows[header_index]]
        rows=[]
        for i in range(header_index+1,sheet.nrows):
            vals=sheet.row_values(i)
            if not any(v not in (None,"") for v in vals): continue
            rows.append({headers[j]:(vals[j] if j<len(vals) else "") for j in range(len(headers))})
            if len(rows)>MAX_IMPORT_ROWS: raise ValueError(f"Statement contains more than {MAX_IMPORT_ROWS:,} rows. Please import a smaller date range.")
        book.release_resources(); return rows, headers, "xls"
    raise ValueError("Unsupported Excel format.")


def _pdf_bytes(fileobj, password=None):
    from pypdf import PdfReader
    fileobj.seek(0); data=fileobj.read(); reader=PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        if not password: raise ValueError("PDF_PASSWORD_REQUIRED")
        if reader.decrypt(password)==0: raise ValueError("PDF_PASSWORD_INVALID")
    return reader,data


def rows_from_pdf(fileobj,password=None):
    reader,data=_pdf_bytes(fileobj,password)
    rows=[]
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data), password=password or None) as pdf:
            for page in pdf.pages:
                tables=page.extract_tables() or []
                for table in tables:
                    if len(table)<2: continue
                    # Find the strongest header row within first few rows.
                    header_index=max(range(min(5,len(table))), key=lambda i:_header_score(table[i]))
                    if _header_score(table[header_index])<5: continue
                    headers=[str(x or "").strip() for x in table[header_index]]
                    for vals in table[header_index+1:]:
                        if not vals or not any(v not in (None,"") for v in vals): continue
                        rows.append({headers[i]:(vals[i] if i<len(vals) else "") for i in range(len(headers))})
                        if len(rows)>MAX_IMPORT_ROWS: raise ValueError(f"Statement contains more than {MAX_IMPORT_ROWS:,} rows.")
    except ValueError: raise
    except Exception: rows=[]
    if rows: return rows, list(rows[0].keys()), "pdf"

    # Text fallback for PDFs whose table grid cannot be extracted.
    text="\n".join((p.extract_text() or "") for p in reader.pages)
    parsed=[]
    date_re=r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
    money_re=r"(?<!\w)(?:\(?[-+]?\s*(?:[$€£₹]|Rs\.?|[A-Z]{0,3}\s*)?\d[\d,]*(?:\.\d{1,2})?\)?\s*(?:DR|CR)?)"
    for line in text.splitlines():
        line=" ".join(line.split()); dm=re.search(date_re,line)
        if not dm: continue
        amounts=re.findall(money_re,line,flags=re.I)
        if not amounts: continue
        try: d=clean_date(dm.group(1))
        except Exception: continue
        # In common bank statement lines the first money token after the description is the transaction amount; later tokens are balances.
        amt=clean_amount(amounts[0])
        desc=line[dm.end():]
        for token in amounts: desc=desc.replace(token," ",1)
        desc=re.sub(r"\s+"," ",desc).strip(" -|")
        if desc and amt!=0: parsed.append({"Date":d,"Description":desc,"Amount":amt})
        if len(parsed)>MAX_IMPORT_ROWS: raise ValueError(f"Statement contains more than {MAX_IMPORT_ROWS:,} rows.")
    if not parsed: raise ValueError("Could not detect transactions in this PDF. Try a CSV/Excel export or another statement format.")
    return parsed,["Date","Description","Amount"],"pdf"


def read_statement(fileobj,filename,password=None):
    ext=Path(filename).suffix.lower()
    if ext==".csv": return rows_from_csv(fileobj)
    if ext in {".xlsx",".xls"}: return rows_from_excel(fileobj,filename)
    if ext==".pdf": return rows_from_pdf(fileobj,password)
    raise ValueError("Unsupported file type. Use CSV, XLSX, XLS or PDF.")


def normalize_rows(rows,columns,categorize):
    date_col=find_col(columns,DATE_ALIASES,DATE_HINTS); desc_col=find_col(columns,DESC_ALIASES,DESC_HINTS)
    amount_col=find_col(columns,AMOUNT_ALIASES,AMOUNT_HINTS); debit_col=find_col(columns,DEBIT_ALIASES,("debit","withdraw","dr")); credit_col=find_col(columns,CREDIT_ALIASES,("credit","deposit","cr"))
    if not date_col: raise ValueError("Could not identify the transaction date column.")
    if not desc_col: raise ValueError("Could not identify the transaction description/narration column.")
    if not amount_col and not debit_col and not credit_col: raise ValueError("Could not identify an amount, debit, or credit column.")
    normalized=[]; errors=[]
    for idx,row in enumerate(rows,start=2):
        try:
            d=clean_date(row.get(date_col)); desc=str(row.get(desc_col) or "").strip()
            if not desc: raise ValueError("description is empty")
            if amount_col:
                amt=clean_amount(row.get(amount_col))
            else:
                debit=clean_amount(row.get(debit_col)) if debit_col else 0; credit=clean_amount(row.get(credit_col)) if credit_col else 0
                if debit and credit: raise ValueError("both debit and credit contain values")
                amt=-abs(debit) if debit else (abs(credit) if credit else 0)
                if amt==0: raise ValueError("amount is empty")
            if amt==0: raise ValueError("amount is zero")
            tx_type="income" if amt>0 else "expense"; amount=abs(round(amt,2)); category=categorize(desc,tx_type)
            normalized.append({"date":d,"description":desc,"transaction_type":tx_type,"amount":amount,"category":category})
        except Exception as e: errors.append(f"Row {idx}: {e}")
    if not normalized and errors: raise ValueError("No valid transactions could be extracted. Please check the statement format.")
    return normalized,errors
