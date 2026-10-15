"""Loopback-only standard-library HTTP transport for the MVC workbench."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import argparse
from controller import Controller

ROOT = Path(__file__).parent
controller = Controller()

class Handler(BaseHTTPRequestHandler):
    def respond(self, code, body, content_type='application/json'):
        data = json.dumps(body).encode() if content_type == 'application/json' else body
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/api/state':
            return self.respond(200, controller.state())
        if self.path == '/api/examples':
            return self.respond(200, {p.stem: p.read_text() for p in sorted((ROOT / 'examples').glob('*.lambda'))})
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
        for script in ('examples.js', 'runtime.js', 'worker.js'):
            files['/' + script] = (script, 'text/javascript')
        if self.path not in files:
            return self.respond(404, {'error': 'Not found'})
        name, kind = files[self.path]
        self.respond(200, (ROOT / 'static' / name).read_bytes(), kind)

    def do_POST(self):
        # Disallow cross-origin browser writes to the local application.
        if self.headers.get('Origin') not in (None, f'http://{self.headers.get("Host")}'):
            return self.respond(403, {'error': 'Cross-origin requests are not allowed.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 400000:
                raise ValueError('Request is too large.')
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            if self.path == '/api/source':
                state = controller.apply(data['source'], data.get('name', 'Untitled'))
            elif self.path == '/api/action':
                state = controller.run(data['operation'])
            else:
                return self.respond(404, {'error': 'Not found'})
            self.respond(200, state)
        except (ValueError, KeyError, TypeError) as error:
            self.respond(400, {'error': str(error)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'LAMBDA workbench: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
