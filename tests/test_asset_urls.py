"""Addresses for the app's stylesheets and scripts that change when the file
does (cyvetech_ui/cyvetech_ui/asset_urls.py), as hooks.py hands them to the desk."""

import os
import re
import tempfile
import unittest

from cyvetech_ui import hooks
from cyvetech_ui.cyvetech_ui import asset_urls

VERSIONED = re.compile(r"^/assets/cyvetech_ui/(css|js)/[\w.]+\?v=[0-9a-f]{10}$")


class Versioned(unittest.TestCase):
	def setUp(self):
		folder = tempfile.TemporaryDirectory()
		self.addCleanup(folder.cleanup)
		self.public = folder.name
		os.makedirs(os.path.join(self.public, "js"))
		self.write("one")

	def write(self, text):
		with open(os.path.join(self.public, "js", "x.js"), "w", encoding="utf-8") as asset:
			asset.write(text)

	def url(self):
		return asset_urls.versioned("/assets/cyvetech_ui/js/x.js", public=self.public)

	def test_the_address_carries_a_hash_of_the_contents(self):
		self.assertRegex(self.url(), r"^/assets/cyvetech_ui/js/x\.js\?v=[0-9a-f]{10}$")

	def test_it_changes_when_the_file_does_and_only_then(self):
		first = self.url()
		self.assertEqual(self.url(), first)
		self.write("two")
		self.assertNotEqual(self.url(), first)

	def test_anything_else_is_left_as_it_is(self):
		for path in (
			"/assets/frappe/js/x.js",  # another app's
			"/assets/cyvetech_ui/js/missing.js",  # not there: never an error in hooks.py
			"/assets/cyvetech_ui/js/x.js?v=1",  # already has a query
			"cyvetech_ui.bundle.js",  # a bundle: Frappe hashes those itself
		):
			self.assertEqual(asset_urls.versioned(path, public=self.public), path)


class Hooks(unittest.TestCase):
	def test_every_desk_file_is_asked_for_by_an_address_that_follows_its_contents(self):
		includes = hooks.app_include_css + hooks.app_include_js
		self.assertEqual(len(includes), 4)
		for url in includes:
			self.assertRegex(url, VERSIONED)
			path = url.split("?")[0][len(asset_urls.PREFIX) :]
			self.assertTrue(os.path.isfile(os.path.join(asset_urls.PUBLIC, *path.split("/"))), path)

	def test_the_sign_in_page_asks_for_its_stylesheet_and_script_the_same_way(self):
		template = os.path.join(os.path.dirname(asset_urls.PUBLIC), "www", "login.html")
		with open(template, encoding="utf-8") as page:
			source = page.read()
		self.assertIn('href="{{ cvt.stylesheet }}"', source)
		self.assertIn('src="{{ cvt.script }}"', source)
		self.assertRegex(asset_urls.versioned("/assets/cyvetech_ui/css/cyvetech_ui_login.css"), VERSIONED)
		self.assertRegex(asset_urls.versioned("/assets/cyvetech_ui/js/cyvetech_ui_login.js"), VERSIONED)
