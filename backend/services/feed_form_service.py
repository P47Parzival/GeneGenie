"""
BioNexus India V2 — FeED Form Service

Generates FeED (Fair Exchange of Experimental Data) protocol compliance
forms pre-filled from access request data. Each form is stored as both
structured JSON (for machine consumption) and rendered PDF (for humans).

Form types generated:
  1. Data User Agreement (DUA)
  2. Data Access Request Form
  3. Institutional Sign-off
  4. Data Management Plan Summary
  5. Publication & Attribution Commitment
  6. Ethics Compliance Declaration

PDF generation uses ReportLab — pure Python, no external API deps.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from config import settings
from database.models import (
    AccessRequest,
    Dataset,
    FeedForm,
    Institution,
    User,
)

logger = logging.getLogger(__name__)

# All form types we generate
FORM_TYPES = [
    "dua",              # Data User Agreement
    "access_request",   # Data Access Request Form
    "signoff",          # Institutional Sign-off
    "dmp",              # Data Management Plan Summary
    "publication",      # Publication & Attribution Commitment
    "ethics",           # Ethics Compliance Declaration
]


class FeedFormService:
    """Generates FeED-compliant forms from access request data."""

    def generate_all_forms(
        self,
        access_request: AccessRequest,
        dataset: Dataset,
        researcher: User,
        institution: Institution | None = None,
    ) -> list[dict]:
        """
        Generate all FeED compliance forms for an access request.

        Returns a list of dicts with form_type, form_data_json, and pdf_path.
        """
        forms = []

        for form_type in FORM_TYPES:
            try:
                form_data = self._build_form_data(
                    form_type, access_request, dataset, researcher, institution
                )
                pdf_path = self._generate_pdf(
                    form_type, form_data, access_request.id
                )

                forms.append({
                    "form_type": form_type,
                    "form_data_json": form_data,
                    "pdf_path": pdf_path,
                })

                logger.info(
                    f"Generated FeED form: {form_type} for request {access_request.id}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to generate form {form_type}: {e}", exc_info=True
                )
                # Still generate JSON even if PDF fails
                forms.append({
                    "form_type": form_type,
                    "form_data_json": self._build_form_data(
                        form_type, access_request, dataset, researcher, institution
                    ),
                    "pdf_path": None,
                })

        return forms

    def _build_form_data(
        self,
        form_type: str,
        ar: AccessRequest,
        ds: Dataset,
        researcher: User,
        inst: Institution | None,
    ) -> dict[str, Any]:
        """Build structured JSON form data based on form type."""

        base_context = {
            "form_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "platform": "BioNexus India",
            "platform_version": "2.0.0",
            "access_request_id": str(ar.id),
            "dataset_name": ds.name,
            "dataset_source": ds.source,
            "dataset_id": str(ds.dataset_id),
            "researcher_name": researcher.full_name,
            "researcher_email": researcher.email,
            "researcher_institution": ar.institution_affiliation or "Not specified",
        }

        if inst:
            base_context.update({
                "data_provider_institution": inst.institution_name,
                "data_provider_type": inst.institution_type,
                "nodal_officer_name": inst.nodal_officer_name or "Not specified",
                "nodal_officer_email": inst.nodal_officer_email or "Not specified",
            })

        builders = {
            "dua": self._build_dua,
            "access_request": self._build_access_request_form,
            "signoff": self._build_signoff,
            "dmp": self._build_dmp,
            "publication": self._build_publication,
            "ethics": self._build_ethics,
        }

        builder = builders.get(form_type, self._build_dua)
        form_data = builder(ar, ds, researcher, inst)
        form_data.update(base_context)
        return form_data

    def _build_dua(self, ar, ds, researcher, inst) -> dict:
        """Data User Agreement form."""
        return {
            "form_title": "Data User Agreement (DUA)",
            "form_description": (
                "This agreement governs the terms under which biological data "
                "from Indian research institutions is shared and used, in compliance "
                "with DBT's Biotech-PRIDE policy and FeED Protocols (January 2025)."
            ),
            "sections": [
                {
                    "title": "1. Parties",
                    "content": {
                        "data_user": researcher.full_name,
                        "data_user_email": researcher.email,
                        "data_user_institution": ar.institution_affiliation,
                        "data_provider": inst.institution_name if inst else ds.institution_name,
                    },
                },
                {
                    "title": "2. Dataset Description",
                    "content": {
                        "dataset_name": ds.name,
                        "data_type": ds.data_type,
                        "population_group": ds.population_group,
                        "state_of_collection": ds.state_of_collection,
                        "sample_size": ds.sample_size,
                        "access_type": ar.requested_access_type,
                    },
                },
                {
                    "title": "3. Purpose of Use",
                    "content": ar.purpose_of_use or "Not specified",
                },
                {
                    "title": "4. Duration",
                    "content": f"{ar.expected_duration_days or 'Not specified'} days",
                },
                {
                    "title": "5. Terms and Conditions",
                    "content": [
                        "The Data User agrees to use the data solely for the stated purpose.",
                        "The Data User will not attempt to re-identify individual participants.",
                        "The Data User will acknowledge the data source in all publications.",
                        "The Data User will comply with all applicable Indian data protection laws.",
                        "The Data User will destroy all copies upon expiry of the access period.",
                        "The Data User will report any data breaches immediately to the Data Provider.",
                    ],
                },
                {
                    "title": "6. Compliance",
                    "content": (
                        "This agreement is in compliance with DBT Biotech-PRIDE Policy (2021) "
                        "and FeED Protocols (January 2025) for sharing of biological data "
                        "generated through DBT-funded research."
                    ),
                },
            ],
            "signature_required": True,
        }

    def _build_access_request_form(self, ar, ds, researcher, inst) -> dict:
        """Data Access Request Form — mirrors FeED protocol fields."""
        return {
            "form_title": "Data Access Request Form",
            "form_description": "Formal request for access to biological data under FeED Protocols.",
            "fields": {
                "applicant_name": researcher.full_name,
                "applicant_email": researcher.email,
                "applicant_institution": ar.institution_affiliation,
                "dataset_requested": ds.name,
                "dataset_id": str(ds.dataset_id),
                "data_type": ds.data_type,
                "access_type_requested": ar.requested_access_type,
                "purpose_of_use": ar.purpose_of_use,
                "expected_duration_days": ar.expected_duration_days,
                "will_data_be_published": ar.will_data_be_published,
                "ethics_approval_number": ar.ethics_approval_number,
                "disease_association": ds.disease_association,
                "population_group": ds.population_group,
                "sample_size": ds.sample_size,
            },
        }

    def _build_signoff(self, ar, ds, researcher, inst) -> dict:
        """Institutional Sign-off section."""
        return {
            "form_title": "Institutional Sign-off",
            "form_description": "Sign-off by the data providing institution's nodal officer.",
            "institution": {
                "name": inst.institution_name if inst else ds.institution_name,
                "type": inst.institution_type if inst else "Not specified",
                "nodal_officer": inst.nodal_officer_name if inst else "Not specified",
                "email": inst.nodal_officer_email if inst else "Not specified",
            },
            "approval_details": {
                "approved_for": researcher.full_name,
                "dataset": ds.name,
                "access_type": ar.requested_access_type,
                "duration_days": ar.expected_duration_days,
                "conditions": "As per DUA terms",
            },
            "signature_required": True,
        }

    def _build_dmp(self, ar, ds, researcher, inst) -> dict:
        """Data Management Plan summary."""
        return {
            "form_title": "Data Management Plan Summary",
            "form_description": "Summary of how the data will be managed, stored, and secured.",
            "sections": [
                {
                    "title": "Data Storage",
                    "content": "Data will be stored on secure institutional servers with encryption at rest.",
                },
                {
                    "title": "Access Control",
                    "content": "Access limited to the requesting researcher and named collaborators only.",
                },
                {
                    "title": "Data Retention",
                    "content": f"Data will be retained for {ar.expected_duration_days or 'the agreed'} days, then securely deleted.",
                },
                {
                    "title": "Data Sharing",
                    "content": "Data will not be shared with third parties without explicit consent from the data provider.",
                },
                {
                    "title": "Security Measures",
                    "content": "Encrypted storage, role-based access, audit logging, regular security reviews.",
                },
            ],
        }

    def _build_publication(self, ar, ds, researcher, inst) -> dict:
        """Publication and Attribution Commitment."""
        return {
            "form_title": "Publication & Attribution Commitment",
            "form_description": "Commitment to proper attribution and publication practices.",
            "commitments": [
                f"All publications using data from '{ds.name}' will include proper citation and acknowledgment.",
                f"The data source ({ds.institution_name or ds.source}) will be acknowledged as the data provider.",
                "Any publications will be shared with the data provider prior to submission.",
                "The DOI of the original dataset will be cited where available.",
                "Co-authorship will be offered to the data provider where their contribution is substantive.",
            ],
            "will_publish": ar.will_data_be_published,
            "dataset_doi": ds.doi,
        }

    def _build_ethics(self, ar, ds, researcher, inst) -> dict:
        """Ethics Compliance Declaration."""
        return {
            "form_title": "Ethics Compliance Declaration",
            "form_description": "Declaration of compliance with ethical requirements for human biological data.",
            "declarations": [
                "The research involving this data has received appropriate ethics committee approval.",
                "All data subjects provided informed consent for their data to be used in research.",
                "The researcher will comply with ICMR National Ethical Guidelines for Biomedical and Health Research (2017).",
                "Any deviation from the approved research protocol will be reported to the ethics committee.",
                "The researcher acknowledges the sensitive nature of biological data from Indian populations.",
            ],
            "researcher_ethics_approval": ar.ethics_approval_number,
            "dataset_ethics_approval": ds.ethics_approval_number,
        }

    def _generate_pdf(
        self, form_type: str, form_data: dict, request_id: uuid.UUID
    ) -> str:
        """
        Generate a PDF document from form data using ReportLab.

        Returns the file path to the generated PDF.
        """
        # Create output directory
        output_dir = Path(settings.upload_dir) / "feed_forms" / str(request_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{form_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = output_dir / filename

        # Build PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "FormTitle",
            parent=styles["Title"],
            fontSize=16,
            textColor=colors.HexColor("#1a365d"),
            spaceAfter=6 * mm,
        )
        heading_style = ParagraphStyle(
            "FormHeading",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#2c5282"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
        body_style = ParagraphStyle(
            "FormBody",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=2 * mm,
            leading=14,
        )
        label_style = ParagraphStyle(
            "FormLabel",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#4a5568"),
        )

        elements = []

        # Header
        elements.append(Paragraph("BioNexus India", label_style))
        elements.append(Paragraph("FeED Protocol Compliance Document", label_style))
        elements.append(Spacer(1, 4 * mm))

        # Form Title
        form_title = form_data.get("form_title", form_type.upper())
        elements.append(Paragraph(form_title, title_style))

        # Description
        desc = form_data.get("form_description", "")
        if desc:
            elements.append(Paragraph(desc, body_style))
            elements.append(Spacer(1, 4 * mm))

        # Metadata table
        meta_data = [
            ["Form ID:", form_data.get("form_id", "N/A")],
            ["Generated:", form_data.get("generated_at", "N/A")],
            ["Request ID:", form_data.get("access_request_id", "N/A")],
            ["Dataset:", form_data.get("dataset_name", "N/A")],
            ["Researcher:", form_data.get("researcher_name", "N/A")],
        ]
        meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
        meta_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4a5568")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 6 * mm))

        # Render sections
        sections = form_data.get("sections", [])
        for section in sections:
            title = section.get("title", "")
            content = section.get("content", "")

            elements.append(Paragraph(title, heading_style))

            if isinstance(content, str):
                elements.append(Paragraph(content, body_style))
            elif isinstance(content, list):
                for item in content:
                    elements.append(Paragraph(f"• {item}", body_style))
            elif isinstance(content, dict):
                for key, value in content.items():
                    label = key.replace("_", " ").title()
                    elements.append(
                        Paragraph(f"<b>{label}:</b> {value or 'Not specified'}", body_style)
                    )
            elements.append(Spacer(1, 2 * mm))

        # Render fields (for access request form)
        fields = form_data.get("fields", {})
        if fields:
            elements.append(Paragraph("Application Details", heading_style))
            for key, value in fields.items():
                label = key.replace("_", " ").title()
                elements.append(
                    Paragraph(f"<b>{label}:</b> {value or 'Not specified'}", body_style)
                )

        # Render commitments/declarations
        for list_key in ["commitments", "declarations"]:
            items = form_data.get(list_key, [])
            if items:
                elements.append(Spacer(1, 4 * mm))
                for i, item in enumerate(items, 1):
                    elements.append(Paragraph(f"{i}. {item}", body_style))

        # Signature block
        if form_data.get("signature_required"):
            elements.append(Spacer(1, 10 * mm))
            elements.append(Paragraph("Signatures", heading_style))

            sig_data = [
                ["", "Data User", "Data Provider"],
                ["Name:", "___________________", "___________________"],
                ["Signature:", "___________________", "___________________"],
                ["Date:", "___________________", "___________________"],
                ["Designation:", "___________________", "___________________"],
            ]
            sig_table = Table(sig_data, colWidths=[3 * cm, 6.5 * cm, 6.5 * cm])
            sig_table.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#2c5282")),
            ]))
            elements.append(sig_table)

        # Footer
        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph(
            "This document was auto-generated by BioNexus India in compliance "
            "with DBT Biotech-PRIDE Policy (2021) and FeED Protocols (January 2025).",
            label_style,
        ))

        # Build the PDF
        doc.build(elements)
        logger.info(f"PDF generated: {filepath}")

        return str(filepath)


# Singleton instance
feed_form_service = FeedFormService()
