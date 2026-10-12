"""Synthetic Government Document Corpus Generator for AutoDoc-Gov Benchmarks.

Generates 50+ heterogeneous documents spanning:
- 5 Document Types: Government Order, Tender Notice, RTI Reply, Public Circular, Certificate
- 3 Syntaxes: JSON, Markdown, Plain Text
- 3 Classification Tiers: Unclassified, Confidential, Secret
- Languages: English, Hindi (Devanagari), Bilingual
- Edge cases: Sensitive PII (Aadhaar, PAN, phone, email, bank IFSC), legal citations, tables.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List


def generate_synthetic_corpus(output_dir: Path = Path("benchmarks/synthetic_corpus")) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: List[Path] = []

    doc_types = ["government_order", "tender_notice", "rti_reply", "public_circular", "certificate"]
    classifications = ["unclassified", "confidential", "secret"]

    aadhaar_pool = [
        "3675 9834 6012", "9999 4105 2108", "5486 3291 7402", "2149 8736 5014", "8821 3490 1256"
    ]
    pan_pool = ["ABCDE1234F", "BNZPK7823M", "AFZPM9912K", "CRDPJ4512Q", "DLTPA8831E"]
    phone_pool = ["+91 98450 12345", "9876543210", "+91 91234 56789", "9988776655"]
    email_pool = ["applicant@gmail.com", "citizen.query@outlook.com", "tenderer@infra.co.in"]
    ifsc_pool = ["SBIN0001234", "HDFC0000456", "ICIC0001122"]

    for i in range(1, 51):
        dtype = doc_types[(i - 1) % len(doc_types)]
        cls_tier = classifications[(i - 1) % len(classifications)]
        syntax = "json" if i % 3 == 1 else ("md" if i % 3 == 2 else "txt")

        doc_num = f"SYNTH/{dtype.upper()[:4]}/{2026}/{1000 + i}"
        has_pii = (dtype == "rti_reply") or (i % 7 == 0)
        is_bilingual = (dtype == "public_circular") or (i % 5 == 0)

        pii_aadhaar = random.choice(aadhaar_pool)
        pii_pan = random.choice(pan_pool)
        pii_phone = random.choice(phone_pool)
        pii_email = random.choice(email_pool)
        pii_ifsc = random.choice(ifsc_pool)

        if syntax == "json":
            file_path = output_dir / f"doc_{i:02d}_{dtype}_{cls_tier}.json"
            data = {
                "document_number": doc_num,
                "title": f"Government Document Subject {i} - {dtype.replace('_', ' ').title()}",
                "department": "Ministry of Electronics and Information Technology",
                "jurisdiction": "Government of India",
                "date": "2026-10-12",
                "classification": cls_tier,
                "doc_type": dtype,
                "languages": ["en", "hi"] if is_bilingual else ["en"],
                "content": [
                    {
                        "type": "heading",
                        "level": 1,
                        "text": f"OFFICIAL PROCEEDINGS - {doc_num}"
                    },
                    {
                        "type": "paragraph",
                        "text": f"This official notification details administrative decision for serial record {i}. Reference is made to the established statutory guidelines."
                    }
                ]
            }

            if is_bilingual:
                data["content"].append({
                    "type": "paragraph",
                    "text": "This circular is hereby published for general public dissemination and mandatory compliance.",
                    "secondary_text": "यह परिपत्र सामान्य जनहित में सूचना एवं अनिवार्य अनुपालन हेतु जारी किया जाता है।",
                    "is_bilingual": True
                })

            if has_pii:
                data["content"].append({
                    "type": "paragraph",
                    "text": f"Applicant Identity Record: Aadhaar number {pii_aadhaar}, Income Tax PAN {pii_pan}, Contact Phone {pii_phone}, Email {pii_email}, Bank Account No: 123456789012 at IFSC {pii_ifsc}."
                })
                data["content"].append({
                    "type": "callout",
                    "callout_type": "statutory",
                    "citation": "Under Section 8(1)(j) of RTI Act 2005",
                    "text": "Personal information disclosure restricted subject to privacy assessment under the DPDP Act 2023."
                })

            data["content"].append({
                "type": "signature",
                "signatory_name": f"Officer In-Charge {i}",
                "designation": "Deputy Secretary to the Government of India",
                "department": "Department of Administrative Reforms",
                "digital_signed": True
            })

            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        elif syntax == "md":
            file_path = output_dir / f"doc_{i:02d}_{dtype}_{cls_tier}.md"
            md_lines = [
                f"# OFFICIAL GAZETTE {doc_num}",
                "**Department:** Department of Revenue & Land Records  ",
                f"**Classification:** {cls_tier.upper()}  ",
                "**Date:** 2026-10-12  ",
                "",
                "## 1. Preamble and Order Details",
                f"Administrative order issued under standard operating procedure for milestone {i}.",
                "",
            ]
            if is_bilingual:
                md_lines.append(
                    "All officers shall ensure prompt execution of these directions. "
                    "सभी संबंधित अधिकारी इन निर्देशों का तत्काल प्रभाव से कड़ाई से पालन सुनिश्चित करें।"
                )
                md_lines.append("")

            if has_pii:
                md_lines.extend([
                    "## 2. Information Regarding Requested Records",
                    f"Verified citizen particulars: Aadhaar: {pii_aadhaar}, PAN: {pii_pan}, Phone: {pii_phone}, Email: {pii_email}.",
                    "",
                    "> **[Statutory Note Under Section 8(1)(j) RTI Act]** Personal information is redacted to uphold constitutional privacy.",
                    "",
                ])

            md_lines.extend([
                "| Milestone | Target Completion | Allocation (INR Lakhs) |",
                "| :--- | :--- | :--- |",
                "| Phase 1 | Q1 2027 | 150.00 |",
                "| Phase 2 | Q3 2027 | 350.00 |",
                "",
                f"[Sd/-] Officer {i}, Joint Director",
            ])
            file_path.write_text("\n".join(md_lines), encoding="utf-8")

        else: # txt
            file_path = output_dir / f"doc_{i:02d}_{dtype}_{cls_tier}.txt"
            txt_lines = [
                "GOVERNMENT OF INDIA",
                f"MINISTRY OF PERSONNEL, PUBLIC GRIEVANCES - {doc_num}",
                f"DOCUMENT TYPE: {dtype.upper()}",
                f"Ref No: {doc_num}",
                "Date: 2026-10-12",
                f"Classification: {cls_tier.upper()}",
                "",
                f"ORDER / NOTIFICATION FOR RECORD {i}",
                "It is hereby notified for the information of all concerned that the administrative review has been completed.",
                "",
            ]
            if is_bilingual:
                txt_lines.append("General public notice issued in both Hindi and English languages.")
                txt_lines.append("यह सार्वजनिक सूचना हिंदी एवं अंग्रेजी दोनों भाषाओं में जारी की गई है।")
                txt_lines.append("")

            if has_pii:
                txt_lines.append(f"Beneficiary verified details: Aadhaar: {pii_aadhaar}, PAN Card: {pii_pan}, Phone: {pii_phone}.")
                txt_lines.append("")

            txt_lines.extend([
                "Name: Director General",
                "Designation: Principal Administrative Secretary",
                "Department: Personnel Wing",
            ])
            file_path.write_text("\n".join(txt_lines), encoding="utf-8")

        generated_files.append(file_path)

    return generated_files


if __name__ == "__main__":
    docs = generate_synthetic_corpus()
    print(f"Generated {len(docs)} synthetic government documents in benchmarks/synthetic_corpus/")
