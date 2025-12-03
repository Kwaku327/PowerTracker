"""
Data ingestion and transformation utilities for LiftingCast live meets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import pandas as pd
import requests

try:
    from .scoring import (
        calculate_dots,
        calculate_glossbrenner,
        calculate_ipf_gl,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from scoring import (  # type: ignore
        calculate_dots,
        calculate_glossbrenner,
        calculate_ipf_gl,
    )

KG_PER_POUND = 0.45359237
MEET_API_TEMPLATE = "https://liftingcast.com/api/meets/{meet_id}"
MEET_LIST_API = "https://liftingcast.com/api/meets"
REQUEST_HEADERS = {"User-Agent": "PowerTrack/1.2"}


class LiftingCastError(RuntimeError):
    """Raised when the LiftingCast API returns an unexpected response."""


@dataclass
class MeetMetadata:
    meet_id: str
    name: str
    date: Optional[str]
    federation: Optional[str]
    equipment: Optional[str]
    units: str
    source: str = "liftingcast"


def _parse_meet_id(raw_value: str) -> str:
    if not raw_value:
        raise ValueError("Meet identifier is empty")

    value = raw_value.strip()
    if not value:
        raise ValueError("Meet identifier is empty")

    if "liftingcast.com" in value:
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if "meets" not in parts:
            raise ValueError("Could not determine meet ID from URL")
        meet_idx = parts.index("meets") + 1
        if meet_idx >= len(parts):
            raise ValueError("Could not determine meet ID from URL")
        return parts[meet_idx]

    return value


def _fetch_meet_docs(meet_id: str, timeout: int = 15) -> List[dict]:
    url = MEET_API_TEMPLATE.format(meet_id=meet_id)
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        raise LiftingCastError(f"Unable to contact LiftingCast ({exc})") from exc

    if response.status_code == 404:
        raise LiftingCastError(
            f"Meet '{meet_id}' was not found on liftingcast.com"
        )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise LiftingCastError(
            f"LiftingCast returned HTTP {response.status_code}"
        ) from exc

    payload = response.json()
    docs = payload.get("docs")
    if not isinstance(docs, list):
        raise LiftingCastError("Unexpected response format from LiftingCast API")
    return docs


def _convert_weight(value: Optional[float], units: str) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if units.upper() == "LBS":
        return round(numeric * KG_PER_POUND, 3)
    return numeric


def _extract_meet_metadata(meet_id: str, docs: List[dict]) -> MeetMetadata:
    meet_doc = next((doc for doc in docs if doc.get("_id") == meet_id), {})
    name = meet_doc.get("name", f"Meet {meet_id}")
    date = meet_doc.get("date")
    federation = meet_doc.get("federation")
    units = meet_doc.get("units", "KG")
    equipment = None
    return MeetMetadata(
        meet_id=meet_id,
        name=name,
        date=_format_date(date, meet_doc.get("dateFormat")),
        federation=federation,
        equipment=equipment,
        units=units,
    )


def _format_date(date_value: Optional[str], fmt: Optional[str]) -> Optional[str]:
    if not date_value or not fmt:
        return date_value
    format_map = {
        "DD/MM/YYYY": "%d/%m/%Y",
        "MM/DD/YYYY": "%m/%d/%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
    }
    python_fmt = format_map.get(fmt.upper())
    if not python_fmt:
        return date_value

    try:
        parsed = pd.to_datetime(date_value, format=python_fmt)
    except (ValueError, TypeError):
        return date_value
    return parsed.strftime("%B %d, %Y")


def _build_division_lookup(docs: Iterable[dict]) -> Dict[str, dict]:
    lookup: Dict[str, dict] = {}
    for doc in docs:
        division_id = doc.get("_id")
        if not division_id or not division_id.startswith("d"):
            continue
        if "weightClasses" in doc:
            lookup[division_id] = doc
    return lookup


def _collect_attempts(docs: Iterable[dict], units: str) -> Dict[str, Dict[str, Dict[str, dict]]]:
    attempt_map: Dict[str, Dict[str, Dict[str, dict]]] = {}
    for doc in docs:
        doc_id = doc.get("_id", "")
        if not doc_id.startswith("a") or "lifterId" not in doc:
            continue
        lifter_id = doc["lifterId"]
        lift_name = doc.get("liftName")
        attempt_number = str(doc.get("attemptNumber"))
        if not lift_name or attempt_number not in {"1", "2", "3"}:
            continue

        lifter_attempts = attempt_map.setdefault(lifter_id, {})
        lift_attempts = lifter_attempts.setdefault(lift_name, {})
        lift_attempts[attempt_number] = {
            "weight": _convert_weight(doc.get("weight"), units),
            "result": doc.get("result"),
        }
    return attempt_map


def _resolve_weight_class(
    divisions: List[dict], division_lookup: Dict[str, dict]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not divisions:
        return None, None, None
    primary = divisions[0]
    division_id = primary.get("divisionId")
    weight_class_id = primary.get("declaredAwardsWeightClassId")
    equipment = primary.get("rawOrEquipped")

    division_doc = division_lookup.get(division_id, {})
    division_name = division_doc.get("name")
    weight_classes = division_doc.get("weightClasses", {})
    weight_class = None
    if isinstance(weight_classes, dict) and weight_class_id:
        class_info = weight_classes.get(weight_class_id)
        if isinstance(class_info, dict):
            weight_class = class_info.get("name")

    return division_name, weight_class, equipment


def _best_lift(attempts: Dict[str, dict]) -> float:
    best = 0.0
    for attempt in attempts.values():
        weight = attempt.get("weight")
        result = attempt.get("result")
        if weight is None or result != "good":
            continue
        if weight > best:
            best = weight
    return round(best, 3)


def _collect_equipment(values: Iterable[Optional[str]]) -> Optional[str]:
    filtered = {value for value in values if value}
    if not filtered:
        return None
    if len(filtered) == 1:
        value = filtered.pop()
        return value.title()
    return "Mixed"


def fetch_recent_liftingcast_meets(
    limit: int = 15, max_age_days: int = 120, timeout: int = 10
) -> List[dict]:
    """
    Fetch recent public meets from LiftingCast's home feed.

    Returns a list of dictionaries containing id, name, date, url, and timestamps.
    """
    try:
        response = requests.get(MEET_LIST_API, headers=REQUEST_HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        raise LiftingCastError(f"Unable to contact LiftingCast ({exc})") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise LiftingCastError(
            f"LiftingCast returned HTTP {response.status_code} while listing meets"
        ) from exc

    payload = response.json()
    docs = payload.get("docs")
    if not isinstance(docs, list):
        raise LiftingCastError("Unexpected response format while listing meets")

    meets: List[dict] = []
    cutoff = (
        pd.Timestamp.utcnow() - pd.Timedelta(days=max_age_days)
        if max_age_days and max_age_days > 0
        else None
    )

    for doc in docs:
        meet_id = doc.get("_id")
        if not meet_id:
            continue
        raw_date = doc.get("date")
        formatted_date = _format_date(raw_date, doc.get("dateFormat"))
        created_at = pd.to_datetime(doc.get("createDate"), errors="coerce", utc=True)
        meet_date = pd.to_datetime(raw_date, errors="coerce", utc=True)
        recency_anchor = created_at or meet_date
        if cutoff is not None and pd.notna(recency_anchor) and recency_anchor < cutoff:
            continue

        meets.append(
            {
                "id": meet_id,
                "name": doc.get("name", f"Meet {meet_id}"),
                "date": formatted_date or raw_date,
                "url": f"https://liftingcast.com/meets/{meet_id}",
                "created_at": created_at.to_pydatetime()
                if pd.notna(created_at)
                else None,
                "meet_date": meet_date.to_pydatetime() if pd.notna(meet_date) else None,
            }
        )

    meets.sort(
        key=lambda item: item.get("created_at")
        or item.get("meet_date")
        or pd.Timestamp.min.to_pydatetime(),
        reverse=True,
    )
    return meets[:limit] if limit and limit > 0 else meets


def load_liftingcast_meet(
    meet_reference: str, timeout: int = 15
) -> Tuple[pd.DataFrame, MeetMetadata]:
    meet_id = _parse_meet_id(meet_reference)
    docs = _fetch_meet_docs(meet_id, timeout=timeout)
    metadata = _extract_meet_metadata(meet_id, docs)
    division_lookup = _build_division_lookup(docs)
    attempts_lookup = _collect_attempts(docs, metadata.units)

    rows: List[dict] = []
    equipment_values: List[Optional[str]] = []

    for doc in docs:
        doc_id = doc.get("_id", "")
        if not doc_id.startswith("l"):
            continue
        if "lifterId" in doc:
            # Attempt documents also start with 'l', skip those
            continue
        if "divisions" not in doc:
            continue

        lifter_id = doc_id
        name = doc.get("name")
        gender = doc.get("gender", "").upper() or None
        body_weight = _convert_weight(doc.get("bodyWeight"), metadata.units)
        division_name, weight_class, lifter_equipment = _resolve_weight_class(
            doc.get("divisions") or [], division_lookup
        )
        equipment_values.append(lifter_equipment)

        lifter_attempts = attempts_lookup.get(lifter_id, {})
        squat_attempts = lifter_attempts.get("squat", {})
        bench_attempts = lifter_attempts.get("bench", {})
        dead_attempts = lifter_attempts.get("dead", {})

        best_squat = _best_lift(squat_attempts)
        best_bench = _best_lift(bench_attempts)
        best_dead = _best_lift(dead_attempts)
        total = round(best_squat + best_bench + best_dead, 3)

        dots = calculate_dots(total, body_weight or 0.0, gender or "")
        ipf_gl = calculate_ipf_gl(total, body_weight or 0.0, gender or "")
        gloss = calculate_glossbrenner(total, body_weight or 0.0, gender or "")

        row = {
            "Lifter ID": lifter_id,
            "Name": name,
            "Gender": gender,
            "Body Weight (kg)": body_weight,
            "Weight Class": weight_class,
            "Awards Division": division_name,
            "Best Squat": best_squat,
            "Best Bench": best_bench,
            "Best Deadlift": best_dead,
            "Total": total,
            "Dots Points": dots,
            "IPF Points": ipf_gl,
            "Glossbrenner Points": gloss,
        }

        # Populate attempt columns
        for lift, attempts, label in [
            ("squat", squat_attempts, "Squat"),
            ("bench", bench_attempts, "Bench"),
            ("dead", dead_attempts, "Deadlift"),
        ]:
            prefix = label[0].upper()
            for attempt_no in ("1", "2", "3"):
                attempt = attempts.get(attempt_no, {})
                row[f"{label} {attempt_no}"] = attempt.get("weight")
                result = attempt.get("result")
                row[f"{prefix}{attempt_no}HRef"] = result

        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        raise LiftingCastError(
            f"Meet '{meet_id}' did not return any lifter data from LiftingCast"
        )

    df["Body Weight (kg)"] = pd.to_numeric(df["Body Weight (kg)"], errors="coerce")
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0.0)
    df["Dots Points"] = pd.to_numeric(df["Dots Points"], errors="coerce").fillna(0.0)
    df["IPF Points"] = pd.to_numeric(df["IPF Points"], errors="coerce").fillna(0.0)
    df["Glossbrenner Points"] = (
        pd.to_numeric(df["Glossbrenner Points"], errors="coerce").fillna(0.0)
    )

    df.sort_values(
        ["Gender", "Total", "Body Weight (kg)"],
        ascending=[True, False, True],
        inplace=True,
    )
    df["Place"] = df.groupby("Gender").cumcount().add(1).astype(int)

    df.reset_index(drop=True, inplace=True)

    metadata.equipment = _collect_equipment(equipment_values)

    return df, metadata
