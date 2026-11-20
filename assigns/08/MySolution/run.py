"""Start the N-Queens animation service.

    python run.py [--host 127.0.0.1] [--port 8000] [--backend compiled|interpreter]
                  [--ttl 300]

Then open http://127.0.0.1:8000/ in a browser.
"""

import argparse
import logging

from queens.server import build_service, make_server
from queens.solver import BACKENDS


def main() -> None:
    parser = argparse.ArgumentParser(description="Animated N-Queens JSON-RPC service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="compiled",
                        help="how to run queens.lam (default: LAMBDA3 compiled to Python)")
    parser.add_argument("--ttl", type=float, default=300.0,
                        help="seconds an idle stream lives before it expires")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    server = make_server(args.host, args.port, build_service(args.backend, ttl_seconds=args.ttl))
    host, port = server.server_address[:2]
    print(f"N-Queens service ({args.backend} backend): http://{host}:{port}/  (RPC: POST /rpc)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
