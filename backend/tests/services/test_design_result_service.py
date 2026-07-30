"""
tests/services/test_design_result_service.py

AIHOME Phase 1 - tests for design_result_service.py: version creation +
lineage ingestion, and baseline approval (idempotency, supersession,
design_scope derivation, first-approval-for-a-scope correctness).
"""
import datetime
import hashlib
import json
from io import BytesIO

import pytest
import httpx
from PIL import Image
from sqlalchemy import BigInteger, create_engine, func, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base
from app.models.project import Project
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.models.design_tool import DesignTool
from app.models.design_job import DesignJob
from app.models.design_job_image import DesignJobImage
from app.models.design_job_execution import DesignJobExecution
from app.models.design_image_version import DesignImageVersion
from app.models.generated_asset import GeneratedAsset
from app.models.workflow_execution import WorkflowExecution
from app.crud.design_image_lineage import design_image_lineage as crud_lineage
from app.crud.approved_design_baseline import approved_design_baseline as crud_baseline

from app.integrations.storage.filesystem_storage_provider import FilesystemStorageProvider
from app.services import design_result_service
from app.services.design_result_service import (
    create_design_image_version,
    approve_design_version,
    DesignResultError,
    ingest_image_design_results,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_as_integer(_type, compiler, **kwargs):
    return "INTEGER"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_scenario(db, suffix, image_role="kitchen"):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="Design Result Test")
    db.add(proj); db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Design Result St")
    db.add(prop); db.commit(); db.refresh(prop)

    img = PropertyImage(property_id=prop.id, image_type="uploaded", image_role=image_role,
                         is_primary=1, image_url=f"https://example.com/{suffix}.jpg")
    db.add(img); db.commit(); db.refresh(img)

    tool = DesignTool(tool_code=f"TOOL-{suffix}", tool_name="Test Tool",
                       design_type="image_creation", workflow_code="WF_DESIGN_STUDIO")
    db.add(tool); db.commit(); db.refresh(tool)

    job = DesignJob(
        job_number=f"DSJ-{suffix}", project_id=proj.project_id, property_id=prop.id, tool_id=tool.id,
        tool_code=tool.tool_code, design_type=tool.design_type, workflow_code=tool.workflow_code,
        tool_options_json={"design_style": "Modern"}, effective_context_json={"x": 1},
        submitted_payload_json={"job_number": f"DSJ-{suffix}"}, status="completed",
    )
    db.add(job); db.commit(); db.refresh(job)

    db.add(DesignJobImage(design_job_id=job.id, property_image_id=img.id, input_role="primary"))
    db.commit()

    wf_exec = WorkflowExecution(
        execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
        workflow_code="WF_DESIGN_STUDIO", status="Completed", priority="Normal",
        completed_at=datetime.datetime.now(),
    )
    db.add(wf_exec); db.commit(); db.refresh(wf_exec)
    db.add(DesignJobExecution(
        design_job_id=job.id,
        workflow_execution_id=wf_exec.execution_id,
        attempt_number=1,
        is_current=True,
    ))
    db.commit()

    return {"project": proj, "property": prop, "image": img, "tool": tool, "job": job, "workflow_execution": wf_exec}


def _suffix():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")


def _png_bytes(color=(20, 40, 60)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (12, 8), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


class _ArtifactResponse:
    def __init__(self, data: bytes, mime_type: str = "image/png", status_code: int = 200):
        self.status_code = status_code
        self._data = data
        self.headers = {
            "Content-Type": mime_type,
            "Content-Disposition": 'attachment; filename="generated.png"',
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def iter_bytes(self):
        midpoint = len(self._data) // 2
        yield self._data[:midpoint]
        yield self._data[midpoint:]


def _configure_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_ROOT", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "WACP_BASE_URL", "https://devtools.example")
    monkeypatch.setattr(settings, "WACP_APPLICATION_ID", "test-app")
    monkeypatch.setattr(settings, "WACP_API_KEY", "test-key")
    monkeypatch.setattr(settings, "WACP_API_SECRET", "test-secret")
    provider = FilesystemStorageProvider()
    monkeypatch.setattr(design_result_service, "_storage_provider", provider)
    return provider


def _artifact_entry(image_id: str, data: bytes, *, url: str = "/wacp/v1/artifacts/file"):
    return {
        "artifact_type": "IMAGE",
        "image_id": image_id,
        "artifact_id": f"artifact-{image_id}",
        "url": url,
        "checksum": hashlib.sha256(data).hexdigest(),
        "mime_type": "image/png",
        "provider": "test-provider",
        "model": "test-model",
    }


class TestCreateDesignImageVersion:
    def test_first_version_is_number_one(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="properties/1/images/1/versions/v1.jpg",
            source_property_image_ids=[s["image"].id],
        )
        assert version.version_number == 1
        assert version.status == "generated"

    def test_version_numbers_increment_monotonically(self, db):
        s = _make_scenario(db, _suffix())
        v1 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg", source_property_image_ids=[s["image"].id],
        )
        assert v1.version_number == 1
        assert v2.version_number == 2

    def test_lineage_row_created_for_source_property_image(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        rows, count = crud_lineage.get_multi(db, image_version_id=version.id)
        assert count == 1
        assert rows[0].source_type == "property_image"
        assert rows[0].source_property_image_id == s["image"].id

    def test_lineage_row_created_for_refinement_of_prior_version(self, db):
        s = _make_scenario(db, _suffix())
        v1 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg", source_image_version_ids=[v1.id],
        )
        rows, count = crud_lineage.get_multi(db, image_version_id=v2.id)
        assert count == 1
        assert rows[0].source_type == "image_version"
        assert rows[0].source_image_version_id == v1.id

    def test_multiple_lineage_sources_all_recorded(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg",
            source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg",
            source_property_image_ids=[s["image"].id], source_image_version_ids=[version.id],
        )
        rows, count = crud_lineage.get_multi(db, image_version_id=v2.id)
        assert count == 2


class TestImageDesignArtifactIngestion:
    def test_standalone_artifact_is_authenticated_stored_and_linked(
        self, db, monkeypatch, tmp_path,
    ):
        scenario = _make_scenario(db, _suffix())
        provider = _configure_storage(monkeypatch, tmp_path)
        data = _png_bytes()
        calls = []

        def fake_stream(method, url, *, headers, timeout):
            calls.append({"method": method, "url": url, "headers": headers, "timeout": timeout})
            return _ArtifactResponse(data)

        monkeypatch.setattr(design_result_service.httpx, "stream", fake_stream)
        entry = _artifact_entry("standalone-1", data)
        versions = ingest_image_design_results(
            db,
            execution=scenario["workflow_execution"],
            result_data={
                "outputs": [{
                    "output_type": "artifact",
                    "title": "Generated image",
                    "content": json.dumps(entry),
                }],
            },
        )

        assert len(versions) == 1
        version = versions[0]
        assert len(calls) == 1
        assert calls[0]["method"] == "GET"
        assert calls[0]["url"] == "https://devtools.example/wacp/v1/artifacts/file"
        assert calls[0]["headers"] == {
            "X-WACP-Application-Id": "test-app",
            "X-WACP-Api-Key": "test-key",
            "X-WACP-Api-Secret": "test-secret",
        }
        assert version.generated_asset_id is not None
        asset = db.get(GeneratedAsset, version.generated_asset_id)
        assert asset is not None
        assert asset.execution_id == scenario["workflow_execution"].execution_id
        assert asset.property_id == scenario["property"].id
        assert asset.storage_path == version.storage_path
        assert asset.thumbnail_path == version.thumbnail_path
        assert version.design_job_id == scenario["job"].id
        assert version.source_provider == "test-provider"
        assert version.source_model == "test-model"
        assert version.source_checksum == entry["checksum"]
        assert version.source_artifact_url == calls[0]["url"]
        assert version.mime_type == "image/png"
        assert (version.width, version.height) == (12, 8)
        assert provider.exists(relative_path=version.storage_path)
        assert provider.exists(relative_path=version.thumbnail_path)

    @pytest.mark.parametrize(
        ("error", "message"),
        [
            (httpx.ReadTimeout("timed out"), "Network error downloading artifact"),
            (httpx.ConnectError("connection refused"), "Network error downloading artifact"),
        ],
    )
    def test_httpx_network_failures_are_retried_and_translated(
        self, monkeypatch, error, message,
    ):
        attempts = []

        def failing_stream(method, url, *, headers, timeout):
            attempts.append((method, url, headers, timeout))
            raise error

        monkeypatch.setattr(design_result_service.httpx, "stream", failing_stream)
        monkeypatch.setattr(design_result_service.time, "sleep", lambda _seconds: None)

        with pytest.raises(design_result_service.ImageDesignIngestionError, match=message):
            design_result_service._download_artifact(
                "https://devtools.example/artifact.png?token=secret#fragment",
                "image/png",
            )

        assert len(attempts) == design_result_service._ARTIFACT_DOWNLOAD_MAX_RETRIES + 1
        assert all(attempt[0] == "GET" for attempt in attempts)
        assert all(
            attempt[3] == design_result_service._ARTIFACT_DOWNLOAD_TIMEOUT_SECONDS
            for attempt in attempts
        )

    def test_httpx_non_success_response_is_translated_without_retry(self, monkeypatch):
        attempts = []

        def forbidden_stream(method, url, *, headers, timeout):
            attempts.append(url)
            return _ArtifactResponse(b"", status_code=403)

        monkeypatch.setattr(design_result_service.httpx, "stream", forbidden_stream)

        with pytest.raises(
            design_result_service.ImageDesignIngestionError,
            match=r"HTTP 403.*expected 200",
        ) as exc_info:
            design_result_service._download_artifact(
                "https://devtools.example/artifact.png?token=secret#fragment",
                "image/png",
            )

        assert attempts == [
            "https://devtools.example/artifact.png?token=secret#fragment"
        ]
        assert "token=secret" not in str(exc_info.value)
        assert "fragment" not in str(exc_info.value)

    def test_final_package_supports_multiple_images(self, db, monkeypatch, tmp_path):
        scenario = _make_scenario(db, _suffix())
        provider = _configure_storage(monkeypatch, tmp_path)
        images = {
            "https://devtools.example/a.png": _png_bytes((10, 20, 30)),
            "https://devtools.example/b.png": _png_bytes((40, 50, 60)),
        }

        def fake_stream(method, url, *, headers, timeout):
            return _ArtifactResponse(images[url])

        monkeypatch.setattr(design_result_service.httpx, "stream", fake_stream)
        entries = [
            _artifact_entry("package-a", images["https://devtools.example/a.png"], url="https://devtools.example/a.png"),
            _artifact_entry("package-b", images["https://devtools.example/b.png"], url="https://devtools.example/b.png"),
        ]
        package = {
            "design_images": entries,
            "design_context": {},
            "quality_review": {"approved": True},
            "design_recommendation": {},
            "execution_metadata": {},
        }

        versions = ingest_image_design_results(
            db,
            execution=scenario["workflow_execution"],
            result_data={"outputs": [{
                "output_type": "json",
                "title": "Final Design Package",
                "content": json.dumps(package),
            }]},
        )

        assert len(versions) == 2
        assert len({version.generated_asset_id for version in versions}) == 2
        assert len({version.storage_path for version in versions}) == 2
        assert all(provider.exists(relative_path=version.storage_path) for version in versions)
        assert all(provider.exists(relative_path=version.thumbnail_path) for version in versions)
        asset_count = db.scalar(
            select(func.count()).select_from(GeneratedAsset).where(
                GeneratedAsset.execution_id == scenario["workflow_execution"].execution_id
            )
        )
        version_count = db.scalar(
            select(func.count()).select_from(DesignImageVersion).where(
                DesignImageVersion.workflow_execution_id == scenario["workflow_execution"].execution_id
            )
        )
        assert asset_count == 2
        assert version_count == 2

    def test_repeated_synchronization_skips_before_download_or_file_write(
        self, db, monkeypatch, tmp_path,
    ):
        scenario = _make_scenario(db, _suffix())
        _configure_storage(monkeypatch, tmp_path)
        data = _png_bytes()
        download_count = 0

        def fake_stream(method, url, *, headers, timeout):
            nonlocal download_count
            download_count += 1
            return _ArtifactResponse(data)

        monkeypatch.setattr(design_result_service.httpx, "stream", fake_stream)
        result_data = {"outputs": [{
            "output_type": "artifact",
            "content": json.dumps(_artifact_entry("repeat-1", data)),
        }]}

        first = ingest_image_design_results(
            db, execution=scenario["workflow_execution"], result_data=result_data,
        )
        files_after_first = sorted(
            path.relative_to(tmp_path).as_posix()
            for path in tmp_path.rglob("*")
            if path.is_file()
        )
        second = ingest_image_design_results(
            db, execution=scenario["workflow_execution"], result_data=result_data,
        )
        files_after_second = sorted(
            path.relative_to(tmp_path).as_posix()
            for path in tmp_path.rglob("*")
            if path.is_file()
        )

        assert download_count == 1
        assert second[0].id == first[0].id
        assert second[0].generated_asset_id == first[0].generated_asset_id
        assert files_after_second == files_after_first
        assert db.scalar(select(func.count()).select_from(GeneratedAsset).where(
            GeneratedAsset.execution_id == scenario["workflow_execution"].execution_id
        )) == 1
        assert db.scalar(select(func.count()).select_from(DesignImageVersion).where(
            DesignImageVersion.workflow_execution_id == scenario["workflow_execution"].execution_id
        )) == 1

    def test_existing_unlinked_version_is_linked_without_redownload(
        self, db, monkeypatch, tmp_path,
    ):
        scenario = _make_scenario(db, _suffix())
        provider = _configure_storage(monkeypatch, tmp_path)
        data = _png_bytes()
        storage_path = provider.save_file(
            property_id=scenario["property"].id,
            category=FilesystemStorageProvider.CATEGORY_AI,
            data=data,
            filename="existing.png",
        )
        thumbnail_path = provider.generate_thumbnail(
            property_id=scenario["property"].id,
            source_relative_path=storage_path,
        )
        entry = _artifact_entry("existing-1", data)
        version = create_design_image_version(
            db,
            design_job=scenario["job"],
            workflow_execution=scenario["workflow_execution"],
            file_name="existing.png",
            storage_path=storage_path,
            thumbnail_path=thumbnail_path,
            mime_type="image/png",
            file_size=len(data),
            width=12,
            height=8,
        )
        version.source_image_id = entry["image_id"]
        version.source_checksum = entry["checksum"]
        version.source_artifact_url = "https://devtools.example/wacp/v1/artifacts/file"
        db.commit()

        def unexpected_download(*args, **kwargs):
            raise AssertionError("duplicate detection must precede download")

        monkeypatch.setattr(design_result_service.httpx, "stream", unexpected_download)
        imported = design_result_service.ingest_one_generated_image(
            db,
            execution=scenario["workflow_execution"],
            design_job=scenario["job"],
            image_entry=entry,
        )

        assert imported.id == version.id
        assert imported.generated_asset_id is not None
        assert db.get(GeneratedAsset, imported.generated_asset_id).storage_path == storage_path

    @pytest.mark.parametrize(
        ("response_mime", "checksum", "expected_message"),
        [
            ("image/jpeg", "valid", "MIME mismatch"),
            ("image/png", "invalid", "Checksum mismatch"),
        ],
    )
    def test_mime_and_checksum_failures_leave_no_rows_or_files(
        self, db, monkeypatch, tmp_path, response_mime, checksum, expected_message,
    ):
        scenario = _make_scenario(db, _suffix())
        _configure_storage(monkeypatch, tmp_path)
        data = _png_bytes()
        entry = _artifact_entry("invalid-1", data)
        if checksum == "invalid":
            entry["checksum"] = "0" * 64

        monkeypatch.setattr(
            design_result_service.httpx,
            "stream",
            lambda method, url, *, headers, timeout: _ArtifactResponse(data, response_mime),
        )
        with pytest.raises(design_result_service.ImageDesignIngestionError, match=expected_message):
            design_result_service.ingest_one_generated_image(
                db,
                execution=scenario["workflow_execution"],
                design_job=scenario["job"],
                image_entry=entry,
            )

        assert db.scalar(select(func.count()).select_from(GeneratedAsset).where(
            GeneratedAsset.execution_id == scenario["workflow_execution"].execution_id
        )) == 0
        assert db.scalar(select(func.count()).select_from(DesignImageVersion).where(
            DesignImageVersion.workflow_execution_id == scenario["workflow_execution"].execution_id
        )) == 0
        assert not any(path.is_file() for path in tmp_path.rglob("*"))

    def test_database_failure_rolls_back_asset_and_removes_new_files(
        self, db, monkeypatch, tmp_path,
    ):
        scenario = _make_scenario(db, _suffix())
        _configure_storage(monkeypatch, tmp_path)
        data = _png_bytes()
        monkeypatch.setattr(
            design_result_service.httpx,
            "stream",
            lambda method, url, *, headers, timeout: _ArtifactResponse(data),
        )

        def fail_version_creation(*args, **kwargs):
            raise RuntimeError("forced database failure")

        monkeypatch.setattr(design_result_service, "create_design_image_version", fail_version_creation)
        with pytest.raises(design_result_service.ImageDesignIngestionError, match="forced database failure"):
            design_result_service.ingest_one_generated_image(
                db,
                execution=scenario["workflow_execution"],
                design_job=scenario["job"],
                image_entry=_artifact_entry("db-failure", data),
            )

        assert db.scalar(select(func.count()).select_from(GeneratedAsset).where(
            GeneratedAsset.execution_id == scenario["workflow_execution"].execution_id
        )) == 0
        assert db.scalar(select(func.count()).select_from(DesignImageVersion).where(
            DesignImageVersion.workflow_execution_id == scenario["workflow_execution"].execution_id
        )) == 0
        assert not any(path.is_file() for path in tmp_path.rglob("*"))


class TestApproveDesignVersion:
    def test_first_approval_for_a_scope_succeeds(self, db):
        """The exact case the Property-row lock design fixes: no active
        baseline exists yet for this scope at all."""
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.status == "active"
        assert baseline.image_version_id == version.id

    def test_design_scope_derived_from_primary_image_role(self, db):
        s = _make_scenario(db, _suffix(), image_role="front_exterior")
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.design_scope == "front_exterior"

    def test_design_scope_falls_back_to_general_when_no_image_role(self, db):
        s = _make_scenario(db, _suffix(), image_role=None)
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.design_scope == "general"

    def test_reapproving_same_version_is_idempotent_noop(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline_first = approve_design_version(db, image_version_id=version.id)
        baseline_second = approve_design_version(db, image_version_id=version.id)
        assert baseline_first.id == baseline_second.id

        all_baselines, count = crud_baseline.get_multi(db, property_id=s["property"].id)
        assert count == 1  # no duplicate row created

    def test_approving_different_version_supersedes_prior_active(self, db):
        s = _make_scenario(db, _suffix())
        v1 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline1 = approve_design_version(db, image_version_id=v1.id)
        baseline2 = approve_design_version(db, image_version_id=v2.id)

        db.refresh(baseline1)
        assert baseline1.status == "superseded"
        assert baseline2.status == "active"

        db.refresh(v1)
        db.refresh(v2)
        assert v2.status == "approved"

    def test_exactly_one_active_baseline_per_scope_after_multiple_approvals(self, db):
        s = _make_scenario(db, _suffix())
        for i in range(3):
            version = create_design_image_version(
                db, design_job=s["job"], workflow_execution=s["workflow_execution"],
                file_name=f"v{i}.jpg", storage_path=f"p/v{i}.jpg", source_property_image_ids=[s["image"].id],
            )
            approve_design_version(db, image_version_id=version.id)

        active_baselines, count = crud_baseline.get_multi(db, property_id=s["property"].id, status="active")
        assert count == 1

    def test_nonexistent_version_raises_domain_error(self, db):
        with pytest.raises(DesignResultError):
            approve_design_version(db, image_version_id=999999999)

    def test_baseline_snapshots_design_job_payload_fields(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.tool_options_json == {"design_style": "Modern"}
        assert baseline.effective_context_json == {"x": 1}
        assert baseline.submitted_payload_json == {"job_number": s["job"].job_number}
