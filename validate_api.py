"""Validate local API configuration without sending a full complaint to the service."""
import sys

import settings


def main():
    issues = []
    try:
        settings.gnani_api_key()
        print("GNANI_API_KEY: ok")
    except RuntimeError as exc:
        issues.append(str(exc))
        print("GNANI_API_KEY: missing/invalid")

    llm_base = settings.get("LLM_BASE_URL", "").strip()
    llm_model = settings.get("LLM_MODEL", "").strip()
    if llm_base or llm_model:
        if not (llm_base and llm_model):
            issues.append("LLM_BASE_URL and LLM_MODEL must both be set together for hybrid mode.")
            print("LLM config: partial/incomplete")
        elif not llm_base.startswith(("http://", "https://")):
            issues.append("LLM_BASE_URL must start with http:// or https://")
            print("LLM config: invalid URL")
        else:
            print("LLM config: ok")
    else:
        print("LLM config: not configured (rules-only mode)")

    if issues:
        print("\nFix the following before running the app:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("\nAPI configuration looks valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
