#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radar report card renderer v7 (kit): section axes, FLG, percentiles, log Top3,
attendance, privacy mode, radar hover details, full-width taller log chart,
summary below log, refresh button (live server), A4 single page."""
import json, os, re, datetime as dt
from collections import defaultdict, Counter

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(KIT, "data"); OUTDIR = os.path.join(KIT, "output")
os.makedirs(OUTDIR, exist_ok=True)
data = json.load(open(os.path.join(DATA, "phase2.json"), encoding="utf-8"))
means = json.load(open(os.path.join(DATA, "class_means.json"), encoding="utf-8"))
meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
TEACHER = meta.get("teacherName") or "Teacher"
NSTUD = meta.get("studentCount") or len(data.get("students", []))
GENERATED = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
METRICS = ["Q1P", "Q1E", "Q1F", "Q2P", "Q2F", "S1P", "S1M"]
COLORS = ["#1f4e79", "#c00000", "#1a7f37", "#b26a00", "#6f42c1", "#0f766e", "#9a3412"]
GROUP_ORDER = {"English": 0, "Chinese": 1, "Mathematics": 2, "Science": 3, "Humanities": 4, "Arts": 5, "PE": 6}
# level ladders: G6-8 HF>ECP>CPA>CP; G9 only A1>A2>Main>Basic; G10-12 AP>ECP>CP (English AP/ESL/EAL)
FLG_MS = ["HF", "ECP", "CPA", "CP"]
FLG_G9 = ["A1", "A2", "Main", "Basic"]
FLG_HS = ["AP", "ECP", "CP", "ESL", "EAL"]
FLG_ORDER = {}
for _codes in (FLG_MS, FLG_G9, FLG_HS):
    for _i, _c in enumerate(_codes): FLG_ORDER.setdefault(_c, _i)

def grade_of(cls):
    m = re.search(r"G(\d+)", str(cls or ""))
    return int(m.group(1)) if m else 0

def flg_rank(grade, flg):
    if not flg: return 9
    if grade and grade <= 8: codes = FLG_MS
    elif grade == 9: codes = FLG_G9
    else: codes = FLG_HS
    return codes.index(flg) if flg in codes else 9

def ordered_labels(sections, grade):
    labs = []
    for sec in sections:
        if sec["label"] not in labs: labs.append(sec["label"])
    def key(l):
        grp = next((s["group"] for s in sections if s["label"] == l), "Other")
        flg = next((s.get("flg", "") for s in sections if s["label"] == l), "")
        return (GROUP_ORDER.get(grp, 9), flg_rank(grade, flg), l)
    return sorted(labs, key=key)

ZH = [("General Science","综合科学"),("Morality and Law","道德与法治"),("Visual Art","视觉艺术"),
      ("Mathematics","数学"),("English","英语"),("Chinese","语文"),("Biology","生物"),("Physics","物理"),
      ("Chemistry","化学"),("Humanities","人文"),("Geography","地理"),("History","历史"),
      ("CDI","创意设计"),("ICS","计算机科学"),("Drama","戏剧"),("Musical","音乐剧"),("PE","体育"),("Arts","艺术")]

def zh_label(label):
    """MS axis label -> Chinese category (+ level code)."""
    toks = label.split()
    code = toks[-1] if toks and toks[-1] in FLG_ORDER else ""
    for en, zh in ZH:
        if label.startswith(en):
            return zh + ((" " + code) if code else "")
    return ""

ZH_CAT = [("biology", "生物"), ("physics", "物理"), ("chemistry", "化学"), ("computer", "计算机"),
          ("calculus", "数学"), ("statistics", "数学"), ("math", "数学"), ("english", "英语"),
          ("chinese", "语文"), ("economic", "经济"), ("geography", "地理"), ("history", "历史"),
          ("humanit", "人文"), ("social studies", "人文"), ("music", "音乐"), ("drama", "戏剧"),
          ("theatre", "戏剧"), ("design", "设计"), ("visual art", "视觉艺术"), ("art", "艺术"),
          ("physical education", "体育"), ("science", "科学")]

def zh_category(label):
    """HS axis label is a course name; the Chinese subtitle is only the subject."""
    t = (label or "").lower()
    for en, zh in ZH_CAT:
        if en in t:
            return zh
    return ""

def pick_metric(st):
    for m in ["Q1P", "S1P", "Q1E", "S1M", "Q1F", "Q2P", "Q2F"]:
        if any(v is not None for v in st["values"].get(m, [])): return m
    return "Q1P"

students = []
for s in data["students"]:
    c = (s.get("courses") or [{}])[0]
    secs = s.get("sections") or []
    grade = grade_of(c.get("className") or c.get("course") or "")
    FLGSET = set(FLG_ORDER.keys())
    def base_of(lbl):
        toks = lbl.split(); return " ".join(toks[:-1]) if toks and toks[-1] in FLGSET else lbl
    best = {}; dropped = []
    for sec in secs:
        if grade >= 9:
            # HS axes are course names: collapse only true duplicates of the same course
            k = sec["label"]
            if k not in best: best[k] = sec
            elif len(sec["scores"]) > len(best[k]["scores"]): dropped.append(best[k]); best[k] = sec
            else: dropped.append(sec)
            continue
        toks = sec["label"].split()
        if not (toks and toks[-1] in FLGSET):
            best[sec["label"] + "|" + sec["course"]] = (sec, 0); continue
        b = base_of(sec["label"]); n = len(sec["scores"])
        if b not in best: best[b] = (sec, n)
        elif n > best[b][1]: dropped.append(best[b][0]); best[b] = (sec, n)
        else: dropped.append(sec)
    secs = [v if grade >= 9 else v[0] for v in best.values()]
    labels = ordered_labels(secs, grade)
    vals = {}
    for m in METRICS:
        arr = []
        for l in labels:
            sc = [x["scores"][m]["pct"] for x in secs if x["label"] == l and m in x["scores"]]
            arr.append(round(sum(sc) / len(sc), 1) if sc else None)
        vals[m] = arr
    own = {}
    for sec in secs:
        for cname, cm in means.items():
            if cname.strip() == (sec["course"] or "").strip():
                own[sec["label"]] = dict(cm["means"]); break
    entries = [{"t": e["date"], "p": e.get("points") or 0,
                "inf": ("infraction" in ((e.get("primaryTypeEn") or "") + (e.get("primaryType") or "")).lower()),
                "ty": e.get("diaryEntryTypeEn") or e.get("diaryEntryType") or "",
                "de": (e.get("description") or "")[:90]} for e in ((s.get("diary") or {}).get("entries") or [])]
    d = s.get("diary") or {}
    pos_types = Counter(e["ty"] for e in entries if not e["inf"] and e["ty"])
    inf_types = Counter(e["ty"] for e in entries if e["inf"] and e["ty"])
    levels = {sec["label"]: sec.get("flg", "") for sec in secs}
    tasks = {sec["label"]: (sec.get("tasks") or []) for sec in secs}
    students.append({
        "id": s["studentId"], "name": c.get("name") or str(s["studentId"]),
        "class": c.get("className") or c.get("course") or "", "course": c.get("course", ""),
        "grade": grade, "ck": ("" if grade >= 9 else (c.get("className") or c.get("course") or "")),
        "advisory": bool(s.get("advisory")), "weighted": (c or {}).get("weightedPct"),
        "labels": labels,
        "labelZh": [(zh_category(x) if grade >= 9 else zh_label(x)) for x in labels],
        "levels": [levels.get(x, "") for x in labels],
        "values": vals, "ownMean": own, "entries": entries, "also": [f"{x['label']} ({x['course']})" for x in dropped],
        "sectionTasks": tasks, "taskTotals": s.get("tasks") or {}, "parents": (c.get("parents") or []),
        "info": s.get("info") or {}, "lifeBlock": s.get("lifeBlock") or [],
        "_diary": {"positives": d.get("positives", 0), "concerns": d.get("concerns", 0),
                   "topPos": pos_types.most_common(3), "topInf": inf_types.most_common(3)},
        "_att": s.get("attendance") or {},
    })

# cohort values / percentile
cohort = defaultdict(list)
for st in students:
    for i, l in enumerate(st["labels"]):
        for m in METRICS:
            v = st["values"][m][i]
            if v is not None: cohort[(st["ck"], l, m)].append(v)
cohort_mean = {f"{k[0]}|{k[1]}|{k[2]}": round(sum(v) / len(v), 1) for k, v in cohort.items()}
cohort_n = {f"{k[0]}|{k[1]}|{k[2]}": len(v) for k, v in cohort.items()}
for st in students:
    pr = {}
    for m in METRICS:
        arr = []
        for i, l in enumerate(st["labels"]):
            v = st["values"][m][i]
            vals = cohort.get((st["ck"], l, m), [])
            if v is None or len(vals) < 5: arr.append(None)
            else: arr.append(round(100 * sum(1 for x in vals if x <= v) / len(vals)))
        pr[m] = arr
    st["pctRank"] = pr

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

def compute_flags(st):
    m = pick_metric(st)
    vals = [v for v in st["values"][m] if v is not None]
    avg = round(sum(vals)/len(vals),1) if vals else None
    low = min(vals) if vals else None
    att = st["_att"]; tasks = st["taskTotals"] or {}
    import datetime as _dt
    now = _dt.datetime.now().timestamp()*1000
    recent = [e for e in st["entries"] if e["t"] >= now - 30*86400000]
    pos30 = sum(1 for e in recent if not e["inf"] and e["p"] > 0)
    conc30 = sum(1 for e in recent if e["inf"])
    absent = (att.get("absent",0)+att.get("excused",0)) if att.get("recorded",0) > 0 else 0
    I1 = (avg is not None and avg < 60) or (low is not None and low < 40)
    I2 = (tasks.get("missing",0) >= 3) or (att.get("recorded",0) >= 10 and (att.get("rate") or 100) < 90) or ((tasks.get("nosub",0) or 0) >= 3)
    I3 = conc30 >= 1 or (pos30 == 0 and st["_diary"]["positives"] > 0)
    alert = sum([I1,I2,I3]) >= 3
    celebrate = ((avg or 0) >= 85 and pos30 >= 3 and conc30 == 0) or (pos30 >= 5 and conc30 == 0)
    return {"avg":avg,"low":low,"pos30":pos30,"conc30":conc30,"absent":absent,
            "I1":I1,"I2":I2,"I3":I3,"alert":alert,"celebrate":celebrate}

def make_profile(st):
    m = pick_metric(st)
    pairs = [(l, st["values"][m][i], st["pctRank"][m][i]) for i,l in enumerate(st["labels"]) if st["values"][m][i] is not None]
    pairs.sort(key=lambda x:x[1], reverse=True)
    f = st["flags"]; info = st["info"] or {}; tasks = st["taskTotals"] or {}; att = st["_att"] or {}; d = st["_diary"]
    entered = ""
    try:
        import datetime as _dt
        entered = _dt.datetime.fromtimestamp((info.get("enterDate") or 0)/1000).strftime("%Y")
    except Exception:
        pass
    facts = []
    if entered: facts.append(f"Enrolled since {entered}")
    facts.append("Boarding" if info.get("boarding") else "Day student")
    if info.get("advisory"): facts.append("Advisory · " + str(info["advisory"]))
    if info.get("gender"): facts.append("Gender · " + str(info["gender"]))
    if info.get("birthday"):
        try:
            import datetime as _dt
            facts.append("DOB · " + _dt.datetime.fromtimestamp(info["birthday"] / 1000).strftime("%Y-%m-%d"))
        except Exception:
            pass
    if st["lifeBlock"]: facts.append("Life Block: " + "; ".join(st["lifeBlock"][:3]))
    total = tasks.get("total",0); graded = tasks.get("graded",0)
    if total:
        if graded / max(1,total) < 0.5:
            facts.append(f"Gradebook: only {graded} of {total} recorded tasks carry a mark (data gap — check before quoting missing work)")
        else:
            facts.append(f"Tasks: {graded}/{total} graded, {tasks.get('missing',0)} without a mark")
    if att.get("recorded",0) > 0: facts.append(f"Attendance recorded {att.get('rate')}% ({att.get('absent',0)+att.get('excused',0)} absence)")
    else: facts.append("Attendance: no usable records this term")
    facts.append(f"Student Log: {d['positives']} Golden Key, {d['concerns']} infractions")
    insights = []
    if pairs:
        a, v, p = pairs[0]
        ca = cohort_mean.get(f"{st['ck']}|{a}|{m}")
        insights.append(f"Strength: {a} at {v}%" + (f" (class average {ca}%, percentile {p})" if ca is not None else "") + ".")
        if len(pairs) > 1:
            b, w, wp = pairs[-1]
            cw = cohort_mean.get(f"{st['ck']}|{b}|{m}")
            insights.append(f"Growth area: {b} at {w}%" + (f" (class average {cw}%)" if cw is not None else "") + " — the clearest priority for support.")
    if total:
        rate = round(100*graded/total)
        insights.append(f"Engagement: {rate}% of recorded tasks graded; {tasks.get('missing',0)} missing and {tasks.get('nosub',0)} no-submission entries.")
    if f["pos30"] or f["conc30"]:
        insights.append(f"Wellbeing: {f['pos30']} Golden Key and {f['conc30']} concern entries in the last 30 days.")
    if att.get("recorded",0) > 3:
        insights.append(f"Attendance: recorded rate {att.get('rate')}%; absences {f['absent']}.")
    insights = insights[:5]
    top = pairs[0][0].split()[0] if pairs else "Science"
    pathway = PATHWAYS.get(top, PATHWAYS["Science"])
    plan = (f"Personal learning plan: focus on {pairs[-1][0] if len(pairs)>1 else 'consistency'} through one 15-minute weekly retrieval session "
            f"and one past-paper question; protect the strongest area ({pairs[0][0] if pairs else 'Science'}) as a confidence anchor. "
            f"Keep a simple weekly check: tasks completed, one Golden Key moment to name, and a short reflection. "
            f"Suggested pathway: {pathway[0]}. How to get there: " + " ".join(pathway[1]) + ".")
    en = f"Profile. " + "; ".join(facts) + ". " + " ".join(insights) + " " + plan
    zh = "；".join(facts[:3]) + f"。优势 {pairs[0][0]} {pairs[0][1]}%" if pairs else ""
    if len(pairs) > 1: zh += f"，增长点 {pairs[-1][0]} {pairs[-1][1]}%"
    zh += "。建议每周一次 15 分钟提取练习，配一道真题，并保留一次优势学科的正向反馈。"
    return {"facts": facts, "insights": insights, "plan": plan, "en": en, "zh": zh, "pathway": pathway}

def make_summary(st):
    m = pick_metric(st)
    pairs = [(l, st["values"][m][i], st["pctRank"][m][i]) for i, l in enumerate(st["labels"]) if st["values"][m][i] is not None]
    pairs.sort(key=lambda x: x[1], reverse=True)
    strong = pairs[:2]; weak = pairs[-2:][::-1] if len(pairs) > 1 else []
    log = st["_diary"]; att = st["_att"]
    parts = [f"This report uses the {m} metric."]
    def fmt_pairs(pairs):
        out = []
        for a, b, p in pairs:
            ca = cohort_mean.get(st["ck"] + "|" + a + "|" + m)
            s = f"{a} {b}%"
            if ca is not None:
                s += f" (class average {ca}%" + (f", percentile {p})" if p is not None else ")")
            out.append(s)
        return "; ".join(out)
    if strong:
        parts.append("Strongest sections: " + fmt_pairs(strong) + ".")
    if weak:
        parts.append("Sections needing support: " + fmt_pairs(weak) + ".")
    for a_m, b_m in [("Q1P", "Q1F"), ("S1P", "S1M"), ("Q1E", "Q1F")]:
        va = [v for v in st["values"].get(a_m, []) if v is not None]
        vb = [v for v in st["values"].get(b_m, []) if v is not None]
        if va and vb:
            diff = round(sum(vb) / len(vb) - sum(va) / len(va), 1)
            parts.append(f"Across sections, {b_m} is {'above' if diff >= 0 else 'below'} {a_m} by {abs(diff)} points on average.")
            break
    if att.get("recorded", 0) > 3:
        parts.append(f"Attendance: recorded rate {att.get('rate')}% with {att.get('absent', 0) + att.get('excused', 0)} absence(s).")
    else:
        parts.append("Attendance: this term the daily register has no usable records, so attendance is not used as a risk signal.")
    logline = f"Student Log: {log['positives']} Golden Key and {log['concerns']} infraction entr{'y' if log['concerns'] == 1 else 'ies'}."
    if log["topPos"]:
        logline += " Most frequent Golden Key: " + "; ".join(f"{a} ×{b}" for a, b in log["topPos"][:3]) + "."
    if log["topInf"]:
        logline += " Most frequent concern: " + "; ".join(f"{a} ×{b}" for a, b in log["topInf"][:3]) + "."
    parts.append(logline)
    sug = []
    if weak and weak[0][1] < 80:
        sug.append(f"Run a focused 15-minute weekly retrieval session on {weak[0][0]}, using one past-paper or checkpoint question each time.")
    if log["concerns"]:
        sug.append("Reinforce one routine at a time and name the Golden Key behaviour explicitly when it happens.")
    elif log["positives"] >= 3:
        sug.append("Keep naming and celebrating the Golden Key behaviours that already work, and share one concrete example with parents.")
    if att.get("recorded", 0) > 3 and (att.get("rate") or 100) < 90:
        sug.append("Follow up attendance with the homeroom teacher and agree a two-week check-in.")
    if strong:
        sug.append(f"Use {strong[0][0]} as a confidence anchor and share one specific win with parents or the advisor.")
    sug = sug[:3]
    en = " ".join(parts) + " Recommended next steps: " + " ".join(f"{i+1}) {x}" for i, x in enumerate(sug))
    zh = []
    if strong: zh.append("优势：" + "、".join(f"{a} {b}%" for a, b, *_ in strong))
    if weak: zh.append("增长点：" + "、".join(f"{a} {b}%" for a, b, *_ in weak))
    zh.append(f"学生日志：金钥匙 {log['positives']} 条、违规 {log['concerns']} 条")
    if log["topInf"]: zh.append("常见违规：" + "、".join(f"{a}×{b}" for a, b in log["topInf"][:2]))
    if sug: zh.append("建议：" + "；".join(["聚焦最弱 Section 做每周 15 分钟提取练习，配一道真题。", "一次强化一个常规。", "用优势科做信心锚点，与家长分享一个具体进步。"][:len(sug)]))
    return {"metric": m, "en": en, "zh": "。".join(zh) + "。",
            "share": f"{st['name']} · {st['class']} · {m}: " + ", ".join(f"{a} {b}%" for a, b, _ in strong) + f" · GK {log['positives']}, Infractions {log['concerns']}"}

for st in students:
    st["flags"] = compute_flags(st)
    st["profileData"] = make_profile(st)
    st["summary"] = make_summary(st)

from collections import Counter as _C
_course_counts = _C([ (st["course"] or "") for st in students if st.get("course") and not str(st["course"]).startswith("Advisory") ])
COURSES = [{"name": k, "n": v} for k, v in _course_counts.most_common()]
try:
    _cfg = json.load(open(os.path.join(KIT, "config.json"), encoding="utf-8"))
except Exception:
    _cfg = {}
DEFAULT_COURSE = _cfg.get("default_class") or (COURSES[0]["name"] if COURSES else "")
COURSES.sort(key=lambda c: (0 if c["name"] == DEFAULT_COURSE else 1, -c["n"]))
if DEFAULT_COURSE and not any(c["name"] == DEFAULT_COURSE for c in COURSES):
    DEFAULT_COURSE = COURSES[0]["name"] if COURSES else ""

payload = {"metrics": METRICS, "rows": students, "taskMeta": (data.get("taskMeta") or {}),
           "courses": COURSES, "defaultCourse": DEFAULT_COURSE,
           "cohortMean": cohort_mean, "cohortN": cohort_n,
           "generated": GENERATED, "teacher": TEACHER,
           "metricNote": {"Q1P": "Q1 进展", "Q1E": "Q1 期中", "Q1F": "Q1 最终（期中20%+平时80%）",
                          "Q2P": "Q2 进展", "Q2F": "Q2 最终", "S1P": "高中 S1 平时进展", "S1M": "高中 S1 期中总评"}}

html = r"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>雷达报告卡 · Radar Report Card</title>
<style>
:root{--blue:#1f4e79;--line:#d0d7de;--bg:#f6f8fa;--green:#1a7f37;--red:#c00000}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"PingFang SC","Segoe UI",Arial,sans-serif;color:#1f2328;background:#fff;font-size:13px}
header{padding:10px 18px;border-bottom:3px solid var(--blue);display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
h1{margin:0;font-size:17px;color:var(--blue)}
.meta{font-size:10.5px;color:#57606a}
.actions{display:flex;gap:6px;align-items:center;position:relative;flex-wrap:wrap}
.btn{border:1px solid var(--blue);background:#fff;color:var(--blue);border-radius:6px;padding:5px 10px;font-size:11.5px;cursor:pointer}
.btn.primary{background:var(--blue);color:#fff}
.btn:disabled{opacity:.5;cursor:wait}
.sharePanel{display:none;position:absolute;right:0;top:34px;background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.12);padding:9px;z-index:60;min-width:220px}
.sharePanel button{display:block;width:100%;text-align:left;margin:3px 0;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:#fff;font-size:11.5px;cursor:pointer}
.sharePanel small{color:#57606a;display:block;margin-top:5px;line-height:1.4;font-size:10px}
.wrap{display:grid;grid-template-columns:260px 1fr;min-height:calc(100vh - 58px)}
aside{background:var(--bg);border-right:1px solid var(--line);padding:10px;overflow:auto}
aside label{display:block;font-size:10.5px;font-weight:600;margin:7px 0 2px}
aside input,aside select{width:100%;padding:5px 7px;border:1px solid var(--line);border-radius:5px;font-size:12px}
.checks{display:flex;flex-wrap:wrap;gap:5px;margin:2px 0 4px}
.checks label{display:flex;align-items:center;gap:3px;font-weight:400;font-size:10.5px;margin:0;background:#fff;border:1px solid var(--line);border-radius:10px;padding:2px 6px;cursor:pointer}
.stu{display:block;width:100%;text-align:left;padding:5px 7px;margin:2px 0;border:1px solid transparent;border-radius:5px;background:#fff;cursor:pointer;font-size:11.5px}
.stu:hover{border-color:var(--line)} .stu.active{border-color:var(--blue);background:#e8f0f8}
.stu small{display:block;color:#57606a;font-size:10px}
main{padding:10px 16px 24px}
.card{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:12px;align-items:start}
.card table td{white-space:normal}
h2{margin:0 0 2px;font-size:20px}
.sub{color:#57606a;font-size:11.5px;margin-bottom:6px}
#radarBox svg{width:100%;height:auto;max-height:780px}
table{border-collapse:collapse;width:100%;font-size:9.2px}
th,td{border:1px solid var(--line);padding:3px 5px;text-align:left;white-space:nowrap}
th{background:var(--bg)}
.note{font-size:9.5px;color:#57606a;margin-top:5px;line-height:1.5}
.legend{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;color:#57606a;margin-top:3px}
.legend span{display:flex;align-items:center;gap:3px;cursor:help}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.logbox{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}
.logbox h3{margin:0 0 5px;font-size:12.5px;color:var(--blue)}
.controls{display:flex;gap:7px;flex-wrap:wrap;font-size:10.5px;color:#57606a;align-items:center;margin-bottom:4px}
.controls select{padding:2px 5px;font-size:10.5px;border:1px solid var(--line);border-radius:4px}
.summary{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}
.summary h3{margin:0 0 6px;font-size:20px;color:var(--blue)}
.summary p{margin:0 0 8px;line-height:1.55;font-size:19px}
.summary .zh{color:#333;font-size:18px}
.src{font-size:9px;color:#6b7280;margin-top:6px;line-height:1.5}
.profile{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}
.profile h3{margin:0 0 6px;font-size:20px;color:var(--blue)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px}
.chip{background:#eef3f8;border:1px solid #d6e0ea;border-radius:12px;padding:3px 9px;font-size:11px;color:#1f2328}
.profile ul{margin:4px 0 8px 18px;padding:0}
.profile li{font-size:14px;line-height:1.55;margin:2px 0}
.profile .plan{font-size:19px;line-height:1.55;margin:6px 0}
.profile .zh{font-size:14px;color:#333;line-height:1.55}
.badge{display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;margin-left:6px;vertical-align:middle}
.badge.alert{background:#fce4e4;color:#a00;border:1px solid #f0b4b4}
.badge.cel{background:#e2efda;color:#1a7f37;border:1px solid #b7dfb9}
.tooltip{position:fixed;display:none;background:#1f2328;color:#fff;font-size:10.5px;padding:6px 9px;border-radius:6px;pointer-events:none;z-index:99;line-height:1.5;max-width:430px}
.tooltip b{color:#fff}
.tooltip .tm{color:#9db8d2}
.tooltip .tx{margin-top:3px;color:#e6edf3}
.tooltip .tk{margin-top:3px;color:#b7c6d4;font-size:9.5px}
.hoverPanel{position:fixed;display:none;background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.15);padding:8px 10px;z-index:98;font-size:10px;max-width:420px}
.cpScroll{overflow-x:auto;overflow-y:hidden;max-width:390px;padding-bottom:2px}
.cpScroll svg{display:block}
.hoverPanel table{font-size:9.3px}
.hoverPanel .cpHead{font-size:11.5px;margin-bottom:1px}
.hoverPanel .cpHead .zh{color:#6b7280;font-size:10px;margin-left:4px}
.hoverPanel .cpSub{color:#57606a;font-size:9.5px;margin-bottom:3px}
.lv{display:inline-block;background:#eef3f8;border:1px solid #d6e0ea;border-radius:8px;padding:0 5px;font-size:8.5px;color:var(--blue);vertical-align:middle}
.tasks{margin-top:8px;border-top:1px solid var(--line);padding-top:7px}
.tasksHead{display:flex;justify-content:space-between;align-items:center;gap:8px}
.tasksHead h3{margin:0;font-size:12.5px;color:var(--blue)}
.taskGrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:4px}
.hl h4{margin:0 0 2px;font-size:10px;color:#57606a;font-weight:600}
.hl h4.up{color:var(--green)} .hl h4.down{color:var(--red)}
.hl table{font-size:8.8px;table-layout:fixed}
.hl th,.hl td{padding:2px 4px;overflow:hidden}
.hl col.cTask{width:auto} .hl col.cPct{width:52px} .hl col.cDt{width:34px}
.hl td.tn{white-space:nowrap}
.hl .tname{display:block;overflow:hidden;text-overflow:ellipsis}
.hl .tcourse{display:block;color:#8b949e;font-size:7.6px;overflow:hidden;text-overflow:ellipsis}
.hl .num{text-align:right;white-space:nowrap}
.hl .tscore{display:block;color:#8b949e;font-size:7.6px}
.hl .dt{color:#57606a}
.hl .miss{color:var(--red);font-weight:600}
.hl tr.empty td{color:#c9d1d9}
.hl .scroll{max-height:none}
.hl .scroll.expanded{max-height:320px;overflow:auto}
.btn.mini{padding:3px 8px;font-size:10px;border-radius:5px}
.week{margin-top:8px;border-top:1px solid var(--line);padding-top:7px}
.wkHead{display:flex;justify-content:space-between;align-items:center}
.wkHead h3{margin:0;font-size:12.5px;color:var(--blue)}
.wkGrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:5px}
.wkBox{border:1px solid var(--line);border-radius:8px;padding:7px 9px;background:#fbfcfe}
.wkBox h4{margin:0 0 3px;font-size:10px;color:#57606a;font-weight:600}
.wkBox .big{font-size:24px;font-weight:700;line-height:1.1;color:var(--blue)}
.wkBox .big.pos{color:var(--green)} .wkBox .big.neg{color:var(--red)} .wkBox .big.muted{color:#9aa7b4}
.wkBox .note{font-size:9px;color:#57606a;line-height:1.45}
.wkBox .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.wk{font-size:8.6px;border:1px solid #d6e0ea;border-radius:9px;padding:1px 6px;background:#fff;white-space:nowrap}
.wk.up{color:#1a7f37;border-color:#bfe0c4} .wk.down{color:#c00000;border-color:#f0c0c0}
.tbar{display:flex;align-items:center;gap:5px;font-size:8.8px;margin:2px 0}
.tbar .tk2{width:36px;color:#57606a} .tbar .tb{flex:1;height:7px;background:#eef2f6;border-radius:4px;overflow:hidden}
.tbar .tb i{display:block;height:100%;background:#1f4e79}
.tbar .tv{width:30px;text-align:right} .tbar .tn{width:22px;color:#8b949e;text-align:right}
.canary{margin:6px 0 0;background:#fff4e5;border-left:4px solid #e8a33d;padding:5px 9px;border-radius:4px;font-size:9.5px;color:#7a4b00}
.queue{font-size:10.5px;margin-top:6px}
.queue th{background:var(--bg)}
.queue tr[data-id]{cursor:pointer}
.queue tr[data-id]:hover{background:#eef3f8}
.queue td.act{color:#1f4e79}
.draftPanel{display:none;position:fixed;right:12px;top:60px;width:min(560px,92vw);background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.18);z-index:120;padding:10px}
.draftPanel textarea{width:100%;height:320px;font-size:11px;font-family:inherit;border:1px solid var(--line);border-radius:6px;padding:8px;line-height:1.5}
.draftPanel .row{display:flex;gap:6px;justify-content:flex-end;margin-top:6px}
.heat{font-size:10px;margin-top:6px;table-layout:fixed}
.heat th{text-align:center}
.heat td{text-align:center;padding:4px 3px;line-height:1.3;white-space:nowrap}
.heat td.cn{text-align:left;white-space:normal}
.heat .zz{color:#57606a;font-size:8px;display:block;font-weight:400;opacity:.85}
.heat .na{color:#c9d1d9;text-align:center}
.heat .num{text-align:right}
.flag{color:#c00000;font-size:8px;margin-left:2px}
.heat.pri td{white-space:normal;font-size:9px}
.comms{font-size:10.5px;margin-top:6px}
.comms td.num{text-align:right}
.comms .tcourse{display:block;color:#8b949e;font-size:8px}
.comms tr.over td{background:#fff4e5}
.comms tr.never td{background:#fdecec}
.selfPanel{display:none;position:fixed;inset:4% 6%;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 14px 40px rgba(0,0,0,.22);z-index:130;padding:18px 22px;overflow:auto}
.selfPanel h2{margin:0 0 4px}
.selfPanel .line{border-bottom:1px solid #c9d1d9;height:26px;margin:6px 0}
.selfPanel table{font-size:11px;margin:8px 0}
.selfPanel .row{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}
body.parent .pctCol,body.parent .avgCol{display:none}
body.parent .teacherOnly,body.parent .canary{display:none}
.limits{margin-top:10px;font-size:9.5px;color:#57606a}
.limits summary{cursor:pointer;color:var(--blue)}
body.privacy .pname{filter:blur(0);}
.foot{font-size:8.5px;color:#8b949e;text-align:center;margin-top:10px}
@media print{
 @page{size:A4 portrait;margin:6mm}
 body{zoom:0.70;font-size:10.5px}
 header{padding:4px 6px;border-width:2px}
 .actions{display:none}
 .wrap{display:block} aside{display:none} main{padding:2px}
 .card{grid-template-columns:minmax(0,1fr) 260px;gap:6px}
 #radarBox svg{max-height:340px}
 table{font-size:8px} th,td{padding:2px 3px;white-space:normal}
 .logbox{margin-top:5px;padding-top:4px}
 .logbox{display:none}
 .draftPanel,.heatPanel{display:none!important}
 body.selfprint header,body.selfprint .wrap,body.selfprint .tooltip{display:none!important}
 body.selfprint .selfPanel{position:static;display:block!important;inset:auto;border:0;box-shadow:none;padding:0}
 .week{margin-top:5px;padding-top:4px}
 .wkBox .big{font-size:12px} .wkBox .note{font-size:6.5px} .wkBox h4{font-size:7px}
 .canary{font-size:7px}
 .tasks{margin-top:5px;padding-top:4px}
 .tasksHead h3{font-size:10px}
 .taskGrid{gap:4px}
 .hl table{font-size:7px} .hl h4{font-size:8px}
 .hl .scroll.expanded{max-height:none;overflow:visible}
 .hl tr:nth-child(n+5){display:none}
 .summary p{font-size:10px} .summary h3{font-size:11px}
 .profile h3{font-size:12px} .profile li{font-size:8.5px} .profile .plan{font-size:9.5px} .profile .zh{font-size:8.5px} .chip{font-size:7.5px}
}
</style></head><body>
<header>
  <div>
    <h1>雷达报告卡 · Radar Report Card</h1>
    <div class="meta">Section axes · G6–8 subject + HF/ECP/CPA/CP · G9 A1/A2/Main/Basic · G10–12 course name (AP/ECP/CP; English AP/ESL/EAL) · Student Detail gradebook</div>
    <div class="meta">Generated __GENERATED__ · __NSTUD__ students · __TEACHER__</div>
  </div>
  <div class="actions">
    <button class="btn teacherOnly" id="queueBtn">本周队列 Queue</button>
    <button class="btn teacherOnly" id="heatBtn">教学优先 Priorities</button>
    <button class="btn teacherOnly" id="commsBtn">沟通 Comms</button>
    <button class="btn" id="selfBtn">学生自评页 Self-check</button>
    <button class="btn" id="draftBtn">家长草稿 Draft</button>
    <button class="btn" id="parentBtn">家长版 Parent</button>
    <button class="btn" id="privacyBtn">隐私模式 Privacy</button>
    <button class="btn" id="printBtn">打印/PDF</button>
    <button class="btn primary" id="shareBtn">分享 Share</button>
    <div class="sharePanel" id="sharePanel">
      <button id="copyBtn">复制摘要 Copy summary</button>
      <button id="emailBtn">邮件 Email</button>
      <button id="copyLinkBtn">复制链接 Copy link</button>
      <small>企业微信 / 微信 / Teams：复制摘要后粘贴；或系统分享面板中选择 App。</small>
    </div>
  </div>
</header>
<div class="wrap">
<aside>
  <label>Search 搜索（中/英文名或班级）</label>
  <input id="q" placeholder="例如 Jason / 董明翊 / G7-C">
  <label>Class 班级 / Course 课程</label>
  <select id="cls"></select>
  <label>Score metric 分数口径（可多选）</label>
  <div class="checks" id="metrics"></div>
  <label>Learner 学生</label>
  <div id="list" style="max-height:calc(100vh - 360px);overflow:auto"></div>
  <div class="note" id="mnote"></div>
</aside>
<main>
  <div id="card"></div>
</main>
</div>
<div class="tooltip" id="tip"></div>
<div class="selfPanel" id="selfPanel"></div>
<div class="draftPanel" id="draftPanel">
  <b>家长草稿 · Parent draft</b>
  <div class="note">中英对照，只生成文字，不会发送；用“邮件 Mail”会在 Outlook 里打开待发邮件。</div>
  <div class="note" id="draftTo"></div>
  <textarea id="draftText" readonly></textarea>
  <div class="note" id="draftStatus"></div>
  <div class="row">
    <button class="btn mini" id="draftCopy">复制 Copy</button>
    <button class="btn mini" id="draftMail">邮件 Mail（Outlook）</button>
    <button class="btn mini" id="draftClose">关闭 Close</button>
  </div>
</div>
<div class="hoverPanel" id="hoverPanel"></div>
<script>
const D = __DATA__;
const COLORS = __COLORS__;
let activeMetrics = ["Q1P"], current = null, privacy = false, parentView = false;
const clsSel = document.getElementById('cls');
(function buildClassSelect(){
  const all=document.createElement('option'); all.value=''; all.textContent='All classes 全部班级'; clsSel.appendChild(all);
  if((D.courses||[]).length){
    const g=document.createElement('optgroup'); g.label='我的课程 My courses 我的课程';
    D.courses.forEach(c=>{const o=document.createElement('option');o.value='course:'+c.name;o.textContent=c.name+' ('+c.n+')';g.appendChild(o);});
    clsSel.appendChild(g);
  }
  const g2=document.createElement('optgroup'); g2.label='班级 Classes 班级';
  [...new Set(D.rows.map(r=>r.class))].sort().forEach(c=>{const o=document.createElement('option');o.value='class:'+c;o.textContent=c||'—';g2.appendChild(o);});
  clsSel.appendChild(g2);
  clsSel.value = D.defaultCourse ? ('course:'+D.defaultCourse) : '';
})();
const mBox = document.getElementById('metrics');
D.metrics.forEach(m=>{
  const lab=document.createElement('label'); const cb=document.createElement('input'); cb.type='checkbox'; cb.value=m; cb.checked=(m==='Q1P');
  cb.onchange=()=>{activeMetrics=D.metrics.filter(x=>mBox.querySelector('input[value="'+x+'"]').checked); if(!activeMetrics.length){cb.checked=true;activeMetrics=[m]} renderList(); if(current) renderCard(current)};
  lab.appendChild(cb); lab.appendChild(document.createTextNode(m)); mBox.appendChild(lab);
});
document.getElementById('mnote').textContent = Object.entries(D.metricNote).map(([k,v])=>k+": "+v).join("；");
function dispName(st){ if(!privacy) return st.name; const parts=st.name.replace(/[（(].*?[）)]/g,'').split(/[,\s]+/).filter(Boolean); return (parts[0]?parts[0][0]:'?')+'.'+(parts[1]?parts[1][0]:'')+'. · '+st.class; }
function match(st,cls,label,metric){ const own=st.ownMean[label]&&st.ownMean[label][metric]; if(own!=null) return own; const n=D.cohortN[cls+'|'+label+'|'+metric]||0; return n>=5?(D.cohortMean[cls+'|'+label+'|'+metric]??null):null; }
function filtered(){ const q=document.getElementById('q').value.trim().toLowerCase(); const v=clsSel.value||'';
  const inScope=r=>{
    if(v.indexOf('course:')===0) return r.course===v.slice(7);
    if(v.indexOf('class:')===0) return r.class===v.slice(6);
    return true;
  };
  return D.rows.filter(r=>inScope(r)&&(!q||(r.name+' '+r.class+' '+r.course).toLowerCase().includes(q))); }
function renderList(){
  const list=document.getElementById('list'); list.innerHTML=''; const rows=filtered();
  rows.forEach(r=>{ const b=document.createElement('button'); b.className='stu'+(current&&current.id===r.id?' active':'');
    const have=D.metrics.filter(m=>r.values[m].some(v=>v!=null)).length;
    b.innerHTML=dispName(r)+'<small>'+r.class+' · '+r.labels.length+' sections · '+have+' metrics</small>';
    b.onclick=()=>{current=r;renderList();renderCard(r)}; list.appendChild(b); });
  if(!current&&rows.length){current=rows[0];renderList();renderCard(current)}
  if(!rows.length){document.getElementById('card').innerHTML='<h2>没有匹配的学生</h2>'}
}
function polar(cx,cy,r,ang){return [cx+r*Math.cos(ang-Math.PI/2),cy+r*Math.sin(ang-Math.PI/2)]}
function esc(t){return String(t==null?'':t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function fmtDate(t){if(!t)return '—';const d=new Date(t);return (d.getMonth()+1)+'-'+String(d.getDate()).padStart(2,'0')}
function wrapLabel(t,max){
  const ws=String(t||'').split(/\s+/).filter(Boolean); const out=[]; let cur='';
  for(const w of ws){ if(!cur) cur=w; else if((cur+' '+w).length<=max) cur+=' '+w; else {out.push(cur);cur=w;} }
  if(cur) out.push(cur);
  if(out.length>3){ const last=out.slice(2).join(' '); out.length=2; out.push(last.length>max?last.slice(0,max-1)+'…':last); }
  return out;
}
function radar(st){
  const axes=st.labels,zh=st.labelZh||axes.map(()=>""),N=axes.length; const W=1000,H=830,cx=500,cy=405,R=288;
  if(!N) return '<div style="color:#8b949e">No gradebook data</div>';
  const rings=[0.2,0.4,0.6,0.8,1].map(f=>{const pts=Array.from({length:N},(_,i)=>polar(cx,cy,R*f,i*2*Math.PI/N).join(',')).join(' ');return '<polygon points="'+pts+'" fill="none" stroke="#e6ebf1"/>'}).join('');
  const ax=Array.from({length:N},(_,i)=>{const [x,y]=polar(cx,cy,R,i*2*Math.PI/N),[lx,ly]=polar(cx,cy,R+52,i*2*Math.PI/N);
    const lines=wrapLabel(axes[i],18);
    const fs=lines.length>=3?15:17, lh=fs+5;
    const blockH=lines.length*lh+(zh[i]?17:0); const y0=ly-blockH/2+fs;
    let tsp=lines.map((t,li)=>'<tspan x="'+lx+'" y="'+(y0+li*lh)+'" font-size="'+fs+'">'+esc(t)+'</tspan>').join('');
    if(zh[i]) tsp+='<tspan x="'+lx+'" y="'+(y0+lines.length*lh)+'" font-size="12" fill="#6b7280">'+esc(zh[i])+'</tspan>';
    return '<g class="axis" data-i="'+i+'" style="cursor:pointer"><circle cx="'+lx+'" cy="'+ly+'" r="'+(blockH/2+8)+'" fill="transparent"/>'+
      '<line x1="'+cx+'" y1="'+cy+'" x2="'+x+'" y2="'+y+'" stroke="#c9d1d9"/><text text-anchor="middle">'+tsp+'</text></g>'}).join('');
  const poly=(arr,color,fill,w,dash)=>{const pts=arr.map((v,i)=>polar(cx,cy,R*((v==null?0:v)/100),i*2*Math.PI/N).join(',')).join(' ');
    return '<polygon points="'+pts+'" fill="'+fill+'" stroke="'+color+'" stroke-width="'+w+'"'+(dash?' stroke-dasharray="'+dash+'"':'')+'/>'};
  let series='';
  activeMetrics.forEach((m,mi)=>series+=poly(st.values[m],COLORS[mi%COLORS.length],COLORS[mi%COLORS.length]+'22',2.2,''));
  if(activeMetrics.length===1 && !parentView) series+=poly(axes.map(a=>match(st,st.ck,a,activeMetrics[0])),'#9aa7b4','rgba(154,167,180,.08)',1.3,'4 3');
  const dots=activeMetrics.map((m,mi)=>st.values[m].map((v,i)=>v==null?'':('<circle cx="'+polar(cx,cy,R*v/100,i*2*Math.PI/N)[0]+'" cy="'+polar(cx,cy,R*v/100,i*2*Math.PI/N)[1]+'" r="3" fill="'+COLORS[mi%COLORS.length]+'"/>')).join('')).join('');
  return '<svg viewBox="0 0 '+W+' '+H+'" data-w="'+W+'" data-h="'+H+'" data-cx="'+cx+'" data-cy="'+cy+'" data-r="'+R+'">'+rings+ax+series+dots+'</svg>';
}
// ---- per-course gradebook chart (hover an axis label) ----
function coursePanel(st,i){
  const lab=st.labels[i], zh=(st.labelZh||[])[i]||'', lv=(st.levels||[])[i]||'';
  const all=((st.sectionTasks||{})[lab])||[];
  // newest first; every task of the term is kept so the list can be scrolled back to week 1
  const rows=all.map((t,idx)=>({t:t,idx:idx})).sort((a,b)=>((b.t.end||0)-(a.t.end||0)));
  const shown=rows;
  const W=Math.max(300,shown.length*24+40),H=200,padL=22,padR=6,top=24,bot=34;
  const bw=(W-padL-padR)/Math.max(1,shown.length), base=H-bot, h100=base-top;
  const scored=shown.filter(r=>r.t.pct!=null).map(r=>r.t.pct);
  const avg=scored.length?Math.round(scored.reduce((a,b)=>a+b,0)/scored.length):null;
  let grid='';
  [0,50,100].forEach(p=>{const y=base-h100*p/100;
    grid+='<line x1="'+padL+'" y1="'+y+'" x2="'+(W-padR)+'" y2="'+y+'" stroke="#e6ebf1"/>'+
          '<text x="'+(padL-4)+'" y="'+(y+3)+'" font-size="8" fill="#8b949e" text-anchor="end">'+p+'</text>';});
  let bars='';
  shown.forEach((row,k)=>{
    const t=row.t, x=padL+k*bw+2, w=Math.max(4,bw-4);
    if(t.pct==null){
      bars+='<rect class="bar" data-i="'+row.idx+'" x="'+x+'" y="'+top+'" width="'+w+'" height="'+h100+'" fill="#fdf1f1" stroke="#e2a3a3" stroke-dasharray="2 3" stroke-width=".8"/>'+
        '<text x="'+(x+w/2)+'" y="'+(top+9)+'" font-size="8" fill="#c00000" text-anchor="middle">?</text>';
      return;
    }
    const h=Math.max(2,h100*t.pct/100);
    const col=t.pct>=85?'#1a7f37':t.pct>=70?'#7fb069':t.pct>=50?'#d0a215':'#c00000';
    bars+='<rect class="bar" data-i="'+row.idx+'" x="'+x+'" y="'+(base-h)+'" width="'+w+'" height="'+h+'" fill="'+col+'" rx="1"/>';
  });
  const showLv=lv&&!new RegExp('(^|[ .-])'+lv.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$','i').test(lab);
  return '<div class="cpHead"><b>'+esc(lab)+'</b>'+(showLv?' <span class="lv">'+esc(lv)+'</span>':'')+(zh?' <span class="zh">'+esc(zh)+'</span>':'')+'</div>'+
    '<div class="cpSub">共 '+shown.length+' 项 · 最新在左 · 左右滚动看更早'+(avg!=null?' · 均分 '+avg+'%':'')+' · 柱高=得分÷满分</div>'+
    '<div class="cpScroll"><svg width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'">'+grid+bars+'</svg></div>';
}
let hideTimer=null;
function scheduleHide(){clearTimeout(hideTimer);hideTimer=setTimeout(()=>{document.getElementById('hoverPanel').style.display='none';hideTip();},200);}
function cancelHide(){clearTimeout(hideTimer);}
function showTaskTip(st,lab,idx,ev){
  const t=((st.sectionTasks||{})[lab]||[])[idx]; if(!t) return;
  const meta=(D.taskMeta||{})[String(t.id)]||{};
  const pct=t.pct==null?'缺交（未录分）':t.pct+'%';
  let h='<b>'+esc(t.name)+'</b>';
  h+='<div class="tm">'+esc(t.type||'Task')+(t.abbr?' · '+esc(t.abbr):'')+' · '+fmtDate(t.end)+' · '+pct+(t.score!=null?' · '+t.score+'/'+t.top:'')+'</div>';
  if(meta.de) h+='<div class="tx">'+esc(String(meta.de).slice(0,260))+(String(meta.de).length>260?'…':'')+'</div>';
  if(meta.rs&&meta.rs.length) h+='<div class="tk">附件：'+esc(meta.rs.join(' · '))+'</div>';
  const flags=[];
  if(meta.it===false) flags.push('不计入总评');
  if(meta.pf===false) flags.push('学生/家长不可见');
  if(flags.length) h+='<div class="tk">'+flags.join(' · ')+'</div>';
  showTip(h);
}
function bindCourseBars(st,lab){
  document.querySelectorAll('#hoverPanel rect.bar').forEach(el=>{
    el.style.cursor='help';
    el.onmouseenter=ev=>showTaskTip(st,lab,Number(el.getAttribute('data-i')),ev);
    el.onmousemove=moveTip;
    el.onmouseleave=hideTip;
  });
}
function showCourse(st,i,ev){
  const p=document.getElementById('hoverPanel');
  p.innerHTML=coursePanel(st,i); p.style.display='block';
  p.onmouseenter=cancelHide; p.onmouseleave=scheduleHide;
  bindCourseBars(st,st.labels[i]);
  const w=p.offsetWidth,h=p.offsetHeight;
  let x=ev.clientX+18,y=ev.clientY-30;
  if(x+w>window.innerWidth-8) x=ev.clientX-w-18;
  if(y+h>window.innerHeight-8) y=window.innerHeight-h-8;
  p.style.left=Math.max(8,x)+'px'; p.style.top=Math.max(8,y)+'px';
}
function bucketTs(entries,gran,win){
  const now=Date.now();
  const earliest=entries.length?Math.min(...entries.map(e=>e.t)):now-120*86400000;
  let start = win==='all' ? Math.min(earliest, now-60*86400000) : now-Number(win)*86400000;
  start = Math.min(start, now);
  const dayKey=t=>{const d=new Date(t);const day=(d.getUTCDay()+6)%7;return new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()-day)).toISOString().slice(0,10)};
  const key=t=>{ if(gran==='day') return new Date(t).toISOString().slice(0,10);
    if(gran==='week') return dayKey(t);
    if(gran==='month') return new Date(t).toISOString().slice(0,7);
    return new Date(t).toISOString().slice(0,4); };
  const keys=[]; const d=new Date(start);
  if(gran==='day'){ let t=Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()); for(;t<=now;t+=86400000) keys.push(new Date(t).toISOString().slice(0,10)); }
  else if(gran==='week'){ let t=Date.parse(dayKey(start)+'T00:00:00Z'); for(;t<=now;t+=7*86400000) keys.push(new Date(t).toISOString().slice(0,10)); }
  else if(gran==='month'){ let y=d.getUTCFullYear(),m=d.getUTCMonth(); for(;;){const t=Date.UTC(y,m,1); if(t>now) break; keys.push(new Date(t).toISOString().slice(0,7)); m++; if(m>11){m=0;y++} } }
  else { let y=d.getUTCFullYear(); for(;;){const t=Date.UTC(y,0,1); if(t>now) break; keys.push(String(y)); y++; } }
  const map={}; for(const k of keys) map[k]={gk:0,inf:0,items:[]};
  for(const e of entries){ if(e.t<start) continue; const k=key(e.t); if(!map[k]) map[k]={gk:0,inf:0,items:[]}; if(e.inf)map[k].inf++;else if(e.p>0)map[k].gk++; map[k].items.push(e); }
  return keys.map(k=>({k,...map[k]}));
}
function trendChart(st){
  const gran=document.getElementById('gran')?document.getElementById('gran').value:'week';
  const win=document.getElementById('win')?document.getElementById('win').value:'all';
  const rows=bucketTs(st.entries,gran,win);
  if(!rows.length) return '<div style="color:#8b949e;font-size:11px">No Student Log entries in this window.</div>';
  const W=1100,H=240,pad=30,bw=(W-pad*2)/rows.length, max=Math.max(1,...rows.map(r=>Math.max(r.gk,r.inf))), y=v=>H-pad-(v/max)*(H-pad*2);
  let bars='';
  rows.forEach((r,i)=>{const x=pad+i*bw,w2=Math.max(3,(bw-6)/2);
    bars+='<rect class="bar" data-json=\''+JSON.stringify(r).replace(/'/g,"&#39;")+'\' x="'+x+'" y="'+y(r.gk)+'" width="'+w2+'" height="'+(H-pad-y(r.gk))+'" fill="#1a7f37"/>';
    bars+='<rect class="bar" data-json=\''+JSON.stringify(r).replace(/'/g,"&#39;")+'\' x="'+(x+w2+2)+'" y="'+y(r.inf)+'" width="'+w2+'" height="'+(H-pad-y(r.inf))+'" fill="#c00000"/>';});
  const labels=rows.map((r,i)=>i%Math.ceil(rows.length/10)===0?'<text x="'+(pad+i*bw)+'" y="'+(H-8)+'" font-size="8" fill="#57606a">'+r.k.slice(-5)+'</text>':'').join('');
  const ticks=rows.map((r,i)=>'<line x1="'+(pad+i*bw+bw/2)+'" y1="'+(H-pad)+'" x2="'+(pad+i*bw+bw/2)+'" y2="'+(H-pad+3)+'" stroke="#d0d7de"/>').join('');
  return '<svg width="100%" viewBox="0 0 '+W+' '+H+'">'+bars+labels+ticks+'</svg>';
}
function showTip(html){const t=document.getElementById('tip');t.innerHTML=html;t.style.display='block';}
function moveTip(ev){const t=document.getElementById('tip');t.style.left=(ev.clientX+12)+'px';t.style.top=(ev.clientY-30)+'px';}
function hideTip(){document.getElementById('tip').style.display='none';}
// ---- top / bottom / missing tasks ----
// Collapsed: top/bottom over the last four weeks, missing over the last week.
// "Show all": every task in the term, in the same three cuts.
let showAllTasks=false;
function taskRows(st,days){
  const now=Date.now(),out=[];
  for(const lab of st.labels){
    for(const t of ((st.sectionTasks||{})[lab]||[])){
      if(!t.end||t.end>now) continue;                       // not due yet
      if(days&&t.end<now-days*86400000) continue;
      out.push({lab:lab,name:t.name,pct:t.pct,score:t.score,top:t.top,end:t.end,id:t.id,ty:t.type});
    }
  }
  return out;
}
function hlTable(title,cls,rows,expanded){
  const body=rows.map(r=>'<tr><td class="tn"><span class="tname">'+esc(r.name)+'</span><span class="tcourse">'+esc(r.lab)+'</span></td>'+
      '<td class="num">'+(r.pct==null?'<span class="miss">missing</span>':r.pct+'%')+
      '<span class="tscore">'+(r.score==null?'—':r.score+'/'+r.top)+'</span></td>'+
      '<td class="num dt">'+fmtDate(r.end)+'</td></tr>').join('');
  const want=expanded?0:3-rows.length;
  let emptyRows='';
  for(let i=0;i<want;i++) emptyRows+='<tr class="empty"><td colspan="3">—</td></tr>';
  return '<div class="hl"><h4 class="'+cls+'">'+title+'</h4>'+
    '<div class="scroll'+(expanded?' expanded':'')+'"><table><colgroup><col class="cTask"><col class="cPct"><col class="cDt"></colgroup>'+
    '<tr><th>Task</th><th>%</th><th>Date</th></tr>'+body+emptyRows+'</table></div></div>';
}
function taskBlock(st){
  const term=taskRows(st,0), month=taskRows(st,28), week=taskRows(st,7);
  const base=showAllTasks?term:month;
  const scored=base.filter(r=>r.pct!=null);
  for(const r of scored) r.pct=Math.round(r.pct*10)/10;
  const top=[...scored].sort((a,b)=>b.pct-a.pct).slice(0,showAllTasks?9999:3);
  const low=[...scored].sort((a,b)=>a.pct-b.pct).slice(0,showAllTasks?9999:3);
  const missSrc=showAllTasks?term.filter(r=>r.pct==null):week.filter(r=>r.pct==null);
  const mis=[...missSrc].sort((a,b)=>b.end-a.end).slice(0,showAllTasks?9999:3);
  const win=showAllTasks?'本学期':'近 4 周';
  return '<div class="tasks"><div class="tasksHead"><h3>Task highlights · 任务亮点</h3>'+
    '<span class="controls">'+
      '<span class="note" style="margin:0">'+(showAllTasks?'本学期 · 全部 ':'')+'仅统计已截止任务 · 未录分=缺交</span>'+
      '<button class="btn mini" id="moreBtn" onclick="showAllTasks=!showAllTasks;renderCard(current)">'+
        (showAllTasks?'收起 Collapse':'展开本学期全部 Show all')+'</button>'+
    '</span></div>'+
    '<div class="taskGrid">'+
      hlTable((showAllTasks?'Top · ':'Top 3 · ')+win+'最高','up',top,showAllTasks)+
      hlTable((showAllTasks?'Bottom · ':'Bottom 3 · ')+win+'最低','down',low,showAllTasks)+
      hlTable((showAllTasks?'Missing · ':'Missing 3 · ')+(showAllTasks?'本学期':'近 1 周')+'缺交','none',mis,showAllTasks)+
    '</div></div>';
}

// ---- weekly reading: attribution, stability, forecast, type profile ----
function taskWeight(t){
  const a=(t.abbr||'').toUpperCase(), ty=(t.type||'').toLowerCase();
  if(a==='H')return 10; if(a==='IA')return 15; if(a==='Q')return 15; if(a==='PL'||a==='P')return 20;
  if(ty.indexOf('homework')>=0)return 10;
  if(ty.indexOf('quiz')>=0)return 15;
  if(ty.indexOf('test')>=0||ty.indexOf('exam')>=0)return 40;
  if(ty.indexOf('project')>=0||ty.indexOf('lab')>=0||ty.indexOf('experiment')>=0||ty.indexOf('practical')>=0)return 20;
  if(ty.indexOf('in-class')>=0||ty.indexOf('classwork')>=0)return 15;
  return 10;
}
function wavg(list){
  let s=0,w=0;
  for(const t of list){ if(t.pct==null) continue; const k=taskWeight(t); s+=t.pct*k; w+=k; }
  return w? s/w : null;
}
function flatTasks(st){
  const out=[];
  for(const lab of st.labels) for(const t of ((st.sectionTasks||{})[lab]||[])) out.push(Object.assign({lab:lab},t));
  out.sort((a,b)=>(a.end||0)-(b.end||0));
  return out;
}
function weekStats(st){
  const now=Date.now(), all=flatTasks(st).filter(t=>t.end&&t.end<=now);
  const w1=all.filter(t=>t.end>=now-7*864e5), w0=all.filter(t=>t.end>=now-14*864e5&&t.end<now-7*864e5);
  const c1=wavg(w1), c0=wavg(w0);
  const delta=(c1!=null&&c0!=null)?c1-c0:null;
  const per=[];
  for(const lab of st.labels){
    const a=wavg(w1.filter(t=>t.lab===lab)), b=wavg(w0.filter(t=>t.lab===lab));
    if(a!=null&&b!=null) per.push({lab:lab,d:a-b});
  }
  per.sort((x,y)=>y.d-x.d);
  const scored=all.filter(t=>t.pct!=null);
  const last=scored.slice(-6).map(t=>t.pct);
  const m=last.length?last.reduce((a,b)=>a+b,0)/last.length:null;
  const sd=last.length>1?Math.sqrt(last.reduce((a,b)=>a+(b-m)*(b-m),0)/(last.length-1)):null;
  let drift=0;
  if(scored.length>=6){ const a=scored.slice(-3).map(t=>t.pct), b=scored.slice(-6,-3).map(t=>t.pct);
    drift=(a.reduce((x,y)=>x+y,0)/3)-(b.reduce((x,y)=>x+y,0)/3); }
  const fc=m!=null?Math.round(Math.max(0,Math.min(100,m+drift*0.5))):null;
  const band=Math.max(5,Math.round((sd||0)*0.9));
  const types={};
  for(const t of scored){
    rememberType(t.type);
    const k=typeLabel(t.type);
    const row=types[k]||(types[k]={pcts:[],ids:{}});
    row.pcts.push(t.pct); if(t.id) row.ids[t.id]=1;
  }
  const typeRows=Object.entries(types).map(([k,v])=>({k:k,n:Math.max(1,Object.keys(v.ids).length),m:Math.round(v.pcts.reduce((a,b)=>a+b,0)/v.pcts.length)}))
    .sort((a,b)=>b.n-a.n).slice(0,8);
  return {delta:delta, per:per, mean:m, sd:sd, fc:fc, band:band, types:typeRows, n1:w1.length, n0:w0.length};
}
let TYPE_FULL={};
function rememberType(name){ const k=typeLabel(name); if(name && !TYPE_FULL[k]) TYPE_FULL[k]=name; }
function typeLabel(name){
  const x=String(name||'').toLowerCase();
  if(!x) return 'Task';
  if(x.indexOf('homework')>=0) return 'HW';
  if(x.indexOf('in-class')>=0||x.indexOf('classwork')>=0) return 'IA';
  if(x.indexOf('quiz')>=0) return 'Quiz';
  if(x.indexOf('lab')>=0||x.indexOf('practical')>=0||x.indexOf('experiment')>=0||x.indexOf('project')>=0) return 'Lab';
  if(x.indexOf('test')>=0||x.indexOf('exam')>=0||x.indexOf('cumulative')>=0) return 'Test';
  if(x.indexOf('swim')>=0) return 'Swim';
  return String(name).replace(/[^A-Za-z ]/g,'').trim().split(/\s+/)[0].slice(0,10) || 'Task';
}
function weekBlock(st){
  const w=weekStats(st);
  const sign=v=>(v>=0?'+':'')+v.toFixed(1);
  const push=(arr)=>arr.map(x=>'<span class="wk '+ (x.d>=0?'up':'down') +'">'+esc(x.lab)+' '+sign(x.d)+'</span>').join('');
  const ups=w.per.slice(0,2), downs=w.per.slice(-2).reverse().filter(x=>x.d<0);
  const volTxt=w.sd==null?'—':(w.sd<8?'稳定':(w.sd<18?'有波动':'大起大落'));
  const deltaHtml=w.delta==null
    ? '<div class="big muted">—</div><div class="note">近两周样本不足，等下一次任务后再看变化。</div>'
    : '<div class="big '+(w.delta>=0?'pos':'neg')+'">'+sign(w.delta)+'</div><div class="note">加权分变化（近 7 天 vs 前 7 天，'+(w.n1+w.n0)+' 项任务）</div><div class="chips">'+(ups.length||downs.length?(push(ups)+push(downs)):'<span class="note">两周内没有可比课程</span>')+'</div>';
  const fcHtml=w.fc==null
    ? '<div class="big muted">—</div>'
    : (function(){const lo=Math.max(0,w.fc-w.band), hi=Math.min(100,w.fc+w.band);
        return '<div class="big">'+w.fc+'</div><div class="note">预测 '+st.summary.metric+' 区间 '+lo+'–'+hi+' · σ '+(w.sd==null?'—':w.sd.toFixed(1))+' ('+volTxt+')</div>';})()+ (w.fc<85?'<div class="note">距 A(85) 还差 '+(85-w.fc)+' 分</div>':'<div class="note">已在 A 线以上</div>');
  const bars=w.types.map(t=>'<div class="tbar" title="'+esc(TYPE_FULL[t.k]||t.k)+'"><span class="tk2">'+t.k+'</span><span class="tb"><i style="width:'+t.m+'%"></i></span><span class="tv">'+t.m+'%</span><span class="tn">×'+t.n+'</span></div>').join('');
  return '<div class="week"><div class="wkHead"><h3>本周解读 · This week</h3><span class="note">按任务类型权重（H10/IA15/Q15/PL20/Test40）</span></div>'+
    '<div class="wkGrid"><div class="wkBox"><h4>变化归因 Attribution</h4>'+deltaHtml+'</div>'+
    '<div class="wkBox"><h4>稳定性与预测 Forecast</h4>'+fcHtml+'</div>'+
    '<div class="wkBox"><h4>按任务类型 By task type</h4>'+(bars||'<div class="note">暂无已评分任务</div>')+'</div></div></div>';
}
function missingRecent(st,days){
  const now=Date.now(); let n=0;
  for(const lab of st.labels) for(const t of ((st.sectionTasks||{})[lab]||[])){
    if(t.pct==null&&t.end&&t.end<=now&&t.end>=now-days*864e5) n++;
  }
  return n;
}
function gradebookGap(st){
  const now=Date.now(); let tot=0, nul=0;
  for(const lab of st.labels) for(const t of ((st.sectionTasks||{})[lab]||[])){
    if(!t.end||t.end>now) continue;
    tot++; if(t.pct==null) nul++;
  }
  return tot?nul/tot:0;
}
function canaryHtml(st){
  const gap=gradebookGap(st), miss=missingRecent(st,14);
  if(gap<0.5&&miss<3) return '';
  const msg=gap>=0.5
    ? '成绩册数据不完整：'+Math.round(gap*100)+'% 的已截止任务没有分数（学生可能转班/转学，或成绩未回传）。缺交统计只按近 7 天计，请先核实数据再对外沟通。'
    : '近两周有 '+miss+' 项任务未录分 —— 先确认是“未交”还是“未批”，再对外沟通。';
  return '<div class="canary">数据提示：'+msg+'</div>';
}
// ---- weekly triage queue (teacher view) ----
function triageList(){
  const now=Date.now(), out=[];
  for(const r of D.rows){
    if(r.advisory) continue;
    const all=flatTasks(r).filter(t=>t.end&&t.end<=now);
    const scored=all.filter(t=>t.pct!=null);
    if(scored.length<4) continue;
    const recent=scored.slice(-6);
    const rm=recent.reduce((a,b)=>a+b.pct,0)/recent.length;
    const miss=missingRecent(r,7);
    let weak=null, weakV=null;
    const m=r.summary.metric;
    r.labels.forEach((lab,i)=>{const v=(r.values[m]||[])[i]; if(v!=null&&(weakV==null||v<weakV)){weak=lab;weakV=v;}});
    if(gradebookGap(r)>0.5) continue;
    if(rm>=78&&miss<2) continue;
    const score=(80-rm)+miss*3+(weakV!=null?Math.max(0,75-weakV)*0.4:0);
    out.push({r:r,rm:rm,miss:miss,weak:weak,weakV:weakV,score:score});
  }
  out.sort((a,b)=>b.score-a.score);
  return out.slice(0,6);
}
function queueView(){
  const rows=triageList();
  const body=rows.map((x,i)=>{
    const r=x.r;
    const reason='近 6 次均分 '+Math.round(x.rm)+'% · 近 7 天未录分 '+x.miss+' 项'+(x.weak?' · 最弱 '+x.weak+' '+x.weakV+'%':'');
    const action=x.miss>=3?('先核对 '+x.miss+' 项未录分（未交/未批）'):(x.rm<60?'15 分钟针对性辅导':'一次 check-in + 家长草稿');
    return '<tr data-id="'+r.id+'"><td>'+(i+1)+'</td><td><b>'+esc(dispName(r))+'</b><span class="tcourse">'+esc(r.class)+'</span></td><td>'+esc(reason)+'</td><td class="act">'+esc(action)+'</td></tr>';
  }).join('');
  document.getElementById('card').innerHTML='<h2>本周跟进队列 · Weekly triage</h2>'+
    '<div class="sub">按“可改变性”排序的 6 名学生：参与度尚可、但有明确可补的缺口。每周只跟进这 6 人。</div>'+
    '<table class="queue"><tr><th>#</th><th>Student</th><th>Signal</th><th>Next action</th></tr>'+body+'</table>'+
    '<div class="note">排序 = 近期均分缺口 + 缺交数 + 最弱课程；数据不足 4 项的学生不进入队列。</div>';
  document.querySelectorAll('table.queue tr[data-id]').forEach(tr=>{
    tr.onclick=()=>{const r=D.rows.find(x=>String(x.id)===tr.getAttribute('data-id')); if(r){current=r;renderList();renderCard(r);}};
  });
}
// ---- teaching priorities: course x task type, teacher view ----
function heatData(){
  const now=Date.now(), map={};
  for(const r of D.rows){
    if(r.advisory) continue;
    for(const lab of r.labels){
      for(const t of ((r.sectionTasks||{})[lab]||[])){
        if(!t.end||t.end>now) continue;
        const ty=typeLabel(t.type);
        const key=r.course+'|'+ty;
        const c=map[key]||(map[key]={course:r.course,ty:ty,sum:0,rows:0,miss:0,ids:{},students:{}});
        const st=(c.students[r.id]=c.students[r.id]||{sum:0,n:0});
        c.rows++; st.n++;
        if(t.pct==null){ c.miss++; continue; }
        c.sum+=t.pct; st.sum+=t.pct; if(t.id) c.ids[t.id]=1;
      }
    }
  }
  return Object.values(map).map(c=>{
    const scored=c.rows-c.miss;
    const avg=scored?c.sum/scored:null;
    const students=Object.values(c.students);
    const withWork=students.filter(s=>s.n>=1).length;
    const affected=students.filter(s=>s.n>=2 && s.sum/s.n<70).length;
    return {course:c.course,ty:c.ty,avg:avg,n:Math.max(1,Object.keys(c.ids).length),missRate:c.rows?c.miss/c.rows:0,affected:affected,students:withWork};
  });
}
function heatView(){
  const cells=heatData();
  const courses=[...new Set(cells.map(c=>c.course))];
  const types=[...new Set(cells.map(c=>c.ty))];
  const typeTotals=types.map(t=>({t:t,n:cells.filter(c=>c.ty===t).reduce((a,c)=>a+c.n,0)}))
    .sort((a,b)=>b.n-a.n).map(x=>x.t).slice(0,8);
  const byKey={}; cells.forEach(c=>byKey[c.course+'|'+c.ty]=c);
  const courseAvg=c=>{
    const cs=cells.filter(x=>x.course===c&&x.avg!=null);
    const w=cs.reduce((a,x)=>a+x.n,0);
    return w?cs.reduce((a,x)=>a+x.avg*x.n,0)/w:null;
  };
  const courseStudents=c=>{
    const set={}; D.rows.filter(r=>r.course===c).forEach(r=>set[r.id]=1);
    return Object.keys(set).length;
  };
  courses.sort((a,b)=>(courseAvg(a)??101)-(courseAvg(b)??101));
  const shade=v=>{ if(v==null) return '#fff'; const a=Math.max(0,Math.min(1,(v-50)/40)); return 'rgba(26,127,55,'+(0.08+0.5*a).toFixed(2)+')'; };
  const head='<tr><th style="width:200px">Course 课程</th><th>Students</th><th>Avg</th>'+
    typeTotals.map(t=>'<th title="'+esc(TYPE_FULL[t]||t)+'">'+esc(t)+'</th>').join('')+'</tr>';
  const body=courses.map(c=>{
    const ca=courseAvg(c);
    return '<tr><td class="cn">'+esc(c)+'</td><td class="num">'+courseStudents(c)+'</td><td class="num">'+(ca==null?'—':Math.round(ca)+'%')+'</td>'+
      typeTotals.map(t=>{
        const x=byKey[c+'|'+t];
        if(!x||x.avg==null) return '<td class="na">—</td>';
        return '<td style="background:'+shade(x.avg)+'"><b>'+Math.round(x.avg)+'%</b><span class="zz">n='+x.n+'</span></td>';
      }).join('')+'</tr>';
  }).join('');
  const pri=cells.filter(c=>c.avg!=null&&c.n>=5&&c.affected>=2)
    .map(c=>Object.assign({},c,{impact:(80-c.avg)*c.affected}))
    .sort((a,b)=>b.impact-a.impact).slice(0,6)
    .map((c,i)=>{
      const act=c.avg<70?'整班重讲 + 5 分钟小测':(c.missRate>0.3?'小组辅导 3–5 人，并查未录分':'小组辅导 3–5 人');
      return '<tr><td>'+(i+1)+'</td><td><b>'+esc(c.course)+'</b> · '+esc(c.ty)+'</td><td class="num">'+Math.round(c.avg)+'%</td>'+
        '<td class="num">'+c.n+'</td><td class="num">'+Math.round(c.missRate*100)+'%</td><td class="num">'+c.affected+'/'+c.students+'</td><td>'+act+'</td></tr>';
    }).join('');
  document.getElementById('card').innerHTML='<h2>教学优先 · Teaching priorities</h2>'+
    '<div class="sub">我的课程 × 任务类型（本学期已截止、且有分数的任务）。颜色越深均分越高；n = 去重任务数；按整门课均分从低到高排列。</div>'+
    '<table class="heat">'+head+body+'</table>'+
    '<div class="note"><b>先做这 6 件（影响 = 低于 70% 的学生数 × 差距）：</b></div>'+
    '<table class="heat pri"><tr><th>#</th><th>课程 · 类型</th><th>均分</th><th>任务数</th><th>未录分</th><th>低于70%（人数）</th><th>建议动作</th></tr>'+(pri||'<tr><td colspan="7">数据不足</td></tr>')+'</table>'+
    '<div class="note">用法：挑第 1 行，打开对应课程的学生卡看 Missing/Bottom，再决定重讲还是个别辅导；这张表只用于排优先级，不用于评价个人。</div>';
}
// ---- communication coverage (C1/C2) ----
function commsData(){
  const now=Date.now(), out=[];
  for(const r of D.rows){
    const es=(r.entries||[]);
    let lastPos=null,lastNeg=null,pos=0,neg=0;
    for(const e of es){
      if(e.inf){ neg++; if(!lastNeg||e.t>lastNeg) lastNeg=e.t; }
      else if(e.p>0){ pos++; if(!lastPos||e.t>lastPos) lastPos=e.t; }
    }
    out.push({r:r,pos:pos,neg:neg,lastPos:lastPos,lastNeg:lastNeg,days:lastPos?Math.floor((now-lastPos)/864e5):null});
  }
  return out;
}
function commsView(){
  const rows=commsData().sort((a,b)=>(b.days==null?9999:b.days)-(a.days==null?9999:a.days));
  const total=rows.length, praised=rows.filter(x=>x.days!=null&&x.days<=21).length;
  const quiet=rows.filter(x=>x.days==null||x.days>21).length;
  const body=rows.slice(0,25).map(x=>{
    const cls=x.days==null?'never':(x.days>21?'over':'');
    const days=x.days==null?'从未':x.days+' 天前';
    return '<tr class="'+cls+'" data-id="'+x.r.id+'"><td>'+esc(dispName(x.r))+'<span class="tcourse">'+esc(x.r.class)+'</span></td>'+
      '<td class="num">'+days+'</td><td class="num">'+x.pos+'</td><td class="num">'+x.neg+'</td>'+
      '<td class="num">'+(x.lastNeg?fmtDate(x.lastNeg):'—')+'</td>'+
      '<td><button class="btn mini dbtn" data-id="'+x.r.id+'">草稿</button></td></tr>';
  }).join('');
  document.getElementById('card').innerHTML='<h2>沟通覆盖 · Communication coverage</h2>'+
    '<div class="sub">近 21 天内有正向反馈：<b>'+praised+'/'+total+'</b>；超过 21 天没有正向记录：<b>'+quiet+'</b> 人。</div>'+
    '<table class="comms"><tr><th>Student</th><th>最近正向</th><th>正向</th><th>违规</th><th>最近违规</th><th></th></tr>'+body+'</table>'+
    '<div class="note">口径：只统计 Student Log（金钥匙/违规）；门户站内消息的阅读回执当前账号无数据，故不展示。' +
      '「草稿」会生成中英文家长信息，仍需你自己发送。</div>';
  document.querySelectorAll('table.comms .dbtn').forEach(bt=>{
    bt.onclick=ev=>{ev.stopPropagation();const r=D.rows.find(x=>String(x.id)===bt.getAttribute('data-id'));
      if(r) openDraft(r);};
  });
  document.querySelectorAll('table.comms tr[data-id]').forEach(tr=>{
    tr.onclick=()=>{const r=D.rows.find(x=>String(x.id)===tr.getAttribute('data-id'));if(r){current=r;renderList();renderCard(r);}};
  });
}
// ---- C3: printable student self-check ----
function selfCheck(st){
  const m=st.summary.metric;
  const pairs=st.labels.map((l,i)=>({l:l,v:(st.values[m]||[])[i]})).filter(x=>x.v!=null).sort((a,b)=>b.v-a.v);
  const strong=pairs[0], weak=pairs[pairs.length-1];
  const nm=dispName(st);
  const bullets=(pairs.length?[]:[]).concat(
    strong?['<li>保持 '+esc(strong.l)+'（'+strong.v+'%）作为信心锚点。</li>']:[],
    weak&&strong&&weak.l!==strong.l?['<li>每周针对 '+esc(weak.l)+' 做 15 分钟提取练习。</li>']:[],
    ['<li>本周缺交任务：<span class="line" style="display:inline-block;width:120px"></span> 项（自查后填写）。</li>']);
  return '<h2>学生自评页 · Weekly self-check</h2><div class="sub">'+esc(nm)+' · '+esc(st.class)+' · 打印后由学生手写完成</div>'+
    '<h3>1. 我这周做到了什么</h3><ul style="font-size:11.5px;line-height:1.7">'+bullets.join('')+'</ul>'+
    '<h3>2. 我给自己打分（1 = 需努力，5 = 很好）</h3>'+
    '<table><tr><th>项目</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th></tr>'+
    ['课堂参与','作业完成','复习与订正','提问与求助'].map(x=>'<tr><td>'+x+'</td>'+'<td></td>'.repeat(5)+'</tr>').join('')+'</table>'+
    '<h3>3. 下周我要做的一件事</h3><div class="line"></div><div class="line"></div>'+
    '<h3>4. 需要老师/家长怎么帮我</h3><div class="line"></div><div class="line"></div>'+
    '<div class="row"><button class="btn mini" id="selfPrint">打印 Print</button><button class="btn mini" id="selfClose">关闭 Close</button></div>';
}
function showSelf(st){
  const p=document.getElementById('selfPanel');
  p.innerHTML=selfCheck(st); p.style.display='block';
  document.getElementById('selfClose').onclick=()=>{p.style.display='none';document.body.classList.remove('selfprint');};
  document.getElementById('selfPrint').onclick=()=>{document.body.classList.add('selfprint');window.print();setTimeout(()=>document.body.classList.remove('selfprint'),800);};
}
// ---- one-click parent draft ----
function parentDraft(st){
  const nm=st.name.replace(/[（(].*?[）)]/g,'').replace(/\s+/g,' ').trim();
  const m=st.summary.metric;
  const pairs=st.labels.map((l,i)=>({l:l,v:(st.values[m]||[])[i]})).filter(x=>x.v!=null).sort((a,b)=>b.v-a.v);
  const strong=pairs[0], weak=pairs[pairs.length-1];
  const miss=missingRecent(st,14);
  const w=weekStats(st);
  const out=[];
  out.push(['Dear Parent/Guardian of '+nm+',', '家长您好（'+nm+' 的家长）：']);
  let en='A short update on the last two weeks. ', zh='向您反馈最近两周的情况。';
  if(strong){ en+='The strongest area right now is '+strong.l+' at '+strong.v+'% of the current '+m+' measure. '; zh+='目前最强的是 '+strong.l+'（'+strong.v+'%）。'; }
  if(weak&&strong&&weak.l!==strong.l){ en+='The area that needs the most support is '+weak.l+' at '+weak.v+'%. '; zh+='最需要支持的是 '+weak.l+'（'+weak.v+'%）。'; }
  if(miss){ en+='There are '+miss+' recent task(s) with no mark recorded yet — please check with your child whether they were submitted. '; zh+='近两周还有 '+miss+' 项任务尚未录分，请和孩子确认是否已提交。'; }
  if(w.delta!=null){ en+='Across the two weeks the weighted score moved '+(w.delta>=0?'+':'')+w.delta.toFixed(1)+' points. '; zh+='两周加权分变化 '+(w.delta>=0?'+':'')+w.delta.toFixed(1)+' 分。'; }
  out.push([en.trim(), zh]);
  out.push(['What I will do next: one short targeted practice on the weakest area each week, and a check-in after the next assessment.',
            '接下来我会：每周针对最弱板块做一次短时练习，并在下次测评后与您同步。']);
  out.push(['What would help at home: 15 minutes of focused review twice a week, and a quiet check that homework is submitted on time.',
            '家庭配合：每周两次、每次 15 分钟专注复习；督促作业按时提交。']);
  out.push(['Happy to talk at any time.\n\nBest regards,\n'+D.teacher,
            '随时联系我，谢谢！\n\n此致敬礼\n'+D.teacher]);
  return out.map(p=>p[0]+'\n'+p[1]).join('\n\n');
}
let draftStudent=null;
function openDraft(st,text){
  draftStudent=st;
  document.getElementById('draftText').value = text || parentDraft(st);
  const to=(st.parents||[]).filter(Boolean);
  const el=document.getElementById('draftTo');
  el.textContent = to.length ? ('To（IntSchool 家长邮箱）：'+to.join('; ')) : '未找到家长邮箱：请在 IntSchool → Student List → Student Detail → Parent 中确认。';
  el.style.color = to.length ? '#57606a' : '#c00000';
  document.getElementById('draftPanel').style.display='block';
}
function renderCard(st){
  const cov=m=>st.values[m].filter(v=>v!=null).length;
  if(activeMetrics.every(m=>cov(m)===0)){let best=null,bestN=0;D.metrics.forEach(m=>{const n=cov(m);if(n>bestN){bestN=n;best=m}});if(best){activeMetrics=[best];mBox.querySelectorAll('input').forEach(cb=>{cb.checked=(cb.value===best)})}}
  const head=activeMetrics.map((m,mi)=>'<span data-m="'+m+'" style="color:'+COLORS[mi%COLORS.length]+'">● '+m+'</span>').join(' ');
  const rowsHtml=st.labels.map((a,i)=>{
    const cells=activeMetrics.map(m=>{const v=st.values[m][i]; if(v==null)return '<td style="color:#8b949e">N/A</td>';
      const avg=match(st,st.ck,a,m); const pr=st.pctRank[m][i];
      if(parentView) return '<td>'+v+'%</td>';
      return '<td>'+v+'%'+(avg!=null?' <span class="avgCol" style="color:#8b949e">avg '+avg+'%</span>':'')+(pr!=null?' <span class="pctCol" style="color:#1f4e79">P'+pr+'</span>':'')+'</td>'}).join('');
    const lv=(st.levels||[])[i];
    const showLv=lv&&!new RegExp('(^|[ .-])'+lv.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$','i').test(a);
    return '<tr><td>'+esc(a)+(showLv?' <span class="lv">'+esc(lv)+'</span>':'')+'</td>'+cells+'</tr>';}).join('');
  const opts=(vals,sel)=>vals.map(v=>'<option value="'+v+'"'+(v===sel?' selected':'')+'>'+v+'</option>').join('');
  document.getElementById('card').innerHTML=`
    <h2><span class="pname">${dispName(st)}</span> ${st.advisory?'<span class="pill">Advisory</span>':''}
      ${st.flags.alert?'<span class="badge alert">3-indicator alert</span>':''}
      ${st.flags.celebrate?'<span class="badge cel">celebrate</span>':''}</h2>
    <div class="sub">${st.class}${st.course?' · '+st.course:''} · ${st.labels.length} sections${parentView?' · 家长版（不显示同伴对比）':''}</div>
    ${canaryHtml(st)}
    <div class="card">
      <div id="radarBox">${radar(st)}<div class="legend">${head}${activeMetrics.length===1&&!parentView?' <span><span class="dot" style="background:#9aa7b4"></span>class avg</span>':''} <span style="color:#8b949e">· 悬停科目名看该科逐项成绩</span></div></div>
      <div>
        <table><tr><th>Section</th>${activeMetrics.map(m=>'<th>'+m+'</th>').join('')}</tr>${rowsHtml}</table>
        <div class="note">${parentView?'<b>家长版：</b>只显示学生本人的分数与目标，不显示同伴对比。<br>每一项都可点开看任务证据。':'<b>分层：</b>G6–8 HF &gt; ECP &gt; CPA &gt; CP；G9 A1 &gt; A2 &gt; Main &gt; Basic；G10–12 AP &gt; ECP &gt; CP（英语 AP/ESL/EAL）。<br>初中学段按学科+分层出轴；高中按课程名出轴（同名课跨年级不等价）。<br>每项显示：分数 · 班级均分（avg）· 同班百分位（P）。'}</div>
      </div>
    </div>
    ${weekBlock(st)}
    ${taskBlock(st)}
    <div class="logbox">
      <h3>Student Log 趋势（金钥匙 vs 违规）</h3>
      <div class="controls">粒度 <select id="gran" onchange="renderCard(current)">${opts(['week','day','month','year'],'week')}</select>
        窗口 <select id="win" onchange="renderCard(current)">${opts(['15','30','60','all'],'all')}</select>
        <span class="legend"><span><span class="dot" style="background:#1a7f37"></span>Golden Key</span><span><span class="dot" style="background:#c00000"></span>Infraction</span></span>
      </div>
      <div id="trendbox">${trendChart(st)}</div>
    </div>
    <div class="summary"><h3>Overall strengths & next steps · 总评与建议</h3><p>${st.summary.en}</p><p class="zh">${st.summary.zh}</p>
      <div class="src">数据来源：IntSchool 成绩册（Student Detail → Grade Book）、Student Log、Attendance；抓取时间 ${D.generated}；本页由本地脚本生成，未上传服务器。口径：Q1P/Q1E/Q1F/Q2P/Q2F（初中）、S1P/S1M（高中）；班级均分优先取 Teaching → Gradebook。</div>
    </div>
    <details class="limits"><summary>方法与边界 · Method &amp; limits</summary>
      <div>数据来自 IntSchool 只读接口（成绩册 / Student Log / 出勤 / 任务说明），抓取时间 ${D.generated}；不上传任何服务器。
      缺分 ≠ 缺交；预测是区间，不是承诺；班级均分与百分位需 ≥5 名同伴；本页不排名、不公开比较；家长信息只生成草稿，发送键始终在老师手里。</div>
    </details>
    <div class="profile">
      <h3>Student Profile & Learning Plan · 学生画像与学习计划</h3>
      <div class="chips">${st.profileData.facts.map(x=>'<span class="chip">'+x+'</span>').join('')}</div>
      <ul>${st.profileData.insights.map(x=>'<li>'+x+'</li>').join('')}</ul>
      <p class="plan">${st.profileData.plan}</p>
      <p class="zh">${st.profileData.zh}</p>
    </div>`;
  document.querySelectorAll('#radarBox .legend span[data-m]').forEach(el=>{
    el.onmouseenter=ev=>{const m=el.dataset.m; const rows=st.labels.map((a,i)=>{const v=st.values[m][i];return '<tr><td>'+a+'</td><td>'+(v==null?'—':v+'%')+'</td><td>'+(match(st,st.class,a,m)??'—')+'</td></tr>'}).join('');
      showTip('<b>'+m+' · all sections (score / class avg)</b><table><tr><th>Section</th><th>Score</th><th>Avg</th></tr>'+rows+'</table>');};
    el.onmousemove=moveTip; el.onmouseleave=hideTip;
  });
  document.querySelectorAll('#radarBox g.axis').forEach(g=>{
    g.onmouseenter=ev=>showCourse(st,Number(g.dataset.i),ev);
    g.onmousemove=ev=>{const p=document.getElementById('hoverPanel');if(p.style.display!=='block')return;
      let x=ev.clientX+18,y=ev.clientY-30;const w=p.offsetWidth,h=p.offsetHeight;
      if(x+w>window.innerWidth-8)x=ev.clientX-w-18; if(y+h>window.innerHeight-8)y=window.innerHeight-h-8;
      p.style.left=Math.max(8,x)+'px';p.style.top=Math.max(8,y)+'px';};
    g.onmouseleave=()=>{scheduleHide();};
  });
  document.querySelectorAll('#trendbox rect.bar').forEach(el=>{
    el.onmouseenter=ev=>{const r=JSON.parse(el.getAttribute('data-json'));const pos=r.items.filter(x=>!x.inf&&x.p>0), neg=r.items.filter(x=>x.inf);
      const lines=['<b>'+r.k+'</b>']; if(pos.length) lines.push('Golden Key ('+r.gk+'): '+pos.slice(0,3).map(x=>x.ty+(x.de?' — '+x.de:'')).join('; '));
      if(neg.length) lines.push('Infraction ('+r.inf+'): '+neg.slice(0,3).map(x=>x.ty+(x.de?' — '+x.de:'')).join('; '));
      showTip(lines.join('<br>'));}; el.onmousemove=moveTip; el.onmouseleave=hideTip;
  });
  setupActions(st);
}
function setupActions(st){
  document.getElementById('printBtn').onclick=()=>window.print();
  document.getElementById('queueBtn').onclick=()=>queueView();
  document.getElementById('heatBtn').onclick=()=>heatView();
  document.getElementById('commsBtn').onclick=()=>commsView();
  document.getElementById('parentBtn').onclick=()=>{parentView=!parentView;document.body.classList.toggle('parent',parentView);renderCard(st);};
  const dp=document.getElementById('draftPanel');
  document.getElementById('draftBtn').onclick=()=>openDraft(st);
  const selfBtn=document.getElementById('selfBtn'); if(selfBtn) selfBtn.onclick=()=>showSelf(st);
  document.getElementById('draftClose').onclick=()=>{dp.style.display='none';};
  document.getElementById('draftCopy').onclick=async()=>{const t=document.getElementById('draftText');await navigator.clipboard.writeText(t.value);};
  document.getElementById('draftMail').onclick=async()=>{
    const st2=draftStudent||st, to=(st2.parents||[]).filter(Boolean);
    const status=document.getElementById('draftStatus');
    if(!to.length){alert('没有找到家长邮箱。请在 IntSchool → Student List → Student Detail → Parent 中确认。');return;}
    const subject='Student update · '+st2.name+' · '+st2.class;
    const body=document.getElementById('draftText').value;
    if(location.protocol.indexOf('http')===0){
      status.textContent='正在 Outlook 里创建草稿…';
      try{
        const r=await fetch('/outlook-draft',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({to:to,subject:subject,body:body})});
        const j=await r.json();
        status.textContent = j.ok ? ('已在 Outlook 打开草稿（'+to.length+' 位收件人）') : ('创建失败：'+(j.error||'未知错误'));
        status.style.color = j.ok ? '#1a7f37' : '#c00000';
      }catch(e){ status.textContent='创建失败：'+e.message; status.style.color='#c00000'; }
      return;
    }
    // file:// mode: no local bridge, download an Outlook-ready .eml
    const eml=['To: '+to.join('; '),'Subject: '+subject,'MIME-Version: 1.0','Content-Type: text/plain; charset=utf-8','',''].join('\r\n')+body;
    const a=document.createElement('a');
    a.href=URL.createObjectURL(new Blob([eml],{type:'message/rfc822'}));
    a.download='Radar_draft_'+st2.class+'.eml'; a.click();
    status.textContent='已下载 .eml：双击用 Outlook 打开。用 3_start_live_report.command 打开本页可一键创建草稿。';
    status.style.color='#b26a00';
  };
  document.getElementById('privacyBtn').onclick=()=>{privacy=!privacy;document.body.classList.toggle('privacy',privacy);if(current)renderCard(current);};
  const shareBtn=document.getElementById('shareBtn'), panel=document.getElementById('sharePanel');
  shareBtn.onclick=async()=>{const text=(privacy?'Learner · '+st.class:st.name)+' · '+st.summary.metric+'\n'+st.summary.en;
    if(navigator.share){try{await navigator.share({title:'Radar Report Card',text,url:location.href});return}catch(e){}}
    panel.style.display=panel.style.display==='block'?'none':'block';};
  document.getElementById('copyBtn').onclick=async()=>{const text=(privacy?'Learner · '+st.class:st.name)+' · '+st.summary.metric+'\n'+st.summary.en; await navigator.clipboard.writeText(text);panel.style.display='none';alert('摘要已复制，可粘贴到企业微信/微信。')};
  document.getElementById('copyLinkBtn').onclick=async()=>{await navigator.clipboard.writeText(location.href);panel.style.display='none';alert('链接已复制。')};
  document.getElementById('emailBtn').onclick=()=>{const text=(privacy?'Learner · '+st.class:st.name)+' · '+st.summary.metric+'\n'+st.summary.en; location.href='mailto:?subject='+encodeURIComponent('Radar Report Card')+'&body='+encodeURIComponent(text);};

}
document.getElementById('q').addEventListener('input',()=>renderList());
clsSel.addEventListener('change',()=>{current=null;renderList()});
renderList();
// The report refreshes its data automatically whenever it is opened in live mode.
(async function autoRefresh(){
  if(!location.protocol.startsWith('http')) return;
  const last=Number(sessionStorage.getItem('radar_last_refresh')||0);
  if(Date.now()-last < 60000) return;
  sessionStorage.setItem('radar_last_refresh', String(Date.now()));
  const mask=document.createElement('div');
  mask.style.cssText='position:fixed;inset:0;background:rgba(255,255,255,.92);z-index:999;display:flex;align-items:center;justify-content:center;flex-direction:column;font-size:16px;color:#1f4e79;gap:8px';
  mask.innerHTML='<b>正在刷新数据…</b><span style="font-size:12px;color:#57606a">重新抓取成绩册 / Student Log / 出勤，约需 1–2 分钟</span>';
  document.body.appendChild(mask);
  try{
    const r=await fetch('/refresh',{method:'POST'});
    if(r.ok){ sessionStorage.setItem('radar_last_refresh', String(Date.now())); location.reload(); return; }
  }catch(e){}
  mask.remove();
})();
</script></body></html>"""

html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False)).replace("__COLORS__", json.dumps(COLORS))
html = html.replace("__GENERATED__", GENERATED).replace("__NSTUD__", str(NSTUD)).replace("__TEACHER__", TEACHER)
out = os.path.join(OUTDIR, f"Radar_{TEACHER.replace(' ', '_')}.html")
open(out, "w", encoding="utf-8").write(html)
print("saved", out, "students:", len(students))
