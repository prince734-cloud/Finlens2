"""
Utility script to generate a high-fidelity sample financial report PDF for Apple Inc. (FY 2024)
using PyMuPDF without needing external heavyweight report libraries.
"""
from pathlib import Path
from typing import Optional
import pymupdf as fitz


def create_apple_sample_report(output_path: Optional[str] = None) -> str:
    """Generates a 3-page realistic financial report excerpt for testing FinLens RAG."""
    if output_path is None:
        script_dir = Path(__file__).resolve().parent
        output_path = str(script_dir / "Apple_Inc_FY2024_Annual_Report.pdf")

    doc = fitz.open()

    # PAGE 1: Company Overview & Consolidated Statements of Operations
    page1 = doc.new_page(width=595, height=842)  # A4 standard
    rect1 = fitz.Rect(50, 50, 545, 792)
    
    p1_text = (
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\n"
        "Washington, D.C. 20549\n\n"
        "FORM 10-K\n"
        "ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934\n"
        "For the fiscal year ended September 28, 2024\n\n"
        "APPLE INC.\n"
        "One Apple Park Way, Cupertino, California 95014\n\n"
        "Business Overview\n"
        "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, "
        "wearables, and accessories, and sells a variety of related services. The Company's fiscal year "
        "is the 52- or 53-week period that ends on the last Saturday of September.\n\n"
        "Consolidated Statements of Operations\n"
        "(In millions, except per share amounts)\n"
        "Years ended September 28, 2024 and September 30, 2023:\n\n"
        "Total net sales: $391,035 (2024) vs $383,285 (2023)\n"
        "Products net sales: $298,085 (2024) vs $298,085 (2023)\n"
        "Services net sales: $92,950 (2024) vs $85,200 (2023)\n"
        "Total cost of sales: $210,352 (2024) vs $214,137 (2023)\n"
        "Gross margin: $180,683 (2024) vs $169,148 (2023)\n\n"
        "Operating expenses:\n"
        "Research and development: $31,370 (2024) vs $29,915 (2023)\n"
        "Selling, general and administrative: $26,094 (2024) vs $24,932 (2023)\n"
        "Total operating expenses: $57,464 (2024) vs $54,847 (2023)\n\n"
        "Operating income: $123,219 (2024) vs $114,301 (2023)\n"
        "Other income/(expense), net: $269 (2024) vs $(380) (2023)\n"
        "Income before provision for income taxes: $123,488 (2024) vs $113,921 (2023)\n"
        "Provision for income taxes: $29,748 (2024) vs $16,741 (2023)\n"
        "Net income: $93,740 (2024) vs $96,995 (2023)\n\n"
        "Operating cash flows were $118,260 million for fiscal 2024, compared to $110,543 million in fiscal 2023.\n"
        "Total assets stood at $364,980 million and total liabilities stood at $308,030 million."
    )
    page1.insert_textbox(rect1, p1_text, fontsize=9.5, fontname="helv")

    # PAGE 2: Management's Discussion and Analysis (MD&A)
    page2 = doc.new_page(width=595, height=842)
    rect2 = fitz.Rect(50, 50, 545, 792)
    p2_text = (
        "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations\n\n"
        "Financial Performance Summary & Growth Drivers\n"
        "Total net sales increased 2% or $7.75 billion during fiscal 2024 compared to fiscal 2023, "
        "driven primarily by higher net sales of Services and Mac, partially offset by lower net sales of Wearables.\n\n"
        "Services Net Sales\n"
        "Services net sales grew 9% to $92.95 billion, reflecting increased customer engagement across the ecosystem, "
        "higher advertising revenue, and subscription momentum in Cloud Services, Apple Music, and the App Store.\n\n"
        "Products Performance\n"
        "iPhone net sales were $201.18 billion in 2024 compared to $200.58 billion in 2023. Mac net sales rose 2% to "
        "$29.98 billion, propelled by M3-powered MacBook Air laptops. iPad net sales were $26.69 billion.\n\n"
        "Gross Margin and Operating Income Drivers\n"
        "Gross margin percentage expanded to 46.2% in 2024 from 44.1% in 2023. This margin expansion was driven by a favorable "
        "shift toward higher-margin Services and cost savings on product components.\n"
        "Operating income increased 8% to $123.22 billion due to higher gross margins, despite increases in research and "
        "development investments relating to artificial intelligence, machine learning, and silicon engineering."
    )
    page2.insert_textbox(rect2, p2_text, fontsize=10, fontname="helv")

    # PAGE 3: Item 1A. Risk Factors
    page3 = doc.new_page(width=595, height=842)
    rect3 = fitz.Rect(50, 50, 545, 792)
    p3_text = (
        "Item 1A. Risk Factors\n\n"
        "The Company's business, reputation, results of operations, and financial condition could be adversely affected by various risks:\n\n"
        "1. Global Economic and Market Conditions\n"
        "Unfavorable global macroeconomic conditions, including inflation, currency volatility, and geopolitical tensions, "
        "could dampen consumer demand for premium consumer electronics and slow enterprise IT spending.\n\n"
        "2. Highly Competitive and Fast-Changing Markets\n"
        "The markets for the Company's products and services are highly competitive and subject to rapid technological shifts, "
        "particularly in generative AI, mobile platforms, and customized semiconductor hardware. If Apple fails to innovate "
        "and introduce compelling new products, its market position could weaken.\n\n"
        "3. Supply Chain and Single-Source Component Dependencies\n"
        "Many components, including advanced semiconductor chips produced by TSMC, OLED displays, and camera modules, are "
        "obtained from single or limited manufacturing sources located in Asia. Disruptions from natural disasters, logistical "
        "bottlenecks, or trade restrictions could severely delay product deliveries.\n\n"
        "4. Regulatory and Antitrust Scrutiny\n"
        "Apple faces intense scrutiny and legal actions globally regarding its App Store guidelines, proprietary iOS ecosystem, "
        "and digital payment technologies. Compliance with the European Union's Digital Markets Act (DMA) may alter the Company's "
        "business model and negatively impact service fees."
    )
    page3.insert_textbox(rect3, p3_text, fontsize=10, fontname="helv")

    doc.save(output_path)
    doc.close()
    print(f"Sample Apple annual report PDF created at: {output_path}")
    return output_path


if __name__ == "__main__":
    create_apple_sample_report()
