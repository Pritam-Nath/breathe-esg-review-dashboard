# Decisions

## SAP

I chose an SAP S/4HANA Purchase Order OData-style extract rather than raw IDoc. SAP IDocs are realistic for integrations, but the assignment asks for a prototype an analyst can reason about in four days. OData purchase order items expose fields like plant, quantity, order unit, and item values in a shape that maps cleanly to review rows while still preserving SAP messiness: plant codes, multilingual column names, inconsistent units, and awkward dates.

Handled subset: purchase/fuel line items with document item IDs, plant/cost center, material group, quantity, unit, spend, currency, and posting date.

Ignored: full SAP authentication, BAPI/RFC connectivity, service entry sheets, material master lookups, plant master lookup tables, and tax/account assignment details.

PM question: Do analysts need procurement spend-based emissions for all categories immediately, or only direct fuel and a narrow set of purchased goods?

## Utility electricity

I chose a Green Button-style portal CSV. Facilities teams commonly download usage/bill data from utility portals, and Green Button data includes billing period and usage semantics. A CSV upload is plausible for first onboarding and easier to validate than utility-by-utility API integrations.

Handled subset: bill ID, meter ID, billing period start/end, kWh, bill amount, and currency.

Ignored: interval data, demand charges, net metering imports/exports, tariff line-item math, and PDF extraction.

PM question: Should the system allocate a non-calendar billing period across calendar months for reporting, or keep the utility bill period intact until a later accounting step?

## Corporate travel

I chose a Concur-like expense/report export. Corporate travel platforms expose report entries, expense types, dates, approved amounts, and itinerary/segment data. The prototype accepts flight distance if present, hotel nights, and ground-transport distance.

Handled subset: expense ID, travel date, expense category, distance/nights, unit, amount, currency, and cost center.

Ignored: OAuth/API sync, itinerary joins, airport-distance enrichment when only airport codes are present, cabin-class multipliers, radiative forcing, and hotel country-specific factors.

PM question: Do we trust travel-platform-calculated emissions when provided, or should Breathe always recalculate from itinerary primitives?

## Analyst workflow

Rows start in `needs_review`. Analysts can approve rows; approved rows can then be locked. Locking is separate because audit readiness is stronger than analyst approval. Suspicious rows are not blocked from approval, but the reason stays visible.
