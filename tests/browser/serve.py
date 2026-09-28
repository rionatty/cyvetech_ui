"""Serve the repository for the browser tests, with the browser's cache off.

Python's own `python -m http.server` lets a browser keep a file it has seen
and use it again without asking, so a test run can quietly load yesterday's
copy of a stylesheet or script. Every response here says no-store: each run
loads the files as they are on disk.

	python tests/browser/serve.py [port]      (default 8766)

then open http://localhost:8766/tests/browser/
"""

import functools
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class NoStore(http.server.SimpleHTTPRequestHandler):
	def end_headers(self):
		self.send_header("Cache-Control", "no-store")
		super().end_headers()


def main():
	port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
	handler = functools.partial(NoStore, directory=ROOT)
	server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
	print(f"Serving {ROOT} on http://localhost:{port}/tests/browser/ (no browser cache)")
	server.serve_forever()


if __name__ == "__main__":
	main()
