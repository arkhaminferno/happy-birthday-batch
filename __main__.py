"""Allow: python -m batch_birthday [run|scan|verify|humanize|deliver|mass-batch ...]"""

import sys

from batch_birthday.orchestrator import main as run_main


def main() -> None:
    """Dispatch to batch run, scan, humanize, or deliver subcommands."""
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        from batch_birthday.upload_scan import main as scan_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        scan_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        from batch_birthday.upload_verify import main as verify_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        verify_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "humanize":
        from batch_birthday.humanize_audio import main as humanize_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        humanize_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "deliver":
        from batch_birthday.deliver_cli import main as deliver_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        deliver_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "mass-batch":
        from batch_birthday.mass_batch import main as mass_batch_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        mass_batch_main()
        return
    run_main()


if __name__ == "__main__":
    main()
