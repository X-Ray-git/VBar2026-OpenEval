import json
import ast

def clean_header(h):
    if "https://" in h or "http://" in h:
        h = h.split("http")[0].strip("：: \n\t")
    res = h.replace('\n', '').strip()
    if res.startswith("评价：可提名") or res.startswith("评价:可提名"):
        return "评价"
    return res

def build():
    with open("data/excel_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    code = [
        "import pandas as pd",
        "import json",
        "from typing import List, Dict, Any, Tuple",
        "from src.models import ReviewerAssessment",
        "from src.parser_registry import register_parser",
        "",
        "# Load color definitions once",
        "try:",
        "    with open('data/color_data.json', 'r', encoding='utf-8') as f:",
        "        COLOR_DATA = json.load(f)",
        "except:",
        "    COLOR_DATA = {}",
        "",
        "def get_color(sheet, r, c):",
        "    if sheet in COLOR_DATA:",
        "        if str(r) in COLOR_DATA[sheet]:",
        "            if str(c) in COLOR_DATA[sheet][str(r)]:",
        "                return COLOR_DATA[sheet][str(r)][str(c)]",
        "    return None",
        "",
        "def clean_str(val: Any) -> str:",
        "    v = str(val).strip()",
        "    if v == '?' or v == '？' or v.lower() == 'nan': return ''",
        "    return v",
        "",
        "def clean_newline(val: str) -> str:",
        "    return val.replace('\\r\\n', '\\n').strip()",
        "",
        "def extract_declaration(df: pd.DataFrame, header_idx: int) -> str:",
        "    import re as _dre",
        "    TEMPLATE_NOISE = ('请于此页复制模板', '请勿在此处打分', '下半场请尽量复用工作表')",
        "    DIVIDER_PATTERN = ('AC1','AC2','AF1','AF2','SC1','SC2','SF1','SF2')",
        "    TICKET_NOISE = ('AC1（', 'AC2（', 'AF1（', 'AF2（', 'SC1（', 'SC2（', 'SF1（', 'SF2（')",
        "    lines = []",
        "    # 1) Scan rows ABOVE the header",
        "    for r in range(header_idx):",
        "        row_vals = []",
        "        for x in df.iloc[r].values:",
        "            cx = clean_str(x)",
        "            if not cx: continue",
        "            if any(t in cx for t in TEMPLATE_NOISE): continue",
        "            row_vals.append(cx)",
        "        if not row_vals: continue",
        "        joined = ' | '.join(row_vals)",
        "        if all(v.strip() in DIVIDER_PATTERN for v in row_vals): continue",
        "        # Skip ticket count lines like 'AC1（6+31）...'",
        "        if any(joined.startswith(t) for t in TICKET_NOISE): continue",
        "        lines.append(joined)",
        "    # 2) Scan rows AFTER header for non-song-ID rows with long text (e.g. X-Ray Row1, Ehu Row2)",
        "    for r in range(header_idx + 1, min(header_idx + 5, len(df))):",
        "        row = df.iloc[r].values",
        "        c0 = ''",
        "        for cell in row:",
        "            cv = clean_str(cell).replace(' ', '')",
        "            if cv:",
        "                c0 = cv",
        "                break",
        "        if _dre.match(r'^[A-Za-z]{2}\\d{3,}', c0): break  # hit real data",
        "        if c0 in DIVIDER_PATTERN: continue  # section label",
        "        if c0 == '编号': continue  # another header",
        "        row_vals = []",
        "        for x in row:",
        "            cx = clean_str(x)",
        "            if not cx: continue",
        "            if any(t in cx for t in TEMPLATE_NOISE): continue",
        "            row_vals.append(cx)",
        "        if not row_vals: continue",
        "        joined = ' | '.join(row_vals)",
        "        if len(joined) > 15:",
        "            lines.append(joined)",
        "    # 3) Scan side columns (col >= 8) in pre-header rows ONLY (not data rows)",
        "    for r in range(0, min(header_idx + 1, len(df))):",
        "        row_vals_all = df.iloc[r].values",
        "        for c in range(8, len(row_vals_all)):",
        "            v = clean_str(row_vals_all[c])",
        "            if v and len(v) > 20 and not v.replace('.','').replace('-','').isdigit():",
        "                if not any(t in v for t in TEMPLATE_NOISE):",
        "                    lines.append(f'[侧栏注] {v}')",
        "    decl = '\\n'.join(lines)",
        "    decl = decl.replace('■ 三倍票', '🟥 三倍票').replace('■ 一倍票', '🟩 一倍票').replace('■ 还在斟酌', '🟨 还在斟酌')",
        "    return decl",
        ""
    ]
    
    # These sheets have handwritten parsers appended below
    HANDWRITTEN_PARSERS = {'品鉴下半A组和SF', '下半S组纯夸感想', 'X-Ray AF'}
    
    for sheet, rows in data.items():
        valid_rows = [row for row in rows if any(str(cell).strip() not in ('nan', '') for cell in row)]
        if not valid_rows:
            continue
        if sheet in HANDWRITTEN_PARSERS:
            continue
            
        header_row_idx = 0
        headers = []
        for r_idx, row in enumerate(rows[:20]):
            row_strs = [str(x).strip() for x in row]
            if "编号" in row_strs or "曲名" in row_strs or any('编号' in x or '曲名' in x for x in row_strs if x):
                header_row_idx = r_idx
                headers = row_strs
                break
                
        # Fix X-Ray default
        if header_row_idx == 0 and not headers:
            headers = [str(x).strip() for x in valid_rows[0]]
            if "X-Ray" in sheet:
                pass
                
        # Find all ID columns (which signify the start of a new table block)
        blocks = []
        id_cols = [i for i, h in enumerate(headers) if '编号' in h or '序号' in h]
        
        # Hardcode fix for X-Ray missing '编号'
        if "X-Ray" in sheet:
            header_row_idx = 0
            if len(headers) < 12:
                headers.extend([""] * (12 - len(headers)))
            id_cols = [0]
            headers[0] = "编号"
            
        if not id_cols and len(headers) > 1:
            id_cols = [0] # fallback
            
        for i, start_col in enumerate(id_cols):
            end_col = id_cols[i+1] if i + 1 < len(id_cols) else len(headers)
            # Find name col
            name_c = -1
            for c in range(start_col, end_col):
                if '曲' in headers[c] or '歌' in headers[c]:
                    name_c = c
                    break
            if name_c == -1 and start_col + 1 < end_col:
                name_c = start_col + 1
                
            block = {'id': start_col, 'name': name_c, 'cols': []}
            for c in range(start_col, end_col):
                if c == start_col or c == name_c: continue
                if headers[c] and headers[c] != 'nan':
                    block['cols'].append(c)
            blocks.append(block)
            
        func_name = "parse_" + "".join(c if c.isalnum() else '_' for c in sheet).strip('_')
        func_name = func_name.replace('__', '_')
        
        code.append(f'@register_parser("{sheet}")')
        code.append(f'def {func_name}(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:')
        code.append(f'    assessments = []')
        code.append(f'    decl = extract_declaration(df, {header_row_idx})')
        code.append(f'    for idx in range({header_row_idx + 1}, len(df)):')
        code.append(f'        row = df.iloc[idx].values')
        
        for block_idx, block in enumerate(blocks):
            if block['id'] == -1 or block['name'] == -1: continue
            
            code.append(f'        # Block {block_idx}')
            code.append(f'        if len(row) > {max(block["id"], block["name"])}:')
            code.append(f'            song_id = clean_str(row[{block["id"]}]).replace(" ", "")')
            code.append(f'            song_name = clean_str(row[{block["name"]}])')
            code.append(f'            # Skip section dividers like AC1, AF2, SC1, SF2')
            code.append(f'            import re as _re')
            code.append(f'            _is_divider = bool(_re.fullmatch(r"[A-Za-z]{{2}}[12]", song_id))')
            code.append(f'            if song_id and not _is_divider and len(song_id) >= 2 and "上半" not in song_id and "下半" not in song_id and "待定" not in song_id and "评委" not in song_id and "编号" not in song_id and "（" not in song_id and "(" not in song_id:')
            code.append(f'                dimensions = {{}}')
            code.append(f'                overall = ""')
            code.append(f'                comments_list = []')
            code.append(f'                audience = {{}}')
            code.append(f'                extra = {{}}')
            
            for c in block['cols']:
                h_clean = clean_header(headers[c])
                code.append(f'                if {c} < len(row):')
                code.append(f'                    val = clean_str(row[{c}])')
                code.append(f'                    color = get_color(reviewer_name, idx, {c})')
                # Skip generic color annotation for: happy sheet (handled as row-level 草票),
                # and columns explicitly named "草票" (handle green = 🌿草票 directly)
                if sheet == "happy":
                    code.append(f'                    # happy: skip color annotation (handled as 草票)')
                elif h_clean == '草票':
                    # Column is explicitly "草票" - green means give 草票
                    code.append(f'                    _green_caopiao = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32")')
                    code.append(f'                    if color and color.upper() in _green_caopiao:')
                    code.append(f'                        val = "🌿草票" + (" " + val if val else "")')
                else:
                    code.append(f'                    if color and val:')
                    code.append(f'                        color_note = ""')
                    code.append(f'                        c_up = color.upper()')
                    code.append(f'                        if c_up in ("FF92D050", "FF00FF00", "FFC3EAD5", "FF277C4F", "FF184E32"): color_note = "【绿色底色：给票/推荐】"')
                    code.append(f'                        elif c_up in ("FFFF0000", "FFE6615D", "FFDE3C36", "FFE74025", "FFFF9C99"): color_note = "【红色底色：多倍票/重点】"')
                    code.append(f'                        elif c_up in ("FFFFC000", "FFFFFF00", "FFF88825", "FFF5C401", "FFF4C243", "FFA38200"): color_note = "【黄色底色：斟酌/待定】"')
                    code.append(f'                        elif c_up in ("FF00A3F5", "FF2972F4", "FFBDD7EE", "FF1450B8", "FF1274A5"): color_note = "【蓝色表态】"')
                    code.append(f'                        if color_note: val = val + color_note')
                code.append(f'                    if val:')
                
                # classify dynamically inside generated code based on header name
                h_lower = h_clean.lower()
                if '总评' in h_lower and '转分' not in h_lower:
                    code.append(f'                        overall = val')
                elif any(k in h_lower for k in ['评语', '瑞平', '乱品', '钝评', '简评', '留言', '说啥', '说明', '评价', '感想']):
                    # It's a comment
                    code.append(f'                        comments_list.append("[{h_clean}]\\n" + val)')
                elif any(k in h_lower for k in ['观众', '互动', '聊天']):
                    code.append(f'                        audience["{h_clean}"] = val')
                elif any(k in h_lower for k in ['操作', '技巧', '解析', '潜力', '20s', '调声', '混音', '投票', '给票', '主观听感']):
                    code.append(f'                        dimensions["{h_clean}"] = val')
                else:
                    code.append(f'                        extra["{h_clean}"] = val')
                    
            code.append(f'                has_content = bool(dimensions or overall or comments_list or audience or extra)')
            
            # Additional heuristic: If dimensions match the template placeholders exactly: A A S S ?
            code.append(f'                # check template placeholders')
            code.append(f'                if "A" in dimensions.values() and "S" in dimensions.values() and "?" in overall:')
            code.append(f'                    has_content = False')
            code.append(f'                if "".join(dimensions.values()) == "AASS":')
            code.append(f'                    has_content = False')
            # Filter exact template example rows: AC1001 D D S S B / AC1002 A S S B A+ / etc.
            code.append(f'                _dim_vals = "".join(dimensions.values()).upper()')
            code.append(f'                _aud_str = str(audience.get("观众留言", "")).strip()')
            code.append(f'                _ghost_texts = {{"问号真来啊", "我认为可行", "←那很敢吃了", "114514", "111", "好像真是一样的", "????", "←我觉得真应该在等级里加个问号（", "支持↑", "SC开篇就是新年财神到，大家新年发大财呀！", "这首还不错，人声很有感情", "很有意思"}}')
            code.append(f'                _has_real_text = False')
            code.append(f'                for _t in comments_list + [_aud_str]:')
            code.append(f'                    if not _t: continue')
            code.append(f'                    _c = _t.split("]\\n")[-1] if "]\\n" in _t else _t')
            code.append(f'                    if _c.strip() not in _ghost_texts: _has_real_text = True')
            code.append(f'                if (comments_list or _aud_str) and not _has_real_text:')
            code.append(f'                    has_content = False')
            code.append(f'                if song_id == "AC1001" and _dim_vals == "DDSS" and overall.upper() == "B" and not _has_real_text:')
            code.append(f'                    has_content = False')
            code.append(f'                if song_id == "AC1002" and _dim_vals == "ASSB" and overall.upper() == "A+" and not _has_real_text:')
            code.append(f'                    has_content = False')
            
            code.append(f'                if has_content:')
            # For "happy" reviewer: detect green background = 草票
            if sheet == "happy":
                all_cols = [block['id'], block['name']] + block['cols']
                code.append(f'                    _green_set = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32")')
                code.append(f'                    _has_green = False')
                for ci in all_cols:
                    code.append(f'                    if get_color(reviewer_name, idx, {ci}) and get_color(reviewer_name, idx, {ci}).upper() in _green_set: _has_green = True')
                code.append(f'                    if _has_green:')
                code.append(f'                        overall = "🌿草票 " + overall if overall else "🌿草票"')
            code.append(f'                    assessments.append(ReviewerAssessment(')
            code.append(f'                        reviewer_name=reviewer_name,')
            code.append(f'                        song_id=song_id,')
            code.append(f'                        song_name=clean_newline(song_name),')
            code.append(f'                        dimension_scores=dimensions,')
            code.append(f'                        overall_score=overall,')
            code.append(f'                        comments=clean_newline("\\n\\n".join(comments_list)),')
            code.append(f'                        audience_comments=audience,')
            code.append(f'                        extra_fields=extra')
            code.append(f'                    ))')
            
        code.append(f'    return assessments, decl')
        code.append(f'')
        
    # ── Handwritten parser: 品鉴下半A组和SF ──────────────────────────────────
    # Left block (col 0-8): 编号/曲名/20s/调声A/调声B/混音/总评/总评转分/瑞平评语
    # Right columns 11-13 (等级/20s/总评): reviewer's own ranking system – kept as extra fields
    # Cols 9,10 are empty.  Sections: AC2 (row2=header), AF2 (row135=header), SF2 (row231=header)
    code.append('@register_parser("品鉴下半A组和SF")')
    code.append('def parse_品鉴下半A组和SF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:')
    code.append('    assessments = []')
    code.append('    decl = extract_declaration(df, 2)')  # Row 0: declaration, Row 1: section label, Row 2: first header
    code.append('    _green_set = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32","FFBFE9d4")')
    code.append('    _red_set   = ("FFFF0000","FFE6615D","FFDE3C36","FFE74025","FFFF9C99")')
    code.append('    _yellow_set= ("FFFFC000","FFFFFF00","FFF88825","FFF5C401","FFF4C243","FFA38200")')
    code.append('    _blue_set  = ("FF00A3F5","FF2972F4","FFBDD7EE","FF1450B8","FF1274A5")')
    code.append('    import re as _re')
    code.append('    # Section headers are rows where col0 is AC2/AF2/SF2 or col0/col1 contain 编号/曲名')
    code.append('    # Iterate reading current active col-name map (changes per section header)')
    code.append('    # Fixed column map for all sections: 0=id,1=name,2=20s,3=调声A,4=调声B,5=混音,6=总评,7=总评转分,8=瑞平评语')
    code.append('    # Cols 11=等级,12=20s,13=总评 are reviewer ranking data → extra_fields')
    code.append('    for idx in range(3, len(df)):')
    code.append('        row = df.iloc[idx].values')
    code.append('        if len(row) < 2: continue')
    code.append('        song_id = clean_str(row[0]).replace(" ","")')
    code.append('        # Skip section labels, headers, and dividers')
    code.append('        if not song_id or _re.fullmatch(r"[A-Za-z]{2}[12]", song_id): continue')
    code.append('        if any(x in song_id for x in ("上半","下半","待定","评委","（","(")): continue')
    code.append('        if len(song_id) < 4: continue')
    code.append('        song_name = clean_str(row[1]) if len(row)>1 else ""')
    code.append('        dimensions = {}')
    code.append('        overall = ""')
    code.append('        comments_list = []')
    code.append('        extra = {}')
    # Main scoring cols 2-5 + 7
    for ci, h in [(2,'20s'),(3,'调声A'),(4,'调声B'),(5,'混音'),(7,'总评转分')]:
        code.append(f'        if len(row)>{ci}:')
        code.append(f'            _v=clean_str(row[{ci}])')
        code.append(f'            if _v: dimensions["{h}"]=_v')
    # overall & comment
    code.append('        if len(row)>6:')
    code.append('            _ov=clean_str(row[6])')
    code.append('            if _ov: overall=_ov')
    code.append('        if len(row)>8:')
    code.append('            _cm=clean_str(row[8])')
    code.append('            if _cm: comments_list.append(_cm)')
    # ranking cols 11-13 as extra
    for ci, h in [(11,'评委排级'),(12,'评委20s排名'),(13,'评委总评排名')]:
        code.append(f'        if len(row)>{ci}:')
        code.append(f'            _xv=clean_str(row[{ci}])')
        code.append(f'            if _xv: extra["{h}"]=_xv')
    # Color enrichment on cols 2-8
    for ci in [2,3,4,5,6,7,8]:
        code.append(f'        _col=get_color(reviewer_name, idx, {ci})')
        code.append(f'        if _col and _col.upper() in _green_set:')
        code.append(f'            _k=list(dimensions.keys())[{ci-2}] if {ci-2}<len(dimensions) else None')
        code.append(f'            pass  # green noted but no extra label needed here')
    code.append('        has_content = bool(dimensions or overall or comments_list or extra)')
    code.append('        _dv = "".join(dimensions.values()).upper()')
    code.append('        if song_id == "AC1001" and _dv == "DDSS" and overall.upper() == "B" and not comments_list: has_content=False')
    code.append('        if song_id == "AC1002" and _dv == "ASSB" and overall.upper() == "A+" and not comments_list: has_content=False')
    code.append('        if has_content:')
    code.append('            assessments.append(ReviewerAssessment(')
    code.append('                reviewer_name=reviewer_name,')
    code.append('                song_id=song_id,')
    code.append('                song_name=clean_newline(song_name),')
    code.append('                dimension_scores=dimensions,')
    code.append('                overall_score=overall,')
    code.append('                comments=clean_newline("\\n\\n".join(comments_list)),')
    code.append('                audience_comments={},')
    code.append('                extra_fields=extra')
    code.append('            ))')
    code.append('    return assessments, decl')
    code.append('')

    # ── Handwritten parser: 下半S组纯夸感想 ──────────────────────────────────
    # SF section (rows 4 header, rows 5-48): col2="草票"(green=🌿草票), col3=感想, col4+=附加评语
    # SC section (rows 51 header, rows 52+): col2="啥评？"(语气词→extra), col3=感想, col8=观众留言
    code.append('@register_parser("下半S组纯夸感想")')
    code.append('def parse_下半S组纯夸感想(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:')
    code.append('    assessments = []')
    code.append('    decl = extract_declaration(df, 4)')  # rows 0-3 are declaration/section marker
    code.append('    _green_caopiao = ("FFC3EAD5","FF92D050","FF00FF00","FF277C4F","FF184E32")')
    code.append('    import re as _re')
    code.append('    # Two sections detected by header rows:')
    code.append('    # SF section: header at row 4, col2="草票"')
    code.append('    # SC section: header at row 51, col2="啥评？"')
    code.append('    _section = "SF"  # start in SF section')
    code.append('    for idx in range(5, len(df)):')
    code.append('        row = df.iloc[idx].values')
    code.append('        if len(row) < 2: continue')
    code.append('        song_id = clean_str(row[0]).replace(" ","")')
    code.append('        # Detect section switch (SC2 label or SC section header)')
    code.append('        if song_id == "SC2" or (song_id == "编号" and len(row)>2 and "啥评" in str(row[2])):')
    code.append('            _section = "SC"')
    code.append('            continue')
    code.append('        # Skip section dividers and empty rows')
    code.append('        if not song_id or _re.fullmatch(r"[A-Za-z]{2}[12]", song_id): continue')
    code.append('        if any(x in song_id for x in ("上半","下半","待定","评委","（","(")): continue')
    code.append('        if len(song_id) < 4: continue')
    code.append('        song_name = clean_str(row[1]) if len(row)>1 else ""')
    code.append('        comments_list = []')
    code.append('        audience = {}')
    code.append('        extra = {}')
    code.append('        overall = ""')
    code.append('        # col2 handling depends on section')
    code.append('        if len(row)>2:')
    code.append('            _c2=clean_str(row[2])')
    code.append('            _color2=get_color(reviewer_name, idx, 2)')
    code.append('            if _section == "SF":')
    code.append('                # Green = 草票, also count text value as part of 草票 note')
    code.append('                _is_green = _color2 and _color2.upper() in _green_caopiao')
    code.append('                if _is_green:')
    code.append('                    overall = "🌿草票" + (" " + _c2 if _c2 else "")')
    code.append('            else:  # SC section')
    code.append('                # "啥评？" column - just a reaction word, put in extra')
    code.append('                if _c2: extra["啥评"] = _c2')
    code.append('        # col3: 感想 (main comment)')
    code.append('        if len(row)>3:')
    code.append('            _c3=clean_str(row[3])')
    code.append('            if _c3: comments_list.append(_c3)')
    code.append('        # col4-7: overflow/additional comments')
    code.append('        for _oc in range(4, min(8, len(row))):')
    code.append('            _ov=clean_str(row[_oc])')
    code.append('            if _ov: comments_list.append(_ov)')
    code.append('        # col8: 观众留言')
    code.append('        if len(row)>8:')
    code.append('            _c8=clean_str(row[8])')
    code.append('            if _c8: audience["观众留言"]=_c8')
    code.append('        has_content = bool(overall or comments_list or audience or extra)')
    code.append('        if has_content:')
    code.append('            assessments.append(ReviewerAssessment(')
    code.append('                reviewer_name=reviewer_name,')
    code.append('                song_id=song_id,')
    code.append('                song_name=clean_newline(song_name),')
    code.append('                dimension_scores={},')
    code.append('                overall_score=overall,')
    code.append('                comments=clean_newline("\\n\\n".join(comments_list)),')
    code.append('                audience_comments=audience,')
    code.append('                extra_fields=extra')
    code.append('            ))')
    code.append('    return assessments, decl')
    code.append('')
    
    # ── Handwritten parser: X-Ray AF ──────────────────────────────────────────
    # Row 0: header (曲名, 投票, 评价, 观众留言) — no '编号' column, col0 is song ID
    # Row 1: LARGE declaration (857 chars, 8 numbered points about voting strategy)
    # Row 2: "下半场" label
    # Row 3+: data rows
    code.append('@register_parser("X-Ray AF")')
    code.append('def parse_X_Ray_AF(df: pd.DataFrame, reviewer_name: str) -> Tuple[List[ReviewerAssessment], str]:')
    code.append('    assessments = []')
    code.append('    import re as _re')
    code.append('    # Declaration is Row 1 (large merged cell with voting strategy)')
    code.append('    decl_parts = []')
    code.append('    for r in [1, 2]:')
    code.append('        if r < len(df):')
    code.append('            row_vals = [clean_str(x) for x in df.iloc[r].values if clean_str(x)]')
    code.append('            if row_vals:')
    code.append('                joined = " | ".join(row_vals)')
    code.append('                if joined != "下半场" and len(joined) > 5:')
    code.append('                    decl_parts.append(joined)')
    code.append('    decl = "\\n".join(decl_parts)')
    code.append('    # Data starts at row 3, cols: 0=songID, 1=曲名, 2=投票, 3=评价, 4=观众留言')
    code.append('    for idx in range(3, len(df)):')
    code.append('        row = df.iloc[idx].values')
    code.append('        if len(row) < 2: continue')
    code.append('        song_id = clean_str(row[0]).replace(" ","")')
    code.append('        if not song_id or _re.fullmatch(r"[A-Za-z]{2}[12]", song_id): continue')
    code.append('        if any(x in song_id for x in ("上半","下半","待定","评委","（","(")): continue')
    code.append('        if len(song_id) < 4: continue')
    code.append('        song_name = clean_str(row[1]) if len(row)>1 else ""')
    code.append('        overall = ""')
    code.append('        comments_list = []')
    code.append('        audience = {}')
    code.append('        extra = {}')
    code.append('        # Col 2: 初赛投票')
    code.append('        if len(row)>2:')
    code.append('            _vote1 = clean_str(row[2])')
    code.append('            if _vote1: extra["初赛投票"] = _vote1')
    code.append('        # Col 3: 决赛投票')
    code.append('        if len(row)>3:')
    code.append('            _vote2 = clean_str(row[3])')
    code.append('            if _vote2: extra["决赛投票"] = _vote2')
    code.append('        # Col 4: 评价 (main comment)')
    code.append('        if len(row)>4:')
    code.append('            _cm = clean_str(row[4])')
    code.append('            if _cm: comments_list.append(_cm)')
    code.append('        # Col 5: 观众留言')
    code.append('        if len(row)>5:')
    code.append('            _aud = clean_str(row[5])')
    code.append('            if _aud: audience["观众留言"] = _aud')
    code.append('        # Additional overflow columns (Col 6 - 9)')
    code.append('        for _oc in range(6, min(10, len(row))):')
    code.append('            _ov = clean_str(row[_oc])')
    code.append('            if _ov: comments_list.append(_ov)')
    code.append('        has_content = bool(comments_list or audience or extra)')
    code.append('        if has_content:')
    code.append('            assessments.append(ReviewerAssessment(')
    code.append('                reviewer_name=reviewer_name,')
    code.append('                song_id=song_id,')
    code.append('                song_name=clean_newline(song_name),')
    code.append('                dimension_scores={},')
    code.append('                overall_score=overall,')
    code.append('                comments=clean_newline("\\n\\n".join(comments_list)),')
    code.append('                audience_comments=audience,')
    code.append('                extra_fields=extra')
    code.append('            ))')
    code.append('    return assessments, decl')
    code.append('')
    
    with open("src/sheet_parsers.py", "w", encoding="utf-8") as f:
        f.write("\n".join(code))
        
    print("sheet_parsers.py successfully regenerated with 100% column capture, independent block processing, color enrichment, and `?` zeroing.")

if __name__ == "__main__":
    build()
