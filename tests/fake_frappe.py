"""A small in-memory stand-in for the parts of Frappe the app's server code uses.

Enough to run branding, desk modules, alerts, permissions, alert delivery and
the boot payload without a bench: tables are lists of dicts, filters support
"=", "in", "is set" and "is not set", and every write is recorded so a test
can check what was written and what was not.

install() puts it in sys.modules as `frappe` (and its submodules) and returns
it; reset() empties it between tests.
"""

import datetime
import re
import sys
import types


class _dict(dict):
	__getattr__ = dict.get

	def __setattr__(self, key, value):
		self[key] = value


class ValidationError(Exception):
	pass


class PermissionError(Exception):  # noqa: A001 — Frappe's own name
	pass


def _matches(row, filters):
	for key, condition in (filters or {}).items():
		value = row.get(key)
		if isinstance(condition, (list, tuple)):
			op, operand = condition[0], condition[1] if len(condition) > 1 else None
			if op == "in":
				if value not in operand:
					return False
			elif op == "is":
				is_set = value not in (None, "")
				if (operand == "set") != is_set:
					return False
			elif op == "=":
				if value != operand:
					return False
			else:
				raise NotImplementedError(op)
		elif value != condition:
			return False
	return True


class FakeDB:
	def __init__(self, fake):
		self.fake = fake

	def exists(self, doctype, name=None):
		if doctype == "DocType":
			return name in self.fake.doctypes
		return any(row.get("name") == name for row in self.fake.tables.get(doctype, []))

	def get_single_value(self, doctype, fieldname):
		return self.fake.singles.get(doctype, {}).get(fieldname)

	def set_single_value(self, doctype, fieldname, value):
		self.fake.writes.append(("single", doctype, fieldname, value))
		self.fake.singles.setdefault(doctype, {})[fieldname] = value

	def get_singles_dict(self, doctype):
		if self.fake.fail_singles:
			raise RuntimeError("database is down")
		return dict(self.fake.singles.get(doctype, {}))

	def get_default(self, key):
		return self.fake.defaults.get(key)

	def set_default(self, key, value):
		if value is None:
			self.fake.defaults.pop(key, None)
		else:
			self.fake.defaults[key] = value

	def get_value(self, doctype, name, fieldname):
		for row in self.fake.tables.get(doctype, []):
			if row.get("name") == name:
				return row.get(fieldname)
		return None

	def set_value(self, doctype, name, fieldname, value, update_modified=True):
		self.fake.writes.append(("value", doctype, name, fieldname, value))
		for row in self.fake.tables.get(doctype, []):
			if row.get("name") == name:
				row[fieldname] = value

	def delete(self, doctype, filters):
		self.fake.writes.append(("delete", doctype, dict(filters)))
		table = self.fake.tables.get(doctype, [])
		self.fake.tables[doctype] = [row for row in table if not _matches(row, filters)]

	def escape(self, value):
		return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


class FakeCache:
	def __init__(self, fake):
		self.fake = fake

	def delete_key(self, key):
		self.fake.cleared.append(key)


class Meta:
	def __init__(self, labels):
		self.labels = labels

	def get_label(self, fieldname):
		return self.labels.get(fieldname, fieldname)


class Row(_dict):
	"""A child-table row, with the attribute access Frappe's rows have."""

	def as_dict(self):
		return dict(self)


class Document:
	"""The part of frappe.model.document.Document the controllers use."""

	_tables = ()
	_labels = {}

	def __init__(self, data=None):
		data = dict(data or {})
		self.__dict__["_data"] = {}
		self.meta = Meta(self._labels)
		for key, value in data.items():
			self.set(key, value)

	def __getattr__(self, key):
		if key.startswith("__"):
			raise AttributeError(key)
		return self.__dict__["_data"].get(key)

	def __setattr__(self, key, value):
		if key == "meta":
			self.__dict__[key] = value
		else:
			self.__dict__["_data"][key] = value

	def get(self, key, default=None):
		value = self.__dict__["_data"].get(key)
		return default if value is None else value

	def set(self, key, value):
		if key in self._tables:
			value = [row if isinstance(row, Row) else Row(row) for row in (value or [])]
		self.__dict__["_data"][key] = value

	def append(self, table, row):
		self.__dict__["_data"].setdefault(table, []).append(Row(row))

	def as_dict(self):
		return dict(self.__dict__["_data"])

	def db_set(self, key, value):
		self.set(key, value)


def install():
	fake = types.ModuleType("frappe")
	fake._dict = _dict
	fake._ = lambda text: text
	fake.bold = lambda text: f"<b>{text}</b>"
	fake.ValidationError = ValidationError
	fake.PermissionError = PermissionError
	fake.whitelist = lambda *args, **kwargs: (lambda fn: fn)

	def throw(message, exc=ValidationError, **kwargs):
		raise exc(message)

	fake.throw = throw

	def only_for(roles):
		roles = [roles] if isinstance(roles, str) else roles
		if not set(roles) & set(fake.get_roles(fake.session.user)):
			raise PermissionError(f"only for {roles}")

	fake.only_for = only_for

	def get_all(doctype, filters=None, fields=None, pluck=None, order_by=None, limit=None, or_filters=None):
		fake.queries.append(_dict(doctype=doctype, filters=filters, fields=fields, or_filters=or_filters, limit=limit))
		if doctype in fake.fail_get_all:
			raise RuntimeError("query failed")
		rows = [row for row in fake.tables.get(doctype, []) if _matches(row, filters)]
		if or_filters:
			rows = [row for row in rows if any(_matches(row, {k: v}) for k, v in or_filters.items())]
		if limit:
			rows = rows[:limit]
		if pluck:
			return [row.get(pluck) for row in rows]
		return [_dict(row) for row in rows]

	fake.get_all = get_all

	class Inserted(_dict):
		"""A document built with frappe.get_doc({...}), recorded on this fake when inserted."""

		def insert(self, ignore_permissions=None):
			fake.inserted.append(dict(self))
			name = f"{self['doctype']}-{len(fake.inserted)}"
			fake.tables.setdefault(self["doctype"], []).append(dict(self, name=name))
			return self

	def get_doc(arg, name=None):
		if isinstance(arg, dict):
			return Inserted(arg)
		return fake.docs[(arg, name)]

	fake.get_doc = get_doc
	fake.get_roles = lambda user=None: fake.roles.get(user or fake.session.user, [])
	fake.clear_cache = lambda *a, **k: fake.cleared.append("all")
	fake.clear_document_cache = lambda doctype, name=None: fake.cleared.append(f"doc:{doctype}")
	fake.log_error = lambda *a, **k: fake.errors.append(k.get("title") or (a[0] if a else ""))
	fake.msgprint = lambda *a, **k: fake.messages.append(a[0] if a else k.get("msg"))
	fake.enqueue = lambda fn, **kwargs: fake.enqueued.append((fn, kwargs))
	fake.db = FakeDB(fake)
	fake.cache = FakeCache(fake)

	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda value: int(float(value)) if str(value or "").strip().lstrip("-").replace(".", "", 1).isdigit() else 0
	utils.strip_html = lambda text: re.sub(r"<[^>]+>", "", text or "")
	utils.today = lambda: fake.today
	utils.now_datetime = lambda: datetime.datetime(2026, 9, 28, 9, 0)
	fake.utils = utils

	model = types.ModuleType("frappe.model")
	document = types.ModuleType("frappe.model.document")
	document.Document = Document
	model.document = document

	sys.modules.update({
		"frappe": fake,
		"frappe.utils": utils,
		"frappe.model": model,
		"frappe.model.document": document,
	})
	reset(fake)
	return fake


def reset(fake):
	fake.session = _dict(user="jane@example.com")
	fake.today = "2026-09-28"
	fake.doctypes = set()
	fake.singles = {}
	fake.defaults = {}
	fake.tables = {}
	fake.docs = {}
	fake.roles = {}
	fake.writes = []
	fake.queries = []
	fake.cleared = []
	fake.errors = []
	fake.messages = []
	fake.enqueued = []
	fake.inserted = []
	fake.fail_get_all = set()
	fake.fail_singles = False


def fresh_import(dotted):
	"""Import one of the app's modules against the fake installed now.

	Modules that import frappe keep the frappe they first saw, so any imported
	earlier (against another test's stand-in) are dropped first. The *_rules
	modules import no Frappe and are left alone.
	"""
	import importlib

	for name in [n for n in sys.modules if n.startswith("cyvetech_ui.cyvetech_ui.") and not n.endswith("_rules")]:
		del sys.modules[name]
	return importlib.import_module(dotted)
