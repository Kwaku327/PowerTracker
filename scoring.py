"""
Utility functions for powerlifting scoring formulas (DOTS, IPF GL, Glossbrenner).
"""

from __future__ import annotations

from math import exp, pow
from typing import Iterable, Tuple


KG_PER_POUND = 0.45359237  # conversion constant


def _coefficient(dividend: float, weight: float, params: Iterable[float]) -> float:
    """Generic polynomial coefficient helper used across multiple formulas."""
    denominator = 0.0
    for index, param in enumerate(params):
        denominator += param * pow(weight, index)
    if denominator == 0:
        return 0.0
    return dividend / denominator


def calculate_dots(total_kg: float, bodyweight_kg: float, gender: str) -> float:
    """Compute DOTS points for the given total/bodyweight."""
    if not total_kg or not bodyweight_kg:
        return 0.0

    gender_key = gender.lower()
    coeffs = {
        "male": (-307.75076, 24.0900756, -0.1918759221, 7.391293e-4, -1.093e-6),
        "female": (-57.96288, 13.6175032, -0.1126655495, 5.158568e-4, -1.0706e-6),
    }.get(gender_key)

    if not coeffs:
        return 0.0

    dots_coeff = _coefficient(500.0, bodyweight_kg, coeffs)
    return round(total_kg * dots_coeff, 2)


def calculate_ipf_gl(total_kg: float, bodyweight_kg: float, gender: str) -> float:
    """Compute IPF GL points."""
    if not total_kg or not bodyweight_kg:
        return 0.0

    gender_key = gender.lower()
    coeff_map: dict[str, Tuple[float, float, float]] = {
        "male": (1199.72839, 1025.18162, 0.009210),
        "female": (610.32796, 1045.59282, 0.03048),
    }
    coeffs = coeff_map.get(gender_key)
    if not coeffs:
        return 0.0

    a, b, c = coeffs
    denominator = a - b * exp(-c * bodyweight_kg)
    if denominator == 0:
        return 0.0
    return round((total_kg * 100.0) / denominator, 2)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def _schwartz(bodyweight_kg: float) -> float:
    bw = _clamp(bodyweight_kg, 40.0, 166.0)
    if bw <= 126:
        x0 = 0.631926e1
        x1 = 0.262349e0 * bw
        x2 = 0.511550e-2 * pow(bw, 2)
        x3 = 0.519738e-4 * pow(bw, 3)
        x4 = 0.267626e-6 * pow(bw, 4)
        x5 = 0.540132e-9 * pow(bw, 5)
        x6 = 0.728875e-13 * pow(bw, 6)
        return x0 - x1 + x2 - x3 + x4 - x5 - x6
    if bw <= 136:
        return 0.5210 - 0.0012 * (bw - 125.0)
    if bw <= 146:
        return 0.5090 - 0.0011 * (bw - 135.0)
    if bw <= 156:
        return 0.4980 - 0.0010 * (bw - 145.0)
    return 0.4879 - 0.00088185 * (bw - 155.0)


def _malone(bodyweight_kg: float) -> float:
    bw = max(bodyweight_kg, 29.24)
    a = 106.011586323613
    b = -1.293027130579051
    c = 0.322935585328304
    return a * pow(bw, b) + c


def _wilks_coefficient(bodyweight_kg: float, gender: str) -> float:
    coeffs_map: dict[str, Tuple[float, float, float, float, float, float]] = {
        "male": (-216.0475144, 16.2606339, -0.002388645, -0.00113732, 7.01863e-6, -1.291e-8),
        "female": (594.31747775582, -27.23842536447, 0.82112226871, -0.00930733913, 4.731582e-5, -9.054e-8),
    }
    coeffs = coeffs_map.get(gender.lower())
    if not coeffs:
        return 0.0
    return _coefficient(500.0, bodyweight_kg, coeffs)


def calculate_glossbrenner(total_kg: float, bodyweight_kg: float, gender: str) -> float:
    """Compute Glossbrenner points."""
    if not total_kg or not bodyweight_kg:
        return 0.0

    gender_key = gender.lower()
    if gender_key == "male":
        if bodyweight_kg < 153.05:
            coeff = (_schwartz(bodyweight_kg) + _wilks_coefficient(bodyweight_kg, "male")) / 2.0
        else:
            a = -0.000821668402557
            b = 0.676940740094416
            coeff = (_schwartz(bodyweight_kg) + a * bodyweight_kg + b) / 2.0
    elif gender_key == "female":
        if bodyweight_kg < 106.3:
            coeff = (_malone(bodyweight_kg) + _wilks_coefficient(bodyweight_kg, "female")) / 2.0
        else:
            a = -0.000313738002024
            b = 0.852664892884785
            coeff = (_malone(bodyweight_kg) + a * bodyweight_kg + b) / 2.0
    else:
        return 0.0

    return round(total_kg * coeff, 2)
