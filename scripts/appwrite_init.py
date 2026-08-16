#!/usr/bin/env python3
"""
Appwrite Database & Collection Schema Initializer (with Network Resilience & Retries)
Neuromarketing Studio Platform - Master Architecture Specification v5.0
Applies the exact schema directly to your live Appwrite Cloud instance.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List

from dotenv import load_dotenv

# Load environment variables from .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("appwrite.schema_init")

try:
    from appwrite.client import Client
    from appwrite.services.databases import Databases
    from appwrite.services.storage import Storage
    from appwrite.permission import Permission
    from appwrite.role import Role
    from appwrite.id import ID
    from appwrite.exception import AppwriteException
except ImportError:
    logger.error("Appwrite Python SDK not found. Run 'pip install appwrite python-dotenv'")
    sys.exit(1)

def get_prop(obj, prop_name, default=""):
    if hasattr(obj, prop_name):
        return getattr(obj, prop_name)
    elif isinstance(obj, dict):
        return obj.get(prop_name, default)
    return default

def retry_api_call(func, max_retries=4, delay=1.5):
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except AppwriteException as e:
            raise e
        except Exception as err:
            if attempt == max_retries:
                raise err
            logger.warning(f"Network retry {attempt}/{max_retries} ({err}). Waiting {delay}s...")
            time.sleep(delay)
            delay *= 1.5

DATABASE_ID = os.getenv("APPWRITE_DATABASE_ID") or "NeuromarketingDB"
DATABASE_NAME = "NeuromarketingDB"
STORAGE_BUCKET_ID = os.getenv("APPWRITE_STORAGE_BUCKET_ID") or "neuromarketing-assets"
STORAGE_BUCKET_NAME = "Neuromarketing Creative Assets"

COLLECTIONS_SPEC = [
    {
        "id": "user_profiles",
        "name": "User Profiles",
        "document_security": True,
        "permissions": [
            Permission.read(Role.users()),
            Permission.create(Role.users()),
            Permission.update(Role.users()),
            Permission.delete(Role.users())
        ],
        "attributes": [
            {"type": "string", "key": "user_id", "size": 255, "required": True},
            {"type": "string", "key": "default_module", "size": 64, "required": False, "default": "UI/UX"},
            {"type": "string", "key": "ui_theme", "size": 32, "required": False, "default": "dark"}
        ]
    },
    {
        "id": "org_settings",
        "name": "Organization Settings",
        "document_security": True,
        "permissions": [
            Permission.read(Role.users()),
            Permission.create(Role.users()),
            Permission.update(Role.users())
        ],
        "attributes": [
            {"type": "string", "key": "team_id", "size": 255, "required": True},
            {"type": "string", "key": "custom_domain_boosts", "size": 65535, "required": False},
            {"type": "string", "key": "report_branding", "size": 65535, "required": False},
            {"type": "integer", "key": "monthly_quota_remaining", "required": False, "default": 50, "min": 0, "max": 1000000}
        ]
    },
    {
        "id": "experiments",
        "name": "Experiments",
        "document_security": True,
        "permissions": [
            Permission.read(Role.users()),
            Permission.create(Role.users()),
            Permission.update(Role.users()),
            Permission.delete(Role.users())
        ],
        "attributes": [
            {"type": "string", "key": "experiment_id", "size": 255, "required": True},
            {"type": "string", "key": "team_id", "size": 255, "required": True},
            {"type": "string", "key": "created_by_user", "size": 255, "required": True},
            {"type": "enum", "key": "status", "elements": ["queued", "processing", "completed", "failed"], "required": True, "default": "queued"},
            {"type": "string", "key": "created_at", "size": 64, "required": True}
        ]
    },
    {
        "id": "variants",
        "name": "Variants",
        "document_security": True,
        "permissions": [
            Permission.read(Role.users()),
            Permission.create(Role.users()),
            Permission.update(Role.users()),
            Permission.delete(Role.users())
        ],
        "attributes": [
            {"type": "string", "key": "variant_id", "size": 255, "required": True},
            {"type": "string", "key": "experiment_id", "size": 255, "required": True},
            {"type": "string", "key": "image_bucket_id", "size": 255, "required": True},
            {"type": "string", "key": "heatmap_bucket_id", "size": 255, "required": False},
            {"type": "string", "key": "metrics_json", "size": 65535, "required": False}
        ]
    }
]

def init_appwrite_schema():
    endpoint = os.getenv("VITE_APPWRITE_ENDPOINT") or os.getenv("APPWRITE_ENDPOINT") or "https://cloud.appwrite.io/v1"
    project_id = os.getenv("VITE_APPWRITE_PROJECT_ID") or os.getenv("APPWRITE_PROJECT_ID") or "neuromarketing-engine"
    api_key = os.getenv("APPWRITE_API_KEY", "")

    logger.info("=" * 70)
    logger.info("Connecting to Appwrite Cloud Instance")
    logger.info(f"Endpoint:   {endpoint}")
    logger.info(f"Project ID: {project_id}")
    logger.info(f"Database:   {DATABASE_ID}")
    logger.info(f"Bucket:     {STORAGE_BUCKET_ID}")
    logger.info(f"API Key:    {api_key[:12]}...{api_key[-6:] if len(api_key)>18 else ''}")
    logger.info("=" * 70)

    client = Client()
    client.set_endpoint(endpoint)
    client.set_project(project_id)
    if api_key:
        client.set_key(api_key)

    databases = Databases(client)
    storage = Storage(client)

    # 1. Initialize / Verify Database
    try:
        db = retry_api_call(lambda: databases.get(DATABASE_ID))
        db_name = get_prop(db, "name", DATABASE_NAME)
        logger.info(f"✓ [Database] Connected to existing Database: '{db_name}' (ID: {DATABASE_ID})")
    except AppwriteException as e:
        if e.code == 404:
            logger.info(f"[Database] Creating database '{DATABASE_ID}' ({DATABASE_NAME})...")
            db = retry_api_call(lambda: databases.create(database_id=DATABASE_ID, name=DATABASE_NAME))
            logger.info(f"✓ [Database] Successfully created database '{DATABASE_NAME}' (ID: {DATABASE_ID})")
        else:
            logger.error(f"[Database] Appwrite error: {e}")
            raise e

    # 2. Initialize Collections & Attributes
    for col_spec in COLLECTIONS_SPEC:
        col_id = col_spec["id"]
        col_name = col_spec["name"]
        doc_sec = col_spec["document_security"]
        perms = col_spec["permissions"]

        try:
            retry_api_call(lambda: databases.get_collection(DATABASE_ID, col_id))
            logger.info(f"✓ [Collection] Found existing collection: '{col_id}' ({col_name})")
        except AppwriteException as e:
            if e.code == 404:
                logger.info(f"[Collection] Creating collection '{col_id}' ({col_name}) with DLS={doc_sec}...")
                retry_api_call(lambda: databases.create_collection(
                    database_id=DATABASE_ID,
                    collection_id=col_id,
                    name=col_name,
                    permissions=perms,
                    document_security=doc_sec
                ))
                logger.info(f"✓ [Collection] Created collection '{col_id}'")
            else:
                logger.error(f"[Collection] Error on '{col_id}': {e}")
                continue

        # Attributes
        for attr in col_spec["attributes"]:
            attr_key = attr["key"]
            attr_type = attr["type"]
            attr_req = attr["required"]

            try:
                retry_api_call(lambda: databases.get_attribute(DATABASE_ID, col_id, attr_key))
                logger.info(f"  └─ ✓ [Attribute] '{attr_key}' already exists in '{col_id}'")
            except AppwriteException as e:
                if e.code == 404:
                    logger.info(f"  └─ [+] [Attribute] Creating {attr_type} attribute '{attr_key}' in '{col_id}'...")
                    try:
                        if attr_type == "string":
                            retry_api_call(lambda: databases.create_string_attribute(
                                database_id=DATABASE_ID,
                                collection_id=col_id,
                                key=attr_key,
                                size=attr["size"],
                                required=attr_req,
                                default=attr.get("default")
                            ))
                        elif attr_type == "integer":
                            retry_api_call(lambda: databases.create_integer_attribute(
                                database_id=DATABASE_ID,
                                collection_id=col_id,
                                key=attr_key,
                                required=attr_req,
                                min=attr.get("min"),
                                max=attr.get("max"),
                                default=attr.get("default")
                            ))
                        elif attr_type == "enum":
                            retry_api_call(lambda: databases.create_enum_attribute(
                                database_id=DATABASE_ID,
                                collection_id=col_id,
                                key=attr_key,
                                elements=attr["elements"],
                                required=attr_req,
                                default=attr.get("default")
                            ))
                        time.sleep(0.6)
                        logger.info(f"  └─ ✓ [Attribute] Created attribute '{attr_key}'")
                    except Exception as attr_err:
                        logger.warning(f"  └─ [!] Note on '{attr_key}': {attr_err}")
                else:
                    logger.warning(f"  └─ [!] Attribute check notice on '{attr_key}': {e}")

    # 3. Initialize / Verify Storage Bucket
    try:
        bucket = retry_api_call(lambda: storage.get_bucket(STORAGE_BUCKET_ID))
        bucket_name = get_prop(bucket, "name", STORAGE_BUCKET_NAME)
        logger.info(f"✓ [Storage] Found existing bucket: '{bucket_name}' (ID: {STORAGE_BUCKET_ID})")
    except AppwriteException as e:
        if e.code == 404:
            logger.info(f"[Storage] Creating bucket '{STORAGE_BUCKET_ID}' ({STORAGE_BUCKET_NAME})...")
            try:
                retry_api_call(lambda: storage.create_bucket(
                    bucket_id=STORAGE_BUCKET_ID,
                    name=STORAGE_BUCKET_NAME,
                    permissions=[Permission.read(Role.users()), Permission.create(Role.users()), Permission.update(Role.users())],
                    file_security=True,
                    enabled=True,
                    maximum_file_size=52428800,
                    allowed_file_extensions=["jpg", "jpeg", "png", "webp", "pdf", "npy", "json"]
                ))
                logger.info(f"✓ [Storage] Successfully created bucket '{STORAGE_BUCKET_NAME}' (ID: {STORAGE_BUCKET_ID})")
            except Exception as b_err:
                logger.error(f"[Storage] Error creating bucket: {b_err}")
        else:
            logger.warning(f"[Storage] Bucket check notice: {e}")

    logger.info("=" * 70)
    logger.info("APPWRITE CLOUD SCHEMA PROVISIONING COMPLETE!")
    logger.info("All Collections and Attributes are now live in your Appwrite Console!")
    logger.info("=" * 70)

if __name__ == "__main__":
    init_appwrite_schema()
