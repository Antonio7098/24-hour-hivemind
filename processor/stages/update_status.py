"""
Update Status Stage - updates checklist item status after processing.

Single responsibility: Update checklist file with new status.
"""

from stageflow import StageContext, StageKind, StageOutput

from ..utils.checklist_parser import ChecklistParser
from ..checkpoint import CheckpointManager


class UpdateStatusStage:
    """Stage that updates the checklist item status."""

    name = "update_status"
    kind = StageKind.WORK

    def __init__(self, parser: ChecklistParser, runs_dir=None):
        self.parser = parser
        self.runs_dir = runs_dir

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Update the item status in the checklist."""
        # Get validation result
        validated = ctx.inputs.get_from("validate_output", "validated", default=False)
        item_id = ctx.inputs.get_from("validate_output", "item_id")
        dry_run = ctx.inputs.get_from("validate_output", "dry_run", default=False)
        run_dir_str = ctx.inputs.get_from("build_prompt", "run_dir")

        if dry_run:
            return StageOutput.ok(
                status_updated=False,
                dry_run=True,
                item_id=item_id,
            )

        if not item_id:
            return StageOutput.fail(error="No item_id provided for status update")

        # Determine new status
        if validated:
            new_status = "✅ Completed"
        else:
            # Check for checkpoint - if exists, mark as paused instead of failed
            if self.runs_dir and run_dir_str:
                from pathlib import Path

                run_dir = Path(run_dir_str)
                checkpoint_manager = CheckpointManager(self.runs_dir)
                if checkpoint_manager.can_resume(run_dir, item_id):
                    new_status = "⏸️ Paused"
                else:
                    new_status = "❌ Failed"
            else:
                new_status = "❌ Failed"

        try:
            await self.parser.update_item_status(item_id, new_status)

            ctx.try_emit_event(
                "status.updated",
                {
                    "item_id": item_id,
                    "new_status": new_status,
                },
            )

            return StageOutput.ok(
                status_updated=True,
                item_id=item_id,
                new_status=new_status,
            )

        except Exception as e:
            ctx.try_emit_event(
                "status.update_failed",
                {
                    "item_id": item_id,
                    "error": str(e),
                },
            )
            return StageOutput.fail(
                error=f"Failed to update status: {e}",
                data={"item_id": item_id},
            )
