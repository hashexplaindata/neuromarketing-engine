"""
Stripe Quota & Billing Metering Engine
ICM Neuromarketing Platform - Tier Enforcement Layer
"""

import os
import json
import logging
from typing import Dict, Any, Tuple
from core.config import settings

logger = logging.getLogger("icm.metering")

TIER_QUOTAS = {
    "starter": {
        "monthly_assets": 25,
        "max_concurrency": 1,
        "max_permutations": 4,
        "formats": ["json", "html"],
        "credit_cost_per_analysis": 1
    },
    "professional": {
        "monthly_assets": 250,
        "max_concurrency": 4,
        "max_permutations": 16,
        "formats": ["json", "html", "pdf"],
        "credit_cost_per_analysis": 1
    },
    "enterprise": {
        "monthly_assets": 999999,
        "max_concurrency": 16,
        "max_permutations": 64,
        "formats": ["json", "html", "pdf", "npy"],
        "credit_cost_per_analysis": 1
    }
}

# In-memory quota ledger for development/mocking (in production, backed by Redis/Postgres)
_TENANT_LEDGER: Dict[str, Dict[str, Any]] = {}

class MeteringService:
    def __init__(self):
        self.enabled = settings.METERING_ENABLED

    def get_tenant_tier_spec(self, tier: str) -> Dict[str, Any]:
        return TIER_QUOTAS.get(tier.lower(), TIER_QUOTAS["starter"])

    def check_quota(self, tenant_id: str, tier: str, requested_permutations: int = 1) -> Tuple[bool, str]:
        """
        Validates whether tenant has sufficient quota and is within tier limits.
        """
        if not self.enabled:
            return True, "Metering disabled (Unlimited dev mode)"

        spec = self.get_tenant_tier_spec(tier)
        
        # Check permutation limits
        if requested_permutations > spec["max_permutations"]:
            return False, f"Requested permutations ({requested_permutations}) exceeds {tier.upper()} tier limit ({spec['max_permutations']}). Please upgrade to Enterprise."

        # Check monthly usage balance
        ledger = _TENANT_LEDGER.setdefault(tenant_id, {
            "used_assets": 0,
            "tier": tier
        })
        
        if ledger["used_assets"] >= spec["monthly_assets"]:
            return False, f"Monthly quota exceeded for tenant '{tenant_id}' ({ledger['used_assets']}/{spec['monthly_assets']}). Upgrade tier in Stripe."

        return True, "Quota verified"

    def deduct_usage(self, tenant_id: str, tier: str, cost: int = 1):
        """Deducts asset credits upon successful pipeline completion."""
        ledger = _TENANT_LEDGER.setdefault(tenant_id, {
            "used_assets": 0,
            "tier": tier
        })
        ledger["used_assets"] += cost
        logger.info(f"Deducted {cost} credit(s) from tenant '{tenant_id}'. Total used: {ledger['used_assets']}")

metering_service = MeteringService()
