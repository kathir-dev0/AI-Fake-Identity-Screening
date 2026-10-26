import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH


TRUSTED_COLUMNS = {
	"nationality": "TEXT",
	"gender": "TEXT",
	"institution": "TEXT",
	"reference_document": "TEXT",
	"register_number": "TEXT",
	"cgpa": "TEXT",
	"created_at": "TEXT",
}

DEMO_RECORDS = [
	("CERTIFICATE", "CERT001", "ARUN KUMAR", "2004-01-01", "DEMO", None,
	 "VALID", "FICTIONAL DEMO INSTITUTE", None, None, "21CS001", "9.0"),
	("PASSPORT", "P0001", "RAHUL SHARMA", "1995-01-01", "FICTIONAL", "M",
	 "VALID", None, None, None, None, None),
]


def get_connection(db_path=DB_PATH):
	"""Open a SQLite connection with named row access."""
	path = Path(db_path)
	path.parent.mkdir(parents=True, exist_ok=True)
	connection = sqlite3.connect(path)
	connection.row_factory = sqlite3.Row
	return connection


def init_db(db_path=DB_PATH):
	"""Create or upgrade the demo registry and screening history tables."""
	with get_connection(db_path) as connection:
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS trusted_documents (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				document_type TEXT NOT NULL,
				document_number TEXT NOT NULL,
				name TEXT NOT NULL,
				date_of_birth TEXT,
				nationality TEXT,
				gender TEXT,
				expiry_date TEXT,
				status TEXT NOT NULL DEFAULT 'VALID',
				institution TEXT,
				reference_face TEXT,
				reference_document TEXT,
				register_number TEXT,
				cgpa TEXT,
				created_at TEXT
			)
			"""
		)
		existing = {
			row["name"] for row in connection.execute("PRAGMA table_info(trusted_documents)")
		}
		for column, sql_type in TRUSTED_COLUMNS.items():
			if column not in existing:
				connection.execute(f"ALTER TABLE trusted_documents ADD COLUMN {column} {sql_type}")
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS screening_history (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				timestamp TEXT NOT NULL,
				filename TEXT NOT NULL,
				document_type TEXT NOT NULL,
				document_number TEXT,
				risk_score INTEGER NOT NULL,
				risk_level TEXT NOT NULL,
				final_status TEXT NOT NULL,
				reasons TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"UPDATE trusted_documents SET created_at = ? WHERE created_at IS NULL",
			(datetime.now(timezone.utc).isoformat(timespec="seconds"),),
		)
		for record in DEMO_RECORDS:
			connection.execute(
				"""
				INSERT INTO trusted_documents (
					document_type, document_number, name, date_of_birth,
					nationality, gender, status, institution, reference_face,
					reference_document, register_number, cgpa, created_at
				)
				SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
				WHERE NOT EXISTS (
					SELECT 1 FROM trusted_documents WHERE document_number = ?
				)
				""",
				(*record, datetime.now(timezone.utc).isoformat(timespec="seconds"), record[1]),
			)
	return Path(db_path)


def _normalize(value):
	if value is None:
		return ""
	return " ".join(str(value).strip().casefold().split())


def find_trusted_document(document_number, db_path=DB_PATH):
	if not document_number:
		return None
	with get_connection(db_path) as connection:
		row = connection.execute(
			"""
			SELECT * FROM trusted_documents
			WHERE lower(document_number) = lower(?) OR lower(register_number) = lower(?)
			ORDER BY id LIMIT 1
			""",
			(str(document_number).strip(), str(document_number).strip()),
		).fetchone()
	return dict(row) if row else None


def compare_with_trusted(fields, document_type=None, db_path=DB_PATH):
	document_number = fields.get("document_number") or fields.get("certificate_id")
	record = find_trusted_document(document_number, db_path)
	if record is None or (
		document_type
		and document_type.upper() != "UNKNOWN"
		and record["document_type"].upper() != document_type.upper()
	):
		return {
			"record_found": False,
			"matched_fields": [],
			"mismatched_fields": {},
			"database_status": "NOT_FOUND",
			"record": None,
			"message": "Trusted reference record unavailable; this alone does not mean the document is fake.",
		}

	field_pairs = {
		"document_number": "document_number",
		"name": "name",
		"date_of_birth": "date_of_birth",
		"nationality": "nationality",
		"gender": "gender",
		"expiry_date": "expiry_date",
		"register_number": "register_number",
		"cgpa": "cgpa",
		"institution": "institution",
	}
	matched = []
	mismatched = {}
	for extracted_key, trusted_key in field_pairs.items():
		extracted_value = fields.get(extracted_key)
		trusted_value = record.get(trusted_key)
		if extracted_value in (None, "") or trusted_value in (None, ""):
			continue
		if _normalize(extracted_value) == _normalize(trusted_value):
			matched.append(extracted_key)
		else:
			mismatched[extracted_key] = {
				"extracted": extracted_value,
				"trusted": trusted_value,
			}
	return {
		"record_found": True,
		"matched_fields": matched,
		"mismatched_fields": mismatched,
		"database_status": record["status"],
		"record": record,
		"message": "Trusted demo record matched." if not mismatched else "One or more fields differ from the trusted demo record.",
	}


def save_screening_result(result, filename, db_path=DB_PATH):
	reasons = result.get("risk", {}).get("reasons", [])
	fields = result.get("fields", {})
	with get_connection(db_path) as connection:
		cursor = connection.execute(
			"""
			INSERT INTO screening_history (
				timestamp, filename, document_type, document_number,
				risk_score, risk_level, final_status, reasons
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				datetime.now(timezone.utc).isoformat(timespec="seconds"),
				Path(filename).name,
				result.get("document_type", "UNKNOWN"),
				fields.get("document_number"),
				result.get("risk", {}).get("score", 0),
				result.get("risk", {}).get("risk_level", "REVIEW REQUIRED"),
				result.get("final_status", "REVIEW REQUIRED"),
				json.dumps(reasons),
			),
		)
		return cursor.lastrowid


def get_screening_history(limit=20, db_path=DB_PATH):
	with get_connection(db_path) as connection:
		rows = connection.execute(
			"SELECT * FROM screening_history ORDER BY id DESC LIMIT ?",
			(max(1, int(limit)),),
		).fetchall()
	return [dict(row) for row in rows]


init_db()
