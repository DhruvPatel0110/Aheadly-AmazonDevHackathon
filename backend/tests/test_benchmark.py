"""
Phase 8: Synthetic Testing, Accuracy Benchmarking & Friction Verification
Runs the 25 synthetic documents in backend/sample_data/benchmark/ against ground_truth.json:
- 6 subscription/trial
- 6 utility/telecom
- 5 insurance
- 4 ambiguous
- 4 non-deadline
Measures Date Exact-Match Accuracy, Evidence Verification, Category Precision,
and records per-document latency statistics (min, median, max).
"""
import pytest
import json
import time
import statistics
from pathlib import Path
from app.engine.obligation_classifier import AnalysisEngine


@pytest.fixture(scope="module")
def benchmark_data():
    bench_dir = Path(__file__).resolve().parent.parent / "sample_data" / "benchmark"
    if not bench_dir.exists():
        bench_dir = Path("backend/sample_data/benchmark")
    gt_file = bench_dir / "ground_truth.json"
    assert gt_file.exists(), f"ground_truth.json not found in {bench_dir}"
    items = json.loads(gt_file.read_text(encoding="utf-8"))
    assert len(items) == 25, f"Expected 25 benchmark documents, found {len(items)}"
    return items


def test_benchmark_full_suite(benchmark_data):
    """
    Evaluates:
    1. Date Exact-Match Accuracy on explicit deadline documents (17 documents).
    2. Zero False Dates on ambiguous and non-deadline documents (8 documents).
    3. Evidence Verification: extracted date appears within evidence snippet (target 100%).
    4. Category Classification Precision.
    5. Latency metrics (min, median, max).
    """
    total_docs = len(benchmark_data)
    date_matches = 0
    date_evaluable = 0
    evidence_matches = 0
    evidence_evaluable = 0
    category_matches = 0
    category_evaluable = 0
    false_positive_dates = 0

    latencies = []

    for doc in benchmark_data:
        text = doc["text"]
        start_t = time.perf_counter()
        candidates = AnalysisEngine.extract_obligations(text)
        lat_ms = (time.perf_counter() - start_t) * 1000
        latencies.append(lat_ms)

        # Ambiguous or non-deadline docs
        if doc["is_ambiguous"] or not doc["is_deadline"]:
            # Must NOT produce any calendar date (e.g. 2026-xx-xx)
            for c in candidates:
                if c["candidate_date"] != "UNVERIFIED" and c["candidate_date"] is not None:
                    false_positive_dates += 1
        else:
            date_evaluable += 1
            expected_date = doc["expected_date"]
            if candidates:
                actual_date = candidates[0]["candidate_date"]
                if actual_date == expected_date:
                    date_matches += 1

                # Evidence verification
                evidence_evaluable += 1
                ev_snippet = candidates[0]["evidence_snippet"]
                # Does the evidence contain the raw or parsed date string?
                raw_str = candidates[0].get("original_date_str") or actual_date
                if raw_str in ev_snippet or actual_date in ev_snippet:
                    evidence_matches += 1

                # Category classification
                if doc.get("expected_category"):
                    category_evaluable += 1
                    actual_cat = candidates[0]["category"].value if hasattr(candidates[0]["category"], "value") else str(candidates[0]["category"])
                    if actual_cat == doc["expected_category"]:
                        category_matches += 1

    date_accuracy = (date_matches / date_evaluable * 100) if date_evaluable else 0.0
    evidence_rate = (evidence_matches / evidence_evaluable * 100) if evidence_evaluable else 0.0
    category_precision = (category_matches / category_evaluable * 100) if category_evaluable else 0.0

    min_lat = min(latencies)
    med_lat = statistics.median(latencies)
    max_lat = max(latencies)

    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS (25 Synthetic Documents)")
    print("=" * 60)
    print(f"Total Documents:             {total_docs}")
    print(f"Date Exact-Match Accuracy:   {date_accuracy:.1f}% ({date_matches}/{date_evaluable})")
    print(f"Evidence Verification Rate:  {evidence_rate:.1f}% ({evidence_matches}/{evidence_evaluable})")
    print(f"Category Precision:          {category_precision:.1f}% ({category_matches}/{category_evaluable})")
    print(f"False Positive Dates:        {false_positive_dates}")
    print(f"Latency (Min / Median / Max): {min_lat:.2f}ms / {med_lat:.2f}ms / {max_lat:.2f}ms")
    print("=" * 60)

    # Assertions
    assert false_positive_dates == 0, f"System hallucinated {false_positive_dates} dates on ambiguous/non-deadline docs!"
    assert evidence_rate == 100.0, f"Evidence verification failed! Target is 100%, got {evidence_rate:.1f}%"
    assert date_accuracy >= 90.0, f"Date exact match accuracy below threshold: {date_accuracy:.1f}%"
    assert category_precision >= 80.0, f"Category precision below threshold: {category_precision:.1f}%"
