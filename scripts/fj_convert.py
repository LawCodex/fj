#!/usr/bin/env python3
"""Convert cached laws.gov.fj API responses (see fj_fetch.py) into LawCodex Markdown.

Usage: fj_convert.py RAW_DIR OUT_DIR
"""
import base64, datetime, io, json, os, re, sys, unicodedata
from bs4 import BeautifulSoup
from markdownify import markdownify
import pypdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fj_fetch import get  # noqa: E402  (cache-only reads once fetched)

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()
SITE = "https://www.laws.gov.fj"


def slug(s, n=90):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n].rstrip("-")


def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def clean_title(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    t = re.sub(r"^\[[^\]]*\]\s*", "", t)  # loose-leaf paragraph number e.g. [ACC 25]
    return t


def html_to_md(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for el in soup.select("span.hidden, div.hiddendiv, style, span.edpnum"):
        el.decompose()
    # drop the node's own title block (we emit our own heading)
    first = soup.find(["section", "div"])
    if first is not None:
        t = first.find("div", class_="title", recursive=False)
        if t is not None:
            t.decompose()
    for img in soup.find_all("img"):
        src = img.get("src", "")
        name = os.path.basename(src.split("?")[0]) if src else ""
        img.replace_with(f"[image: {name}]" if name else "[image]")
    for a in soup.find_all("a"):
        a.unwrap()
    for ul in soup.find_all(["ul", "ol"]):
        ul.name = "div"
    for li in soup.find_all("li"):
        li.name = "p"
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        term = dt.get_text(" ", strip=True)
        b = soup.new_tag("strong")
        b.string = term
        if dd is not None:
            dd.name = "p"
            dd.insert(0, " ")
            dd.insert(0, b)
            dt.decompose()
        else:
            dt.name = "p"
            dt.string = ""
            dt.append(b)
    for tag in soup.find_all("dd"):
        tag.name = "p"
    for tag in soup.find_all(["dl"]):
        tag.name = "div"
    for tag in soup.find_all("blockquote"):
        tag.name = "div"
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.name = "p"
        tag.insert(0, "**")
        tag.append("**")
    for tag in soup.find_all(["div", "section"]):
        # block-level containers: make sure contents are separated
        if tag.find(["p", "div", "table", "section"]) is None and tag.get_text(strip=True):
            tag.name = "p"
    body = soup.body or soup
    md = markdownify(str(body), heading_style="ATX", bullets="-", strip=["span"])
    md = md.replace(" ", " ").replace(" ", " ").replace("\xa0", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n[ \t]+", "\n", md)
    md = re.sub(r"[ \t]{2,}", " ", md)
    md = re.sub(r"\*\*\s+", "**", md)
    md = re.sub(r"\s+\*\*(\n|$)", r"**\1", md)
    md = re.sub(r"\*\*\*\*", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def nodes_sorted(lst):
    return sorted(lst or [], key=lambda x: int(x.get("Position") or 0))


def render_tree(lst, depth, out):
    for n in nodes_sorted(lst):
        d = get("retrieve_html/" + n["LegalId"]) or {}
        title = clean_title(n["Title"])
        if title.endswith("(Repealed)"):
            title = title[:-10].strip()
        if n.get("IsRepealed") == "true":
            title += " (Repealed)"
        if depth <= 6:
            out.append("#" * depth + " " + title)
        else:
            out.append("**" + title + "**")
        body = html_to_md(d.get("section_html", ""))
        if body:
            out.append(body)
        fns = [html_to_md(f.get("Html", "")) for f in (d.get("FootNoteRels") or [])]
        fns = [f for f in fns if f and f not in body]
        if fns:
            out.append("Footnotes:\n\n" + "\n\n".join(fns))
        render_tree(n.get("SectionData"), depth + 1, out)


def parse_date(s):
    for fmt in ("%d %B %Y", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date().isoformat()
        except Exception:
            pass
    return None


def write_law(path, body_node, kind, parent=None, act_meta=None):
    d = get("retrieve_html/" + body_node["LegalId"]) or {}
    title = clean_title(body_node["Title"])
    ident = re.sub(r"\.BODY$", "", body_node["LegalId"])
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b(?!.*\b(1[89]\d\d|20\d\d)\b)", title)
    fm = ["---", f"title: {yq(title)}", f"identifier: {yq(ident)}", f"type: {kind}",
          "jurisdiction: fj", "language: en"]
    if m:
        fm.append(f"year: {m.group(1)}")
    lu = parse_date(d.get("act_last_updated") or "")
    if lu:
        fm.append(f"last_amended: {lu}  # 'last updated' date of the consolidation on laws.gov.fj")
    fm.append("status: " + ("repealed" if body_node.get("IsRepealed") == "true" else "in_force"))
    if parent:
        fm.append(f"parent_act: {yq(parent)}")
    if act_meta:
        fm.append(f"source: {yq(SITE + '/consolidated-law/' + act_meta['ActId'])}")
    fm += [f"source_api: {yq(SITE + '/api/retrieve_html/' + body_node['LegalId'])}", f"retrieved: {TODAY}", "---", ""]
    out = [f"# {title}"]
    desc = html_to_md(d.get("act_description", ""))
    if desc:
        out.append(desc)
    body = html_to_md(d.get("section_html", ""))
    if body:
        out.append(body)
    render_tree(body_node.get("SectionData"), 2, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(fm) + "\n\n".join(out) + "\n")


def structure_constitution(lines):
    """Turn extracted constitution lines into Markdown (skip the table of contents)."""
    lines = [l for l in lines if l]
    idx = [i for i, l in enumerate(lines) if l in ("PREAMBLE", "IKAU")]
    if len(idx) >= 2:
        lines = lines[idx[1]:]
    out, para = [], []

    def flush():
        if para:
            out.append(" ".join(para))
            para.clear()

    i = 0
    while i < len(lines):
        l = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if re.match(r"^(CHAPTER|WASE) \d+\s*—", l) or l in ("PREAMBLE", "IKAU") or re.match(r"^(SCHEDULE|IVAKAMACALA)\b", l):
            flush(); out.append("## " + l)
        elif re.match(r"^(Part|Tabana) [A-Z]\s*—", l):
            flush(); out.append("### " + l)
        elif re.match(r"^\d+[A-Z]?\.(—|\s)", nxt) and not re.search(r"[.;:,—-]$", l) and len(l) < 120 and not l.startswith("("):
            flush()
            num = re.match(r"^(\d+[A-Z]?)\.", nxt).group(1)
            out.append(f"#### {num}. {l}")
            para.append(nxt)
            i += 1
        elif re.match(r"^(\(\w{1,5}\)|\d+[A-Z]?\.(—|\s))", l):
            flush(); para.append(l)
        else:
            para.append(l)
        i += 1
    flush()
    return "\n\n".join(out)


def constitution():
    c = get("retrieve_constitution")
    n = 0
    for lang, key, code in (("English", "English_PDFFile", "en"), ("iTaukei", "Taukei_PDFFile", "fj")):
        pdf = base64.b64decode(c[key])
        assert pdf.rstrip().endswith(b"%%EOF"), "truncated constitution PDF"
        r = pypdf.PdfReader(io.BytesIO(pdf))
        pages = [p.extract_text() or "" for p in r.pages]
        text = "\n\n".join(pages)
        text = text.replace("\t", " ")
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        lines = []
        for ln in text.split("\n"):
            s = ln.strip()
            if re.fullmatch(r"\d{1,3}", s):  # page numbers
                continue
            lines.append(s)
        text = structure_constitution(lines)
        title = "Constitution of the Republic of Fiji" if code == "en" else "Constitution of the Republic of Fiji (iTaukei translation)"
        fm = ["---", f"title: {yq(title)}", 'identifier: "Constitution 2013"', "type: constitution",
              "jurisdiction: fj", f"language: {code}", "date: 2013-09-06", "status: in_force",
              f"source: {yq(SITE + '/fijian-constitution')}",
              f"source_api: {yq(SITE + '/api/retrieve_constitution')}",
              f"source_file: {yq(c.get(key + '_Name') or c.get(key.replace('PDFFile', 'PDFFile_Name')) or '')}",
              "format_note: \"text extracted from the official PDF; page layout not preserved\"",
              f"retrieved: {TODAY}", "---", ""]
        if code != "en":
            fm.insert(-3, 'note: "official translation; the English text is authoritative (s 3(3) of the Constitution)"')
        p = os.path.join(OUT, "constitution", f"constitution-2013-{code}.md")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(fm) + f"# {title}\n\n" + text + "\n")
        n += 1
    return n


def main():
    nc = constitution()
    acts = get("get_all_acts")
    na = ns = 0
    used = set()
    for a in acts:
        toc = get("get_act_by_id/" + a["ActId"]) or []
        main_grp = [g for g in toc if g.get("ActId") == a["ActId"]]
        sub_grp = [g for g in toc if g.get("ActId") != a["ActId"]]
        aslug = slug(a["ActName"])
        if aslug in used:
            aslug += "-" + a["ActId"]
        used.add(aslug)
        for g in main_grp:
            tops = nodes_sorted(g.get("Sections"))
            for i, body in enumerate(tops):
                p = os.path.join(OUT, "acts", aslug + (f"-{i+1}" if i else "") + ".md")
                write_law(p, body, "act", act_meta=a)
                na += 1
        sused = set()
        for g in sub_grp:
            for body in nodes_sorted(g.get("Sections")):
                s = slug(clean_title(body["Title"]))
                if s in sused:
                    s += "-" + slug(body["LegalId"].split(".")[-2] if "." in body["LegalId"] else body["Position"])
                sused.add(s)
                p = os.path.join(OUT, "subsidiary", aslug, s + ".md")
                write_law(p, body, "subsidiary", parent=a["ActName"], act_meta=a)
                ns += 1
    print(f"constitution {nc}, acts {na}, subsidiary {ns}")


if __name__ == "__main__":
    main()
