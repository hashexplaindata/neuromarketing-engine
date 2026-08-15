#!/usr/bin/env python3
"""
Appwrite Cloud BaaS Client Helper
Handles direct asset streaming, experiment record management, and storage bucket sync.
"""

import os
import logging
from typing import Optional, Dict, Any

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logger = logging.getLogger("core.appwrite")


class AppwriteService:
    def __init__(self):
        self.endpoint = os.getenv("VITE_APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
        self.project_id = os.getenv("VITE_APPWRITE_PROJECT_ID", "neuromarketing-engine")
        self.api_key = os.getenv("APPWRITE_API_KEY", "")
        self.database_id = os.getenv("APPWRITE_DATABASE_ID", "NeuromarketingDB")
        self.bucket_id = os.getenv("APPWRITE_STORAGE_BUCKET_ID", "neuromarketing-assets")

        self.client = None
        self.storage = None
        self.databases = None

        if self.api_key and self.project_id:
            try:
                from appwrite.client import Client
                from appwrite.services.storage import Storage
                from appwrite.services.databases import Databases

                self.client = Client()
                self.client.set_endpoint(self.endpoint)
                self.client.set_project(self.project_id)
                self.client.set_key(self.api_key)

                self.storage = Storage(self.client)
                self.databases = Databases(self.client)
                logger.info("AppwriteService initialized successfully.")
            except Exception as e:
                logger.warning(f"Appwrite initialization note: {e}")

    def download_file_to_path(self, file_id: str, target_path: str) -> bool:
        """Downloads a file directly from Appwrite Storage by file_id."""
        if not self.storage:
            return False
        try:
            result = self.storage.get_file_download(bucket_id=self.bucket_id, file_id=file_id)
            with open(target_path, "wb") as f:
                f.write(result)
            logger.info(f"Downloaded Appwrite file '{file_id}' to '{target_path}'")
            return True
        except Exception as e:
            logger.error(f"Failed downloading Appwrite file '{file_id}': {e}")
            return False

    def get_experiment_status(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Queries the status of an experiment from Appwrite Database."""
        if not self.databases:
            return None
        try:
            from appwrite.query import Query
            docs = self.databases.list_documents(
                database_id=self.database_id,
                collection_id="experiments",
                queries=[Query.equal("experiment_id", experiment_id), Query.limit(1)]
            )
            if docs and docs.get("documents"):
                return docs["documents"][0]
            return None
        except Exception as e:
            logger.warning(f"Error querying experiment status: {e}")
            return None