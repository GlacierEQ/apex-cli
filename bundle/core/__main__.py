"""
computer-user CLI — Run pipelines and skills from command line.

Usage:
  python -m computer-user boot                    # Verify system ready
  python -m computer-user skill <name>            # Run a skill
  python -m computer-user linkedin --url <url>    # Fetch LinkedIn profile
  python -m computer-user gmail --mode triage     # Gmail triage
  python -m computer-user pipeline                # Full boot pipeline
"""

import argparse
import json
import sys
from pathlib import Path


def cmd_boot(args):
    """Verify system is ready."""
    from pipeline import make_boot_pipeline
    p = make_boot_pipeline()
    report = p.run()
    if report["status"] != "passed":
        sys.exit(1)


def cmd_pipeline(args):
    """Run full boot pipeline."""
    from pipeline import make_boot_pipeline
    p = make_boot_pipeline()
    report = p.run()
    print(json.dumps(report, indent=2))


def cmd_skill(args):
    """Run a specific skill."""
    from pipeline import make_skill_pipeline
    p = make_skill_pipeline(args.name)
    p.set("services_needed", args.services.split(",") if args.services else [])
    report = p.run()
    if report["status"] != "passed":
        sys.exit(1)


def cmd_linkedin(args):
    """Fetch LinkedIn profile via headless browser."""
    from browser_adapter import get_backend

    def fetch_linkedin(context):
        b = get_backend(context.get("backend"))

        if args.cookie:
            # Inject li_at cookie
            b.navigate("https://www.linkedin.com/")
            b.wait(2000)
            b.eval_js(f"""
                document.cookie = "li_at={args.cookie}; domain=.linkedin.com; path=/; secure";
            """)
            b.wait(1000)

        if args.email and args.password:
            # Login
            b.navigate("https://www.linkedin.com/login")
            b.wait(3000)
            b.evaluate = b.eval_js
            # Use keyboard approach
            b.eval_js(f"""
                (() => {{
                    const inputs = document.querySelectorAll('input[type="email"]');
                    const target = inputs[inputs.length - 1];
                    if (target) {{ target.focus(); }}
                }})()
            """)
            b.type_text(args.email)
            b.press_key("Tab")
            b.type_text(args.password)
            b.press_key("Enter")
            b.wait(8000)

            url = b.get_url()
            if "login" in url or "authwall" in url:
                print("LOGIN FAILED", file=sys.stderr)
                b.close()
                sys.exit(1)

        # Navigate to profile
        b.navigate(args.url)
        b.wait(5000)

        # Expand sections
        for _ in range(3):
            b.eval_js("""
                document.querySelectorAll('button').forEach(b => {
                    if (/see more|show more|see all|expand/i.test(b.innerText)) b.click();
                });
            """)
            b.wait(1000)

        text = b.get_text(max_chars=30000)
        b.close()
        return text

    from pipeline import Pipeline
    p = Pipeline("linkedin-fetch")
    p.phase("fetch", fetch_linkedin)
    report = p.run()

    if p.status == "passed":
        # Output the profile text
        text = p.get("fetch_result")
        if text:
            print(text)
    else:
        sys.exit(1)


def cmd_gmail(args):
    """Run Gmail operations."""
    from pipeline import make_skill_pipeline
    p = make_skill_pipeline("gmail-orchestrator", services=["gmail"])
    p.set("gmail_mode", args.mode)
    report = p.run()
    if report["status"] != "passed":
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="computer-user",
        description="Platform-agnostic desktop automation agent"
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # boot
    sub.add_parser("boot", help="Verify system is ready")

    # pipeline
    sub.add_parser("pipeline", help="Run full boot pipeline")

    # skill
    skill_p = sub.add_parser("skill", help="Run a specific skill")
    skill_p.add_argument("name", help="Skill name (e.g. gmail-orchestrator)")
    skill_p.add_argument("--services", help="Required services (comma-separated)")

    # linkedin
    li_p = sub.add_parser("linkedin", help="Fetch LinkedIn profile")
    li_p.add_argument("--url", required=True, help="LinkedIn profile URL")
    li_p.add_argument("--email", help="LinkedIn email for login")
    li_p.add_argument("--password", help="LinkedIn password")
    li_p.add_argument("--cookie", help="li_at cookie value")
    li_p.add_argument("--backend", help="Browser backend (puppeteer/tasklet)")

    # gmail
    gmail_p = sub.add_parser("gmail", help="Gmail operations")
    gmail_p.add_argument("--mode", default="triage", choices=["triage", "forensic", "draft", "full"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "boot": cmd_boot,
        "pipeline": cmd_pipeline,
        "skill": cmd_skill,
        "linkedin": cmd_linkedin,
        "gmail": cmd_gmail,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
