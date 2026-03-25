import pandas as pd
import json
from typing import List, Dict, Any, Tuple
from src.models import ReviewerAssessment
from src.parser_registry import register_parser

# Load color definitions once
try:
    with open('data/color_data.json', 'r', encoding='utf-8') as f:
        COLOR_DATA = json.load(f)
except:
    COLOR_DATA = {}

def get_color(sheet, r, c):
    if sheet in COLOR_DATA:
        if str(r) in COLOR_DATA[sheet]:
            if str(c) in COLOR_DATA[sheet][str(r)]:
                return COLOR_DATA[sheet][str(r)][str(c)]
    return None

def clean_str(val: Any) -> str:
    v = str(val).strip()
    if v == '?' or v == '？' or v.lower() == 'nan': return ''
    return v

def clean_newline(val: str) -> str:
    return val.replace('\r\n', '\n').strip()

def extract_declaration(df: pd.DataFrame, header_idx: int) -> str:
    import re as _dre
    TEMPLATE_NOISE = ('请于此页复制模板', '请勿在此处打分', '下半场请尽量复用工作表')
    DIVIDER_PATTERN = ('AC1','AC2','AF1','AF2','SC1','SC2','SF1','SF2')
    TICKET_NOISE = ('AC1（', 'AC2（', 'AF1（', 'AF2（', 'SC1（', 'SC2（', 'SF1（', 'SF2（')
    lines = []
    # 1) Scan rows ABOVE the header
    for r in range(header_idx):
        row_vals = []
        for x in df.iloc[r].values:
            cx = clean_str(x)
            if not cx: continue
            if any(t in cx for t in TEMPLATE_NOISE): continue
            row_vals.append(cx)
        if not row_vals: continue
        joined = ' | '.join(row_vals)
        if all(v.strip() in DIVIDER_PATTERN for v in row_vals): continue
        # Skip ticket count lines like 'AC1（6+31）...'
        if any(joined.startswith(t) for t in TICKET_NOISE): continue
        lines.append(joined)
    # 2) Scan rows AFTER header for non-song-ID rows with long text (e.g. X-Ray Row1, Ehu Row2)
    for r in range(header_idx + 1, min(header_idx + 5, len(df))):
        row = df.iloc[r].values
        c0 = ''
        for cell in row:
            cv = clean_str(cell).replace(' ', '')
            if cv:
                c0 = cv
                break
        if _dre.match(r'^[A-Za-z]{2}\d{3,}', c0): break  # hit real data
        if c0 in DIVIDER_PATTERN: continue  # section label
        if c0 == '编号': continue  # another header
        row_vals = []
        for x in row:
            cx = clean_str(x)
            if not cx: continue
            if any(t in cx for t in TEMPLATE_NOISE): continue
            row_vals.append(cx)
        if not row_vals: continue
        joined = ' | '.join(row_vals)
        if len(joined) > 15:
            lines.append(joined)
    # 3) Scan side columns (col >= 8) in pre-header rows ONLY (not data rows)
    for r in range(0, min(header_idx + 1, len(df))):
        row_vals_all = df.iloc[r].values
        for c in range(8, len(row_vals_all)):
            v = clean_str(row_vals_all[c])
            if v and len(v) > 20 and not v.replace('.','').replace('-','').isdigit():
                if not any(t in v for t in TEMPLATE_NOISE):
                    lines.append(f'[侧栏注] {v}')
    decl = '\n'.join(lines)
    decl = decl.replace('■ 三倍票', '🟥 三倍票').replace('■ 一倍票', '🟩 一倍票').replace('■ 还在斟酌', '🟨 还在斟酌')
    return decl

@register_parser("模板页")
def parse_模板页(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 3
        if len(row) > 22:
            song_id = clean_str(row[21]).replace(" ", "")
            song_name = clean_str(row[22])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 23 < len(row):
                    val = clean_str(row[23])
                    color = get_color(reviewer_name, idx, 23)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 24 < len(row):
                    val = clean_str(row[24])
                    color = get_color(reviewer_name, idx, 24)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 25 < len(row):
                    val = clean_str(row[25])
                    color = get_color(reviewer_name, idx, 25)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 26 < len(row):
                    val = clean_str(row[26])
                    color = get_color(reviewer_name, idx, 26)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 27 < len(row):
                    val = clean_str(row[27])
                    color = get_color(reviewer_name, idx, 27)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 28 < len(row):
                    val = clean_str(row[28])
                    color = get_color(reviewer_name, idx, 28)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 29 < len(row):
                    val = clean_str(row[29])
                    color = get_color(reviewer_name, idx, 29)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("檐下猫&南宫若馨Cylna.AC+部分AF")
def parse_檐下猫_南宫若馨Cylna_AC_部分AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["虚拟一倍"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["虚拟三倍"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["草"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["南宫评"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["猫评"] = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[猫评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 10:
            song_id = clean_str(row[9]).replace(" ", "")
            song_name = clean_str(row[10])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 11 < len(row):
                    val = clean_str(row[11])
                    color = get_color(reviewer_name, idx, 11)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["一倍"] = val
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["三倍"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["草"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["南宫评"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["一倍"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["三倍"] = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["草"] = val
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["猫评"] = val
                if 19 < len(row):
                    val = clean_str(row[19])
                    color = get_color(reviewer_name, idx, 19)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[猫留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("ctce SF瞎评价")
def parse_ctce_SF瞎评价(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 14)
    for idx in range(15, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 3:
            song_id = clean_str(row[2]).replace(" ", "")
            song_name = clean_str(row[3])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["20s印象"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["票"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("枫岚聊混音")
def parse_枫岚聊混音(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["融合性/均衡/质感"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["混响"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["声场"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 10:
            song_id = clean_str(row[9]).replace(" ", "")
            song_name = clean_str(row[10])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 11 < len(row):
                    val = clean_str(row[11])
                    color = get_color(reviewer_name, idx, 11)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("imi的sc乱评")
def parse_imi的sc乱评(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("乱评价")
def parse_乱评价(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("アドミン.SF")
def parse_アドミン_SF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 3)
    for idx in range(4, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("雷云云云.AF")
def parse_雷云云云_AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("锐评一个a组下半场")
def parse_锐评一个a组下半场(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("186.SC")
def parse_186_SC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["操作"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["解析"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["操作"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["技巧"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["解析"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["潜力"] = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 19 < len(row):
                    val = clean_str(row[19])
                    color = get_color(reviewer_name, idx, 19)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("Ehu.SC")
def parse_Ehu_SC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["歌姬"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["操作"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["技巧"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["解析"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["潜力"] = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("。SC")
def parse_SC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["歌姬"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["操作"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["技巧"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["解析"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["潜力"] = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("720 下半AF")
def parse_720_下半AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["瞎几把ray一下（）"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("happy")
def parse_happy(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        overall = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        extra["瞎几把评"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        extra["唠嗑（？"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    _green_set = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32")
                    _has_green = False
                    if get_color(reviewer_name, idx, 0) and get_color(reviewer_name, idx, 0).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 1) and get_color(reviewer_name, idx, 1).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 2) and get_color(reviewer_name, idx, 2).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 3) and get_color(reviewer_name, idx, 3).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 4) and get_color(reviewer_name, idx, 4).upper() in _green_set: _has_green = True
                    if _has_green:
                        overall = "🌿草票 " + overall if overall else "🌿草票"
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 7:
            song_id = clean_str(row[6]).replace(" ", "")
            song_name = clean_str(row[7])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        overall = val
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        extra["随便评"] = val
                if 10 < len(row):
                    val = clean_str(row[10])
                    color = get_color(reviewer_name, idx, 10)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        extra["唠嗑"] = val
                if 11 < len(row):
                    val = clean_str(row[11])
                    color = get_color(reviewer_name, idx, 11)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        extra["（5+23，5+15，3+9，4+14）"] = val
                if 30 < len(row):
                    val = clean_str(row[30])
                    color = get_color(reviewer_name, idx, 30)
                    # happy: skip color annotation (handled as 草票)
                    if val:
                        extra["放置家产进行镇宅.jpg"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    _green_set = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32")
                    _has_green = False
                    if get_color(reviewer_name, idx, 6) and get_color(reviewer_name, idx, 6).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 7) and get_color(reviewer_name, idx, 7).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 8) and get_color(reviewer_name, idx, 8).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 9) and get_color(reviewer_name, idx, 9).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 10) and get_color(reviewer_name, idx, 10).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 11) and get_color(reviewer_name, idx, 11).upper() in _green_set: _has_green = True
                    if get_color(reviewer_name, idx, 30) and get_color(reviewer_name, idx, 30).upper() in _green_set: _has_green = True
                    if _has_green:
                        overall = "🌿草票 " + overall if overall else "🌿草票"
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("F组仅日语（by ld）")
def parse_F组仅日语_by_ld(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 0)
    for idx in range(1, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[感想]\n" + val)
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["（自己很菜所以不具体评，只是打出来想说的话，虽然评得很慢，但可能就一两个字"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("KalonTonics AF")
def parse_KalonTonics_AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("krvspt")
def parse_krvspt(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["投票"] = val
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 12:
            song_id = clean_str(row[11]).replace(" ", "")
            song_name = clean_str(row[12])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 19 < len(row):
                    val = clean_str(row[19])
                    color = get_color(reviewer_name, idx, 19)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["投票"] = val
                if 20 < len(row):
                    val = clean_str(row[20])
                    color = get_color(reviewer_name, idx, 20)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 3
        if len(row) > 24:
            song_id = clean_str(row[23]).replace(" ", "")
            song_name = clean_str(row[24])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 25 < len(row):
                    val = clean_str(row[25])
                    color = get_color(reviewer_name, idx, 25)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 26 < len(row):
                    val = clean_str(row[26])
                    color = get_color(reviewer_name, idx, 26)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 27 < len(row):
                    val = clean_str(row[27])
                    color = get_color(reviewer_name, idx, 27)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 28 < len(row):
                    val = clean_str(row[28])
                    color = get_color(reviewer_name, idx, 28)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 29 < len(row):
                    val = clean_str(row[29])
                    color = get_color(reviewer_name, idx, 29)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 30 < len(row):
                    val = clean_str(row[30])
                    color = get_color(reviewer_name, idx, 30)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["投票"] = val
                if 31 < len(row):
                    val = clean_str(row[31])
                    color = get_color(reviewer_name, idx, 31)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 32 < len(row):
                    val = clean_str(row[32])
                    color = get_color(reviewer_name, idx, 32)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("sm乱打-AC")
def parse_sm乱打_AC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("sm乱打-SC")
def parse_sm乱打_SC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("哈弗茨~ACAFSC")
def parse_哈弗茨_ACAFSC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["20s印象（B以下我直接不听了）"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 12:
            song_id = clean_str(row[11]).replace(" ", "")
            song_name = clean_str(row[12])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["20s印象（B以下我直接不听了）"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 19 < len(row):
                    val = clean_str(row[19])
                    color = get_color(reviewer_name, idx, 19)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 20 < len(row):
                    val = clean_str(row[20])
                    color = get_color(reviewer_name, idx, 20)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("JFLACSCAAF")
def parse_JFLACSCAAF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["投票"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["二轮"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[评价]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 7:
            song_id = clean_str(row[6]).replace(" ", "")
            song_name = clean_str(row[7])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["20s"] = val
                if 9 < len(row):
                    val = clean_str(row[9])
                    color = get_color(reviewer_name, idx, 9)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["一轮"] = val
                if 10 < len(row):
                    val = clean_str(row[10])
                    color = get_color(reviewer_name, idx, 10)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["tier"] = val
                if 11 < len(row):
                    val = clean_str(row[11])
                    color = get_color(reviewer_name, idx, 11)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[评价]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 3
        if len(row) > 15:
            song_id = clean_str(row[14]).replace(" ", "")
            song_name = clean_str(row[15])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["打分"] = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["序次"] = val
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[补充评价]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("hs sc")
def parse_hs_sc(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 6)
    for idx in range(7, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("正言ACSC")
def parse_正言ACSC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 10:
            song_id = clean_str(row[9]).replace(" ", "")
            song_name = clean_str(row[10])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 11 < len(row):
                    val = clean_str(row[11])
                    color = get_color(reviewer_name, idx, 11)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("星空ACSC")
def parse_星空ACSC(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("蓝婉111")
def parse_蓝婉111(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 0)
    for idx in range(1, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["总"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["草"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("KATIKA评AF")
def parse_KATIKA评AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        audience["聊天"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
        # Block 1
        if len(row) > 12:
            song_id = clean_str(row[11]).replace(" ", "")
            song_name = clean_str(row[12])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 16 < len(row):
                    val = clean_str(row[16])
                    color = get_color(reviewer_name, idx, 16)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 17 < len(row):
                    val = clean_str(row[17])
                    color = get_color(reviewer_name, idx, 17)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 18 < len(row):
                    val = clean_str(row[18])
                    color = get_color(reviewer_name, idx, 18)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 19 < len(row):
                    val = clean_str(row[19])
                    color = get_color(reviewer_name, idx, 19)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        audience["聊天"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("乱评")
def parse_乱评(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 0)
    for idx in range(1, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 4:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[4])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 1 < len(row):
                    val = clean_str(row[1])
                    color = get_color(reviewer_name, idx, 1)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["24/31"] = val
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["19/6"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["草"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["二筛投票（听不完了，写个python抽奖脚本QAQ）"] = val
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("李逵乱评- SF")
def parse_李逵乱评_SF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("Periberry 下半A组")
def parse_Periberry_下半A组(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 3)
    for idx in range(4, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["给票"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[评语]\n" + val)
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[我还想说啥来着]\n" + val)
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("临江 下半场SC钝评")
def parse_临江_下半场SC钝评(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 0)
    for idx in range(1, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["操作"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["技巧"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["解析"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["潜力"] = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[钝评评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("千千潜秋乱品.acf.sc")
def parse_千千潜秋乱品_acf_sc(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 1)
    for idx in range(2, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 11:
            song_id = clean_str(row[10]).replace(" ", "")
            song_name = clean_str(row[11])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 12 < len(row):
                    val = clean_str(row[12])
                    color = get_color(reviewer_name, idx, 12)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件技巧"] = val
                if 13 < len(row):
                    val = clean_str(row[13])
                    color = get_color(reviewer_name, idx, 13)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["主观听感"] = val
                if 14 < len(row):
                    val = clean_str(row[14])
                    color = get_color(reviewer_name, idx, 14)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        extra["?"] = val
                if 15 < len(row):
                    val = clean_str(row[15])
                    color = get_color(reviewer_name, idx, 15)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[乱品评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("imi下半场sf锐评极速版")
def parse_imi下半场sf锐评极速版(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[说明：因为没啥时间，极速版锐评，是在车上评的，不一定能评完，听哪评哪，很主观的评价。评价等级C+～S]\n" + val)
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("备份P SF乱评")
def parse_备份P_SF乱评(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        # Block 0
        if len(row) > 1:
            song_id = clean_str(row[0]).replace(" ", "")
            song_name = clean_str(row[1])
            # Skip section dividers like AC1, AF2, SC1, SF2
            import re as _re
            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{2}[12]", song_id))
            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:
                dimensions = {}
                overall = ""
                comments_list = []
                audience = {}
                extra = {}
                if 2 < len(row):
                    val = clean_str(row[2])
                    color = get_color(reviewer_name, idx, 2)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["软件操作使用"] = val
                if 3 < len(row):
                    val = clean_str(row[3])
                    color = get_color(reviewer_name, idx, 3)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["艺术表达技巧"] = val
                if 4 < len(row):
                    val = clean_str(row[4])
                    color = get_color(reviewer_name, idx, 4)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["歌声解析能力"] = val
                if 5 < len(row):
                    val = clean_str(row[5])
                    color = get_color(reviewer_name, idx, 5)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        dimensions["发展潜力"] = val
                if 6 < len(row):
                    val = clean_str(row[6])
                    color = get_color(reviewer_name, idx, 6)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        overall = val
                if 7 < len(row):
                    val = clean_str(row[7])
                    color = get_color(reviewer_name, idx, 7)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[瑞平评语]\n" + val)
                if 8 < len(row):
                    val = clean_str(row[8])
                    color = get_color(reviewer_name, idx, 8)
                    if color and val:
                        color_note = ""
                        c_up = color.upper()
                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"
                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"
                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"
                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"
                        if color_note: val = val + color_note
                    if val:
                        comments_list.append("[观众留言]\n" + val)
                has_content = bool(dimensions or overall or comments_list or audience or extra)
                # check template placeholders
                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:
                    has_content = False
                if "".join(dimensions.values()) == "AASS":
                    has_content = False
                _dim_vals = "".join(dimensions.values()).upper()
                _aud_str = str(audience.get("观众留言", "")).strip()
                _ghost_texts = {"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}
                _has_real_text = False
                for _t in comments_list + [_aud_str]:
                    if not _t: continue
                    _c = _t.split("]\n")[-1] if "]\n" in _t else _t
                    if _c.strip() not in _ghost_texts: _has_real_text = True
                if (comments_list or _aud_str) and not _has_real_text:
                    has_content = False
                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:
                    has_content = False
                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:
                    has_content = False
                if has_content:
                    assessments.append(ReviewerAssessment(
                        reviewer_name=reviewer_name,
                        song_id=song_id,
                        song_name=clean_newline(song_name),
                        dimension_scores=dimensions,
                        overall_score=overall,
                        comments=clean_newline("\n\n".join(comments_list)),
                        audience_comments=audience,
                        extra_fields=extra
                    ))
    return assessments, decl

@register_parser("品鉴下半A组和SF")
def parse_品鉴下半A组和SF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 2)
    _green_set = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32","FFBFE9d4")
    _red_set   = ("FFFF0000","FFE6615D","FFDE3C36","FFE74025","FFFF9C99")
    _yellow_set= ("FFFFC000","FFFFFF00","FFF88825","FFF5C401","FFF4C243","FFA38200")
    _blue_set  = ("FF00A3F5","FF2972F4","FFBDD7EE","FF1450B8","FF1274A5")
    import re as _re
    # Section headers are rows where col0 is AC2/AF2/SF2 or col0/col1 contain 编号/曲名
    # Iterate reading current active col-name map (changes per section header)
    # Fixed column map for all sections: 0=id,1=name,2=20s,3=调声A,4=调声B,5=混音,6=总评,7=总评转分,8=瑞平评语
    # Cols 11=等级,12=20s,13=总评 are reviewer ranking data → extra_fields
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        if len(row) < 2: continue
        song_id = clean_str(row[0]).replace(" ","")
        # Skip section labels, headers, and dividers
        if not song_id or _re.fullmatch(r"[A-Za-z]{2}[12]", song_id): continue
        if any(x in song_id for x in ("上半","下半","待定","评委","（","(")): continue
        if len(song_id) < 4: continue
        song_name = clean_str(row[1]) if len(row)>1 else ""
        dimensions = {}
        overall = ""
        comments_list = []
        extra = {}
        if len(row)>2:
            _v=clean_str(row[2])
            if _v: dimensions["20s"]=_v
        if len(row)>3:
            _v=clean_str(row[3])
            if _v: dimensions["调声A"]=_v
        if len(row)>4:
            _v=clean_str(row[4])
            if _v: dimensions["调声B"]=_v
        if len(row)>5:
            _v=clean_str(row[5])
            if _v: dimensions["混音"]=_v
        if len(row)>7:
            _v=clean_str(row[7])
            if _v: dimensions["总评转分"]=_v
        if len(row)>6:
            _ov=clean_str(row[6])
            if _ov: overall=_ov
        if len(row)>8:
            _cm=clean_str(row[8])
            if _cm: comments_list.append(_cm)
        if len(row)>11:
            _xv=clean_str(row[11])
            if _xv: extra["评委排级"]=_xv
        if len(row)>12:
            _xv=clean_str(row[12])
            if _xv: extra["评委20s排名"]=_xv
        if len(row)>13:
            _xv=clean_str(row[13])
            if _xv: extra["评委总评排名"]=_xv
        _col=get_color(reviewer_name, idx, 2)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[0] if 0<len(dimensions) else None
            pass  # green noted but no extra label needed here
        _col=get_color(reviewer_name, idx, 3)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[1] if 1<len(dimensions) else None
            pass  # green noted but no extra label needed here
        _col=get_color(reviewer_name, idx, 4)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[2] if 2<len(dimensions) else None
            pass  # green noted but no extra label needed here
        _col=get_color(reviewer_name, idx, 5)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[3] if 3<len(dimensions) else None
            pass  # green noted but no extra label needed here
        _col=get_color(reviewer_name, idx, 6)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[4] if 4<len(dimensions) else None
            pass  # green noted but no extra label needed here
        _col=get_color(reviewer_name, idx, 7)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[5] if 5<len(dimensions) else None
            pass  # green noted but no extra label needed here
        _col=get_color(reviewer_name, idx, 8)
        if _col and _col.upper() in _green_set:
            _k=list(dimensions.keys())[6] if 6<len(dimensions) else None
            pass  # green noted but no extra label needed here
        has_content = bool(dimensions or overall or comments_list or extra)
        _dv = "".join(dimensions.values()).upper()
        if song_id == "AC1001" and _dv == "DDSS" and overall.upper() == "B" and not comments_list: has_content=False
        if song_id == "AC1002" and _dv == "ASSB" and overall.upper() == "A+" and not comments_list: has_content=False
        if has_content:
            assessments.append(ReviewerAssessment(
                reviewer_name=reviewer_name,
                song_id=song_id,
                song_name=clean_newline(song_name),
                dimension_scores=dimensions,
                overall_score=overall,
                comments=clean_newline("\n\n".join(comments_list)),
                audience_comments={},
                extra_fields=extra
            ))
    return assessments, decl

@register_parser("下半S组纯夸感想")
def parse_下半S组纯夸感想(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    decl = extract_declaration(df, 4)
    _green_caopiao = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32")
    import re as _re
    # Two sections detected by header rows:
    # SF section: header at row 4, col2="草票"
    # SC section: header at row 51, col2="啥评？"
    _section = "SF"  # start in SF section
    for idx in range(5, len(df)):
        row = df.iloc[idx].values
        if len(row) < 2: continue
        song_id = clean_str(row[0]).replace(" ","")
        # Detect section switch (SC2 label or SC section header)
        if song_id == "SC2" or (song_id == "编号" and len(row)>2 and "啥评" in str(row[2])):
            _section = "SC"
            continue
        # Skip section dividers and empty rows
        if not song_id or _re.fullmatch(r"[A-Za-z]{2}[12]", song_id): continue
        if any(x in song_id for x in ("上半","下半","待定","评委","（","(")): continue
        if len(song_id) < 4: continue
        song_name = clean_str(row[1]) if len(row)>1 else ""
        comments_list = []
        audience = {}
        extra = {}
        overall = ""
        # col2 handling depends on section
        if len(row)>2:
            _c2=clean_str(row[2])
            _color2=get_color(reviewer_name, idx, 2)
            if _section == "SF":
                # Green = 草票, also count text value as part of 草票 note
                _is_green = _color2 and _color2.upper() in _green_caopiao
                if _is_green:
                    overall = "🌿草票" + (" " + _c2 if _c2 else "")
            else:  # SC section
                # "啥评？" column - just a reaction word, put in extra
                if _c2: extra["啥评"] = _c2
        # col3: 感想 (main comment)
        if len(row)>3:
            _c3=clean_str(row[3])
            if _c3: comments_list.append(_c3)
        # col4-7: overflow/additional comments
        for _oc in range(4, min(8, len(row))):
            _ov=clean_str(row[_oc])
            if _ov: comments_list.append(_ov)
        # col8: 观众留言
        if len(row)>8:
            _c8=clean_str(row[8])
            if _c8: audience["观众留言"]=_c8
        has_content = bool(overall or comments_list or audience or extra)
        if has_content:
            assessments.append(ReviewerAssessment(
                reviewer_name=reviewer_name,
                song_id=song_id,
                song_name=clean_newline(song_name),
                dimension_scores={},
                overall_score=overall,
                comments=clean_newline("\n\n".join(comments_list)),
                audience_comments=audience,
                extra_fields=extra
            ))
    return assessments, decl

@register_parser("X-Ray AF")
def parse_X_Ray_AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:
    assessments = []
    import re as _re
    # Declaration is Row 1 (large merged cell with voting strategy)
    decl_parts = []
    for r in [1, 2]:
        if r < len(df):
            row_vals = [clean_str(x) for x in df.iloc[r].values if clean_str(x)]
            if row_vals:
                joined = " | ".join(row_vals)
                if joined != "下半场" and len(joined) > 5:
                    decl_parts.append(joined)
    decl = "\n".join(decl_parts)
    # Data starts at row 3, cols: 0=songID, 1=曲名, 2=投票, 3=评价, 4=观众留言
    for idx in range(3, len(df)):
        row = df.iloc[idx].values
        if len(row) < 2: continue
        song_id = clean_str(row[0]).replace(" ","")
        if not song_id or _re.fullmatch(r"[A-Za-z]{2}[12]", song_id): continue
        if any(x in song_id for x in ("上半","下半","待定","评委","（","(")): continue
        if len(song_id) < 4: continue
        song_name = clean_str(row[1]) if len(row)>1 else ""
        overall = ""
        comments_list = []
        audience = {}
        extra = {}
        # Col 2: 初赛投票
        if len(row)>2:
            _vote1 = clean_str(row[2])
            if _vote1: extra["初赛投票"] = _vote1
        # Col 3: 决赛投票
        if len(row)>3:
            _vote2 = clean_str(row[3])
            if _vote2: extra["决赛投票"] = _vote2
        # Col 4: 评价 (main comment)
        if len(row)>4:
            _cm = clean_str(row[4])
            if _cm: comments_list.append(_cm)
        # Col 5: 观众留言
        if len(row)>5:
            _aud = clean_str(row[5])
            if _aud: audience["观众留言"] = _aud
        # Additional overflow columns (Col 6 - 9)
        for _oc in range(6, min(10, len(row))):
            _ov = clean_str(row[_oc])
            if _ov: comments_list.append(_ov)
        has_content = bool(comments_list or audience or extra)
        if has_content:
            assessments.append(ReviewerAssessment(
                reviewer_name=reviewer_name,
                song_id=song_id,
                song_name=clean_newline(song_name),
                dimension_scores={},
                overall_score=overall,
                comments=clean_newline("\n\n".join(comments_list)),
                audience_comments=audience,
                extra_fields=extra
            ))
    return assessments, decl
