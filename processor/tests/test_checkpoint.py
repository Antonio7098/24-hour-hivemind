"""
Tests for checkpoint module - phase-based state persistence.

Tests cover:
1. Phase enum - transitions and artifact detection
2. Checkpoint dataclass - serialization, phase advancement, artifact/error tracking
3. CheckpointManager - load/save/resume functionality
4. detect_phase_completion - phase completion detection
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from ..checkpoint import (
    Phase,
    Checkpoint,
    CheckpointManager,
    detect_phase_completion,
)


class TestPhaseEnum:
    """Tests for Phase enum."""

    def test_phase_order(self):
        """Phases should be in correct order."""
        order = [
            Phase.INIT,
            Phase.RESEARCH,
            Phase.TESTS,
            Phase.EXECUTION,
            Phase.REPORT,
            Phase.COMPLETE,
        ]
        assert list(Phase) == order

    def test_next_phase_from_init(self):
        """next_phase should return RESEARCH from INIT."""
        assert Phase.next_phase(Phase.INIT) == Phase.RESEARCH

    def test_next_phase_from_research(self):
        """next_phase should return TESTS from RESEARCH."""
        assert Phase.next_phase(Phase.RESEARCH) == Phase.TESTS

    def test_next_phase_from_tests(self):
        """next_phase should return EXECUTION from TESTS."""
        assert Phase.next_phase(Phase.TESTS) == Phase.EXECUTION

    def test_next_phase_from_execution(self):
        """next_phase should return REPORT from EXECUTION."""
        assert Phase.next_phase(Phase.EXECUTION) == Phase.REPORT

    def test_next_phase_from_report(self):
        """next_phase should return COMPLETE from REPORT."""
        assert Phase.next_phase(Phase.REPORT) == Phase.COMPLETE

    def test_next_phase_from_complete(self):
        """next_phase should return None from COMPLETE."""
        assert Phase.next_phase(Phase.COMPLETE) is None

    def test_from_artifacts_non_existent_dir(self):
        """from_artifacts should return INIT for non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "non_existent"
            assert run_dir.exists() is False
            assert Phase.from_artifacts(run_dir) == Phase.INIT

    def test_from_artifacts_empty_dir(self):
        """from_artifacts should return INIT for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "empty_run"
            run_dir.mkdir()
            assert Phase.from_artifacts(run_dir) == Phase.INIT

    def test_from_artifacts_detects_complete(self):
        """from_artifacts should return COMPLETE when FINAL_REPORT.md exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "complete_run"
            run_dir.mkdir()
            report = run_dir / "FINAL_REPORT.md"
            report.write_text("# Final Report\n" + "x" * 100)
            assert Phase.from_artifacts(run_dir) == Phase.COMPLETE

    def test_from_artifacts_ignores_small_report(self):
        """from_artifacts should NOT return COMPLETE for small FINAL_REPORT.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "small_report_run"
            run_dir.mkdir()
            report = run_dir / "FINAL_REPORT.md"
            report.write_text("Short")  # Less than 100 bytes
            assert Phase.from_artifacts(run_dir) == Phase.INIT

    def test_from_artifacts_detects_report_phase(self):
        """from_artifacts should return REPORT when results exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "results_run"
            run_dir.mkdir()
            results_dir = run_dir / "results"
            results_dir.mkdir()
            (results_dir / "results.json").write_text("{}")
            assert Phase.from_artifacts(run_dir) == Phase.REPORT

    def test_from_artifacts_detects_execution_phase(self):
        """from_artifacts should return EXECUTION when tests exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "tests_run"
            run_dir.mkdir()
            tests_dir = run_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("def test(): pass")
            assert Phase.from_artifacts(run_dir) == Phase.EXECUTION

    def test_from_artifacts_detects_tests_phase_various_patterns(self):
        """from_artifacts should detect tests for various naming patterns."""
        patterns = [
            ("test_example.py", Phase.EXECUTION),
            ("example_test.py", Phase.EXECUTION),
            ("example.test.js", Phase.EXECUTION),
            ("example_test.js", Phase.EXECUTION),
            ("example_test.rs", Phase.EXECUTION),
        ]
        for filename, expected_phase in patterns:
            with tempfile.TemporaryDirectory() as tmpdir:
                run_dir = Path(tmpdir) / f"test_{filename}"
                run_dir.mkdir()
                tests_dir = run_dir / "tests"
                tests_dir.mkdir()
                (tests_dir / filename).write_text("test code")
                assert Phase.from_artifacts(run_dir) == expected_phase, (
                    f"Failed for {filename}"
                )

    def test_from_artifacts_detects_tests_phase(self):
        """from_artifacts should return TESTS when research exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "research_run"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "notes.md").write_text("# Research notes")
            assert Phase.from_artifacts(run_dir) == Phase.TESTS

    def test_from_artifacts_priorities_complete_over_results(self):
        """COMPLETE should take priority over REPORT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "complete_with_results"
            run_dir.mkdir()
            (run_dir / "FINAL_REPORT.md").write_text("# Report" + "x" * 100)
            results_dir = run_dir / "results"
            results_dir.mkdir()
            (results_dir / "results.json").write_text("{}")
            assert Phase.from_artifacts(run_dir) == Phase.COMPLETE

    def test_from_artifacts_priorities_results_over_tests(self):
        """REPORT should take priority over EXECUTION phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "results_with_tests"
            run_dir.mkdir()
            results_dir = run_dir / "results"
            results_dir.mkdir()
            (results_dir / "results.json").write_text("{}")
            tests_dir = run_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test.py").write_text("test")
            assert Phase.from_artifacts(run_dir) == Phase.REPORT


class TestCheckpointDataclass:
    """Tests for Checkpoint dataclass."""

    def test_checkpoint_creation_with_defaults(self):
        """Checkpoint should have correct default values."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        assert checkpoint.item_id == "TEST-001"
        assert checkpoint.phase == Phase.INIT
        assert checkpoint.attempt == 1
        assert checkpoint.started_at != ""
        assert checkpoint.updated_at != ""
        assert checkpoint.elapsed_ms == 0
        assert checkpoint.artifacts == {}
        assert checkpoint.errors == []
        assert checkpoint.metadata == {}

    def test_checkpoint_creation_with_custom_values(self):
        """Checkpoint should accept custom values."""
        checkpoint = Checkpoint(
            item_id="TEST-002",
            phase=Phase.RESEARCH,
            attempt=3,
            elapsed_ms=60000,
            metadata={"key": "value"},
        )
        assert checkpoint.item_id == "TEST-002"
        assert checkpoint.phase == Phase.RESEARCH
        assert checkpoint.attempt == 3
        assert checkpoint.elapsed_ms == 60000
        assert checkpoint.metadata == {"key": "value"}

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        result = checkpoint.to_dict()
        assert result["item_id"] == "TEST-001"
        assert result["phase"] == "init"
        assert result["attempt"] == 1
        assert result["started_at"] != ""
        assert result["updated_at"] != ""
        assert result["elapsed_ms"] == 0
        assert result["artifacts"] == {}
        assert result["errors"] == []
        assert result["metadata"] == {}

    def test_from_dict(self):
        """from_dict should deserialize correctly."""
        data = {
            "item_id": "TEST-001",
            "phase": "research",
            "attempt": 2,
            "started_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "elapsed_ms": 30000,
            "artifacts": {"research": ["doc.md"]},
            "errors": ["Error 1"],
            "metadata": {"key": "value"},
        }
        checkpoint = Checkpoint.from_dict(data)
        assert checkpoint.item_id == "TEST-001"
        assert checkpoint.phase == Phase.RESEARCH
        assert checkpoint.attempt == 2
        assert checkpoint.elapsed_ms == 30000
        assert checkpoint.artifacts == {"research": ["doc.md"]}
        assert checkpoint.errors == ["Error 1"]
        assert checkpoint.metadata == {"key": "value"}

    def test_from_dict_with_invalid_phase(self):
        """from_dict should raise error for invalid phase."""
        data = {"item_id": "TEST-001", "phase": "invalid_phase"}
        with pytest.raises(ValueError):
            Checkpoint.from_dict(data)

    def test_advance_phase(self):
        """advance_phase should move to next phase."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        assert checkpoint.advance_phase() is True
        assert checkpoint.phase == Phase.RESEARCH

    def test_advance_phase_no_more_phases(self):
        """advance_phase should return False when no more phases."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.COMPLETE)
        assert checkpoint.advance_phase() is False
        assert checkpoint.phase == Phase.COMPLETE

    def test_advance_phase_updates_timestamp(self):
        """advance_phase should update updated_at timestamp."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        original_updated = checkpoint.updated_at
        import time

        time.sleep(0.01)
        checkpoint.advance_phase()
        assert checkpoint.updated_at > original_updated

    def test_add_artifact(self):
        """add_artifact should record artifact for phase."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_artifact("research", "doc.md")
        assert checkpoint.artifacts == {"research": ["doc.md"]}

    def test_add_artifact_multiple(self):
        """add_artifact should append to existing artifacts."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_artifact("research", "doc1.md")
        checkpoint.add_artifact("research", "doc2.md")
        assert checkpoint.artifacts == {"research": ["doc1.md", "doc2.md"]}

    def test_add_artifact_prevents_duplicates(self):
        """add_artifact should not add duplicate paths."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_artifact("research", "doc.md")
        checkpoint.add_artifact("research", "doc.md")
        assert checkpoint.artifacts == {"research": ["doc.md"]}

    def test_add_artifact_different_phases(self):
        """add_artifact should track artifacts per phase."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_artifact("research", "doc.md")
        checkpoint.add_artifact("tests", "test.py")
        assert checkpoint.artifacts == {"research": ["doc.md"], "tests": ["test.py"]}

    def test_add_error(self):
        """add_error should record error with timestamp."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_error("Something went wrong")
        assert len(checkpoint.errors) == 1
        assert "Something went wrong" in checkpoint.errors[0]
        assert "[" in checkpoint.errors[0]  # Timestamp format

    def test_add_error_multiple(self):
        """add_error should record multiple errors."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_error("Error 1")
        checkpoint.add_error("Error 2")
        assert len(checkpoint.errors) == 2
        assert "Error 1" in checkpoint.errors[0]
        assert "Error 2" in checkpoint.errors[1]


class TestCheckpointManager:
    """Tests for CheckpointManager."""

    def test_manager_creation(self):
        """CheckpointManager should initialize with runs_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            assert manager.runs_dir == Path(tmpdir)

    def test_get_checkpoint_path(self):
        """get_checkpoint_path should return correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "runs" / "TEST-001"
            path = manager.get_checkpoint_path(run_dir)
            assert path == run_dir / ".checkpoint.json"

    def test_load_new_checkpoint(self):
        """load should create new checkpoint when none exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            checkpoint = manager.load(run_dir, "TEST-001")
            assert checkpoint.item_id == "TEST-001"
            assert checkpoint.phase == Phase.INIT

    def test_load_existing_checkpoint(self):
        """load should load existing checkpoint from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()

            existing_checkpoint = Checkpoint(
                item_id="TEST-001",
                phase=Phase.RESEARCH,
            )
            manager.save(run_dir, existing_checkpoint)

            loaded = manager.load(run_dir, "TEST-001")
            assert loaded.phase == Phase.RESEARCH
            assert loaded.item_id == "TEST-001"

    def test_load_detects_existing_progress(self):
        """load should detect phase from existing artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "doc.md").write_text("# Research")
            checkpoint = manager.load(run_dir, "TEST-001")
            assert checkpoint.phase == Phase.TESTS
            assert "research" in checkpoint.artifacts

    def test_save_and_load_roundtrip(self):
        """save and load should maintain data integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()

            original = Checkpoint(
                item_id="TEST-001",
                phase=Phase.EXECUTION,
                attempt=2,
                elapsed_ms=120000,
            )
            original.add_artifact("research", "doc.md")
            original.add_artifact("tests", "test.py")
            original.add_error("Minor issue")
            original.metadata["key"] = "value"

            manager.save(run_dir, original)
            loaded = manager.load(run_dir, "TEST-001")

            assert loaded.item_id == original.item_id
            assert loaded.phase == original.phase
            assert loaded.attempt == original.attempt
            assert loaded.elapsed_ms == original.elapsed_ms
            assert loaded.artifacts == original.artifacts
            assert loaded.errors == original.errors
            assert loaded.metadata == original.metadata

    def test_delete_checkpoint(self):
        """delete should remove checkpoint file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            checkpoint_path = run_dir / ".checkpoint.json"
            checkpoint_path.write_text("{}")

            assert checkpoint_path.exists()
            manager.delete(run_dir)
            assert checkpoint_path.exists() is False

    def test_delete_nonexistent(self):
        """delete should not fail for non-existent checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            manager.delete(run_dir)  # Should not raise

    def test_can_resume_init_phase(self):
        """can_resume should return False for INIT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            result = manager.can_resume(run_dir, "TEST-001")
            assert result is False

    def test_can_resume_complete_phase(self):
        """can_resume should return False for COMPLETE phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            (run_dir / "FINAL_REPORT.md").write_text("# Report" + "x" * 100)
            result = manager.can_resume(run_dir, "TEST-001")
            assert result is False

    def test_can_resume_tests_phase(self):
        """can_resume should return True for TESTS phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "doc.md").write_text("# Research")
            result = manager.can_resume(run_dir, "TEST-001")
            assert result is True

    def test_get_resume_instructions_tests_phase(self):
        """get_resume_instructions should return correct instructions for TESTS phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "doc.md").write_text("# Research")

            checkpoint = manager.load(run_dir, "TEST-001")
            instructions = manager.get_resume_instructions(checkpoint)

            assert "Research phase complete" in instructions
            assert "SKIP research phase" in instructions

    def test_get_resume_instructions_execution_phase(self):
        """get_resume_instructions should return correct instructions for EXECUTION phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            tests_dir = run_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("test")

            checkpoint = manager.load(run_dir, "TEST-001")
            instructions = manager.get_resume_instructions(checkpoint)

            assert "Tests created" in instructions
            assert "SKIP research and test creation phases" in instructions

    def test_get_resume_instructions_report_phase(self):
        """get_resume_instructions should return correct instructions for REPORT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            results_dir = run_dir / "results"
            results_dir.mkdir()
            (results_dir / "results.json").write_text("{}")

            checkpoint = manager.load(run_dir, "TEST-001")
            instructions = manager.get_resume_instructions(checkpoint)

            assert "Tests executed" in instructions
            assert "SKIP all phases except report generation" in instructions

    def test_get_resume_instructions_init_phase(self):
        """get_resume_instructions should return empty string for INIT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()

            checkpoint = manager.load(run_dir, "TEST-001")
            instructions = manager.get_resume_instructions(checkpoint)

            assert instructions == ""

    def test_scan_artifacts_research(self):
        """_scan_artifacts should find research markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "doc1.md").write_text("# Doc 1")
            (research_dir / "doc2.md").write_text("# Doc 2")

            checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
            manager._scan_artifacts(run_dir, checkpoint)

            assert "research" in checkpoint.artifacts
            assert len(checkpoint.artifacts["research"]) == 2

    def test_scan_artifacts_tests(self):
        """_scan_artifacts should find test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            tests_dir = run_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_a.py").write_text("test")
            (tests_dir / "b_test.js").write_text("test")

            checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
            manager._scan_artifacts(run_dir, checkpoint)

            assert "tests" in checkpoint.artifacts
            assert len(checkpoint.artifacts["tests"]) == 2

    def test_scan_artifacts_results(self):
        """_scan_artifacts should find result JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            results_dir = run_dir / "results"
            results_dir.mkdir()
            (results_dir / "results.json").write_text("{}")
            (results_dir / "output_results.json").write_text("{}")

            checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
            manager._scan_artifacts(run_dir, checkpoint)

            assert "execution" in checkpoint.artifacts
            assert len(checkpoint.artifacts["execution"]) == 2


class TestDetectPhaseCompletion:
    """Tests for detect_phase_completion function."""

    def test_detect_research_phase_complete(self):
        """detect_phase_completion should return True for complete RESEARCH phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "doc.md").write_text("# Research")
            result = detect_phase_completion(run_dir, Phase.RESEARCH)
            assert result is True

    def test_detect_research_phase_incomplete(self):
        """detect_phase_completion should return False for incomplete RESEARCH phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            result = detect_phase_completion(run_dir, Phase.RESEARCH)
            assert result is False

    def test_detect_tests_phase_complete(self):
        """detect_phase_completion should return True for complete TESTS phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            tests_dir = run_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("test")
            result = detect_phase_completion(run_dir, Phase.TESTS)
            assert result is True

    def test_detect_tests_phase_incomplete(self):
        """detect_phase_completion should return False for incomplete TESTS phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            result = detect_phase_completion(run_dir, Phase.TESTS)
            assert result is False

    def test_detect_execution_phase_complete(self):
        """detect_phase_completion should return True for complete EXECUTION phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            results_dir = run_dir / "results"
            results_dir.mkdir()
            (results_dir / "results.json").write_text("{}")
            result = detect_phase_completion(run_dir, Phase.EXECUTION)
            assert result is True

    def test_detect_execution_phase_incomplete(self):
        """detect_phase_completion should return False for incomplete EXECUTION phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            result = detect_phase_completion(run_dir, Phase.EXECUTION)
            assert result is False

    def test_detect_report_phase_complete(self):
        """detect_phase_completion should return True for complete REPORT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            report = run_dir / "FINAL_REPORT.md"
            report.write_text("# Report" + "x" * 100)
            result = detect_phase_completion(run_dir, Phase.REPORT)
            assert result is True

    def test_detect_report_phase_small_report(self):
        """detect_phase_completion should return False for small FINAL_REPORT.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            report = run_dir / "FINAL_REPORT.md"
            report.write_text("Short")
            result = detect_phase_completion(run_dir, Phase.REPORT)
            assert result is False

    def test_detect_init_phase_always_false(self):
        """detect_phase_completion should return False for INIT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            result = detect_phase_completion(run_dir, Phase.INIT)
            assert result is False

    def test_detect_complete_phase_always_false(self):
        """detect_phase_completion should return False for COMPLETE phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            result = detect_phase_completion(run_dir, Phase.COMPLETE)
            assert result is False


class TestCheckpointEdgeCases:
    """Tests for edge cases and error handling."""

    def test_load_corrupted_checkpoint(self):
        """load should recover from corrupted checkpoint file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "TEST-001"
            run_dir.mkdir()
            checkpoint_path = run_dir / ".checkpoint.json"
            checkpoint_path.write_text("invalid json{")

            checkpoint = manager.load(run_dir, "TEST-001")
            assert checkpoint.phase == Phase.INIT
            assert checkpoint.item_id == "TEST-001"

    def test_save_to_nonexistent_directory(self):
        """save should create parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(Path(tmpdir))
            run_dir = Path(tmpdir) / "nested" / "path" / "TEST-001"
            checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.RESEARCH)

            manager.save(run_dir, checkpoint)
            assert (run_dir / ".checkpoint.json").exists()

    def test_checkpoint_with_empty_artifacts(self):
        """Checkpoint should handle empty artifacts dict."""
        checkpoint = Checkpoint(item_id="TEST-001", phase=Phase.INIT)
        checkpoint.add_artifact("research", "doc.md")
        checkpoint.artifacts["research"].clear()
        result = checkpoint.to_dict()
        assert result["artifacts"] == {"research": []}

    def test_phase_from_artifacts_with_nested_dirs(self):
        """from_artifacts should work with nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "project"
            run_dir.mkdir()
            research_dir = run_dir / "research"
            research_dir.mkdir()
            (research_dir / "doc.md").write_text("# Research")
            assert Phase.from_artifacts(run_dir) == Phase.TESTS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
