"""Build the static dashboard (docs/index.html) from results/.

The page is one self-contained file with the data embedded, so it can be
served by GitHub Pages from the docs/ folder or opened from disk.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

GRID = {  # tile-grid map position (column, row) by state
    "Alaska": (0, 0), "Maine": (10, 0), "Vermont": (9, 1), "New Hampshire": (10, 1),
    "Washington": (0, 2), "Idaho": (1, 2), "Montana": (2, 2), "North Dakota": (3, 2),
    "Minnesota": (4, 2), "Illinois": (5, 2), "Wisconsin": (6, 2), "Michigan": (7, 2),
    "New York": (8, 2), "Rhode Island": (9, 2), "Massachusetts": (10, 2),
    "Oregon": (0, 3), "Nevada": (1, 3), "Wyoming": (2, 3), "South Dakota": (3, 3),
    "Iowa": (4, 3), "Indiana": (5, 3), "Ohio": (6, 3), "Pennsylvania": (7, 3),
    "New Jersey": (8, 3), "Connecticut": (9, 3),
    "California": (0, 4), "Utah": (1, 4), "Colorado": (2, 4), "Nebraska": (3, 4),
    "Missouri": (4, 4), "Kentucky": (5, 4), "West Virginia": (6, 4), "Virginia": (7, 4),
    "Maryland": (8, 4), "Delaware": (9, 4),
    "Arizona": (1, 5), "New Mexico": (2, 5), "Kansas": (3, 5), "Arkansas": (4, 5),
    "Tennessee": (5, 5), "North Carolina": (6, 5), "South Carolina": (7, 5),
    "District of Columbia": (8, 5),
    "Oklahoma": (3, 6), "Louisiana": (4, 6), "Mississippi": (5, 6), "Alabama": (6, 6),
    "Georgia": (7, 6), "Hawaii": (0, 7), "Texas": (3, 7), "Florida": (8, 7),
}
ABBR = dict(zip(
    ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
     "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
     "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
     "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
     "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
     "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
     "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
     "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"],
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
    "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()))

def read_json(path):
    """Load a results file, with a clear message if an earlier step was skipped."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"{path} not found; run the earlier pipeline steps first")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chlamydia and syphilis forecasting prototype</title>
<style>
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;
--rule:#e4e3df;--s1:#2a78d6;--s2:#eb6834;--note:#f6f5f1}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:24px;margin:0 0 4px}
h2{font-size:17px;margin:0 0 2px}
p{margin:6px 0}
.sub{color:var(--ink2);max-width:760px}
.note{background:var(--note);border:1px solid var(--rule);border-radius:8px;padding:10px 14px;
margin:16px 0;color:var(--ink2);font-size:14px}
.filters{display:flex;flex-wrap:wrap;gap:14px 20px;margin:18px 0 8px;align-items:end}
label{display:flex;flex-direction:column;font-size:12px;color:var(--ink2);gap:3px}
select{font:inherit;padding:6px 8px;border:1px solid var(--rule);border-radius:6px;background:#fff;color:var(--ink)}
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:16px 18px;margin-top:16px}
.cap{color:var(--ink2);font-size:13px;margin-bottom:8px}
.tiles{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}
.tile{flex:1 1 170px;border:1px solid var(--rule);border-radius:8px;padding:10px 12px}
.tile b{display:block;font-size:22px;font-weight:600}
.tile span{font-size:12px;color:var(--ink2)}
svg text{font:12px system-ui,sans-serif;fill:var(--ink2)}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--ink2);margin:4px 0 6px}
.legend i{display:inline-block;width:22px;height:0;border-top:2px solid;vertical-align:middle;margin-right:6px}
#tip{position:fixed;pointer-events:none;background:#fff;border:1px solid var(--rule);border-radius:6px;
padding:6px 9px;font-size:12.5px;box-shadow:0 2px 8px rgba(0,0,0,.12);display:none;z-index:5;max-width:240px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:right;padding:5px 8px;border-bottom:1px solid var(--rule)}
th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:600}
details{margin-top:10px}summary{cursor:pointer;color:var(--ink2);font-size:13px}
.cell{cursor:pointer}
footer{color:var(--ink2);font-size:13px;margin-top:26px}
a{color:var(--s1)}
</style>
</head>
<body>
<main>
<h1>Chlamydia and syphilis forecasting prototype</h1>
<p class="sub">State-level transmission models fitted to CDC surveillance counts, with forecasts
to __FORECAST_TO__ and what-if scenarios for diagnosis-and-treatment and contact rates.</p>
<div class="note"><b>Research prototype.</b> Not for clinical or operational use. Forecasts come from
simple compartmental models with constant rates and carry no uncertainty interval yet.
See the backtest results below for how accurate they have been. Built __BUILD_DATE__.</div>

<div class="filters">
<label>Infection<select id="dis"><option value="chlamydia">Chlamydia</option>
<option value="ps_syphilis">Primary and secondary syphilis</option></select></label>
<label>Area<select id="st"></select></label>
<label>Model<select id="mod"><option value="integer">Integer order (alpha = 1)</option>
<option value="fractional">Fractional order (alpha fitted)</option></select></label>
<label>Diagnosis and treatment rate<select id="tr"></select></label>
<label>Contact rate<select id="ct"></select></label>
</div>

<div class="panel">
<h2 id="t1"></h2>
<div class="cap">Reported cases per 100,000 residents per year. Scenario changes start in __SCEN_YEAR__. The fitted models sit close to the epidemic threshold, so scenario results swing widely and should be read as direction, not magnitude.</div>
<div class="legend"><span><i style="border-color:var(--ink)"></i>Reported (CDC NNDSS)</span>
<span><i style="border-color:var(--s1)"></i>Model fit and forecast</span>
<span id="lgb"><i style="border-color:var(--muted);border-top-style:dashed"></i>Forecast with no change</span></div>
<svg id="chart" viewBox="0 0 1000 380" width="100%" role="img" aria-label="Observed and modelled case rates"></svg>
<div class="tiles" id="tiles"></div>
<details><summary>Show these numbers as a table</summary><div id="tbl"></div></details>
</div>

<div class="panel">
<h2 id="t2"></h2>
<div class="cap">Each square is a state, placed roughly where it sits on the map. Darker means a higher rate.
Select a square to load that state above.</div>
<svg id="map" viewBox="0 0 1000 496" width="100%" role="img" aria-label="Tile map of state rates"></svg>
</div>

<div class="panel">
<h2>How accurate have the forecasts been?</h2>
<div class="cap">Rolling-origin backtest over the 50 states and DC. Each model was fitted to data through
2019, 2020, 2021 and 2022 in turn and asked to forecast one and two years ahead. Figures are the
median absolute percentage error; lower is better. "Persistence" repeats the last observed year and
"trend" extends a straight line through the last five years.</div>
<div id="bt"></div>
</div>

<footer>
<p><b>Data.</b> Case counts: CDC National Notifiable Diseases Surveillance System weekly tables on
data.cdc.gov, retrieved __RETRIEVED__. The count for each year is taken from the following year's
final weekly table, so it includes late reports but can differ slightly from CDC's finalized annual
report. Population: U.S. Census Bureau state estimates.</p>
<p><b>Models.</b> Chlamydia uses the S-E-V-I-T-R model of Egbemhenghe, Akor, Atokolo and Amos (2025),
<a href="https://doi.org/10.5281/zenodo.14716850">doi:10.5281/zenodo.14716850</a>, with the vaccination
rate set to zero. Syphilis uses a multi-stage model with incubating, primary, secondary and early latent
stages. Both are solved with the fractional Adams-Bashforth-Moulton method.</p>
</footer>
</main>
<div id="tip"></div>
<script>
const D = __DATA__;
const $ = id => document.getElementById(id);
const fmt = v => v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2);
const NAMES = {chlamydia: "Chlamydia", ps_syphilis: "Primary and secondary syphilis"};
const TRL = {"1.0":"No change","1.1":"10% faster","1.25":"25% faster","1.5":"50% faster"};
const CTL = {"1.0":"No change","0.9":"10% lower","0.8":"20% lower"};
function opts(sel, vals, lab){ sel.innerHTML = vals.map(v => `<option value="${v}">${lab(v)}</option>`).join(""); }
const key = v => Number.isInteger(v) ? v.toFixed(1) : String(v);
opts($("tr"), D.treat.map(key), v => TRL[v] || v);
opts($("ct"), D.contact.map(key), v => CTL[v] || v);
const areas = Object.keys(D.fits.chlamydia).sort((a,b)=> a==="United States"?-1:b==="United States"?1:a.localeCompare(b));
opts($("st"), areas, v => v);

function tip(ev, html){ const t=$("tip"); t.innerHTML=html; t.style.display="block";
  const x=Math.min(ev.clientX+14, innerWidth-250); t.style.left=x+"px"; t.style.top=(ev.clientY+14)+"px"; }
function untip(){ $("tip").style.display="none"; }

function current(){
  const dis=$("dis").value, st=$("st").value, mod=$("mod").value;
  const f=D.fits[dis][st], m=f[mod];
  const yrs=[]; for(let y=m.first_year;y<=D.forecast_to;y++) yrs.push(y);
  const scen=m.scenarios[$("ct").value+"|"+$("tr").value], base=m.scenarios["1.0|1.0"];
  return {dis,st,mod,f,m,yrs,scen,base};
}

function drawChart(){
  const c=current(), W=1000,H=380,L=56,R=24,T=14,B=34;
  const obs=c.f.observed, last=c.m.last_data_year;
  const all=[...Object.values(obs),...c.scen,...c.base];
  const ymax=Math.max(...all)*1.12;
  const x=y=>L+(y-c.yrs[0])/(c.yrs.length-1)*(W-L-R), yy=v=>H-B-(v/ymax)*(H-T-B);
  let s="";
  const step=Math.pow(10,Math.floor(Math.log10(ymax/4))); const tick=[1,2,5,10].map(k=>k*step).find(k=>ymax/k<=6);
  for(let v=0;v<=ymax;v+=tick){ s+=`<line x1="${L}" x2="${W-R}" y1="${yy(v)}" y2="${yy(v)}" stroke="#e4e3df"/>`+
    `<text x="${L-8}" y="${yy(v)+4}" text-anchor="end">${fmt(v).replace(/\.0+$/,"")}</text>`; }
  c.yrs.forEach(y=>{ if((y-c.yrs[0])%2===0||y===D.forecast_to) s+=`<text x="${x(y)}" y="${H-10}" text-anchor="middle">${y}</text>`; });
  s+=`<rect x="${x(last)+ (x(last+1)-x(last))/2}" y="${T}" width="${W-R-x(last)-(x(last+1)-x(last))/2}" height="${H-T-B}" fill="#f6f5f1"/>`+
     `<text x="${x(last+1)}" y="${T+14}">Forecast</text>`;
  const path=(arr,from)=>arr.map((v,i)=>({y:c.yrs[i],v})).filter(p=>p.y>=from).map((p,i)=>(i?"L":"M")+x(p.y).toFixed(1)+" "+yy(p.v).toFixed(1)).join("");
  const changed = $("ct").value!=="1.0"||$("tr").value!=="1.0";
  $("lgb").style.display = changed?"":"none";
  if(changed) s+=`<path d="${path(c.base,last)}" fill="none" stroke="#8a8984" stroke-width="2" stroke-dasharray="5 4"/>`;
  s+=`<path d="${path(c.scen,c.yrs[0])}" fill="none" stroke="#2a78d6" stroke-width="2"/>`;
  const oy=Object.keys(obs).map(Number).sort();
  s+=`<path d="${oy.map((y,i)=>(i?"L":"M")+x(y).toFixed(1)+" "+yy(obs[y]).toFixed(1)).join("")}" fill="none" stroke="#0b0b0b" stroke-width="2"/>`;
  oy.forEach(y=>{ s+=`<circle cx="${x(y)}" cy="${yy(obs[y])}" r="4" fill="#0b0b0b" stroke="#fff" stroke-width="2"/>`; });
  s+=`<line id="xh" y1="${T}" y2="${H-B}" stroke="#52514e" stroke-dasharray="2 3" style="display:none"/>`+
     `<rect id="hit" x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}" fill="transparent"/>`;
  const svg=$("chart"); svg.innerHTML=s;
  $("hit").onmousemove=ev=>{ const r=svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*W;
    const i=Math.max(0,Math.min(c.yrs.length-1,Math.round((px-L)/(W-L-R)*(c.yrs.length-1)))), y=c.yrs[i];
    const xh=$("xh"); xh.setAttribute("x1",x(y)); xh.setAttribute("x2",x(y)); xh.style.display="";
    let h=`<b>${y}</b><br>`; if(obs[y]!==undefined) h+=`Reported: ${fmt(obs[y])}<br>`;
    h+=`Model: ${fmt(c.scen[i])}`; if(changed&&y>last) h+=`<br>No change: ${fmt(c.base[i])}`; tip(ev,h); };
  $("hit").onmouseleave=()=>{ untip(); $("xh").style.display="none"; };

  $("t1").textContent=`${NAMES[c.dis]}, ${c.st}`;
  const n=c.yrs.length-1, pct=(c.scen[n]-c.base[n])/c.base[n]*100;
  let tiles=`<div class="tile"><b>${fmt(obs[last])}</b><span>Reported rate, ${last}</span></div>`+
    `<div class="tile"><b>${fmt(c.scen[n])}</b><span>Modelled rate, ${D.forecast_to}</span></div>`;
  if(changed) tiles+=`<div class="tile"><b>${pct>0?"+":""}${pct.toFixed(1)}%</b><span>Against no change, ${D.forecast_to}</span></div>`;
  tiles+=`<div class="tile"><b>${c.m.alpha.toFixed(2)}</b><span>Fractional order alpha</span></div>`+
    `<div class="tile"><b>${(c.m.train_rmse_rel*100).toFixed(1)}%</b><span>Fit error (relative RMSE)</span></div>`;
  $("tiles").innerHTML=tiles;
  $("tbl").innerHTML="<table><tr><th>Year</th><th>Reported</th><th>Model</th><th>No change</th></tr>"+
    c.yrs.map((y,i)=>`<tr><td>${y}</td><td>${obs[y]!==undefined?fmt(obs[y]):""}</td><td>${fmt(c.scen[i])}</td><td>${fmt(c.base[i])}</td></tr>`).join("")+"</table>";
}

function drawMap(){
  const dis=$("dis").value, F=D.fits[dis];
  const vals={}; Object.keys(D.grid).forEach(s=>{ const o=F[s].observed, ys=Object.keys(o).map(Number); vals[s]=[o[Math.max(...ys)],Math.max(...ys)]; });
  const vs=Object.values(vals).map(v=>v[0]).sort((a,b)=>a-b), lo=vs[0], hi=vs[Math.floor(vs.length*0.96)];
  const ramp=t=>{ t=Math.max(0,Math.min(1,t)); const a=[222,235,250], b=[16,62,128];
    return "rgb("+a.map((v,i)=>Math.round(v+(b[i]-v)*t)).join(",")+")"; };
  const S=56,G=4,X0=170,Y0=6; let s="";
  Object.entries(D.grid).forEach(([st,[cx,cy]])=>{ const [v,yr]=vals[st], t=(v-lo)/(hi-lo);
    s+=`<g class="cell" data-s="${st}" data-v="${fmt(v)}" data-y="${yr}"><rect x="${X0+cx*(S+G)}" y="${Y0+cy*(S+G)}" width="${S}" height="${S}" rx="5" fill="${ramp(t)}"`+
       `${st===$("st").value?' stroke="#0b0b0b" stroke-width="2.5"':''}/>`+
       `<text x="${X0+cx*(S+G)+S/2}" y="${Y0+cy*(S+G)+S/2+4}" text-anchor="middle" style="fill:${t>0.5?'#fff':'#0b0b0b'};font-weight:600">${D.abbr[st]}</text></g>`; });
  for(let i=0;i<=20;i++) s+=`<rect x="${840}" y="${330-i*12}" width="16" height="12" fill="${ramp(i/20)}"/>`;
  s+=`<text x="862" y="342">${fmt(lo)}</text><text x="862" y="98">${fmt(hi)}+</text><text x="840" y="76">per 100,000</text>`;
  const svg=$("map"); svg.innerHTML=s;
  svg.querySelectorAll(".cell").forEach(g=>{ g.onmousemove=ev=>tip(ev,`<b>${g.dataset.s}</b><br>${fmt(+g.dataset.v)} per 100,000 (${g.dataset.y})`);
    g.onmouseleave=untip; g.onclick=()=>{ $("st").value=g.dataset.s; render(); }; });
  $("t2").textContent=`${NAMES[dis]}: latest reported rate by state`;
}

function drawBacktest(){
  const order=["integer","fractional","persistence","trend"], lab={integer:"Model, integer order",fractional:"Model, fractional order",persistence:"Persistence",trend:"Five-year trend"};
  let h="<table><tr><th>Forecaster</th><th>Chlamydia, 1 yr</th><th>Chlamydia, 2 yr</th><th>Syphilis, 1 yr</th><th>Syphilis, 2 yr</th></tr>";
  order.forEach(m=>{ h+=`<tr><td>${lab[m]}</td>`+["chlamydia|1","chlamydia|2","ps_syphilis|1","ps_syphilis|2"].map(k=>{
    const r=D.backtest[k+"|"+m]; return `<td>${r?r.median.toFixed(1)+"%":""}</td>`; }).join("")+"</tr>"; });
  $("bt").innerHTML=h+"</table>";
}
function render(){ drawChart(); drawMap(); }
["dis","st","mod","tr","ct"].forEach(id=>$(id).onchange=render);
drawBacktest(); render();
</script>
</body>
</html>
"""


def main():
    res = ROOT / "results"
    fits = read_json(res / "fits.json")
    summ = pd.read_csv(res / "summary.csv")
    src = read_json(ROOT / "data" / "SOURCES.json")
    bt = {f"{r.disease}|{r.horizon}|{r.model}": {"median": r["median"], "mean": r["mean"], "n": int(r.n)}
          for _, r in summ.iterrows()}
    any_fit = next(iter(fits["fits"]["chlamydia"].values()))["integer"]
    data = {"fits": fits["fits"], "treat": fits["treatment_multipliers"],
            "contact": fits["contact_multipliers"], "forecast_to": fits["forecast_to"],
            "grid": GRID, "abbr": ABBR, "backtest": bt}
    html = (TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
            .replace("__FORECAST_TO__", str(fits["forecast_to"]))
            .replace("__SCEN_YEAR__", str(max(f["integer"]["last_data_year"] for f in fits["fits"]["chlamydia"].values()) + 1))
            .replace("__BUILD_DATE__", date.today().isoformat())
            .replace("__RETRIEVED__", src["retrieved_utc"][:10]))
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(html, encoding="utf-8")
    print("wrote docs/index.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
