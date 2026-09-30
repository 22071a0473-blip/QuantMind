"""Print the installed Hindsight SDK surface used by the event backfill."""

from __future__ import annotations

import inspect

from hindsight_client import Hindsight


def main() -> None:
    for name in ("aretain", "aretain_batch", "alist_memories", "aget_bank_config", "acreate_bank"):
        method = getattr(Hindsight, name)
        print(f"{name}{inspect.signature(method)}")
    operation_names = [name for name in dir(Hindsight) if "operation" in name.lower()]
    print(f"operation-related SDK members: {operation_names}")
    print("Batch contract: aretain_batch(items=..., document_id per item, tags, metadata, update_mode, operation_id).")
    print("The installed SDK exposes no public operation-status polling method; synchronous retain is used.")


if __name__ == "__main__":
    main()
