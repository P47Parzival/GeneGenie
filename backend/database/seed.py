"""
BioNexus India V2 — Seed Data

V1: 10 realistic Indian biological dataset metadata records.
V2: Admin user, institution users, institutions, researcher users,
    and a sample access request.

Usage:
    python -m database.seed
"""

import uuid
import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select

from database import async_session_factory, engine
from database.models import (
    Base, Dataset, User, Institution, AccessRequest, AccessRequestTransition,
)
from services.auth_service import hash_password

logger = logging.getLogger(__name__)


# =============================================================================
# V1 Seed Datasets (unchanged)
# =============================================================================

SEED_DATASETS = [
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "indigenomes-wgs-1029"),
        "name": "IndiGenomes Whole Genome Sequences of 1029 Indian Individuals",
        "source": "indigenomes",
        "institution_name": "CSIR-Institute of Genomics and Integrative Biology (IGIB), Delhi",
        "state_of_collection": "Multi-state",
        "population_group": "Pan-Indian (27 ethnic groups)",
        "data_type": "genomic",
        "disease_association": "Population reference panel (healthy individuals)",
        "sample_size": 1029,
        "collection_date": date(2019, 6, 15),
        "access_type": "managed",
        "source_url": "https://indigenomes.igib.res.in",
        "ethics_approval_number": "IGIB/IRB/2017/034",
        "contact_researcher": "Dr. Sridhar Sivasubbu, CSIR-IGIB",
        "license_type": "Academic use only",
        "doi": "10.1093/nar/gkz1037",
        "raw_checksum": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "ibdc-breast-cancer-wb"),
        "name": "IBDC Breast Cancer Genomic Profiles — Eastern India Cohort",
        "source": "ibdc",
        "institution_name": "Indian Biological Data Centre (IBDC), Regional Centre for Biotechnology",
        "state_of_collection": "West Bengal",
        "population_group": "Bengali",
        "data_type": "genomic",
        "disease_association": "Breast cancer (triple-negative subtype)",
        "sample_size": 347,
        "collection_date": date(2022, 3, 10),
        "access_type": "controlled",
        "source_url": "https://ibdc.rcb.res.in/datasets/bc-eastern-india",
        "ethics_approval_number": "RCB/EC/2021/089",
        "contact_researcher": "Dr. Arindam Maitra, NIBMG",
        "license_type": "Restricted — DBT approval required",
        "doi": None,
        "raw_checksum": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "genomeindia-dravidian-panel"),
        "name": "GenomeIndia Dravidian Population Reference Panel",
        "source": "genomeindia",
        "institution_name": "Indian Institute of Science (IISc), Bengaluru",
        "state_of_collection": "Tamil Nadu",
        "population_group": "Dravidian (Tamil, Telugu, Kannada, Malayalam)",
        "data_type": "genomic",
        "disease_association": "Population reference panel",
        "sample_size": 2500,
        "collection_date": date(2023, 1, 20),
        "access_type": "managed",
        "source_url": "https://genomeindia.org/data/dravidian-panel",
        "ethics_approval_number": "IISc/IEC/2021/156",
        "contact_researcher": "Prof. Partha P. Majumder, NIBMG/ISI Kolkata",
        "license_type": "Academic use — attribution required",
        "doi": None,
        "raw_checksum": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "gsbtm-gujarati-t2d"),
        "name": "GSBTM Gujarati Type 2 Diabetes GWAS Dataset",
        "source": "gsbtm",
        "institution_name": "Gujarat State Biotechnology Mission (GSBTM), Gandhinagar",
        "state_of_collection": "Gujarat",
        "population_group": "Gujarati",
        "data_type": "genomic",
        "disease_association": "Type 2 Diabetes Mellitus",
        "sample_size": 1850,
        "collection_date": date(2021, 8, 5),
        "access_type": "managed",
        "source_url": "https://gsbtm.in/research/t2d-gwas",
        "ethics_approval_number": "GSBTM/EC/2020/042",
        "contact_researcher": "Dr. Rashmi Shah, GSBTM",
        "license_type": "Government of Gujarat — restricted",
        "doi": "10.1038/s41588-021-00912-4",
        "raw_checksum": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "icmr-covid19-mh"),
        "name": "ICMR COVID-19 Genomic Surveillance — Maharashtra Wave Data",
        "source": "icmr",
        "institution_name": "Indian Council of Medical Research (ICMR), National Institute of Virology, Pune",
        "state_of_collection": "Maharashtra",
        "population_group": "Maharashtrian (multi-ethnic)",
        "data_type": "genomic",
        "disease_association": "COVID-19 (SARS-CoV-2 variants)",
        "sample_size": 12450,
        "collection_date": date(2021, 5, 1),
        "access_type": "open",
        "source_url": "https://www.icmr.gov.in/covid19-genomics",
        "ethics_approval_number": "ICMR/NIV/EC/2020/301",
        "contact_researcher": "Dr. Priya Abraham, NIV Pune",
        "license_type": "CC-BY 4.0",
        "doi": "10.1101/2021.06.15.448604",
        "raw_checksum": "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "aiims-cardiac-imaging-delhi"),
        "name": "AIIMS Delhi Cardiac MRI and Echocardiography Dataset",
        "source": "aiims",
        "institution_name": "All India Institute of Medical Sciences (AIIMS), New Delhi",
        "state_of_collection": "Delhi",
        "population_group": "North Indian (multi-ethnic)",
        "data_type": "imaging",
        "disease_association": "Coronary artery disease, cardiomyopathy",
        "sample_size": 890,
        "collection_date": date(2022, 11, 15),
        "access_type": "controlled",
        "source_url": "https://www.aiims.edu/research/cardiac-imaging",
        "ethics_approval_number": "AIIMS/IEC/2022/4567",
        "contact_researcher": "Dr. Sandeep Seth, AIIMS Cardiology",
        "license_type": "Restricted — institutional collaboration only",
        "doi": None,
        "raw_checksum": "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "cmc-thalassemia-tn"),
        "name": "CMC Vellore Thalassemia Carrier Screening Registry",
        "source": "cmc_vellore",
        "institution_name": "Christian Medical College (CMC), Vellore",
        "state_of_collection": "Tamil Nadu",
        "population_group": "South Indian (Tamil, multi-caste)",
        "data_type": "clinical",
        "disease_association": "Beta-thalassemia, sickle cell disease",
        "sample_size": 5600,
        "collection_date": date(2020, 4, 20),
        "access_type": "managed",
        "source_url": "https://www.cmch-vellore.edu/thalassemia-registry",
        "ethics_approval_number": "CMC/IRB/2019/10345",
        "contact_researcher": "Dr. Biju George, CMC Vellore Haematology",
        "license_type": "Academic use — MoU required",
        "doi": "10.1111/bjh.17015",
        "raw_checksum": "a1c2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "nimhans-neurogenomics-ka"),
        "name": "NIMHANS Neuropsychiatric Genomics — South Indian Cohort",
        "source": "nimhans",
        "institution_name": "National Institute of Mental Health and Neurosciences (NIMHANS), Bengaluru",
        "state_of_collection": "Karnataka",
        "population_group": "Kannadiga",
        "data_type": "genomic",
        "disease_association": "Schizophrenia, bipolar disorder, autism spectrum disorder",
        "sample_size": 1200,
        "collection_date": date(2023, 6, 1),
        "access_type": "controlled",
        "source_url": "https://nimhans.ac.in/neurogenomics",
        "ethics_approval_number": "NIMHANS/IEC/2022/0891",
        "contact_researcher": "Dr. Sanjeev Jain, NIMHANS",
        "license_type": "Restricted — ethics board approval required",
        "doi": None,
        "raw_checksum": "b2d3f4a5c6e7b8d9f0a1c2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "pgimer-clinical-genomics-pb"),
        "name": "PGIMER Chandigarh Clinical Genomics — Punjab Sikh Population",
        "source": "pgimer",
        "institution_name": "Post Graduate Institute of Medical Education and Research (PGIMER), Chandigarh",
        "state_of_collection": "Punjab",
        "population_group": "Punjabi Sikh",
        "data_type": "genomic",
        "disease_association": "Cardiovascular disease, Type 2 Diabetes, obesity",
        "sample_size": 780,
        "collection_date": date(2022, 9, 10),
        "access_type": "managed",
        "source_url": "https://pgimer.edu.in/clinical-genomics",
        "ethics_approval_number": "PGI/IEC/2021/2345",
        "contact_researcher": "Dr. Madhu Khullar, PGIMER",
        "license_type": "Academic use — collaboration required",
        "doi": "10.1007/s12041-022-01375-6",
        "raw_checksum": "c3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4",
    },
    {
        "dataset_id": uuid.uuid5(uuid.NAMESPACE_URL, "bjmc-oral-cancer-gj"),
        "name": "BJ Medical College Oral Cancer Genomics — Gujarat Tobacco Chewers",
        "source": "bjmc",
        "institution_name": "BJ Government Medical College, Ahmedabad",
        "state_of_collection": "Gujarat",
        "population_group": "Gujarati",
        "data_type": "genomic",
        "disease_association": "Oral squamous cell carcinoma, oral submucous fibrosis",
        "sample_size": 420,
        "collection_date": date(2023, 2, 28),
        "access_type": "controlled",
        "source_url": "https://bjmcah.edu.in/research/oral-cancer-genomics",
        "ethics_approval_number": "BJMC/IEC/2022/078",
        "contact_researcher": "Dr. Prateek Jain, BJ Medical College",
        "license_type": "Restricted — institutional approval required",
        "doi": None,
        "raw_checksum": "d4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5",
    },
]


# =============================================================================
# V2 Seed Data
# =============================================================================

# Fixed UUIDs for seed users and institutions
ADMIN_ID = uuid.uuid5(uuid.NAMESPACE_URL, "admin@bionexus.in")
IGIB_INST_ID = uuid.uuid5(uuid.NAMESPACE_URL, "institution-csir-igib")
RCB_INST_ID = uuid.uuid5(uuid.NAMESPACE_URL, "institution-rcb-ibdc")
IGIB_USER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "nodal@igib.res.in")
RCB_USER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "nodal@rcb.res.in")
RESEARCHER1_ID = uuid.uuid5(uuid.NAMESPACE_URL, "researcher1@iitd.ac.in")
RESEARCHER2_ID = uuid.uuid5(uuid.NAMESPACE_URL, "researcher2@iisc.ac.in")


SEED_INSTITUTIONS = [
    {
        "id": IGIB_INST_ID,
        "institution_name": "CSIR-Institute of Genomics and Integrative Biology (IGIB)",
        "institution_type": "government",
        "state": "Delhi",
        "nodal_officer_name": "Dr. Sridhar Sivasubbu",
        "nodal_officer_email": "nodal@igib.res.in",
        "nodal_officer_phone": "+91-11-27666156",
        "funding_source": "DBT",
        "ibdc_registration_number": "IBDC-IGIB-001",
        "is_verified": True,
        "verified_at": datetime(2025, 1, 15),
        "verified_by": ADMIN_ID,
    },
    {
        "id": RCB_INST_ID,
        "institution_name": "Regional Centre for Biotechnology (RCB), Faridabad",
        "institution_type": "government",
        "state": "Haryana",
        "nodal_officer_name": "Dr. Shubhra Acharya",
        "nodal_officer_email": "nodal@rcb.res.in",
        "nodal_officer_phone": "+91-129-2848800",
        "funding_source": "DBT",
        "ibdc_registration_number": "IBDC-RCB-001",
        "is_verified": True,
        "verified_at": datetime(2025, 1, 15),
        "verified_by": ADMIN_ID,
    },
]

SEED_USERS = [
    {
        "id": ADMIN_ID,
        "email": "admin@bionexus.in",
        "hashed_password": hash_password("Admin@BioNexus2025"),
        "full_name": "BioNexus Admin",
        "role": "admin",
        "institution_id": None,
        "is_active": True,
    },
    {
        "id": IGIB_USER_ID,
        "email": "nodal@igib.res.in",
        "hashed_password": hash_password("IGIB@Nodal2025"),
        "full_name": "Dr. Sridhar Sivasubbu",
        "role": "institution",
        "institution_id": IGIB_INST_ID,
        "is_active": True,
    },
    {
        "id": RCB_USER_ID,
        "email": "nodal@rcb.res.in",
        "hashed_password": hash_password("RCB@Nodal2025"),
        "full_name": "Dr. Shubhra Acharya",
        "role": "institution",
        "institution_id": RCB_INST_ID,
        "is_active": True,
    },
    {
        "id": RESEARCHER1_ID,
        "email": "researcher@iitd.ac.in",
        "hashed_password": hash_password("Research@IIT2025"),
        "full_name": "Dr. Priya Sharma",
        "role": "researcher",
        "institution_id": None,
        "is_active": True,
    },
    {
        "id": RESEARCHER2_ID,
        "email": "researcher@iisc.ac.in",
        "hashed_password": hash_password("Research@IISc2025"),
        "full_name": "Dr. Amit Verma",
        "role": "researcher",
        "institution_id": None,
        "is_active": True,
    },
]


async def seed_database():
    """
    Insert all seed data into the database.
    Idempotent — safe to run multiple times.
    """
    async with async_session_factory() as session:
        # --- Seed Institutions (V2) — WITHOUT verified_by first (FK ordering) ---
        for record in SEED_INSTITUTIONS:
            existing = await session.execute(
                select(Institution).where(Institution.id == record["id"])
            )
            if existing.scalar_one_or_none() is None:
                # Insert without verified_by to avoid FK violation
                inst_data = {k: v for k, v in record.items() if k != "verified_by"}
                inst_data["is_verified"] = False  # Will update after admin exists
                inst_data["verified_at"] = None
                session.add(Institution(**inst_data))
                logger.info(f"Inserted institution: {record['institution_name']}")

        await session.flush()

        # --- Seed Users (V2) ---
        for record in SEED_USERS:
            existing = await session.execute(
                select(User).where(User.id == record["id"])
            )
            if existing.scalar_one_or_none() is None:
                session.add(User(**record))
                logger.info(f"Inserted user: {record['email']} (role={record['role']})")

        await session.flush()

        # --- Update Institutions with verified_by now that admin exists ---
        for record in SEED_INSTITUTIONS:
            if record.get("verified_by"):
                result = await session.execute(
                    select(Institution).where(Institution.id == record["id"])
                )
                inst = result.scalar_one_or_none()
                if inst and not inst.is_verified:
                    inst.is_verified = True
                    inst.verified_at = record.get("verified_at", datetime.utcnow())
                    inst.verified_by = record["verified_by"]
                    logger.info(f"Verified institution: {inst.institution_name}")

        await session.flush()

        # --- Seed Datasets (V1) ---
        inserted_ds = 0
        for record in SEED_DATASETS:
            existing = await session.execute(
                select(Dataset).where(Dataset.dataset_id == record["dataset_id"])
            )
            if existing.scalar_one_or_none() is None:
                # Link first dataset to IGIB institution
                extra = {}
                if record["source"] == "indigenomes":
                    extra["managing_institution_id"] = IGIB_INST_ID
                elif record["source"] == "ibdc":
                    extra["managing_institution_id"] = RCB_INST_ID

                session.add(Dataset(
                    date_ingested=datetime.utcnow(),
                    **record,
                    **extra,
                ))
                inserted_ds += 1
                logger.info(f"Inserted dataset: {record['name'][:60]}")

        await session.flush()

        # --- Seed Sample Access Request (V2) ---
        ar_id = uuid.uuid5(uuid.NAMESPACE_URL, "sample-access-request-1")
        existing_ar = await session.execute(
            select(AccessRequest).where(AccessRequest.id == ar_id)
        )
        if existing_ar.scalar_one_or_none() is None:
            # Get the IndiGenomes dataset
            ds_id = uuid.uuid5(uuid.NAMESPACE_URL, "indigenomes-wgs-1029")

            ar = AccessRequest(
                id=ar_id,
                requesting_user_id=RESEARCHER1_ID,
                dataset_id=ds_id,
                status="approved",
                purpose_of_use="Study of genetic variants associated with Type 2 Diabetes in Indian populations",
                institution_affiliation="Indian Institute of Technology Delhi (IIT-D)",
                expected_duration_days=365,
                will_data_be_published=True,
                ethics_approval_number="IITD/IEC/2024/A-15",
                requested_access_type="managed",
                reviewer_id=IGIB_USER_ID,
                submitted_at=datetime(2025, 2, 1),
                approved_at=datetime(2025, 2, 10),
                expires_at=datetime(2026, 2, 10),
            )
            session.add(ar)
            await session.flush()

            # Add transitions
            transitions = [
                ("draft", RESEARCHER1_ID, "Request created"),
                ("submitted", RESEARCHER1_ID, "Submitted for review"),
                ("under_review", IGIB_USER_ID, "Review started"),
                ("approved", IGIB_USER_ID, "Access granted — valid for 1 year"),
            ]
            prev_status = None
            for to_status, actor_id, reason in transitions:
                session.add(AccessRequestTransition(
                    id=uuid.uuid4(),
                    access_request_id=ar_id,
                    from_status=prev_status,
                    to_status=to_status,
                    actor_id=actor_id,
                    reason=reason,
                ))
                prev_status = to_status

            logger.info("Inserted sample access request (approved)")

        await session.commit()
        logger.info("Seed complete!")


async def main():
    """Entry point for running seed as a standalone script."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting database seed (V2)...")
    await seed_database()
    await engine.dispose()
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
