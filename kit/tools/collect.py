#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radar Kit collector: reads a teacher's token, auto-detects their classes + advisory,
pulls gradebook sections / Student Log / attendance, and writes data/phase2.json.

Works for any teacher account; permissions are enforced by IntSchool.
"""
import json, os, re, sys, time, base64, urllib.request, urllib.error, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(KIT, "data")
CONFIG_PATH = os.path.join(KIT, "config.json")
BASE = "https://teacher.intschool.cn/api"

GROUP = {
    "MS ELA 英语": "English", "MS CLA 语文": "Chinese", "MS Mathematics 数学": "Mathematics",
    "MS Science 科学": "Science", "MS Humanities 人文": "Humanities",
    "MS Arts and Design 艺术与设计": "Arts", "MS Physical Education 体育": "PE",
    "SS English": "English", "SS Chinese": "Chinese", "SS Mathematics": "Mathematics",
    "SS Science": "Science", "SS Humanities": "Humanities", "SS Arts and Design": "Arts",
    "SS Health and Wellness": "PE",
}
SCI_ORDER = ["Biology", "Physics", "Chemistry", "General Science"]
FLG_MS = ["HF", "ECP", "CPA", "CP"]
FLG_G9 = ["A1", "A2", "Main", "Basic"]
FLG_HS = ["AP", "ECP", "CP", "ESL", "EAL"]

def load_config():
    cfg = {"advisory_keywords": ["Advisory"], "exclude_keywords": ["Meeting", "Study Hall", "Table Table", "Table Tennis", "Club", "CCA", "Conference", "Life Block", "Department"], "include_course_ids": [], "exclude_course_ids": []}
    if os.path.exists(CONFIG_PATH):
        try:
            cfg.update(json.load(open(CONFIG_PATH, encoding="utf-8")))
        except Exception as e:
            print("config.json 读取失败，使用默认值：", e)
    return cfg

def read_token():
    p = os.path.join(KIT, "token.txt")
    if os.path.exists(p):
        t = open(p, encoding="utf-8").read().strip()
        if t:
            return t
    print("未找到 token.txt。请先双击 1_get_token.command，或手动粘贴 token。")
    t = input("Token: ").strip()
    if not t:
        sys.exit(1)
    open(p, "w", encoding="utf-8").write(t)
    os.chmod(p, 0o600)
    return t

def school_from_token(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        obj = json.loads(base64.urlsafe_b64decode(payload))
        ids = obj.get("schoolIds") or []
        return ids[0] if ids else 2
    except Exception:
        return 2

TOKEN = read_token()
SCHOOL = school_from_token(TOKEN)
H = {"X-Token": TOKEN, "X-SchoolId": str(SCHOOL), "X-Locale": "en", "Accept": "application/json"}

def get(path, timeout=20):
    req = urllib.request.Request(BASE + path, headers=H)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

# ---------- labels ----------
def clean_course(course):
    c = re.sub(r"^G\d+[A-Za-z]?\s+", "", course or "")
    c = re.sub(r"\s*\(\d+\)\s*$", "", c)
    c = re.sub(r"\.Y\s*$", "", c).strip()
    if " - " in c:
        c = c.split(" - ")[-1].strip()
    return c or (course or "Other")

def grade_of(cls):
    m = re.match(r"G(\d+)", str(cls or ""))
    return int(m.group(1)) if m else 0

def flg_of(course, grade, subject=""):
    """Level code used by each grade band.

    G6-8  HF > ECP > CPA > CP      (middle-school banding)
    G9    A1 > A2 > Main > Basic   (only G9 uses this ladder)
    G10-12 AP > ECP > CP, and English also AP / ESL / EAL
    """
    course = str(course or "")
    if grade and grade <= 8:
        codes = FLG_MS
    elif grade == 9:
        codes = FLG_G9
    else:
        codes = FLG_HS
    for f in codes:
        if f == "ESL":
            if re.search(r"second language|\bESL\b", course, re.I): return "ESL"
        elif f == "EAL":
            if re.search(r"\bEAL\b", course, re.I): return "EAL"
        elif f == "AP":
            if re.search(r"\bAP\b|advanced placement", course, re.I): return "AP"
        elif f in ("A1", "A2"):
            if re.search(rf"[ \-]{f}\b", course): return f
        elif f == "Main":
            if "Main" in course: return "Main"
        elif f == "Basic":
            if "Basic" in course: return "Basic"
        elif f" {f}" in course or f"-{f}" in course or course.rstrip().endswith(f) or f".{f}" in course:
            return f
    return ""

def guess_group(subject):
    t = (subject or "").lower()
    for key, grp in [("english", "English"), ("ela", "English"), ("chinese", "Chinese"), ("语文", "Chinese"),
                     ("math", "Mathematics"), ("science", "Science"), ("biology", "Science"), ("physics", "Science"),
                     ("chemistry", "Science"), ("humanities", "Humanities"), ("history", "Humanities"),
                     ("geography", "Humanities"), ("economic", "Humanities"), ("art", "Arts"), ("music", "Arts"),
                     ("drama", "Arts"), ("design", "Arts"), ("physical", "PE"), ("pe", "PE")]:
        if key in t:
            return grp
    return None

def clean_course_hs(course):
    """High-school axis name: the course itself, minus section number / year marker.

    "AP Calculus AB.Y (2)" -> "AP Calculus AB"; "Chemistry IG-0620.Y (3)" ->
    "Chemistry IG-0620". A course can be taken by several grades (AP Precalculus
    in G10 and G11), so the course name is what identifies the axis.
    """
    c = re.sub(r"\s*\(\d+\)\s*$", "", str(course or "")).strip()
    c = re.sub(r"\.(Y|S)\s*$", "", c).strip()
    c = re.sub(r"\s+", " ", c)
    return c or str(course or "Other")

def section_label(subject, course, grade):
    g = GROUP.get((subject or "").strip()) or guess_group(subject)
    if grade >= 9:
        # High school: one axis per course, not per subject category.
        return clean_course_hs(course), (g or "Other"), flg_of(course, grade, subject)
    if g is None:
        return clean_course(course), "Other", ""
    if g == "Science":
        base = "Science"
        for key in SCI_ORDER:
            if key.lower() in course.lower():
                base = key
                break
        f = flg_of(course, grade)
        return (f"{base} {f}" if f else base), "Science", f
    if g in ("Arts", "Humanities") and grade <= 8:
        return clean_course(course), g, ""
    if g in ("English", "Mathematics"):
        f = flg_of(course, grade)
        return (f"{g} {f}".strip() if f else g), g, f
    if g == "Chinese":
        return "Chinese", g, ""
    if g == "PE":
        return "PE", g, ""
    return g, g, flg_of(course, grade)

def clean_advisory(course):
    """'G10 Advisory - Nora Shi' -> 'Nora Shi'"""
    c = str(course or "").strip()
    if " - " in c:
        c = c.split(" - ")[-1].strip()
    c = re.sub(r"^G\d+[A-Za-z]?\s+", "", c)
    c = re.sub(r"\bAdvisory\b", "", c, flags=re.I).strip(" -·")
    return c or str(course or "")

def keep_section(subject, course):
    if "Skills" in course and GROUP.get((subject or "").strip()) == "English":
        return False
    return True

# ---------- discovery ----------
def discover():
    cfg = load_config()
    teacher = {}
    try:
        teacher = get("/login/userInfo")
    except Exception:
        pass
    year = get("/semester/currentSchoolYear")
    courses = get("/dropDown/teach/courses")
    adv_kw = [k.lower() for k in cfg.get("advisory_keywords", ["Advisory"])]
    ex_kw = [k.lower() for k in cfg.get("exclude_keywords", [])]
    include = set(cfg.get("include_course_ids") or [])
    exclude = set(cfg.get("exclude_course_ids") or [])
    advisory_students = {}
    teaching = []
    for c in courses:
        cid, name = c["key"], c.get("value") or str(c["key"])
        low = name.lower()
        if cid in exclude:
            continue
        is_adv = any(k in low for k in adv_kw)
        is_ex = any(k in low for k in ex_kw)
        if is_adv:
            try:
                rost = get(f"/course/students?courseId={cid}&pageCurrent=1&pageSize=500")
                for r in rost.get("items", []):
                    advisory_students[r["studentId"]] = r
            except Exception:
                pass
            continue
        if is_ex and cid not in include:
            continue
        try:
            rost = get(f"/course/students?courseId={cid}&pageCurrent=1&pageSize=500")
        except Exception:
            continue
        items = rost.get("items", [])
        if items:
            teaching.append({"courseId": cid, "name": name, "students": items})
    return teacher, year, teaching, advisory_students

def main():
    os.makedirs(DATA, exist_ok=True)
    teacher, year, teaching, advisory = discover()
    teacher_name = teacher.get("name") or teacher.get("enName") or "Teacher"
    year_id = year.get("schoolYearId")
    year_start = year.get("startTime") or (dt.datetime.now().timestamp() * 1000 - 120 * 86400000)
    end = int(dt.datetime.now().timestamp() * 1000)
    print(f"账号：{teacher_name} · 学年 {year.get('name')} · 教学课程 {len(teaching)} 门 · 导师组 {len(advisory)} 人")

    scope = {}
    for c in teaching:
        for r in c["students"]:
            rec = scope.setdefault(r["studentId"], {
                "studentId": r["studentId"], "name": r.get("name"), "className": r.get("className", ""),
                "parents": r.get("parentsEmail") or ([r["parentEmail"]] if r.get("parentEmail") else []),
                "courses": [], "advisory": False})
            rec["courses"].append(c["courseId"])
    for sid, r in advisory.items():
        rec = scope.setdefault(sid, {"studentId": sid, "name": r.get("name"), "className": r.get("className", ""),
                                     "parents": r.get("parentsEmail") or ([r["parentEmail"]] if r.get("parentEmail") else []),
                                     "courses": [], "advisory": False})
        rec["advisory"] = True

    # class means for the teacher's own courses
    means = {}
    for c in teaching:
        try:
            gb = get(f"/grade-book/grade-book?courseId={c['courseId']}")
            colname = {}
            for it in gb.get("gradeItems", []):
                col = it.get("columnId") or ""
                if str(col).startswith("cus_"):
                    colname[col] = it.get("name")
            m = {}
            for k, v in (gb.get("meanMap") or {}).items():
                if k in colname and v is not None:
                    m[colname[k]] = round(v, 1)
            means[c["name"]] = {"courseId": c["courseId"], "means": m}
        except Exception as e:
            print("课程均分失败", c["name"], e)

    def one(rec):
        sid = rec["studentId"]; grade = grade_of(rec.get("className"))
        out = {"sections": [], "diary": {"entries": []}, "attendance": {}, "tasks": {}, "info": {}, "lifeBlock": []}
        try:
            gb = get(f"/grade-book/grade-book/?studentId={sid}&schoolYearId={year_id}")
            names = {cc["customColumnId"]: cc["customColumnName"] for cc in gb.get("customColumns", [])}
            by = {}
            for it in gb.get("gradeBookItems", []):
                course = it.get("courseName") or ""
                subject = it.get("subject")
                if re.search(r"advisory", course, re.I):
                    out["info"]["advisory"] = clean_advisory(course)
                if it.get("inClass") is False:   # subject category marked "Out of class"
                    continue
                if not keep_section(subject, course):
                    continue
                label, group, flg = section_label(subject, course, grade)
                if group == "Other" and re.search(r"conference|life block|advisory|study hall|club|cca|meeting|department|assembly|tutorial", course + " " + (subject or ""), re.I):
                    continue
                scores = {}
                for cid, v in (it.get("customColumnScores") or {}).items():
                    if not v or v.get("score") is None or v["score"] < 0:
                        continue
                    scores[names.get(int(cid), str(cid))] = {"pct": v["score"], "level": v.get("level") or ""}
                # task-level marks for the hover chart and the top/bottom/missing table
                sec_tasks = []
                for t in (it.get("taskScores") or []):
                    top = t.get("topScore") or 0; sc = t.get("score")
                    if top <= 0: continue
                    sec_tasks.append({
                        "id": t.get("taskId"),
                        "name": (t.get("taskName") or "")[:120],
                        "abbr": t.get("abbr") or "",
                        "type": t.get("taskTypeName") or "",
                        "color": t.get("color") or "",
                        "end": t.get("endDate") or 0,
                        "top": top,
                        "score": sc,
                        "pct": round(100 * sc / top, 1) if sc is not None else None,
                    })
                    out["tasks"]["total"] = out["tasks"].get("total", 0) + 1
                    if sc is None: out["tasks"]["missing"] = out["tasks"].get("missing", 0) + 1
                    else:
                        out["tasks"]["graded"] = out["tasks"].get("graded", 0) + 1
                        abbr = (t.get("abbr") or "")
                        if abbr in ("H", "IA", "PL") and abs(sc - top / 2) < 0.001:
                            out["tasks"]["nosub"] = out["tasks"].get("nosub", 0) + 1
                if scores:
                    sec_tasks.sort(key=lambda x: x["end"] or 0)
                    out["sections"].append({"label": label, "group": group, "course": course,
                                            "flg": flg, "scores": scores,
                                            "tasks": sec_tasks})
        except Exception as e:
            out["sections_error"] = str(e)[:80]
        try:
            entries = []
            for page in range(1, 5):
                j = get(f"/diary/by-student?studentId={sid}&pageCurrent={page}&pageSize=100")
                pl = j.get("diaryEntryItemResponsePagedList") or {}
                items = pl.get("items") or []
                entries += items
                if len(items) < 100:
                    break
            term = [e for e in entries if (e.get("createTime") or 0) >= year_start]
            out["diary"] = {"entries": [{"date": e.get("createTime"), "points": e.get("points") or 0,
                                         "primaryType": e.get("primaryType"), "primaryTypeEn": e.get("primaryTypeEn"),
                                         "diaryEntryType": e.get("diaryEntryType"), "diaryEntryTypeEn": e.get("diaryEntryTypeEn"),
                                         "description": e.get("description"), "creator": e.get("creator"),
                                         "notice": e.get("notice")} for e in term[:300]],
                            "positives": sum(1 for e in term if (e.get("points") or 0) > 0 and "infraction" not in ((e.get("primaryTypeEn") or "") + (e.get("primaryType") or "")).lower()),
                            "concerns": sum(1 for e in term if "infraction" in ((e.get("primaryTypeEn") or "") + (e.get("primaryType") or "")).lower())}
        except Exception:
            pass
        try:
            att = get(f"/attendance/statistic/student/{year_id}?studentId={sid}&start={int(year_start)}&end={end}", timeout=8)
            c = {"present": 0, "late": 0, "absent": 0, "excused": 0, "noRecord": 0, "holiday": 0}
            for d in att.get("dailyStatistics", []):
                for k in ("am", "pm"):
                    v = d.get(k)
                    if not v: continue
                    if v in ("intime", "online"): c["present"] += 1
                    elif v in ("late", "excusedLate"): c["late"] += 1
                    elif v in ("absent", "unexcusedAbsent", "others"): c["absent"] += 1
                    elif v in ("illness", "personal"): c["excused"] += 1
                    elif v == "noRecords": c["noRecord"] += 1
                    else: c["holiday"] += 1
            den = c["present"] + c["late"] + c["absent"] + c["excused"]
            out["attendance"] = {**c, "recorded": den, "rate": round((c["present"] + c["late"]) / den * 100, 1) if den else None}
        except Exception:
            out["attendance"] = {"recorded": 0, "rate": None}
        try:
            d = get(f"/student/detail?studentId={sid}")
            # houseGroupName is the advisory group (tutor group), houseName is the house band
            out["info"] = {"enterDate": d.get("enterDate"), "boarding": d.get("boarding"),
                           "dormitory": d.get("dormitoryName") or "",
                           "advisory": d.get("houseGroupName") or out["info"].get("advisory") or "",
                           "house": d.get("houseName") or "",
                           "gender": d.get("gender") or "",
                           "birthday": d.get("birthday") or 0,
                           "bus": d.get("schoolBus")}
        except Exception:
            out["info"].setdefault("advisory", "")
        try:
            ci = get(f"/student/course-info?studentId={sid}&schoolYearId={year_id}")
            out["lifeBlock"] = [c.get("course") for c in ci if "Life Block" in (c.get("subject") or "") or "Student Clubs" in (c.get("subject") or "")]
        except Exception:
            out["lifeBlock"] = []
        return sid, out

    students = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(one, rec): rec for rec in scope.values()}
        for f in as_completed(futs):
            rec = futs[f]
            try:
                sid, out = f.result()
            except Exception:
                continue
            _cid = rec["courses"][0] if rec["courses"] else 0
            _cn = next((t["name"] for t in teaching if t.get("courseId") == _cid), "") or ("Advisory" if not rec["courses"] else "")
            students.append({
                "studentId": rec["studentId"], "advisory": rec["advisory"],
                "courses": [{"courseId": _cid,
                             "course": _cn, "name": rec["name"], "className": rec["className"],
                             "parents": rec["parents"], "weightedPct": None}],
                "sections": out.get("sections", []), "diary": out.get("diary", {"entries": []}),
                "attendance": out.get("attendance", {}), "tasks": out.get("tasks", {}),
                "info": out.get("info", {}), "lifeBlock": out.get("lifeBlock", []),
            })
            print(f"\r采集 {len(students)}/{len(scope)}", end="")
    print()
    if not students:
        print("没有取到任何学生数据。请确认该账号在 IntSchool 有任教班级，或检查 token 是否过期。")
        sys.exit(1)
    # Task Weights palette: abbr, colour and weight per task type, as shown in the gradebook
    palette = {}
    course_weights = {}
    for c in teaching:
        try:
            rules = get(f"/task-grade/rule?courseId={c['courseId']}&schoolYearId={year_id}", timeout=15)
            w = {}
            for block in rules or []:
                for r in block.get("rules") or []:
                    name = r.get("taskType")
                    if not name: continue
                    w[name] = r.get("percentage")
                    if name not in palette:
                        palette[name] = {"name": name, "abbr": r.get("abbr") or "",
                                         "colour": r.get("colour") or "", "weight": r.get("percentage")}
            if w: course_weights[c["name"]] = w
        except Exception as e:
            print("任务类型调色板失败", c["name"], e)
    meta = {"teacherName": teacher_name, "schoolId": SCHOOL, "schoolYear": year.get("name"),
            "yearId": year_id, "studentCount": len(students), "generatedAt": dt.datetime.now().isoformat(),
            "teachingCourses": [c["name"] for c in teaching], "advisoryCount": len(advisory)}
    # task descriptions + attachments for the hover detail
    # Cached in data/task_meta_cache.json so nightly runs only fetch new tasks.
    cache_path = os.path.join(DATA, "task_meta_cache.json")
    try:
        task_meta = json.load(open(cache_path, encoding="utf-8"))
    except Exception:
        task_meta = {}
    tids = []
    for st_ in students:
        for sec in st_.get("sections", []):
            for t in sec.get("tasks", []):
                if t.get("id"): tids.append(t["id"])
    uniq = [t for t in dict.fromkeys(tids) if str(t) not in task_meta]
    def fetch_detail(tid):
        try:
            return tid, get(f"/task/detail?taskId={tid}", timeout=12)
        except Exception:
            return tid, None
    if uniq:
        print(f"新增任务说明 {len(uniq)} 条…")
        with ThreadPoolExecutor(max_workers=10) as ex:
            for f in as_completed([ex.submit(fetch_detail, t) for t in uniq]):
                tid, d = f.result()
                if not d: continue
                desc = re.sub(r"<[^>]+>", " ", d.get("description") or "")
                desc = re.sub(r"&nbsp;", " ", desc)
                desc = re.sub(r"\s+", " ", desc).strip()
                task_meta[str(tid)] = {
                    "de": desc[:600],
                    "rs": [r.get("resourceName") for r in (d.get("resources") or [])][:4],
                    "it": d.get("inTotal"), "pf": d.get("publicFlag"),
                }
        try:
            json.dump(task_meta, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
        except Exception as e:
            print("任务缓存写入失败", e)
    print(f"任务说明缓存：{len(task_meta)} 条")
    json.dump({"students": students, "taskMeta": task_meta,
               "taskTypes": list(palette.values()), "courseWeights": course_weights},
              open(os.path.join(DATA, "phase2.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(means, open(os.path.join(DATA, "class_means.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(meta, open(os.path.join(DATA, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：{len(students)} 名学生，写入 data/phase2.json")

if __name__ == "__main__":
    main()
