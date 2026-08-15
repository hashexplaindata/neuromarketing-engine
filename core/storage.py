"""
Ephemeral Multi-Tenant Workspace & Storage Manager
ICM Neuromarketing Pipeline - Storage Virtualization Layer
"""

import os
import shutil
import json
import logging
from typing import Dict, Any, Optional
from core.config import settings

logger = logging.getLogger("icm.storage")

STAGE_NAMES = [
    "01_asset_ingestion",
    "02_ensemble_saliency",
    "03_n_factorial_engine",
    "04_domain_roi_analytics",
    "05_epistemic_validation",
    "06_strategic_synthesis"
]

class EphemeralWorkspaceManager:
    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or settings.EPHEMERAL_ROOT
        self.base_engine_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_stages_dir = os.path.join(self.base_engine_dir, "stages")
        self.template_config_dir = os.path.join(self.base_engine_dir, "_config")
        os.makedirs(self.root_dir, exist_ok=True)

    def get_session_dir(self, tenant_id: str, session_id: str) -> str:
        """Returns the isolated ephemeral local directory for a tenant session."""
        # Sanitize tenant and session IDs to prevent directory traversal
        clean_tenant = "".join(c for c in tenant_id if c.isalnum() or c in ("-", "_"))
        clean_session = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.root_dir, clean_tenant, clean_session)

    def get_stage_path(self, tenant_id: str, session_id: str, stage_name: str) -> str:
        """Returns absolute path to a specific stage folder in the session workspace."""
        return os.path.join(self.get_session_dir(tenant_id, session_id), "stages", stage_name)

    def get_stage_output_dir(self, tenant_id: str, session_id: str, stage_name: str) -> str:
        """Returns absolute path to a stage's output artifact directory."""
        return os.path.join(self.get_stage_path(tenant_id, session_id, stage_name), "output")

    def initialize_session(self, tenant_id: str, session_id: str, asset_bytes: Optional[bytes] = None, filename: str = "input_asset.png") -> str:
        """
        Dynamically initializes an isolated 5-layer ICM workspace for the tenant session.
        Guarantees zero concurrency collisions between parallel tenant runs.
        """
        session_dir = self.get_session_dir(tenant_id, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 1. Create input_assets directory
        input_assets_dir = os.path.join(session_dir, "input_assets")
        os.makedirs(input_assets_dir, exist_ok=True)
        
        if asset_bytes:
            asset_path = os.path.join(input_assets_dir, filename)
            with open(asset_path, "wb") as f:
                f.write(asset_bytes)
        
        # 2. Copy global _config (Layer 3)
        session_config_dir = os.path.join(session_dir, "_config")
        if os.path.exists(self.template_config_dir):
            if not os.path.exists(session_config_dir):
                shutil.copytree(self.template_config_dir, session_config_dir)
        else:
            os.makedirs(session_config_dir, exist_ok=True)
            
        # 3. Create stages structure (Layer 2 & Layer 4)
        for stage in STAGE_NAMES:
            stage_dir = os.path.join(session_dir, "stages", stage)
            refs_dir = os.path.join(stage_dir, "references")
            out_dir = os.path.join(stage_dir, "output")
            os.makedirs(refs_dir, exist_ok=True)
            os.makedirs(out_dir, exist_ok=True)
            
            # Copy template CONTEXT.md and references if available
            tpl_stage_dir = os.path.join(self.template_stages_dir, stage)
            if os.path.exists(tpl_stage_dir):
                tpl_context = os.path.join(tpl_stage_dir, "CONTEXT.md")
                if os.path.exists(tpl_context):
                    shutil.copy2(tpl_context, os.path.join(stage_dir, "CONTEXT.md"))
                
                tpl_refs = os.path.join(tpl_stage_dir, "references")
                if os.path.exists(tpl_refs):
                    for ref_file in os.listdir(tpl_refs):
                        src_ref = os.path.join(tpl_refs, ref_file)
                        dst_ref = os.path.join(refs_dir, ref_file)
                        if os.path.isfile(src_ref):
                            shutil.copy2(src_ref, dst_ref)

        # 4. Write session metadata (Layer 0 & 1 metadata)
        session_meta = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "status": "INITIALIZED",
            "ephemeral_path": session_dir,
            "s3_path": f"s3://{settings.S3_BUCKET}/{tenant_id}/{session_id}/"
        }
        with open(os.path.join(session_dir, "session_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(session_meta, f, indent=2)

        logger.info(f"Initialized ephemeral workspace for tenant '{tenant_id}' session '{session_id}' at {session_dir}")
        return session_dir

    def sync_to_s3(self, tenant_id: str, session_id: str) -> bool:
        """
        Synchronizes all output artifacts to AWS S3 / MinIO object storage.
        """
        if not settings.USE_S3_STORAGE:
            return True
            
        session_dir = self.get_session_dir(tenant_id, session_id)
        if not os.path.exists(session_dir):
            return False
            
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            s3_prefix = f"{tenant_id}/{session_id}"
            for root, _, files in os.walk(session_dir):
                for f in files:
                    local_file = os.path.join(root, f)
                    rel_path = os.path.relpath(local_file, session_dir)
                    s3_key = f"{s3_prefix}/{rel_path}".replace("\\", "/")
                    s3_client.upload_file(local_file, settings.S3_BUCKET, s3_key)
            logger.info(f"Successfully synced session {session_id} to s3://{settings.S3_BUCKET}/{s3_prefix}/")
            return True
        except Exception as e:
            logger.error(f"S3 sync failed for {session_id}: {e}")
            return False

    def cleanup_session(self, tenant_id: str, session_id: str):
        """Purges the local ephemeral directory after S3 sync to prevent disk bloat."""
        session_dir = self.get_session_dir(tenant_id, session_id)
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up ephemeral workspace for session '{session_id}'")
            except Exception as e:
                logger.warning(f"Error purging ephemeral workspace '{session_dir}': {e}")

workspace_manager = EphemeralWorkspaceManager()
