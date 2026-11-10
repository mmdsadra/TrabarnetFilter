from __future__ import annotations
import csv, io, json, os, re
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-dev-only-change-me")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
LOADS_FILE = DATA_DIR / "loads.json"

ALIASES = {
    "origin": ["origin","مبدا","مبدأ","شهر مبدا","شهر مبدأ"],
    "destination": ["destination","مقصد","شهر مقصد"],
    "weight_ton": ["weight_ton","weight","وزن","تناژ","وزن (تن)","وزن بار"],
    "price": ["price","fare","کرایه","مبلغ","قیمت"],
    "truck": ["truck","vehicle","ماشین","نوع ماشین","نوع کامیون","بارگیر"],
    "cargo": ["cargo","load","بار","نوع بار","کالا"],
    "date": ["date","تاریخ","زمان ثبت"],
    "phone": ["phone","mobile","تلفن","شماره تماس"],
    "description": ["description","توضیحات","شرح"],
}
def norm(s):
    return re.sub(r"[\u200c\s_-]+", "", str(s or "").strip().lower()).replace("ي","ی").replace("ك","ک")
def number(value):
    s = str(value or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    s=s.replace(",","").replace("٬","").replace("٫",".")
    m=re.search(r"-?\d+(?:\.\d+)?",s)
    return float(m.group()) if m else None
def read_loads():
    if LOADS_FILE.exists():
        try: return json.loads(LOADS_FILE.read_text(encoding="utf-8"))
        except Exception: pass
    return []
def save_loads(loads):
    LOADS_FILE.write_text(json.dumps(loads,ensure_ascii=False,indent=2),encoding="utf-8")
def map_headers(headers):
    result={}
    normalized={norm(h):h for h in headers}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if norm(alias) in normalized:
                result[field]=normalized[norm(alias)]; break
    return result
def parse_csv(raw):
    text=raw.decode("utf-8-sig",errors="replace")
    sample=text[:4096]
    try: dialect=csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error: dialect=csv.excel
    reader=csv.DictReader(io.StringIO(text),dialect=dialect)
    mapping=map_headers(reader.fieldnames or [])
    if not mapping.get("origin") or not mapping.get("price"):
        raise ValueError("ستون‌های مبدأ و کرایه ضروری‌اند. نام ستون‌ها را در CSV بررسی کنید.")
    out=[]
    for row in reader:
        item={k:(row.get(v,"") if v else "") for k,v in mapping.items()}
        item["weight_ton"]=number(item.get("weight_ton"))
        item["price"]=number(item.get("price"))
        if not item.get("origin") and not item.get("price"): continue
        out.append(item)
    return out
HTML = """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrabarnetFilter</title><style>
body{font-family:Tahoma,Arial;background:#f4f6f8;color:#18212b;margin:0;padding:20px}main{max-width:1100px;margin:auto}
.card{background:white;padding:18px;border-radius:12px;margin:14px 0;box-shadow:0 2px 8px #0001}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
label{display:block;font-size:13px;margin-bottom:5px}input,select,button{box-sizing:border-box;width:100%;padding:10px;border:1px solid #ccd3da;border-radius:8px;font:inherit}
button{background:#176b53;color:white;border:0;cursor:pointer;margin-top:10px}.secondary{background:#536273}
table{width:100%;border-collapse:collapse;background:white}th,td{padding:10px;border-bottom:1px solid #e5e9ed;text-align:right}
th{background:#edf2f5}.muted{color:#66717d;font-size:13px}.warning{background:#fff3cd;padding:12px;border-radius:8px}
@media(max-width:650px){body{padding:8px}.tablewrap{overflow:auto}}
</style><main><h1>🚚 TrabarnetFilter</h1><p class="muted">فیلتر محلی بارها — داده‌ها روی همین کامپیوتر ذخیره می‌شوند.</p>
{% with messages=get_flashed_messages() %}{% if messages %}<div class="warning">{% for m in messages %}{{m}}{% endfor %}</div>{% endif %}{% endwith %}
<section class="card"><h3>۱) وارد کردن بارها</h3><p class="muted">CSV خروجی/داده‌ای که مجاز به ذخیره‌اش هستید را انتخاب کنید. ستون مبدأ و کرایه لازم است.</p>
<form method="post" action="/import" enctype="multipart/form-data"><input type="file" name="file" accept=".csv" required><button>وارد کردن CSV (جایگزین داده قبلی)</button></form></section>
<section class="card"><h3>۲) فیلتر</h3><form method="get"><div class="grid">
<div><label>مبدأ شامل</label><input name="origin" value="{{f.origin}}" placeholder="مثلاً اصفهان"></div>
<div><label>مقصد شامل</label><input name="destination" value="{{f.destination}}"></div>
<div><label>حداقل وزن (تن)</label><input name="min_weight" type="number" step=".1" value="{{f.min_weight}}"></div>
<div><label>حداکثر وزن (تن)</label><input name="max_weight" type="number" step=".1" value="{{f.max_weight}}"></div>
<div><label>حداقل کرایه (تومان)</label><input name="min_price" type="number" value="{{f.min_price}}"></div>
<div><label>حداقل کرایه هر تن (تومان)</label><input name="min_per_ton" type="number" value="{{f.min_per_ton}}"></div>
<div><label>نوع کامیون/بارگیر شامل</label><input name="truck" value="{{f.truck}}"></div>
<div><label>نوع بار شامل</label><input name="cargo" value="{{f.cargo}}"></div>
</div><button>اعمال فیلتر</button><a href="/" style="display:block;text-align:center;margin-top:12px">پاک کردن فیلترها</a></form></section>
<section class="card"><h3>۳) نتایج ({{loads|length}} بار)</h3><div class="tablewrap"><table><thead><tr><th>مبدأ → مقصد</th><th>بار</th><th>ماشین</th><th>وزن</th><th>کرایه</th><th>تومان/تن</th><th>تماس</th></tr></thead><tbody>
{% for x in loads %}<tr><td>{{x.origin}} → {{x.destination}}</td><td>{{x.cargo}}</td><td>{{x.truck}}</td><td>{{x.weight_ton if x.weight_ton is not none else "—"}}</td><td>{{"{:,.0f}".format(x.price) if x.price is not none else "—"}}</td><td>{{"{:,.0f}".format(x.price/x.weight_ton) if x.price and x.weight_ton else "—"}}</td><td>{{x.phone}}</td></tr>{% else %}<tr><td colspan="7">بار منطبق پیدا نشد؛ CSV وارد کنید یا فیلتر را سبک‌تر کنید.</td></tr>{% endfor %}
</tbody></table></div></section>
<p class="muted">این برنامه بار جدید را خودکار از ترابرنت دریافت نمی‌کند و با ترابرنت ارتباط رسمی ندارد. برای دریافت خودکار، باید روش مجاز/مستند اتصال مشخص شود.</p></main></html>"""
@app.route("/")
def index():
    f={k:request.args.get(k,"").strip() for k in ["origin","destination","min_weight","max_weight","min_price","min_per_ton","truck","cargo"]}
    loads=read_loads()
    def contains(value,query): return not query or query.casefold() in str(value or "").casefold()
    result=[]
    for x in loads:
        w=x.get("weight_ton"); p=x.get("price")
        if not contains(x.get("origin"),f["origin"]) or not contains(x.get("destination"),f["destination"]): continue
        if not contains(x.get("truck"),f["truck"]) or not contains(x.get("cargo"),f["cargo"]): continue
        if f["min_weight"] and (w is None or w<float(f["min_weight"])): continue
        if f["max_weight"] and (w is None or w>float(f["max_weight"])): continue
        if f["min_price"] and (p is None or p<float(f["min_price"])): continue
        if f["min_per_ton"] and (not w or not p or p/w<float(f["min_per_ton"])): continue
        result.append(x)
    result.sort(key=lambda x:(x.get("price") or 0),reverse=True)
    return render_template_string(HTML,loads=result,f=f)
@app.post("/import")
def import_csv():
    file=request.files.get("file")
    if not file or not file.filename: flash("فایل انتخاب نشده است."); return redirect(url_for("index"))
    try:
        loads=parse_csv(file.read()); save_loads(loads); flash(f"{len(loads)} بار وارد شد.")
    except Exception as e: flash("خطا در CSV: "+str(e))
    return redirect(url_for("index"))
if __name__=="__main__":
    app.run(host="127.0.0.1",port=5050,debug=False)
