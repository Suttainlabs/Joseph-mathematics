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
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"cannot read {path}: {e}")


def read_summary(path):
    """Load the backtest summary table, with a clear message if it is missing or damaged."""
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as e:
        raise SystemExit(f"cannot read {path}: {e}. Run scripts/run_validation.py first.")


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
<p class="sub">A multi-stage transmission model whose contact rate is estimated from CDC surveillance
data each year and forecast by a machine-learning model trained on all states. Forecasts run to
__LAST_FC__, with what-if scenarios, state hotspots and an allocation exercise.</p>
<div class="note"><b>Research prototype.</b> Not for clinical or operational use. In backtests this
forecaster was less accurate than the simple rule "next year equals this year", except for syphilis two
years ahead, where it was about level. See the accuracy table below. Built __BUILD_DATE__.</div>

<div class="filters">
<label>Infection<select id="dis"><option value="chlamydia">Chlamydia</option>
<option value="ps_syphilis">Primary and secondary syphilis</option></select></label>
<label>Area<select id="st"></select></label>
<label>Diagnosis and treatment rate<select id="tr"></select></label>
<label>Contact rate<select id="ct"></select></label>
</div>

<div class="panel">
<h2 id="t1"></h2>
<div class="cap">Reported cases per 100,000 residents per year. Shaded band: range that held 80% of
past forecast errors (it covered about __COVER__ of cases when tested on held-out years). Past forecasts ran high, so the band sits mostly below the line. Scenario
changes start in __SCEN_YEAR__ and their size is very sensitive to model assumptions; read them as
direction, not magnitude.</div>
<div class="legend"><span><i style="border-color:var(--ink)"></i>Reported (CDC NNDSS)</span>
<span><i style="border-color:var(--s1)"></i>Forecast</span>
<span id="lgb"><i style="border-color:var(--muted);border-top-style:dashed"></i>Forecast with no change</span></div>
<svg id="chart" viewBox="0 0 1000 380" width="100%" role="img" aria-label="Reported and forecast case rates"></svg>
<div class="tiles" id="tiles"></div>
<details><summary>Show these numbers as a table</summary><div id="tbl"></div></details>
</div>

<div class="panel">
<h2 id="t2"></h2>
<div class="filters" style="margin:6px 0 8px"><label>Show<select id="metric">
<option value="fc">Forecast rate, __HOT_YEAR__</option><option value="obs">Latest reported rate</option>
<option value="chg">Forecast change from latest report</option></select></label></div>
<div class="cap">Each square is a state, placed roughly where it sits on the map. Select a square to load that state above.</div>
<svg id="map" viewBox="0 0 1000 496" width="100%" role="img" aria-label="Tile map of states"></svg>
<details><summary>Ten highest states as a table</summary><div id="hot"></div></details>
</div>

<div class="panel">
<h2>How accurate have the forecasts been?</h2>
<div class="cap">Rolling-origin backtest over the 50 states and DC. Each forecaster saw data through
2019, 2020, 2021, 2022 and 2023 in turn and forecast one and two years ahead. Figures are the median
absolute percentage error; lower is better.</div>
<div id="bt"></div>
</div>

<div class="panel">
<h2 id="t3"></h2>
<div class="cap">An exercise, not a recommendation. Budget: enough extra diagnosis-and-treatment capacity to raise the
rate 10% in every state. The cost of a step is assumed proportional to a state's current caseload. Capacity goes,
in 10-point steps up to 30%, to wherever the next step averts the most modelled cases per unit cost.</div>
<div id="alloc"></div>
</div>

<footer>
<p><b>Data.</b> CDC National Notifiable Diseases Surveillance System weekly tables on data.cdc.gov,
retrieved __RETRIEVED__; each year's count is read from the following year's final table. Population:
U.S. Census Bureau state estimates. National Inpatient Sample data are not used.</p>
<p><b>Method.</b> Chlamydia: susceptible, exposed, infected, on treatment, recovered. Syphilis: susceptible,
incubating, primary, secondary, early latent, treated. Solved with a fractional Adams-Bashforth-Moulton scheme
(order __ALPHA__ shown here). The learner is a gradient-boosted regression model.</p>
</footer>
</main>
<div id="tip"></div>
<script>
const D = __DATA__;
const $ = id => document.getElementById(id);
const fmt = v => v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2);
const NAMES = {chlamydia: "Chlamydia", ps_syphilis: "Primary and secondary syphilis"};
const TRL = {"1.0":"No change","1.1":"10% faster","1.2":"20% faster","1.3":"30% faster"};
const CTL = {"1.0":"No change","0.95":"5% lower","0.9":"10% lower"};
const key = v => Number.isInteger(v) ? v.toFixed(1) : String(v);
function opts(sel, vals, lab){ sel.innerHTML = vals.map(v => `<option value="${v}">${lab(v)}</option>`).join(""); }
opts($("tr"), D.treat.map(key), v => TRL[v] || v);
opts($("ct"), D.contact.map(key), v => CTL[v] || v);
const areas = Object.keys(D.fits.chlamydia).sort((a,b)=> a==="United States"?-1:b==="United States"?1:a.localeCompare(b));
opts($("st"), areas, v => v);
const FY = D.forecast_years, LAST = D.last_data_year;

function tip(ev, html){ const t=$("tip"); t.innerHTML=html; t.style.display="block";
  t.style.left=Math.min(ev.clientX+14, innerWidth-250)+"px"; t.style.top=(ev.clientY+14)+"px"; }
function untip(){ $("tip").style.display="none"; }
function band(dis, h){ const a=D.intervals[dis+"|1"], b=D.intervals[dis+"|2"];
  if(h===1) return [a.lo,a.hi]; const k=Math.sqrt(h/2); return [Math.pow(b.lo,k), Math.pow(b.hi,k)]; }

function drawChart(){
  const dis=$("dis").value, st=$("st").value, f=D.fits[dis][st];
  const scen=f.scenarios[$("ct").value+"|"+$("tr").value], base=f.scenarios["1.0|1.0"];
  const obs=f.observed, oy=Object.keys(obs).map(Number).sort((a,b)=>a-b), lastY=oy[oy.length-1];
  const y0=oy[0], y1=FY[FY.length-1], W=1000,H=380,L=56,R=24,T=14,B=34;
  const bands=FY.map((y,i)=>band(dis,i+1).map(m=>m*base[i]));
  const ymax=Math.max(...Object.values(obs),...scen,...bands.map(b=>b[1]))*1.08;
  const x=y=>L+(y-y0)/(y1-y0)*(W-L-R), yy=v=>H-B-(v/ymax)*(H-T-B);
  let s="";
  const step=Math.pow(10,Math.floor(Math.log10(ymax/4))); const tick=[1,2,5,10].map(k=>k*step).find(k=>ymax/k<=6);
  for(let v=0;v<=ymax;v+=tick){ s+=`<line x1="${L}" x2="${W-R}" y1="${yy(v)}" y2="${yy(v)}" stroke="#e4e3df"/>`+
    `<text x="${L-8}" y="${yy(v)+4}" text-anchor="end">${fmt(v).replace(/\.0+$/,"")}</text>`; }
  for(let y=y0;y<=y1;y++) if((y-y0)%2===0||y===y1) s+=`<text x="${x(y)}" y="${H-10}" text-anchor="middle">${y}</text>`;
  s+=`<text x="${x(FY[0])-4}" y="${T+12}">Forecast</text><line x1="${x(LAST)+ (x(FY[0])-x(LAST))/2}" x2="${x(LAST)+(x(FY[0])-x(LAST))/2}" y1="${T}" y2="${H-B}" stroke="#e4e3df" stroke-dasharray="3 3"/>`;
  const changed = $("ct").value!=="1.0"||$("tr").value!=="1.0";
  $("lgb").style.display = changed?"":"none";
  const up=[[LAST,obs[LAST]??base[0]],...FY.map((y,i)=>[y,bands[i][1]])], dn=[[LAST,obs[LAST]??base[0]],...FY.map((y,i)=>[y,bands[i][0]])].reverse();
  s+=`<path d="${[...up,...dn].map((p,i)=>(i?"L":"M")+x(p[0]).toFixed(1)+" "+yy(p[1]).toFixed(1)).join("")}Z" fill="#2a78d6" opacity="0.13"/>`;
  const line=arr=>[[LAST,obs[LAST]??arr[0]],...FY.map((y,i)=>[y,arr[i]])].map((p,i)=>(i?"L":"M")+x(p[0]).toFixed(1)+" "+yy(p[1]).toFixed(1)).join("");
  if(changed) s+=`<path d="${line(base)}" fill="none" stroke="#8a8984" stroke-width="2" stroke-dasharray="5 4"/>`;
  s+=`<path d="${line(scen)}" fill="none" stroke="#2a78d6" stroke-width="2"/>`;
  FY.forEach((y,i)=>{ s+=`<circle cx="${x(y)}" cy="${yy(scen[i])}" r="4" fill="#2a78d6" stroke="#fff" stroke-width="2"/>`; });
  s+=`<path d="${oy.map((y,i)=>(i?"L":"M")+x(y).toFixed(1)+" "+yy(obs[y]).toFixed(1)).join("")}" fill="none" stroke="#0b0b0b" stroke-width="2"/>`;
  oy.forEach(y=>{ s+=`<circle cx="${x(y)}" cy="${yy(obs[y])}" r="4" fill="#0b0b0b" stroke="#fff" stroke-width="2"/>`; });
  s+=`<line id="xh" y1="${T}" y2="${H-B}" stroke="#52514e" stroke-dasharray="2 3" style="display:none"/>`+
     `<rect id="hit" x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}" fill="transparent"/>`;
  const svg=$("chart"); svg.innerHTML=s;
  $("hit").onmousemove=ev=>{ const r=svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*W;
    const y=Math.max(y0,Math.min(y1,Math.round(y0+(px-L)/(W-L-R)*(y1-y0))));
    const xh=$("xh"); xh.setAttribute("x1",x(y)); xh.setAttribute("x2",x(y)); xh.style.display="";
    let h=`<b>${y}</b><br>`; const i=FY.indexOf(y);
    if(obs[y]!==undefined) h+=`Reported: ${fmt(obs[y])}`;
    if(i>=0){ h+=`Forecast: ${fmt(scen[i])}<br>80% band: ${fmt(bands[i][0])} to ${fmt(bands[i][1])}`; if(changed) h+=`<br>No change: ${fmt(base[i])}`; }
    tip(ev,h); };
  $("hit").onmouseleave=()=>{ untip(); $("xh").style.display="none"; };
  $("t1").textContent=`${NAMES[dis]}, ${st}`;
  const n=FY.length-1, pct=(scen[n]-base[n])/base[n]*100;
  let tiles=`<div class="tile"><b>${fmt(obs[lastY])}</b><span>Reported rate, ${lastY}</span></div>`+
    `<div class="tile"><b>${fmt(scen[1])}</b><span>Forecast rate, ${FY[1]}</span></div>`+
    `<div class="tile"><b>${fmt(bands[1][0])} to ${fmt(bands[1][1])}</b><span>80% band, ${FY[1]} (no change)</span></div>`;
  if(changed) tiles+=`<div class="tile"><b>${pct>0?"+":""}${pct.toFixed(0)}%</b><span>Against no change, ${FY[n]}</span></div>`;
  $("tiles").innerHTML=tiles;
  $("tbl").innerHTML="<table><tr><th>Year</th><th>Reported</th><th>Forecast</th><th>No change</th><th>80% band (no change)</th></tr>"+
    oy.map(y=>`<tr><td>${y}</td><td>${fmt(obs[y])}</td><td></td><td></td><td></td></tr>`).join("")+
    FY.map((y,i)=>`<tr><td>${y}</td><td></td><td>${fmt(scen[i])}</td><td>${fmt(base[i])}</td><td>${fmt(bands[i][0])} to ${fmt(bands[i][1])}</td></tr>`).join("")+"</table>";
}

function drawMap(){
  const dis=$("dis").value, F=D.fits[dis], metric=$("metric").value;
  const vals={}; Object.keys(D.grid).forEach(s=>{ const o=F[s].observed, ly=F[s].last_reported_year, fc=F[s].scenarios["1.0|1.0"][1];
    vals[s]= metric==="fc"?fc : metric==="obs"?o[ly] : (fc/o[ly]-1)*100; });
  const vs=Object.values(vals).sort((a,b)=>a-b);
  const seq=t=>{ t=Math.max(0,Math.min(1,t)); const a=[222,235,250], b=[16,62,128]; return "rgb("+a.map((v,i)=>Math.round(v+(b[i]-v)*t)).join(",")+")"; };
  const div=t=>{ t=Math.max(-1,Math.min(1,t)); const m=[236,235,231], e=t<0?[42,120,214]:[217,89,38]; return "rgb("+m.map((v,i)=>Math.round(v+(e[i]-v)*Math.abs(t))).join(",")+")"; };
  const lo=vs[0], hi=vs[Math.floor(vs.length*0.96)], amax=Math.max(Math.abs(vs[1]),Math.abs(vs[vs.length-2]));
  const col=v=> metric==="chg"? div(v/amax) : seq((v-lo)/(hi-lo));
  const dark=v=> metric==="chg"? Math.abs(v/amax)>0.6 : (v-lo)/(hi-lo)>0.5;
  const lab=v=> metric==="chg"? (v>0?"+":"")+v.toFixed(0)+"%" : fmt(v)+" per 100,000";
  const S=56,G=4,X0=170,Y0=6; let s="";
  Object.entries(D.grid).forEach(([st,[cx,cy]])=>{ const v=vals[st];
    s+=`<g class="cell" data-s="${st}" data-l="${lab(v)}"><rect x="${X0+cx*(S+G)}" y="${Y0+cy*(S+G)}" width="${S}" height="${S}" rx="5" fill="${col(v)}"`+
       `${st===$("st").value?' stroke="#0b0b0b" stroke-width="2.5"':''}/>`+
       `<text x="${X0+cx*(S+G)+S/2}" y="${Y0+cy*(S+G)+S/2+4}" text-anchor="middle" style="fill:${dark(v)?'#fff':'#0b0b0b'};font-weight:600">${D.abbr[st]}</text></g>`; });
  for(let i=0;i<=20;i++){ const t=i/20; s+=`<rect x="840" y="${330-i*12}" width="16" height="12" fill="${metric==="chg"?div(t*2-1):seq(t)}"/>`; }
  s+= metric==="chg" ? `<text x="862" y="342">-${amax.toFixed(0)}%</text><text x="862" y="222">0</text><text x="862" y="98">+${amax.toFixed(0)}%</text>`
     : `<text x="862" y="342">${fmt(lo)}</text><text x="862" y="98">${fmt(hi)}+</text><text x="840" y="76">per 100,000</text>`;
  const svg=$("map"); svg.innerHTML=s;
  svg.querySelectorAll(".cell").forEach(g=>{ g.onmousemove=ev=>tip(ev,`<b>${g.dataset.s}</b><br>${g.dataset.l}`);
    g.onmouseleave=untip; g.onclick=()=>{ $("st").value=g.dataset.s; render(); }; });
  const title={fc:`forecast rate by state, ${FY[1]}`,obs:"latest reported rate by state",chg:`forecast change by state, latest report to ${FY[1]}`}[metric];
  $("t2").textContent=`${NAMES[dis]}: ${title}`;
  const top=Object.entries(vals).sort((a,b)=>b[1]-a[1]).slice(0,10);
  $("hot").innerHTML="<table><tr><th>State</th><th>Value</th><th>Latest reported</th><th>Forecast "+FY[1]+"</th></tr>"+top.map(([st,v])=>
    `<tr><td>${st}</td><td>${lab(v)}</td><td>${fmt(F[st].observed[F[st].last_reported_year])}</td><td>${fmt(F[st].scenarios["1.0|1.0"][1])}</td></tr>`).join("")+"</table>";
}

function drawBacktest(){
  const rows=[["hybrid_a1.0","Transmission model + learned contact rate (this tool)"],["hybrid_a0.8","Same, fractional order 0.8"],
    ["momentum_a1.0","Transmission model, contact rate held constant"],["ml_rate","Learner on reported rates, no transmission model"],
    ["persistence","Next year equals this year"],["trend","Five-year straight line"]];
  let h="<table><tr><th>Forecaster</th><th>Chlamydia, 1 yr</th><th>Chlamydia, 2 yr</th><th>Syphilis, 1 yr</th><th>Syphilis, 2 yr</th></tr>";
  rows.forEach(([m,l])=>{ h+=`<tr><td>${l}</td>`+["chlamydia|1","chlamydia|2","ps_syphilis|1","ps_syphilis|2"].map(k=>{
    const r=D.backtest[k+"|"+m]; return `<td>${r?r.median.toFixed(1)+"%":""}</td>`; }).join("")+"</tr>"; });
  $("bt").innerHTML=h+"</table>";
}
function drawAlloc(){
  const dis=$("dis").value, a=D.allocation[dis];
  const top=Object.entries(a.averted).filter(([s])=>a.uplift_pct[s]>0).sort((x,y)=>y[1]-x[1]).slice(0,10);
  $("t3").textContent=`${NAMES[dis]}: where extra treatment capacity would avert the most modelled cases`;
  $("alloc").innerHTML=`<p>Even 10% everywhere: <b>${a.cases_averted_uniform.toLocaleString()}</b> modelled cases averted over ${a.years} years. `+
    `Targeted: <b>${a.cases_averted_targeted.toLocaleString()}</b>. The difference is ${((a.cases_averted_targeted/a.cases_averted_uniform-1)*100).toFixed(1)}%.</p>`+
    "<table><tr><th>State</th><th>Rate increase</th><th>Modelled cases averted</th></tr>"+top.map(([s,v])=>`<tr><td>${s}</td><td>${a.uplift_pct[s]}%</td><td>${v.toLocaleString()}</td></tr>`).join("")+"</table>";
}
function render(){ drawChart(); drawMap(); drawAlloc(); }
["dis","st","tr","ct","metric"].forEach(id=>$(id).onchange=render);
drawBacktest(); render();
</script>
</body>
</html>
"""


def national(fits):
    """Population-weighted national series built from the state results."""
    w = {s: v["population"] for s, v in fits.items()}
    tot = sum(w.values())
    years = sorted({int(y) for v in fits.values() for y in v["observed"]})
    obs = {}
    for y in years:
        have = [s for s in fits if observed_rate(fits[s], y) is not None]
        if len(have) >= len(fits) - 1:                       # allow one state missing in a year
            obs[y] = round(sum(observed_rate(fits[s], y) * w[s] for s in have) / sum(w[s] for s in have), 3)
    keys = next(iter(fits.values()))["scenarios"].keys()
    scen = {k: [round(sum(fits[s]["scenarios"][k][i] * w[s] for s in fits) / tot, 3)
                for i in range(len(next(iter(fits.values()))["scenarios"][k]))] for k in keys}
    return {"observed": obs, "scenarios": scen, "last_reported_year": max(obs),
            "population": tot, "last_cases": sum(v["last_cases"] for v in fits.values())}


def observed_rate(state_fit, year):
    """Reported rate for a year, or None. JSON turns the year keys into strings."""
    o = state_fit["observed"]
    return o.get(year, o.get(str(year)))


def main():
    res = ROOT / "results"
    fc = read_json(res / "forecasts.json")
    summ = read_summary(res / "summary.csv")
    src = read_json(ROOT / "data" / "SOURCES.json")
    bt = {f"{r.disease}|{r.horizon}|{r.model}": {"median": r["median"], "mean": r["mean"], "n": int(r.n)}
          for _, r in summ.iterrows()}
    fits = {}
    for dis, states in fc["fits"].items():
        fits[dis] = {st: {k: v[k] for k in ("observed", "scenarios", "last_reported_year")}
                     for st, v in states.items()}
        nat = national(states)
        fits[dis]["United States"] = {k: nat[k] for k in ("observed", "scenarios", "last_reported_year")}
    cover = sum(v["coverage_leave_one_origin_out"] for v in fc["intervals"].values()) / len(fc["intervals"])
    data = {"fits": fits, "treat": fc["treatment_multipliers"], "contact": fc["contact_multipliers"],
            "forecast_years": fc["forecast_years"], "last_data_year": fc["last_data_year"],
            "intervals": fc["intervals"], "allocation": fc["allocation"],
            "grid": GRID, "abbr": ABBR, "backtest": bt}
    html = (TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
            .replace("__LAST_FC__", str(fc["forecast_years"][-1]))
            .replace("__HOT_YEAR__", str(fc["forecast_years"][1]))
            .replace("__SCEN_YEAR__", str(fc["forecast_years"][0]))
            .replace("__COVER__", f"{cover * 100:.0f}%")
            .replace("__ALPHA__", fc["primary"].split("_a")[1])
            .replace("__BUILD_DATE__", date.today().isoformat())
            .replace("__RETRIEVED__", src["retrieved_utc"][:10]))
    out = ROOT / "docs" / "index.html"
    try:
        out.parent.mkdir(exist_ok=True)
        out.write_text(html, encoding="utf-8")
    except OSError as e:
        raise SystemExit(f"could not write {out}: {e}")
    print("wrote docs/index.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
