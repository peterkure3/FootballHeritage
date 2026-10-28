"""Render the architecture overview with Pillow (no external renderer required)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
im = Image.new('RGB', (2200, 1550), '#f4f6f9')
d = ImageDraw.Draw(im)
def font(size, bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/' + ('arialbd.ttf' if bold else 'arial.ttf'), size)
def text(x, y, value, size=23, color='#223648', bold=False):
    d.multiline_text((x,y), value, font=font(size,bold), fill=color, spacing=10)
def box(x,y,w,h,title,body,fill='white'):
    d.rounded_rectangle((x,y,x+w,y+h),18,fill=fill,outline='#becbd5',width=2)
    text(x+22,y+20,title,25,bold=True)
    text(x+22,y+65,body,21)
def arrow(points, label='', pos=None):
    d.line(points,fill='#506b80',width=4)
    x,y=points[-1]; px,py=points[-2]
    import math
    angle=math.atan2(y-py,x-px)
    d.polygon([(x,y),(x-15*math.cos(angle-.45),y-15*math.sin(angle-.45)),(x-15*math.cos(angle+.45),y-15*math.sin(angle+.45))],fill='#506b80')
    if label and pos: text(*pos,label,18)

text(65,40,'FootballHeritage',44,bold=True)
text(65,100,'System architecture  /  28 October 2026',27)
text(65,145,'Hosted release + local frontend improvements • Current hosted database remains Neon staging',21)
for x,w,title in [(55,620,'USER DEVICE + VERCEL'),(760,620,'NEON POSTGRESQL'),(1465,680,'PRIVATE WINDOWS HOST')]:
    d.rounded_rectangle((x,215,x+w,1310),22,fill='#e9eef3')
    text(x+24,238,title,25,bold=True)

box(80,300,570,170,'React 19 + Vite frontend','Predictions • intelligence • account UI\nReact Query • feature gates • auth','#e1f1e8')
box(80,510,570,160,'Vercel frontend deployment','Static HTML, JavaScript and CSS\nBrowser calls the Rust API over HTTPS')
box(80,735,570,190,'Rust + Actix-web API on Vercel','Durable sessions • policy • admin\nBetting / wallet • published AI Picks\nRust RAG for hosted chat','#e1f1e8')
box(80,990,570,170,'Durable gateway','/api/v1/pipeline/* compatibility routes\nSnapshot read or queue → 202 pending\nBrowser polls until result is available')
box(785,300,570,170,'Application tables','Users • sessions • feature policies\nEvents • markets • bets / wallet','#e4edfb')
box(785,650,570,190,'Published datasets','Atomic fixture bundles + model metadata\nSimulation bundles • provenance\nGeneration time and freshness','#e4edfb')
box(785,990,570,190,'Gateway jobs + saved responses','Stream / user scope • idempotency\nLeased work • expiry • bounded results\nPrewarmed public snapshots','#e4edfb')
box(1490,300,630,170,'Sports / bookmaker feeds → Python ETL','Verified feeds and website collectors\nFixtures • results • timestamped odds')
box(1490,530,630,160,'Local PostgreSQL + saved artifacts','History • features • predictions • trials\nActive and candidate models stay distinct','#e4edfb')
box(1490,750,630,180,'Python models + analytics','Training / inference • simulations\nEV / devig / arbitrage • FPL / trials\nExisting internal Python interfaces')
box(1490,990,295,195,'Publication worker','Validated bundles\nTransactional outbox\nReceipts + retries')
box(1810,990,310,195,'Compute worker','Claim leased jobs\nBounded execution\nCommit responses')
arrow([(365,670),(365,735)],'HTTPS',(380,686))
arrow([(365,925),(365,990)])
arrow([(650,800),(710,800),(710,385),(785,385)])
arrow([(785,745),(650,830)],'reads',(690,755))
arrow([(650,1075),(785,1075)])
arrow([(785,1125),(650,1125)])
arrow([(1805,470),(1805,530)])
arrow([(1805,690),(1805,750)])
arrow([(1635,690),(1430,690),(1430,950),(1635,950),(1635,990)])
arrow([(1490,1080),(1410,1080),(1410,745),(1355,745)],'outbound TLS',(1370,885))
arrow([(1810,1150),(1385,1150),(1385,1200),(1070,1200),(1070,1180)])
arrow([(1355,1030),(1445,1030),(1445,965),(1960,965),(1960,990)])
text(1510,1210,'Windows Task Scheduler: separate worker tasks',21,bold=True)
text(1510,1250,'Host must remain awake and user signed in',20)
box(80,1340,990,165,'Local frontend improvement — historical public data only','Settled history first; summary + version list follow. Two-minute session cache\nuses exact filter keys and refreshes in background. No live prices or accounts.','#fff2d5')
box(1100,1340,1020,165,'Serving boundary','Vercel reads Neon; it never calls the Windows host over HTTP.\nPython owns computation. Ranking freshness and kickoff limits still apply.\nHosted published chat uses Rust RAG; legacy Node / Genkit is superseded.')
im.save(ROOT/'architecture.png')
print(f'Saved {ROOT / "architecture.png"} ({im.width} x {im.height})')
