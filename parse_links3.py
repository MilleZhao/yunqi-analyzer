import sys, json, os, re
sys.stdout.reconfigure(encoding="utf-8")
import docx as dx

links_path = r"C:\Users\LENOVO\Documents\CodexProjects\Project018-云阙智能1\链接.docx"
links_doc = dx.Document(links_path)

xhs_children = []
xhs_books = []
dy_children = []
dy_books = []
section = None
pending_url = ""

for p in links_doc.paragraphs:
    t = p.text.strip()
    if not t:
        continue
    
    if "少儿童书——小红书" in t:
        section = "xhs_children"; continue
    elif "图书——小红书" in t:
        section = "xhs_books"; continue
    elif "少儿童书——抖音" in t:
        section = "dy_children"; pending_url = ""; continue
    elif "图书——抖音" in t:
        section = "dy_books"; pending_url = ""; continue
    
    if section in ("xhs_children", "xhs_books"):
        # Split paragraph by "http" - each URL is a separate entry
        parts = re.split(r'(https?://[^\s]+)', t)
        entries = []
        for j in range(0, len(parts)-1, 2):
            desc = parts[j].strip()
            url = parts[j+1].strip()
            # Clean desc: extract account name and description
            m_acc = re.search(r'^(.+?)\s*[|｜]', desc)\n            if not m_acc:\n                m_acc = re.search(r'-\s*(.+?)\s*[|｜]', desc)
            account = m_acc.group(1).strip() if m_acc else ""
            m_desc = re.search(r'【(.+?)】', desc)
            desc_clean = m_desc.group(1).strip() if m_desc else ""
            entries.append({"account": account, "desc": desc_clean, "url": url})
        
        if section == "xhs_children":
            xhs_children.extend(entries)
        else:
            xhs_books.extend(entries)
    
    elif section in ("dy_children", "dy_books"):
        if t.startswith("http") or t.startswith("douyin.com"):
            pending_url = t if t.startswith("http") else "https://" + t
        elif pending_url:
            # desc line
            clean_desc = re.sub(r'\s*-\s*抖音$', '', t).strip()
            if section == "dy_children":
                dy_children.append({"desc": clean_desc, "url": pending_url})
            else:
                dy_books.append({"desc": clean_desc, "url": pending_url})
            pending_url = ""

# Save
parsed = {"xhs_children": xhs_children, "xhs_books": xhs_books, "dy_children": dy_children, "dy_books": dy_books}
with open(r"C:\Users\LENOVO\Documents\云阙智能1\links_parsed.json", "w", encoding="utf-8") as f:
    json.dump(parsed, f, ensure_ascii=False, indent=2)

print(f"XHS Children: {len(xhs_children)}")
for x in xhs_children:
    print(f"  [{x['account']}] {x['desc'][:60]}  ->  {x['url'][:60]}")
print(f"\nXHS Books: {len(xhs_books)}")
for x in xhs_books:
    print(f"  [{x['account']}] {x['desc'][:60]}  ->  {x['url'][:60]}")
print(f"\nDY Children: {len(dy_children)}")
for x in dy_children:
    print(f"  {x['desc'][:50]}  ->  {x['url'][:50]}")
print(f"\nDY Books: {len(dy_books)}")
for x in dy_books:
    print(f"  {x['desc'][:50]}  ->  {x['url'][:50]}")
