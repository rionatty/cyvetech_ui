# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Addresses for this app's stylesheets and scripts that change when the file does.

Bench's nginx serves /assets with a year-long Cache-Control, and Frappe
passes a plain asset path (anything that is not a .bundle.) to the page
unchanged, so a browser that has a file keeps using it after an update.
A short hash of the file's contents in the query string gives each version
of a file an address of its own: a changed file is fetched the first time
a page asks for it, an unchanged one stays cached.

Used by hooks.py, so it must never raise, and it works without a site.
"""

import hashlib
import os

PREFIX = "/assets/cyvetech_ui/"
PUBLIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")


def versioned(path, public=PUBLIC):
	"""/assets/cyvetech_ui/js/x.js -> /assets/cyvetech_ui/js/x.js?v=<10 hex digits>

	The path as given if it is not one of this app's files or cannot be read.
	"""
	if not path.startswith(PREFIX) or "?" in path:
		return path
	try:
		with open(os.path.join(public, *path[len(PREFIX) :].split("/")), "rb") as asset:
			digest = hashlib.sha256(asset.read()).hexdigest()[:10]
	except OSError:
		return path
	return f"{path}?v={digest}"
