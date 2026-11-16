#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Early-warning & celebration engine + semester report drafter.
Reads data/phase2.json (fresh from collect.py), computes three risk indicators,
writes alerts/celebrations, parent email drafts (.eml), and — on the Jan 10 / Jun 10
windows or with --semester-report — drafts a <=500-word semester report per student.
"""
import json, os, sys, datetime as dt, glob
from collections import Counter

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(KIT, "data"); OUT = os.path.join(KIT, "output")
os.makedirs(OUT, exist_ok=True)
p2 = json.load(open(os.path.join(DATA, "phase2.json"), encoding="utf-8"))
meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
means = json.load(open(os.path.join(DATA, "class_means.json"), encoding="utf-8"))
TODAY = dt.date.today()
METRICS = ["Q1P", "Q1E", "Q1F", "Q2P", "Q2F", "S1P", "S1M"]
PATHWAYS = {
 "Science": ("STEM, biomedical science, engineering, environmental science",
             ["Keep one lab report per unit with a clear variable and error discussion.",
              "Add one stretch question per unit from a past paper or data-analysis task.",
              "Look for a science competition or a lab-based summer programme next term."]),
 "Mathematics": ("data science, economics, engineering, actuarial science",
                 ["Keep a mistake log and redo one wrong item each week.",
                  "Add one non-routine problem per week to build transfer.",
                  "Try a small data-analysis project linked to a real question."]),
 "English": ("international relations, law, media, translation",
             ["Read one short article per week and summarise it in three sentences.",
              "Build an academic word bank from your own writing errors.",
              "Join a debate or Model UN activity next term."]),
 "Chinese": ("journalism, education, law, cultural industries",
             ["Read one long-form piece per week and note its structure.",
              "Practise one timed writing piece per fortnight.",
              "Join a reading or writing club."]),
 "Humanities": ("law, policy, international studies, journalism",
                ["Practise source evaluation with one primary source per week.",
                 "Build a timeline of key events for each unit.",
                 "Write one argumentative paragraph per fortnight."]),
 "Arts": ("design, architecture, media production, creative industries",
          ["Keep a visual journal with one sketch per week.",
           "Document one process piece from idea to final work.",
           "Ask about portfolio requirements for your preferred pathway."]),
}
def pick_metric(st):
    for m in ["Q1P","S1P","Q1E","S1M","Q1F","Q2P","Q2F"]:
        if any(v is not None for v in st["values"].get(m, [])): return m
    return "Q1P"
def cls_of(s):
    return ((s.get("courses") or [{}])[0].get("className") or "")
def cohort(st, label, metric):
    cls = cls_of(st)
    vals = [s["values"][metric][i] for s in ROWS for i,l in enumerate(s["labels"]) if l==label and cls_of(s)==cls and s["values"][metric][i] is not None]
    return round(sum(vals)/len(vals),1) if len(vals)>=4 else None

# pre-compute labels/values from sections (same rules as the report)
ROWS = p2["students"]
GROUP_ORDER = {"English":0,"Chinese":1,"Mathematics":2,"Science":3,"Humanities":4,"Arts":5,"PE":6}
FLG = {"HF","ECP","CPA","CP","A1","A2","Main","Basic"}
def prep(st):
    secs = st.get("sections") or []
    best = {}
    for sec in secs:
        toks = sec["label"].split()
        key = (" ".join(toks[:-1]) if toks and toks[-1] in FLG else sec["label"]) + "|" + sec["course"]
        n = len(sec["scores"])
        if key not in best or n > best[key][1]:
            best[key] = (sec, n)
    secs = [v[0] for v in best.values()]
    labels = []
    for sec in secs:
        if sec["label"] not in labels: labels.append(sec["label"])
    labels.sort(key=lambda l: (GROUP_ORDER.get(next((x["group"] for x in secs if x["label"]==l), "Other"), 9), l))
    values = {}
    for m in METRICS:
        arr=[]
        for l in labels:
            sc=[x["scores"][m]["pct"] for x in secs if x["label"]==l and m in x["scores"]]
            arr.append(round(sum(sc)/len(sc),1) if sc else None)
        values[m]=arr
    st["labels"]=labels; st["values"]=values
for r in ROWS:
    prep(r)
for r in ROWS:
    if "values" not in r: r["values"]={m:[] for m in METRICS}

def analyse(st, values):
    m = pick_metric(st)
    pairs = [(l, values[m][i], None) for i,l in enumerate(st["labels"]) if values[m][i] is not None]
    pairs.sort(key=lambda x:x[1], reverse=True)
    avg = round(sum(v for _,v,_ in pairs)/len(pairs),1) if pairs else None
    low = min((v for _,v,_ in pairs), default=None)
    att = st.get("attendance") or {}; tasks = st.get("tasks") or {}
    entries = (st.get("diary") or {}).get("entries") or []
    pos = sum(1 for e in entries if not ("infraction" in ((e.get("primaryTypeEn") or "")+(e.get("primaryType") or "")).lower()) and (e.get("points") or 0)>0)
    inf = sum(1 for e in entries if "infraction" in ((e.get("primaryTypeEn") or "")+(e.get("primaryType") or "")).lower())
    now = dt.datetime.now().timestamp()*1000
    recent = [e for e in entries if (e.get("date") or 0) >= now-30*86400000]
    pos30 = sum(1 for e in recent if not ("infraction" in ((e.get("primaryTypeEn") or "")+(e.get("primaryType") or "")).lower()) and (e.get("points") or 0)>0)
    inf30 = sum(1 for e in recent if "infraction" in ((e.get("primaryTypeEn") or "")+(e.get("primaryType") or "")).lower())
    absent = (att.get("absent",0)+att.get("excused",0)) if att.get("recorded",0)>0 else 0
    I1 = (avg is not None and avg<60) or (low is not None and low<40)
    I2 = tasks.get("missing",0)>=3 or (att.get("recorded",0)>=10 and (att.get("rate") or 100)<90) or (tasks.get("nosub",0) or 0)>=3
    I3 = inf30>=1 or (pos30==0 and pos>0)
    alert = sum([I1,I2,I3])>=3
    celebrate = ((avg or 0)>=85 and pos30>=3 and inf30==0) or (pos30>=5 and inf30==0)
    return {"metric":m,"pairs":pairs,"avg":avg,"low":low,"pos":pos,"inf":inf,"pos30":pos30,"inf30":inf30,
            "absent":absent,"att":att,"tasks":tasks,"I1":I1,"I2":I2,"I3":I3,"alert":alert,"celebrate":celebrate}

def profile_text(st, a):
    info = st.get("info") or {}; facts=[]
    entered=""
    try: entered=dt.datetime.fromtimestamp((info.get("enterDate") or 0)/1000).strftime("%Y")
    except Exception: pass
    if entered: facts.append(f"enrolled since {entered}")
    facts.append("boarding" if info.get("boarding") else "day student")
    if info.get("house"): facts.append("house "+info["house"])
    if st.get("lifeBlock"): facts.append("Life Block: "+"; ".join(st["lifeBlock"][:3]))
    t=a["tasks"]; 
    if t.get("total"): facts.append(f"tasks {t.get('graded',0)}/{t['total']} graded, {t.get('missing',0)} missing")
    if a["att"].get("recorded",0)>0: facts.append(f"attendance {a['att'].get('rate')}%")
    else: facts.append("attendance not recorded this term")
    facts.append(f"Student Log {a['pos']} Golden Key / {a['inf']} infractions")
    insights=[]
    if a["pairs"]:
        l,v,_=a["pairs"][0]; ca=cohort(st,l,a["metric"])
        insights.append(f"Strength: {l} at {v}%." + (f" Class average {ca}%." if ca is not None else ""))
        if len(a["pairs"])>1:
            l2,v2,_=a["pairs"][-1]; c2=cohort(st,l2,a["metric"])
            insights.append(f"Growth area: {l2} at {v2}%." + (f" Class average {c2}%." if c2 is not None else "") + " This is the top priority for support.")
    if t.get("total"):
        insights.append(f"Engagement: {round(100*t.get('graded',0)/t['total'])}% of tasks graded, {t.get('missing',0)} missing, {t.get('nosub',0)} no-submission.")
    insights.append(f"Wellbeing: {a['pos30']} Golden Key and {a['inf30']} concern entries in the last 30 days.")
    if a["att"].get("recorded",0)>3: insights.append(f"Attendance: recorded rate {a['att'].get('rate')}%, {a['absent']} absences.")
    top = a["pairs"][0][0].split()[0] if a["pairs"] else "Science"
    pathway = PATHWAYS.get(top, PATHWAYS["Science"])
    plan = (f"Learning plan: {len(insights)} priorities — weekly 15-minute retrieval on {a['pairs'][-1][0] if len(a['pairs'])>1 else 'the weakest section'}, "
            f"one past-paper question, keep the strongest area ({a['pairs'][0][0] if a['pairs'] else 'Science'}) as a confidence anchor, and a short weekly reflection. "
            f"Suggested pathway: {pathway[0]}. How to get there: " + " ".join(pathway[1]))
    return facts, insights, plan, pathway

def eml(path, to, subject, body):
    open(path,"w",encoding="utf-8").write("From: Teacher\nTo: "+", ".join(to)+"\nSubject: "+subject+"\nMIME-Version: 1.0\nContent-Type: text/plain; charset=utf-8\n\n"+body)

def run_semester_reports(limit=None):
    season = "S1" if (TODAY.month==1 and TODAY.day>=10) else ("S2" if (TODAY.month==6 and TODAY.day>=10) else None)
    season = season or "S1"
    outdir = os.path.join(OUT, "semester_reports", season)
    os.makedirs(outdir, exist_ok=True)
    rows = ROWS[:limit] if limit else ROWS
    count=0
    for st in rows:
        a = analyse(st, st["values"])
        facts, insights, plan, pathway = profile_text(st,a)
        name = st["courses"][0].get("name") or str(st["studentId"])
        words = len((plan+" "+" ".join(insights)).split())
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Semester Report · {name}</title>
<style>body{{font-family:-apple-system,"PingFang SC",Arial;margin:24px;color:#1f2328;line-height:1.6;font-size:13px}}
h1{{color:#1f4e79;font-size:20px}} .box{{border:1px solid #d0d7de;border-radius:8px;padding:12px;margin:10px 0}}
li{{margin:4px 0}}</style></head><body>
<h1>Semester Report · 学期报告（草稿）</h1>
<p><b>{name}</b> · {st['courses'][0].get('className','')} · {meta.get('schoolYear','')} {season} · drafted {TODAY.isoformat()}</p>
<div class="box"><b>Profile</b><p>{'; '.join(facts)}.</p></div>
<div class="box"><b>Insights</b><ul>{''.join('<li>'+x+'</li>' for x in insights)}</ul></div>
<div class="box"><b>Learning plan & pathway</b><p>{plan}</p></div>
<div class="box"><b>Pathway steps</b><ol>{''.join('<li>'+x+'</li>' for x in pathway[1])}</ol></div>
<p style="color:#57606a;font-size:11px">Draft for teacher review · {words} words · data from IntSchool (read-only)</p>
</body></html>"""
        safe = name.replace("/","_").replace(" ","_")
        open(os.path.join(outdir, f"{safe}.html"),"w",encoding="utf-8").write(html)
        count+=1
    print(f"semester reports ({season}): {count} drafts -> {outdir}")

def main():
    alerts=[]; cels=[]
    for st in ROWS:
        a = analyse(st, st["values"])
        facts, insights, plan, pathway = profile_text(st,a)
        name = st["courses"][0].get("name") or str(st["studentId"])
        if a["alert"]:
            reasons = [k for k in ("I1","I2","I3") if a[k]]
            alerts.append({"student":name,"class":st["courses"][0].get("className",""),"reasons":reasons,"avg":a["avg"],"missing":a["tasks"].get("missing"),"concerns30":a["inf30"]})
            parents = st["courses"][0].get("parents") or []
            if parents:
                body=(f"Dear Parents of {name},\n\nWe have noticed three early signals in the last few weeks: "
                      f"academic progress averaging {a['avg']}%, {a['tasks'].get('missing',0)} missing tasks, and {a['inf30']} recent concern entries. "
                      f"This is an early signal, not a judgement. Our plan: a short one-to-one check-in, a catch-up plan for missing work, and a 15-minute call with you if helpful.\n\nThank you,\nTeacher")
                eml(os.path.join(OUT, f"alert_{name.replace(' ','_')}.eml"), parents, f"[Alert] Follow-up on {name}", body)
        if a["celebrate"]:
            cels.append({"student":name,"class":st["courses"][0].get("className",""),"avg":a["avg"],"pos30":a["pos30"]})
            parents = st["courses"][0].get("parents") or []
            if parents:
                body=(f"Dear Parents of {name},\n\nGood news: {name} has {a['pos30']} Golden Key entries in the last 30 days "
                      f"and is averaging {a['avg']}% across sections. That is worth naming — please pass on our congratulations.\n\nThank you,\nTeacher")
                eml(os.path.join(OUT, f"congrats_{name.replace(' ','_')}.eml"), parents, f"[Good news] {name}", body)
    stamp = TODAY.isoformat()
    json.dump({"generated":stamp,"alerts":alerts,"celebrations":cels}, open(os.path.join(OUT,f"early_warning_{stamp}.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    lines=[f"Early-warning scan · {stamp}", f"", f"Alerts (3 indicators): {len(alerts)}"]
    lines += [f"  • {x['student']} ({x['class']}) — {','.join(x['reasons'])}, avg {x['avg']}%, missing {x['missing']}, concerns30 {x['concerns30']}" for x in alerts]
    lines += ["", f"Celebrations: {len(cels)}"] + [f"  • {x['student']} ({x['class']}) — avg {x['avg']}%, Golden Keys 30d {x['pos30']}" for x in cels]
    md="\n".join(lines); open(os.path.join(OUT,f"early_warning_{stamp}.md"),"w",encoding="utf-8").write(md)
    print(md)
    if "--semester-report" in sys.argv or (TODAY.month==1 and TODAY.day>=10) or (TODAY.month==6 and TODAY.day>=10):
        limit=None
        if "--limit" in sys.argv: limit=int(sys.argv[sys.argv.index("--limit")+1])
        run_semester_reports(limit)

if __name__=="__main__":
    main()
