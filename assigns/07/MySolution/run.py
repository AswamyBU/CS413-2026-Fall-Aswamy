"""Start the LAMBDA3 JSON-RPC service: python MySolution/run.py [--port 8000]"""

import argparse
import logging


def main() -> None:
    # Imports live here so the interpreter's spawned worker processes, which
    # re-import this file as __mp_main__, do not load Flask.
    from lambda_rpc.app import create_app

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_app()
    print(f"LAMBDA3 JSON-RPC service: POST http://{args.host}:{args.port}/rpc")
    app.run(host=args.host, port=args.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
