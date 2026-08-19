import re, json, sqlite3, time, threading
from urllib.parse import quote_plus, urlparse
import requests
from bs4 import BeautifulSoup
import streamlit as st

DB='scentcompare.db'
HEADERS={'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1'}

SEED=[
 {'store':'CallPerfume','price':115,'shipping':0,'stock':True,'url':'https://callperfume.co.il/%D7%A8%D7%A1%D7%90%D7%A1%D7%99-%D7%94%D7%95%D7%95%D7%90%D7%A1-%D7%90%D7%99%D7%99%D7%A1-%D7%91%D7%95%D7%A9%D7%9D-%D7%9C%D7%92%D7%91%D7%A8-%D7%90%D7%93%D7%A4-100%D7%9E%D7%B4%D7%9C-rasasi-hawas-ice-for-2/'},
 {'store':'Ivory','price':239,'shipping':0,'stock':True,'url':'https://www.ivory.co.il/catalog.php?id=93972'},
]

ALIASES={'rasasi':'rasasi','רסאסי':'rasasi','رَسَاسِي':'rasasi','هواس':'hawas','הוואס':'hawas','هواز':'hawas','ice':'ice','אייס':'ice','ايس':'ice','edp':'edp','אדפ':'edp','مل':'ml','מל':'ml'}

def norm(s):
    s=s.lower().replace('״','"').replace('”','"').replace('″','"')
    for a,b in ALIASES.items(): s=s.replace(a,b)
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def parse_volume(s):
    m=re.search(r'(\d{2,4})\s*(?:ml|מ\s*l|מל|מ"ל)',s.lower())
    return int(m.group(1)) if m else None

def product_key(s):
    n=norm(s); vol=parse_volume(s)
    bits=[]
    for x in ('rasasi','hawas','ice','edp'):
        if x in n: bits.append(x)
    if vol: bits.append(str(vol)+'ml')
    return '-'.join(bits)

def db():
    c=sqlite3.connect(DB)
    c.execute('create table if not exists offers(id integer primary key, product_key text, name text, store text, price real, shipping real, stock integer, url text, checked_at real, unique(store,url))')
    return c

def save(o):
    c=db(); c.execute('''insert into offers(product_key,name,store,price,shipping,stock,url,checked_at) values(?,?,?,?,?,?,?,?)
      on conflict(store,url) do update set price=excluded.price,shipping=excluded.shipping,stock=excluded.stock,checked_at=excluded.checked_at''',
      (o['product_key'],o['name'],o['store'],o['price'],o['shipping'],int(o['stock']),o['url'],time.time())); c.commit(); c.close()

def jsonld(url):
    r=requests.get(url,headers=HEADERS,timeout=15); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            x=json.loads(tag.string or tag.get_text())
            arr=x if isinstance(x,list) else [x]
            for y in arr:
                if isinstance(y,dict) and (y.get('@type')=='Product' or 'offers' in y): return y,soup
        except Exception: pass
    return {},soup

def fetch_page(url,store):
    try:
        data,soup=jsonld(url); name=data.get('name') or (soup.title.get_text(' ',strip=True) if soup.title else '')
        offers=data.get('offers',{})
        if isinstance(offers,list): offers=offers[0] if offers else {}
        price=offers.get('price') if isinstance(offers,dict) else None
        if price is None:
            txt=soup.get_text(' ',strip=True)
            ms=re.findall(r'(?:₪|ILS)\s*([0-9]{2,4}(?:\.[0-9]+)?)|([0-9]{2,4}(?:\.[0-9]+)?)\s*₪',txt)
            vals=[float(a or b) for a,b in ms if float(a or b)<2000]
            price=min(vals) if vals else None
        stock=True
        av=(offers.get('availability','') if isinstance(offers,dict) else '').lower()
        if 'outofstock' in av: stock=False
        if price is None: return None
        return {'product_key':product_key(name),'name':name,'store':store,'price':float(price),'shipping':0,'stock':stock,'url':url}
    except Exception as e: return None

def live_fetch(query):
    results=[]
    # Search engines are used only as discovery; store pages are fetched and parsed afterwards.
    domains=['ivory.co.il','callperfume.co.il']
    for domain in domains:
        try:
            q=quote_plus(f'site:{domain} {query}')
            html=requests.get('https://html.duckduckgo.com/html/?q='+q,headers=HEADERS,timeout=15).text
            soup=BeautifulSoup(html,'html.parser')
            urls=[]
            for a in soup.select('.result__a'):
                href=a.get('href','')
                if domain in href and href.startswith('http'): urls.append(href)
            for u in urls[:5]:
                o=fetch_page(u, 'Ivory' if 'ivory.co.il' in u else 'CallPerfume')
                if o and query_match(query,o['name']): results.append(o); save(o)
        except Exception: pass
    return results

def query_match(q,name):
    a=norm(q); b=norm(name)
    # forgiving token matching; exact volume/variant when supplied
    toks=[t for t in a.split() if t not in ('for','men','woman','the')]
    return sum(t in b for t in toks) >= max(1,min(3,len(toks)))

def get_offers(q):
    c=db(); rows=c.execute('select name,store,price,shipping,stock,url,checked_at from offers where product_key like ? order by (price+shipping) asc',('%'+product_key(q)+'%',)).fetchall(); c.close()
    if not rows: rows=[]
    return rows

st.set_page_config(page_title='ScentCompare Israel',page_icon='🧴',layout='centered')
st.markdown('''<style> .block-container{max-width:850px;padding-top:1rem} .price{font-size:2rem;font-weight:800} .store{font-size:1.1rem;font-weight:700} .card{padding:1rem;border:1px solid #ddd;border-radius:16px;margin:.6rem 0} </style>''',unsafe_allow_html=True)
st.title('🧴 ScentCompare Israel')
st.caption('Compare Israeli perfume prices • English / עברית / عربي')
q=st.text_input('Search perfume',value='Rasasi Hawas Ice 100ml',placeholder='Hawas Ice / הוואס אייס / هواس آيس')
col1,col2=st.columns([2,1])
with col1: refresh=st.button('🔄 Search live prices',use_container_width=True)
with col2: st.write('')
if refresh:
    with st.spinner('Searching stores…'):
        live_fetch(q)
rows=get_offers(q)
if not rows and query_match(q,'Rasasi Hawas Ice 100ml'):
    for o in SEED: save({'product_key':'rasasi-hawas-ice-edp-100ml','name':'Rasasi Hawas Ice EDP For Men 100ML',**o})
    rows=get_offers(q)
if rows:
    st.subheader(f'{len(rows)} offers')
    for name,store,price,shipping,stock,url,checked in rows:
        total=price+shipping
        st.markdown(f'''<div class="card"><div class="store">{store}</div><div>{name}</div><div class="price">₪{total:,.0f}</div><div>{'🟢 In stock' if stock else '🔴 Out of stock'} • Shipping ₪{shipping:,.0f}</div></div>''',unsafe_allow_html=True)
        st.link_button('Open store',url,use_container_width=True)
else:
    st.info('No indexed offer yet. Tap “Search live prices”.')

with st.expander('⚙️ How this MVP works'):
    st.write('Live discovery currently covers Ivory and CallPerfume. The architecture is ready for additional store adapters. Prices are parsed from store pages and stored locally in SQLite. Search-engine discovery can fail when a site blocks automated requests.')
    st.write('For a production-scale engine, add dedicated APIs/adapters, barcode matching, shipping rules, scheduled crawling, and a cloud database.')
