# zeno/__main__.py — add at top, before other zeno imports
from zeno.logging_setup import configure_logging
import os
configure_logging(debug=os.environ.get("ZENO_DEBUG", "").lower() in ("1", "true"))

"""ZENO entry point."""



def main() -> None:
    """Start the ZENO assistant daemon."""
    print("ZENO starting...")


if __name__ == "__main__":
    main()
