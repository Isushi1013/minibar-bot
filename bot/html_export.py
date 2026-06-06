from __future__ import annotations

import html
from datetime import datetime

from bot.catalog import ALL_ITEMS, DISPLAY_ORDER
from bot.config import HTML_EXPORT_PATH, TXT_EXPORT_PATH
from bot.formatters import format_room_block
from bot.storage import load_history


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def _room_items_html(counts: dict[str, int]) -> str:
    rows: list[str] = []
    for key in DISPLAY_ORDER:
        n = counts.get(key, 0)
        if n > 0:
            rows.append(
                f"<li><span class=\"item\">{_esc(ALL_ITEMS[key])}</span>"
                f"<span class=\"qty\">× {n}</span></li>"
            )
    if not rows:
        rows.append('<li class="empty-item">— без позиций —</li>')
    return f"<ul class=\"items\">{''.join(rows)}</ul>"


def _batch_card(batch: dict) -> str:
    rooms_html: list[str] = []
    for room_entry in batch.get("rooms", []):
        room = room_entry.get("room", "?")
        counts = room_entry.get("counts", {})
        rooms_html.append(
            f"""
<div class="room">
  <h3>Номер {_esc(str(room))}</h3>
  {_room_items_html(counts)}
</div>"""
        )
    bid = batch.get("id", "")
    return f"""
<article class="batch">
  <header class="batch-head">
    <time>{_esc(bid)}</time>
    <span class="badge">{len(batch.get('rooms', []))} ном.</span>
  </header>
  {''.join(rooms_html)}
</article>"""


def render_full_html(data: dict | None = None) -> str:
    data = data or load_history()
    batches = list(reversed(data.get("batches", [])))
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    total_rooms = sum(len(b.get("rooms", [])) for b in data.get("batches", []))

    if batches:
        cards = "\n".join(_batch_card(b) for b in batches)
    else:
        cards = '<p class="empty">Списаний пока нет.</p>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Списания мини-бара</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0; padding: 12px;
      background: #e8f0f8; color: #1a2a3a;
      line-height: 1.45;
    }}
    header {{
      background: linear-gradient(135deg, #1e5a8a, #3d8fd1);
      color: #fff; padding: 20px 16px; border-radius: 16px;
      margin-bottom: 16px;
    }}
    header h1 {{ margin: 0 0 4px; font-size: 1.35rem; }}
    header .updated {{ opacity: 0.9; font-size: 0.85rem; }}
    .stats {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
      margin-bottom: 16px;
    }}
    .stat {{
      background: #fff; border-radius: 12px; padding: 12px;
      text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }}
    .stat b {{ display: block; font-size: 1.5rem; color: #1e5a8a; }}
    .stat span {{ font-size: 0.8rem; color: #666; }}
    .batch {{
      background: #fff; border-radius: 14px; padding: 14px 16px;
      margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.07);
    }}
    .batch-head {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 12px; padding-bottom: 8px;
      border-bottom: 1px solid #e8eef4;
    }}
    .batch-head time {{ font-weight: 600; color: #1e5a8a; }}
    .badge {{
      font-size: 0.8rem; background: #e8f4fc; color: #1e5a8a;
      padding: 4px 10px; border-radius: 20px;
    }}
    .room {{
      margin-bottom: 12px; padding: 10px 12px;
      background: #f7fafc; border-radius: 10px;
      border-left: 4px solid #3d8fd1;
    }}
    .room h3 {{ margin: 0 0 8px; font-size: 1.05rem; }}
    .items {{ list-style: none; margin: 0; padding: 0; }}
    .items li {{
      display: flex; justify-content: space-between;
      padding: 4px 0; font-size: 0.95rem;
    }}
    .item {{ color: #333; }}
    .qty {{ font-weight: 600; color: #1e5a8a; }}
    .empty-item {{ color: #999; font-style: italic; }}
    .empty {{ text-align: center; color: #888; padding: 24px; }}
    footer {{ text-align: center; font-size: 0.75rem; color: #999; padding: 16px; }}
  </style>
</head>
<body>
  <header>
    <h1>🍾 Списания мини-бара</h1>
    <p class="updated">Обновлено: {now}</p>
  </header>
  <section class="stats">
    <div class="stat"><b>{len(data.get('batches', []))}</b><span>оформлений</span></div>
    <div class="stat"><b>{total_rooms}</b><span>номеров всего</span></div>
  </section>
  <main>
    {cards}
  </main>
  <footer>Файл создан ботом списаний мини-бара</footer>
</body>
</html>"""


def write_html_export(data: dict | None = None) -> str:
    content = render_full_html(data)
    path = HTML_EXPORT_PATH
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p.resolve())


def render_text_export(data: dict | None = None) -> str:
    data = data or load_history()
    batches = list(reversed(data.get("batches", [])))
    lines = ["Списания мини-бара", ""]
    if not batches:
        lines.append("Списаний пока нет.")
        return "\n".join(lines)

    for batch in batches:
        lines.append(f"Оформление: {batch.get('id', '')}")
        for entry in batch.get("rooms", []):
            lines.append(format_room_block(str(entry.get("room", "?")), entry.get("counts", {})))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_text_export(data: dict | None = None) -> str:
    content = render_text_export(data)
    from pathlib import Path

    p = Path(TXT_EXPORT_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p.resolve())
