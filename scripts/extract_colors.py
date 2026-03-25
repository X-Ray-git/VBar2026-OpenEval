import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import json

def extract_colors(xlsx_path):
    color_data = {}
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        # 1. Map sheet names to target xml files
        wb_xml = ET.fromstring(z.read('xl/workbook.xml'))
        ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main', 
              'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
              
        rels_xml = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rel_map = {}
        for rel in rels_xml.findall('.//main:Relationship', namespaces=ns) + rels_xml.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
            rel_map[rel.attrib['Id']] = rel.attrib['Target']

        sheet_files = {}
        for sheet in wb_xml.findall('.//main:sheet', namespaces=ns):
            name = sheet.attrib['name']
            rId = sheet.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if not rId: continue
            target = rel_map.get(rId)
            if target:
                # Target is usually like 'worksheets/sheet1.xml'
                sheet_files[name] = f"xl/{target}"

        # 2. Parse styles.xml to get fill colors
        styles_xml = ET.fromstring(z.read('xl/styles.xml'))
        fills = styles_xml.findall('.//main:fill', namespaces=ns)
        fill_colors = []
        for fill in fills:
            pattern = fill.find('main:patternFill', namespaces=ns)
            color = None
            if pattern is not None:
                fg = pattern.find('main:fgColor', namespaces=ns)
                if fg is not None:
                    color = fg.attrib.get('rgb')
                    if not color:
                        color = fg.attrib.get('theme') # simplified, not exact
            fill_colors.append(color)

        cellXfs = styles_xml.find('.//main:cellXfs', namespaces=ns)
        xf_fills = []
        if cellXfs is not None:
            for xf in cellXfs.findall('main:xf', namespaces=ns):
                fillId = int(xf.attrib.get('fillId', 0))
                color = fill_colors[fillId] if fillId < len(fill_colors) else None
                xf_fills.append(color)

        # 3. Read each sheet to map cells to fill colors
        for sheet_name, xml_path in sheet_files.items():
            try:
                sheet_xml = ET.fromstring(z.read(xml_path))
            except KeyError:
                continue
                
            color_data[sheet_name] = {}
            for row in sheet_xml.findall('.//main:row', namespaces=ns):
                r_idx = int(row.attrib['r']) - 1 # 0-indexed
                color_data[sheet_name][r_idx] = {}
                for c in row.findall('main:c', namespaces=ns):
                    col_ref = c.attrib['r']
                    # Convert 'A1' to col index 0 format
                    col_str = ''.join(filter(str.isalpha, col_ref))
                    c_idx = 0
                    for char in col_str:
                        c_idx = c_idx * 26 + (ord(char) - ord('A') + 1)
                    c_idx -= 1 # 0-indexed
                    
                    s_idx = int(c.attrib.get('s', 0))
                    if s_idx < len(xf_fills) and xf_fills[s_idx]:
                        rgb = xf_fills[s_idx]
                        if rgb and rgb != '00000000' and rgb != 'FFFFFFFF': # Ignore clear/white
                            color_data[sheet_name][r_idx][c_idx] = rgb

    return color_data

if __name__ == '__main__':
    colors = extract_colors('data/26V8在线瑞平0325.xlsx')
    with open('data/color_data.json', 'w') as f:
        json.dump(colors, f)
    print("Color data extracted via low-level XML parsing.")
