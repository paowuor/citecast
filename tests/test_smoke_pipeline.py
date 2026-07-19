from app.core.pipeline import CiteCastPipeline


def test_pipeline_job_lifecycle_works_with_local_storage(tmp_path):
    document_path = tmp_path / "sample.txt"
    document_path.write_text("This is a sample document for smoke testing.", encoding="utf-8")

    pipeline = CiteCastPipeline(b2_bucket="local-smoke")
    job_id = pipeline.create_job(str(document_path), audience="executive", num_scenes=2)

    assert job_id.startswith("job_")
    assert pipeline.active_jobs[job_id].status == "pending"

    status = pipeline.get_job_status(job_id)
    assert status is not None
    assert status["audience"] == "executive"
