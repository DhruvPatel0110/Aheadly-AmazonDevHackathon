"""
Integration tests for FastAPI REST endpoints and database lifespan.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.models import SourceCreate, DeadlineCreate, DeadlineCategory, ObligationType, DeadlineStatus
from app.services.deadline_service import DeadlineService


@pytest.mark.asyncio
async def test_health_and_info_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["budget_mode"] == "Strict ₹0 out-of-pocket"

        info_res = await ac.get("/api/info")
        assert info_res.status_code == 200
        info_data = info_res.json()
        assert info_data["track"] == "Alexa+"
        assert info_data["mcp_server"] == "deadline-rescue-mcp"


@pytest.mark.asyncio
async def test_deadlines_api_endpoints():
    await init_db()
    source = await DeadlineService.create_source(
        SourceCreate(title="API Test Source", raw_text="Electric bill due 2026-10-30 amount INR 1200")
    )
    deadline = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Tata Power",
            category=DeadlineCategory.UTILITY,
            obligation_type=ObligationType.PAYMENT_DUE,
            candidate_date="2026-10-30",
            amount=1200.0,
            evidence_snippet="Electric bill due 2026-10-30 amount INR 1200",
            status=DeadlineStatus.NEEDS_REVIEW
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test stats
        stats_res = await ac.get("/api/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total"] >= 1

        # Test list
        list_res = await ac.get("/api/deadlines")
        assert list_res.status_code == 200
        deadlines = list_res.json()
        assert any(d["id"] == deadline.id for d in deadlines)

        # Test get single
        get_res = await ac.get(f"/api/deadlines/{deadline.id}")
        assert get_res.status_code == 200
        assert get_res.json()["provider_name"] == "Tata Power"

        # Test patch update
        patch_res = await ac.patch(
            f"/api/deadlines/{deadline.id}",
            json={"status": "confirmed"}
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "confirmed"

        # Test audit log
        audit_res = await ac.get(f"/api/deadlines/{deadline.id}/audit")
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert len(logs) >= 2  # extracted + status_changed
