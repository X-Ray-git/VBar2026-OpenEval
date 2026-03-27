import os
import pandas as pd
import logging
from src.models import EvaluationReport
from src.parser_registry import get_parser
from src.pdf_generator import generate_pdf

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    file_path = "data/26V8在线瑞平0325.xlsx"
    output_pdf = "26V8在线瑞平评委评价汇编.pdf"
    
    if not os.path.exists(file_path):
        logger.error(f"File {file_path} not found.")
        return
        
    logger.info("Initializing Evaluation Report...")
    report = EvaluationReport()
    
    logger.info(f"Loading Excel file: {file_path}")
    try:
        xls = pd.ExcelFile(file_path, engine='calamine')
    except Exception as e:
        logger.error(f"Failed to load Excel file: {e}")
        return
        
    total_assessments_added = 0
    for sheet in xls.sheet_names:
        logger.info(f"Processing sheet: {sheet}")
        
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            
            parser_func = get_parser(sheet)
            if not parser_func:
                continue
                
            assessments, decl = parser_func(df, sheet)
            
            # Store the reviewer's declaration
            report.add_reviewer_info(sheet, decl)
            
            for assessment in assessments:
                report.add_assessment(assessment)
                total_assessments_added += 1
                
            logger.info(f"  -> Extracted {len(assessments)} assessments.")
        except Exception as e:
            logger.warning(f"  -> Error parsing sheet '{sheet}': {e}")
            
    logger.info(f"Total songs aggregated: {len(report.songs)}")
    logger.info(f"Total assessments aggregated: {total_assessments_added}")
    
    if len(report.songs) == 0:
        logger.error("No valid data found to generate PDF.")
        return
        
    # Generate the actual PDF
    try:
        generate_pdf(report, output_pdf)
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")

if __name__ == "__main__":
    main()
