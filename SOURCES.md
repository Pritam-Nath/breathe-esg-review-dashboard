# Sources and sample data rationale

## SAP procurement/fuel

Researched format: SAP S/4HANA Purchase Order OData and SAP IDoc structure.

Sources:

- SAP Help Portal, Purchase Order OData V4: https://help.sap.com/docs/SAP_S4HANA_CLOUD/0e602d466b99490187fcbb30d1dc897c/c89eec80ec2043d980cb7b8c89e0a00a.html
- SAP Help Portal, IDoc structure: https://help.sap.com/saphelp_gbt10/helpdata/en/4b/38625bad7f74fee10000000a421937/content.htm

What I learned: SAP exposes structured purchase order APIs, but enterprise exports still carry SAP concepts such as plant, document item, material group, order unit, and localized/custom field names. IDocs are segment-based and realistic, but heavier than needed for this prototype.

Sample data: fuel rows include plant codes, German headers (`Werk`, `Warengruppe`, `Menge`, `MEINS`), liters, and a high fuel quantity. Procurement rows include a purchased material group and spend.

What would break: missing plant lookup tables, custom material groups, UoM conversions not in the prototype, and purchase lines where the invoice unit differs from the order unit.

## Utility electricity

Researched format: Green Button utility usage/billing exports.

Sources:

- Green Button Alliance utility bill data mapping: https://www.greenbuttonalliance.org/utility-bill-data
- UtilityAPI Green Button XML docs: https://utilityapi.com/docs/greenbutton/xml
- Oracle utilities Green Button overview: https://docs.oracle.com/en/industries/energy-water/energy-efficiency/energy-efficiency-overview/Content/Customer_Experience_Overview/Green_Button.htm

What I learned: Utility data often revolves around meter/account, billing period, total usage, and bill values. Billing periods do not necessarily align with calendar months.

Sample data: meter IDs, bill IDs, kWh, costs, and billing periods. One row has a long/high-usage period; another row has missing usage to exercise validation.

What would break: interval data, time zones, estimated vs actual reads, demand charges, net metering, PDF bills, and tariffs with multiple rate components.

## Corporate travel

Researched format: SAP Concur travel/expense reporting and segment concepts.

Sources:

- SAP Concur travel allowance data: https://help.sap.com/docs/CONCUR_EXPENSE/bb83754b1c5541808d50c09901e11475/c874de5531db4ffa846ecf809f502448.html
- SAP Learning, Concur request segments: https://learning.sap.com/courses/getting-started-with-concur-standard-request-for-business-users/adding-segments-to-a-request-1
- SAP Developers tutorial on Concur APIs: https://developers.sap.com/tutorials/data-to-value-conn-concur-part01..html

What I learned: Concur-style data separates report entries/expense types from travel segments. Flights, hotels, rail/car, and other ground transport imply different emission models. Distances may be absent and need itinerary enrichment.

Sample data: flight distance between airport codes, hotel nights, and ground transport miles. A zero-distance taxi row is suspicious but not invalid enough to auto-reject.

What would break: itinerary joins, airport-code distance calculation, cabin class, hotel location factors, refunds/credits, and trips split across multiple reports.
