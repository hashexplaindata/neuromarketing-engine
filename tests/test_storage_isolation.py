"""
Multi-Tenancy Ephemeral Workspace Isolation Tests
Verifies zero data collisions between concurrent agency sessions
"""

import os
import shutil
import pytest
from core.storage import EphemeralWorkspaceManager

def test_tenant_workspace_isolation(tmp_path):
    manager = EphemeralWorkspaceManager(root_dir=str(tmp_path))
    
    # Simulate concurrent requests from two different agencies
    agency_a = "agency_omnicom"
    agency_b = "agency_wpp"
    session_a = "sess_001_alpha"
    session_b = "sess_002_beta"
    
    dir_a = manager.initialize_session(agency_a, session_a, b"IMAGE_DATA_A", "creative_a.png")
    dir_b = manager.initialize_session(agency_b, session_b, b"IMAGE_DATA_B", "creative_b.png")
    
    # 1. Verify directory isolation
    assert dir_a != dir_b
    assert os.path.exists(dir_a)
    assert os.path.exists(dir_b)
    assert agency_a in dir_a
    assert agency_b in dir_b
    
    # 2. Verify independent stage 01 output paths
    out_a = manager.get_stage_output_dir(agency_a, session_a, "01_asset_ingestion")
    out_b = manager.get_stage_output_dir(agency_b, session_b, "01_asset_ingestion")
    assert out_a != out_b
    
    # 3. Simulate Agency A writing metrics
    file_a = os.path.join(out_a, "low_level_metrics.json")
    with open(file_a, "w") as f:
        f.write('{"tenant": "omnicom", "entropy": 6.8}')
        
    # Simulate Agency B writing different metrics
    file_b = os.path.join(out_b, "low_level_metrics.json")
    with open(file_b, "w") as f:
        f.write('{"tenant": "wpp", "entropy": 7.4}')
        
    # 4. Verify no data overwrite
    with open(file_a, "r") as f:
        assert "omnicom" in f.read()
    with open(file_b, "r") as f:
        assert "wpp" in f.read()
        
    # 5. Test session cleanup
    manager.cleanup_session(agency_a, session_a)
    assert not os.path.exists(dir_a)
    assert os.path.exists(dir_b)
