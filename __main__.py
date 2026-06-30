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
    if len(sys.argv) > 1 and sys.argv[1] == "world-batch":
        from batch_birthday.world_batch import main as world_batch_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        world_batch_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "release-status":
        from batch_birthday.release_status_cli import main as release_status_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        release_status_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "ae-batch":
        from batch_birthday.ae_batch_cli import main as ae_batch_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        ae_batch_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "generic-intro":
        from batch_birthday.generic_intro import main as generic_intro_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        generic_intro_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        from batch_birthday.acestep_env import run_doctor

        raise SystemExit(run_doctor())
    if len(sys.argv) > 1 and sys.argv[1] == "init-api":
        from batch_birthday.acestep_env import init_llm_models

        data = init_llm_models()
        print(f"LLM ready: {data.get('llm_initialized')}")
        return
    run_main()


if __name__ == "__main__":
    main()
