"""Source adapters: normalize one messy real-world dataset onto the canonical contract.

Each adapter knows the quirks of a single source (column names, district naming,
totals/subtotals) and emits clean (district, year, category_code, count) rows.
"""
