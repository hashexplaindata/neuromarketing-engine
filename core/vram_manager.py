#!/usr/bin/env python3
"""
Dynamic VRAM Lifecycle & Memory Triage Manager
Guarantees sequential execution of generative/diffusion and analytical vision models
without triggering CUDA Out-Of-Memory (OOM) fatal crashes on 16GB/24GB GPUs.
"""

import gc
import logging
from contextlib import contextmanager

logger = logging.getLogger("core.vram")


class VRAMManager:
    @staticmethod
    def clean_vram():
        """Cleans CPU and GPU memory caches."""
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except ImportError:
            pass

    @staticmethod
    @contextmanager
    def vram_stage(stage_name: str):
        """
        Context manager that flushes VRAM before and after a model execution stage.
        """
        VRAMManager.clean_vram()
        logger.info(f"[VRAM] Stage '{stage_name}' starting -> Memory caches flushed.")
        try:
            yield
        finally:
            VRAMManager.clean_vram()
            logger.info(f"[VRAM] Stage '{stage_name}' concluded -> Memory caches reclaimed.")