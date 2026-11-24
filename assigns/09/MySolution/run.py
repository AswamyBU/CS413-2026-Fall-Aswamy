"""Start LAMBDA Studio: the studio page, the in-memory database service, and
the Assign07 LAMBDA3 service, all on http://127.0.0.1:8009/.

    python run.py [--host 127.0.0.1] [--port 8009] [--db-only]

--db-only starts just the database service (and the page, which will report
LAMBDA3 as unreachable).

All imports live inside main(): the LAMBDA3 service starts worker processes
with `spawn`, and those re-import this file; they must not start a server.
"""

import argparse
import logging


def main() -> None:
    parser = argparse.ArgumentParser(description="LAMBDA Studio with the in-memory database service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--db-only", action="store_true",
                        help="do not mount the Assign07 LAMBDA3 service at /lambda/rpc")
    args = parser.parse_args()

    from werkzeug.serving import run_simple

    from studio_host import create_studio_app

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_studio_app(with_lambda=not args.db_only)
    base = f"http://{args.host}:{args.port}"
    print(f"LAMBDA Studio:     {base}/")
    print(f"Database API:      {base}/api/v1  (in memory: cleared when this process stops)")
    if not args.db_only:
        print(f"LAMBDA3 JSON-RPC:  {base}/lambda/rpc")
    run_simple(args.host, args.port, app, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
