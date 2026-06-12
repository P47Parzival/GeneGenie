"""
BioNexus India V1 — Seed Data

10 realistic Indian biological dataset metadata records for immediate testing.
These represent actual research areas and institutions across India.

Usage:
    python -m database.seed
"""

import uuid
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy import select

from database import async_session_factory, engine
from database.models import Base, Dataset

logger = logging.getLogger(__name__)

# 10 realistic Indian biological datasets
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


async def seed_database():
    """
    Insert seed datasets into the database.

    Skips records that already exist (based on dataset_id) to make
    this script idempotent — safe to run multiple times.
    """
    async with async_session_factory() as session:
        inserted = 0
        skipped = 0

        for record in SEED_DATASETS:
            # Check if already exists
            existing = await session.execute(
                select(Dataset).where(
                    Dataset.dataset_id == record["dataset_id"]
                )
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                logger.info(f"Skipping existing dataset: {record['name']}")
                continue

            dataset = Dataset(
                date_ingested=datetime.utcnow(),
                **record,
            )
            session.add(dataset)
            inserted += 1
            logger.info(f"Inserted dataset: {record['name']}")

        await session.commit()
        logger.info(
            f"Seed complete: {inserted} inserted, {skipped} skipped "
            f"(total seed records: {len(SEED_DATASETS)})"
        )


async def main():
    """Entry point for running seed as a standalone script."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting database seed...")
    await seed_database()
    await engine.dispose()
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
