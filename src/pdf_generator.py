import logging
from weasyprint import HTML, CSS
from src.models import EvaluationReport, Song
import re

logger = logging.getLogger(__name__)

def generate_pdf(report: EvaluationReport, output_path: str):
    logger.info("Generating HTML content for PDF...")
    
    # Sort songs naturally
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', s.song_id)]
                
    sorted_songs = sorted(report.songs.values(), key=natural_sort_key)
    
    html = [
        "<html><head><meta charset='utf-8'><style>",
        """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page);
                font-family: "PingFang SC", "Heiti SC", sans-serif;
                font-size: 9pt;
                color: #888;
            }
        }
        body {
            font-family: "PingFang SC", "Heiti SC", "Microsoft YaHei", sans-serif;
            color: #333;
            line-height: 1.6;
            background-color: #fcfcfc;
        }
        h1.title {
            text-align: center;
            font-size: 32pt;
            margin-top: 30vh;
            color: #1a1a1a;
            page-break-after: always;
        }
        .song-section {
            page-break-before: auto;
            page-break-inside: avoid;
            margin-bottom: 2rem;
            background: #fff;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #eaeaea;
        }
        h2.song-title {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
            margin-top: 0;
            font-size: 18pt;
        }
        .assessment {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px dashed #ddd;
        }
        .reviewer-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .reviewer-name {
            font-size: 13pt;
            font-weight: bold;
            color: #e67e22;
        }
        .overall-score {
            font-size: 14pt;
            font-weight: bold;
            color: #e74c3c;
            background: #fdf5f6;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
        }
        .dimensions {
            margin: 0.5rem 0;
            color: #555;
            font-size: 10.5pt;
        }
        .dimension-badge {
            display: inline-block;
            background: #edf2f7;
            padding: 0.1rem 0.5rem;
            border-radius: 3px;
            margin-right: 0.5rem;
            margin-bottom: 0.2rem;
            border: 1px solid #e2e8f0;
        }
        .comments {
            background: #f8f9fa;
            padding: 0.8rem;
            border-left: 4px solid #3498db;
            margin-top: 0.5rem;
            font-size: 11pt;
            white-space: pre-wrap;
        }
        .audience-info {
            background: #fff3cd;
            padding: 0.8rem;
            border-left: 4px solid #ffc107;
            margin-top: 0.5rem;
            font-size: 10.5pt;
        }
        .extra-info {
            background: #e2e3e5;
            padding: 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            font-size: 10pt;
            color: #383d41;
        }
        """,
        "</style></head><body>",
        "<h1 class='title'>26V8 在线瑞平评委评价汇编</h1>",
        "<div style='page-break-after: always;'>"
    ]
    
    # Add Reviewers Declarations Section
    if report.reviewers:
        html.append("<h2 class='song-title' style='text-align: center; margin-bottom: 2rem;'>评委全局声明与前言留言</h2>")
        for rev_name, info in report.reviewers.items():
            if info.declaration.strip():
                html.append("<div class='song-section' style='background: #fffafa; border-left: 4px solid #e74c3c;'>")
                html.append(f"<h3 style='color: #c0392b; margin-top: 0;'>📢 评委：{rev_name}</h3>")
                html.append(f"<div class='comments'>{info.declaration}</div>")
                html.append("</div>")
                
    html.append("</div>")
    
    def strip_color(text):
        if not text: return ""
        if not isinstance(text, str): text = str(text)
        return re.sub(r'\[(?:Color|Marked) [a-fA-F0-9]+\]\s*', '', text).strip()
    
    # Grouping by prefix + half
    # e.g. AC1xxx = AC上半场, AC2xxx = AC下半场
    groups = {}
    for song in sorted_songs:
        prefix = song.song_id[:2].upper()
        if prefix not in ('AC', 'AF', 'SC', 'SF'):
            prefix = 'Other'
            half = ''
        else:
            # 3rd char determines half: 1=上半场, 2=下半场
            third = song.song_id[2] if len(song.song_id) > 2 else '1'
            half = '上半场' if third == '1' else '下半场'
        key = (prefix, half)
        if key not in groups:
            groups[key] = []
        groups[key].append(song)
    
    group_order = [
        ('AC', '上半场'), ('AC', '下半场'),
        ('AF', '上半场'), ('AF', '下半场'),
        ('SC', '上半场'), ('SC', '下半场'),
        ('SF', '上半场'), ('SF', '下半场'),
    ]
    
    for (group_name, half) in group_order:
        group_songs = groups.get((group_name, half), [])
        if not group_songs:
            continue
            
        # Add Chapter Cover
        label = f"{group_name} {half}" if half else f"{group_name} 组"
        html.append(f"<div style='page-break-before: always; text-align: center; padding-top: 35%;'>")
        html.append(f"<h1 style='font-size: 42pt; color: #2980b9;'>{label}</h1>")
        html.append(f"<p style='font-size: 14pt; color: #7f8c8d;'>共 {len(group_songs)} 首曲目</p>")
        html.append("</div>")

        for song in group_songs:
            html.append("<div class='song-section'>")
            if song.song_name:
                html.append(f"<h2 class='song-title'>[{song.song_id}] {song.song_name}</h2>")
            else:
                html.append(f"<h2 class='song-title'>编号: {song.song_id}</h2>")
                
            for assessment in song.assessments:
                html.append("<div class='assessment'>")
                
                # Header
                html.append("<div class='reviewer-head'>")
                html.append(f"<div class='reviewer-name'>📌 评委：{assessment.reviewer_name}</div>")
                if assessment.overall_score:
                    html.append(f"<div class='overall-score'>总评：{strip_color(assessment.overall_score)}</div>")
                html.append("</div>")
                
                # Dimensions
                if assessment.dimension_scores:
                    html.append("<div class='dimensions'>")
                    for dim, score in assessment.dimension_scores.items():
                        html.append(f"<span class='dimension-badge'><b>{dim}:</b> {strip_color(score)}</span>")
                    html.append("</div>")
                    
                # Comments
                if assessment.comments:
                    html.append(f"<div class='comments'>{strip_color(assessment.comments).replace(chr(10), '<br/>')}</div>")
                    
                # Audience
                if assessment.audience_comments:
                    html.append("<div class='audience-info'>")
                    for aud, msg in assessment.audience_comments.items():
                        html.append(f"<b>💬 {aud}:</b> {strip_color(msg).replace(chr(10), '<br/>')}<br>")
                    html.append("</div>")
                    
                # Extra fields
                if assessment.extra_fields:
                    html.append("<div class='extra-info'>")
                    for k, v in assessment.extra_fields.items():
                        # only show if valid
                        if v and str(v).lower() != 'nan':
                            html.append(f"<b>{k}:</b> {strip_color(str(v)).replace(chr(10), '<br/>')}<br>")
                    html.append("</div>")
                    
                html.append("</div>") # close assessment
                
            html.append("</div>") # close song section
        
    html.append("</body></html>")
    
    html_str = "".join(html)
    logger.info(f"Writing PDF to {output_path}...")
    HTML(string=html_str).write_pdf(output_path)
    logger.info("PDF generated successfully.")
