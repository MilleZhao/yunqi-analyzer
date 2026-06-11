import sys, json, re, os
sys.stdout.reconfigure(encoding="utf-8")
import docx as dx
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

workdir = r"C:\Users\LENOVO\Documents\云阙智能1"
links_path = r"C:\Users\LENOVO\Documents\CodexProjects\Project018-云阙智能1\链接.docx"

# === READ 链接.docx with simpler approach ===
links_doc = dx.Document(links_path)

xhs_children = []
xhs_books = []
dy_children = []
dy_books = []

# Collect all paragraphs in order
all_paras = [(p.text.strip(), p) for p in links_doc.paragraphs]

section = None
pending = {"url": "", "desc": ""}

def flush_pair():
    global pending
    url = pending["url"].strip()
    desc = pending["desc"].strip()
    if not url:
        pending = {"url": "", "desc": ""}
        return
    if section == "xhs_children":
        # Try extract account name from desc: "desc - account | 小红书"
        m = re.search(r'-\s*(.+?)\s*\|', desc) or re.search(r'-\s*(.+?)$', desc)
        account = m.group(1).strip() if m else ""
        desc_clean = re.sub(r'^\d+\s*【(.+?)】.*', r'\1', desc) if desc else ""
        if desc_clean == desc:
            desc_clean = desc[:200]
        xhs_children.append({"account": account, "desc": desc_clean, "url": url})
    elif section == "xhs_books":
        m = re.search(r'-\s*(.+?)\s*\|', desc) or re.search(r'-\s*(.+?)$', desc)
        account = m.group(1).strip() if m else ""
        desc_clean = re.sub(r'^\d+\s*【(.+?)】.*', r'\1', desc) if desc else ""
        if desc_clean == desc:
            desc_clean = desc[:200]
        xhs_books.append({"account": account, "desc": desc_clean, "url": url})
    elif section == "dy_children":
        dy_children.append({"desc": desc[:200], "url": url})
    elif section == "dy_books":
        dy_books.append({"desc": desc[:200], "url": url})
    pending = {"url": "", "desc": ""}

i = 0
while i < len(all_paras):
    t, p = all_paras[i]
    
    # Detect section headers
    if "少儿童书——小红书" in t:
        flush_pair()
        section = "xhs_children"
        i += 1
        continue
    elif "图书——小红书" in t:
        flush_pair()
        section = "xhs_books"
        i += 1
        continue
    elif "少儿童书——抖音" in t:
        flush_pair()
        section = "dy_children"
        i += 1
        continue
    elif "图书——抖音" in t:
        flush_pair()
        section = "dy_books"
        i += 1
        continue
    
    if not t:
        # Blank line: flush if we have a complete pair
        if pending["url"] and pending["desc"]:
            flush_pair()
        elif pending["url"] and not pending["desc"]:
            # URL without desc yet, look ahead
            pass
        i += 1
        continue
    
    if section in ("xhs_children", "xhs_books"):
        # Each paragraph is self-contained with URL
        link_match = re.search(r'(https?://[^\s]+)', t)
        if link_match:
            url = link_match.group(1)
            m = re.search(r'-\s*(.+?)\s*\|', t)
            account = m.group(1).strip() if m else ""
            desc_clean = re.sub(r'^\d+\s*【(.+?)】.*', r'\1', t) if t else ""
            if desc_clean == t:
                desc_clean = ""
            if section == "xhs_children":
                xhs_children.append({"account": account, "desc": desc_clean, "url": url})
            else:
                xhs_books.append({"account": account, "desc": desc_clean, "url": url})
        i += 1
        continue
    
    elif section in ("dy_children", "dy_books"):
        if t.startswith("http") or t.startswith("douyin.com"):
            if pending["url"] and pending["desc"]:
                flush_pair()
            elif pending["url"] and not pending["desc"]:
                flush_pair()
            pending["url"] = t if t.startswith("http") else "https://" + t
            pending["desc"] = ""
        else:
            if pending["url"]:
                pending["desc"] = t
                # Next is likely blank, so flush now
                # But check if next is not a URL
                if i+1 < len(all_paras):
                    nt = all_paras[i+1][0].strip()
                    if not nt.startswith("http") and not nt.startswith("douyin.com"):
                        # Could be continuation of desc, wait
                        pass
                flush_pair()
        i += 1
        continue
    
    i += 1

# Flush remaining
flush_pair()

print(f"小红书 少儿童书: {len(xhs_children)}")
for x in xhs_children: print(f"  [{x['account']}] {x['url'][:70]}")
print(f"\n小红书 图书: {len(xhs_books)}")
for x in xhs_books: print(f"  [{x['account']}] {x['url'][:70]}")
print(f"\n抖音 少儿童书: {len(dy_children)}")
for x in dy_children: print(f"  {x['url'][:60]} | {x['desc'][:50]}")
print(f"\n抖音 图书: {len(dy_books)}")
for x in dy_books: print(f"  {x['url'][:60]} | {x['desc'][:50]}")

# Save parsed data for document builder
parsed = {"xhs_children": xhs_children, "xhs_books": xhs_books, "dy_children": dy_children, "dy_books": dy_books}
with open(os.path.join(workdir, "links_parsed.json"), "w", encoding="utf-8") as f:
    json.dump(parsed, f, ensure_ascii=False, indent=2)
print("\nParsed data saved to links_parsed.json")
