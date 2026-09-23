import os
import sqlite3
from sqlmodel import create_engine, Session, select

from pages.helper.data_models import RegisteredCases, PublicSubmissions
from pages.helper.validators import Validators, ValidationError
from pages.helper.logging_config import get_logger, log_exception, ErrorHandler

logger = get_logger(__name__)
sqlite_url = "sqlite:///sqlite_database.db"
engine = create_engine(sqlite_url)


def create_db():
    try:
        RegisteredCases.__table__.create(engine)
        PublicSubmissions.__table__.create(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.info(f"Database tables may already exist: {str(e)}")
    
    # Add new columns to existing tables if they don't exist (SQLite migration)
    try:
        _migrate_db()
    except Exception as e:
        log_exception(logger, e, "Database migration")
        ErrorHandler.handle_error(e, "Database migration", logger, reraise=False)


def _migrate_db():
    """Add any new columns to existing tables without dropping data."""
    new_columns = [
        ("registeredcases", "complainant_email", "TEXT"),
        ("registeredcases", "city", "TEXT"),
        ("registeredcases", "description", "TEXT"),
    ]
    try:
        con = sqlite3.connect("sqlite_database.db")
        cursor = con.cursor()
        for table, column, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists
        con.commit()
        con.close()
    except Exception:
        pass


def register_new_case(case_details: RegisteredCases):
    try:
        with Session(engine) as session:
            session.add(case_details)
            session.commit()
            logger.info(f"Case registered: {case_details.id}")
    except Exception as e:
        log_exception(logger, e, "Registering new case")
        ErrorHandler.handle_error(e, "Failed to register case", logger, reraise=True)


def fetch_registered_cases(submitted_by: str | None, status: str):
    if status == "All":
        status = ["F", "NF"]
    elif status == "Found":
        status = ["F"]
    elif status == "Not Found":
        status = ["NF"]

    with Session(engine) as session:
        query = (
            select(
                RegisteredCases.id,
                RegisteredCases.name,
                RegisteredCases.age,
                RegisteredCases.status,
                RegisteredCases.last_seen,
                RegisteredCases.matched_with,
            )
            .where(RegisteredCases.status.in_(status))
        )
        if submitted_by:
            query = query.where(RegisteredCases.submitted_by == submitted_by)

        result = session.exec(query).all()
        return result


def fetch_public_cases(train_data: bool, status: str):
    if train_data:
        with Session(engine) as session:
            result = session.exec(
                select(
                    PublicSubmissions.id,
                    PublicSubmissions.face_mesh,
                ).where(PublicSubmissions.status == status)
            ).all()
            return result

    with Session(engine) as session:
        result = session.exec(
            select(
                PublicSubmissions.id,
                PublicSubmissions.status,
                PublicSubmissions.location,
                PublicSubmissions.mobile,
                PublicSubmissions.birth_marks,
                PublicSubmissions.submitted_on,
                PublicSubmissions.submitted_by,
            )
        ).all()
        return result


def get_not_confirmed_registered_cases(submitted_by: str):
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases)
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status == "NF")
        ).all()
        return result


def get_training_data(submitted_by: str):
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases.id, RegisteredCases.face_mesh)
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status == "NF")
        ).all()
        return result


def new_public_case(public_case_details: PublicSubmissions):
    try:
        with Session(engine) as session:
            session.add(public_case_details)
            session.commit()
            logger.info(f"Public case submitted: {public_case_details.id}")
    except Exception as e:
        log_exception(logger, e, "Submitting public case")
        ErrorHandler.handle_error(e, "Failed to submit public case", logger, reraise=True)


def get_public_case_detail(case_id: str):
    try:
        validated_id = Validators.validate_id_string(case_id)
    except ValidationError:
        return []
    
    with Session(engine) as session:
        result = session.exec(
            select(
                PublicSubmissions.location,
                PublicSubmissions.submitted_by,
                PublicSubmissions.mobile,
                PublicSubmissions.birth_marks,
            ).where(PublicSubmissions.id == validated_id)
        ).all()
        return result


def get_registered_case_detail(case_id: str):
    try:
        validated_id = Validators.validate_id_string(case_id)
    except ValidationError:
        return []
    
    with Session(engine) as session:
        result = session.exec(
            select(
                RegisteredCases.name,
                RegisteredCases.complainant_mobile,
                RegisteredCases.complainant_email,
                RegisteredCases.age,
                RegisteredCases.last_seen,
                RegisteredCases.birth_marks,
            ).where(RegisteredCases.id == validated_id)
        ).all()
        return result


def list_public_cases():
    with Session(engine) as session:
        result = session.exec(select(PublicSubmissions)).all()
        return result


def update_found_status(register_case_id: str, public_case_id: str):
    try:
        with Session(engine) as session:
            registered_case_details = session.exec(
                select(RegisteredCases).where(RegisteredCases.id == str(register_case_id))
            ).one()
            registered_case_details.status = "F"
            registered_case_details.matched_with = str(public_case_id)

            public_case_details = session.exec(
                select(PublicSubmissions).where(PublicSubmissions.id == str(public_case_id))
            ).one()
            public_case_details.status = "F"

            session.add(registered_case_details)
            session.add(public_case_details)
            session.commit()
            logger.info(f"Match found: {register_case_id} <-> {public_case_id}")
    except Exception as e:
        log_exception(logger, e, "Updating found status")
        ErrorHandler.handle_error(e, "Failed to update match status", logger, reraise=True)


def get_registered_cases_count(submitted_by: str, status: str):
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases)
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status == status)
        ).all()
        return result


def get_case_counts_by_city():
    """Return a dict mapping city -> {found: int, not_found: int}."""
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases.city, RegisteredCases.status)
        ).all()
    counts = {}
    for city, status in result:
        if not city:
            city = "Unknown"
        if city not in counts:
            counts[city] = {"found": 0, "not_found": 0}
        if status == "F":
            counts[city]["found"] += 1
        else:
            counts[city]["not_found"] += 1
    return counts


def delete_registered_case(case_id: str):
    try:
        with Session(engine) as session:
            case = session.exec(
                select(RegisteredCases).where(RegisteredCases.id == case_id)
            ).one()
            session.delete(case)
            session.commit()
            logger.info(f"Case deleted: {case_id}")
    except Exception as e:
        log_exception(logger, e, "Deleting registered case")
        ErrorHandler.handle_error(e, "Failed to delete case", logger, reraise=True)
    
    # Remove image from disk
    try:
        image_path = f"./resources/{case_id}.jpg"
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Image deleted: {image_path}")
    except Exception as e:
        log_exception(logger, e, "Deleting case image")
        ErrorHandler.handle_error(e, "Failed to delete case image", logger, reraise=False)


def update_registered_case(case_id: str, fields: dict):
    try:
        with Session(engine) as session:
            case = session.exec(
                select(RegisteredCases).where(RegisteredCases.id == case_id)
            ).one()
            for key, value in fields.items():
                setattr(case, key, value)
            session.add(case)
            session.commit()
            logger.info(f"Case updated: {case_id}")
    except Exception as e:
        log_exception(logger, e, "Updating registered case")
        ErrorHandler.handle_error(e, "Failed to update case", logger, reraise=True)


if __name__ == "__main__":
    r = fetch_public_cases("NF")
    print(r)
