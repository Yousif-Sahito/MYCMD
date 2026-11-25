"""Validate production deployment configuration without starting external services."""

import argparse

from server.app.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    settings = Settings.load()
    if settings.environment != "production":
        raise RuntimeError("Set MYCMD_ENVIRONMENT=production")
    print("Production deployment configuration passed")
    print(f"Database: {settings.database_url.split('://', 1)[0]}")
    print(f"Public origins: {settings.public_origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
