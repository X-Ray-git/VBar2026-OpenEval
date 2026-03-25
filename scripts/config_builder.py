import json

def build_configs():
    with open("data/excel_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    configs = {}
    for sheet, rows in data.items():
        valid_rows = [row for row in rows if any(str(cell).strip() not in ('nan', '') for cell in row)]
        if not valid_rows:
            continue
            
        header_row_idx = 0
        headers = []
        for r_idx, row in enumerate(valid_rows[:6]):
            row_strs = [str(x).strip() for x in row]
            if any('编号' in x or '曲名' in x for x in row_strs):
                header_row_idx = r_idx
                headers = row_strs
                break
                
        # Some sheets lack headers like 'X-Ray AF'
        if header_row_idx == 0 and not headers:
            headers = [str(x).strip() for x in valid_rows[0]]
            # hardcode for X-Ray
            if "X-Ray" in sheet:
                # Based on previous dump, '曲名' is at index 1 in row 0
                pass

        id_col = -1
        name_col = -1
        score_cols = {}
        overall_col = -1
        comment_cols = {}
        audience_cols = {}
        
        for i, h in enumerate(headers):
            h_lower = h.lower()
            if not h or h_lower == 'nan':
                continue
            if '编号' in h_lower or '序号' in h_lower:
                id_col = i
            elif '曲名' in h_lower or '曲目' in h_lower or '歌名' in h_lower:
                name_col = i
            elif '总评' in h_lower and '转分' not in h_lower:
                overall_col = i
            elif any(k in h_lower for k in ['评语', '瑞平', '乱品', '钝评', '简评', '留言', '说啥', '说明', '评价', '感想', '感想等']):
                comment_cols[h] = i
            elif any(k in h_lower for k in ['观众', '互动', '聊天']):
                audience_cols[h] = i
            elif any(k in h_lower for k in ['操作', '技巧', '解析', '潜力', '20s', '调声', '混音', '投票', '给票', '主观听感']):
                score_cols[h] = i
                
        # Fix X-Ray
        if "X-Ray" in sheet:
            header_row_idx = 0
            id_col = 0 # implicit based on earlier rows
            name_col = 1
            score_cols = {"投票": 2}
            comment_cols = {"评价": 3}
            audience_cols = {"观众留言": 4}
            # Note: in X-Ray row 0 is the header, but ID is empty header. We'll handle it during parse.
            
        configs[sheet] = {
            "header_row_idx": header_row_idx,
            "id_col": id_col,
            "name_col": name_col,
            "score_cols": score_cols,
            "overall_col": overall_col,
            "comment_cols": comment_cols,
            "audience_cols": audience_cols
        }
        
    with open("data/sheet_configs.json", "w", encoding="utf-8") as f:
        json.dump(configs, f, ensure_ascii=False, indent=4)
        
    print("Configs generated to sheet_configs.json")

if __name__ == "__main__":
    build_configs()
