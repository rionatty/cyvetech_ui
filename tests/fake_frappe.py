"""A small in-memory stand-in for the parts of Frappe the app's server code uses.

Enough to run branding, desk modules, alerts, permissions, alert delivery, the
boot payload, the desk home and the module pages without a bench: tables are
lists of dicts, filters support the operators the app uses ("=", "!=", "<",
">", "<=", ">=", "in", "not in", "between", "is set" and "is not set"), and
every write is recorded so a test can check what was written and what was not.

get_list is get_all with the user's read permission checked first (the
doctypes in `readable`), and both take what the app asks of them: sums,
counts, minimums and maximums written as Frappe v16 wants them ({"SUM": field,
"as": alias}) or as v15 does ("sum(`field`) as alias"), grouped by one or more
fields, sorted and limited.

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


def _comparable(value):
	"""A value as SQL would compare it: numbers as numbers, dates as their ISO text."""
	if isinstance(value, bool):
		return int(value)
	if isinstance(value, (int, float)):
		return value
	if isinstance(value, (datetime.date, datetime.datetime)):
		return str(value)
	return "" if value is None else str(value)


def _ordered(value, operand):
	a, b = _comparable(value), _comparable(operand)
	if isinstance(a, str) != isinstance(b, str):
		a, b = str(a), str(b)
	return a, b


def _meets(value, op, operand):
	if op in ("=", "=="):
		return _comparable(value) == _comparable(operand) if value is not None else operand is None
	if op == "!=":
		return value != operand
	if op in ("<", ">", "<=", ">="):
		if value in (None, ""):
			return False
		a, b = _ordered(value, operand)
		return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
	if op == "in":
		return value in operand
	if op == "not in":
		return value not in operand
	if op == "between":
		if value in (None, ""):
			return False
		low, high = operand
		above = _ordered(low, value)
		below = _ordered(value, high)
		return above[0] <= above[1] and below[0] <= below[1]
	if op == "is":
		is_set = value not in (None, "")
		return (operand == "set") == is_set
	raise NotImplementedError(op)


def _matches(row, filters):
	for key, condition in (filters or {}).items():
		value = row.get(key)
		if isinstance(condition, (list, tuple)):
			op, operand = condition[0], condition[1] if len(condition) > 1 else None
			if not _meets(value, op, operand):
				return False
		elif not _meets(value, "=", condition):
			return False
	return True


_STRING_AGGREGATE = re.compile(r"^(sum|count|min|max|avg)\(`?([\w*]+)`?\)\s+as\s+(\w+)$", re.IGNORECASE)
_ALIASED = re.compile(r"^`?(\w+)`?\s+as\s+(\w+)$", re.IGNORECASE)
FUNCTIONS = ("SUM", "COUNT", "MIN", "MAX", "AVG")


def _field(spec, strict):
	"""("plain", source, name) or ("aggregate", FUNCTION, source, name) for one field of a query.
	strict: Frappe v16, which takes a function only as a dict, never as SQL in a string."""
	if isinstance(spec, dict):
		function = next(key for key in spec if key != "as")
		if function not in FUNCTIONS:
			raise ValueError(f"unsupported function {function}")
		return ("aggregate", function, spec[function], spec.get("as") or function.lower())
	text = str(spec).strip()
	if strict and "(" in text:
		raise ValidationError(f"SQL functions are not allowed as strings in SELECT: {text}")
	found = _STRING_AGGREGATE.match(text)
	if found:
		return ("aggregate", found.group(1).upper(), found.group(2), found.group(3))
	found = _ALIASED.match(text)
	if found:
		return ("plain", found.group(1), found.group(2))
	return ("plain", text.strip("`"), text.strip("`"))


def _aggregate(function, source, rows):
	if function == "COUNT":
		return len(rows) if source == "*" else sum(1 for row in rows if row.get(source) is not None)
	values = [row.get(source) for row in rows if row.get(source) is not None]
	if not values:
		return None
	if function == "SUM":
		return sum(float(value) for value in values)
	if function == "AVG":
		return sum(float(value) for value in values) / len(values)
	return (min if function == "MIN" else max)(values, key=_comparable)


def _sort(rows, order_by):
	if not order_by:
		return rows
	for part in reversed([piece.strip() for piece in str(order_by).split(",") if piece.strip()]):
		words = part.split()
		key, descending = words[0].strip("`"), len(words) > 1 and words[1].lower() == "desc"
		present = [row for row in rows if row.get(key) not in (None, "")]
		missing = [row for row in rows if row.get(key) in (None, "")]
		present.sort(key=lambda row: _comparable(row.get(key)), reverse=descending)
		rows = present + missing
	return rows


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
		return self.fake.db_defaults.get(key)

	def set_default(self, key, value):
		if value is None:
			self.fake.db_defaults.pop(key, None)
		else:
			self.fake.db_defaults[key] = value

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

	def get_value(self, key, user=None, **kwargs):
		return self.fake.cached.get((key, user))

	def set_value(self, key, value, user=None, expires_in_sec=None, **kwargs):
		self.fake.cached[(key, user)] = value
		self.fake.cache_seconds[(key, user)] = expires_in_sec


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

	def db_set(self, key, value, **kwargs):
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

	def query(doctype, filters=None, fields=None, pluck=None, order_by=None, limit=None, or_filters=None,
			group_by=None, limit_page_length=None, checked=False, **kwargs):
		fake.queries.append(
			_dict(doctype=doctype, filters=filters, fields=fields, or_filters=or_filters, limit=limit,
				group_by=group_by, order_by=order_by, limit_page_length=limit_page_length, checked=checked)
		)
		if doctype in fake.fail_get_all:
			raise RuntimeError("query failed")
		table = fake.tables.get(doctype)
		if table is None and doctype == "DocType":
			table = [{"name": name} for name in sorted(fake.doctypes)]
		rows = [row for row in table or [] if _matches(row, filters)]
		if or_filters:
			rows = [row for row in rows if any(_matches(row, {k: v}) for k, v in or_filters.items())]
		specs = [_field(spec, str(fake.__version__).startswith("16")) for spec in (fields or [])]
		if group_by or any(spec[0] == "aggregate" for spec in specs):
			keys = [part.strip() for part in (group_by or "").split(",") if part.strip()]
			groups = {}
			for row in rows:
				groups.setdefault(tuple(row.get(key) for key in keys), []).append(row)
			if not keys and not groups:
				groups[()] = []  # an aggregate over nothing is still one row, as in SQL
			out = []
			for members in groups.values():
				found = _dict()
				for spec in specs:
					if spec[0] == "plain":
						found[spec[2]] = members[0].get(spec[1]) if members else None
					else:
						found[spec[3]] = _aggregate(spec[1], spec[2], members)
				out.append(found)
			# grouped: sorted on what was selected, totals and aliases included
			rows = _sort(out, order_by)
		else:
			# as SQL sorts: on any column, selected or not
			rows = _sort(rows, order_by)
			if specs:
				rows = [_dict({spec[2]: row.get(spec[1]) for spec in specs}) for row in rows]
			else:
				rows = [_dict(row) for row in rows]
		size = limit if limit is not None else limit_page_length
		if size:
			rows = rows[:size]
		if pluck:
			return [row.get(pluck) for row in rows]
		return [_dict(row) for row in rows]

	def get_all(doctype, *args, **kwargs):
		return query(doctype, *args, **kwargs)

	def get_list(doctype, *args, **kwargs):
		if doctype not in fake.readable:
			raise PermissionError(f"not permitted to read {doctype}")
		return query(doctype, *args, checked=True, **kwargs)

	fake.get_all = get_all
	fake.get_list = get_list

	def has_permission(doctype=None, ptype="read", doc=None, user=None, **kwargs):
		if ptype == "create":
			return doctype in fake.creatable
		return doctype in fake.readable

	fake.has_permission = has_permission
	fake.get_cached_value = lambda doctype, name, fieldname: fake.db.get_value(doctype, name, fieldname)

	class UserRecord:
		"""A User as far as its blocked modules: those in fake.blocked for it."""

		def __init__(self, name):
			self.name = name

		def get_blocked_modules(self):
			return list(fake.blocked.get(self.name, ()))

	fake.get_cached_doc = lambda doctype, name=None: UserRecord(name) if doctype == "User" else fake.docs[(doctype, name)]

	# frappe.desk.desk_views.DeskViews, as far as the reports a user may open: fake.allowed_reports
	desk = types.ModuleType("frappe.desk")
	desk_views = types.ModuleType("frappe.desk.desk_views")

	class DeskViews:
		@classmethod
		def get_allowed_report_names(cls, cache=False, user=None):
			return set(fake.allowed_reports)

	desk_views.DeskViews = DeskViews
	desk.desk_views = desk_views
	fake.desk = desk
	defaults = types.ModuleType("frappe.defaults")
	defaults.get_user_default = lambda key, user=None: fake.user_defaults.get(key)
	fake.defaults = defaults

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

	class Logger:
		"""frappe.logger(module): what was logged, kept on this fake."""

		def __init__(self, module):
			self.module = module

		def exception(self, message, *args):
			fake.logged.append((self.module, message % args if args else message))

	fake.logger = lambda module=None, *a, **k: Logger(module)

	class Meta:
		"""frappe.get_meta(doctype), as far as has_field and title_field: the fields in
		fake.meta_fields, the title field in fake.title_fields."""

		def __init__(self, doctype):
			self.fields = fake.meta_fields.get(doctype, set())
			self.title_field = fake.title_fields.get(doctype)

		def has_field(self, fieldname):
			return fieldname in self.fields

	fake.get_meta = lambda doctype, *a, **k: Meta(doctype)
	fake.msgprint = lambda *a, **k: fake.messages.append(a[0] if a else k.get("msg"))
	fake.enqueue = lambda fn, **kwargs: fake.enqueued.append((fn, kwargs))

	def sendmail(**kwargs):
		if fake.fail_sendmail:
			raise RuntimeError("no outgoing email account")
		fake.sent_mail.append(_dict(kwargs))

	fake.sendmail = sendmail
	fake.db = FakeDB(fake)
	fake.cache = FakeCache(fake)

	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda value: int(float(value)) if str(value or "").strip().lstrip("-").replace(".", "", 1).isdigit() else 0
	utils.strip_html = lambda text: re.sub(r"<[^>]+>", "", text or "")
	utils.today = lambda: fake.today
	utils.nowdate = lambda: fake.today
	utils.getdate = lambda value=None: (
		value if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime)
		else value.date() if isinstance(value, datetime.datetime)
		else datetime.date.fromisoformat(str(value or fake.today)[:10])
	)
	utils.add_days = lambda value, days: utils.getdate(value) + datetime.timedelta(days=days)
	utils.now_datetime = lambda: fake.now
	utils.validate_email_address = lambda text, throw=False: text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text or "") else ""
	utils.get_url_to_form = lambda doctype, name: f"https://erp.example.com/app/{doctype.lower().replace(' ', '-')}/{name}"
	utils.get_fullname = lambda user=None: fake.full_names.get(user, user)
	fake.utils = utils

	model = types.ModuleType("frappe.model")
	document = types.ModuleType("frappe.model.document")
	document.Document = Document
	model.document = document

	fake._modules = {
		"frappe": fake,
		"frappe.utils": utils,
		"frappe.model": model,
		"frappe.model.document": document,
		"frappe.desk": desk,
		"frappe.desk.desk_views": desk_views,
	}
	reset(fake)
	return fake


def reset(fake):
	# This stand-in is the frappe of the test about to run, as a bench has only one: code that imports
	# from frappe as it runs (frappe.desk.desk_views, in home.py) finds this one, not the last installed.
	sys.modules.update(fake._modules)
	fake.session = _dict(user="jane@example.com")
	fake.today = "2026-09-28"
	fake.now = datetime.datetime(2026, 9, 28, 9, 0)
	fake.__version__ = "16.34.0"
	fake.readable = set()  # the doctypes the session user may read (get_list, has_permission)
	fake.creatable = set()  # and may create
	fake.user_defaults = {}
	fake.blocked = {}  # user: [the modules blocked for them]
	fake.allowed_reports = set()  # the reports the session user may open
	fake.cached = {}
	fake.cache_seconds = {}
	fake.title_fields = {}
	fake.doctypes = set()
	fake.singles = {}
	fake.db_defaults = {}  # frappe.db.get_default; frappe.defaults is the module, as in Frappe
	fake.tables = {}
	fake.docs = {}
	fake.roles = {}
	fake.writes = []
	fake.queries = []
	fake.cleared = []
	fake.errors = []
	fake.logged = []
	fake.sent_mail = []
	fake.fail_sendmail = False
	fake.full_names = {}
	fake.meta_fields = {"Notification Log": {"subject", "description", "email_content"}}  # Frappe v16
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
