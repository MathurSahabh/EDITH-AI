"""
Feature 4: Unit Converter for EDITH-AI
========================================
Pure Python — no external API required.

Commands:
  convert 100 km to miles
  convert 50 celsius to fahrenheit
  convert 10 kg to pounds
  convert 5 feet to meters
  convert 1 gallon to liters
  convert 1000 bytes to kb
"""

import re
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Conversion tables — all values are ratios TO a common base unit
# ---------------------------------------------------------------------------

# Length  (base: meters)
LENGTH = {
    "m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1,
    "km": 1000, "kilometer": 1000, "kilometers": 1000,
    "kilometre": 1000, "kilometres": 1000,
    "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
    "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
    "mile": 1609.344, "miles": 1609.344, "mi": 1609.344,
    "yard": 0.9144, "yards": 0.9144, "yd": 0.9144,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254, "in": 0.0254,
    "nautical mile": 1852, "nautical miles": 1852, "nmi": 1852,
}

# Mass / Weight  (base: grams)
MASS = {
    "g": 1, "gram": 1, "grams": 1,
    "kg": 1000, "kilogram": 1000, "kilograms": 1000,
    "mg": 0.001, "milligram": 0.001, "milligrams": 0.001,
    "lb": 453.592, "lbs": 453.592, "pound": 453.592, "pounds": 453.592,
    "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
    "ton": 1_000_000, "tons": 1_000_000, "tonne": 1_000_000, "tonnes": 1_000_000,
    "quintal": 100_000, "quintals": 100_000,
}

# Volume  (base: liters)
VOLUME = {
    "l": 1, "liter": 1, "liters": 1, "litre": 1, "litres": 1,
    "ml": 0.001, "milliliter": 0.001, "milliliters": 0.001,
    "gallon": 3.78541, "gallons": 3.78541,
    "quart": 0.946353, "quarts": 0.946353, "qt": 0.946353,
    "pint": 0.473176, "pints": 0.473176, "pt": 0.473176,
    "cup": 0.236588, "cups": 0.236588,
    "fl oz": 0.0295735, "fluid ounce": 0.0295735, "fluid ounces": 0.0295735,
    "tbsp": 0.0147868, "tablespoon": 0.0147868, "tablespoons": 0.0147868,
    "tsp": 0.00492892, "teaspoon": 0.00492892, "teaspoons": 0.00492892,
}

# Speed  (base: m/s)
SPEED = {
    "m/s": 1, "ms": 1, "meters per second": 1,
    "km/h": 1 / 3.6, "kph": 1 / 3.6, "kmh": 1 / 3.6, "kilometers per hour": 1 / 3.6,
    "mph": 0.44704, "miles per hour": 0.44704,
    "knot": 0.514444, "knots": 0.514444, "kt": 0.514444,
    "ft/s": 0.3048, "fps": 0.3048, "feet per second": 0.3048,
}

# Data size  (base: bytes)
DATA = {
    "b": 1, "byte": 1, "bytes": 1,
    "kb": 1024, "kilobyte": 1024, "kilobytes": 1024,
    "mb": 1024 ** 2, "megabyte": 1024 ** 2, "megabytes": 1024 ** 2,
    "gb": 1024 ** 3, "gigabyte": 1024 ** 3, "gigabytes": 1024 ** 3,
    "tb": 1024 ** 4, "terabyte": 1024 ** 4, "terabytes": 1024 ** 4,
    "pb": 1024 ** 5, "petabyte": 1024 ** 5, "petabytes": 1024 ** 5,
}

# Energy  (base: joules)
ENERGY = {
    "j": 1, "joule": 1, "joules": 1,
    "kj": 1000, "kilojoule": 1000, "kilojoules": 1000,
    "cal": 4.184, "calorie": 4.184, "calories": 4.184,
    "kcal": 4184, "kilocalorie": 4184, "kilocalories": 4184,
    "wh": 3600, "watt-hour": 3600, "watt hour": 3600,
    "kwh": 3_600_000, "kilowatt-hour": 3_600_000, "kilowatt hour": 3_600_000,
    "btu": 1055.06,
}

# All dimension tables
DIMENSIONS = [
    ("length", LENGTH),
    ("mass", MASS),
    ("volume", VOLUME),
    ("speed", SPEED),
    ("data", DATA),
    ("energy", ENERGY),
]

# Temperature is handled separately (not a simple ratio)


class UnitConverter:
    """Converts between common units of measurement."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[str]:
        """Return a response string if this module handles the command, else None."""
        raw = (text or "").strip()
        low = raw.lower()

        if not low.startswith("convert "):
            return None

        payload = raw[len("convert "):].strip()
        return self._parse_and_convert(payload)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_and_convert(self, payload: str) -> str:
        """
        Parse: '<value> <from_unit> to <to_unit>'
        """
        low = payload.lower()

        # Split on ' to '
        if " to " not in low:
            return (
                "Could not parse conversion. Try:\n"
                "  convert 100 km to miles\n"
                "  convert 50 celsius to fahrenheit\n"
                "  convert 10 kg to pounds"
            )

        idx = low.index(" to ")
        left = payload[:idx].strip()
        to_unit = payload[idx + 4:].strip().lower().rstrip(".")

        # Extract value and from_unit from left
        m = re.match(r"^(-?[\d,.]+)\s+(.+)$", left)
        if not m:
            return f"Could not parse value/unit from '{left}'. Example: 100 km"

        raw_val = m.group(1).replace(",", "")
        try:
            value = float(raw_val)
        except ValueError:
            return f"Invalid number: '{m.group(1)}'"

        from_unit = m.group(2).strip().lower()

        return self._convert(value, from_unit, to_unit)

    # ------------------------------------------------------------------
    # Conversion logic
    # ------------------------------------------------------------------

    def _convert(self, value: float, from_unit: str, to_unit: str) -> str:
        # Temperature — special case
        temp_result = self._try_temperature(value, from_unit, to_unit)
        if temp_result is not None:
            return temp_result

        # Generic ratio conversion
        for dim_name, table in DIMENSIONS:
            if from_unit in table and to_unit in table:
                base_value = value * table[from_unit]
                result = base_value / table[to_unit]
                return self._format_result(value, from_unit, result, to_unit, dim_name)

        # One unit known but not both
        known_from = any(from_unit in t for _, t in DIMENSIONS)
        known_to = any(to_unit in t for _, t in DIMENSIONS)

        if known_from and not known_to:
            return f"Unknown unit: '{to_unit}'."
        if not known_from and known_to:
            return f"Unknown unit: '{from_unit}'."
        if not known_from and not known_to:
            return (
                f"Unknown units: '{from_unit}' and '{to_unit}'.\n"
                "Supported categories: length, mass, volume, speed, data, energy, temperature."
            )

        return f"Cannot convert '{from_unit}' to '{to_unit}' — they are different dimensions."

    # ------------------------------------------------------------------
    # Temperature
    # ------------------------------------------------------------------

    _CELSIUS_ALIASES = {"c", "celsius", "centigrade", "°c"}
    _FAHRENHEIT_ALIASES = {"f", "fahrenheit", "°f"}
    _KELVIN_ALIASES = {"k", "kelvin", "°k"}

    def _try_temperature(self, value: float, from_unit: str, to_unit: str) -> Optional[str]:
        from_is_temp = (
            from_unit in self._CELSIUS_ALIASES
            or from_unit in self._FAHRENHEIT_ALIASES
            or from_unit in self._KELVIN_ALIASES
        )
        to_is_temp = (
            to_unit in self._CELSIUS_ALIASES
            or to_unit in self._FAHRENHEIT_ALIASES
            or to_unit in self._KELVIN_ALIASES
        )

        if not (from_is_temp or to_is_temp):
            return None
        if not (from_is_temp and to_is_temp):
            return "Cannot mix temperature and non-temperature units."

        # Convert from_unit → Celsius first
        if from_unit in self._CELSIUS_ALIASES:
            celsius = value
        elif from_unit in self._FAHRENHEIT_ALIASES:
            celsius = (value - 32) * 5 / 9
        else:  # Kelvin
            celsius = value - 273.15

        # Celsius → to_unit
        if to_unit in self._CELSIUS_ALIASES:
            result = celsius
        elif to_unit in self._FAHRENHEIT_ALIASES:
            result = celsius * 9 / 5 + 32
        else:  # Kelvin
            result = celsius + 273.15

        return self._format_result(value, from_unit, result, to_unit, "temperature")

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_result(
        value: float, from_unit: str, result: float, to_unit: str, dim_name: str
    ) -> str:
        # Choose precision
        if abs(result) >= 100:
            formatted = f"{result:,.4f}".rstrip("0").rstrip(".")
        elif abs(result) >= 1:
            formatted = f"{result:.6f}".rstrip("0").rstrip(".")
        else:
            formatted = f"{result:.10f}".rstrip("0").rstrip(".")

        return (
            f"{dim_name.title()} conversion:\n"
            f"  {value:g} {from_unit}  =  {formatted} {to_unit}"
        )
