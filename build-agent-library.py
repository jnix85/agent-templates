#!/usr/bin/env python3
"""Build agent-library.html — a self-contained viewer for all agent .md files.

Usage:  python3 build-agent-library.py
Re-run whenever agents are added or edited to refresh the library.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "agent-library.html"


def parse_frontmatter(text: str):
    """Minimal YAML frontmatter parser for name/description/color keys."""
    meta = {}
    body = text
    if text.startswith("---"):
        end = re.search(r"\n---\s*\n", text[3:])
        if end:
            fm = text[3 : 3 + end.start()]
            body = text[3 + end.end():]
            lines = fm.split("\n")
            i = 0
            while i < len(lines):
                m = re.match(r"^(\w[\w-]*):\s*(.*)$", lines[i])
                if m:
                    key, val = m.group(1), m.group(2).strip()
                    if val in ("|", "|-", ">", ">-", ""):
                        block = []
                        i += 1
                        while i < len(lines) and (lines[i].startswith("  ") or lines[i].strip() == ""):
                            block.append(lines[i][2:] if lines[i].startswith("  ") else "")
                            i += 1
                        meta[key] = "\n".join(block).strip()
                        continue
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                        val = val[1:-1]
                    meta[key] = val
                i += 1
    return meta, body


def first_sentence(text: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def collect_agents():
    agents = []
    for path in sorted(HERE.glob("*.md"), key=lambda p: p.name.lower()):
        raw = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(raw)
        name = meta.get("name") or path.stem
        desc = meta.get("description", "")
        # Strip <example> blocks from the sidebar blurb; keep full desc for the viewer.
        blurb_src = re.split(r"<example>", desc)[0] if desc else body
        agents.append({
            "file": path.name,
            "name": name,
            "color": meta.get("color", "").lower(),
            "description": desc,
            "blurb": first_sentence(blurb_src or ""),
            "body": body.strip(),
            "modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"),
        })
    return agents


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Library</title>
<style>
  :root {
    --bg: #f6f7f9; --panel: #ffffff; --border: #e2e5ea; --text: #1c2430;
    --muted: #667085; --accent: #3b82f6; --code-bg: #f1f3f6; --pre-bg: #10151d;
    --pre-text: #d6deea; --hover: #eef1f5; --active: #e5edfb;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1319; --panel: #161c25; --border: #2a3341; --text: #dbe2ec;
      --muted: #8b96a8; --accent: #60a5fa; --code-bg: #232b38; --pre-bg: #0a0e14;
      --pre-text: #cfd8e6; --hover: #1d2530; --active: #21304a;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; display: flex; height: 100vh; background: var(--bg); color: var(--text);
    font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  #sidebar {
    width: 320px; min-width: 320px; display: flex; flex-direction: column;
    border-right: 1px solid var(--border); background: var(--panel);
  }
  #sidebar header { padding: 16px 16px 10px; border-bottom: 1px solid var(--border); }
  #sidebar h1 { margin: 0 0 2px; font-size: 17px; }
  #sidebar .count { font-size: 12px; color: var(--muted); }
  #search {
    margin: 10px 16px; padding: 8px 12px; width: calc(100% - 32px);
    border: 1px solid var(--border); border-radius: 8px; font-size: 14px;
    background: var(--bg); color: var(--text); outline: none;
  }
  #search:focus { border-color: var(--accent); }
  #list { overflow-y: auto; flex: 1; padding: 4px 8px 16px; }
  .item {
    padding: 9px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 2px;
  }
  .item:hover { background: var(--hover); }
  .item.active { background: var(--active); }
  .item .row { display: flex; align-items: center; gap: 8px; }
  .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
  .item .name { font-weight: 600; font-size: 14px; }
  .item .blurb {
    font-size: 12px; color: var(--muted); margin-top: 2px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  #main { flex: 1; overflow-y: auto; }
  #content { max-width: 860px; margin: 0 auto; padding: 32px 40px 80px; }
  #meta-card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 22px; margin-bottom: 28px;
  }
  #meta-card h1 { margin: 0 0 4px; font-size: 24px; display: flex; align-items: center; gap: 10px; }
  #meta-card .sub { font-size: 13px; color: var(--muted); margin-bottom: 10px; }
  #meta-card .desc { font-size: 14px; color: var(--text); white-space: pre-wrap; }
  #meta-card details summary { cursor: pointer; font-size: 13px; color: var(--accent); margin-top: 6px; }
  .empty { color: var(--muted); text-align: center; margin-top: 30vh; }
  /* rendered markdown */
  .md h1, .md h2, .md h3, .md h4 { line-height: 1.3; margin: 1.6em 0 0.5em; }
  .md h1 { font-size: 22px; } .md h2 { font-size: 19px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  .md h3 { font-size: 16px; } .md h4 { font-size: 15px; }
  .md p { margin: 0.7em 0; }
  .md code { background: var(--code-bg); border-radius: 4px; padding: 1px 5px; font-size: 13px;
             font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .md pre { background: var(--pre-bg); color: var(--pre-text); border-radius: 10px;
            padding: 14px 16px; overflow-x: auto; font-size: 13px; line-height: 1.5; }
  .md pre code { background: none; padding: 0; color: inherit; }
  .md table { border-collapse: collapse; margin: 1em 0; width: 100%; font-size: 14px; display: block; overflow-x: auto; }
  .md th, .md td { border: 1px solid var(--border); padding: 6px 10px; text-align: left; }
  .md th { background: var(--code-bg); }
  .md blockquote { border-left: 3px solid var(--accent); margin: 1em 0; padding: 2px 14px; color: var(--muted); }
  .md ul, .md ol { padding-left: 26px; margin: 0.6em 0; }
  .md li { margin: 0.2em 0; }
  .md hr { border: none; border-top: 1px solid var(--border); margin: 1.6em 0; }
  .md a { color: var(--accent); }
  .md input[type=checkbox] { margin-right: 6px; }
</style>
</head>
<body>
<nav id="sidebar">
  <header>
    <h1>Agent Library</h1>
    <div class="count"><span id="shown"></span> agents · built __BUILT__</div>
  </header>
  <input id="search" type="search" placeholder="Filter agents…" autocomplete="off">
  <div id="list"></div>
</nav>
<main id="main"><div id="content"><div class="empty">Select an agent to view it.</div></div></main>
<script>
const AGENTS = __AGENT_DATA__;
const COLORS = { red:'#ef4444', crimson:'#dc2626', rose:'#f43f5e', orange:'#f97316', amber:'#f59e0b',
  yellow:'#eab308', lime:'#84cc16', green:'#22c55e', emerald:'#10b981', teal:'#14b8a6', cyan:'#06b6d4',
  blue:'#3b82f6', indigo:'#6366f1', violet:'#8b5cf6', purple:'#a855f7', magenta:'#d946ef', pink:'#ec4899',
  gray:'#6b7280', grey:'#6b7280', slate:'#64748b', stone:'#78716c', white:'#9ca3af' };
const PALETTE = Object.values(COLORS).filter((v,i,arr) => arr.indexOf(v) === i);
const colorOf = a => {
  if (COLORS[a.color]) return COLORS[a.color];
  let h = 0;
  for (const ch of a.name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
};

/* ---------- tiny markdown renderer ---------- */
const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
function inline(s){
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, (_,c) => '<code>'+c+'</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[\s(>])\*([^*\s](?:[^*]*[^*\s])?)\*/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s;
}
function renderMarkdown(src){
  const lines = src.replace(/\r\n/g,'\n').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length){
    const line = lines[i];
    if (!line.trim()){ i++; continue; }
    // fenced code
    let m = line.match(/^\s*(`{3,}|~{3,})\s*(\S*)\s*$/) || line.match(/^\s*(`{3,}|~{3,})(.*)$/);
    if (m){
      const marker = m[1][0], len = m[1].length, lang = (m[2]||'').trim();
      const buf = []; i++;
      while (i < lines.length){
        const c = lines[i].match(/^\s*(`{3,}|~{3,})\s*$/);
        if (c && c[1][0] === marker && c[1].length >= len){ i++; break; }
        buf.push(lines[i]); i++;
      }
      out.push('<pre><code>'+esc(buf.join('\n'))+'</code></pre>');
      continue;
    }
    // heading
    m = line.match(/^(#{1,6})\s+(.*)$/);
    if (m){ const l = m[1].length; out.push(`<h${l}>`+inline(m[2])+`</h${l}>`); i++; continue; }
    // hr
    if (/^\s*([-*_])\s*(\1\s*){2,}$/.test(line)){ out.push('<hr>'); i++; continue; }
    // blockquote
    if (/^\s*>/.test(line)){
      const buf = [];
      while (i < lines.length && /^\s*>/.test(lines[i])){ buf.push(lines[i].replace(/^\s*>\s?/,'')); i++; }
      out.push('<blockquote>'+renderMarkdown(buf.join('\n'))+'</blockquote>');
      continue;
    }
    // table
    if (line.includes('|') && i+1 < lines.length && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i+1])){
      const cells = r => r.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|').map(c=>c.trim());
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()){ rows.push(cells(lines[i])); i++; }
      let t = '<table><thead><tr>' + head.map(c=>'<th>'+inline(c)+'</th>').join('') + '</tr></thead><tbody>';
      for (const r of rows) t += '<tr>' + r.map(c=>'<td>'+inline(c)+'</td>').join('') + '</tr>';
      out.push(t + '</tbody></table>');
      continue;
    }
    // list (with simple nesting by indent)
    if (/^\s*([-*+]|\d+\.)\s+/.test(line)){
      const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])){
        const lm = lines[i].match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
        items.push({ indent: lm[1].length, ordered: /\d/.test(lm[2]), text: lm[3] });
        i++;
        // continuation lines
        while (i < lines.length && lines[i].trim() && !/^\s*([-*+]|\d+\.)\s+/.test(lines[i]) &&
               /^\s{2,}/.test(lines[i]) && !/^\s*(`{3,}|~{3,})/.test(lines[i])){
          items[items.length-1].text += ' ' + lines[i].trim(); i++;
        }
      }
      out.push(buildList(items, 0));
      continue;
    }
    // paragraph
    const buf = [line];
    i++;
    while (i < lines.length && lines[i].trim() &&
           !/^(#{1,6}\s|\s*([-*+]|\d+\.)\s|\s*>|\s*(`{3,}|~{3,}))/.test(lines[i]) &&
           !(lines[i].includes('|') && i+1 < lines.length && /^\s*\|?[\s:|-]+\|/.test(lines[i+1]))){
      buf.push(lines[i]); i++;
    }
    out.push('<p>'+inline(buf.join(' '))+'</p>');
  }
  return out.join('\n');
}
function buildList(items, depth){
  if (!items.length) return '';
  const base = items[0].indent;
  const tag = items[0].ordered ? 'ol' : 'ul';
  let html = '<'+tag+'>';
  let k = 0;
  while (k < items.length){
    const it = items[k];
    const kids = [];
    let j = k + 1;
    while (j < items.length && items[j].indent > base){ kids.push(items[j]); j++; }
    let text = it.text;
    let cb = '';
    const cbm = text.match(/^\[([ xX])\]\s+(.*)$/);
    if (cbm){ cb = '<input type="checkbox" disabled'+(cbm[1] !== ' ' ? ' checked' : '')+'>'; text = cbm[2]; }
    html += '<li>' + cb + inline(text) + (kids.length && depth < 4 ? buildList(kids, depth+1) : '') + '</li>';
    k = j;
  }
  return html + '</'+tag+'>';
}

/* ---------- app ---------- */
const listEl = document.getElementById('list');
const contentEl = document.getElementById('content');
const searchEl = document.getElementById('search');
const shownEl = document.getElementById('shown');
let activeFile = null;

function renderList(filter){
  const q = (filter||'').toLowerCase();
  const matches = AGENTS.filter(a =>
    !q || a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q) || a.file.toLowerCase().includes(q));
  shownEl.textContent = q ? matches.length + ' / ' + AGENTS.length : AGENTS.length;
  listEl.innerHTML = '';
  for (const a of matches){
    const div = document.createElement('div');
    div.className = 'item' + (a.file === activeFile ? ' active' : '');
    div.innerHTML = '<div class="row"><span class="dot" style="background:'+colorOf(a)+'"></span>' +
                    '<span class="name">'+esc(a.name)+'</span></div>' +
                    '<div class="blurb">'+esc(a.blurb)+'</div>';
    div.onclick = () => show(a.file);
    listEl.appendChild(div);
  }
  if (!matches.length) listEl.innerHTML = '<div style="padding:16px;color:var(--muted);font-size:13px">No agents match.</div>';
}

function show(file){
  const a = AGENTS.find(x => x.file === file);
  if (!a) return;
  activeFile = file;
  location.hash = encodeURIComponent(file);
  renderList(searchEl.value);
  let descBlock = '';
  if (a.description){
    const short = a.description.split(/<example>/)[0].trim();
    const hasExamples = a.description.includes('<example>');
    descBlock = '<div class="desc">'+esc(short)+'</div>' +
      (hasExamples ? '<details><summary>Full description with examples</summary><div class="desc" style="margin-top:8px">'+esc(a.description)+'</div></details>' : '');
  }
  contentEl.innerHTML =
    '<div id="meta-card"><h1><span class="dot" style="background:'+colorOf(a)+';width:12px;height:12px"></span>'+esc(a.name)+'</h1>' +
    '<div class="sub">'+esc(a.file)+' · modified '+a.modified+'</div>' + descBlock + '</div>' +
    '<div class="md">'+renderMarkdown(a.body)+'</div>';
  document.getElementById('main').scrollTop = 0;
}

searchEl.addEventListener('input', () => renderList(searchEl.value));
renderList('');
const initial = decodeURIComponent(location.hash.slice(1));
if (initial && AGENTS.some(a => a.file === initial)) show(initial);
</script>
</body>
</html>
"""


def main():
    agents = collect_agents()
    if not agents:
        sys.exit("No .md files found next to this script.")
    data = json.dumps(agents, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__AGENT_DATA__", data).replace(
        "__BUILT__", datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"Indexed {len(agents)} agents -> {OUT}")


if __name__ == "__main__":
    main()
