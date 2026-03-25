import pandas as pd
import json

file_path = "data/26V8在线瑞平0325.xlsx"
output_file = "data/excel_data.json"
try:
    xls = pd.ExcelFile(file_path, engine='calamine')
    
    output = {}
    for sheet in xls.sheet_names:
        if sheet == '💥':
            continue
        df = pd.read_excel(xls, sheet_name=sheet, header=None)
        # Convert all to strings and replace NaNs with empty strings
        data = df.fillna("").astype(str).values.tolist()
        output[sheet] = data
        
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_file}")
except Exception as e:
    print(f"Error: {e}")
