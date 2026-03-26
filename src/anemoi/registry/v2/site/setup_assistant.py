# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Interactive setup assistant for site agents."""

import logging
import os
import sys
from pathlib import Path

LOG = logging.getLogger(__name__)

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║           Anemoi Registry — Site Setup Assistant            ║
╚══════════════════════════════════════════════════════════════╝
"""

OVERVIEW = """
This assistant will guide you through setting up a site agent.

A site agent runs on an HPC cluster (or any machine with datasets)
and periodically reports quota usage and dataset replica status
back to the Anemoi catalogue server.

The workflow has two phases:

  Phase 1 — Setup (one-time, what we are doing now):
    • You provide the URL for your site's API endpoint.
    • We create a bootstrap file (~/.config/anemoi/site.toml).
    • We validate the server configuration.
    • We download config files from the server.

  Phase 2 — Monitoring (recurring, usually via cron):
    • Report storage/quota usage:   anemoi-registry site --storage
    • Report dataset replica status: anemoi-registry site --datasets
    • Or both at once:               anemoi-registry site --all
    • Download auxiliary files:      anemoi-registry site --update-auxiliary
"""


def _ask(prompt, default=None, choices=None):
    """Prompt the user for input.

    Parameters
    ----------
    prompt : str
        Text displayed to the user.
    default : str, optional
        Default value if the user presses Enter.
    choices : list[str], optional
        If given, only accept one of these values.
    """
    suffix = ""
    if choices:
        suffix = f" [{'/'.join(choices)}]"
    if default is not None:
        suffix += f" (default: {default})"
    suffix += ": "

    while True:
        try:
            answer = input(prompt + suffix).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)

        if not answer and default is not None:
            return default
        if choices and answer not in choices:
            print(f"  Please enter one of: {', '.join(choices)}")
            continue
        if answer:
            return answer
        print("  Please enter a value.")


def _confirm(prompt, default="y"):
    """Ask a yes/no question.

    Parameters
    ----------
    prompt : str
        Text displayed to the user.
    default : str
        Default answer ('y' or 'n').
    """
    answer = _ask(prompt, default=default, choices=["y", "n"])
    return answer.lower() == "y"


def _step(number, title):
    """Print a step header."""
    print(f"\n{'─' * 60}")
    print(f"  Step {number}: {title}")
    print(f"{'─' * 60}\n")


def run_setup_assistant():
    """Run the interactive setup assistant."""
    from .bootstrap import BOOTSTRAP_PATH, setup_bootstrap, load_bootstrap
    from .parsers import PARSERS

    print(BANNER)
    print(OVERVIEW)

    if not _confirm("Ready to begin?"):
        print("Setup cancelled.")
        return

    # ──────────────────────────────────────────────────────────
    # Step 1: Explain and collect the URL
    # ──────────────────────────────────────────────────────────
    _step(1, "Site API URL")

    print("""\
  The site URL is the API endpoint for your site on the Anemoi
  catalogue server. It looks like:

    https://<server>/api/v1/sites/<site-name>

  Your server administrator should have provided this URL.
  The <site-name> part identifies your HPC cluster or location
  (e.g. 'atos', 'lumi', 'leonardo', 'test').
""")

    # Check for existing bootstrap
    existing_url = None
    if BOOTSTRAP_PATH.exists():
        try:
            bootstrap = load_bootstrap()
            existing_url = bootstrap.get("base_url")
        except Exception:
            pass

    if existing_url:
        print(f"  An existing bootstrap was found at {BOOTSTRAP_PATH}")
        print(f"  Current URL: {existing_url}")
        print()
        if _confirm("  Use the existing URL?"):
            url = existing_url
        else:
            url = _ask("  Enter your site URL")
    else:
        url = _ask("  Enter your site URL")

    # Basic URL validation
    if not url.startswith("http://") and not url.startswith("https://"):
        print("  Note: Adding https:// prefix.")
        url = "https://" + url

    if url.startswith("http://"):
        print("  Note: Will be upgraded to HTTPS during setup.")

    print(f"\n  URL: {url}")
    if not _confirm("  Proceed with this URL?"):
        print("Setup cancelled.")
        return

    # ──────────────────────────────────────────────────────────
    # Step 2: Run bootstrap setup
    # ──────────────────────────────────────────────────────────
    _step(2, "Bootstrap and server validation")

    print("""\
  Now we will:
    a) Write the bootstrap file (~/.config/anemoi/site.toml)
    b) Contact the server and validate the configuration
    c) Download config files (monitoring, datasets, auxiliary)
""")

    if not _confirm("  Run setup now?"):
        print("Setup cancelled.")
        return

    print()
    try:
        setup_bootstrap(url)
    except SystemExit:
        print("\n  Setup encountered errors (see above).")
        print("  Fix the server-side configuration and try again.")
        return
    except Exception as e:
        print(f"\n  Setup failed: {e}")
        print("  Check the URL and your network connection.")
        return

    # ──────────────────────────────────────────────────────────
    # Step 3: Verify what was created
    # ──────────────────────────────────────────────────────────
    _step(3, "Verify configuration")

    print("  Checking what was created...\n")

    try:
        bootstrap = load_bootstrap()
    except Exception as e:
        print(f"  Could not reload bootstrap: {e}")
        return

    base_url = bootstrap.get("base_url", "?")
    config_dir = bootstrap.get("config_dir", "?")

    print(f"  Bootstrap file : {BOOTSTRAP_PATH}")
    print(f"  Base URL       : {base_url}")
    print(f"  Config dir     : {config_dir}")
    print()

    config_path = Path(config_dir) if config_dir != "?" else None
    if config_path and config_path.exists():
        configs_found = sorted(config_path.glob("*.json"))
        if configs_found:
            print("  Config files downloaded:")
            for cf in configs_found:
                print(f"    • {cf.name}")
        else:
            print("  Warning: No config files found in config directory.")
    print()
    print("  ✓ Setup complete!")

    # ──────────────────────────────────────────────────────────
    # Step 4: Explain monitoring
    # ──────────────────────────────────────────────────────────
    _step(4, "What to do next — Monitoring")

    print(f"""\
  Your site agent is now configured. The next step is to run
  monitoring commands, either manually or via a cron job.

  Available monitoring commands:

    # Report quota/storage usage to the server
    anemoi-registry site --storage

    # Report dataset replica status (checks local paths)
    anemoi-registry site --datasets

    # Run both at once
    anemoi-registry site --all

  Options:

    --dry-run           Test without sending data to the server.
                        Useful for verifying everything works first.

    --update-auxiliary   Download auxiliary files (model checkpoints,
                        etc.) defined in your site's auxiliary config.
""")

    # ──────────────────────────────────────────────────────────
    # Step 5: Offer a dry-run test
    # ──────────────────────────────────────────────────────────
    _step(5, "Test with a dry run (optional)")

    print("""\
  We can now do a quick dry-run test to verify that the monitoring
  commands work correctly without sending any data to the server.
""")

    if _confirm("  Run a dry-run test of --storage?"):
        print()
        try:
            from ..entry.site import SiteCatalogueEntry
            site = SiteCatalogueEntry(name="local")
            site.report_storage(dry_run=True)
            print("\n  ✓ Storage dry-run completed successfully!")
        except Exception as e:
            print(f"\n  Storage dry-run encountered an error: {e}")
            print("  This may be expected if the quota command")
            print("  is not available on this machine.")
    else:
        print("  Skipped.")

    print()
    if _confirm("  Run a dry-run test of --datasets?"):
        print()
        try:
            from ..entry.site import SiteCatalogueEntry
            site = SiteCatalogueEntry(name="local")
            site.report_datasets(dry_run=True)
            print("\n  ✓ Datasets dry-run completed successfully!")
        except Exception as e:
            print(f"\n  Datasets dry-run encountered an error: {e}")
            print("  This may be expected if no replicas are")
            print("  registered for this site yet.")
    else:
        print("  Skipped.")

    # ──────────────────────────────────────────────────────────
    # Step 6: Cron job guidance
    # ──────────────────────────────────────────────────────────
    _step(6, "Setting up a cron job (recommended)")

    print("""\
  For continuous monitoring, set up a cron job to run the site
  agent periodically. Here is an example crontab entry that
  runs every hour:

    0 * * * * anemoi-registry site --all >> /var/log/anemoi-site.log 2>&1

  Or a more conservative schedule (every 6 hours):

    0 */6 * * * anemoi-registry site --all >> /var/log/anemoi-site.log 2>&1

  To edit your crontab:

    crontab -e

  Make sure the anemoi-registry command is on the PATH in the
  cron environment, or use the full path to the executable.
""")

    # ──────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────
    print(f"{'═' * 60}")
    print("  Setup assistant complete!")
    print()
    print("  Quick reference:")
    print(f"    Bootstrap    : {BOOTSTRAP_PATH}")
    print(f"    Config dir   : {config_dir}")
    print(f"    Server URL   : {base_url}")
    print()
    print("  Commands:")
    print("    anemoi-registry site --storage     # quota usage")
    print("    anemoi-registry site --datasets    # replica status")
    print("    anemoi-registry site --all         # both")
    print("    anemoi-registry site --dry-run     # test mode")
    print(f"{'═' * 60}")
