"""Logical field definitions — the single source of truth.

Each field defines WHAT a property is (type, options, set membership,
object type) without any HubSpot property naming. Property names are
determined by presets (see presets.py).

This file is the field registry described in
docs/architecture.md (Layer 2).
"""


FIELDS: dict[str, dict] = {
    # ── fit set / contact ─────────────────────────────────────────────
    "title": {
        "set": "fit",
        "label": "Title",
        "description": "Cleaned, normalized job title",
        "type": "string",
        "field_type": "text",
        "object_type": "contact",
    },
    "seniority": {
        "set": "fit",
        "label": "Seniority",
        "description": "Derived seniority level from job title",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "C-Level", "value": "c_level"},
            {"label": "VP", "value": "vp"},
            {"label": "Director", "value": "director"},
            {"label": "Manager", "value": "manager"},
            {"label": "Individual Contributor", "value": "individual_contributor"},
            {"label": "Unknown", "value": "unknown"},
        ],
    },
    "department": {
        "set": "fit",
        "label": "Department",
        "description": "Normalized department from job title",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "Engineering", "value": "engineering"},
            {"label": "Marketing", "value": "marketing"},
            {"label": "Sales", "value": "sales"},
            {"label": "Finance", "value": "finance"},
            {"label": "Operations", "value": "operations"},
            {"label": "HR", "value": "hr"},
            {"label": "Product", "value": "product"},
            {"label": "Design", "value": "design"},
            {"label": "Customer Success", "value": "customer_success"},
            {"label": "Executive", "value": "executive"},
            {"label": "Other", "value": "other"},
            {"label": "Unknown", "value": "unknown"},
        ],
    },
    "function": {
        "set": "fit",
        "label": "Function",
        "description": "Normalized job function",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "Leadership", "value": "leadership"},
            {"label": "Management", "value": "management"},
            {"label": "Technical", "value": "technical"},
            {"label": "Creative", "value": "creative"},
            {"label": "Administrative", "value": "administrative"},
            {"label": "Other", "value": "other"},
            {"label": "Unknown", "value": "unknown"},
        ],
    },
    "data_confidence": {
        "set": "fit",
        "label": "Data Confidence",
        "description": "Data quality confidence score 0-100",
        "type": "number",
        "field_type": "number",
        "object_type": "contact",
    },
    "normalization_notes": {
        "set": "fit",
        "label": "Normalization Notes",
        "description": "Debug notes from normalization engine",
        "type": "string",
        "field_type": "textarea",
        "object_type": "contact",
    },
    "email_type": {
        "set": "fit",
        "label": "Email Type",
        "description": "Work or personal email classification",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "Work Email", "value": "work_email"},
            {"label": "Personal Email", "value": "personal_email"},
        ],
    },
    "persona": {
        "set": "fit",
        "label": "Persona",
        "description": "Buyer persona classification",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "Economic Buyer", "value": "economic_buyer"},
            {"label": "Champion", "value": "champion"},
            {"label": "Technical Evaluator", "value": "technical_evaluator"},
            {"label": "End User", "value": "end_user"},
            {"label": "Influencer", "value": "influencer"},
        ],
    },
    "lead_source": {
        "set": "fit",
        "label": "Lead Source",
        "description": "Attributed lead source",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "Organic Search", "value": "organic_search"},
            {"label": "Paid Search", "value": "paid_search"},
            {"label": "Paid Social", "value": "paid_social"},
            {"label": "Content Download", "value": "content_download"},
            {"label": "Webinar", "value": "webinar"},
            {"label": "Partner Referral", "value": "partner_referral"},
            {"label": "Customer Referral", "value": "customer_referral"},
            {"label": "Direct", "value": "direct"},
            {"label": "Event", "value": "event"},
            {"label": "Outbound", "value": "outbound"},
        ],
    },
    # ── fit set / company ─────────────────────────────────────────────
    "company_domain": {
        "set": "fit",
        "label": "Domain",
        "description": "Cleaned company domain",
        "type": "string",
        "field_type": "text",
        "object_type": "company",
    },
    "company_industry": {
        "set": "fit",
        "label": "Industry",
        "description": "Normalized industry classification",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "company",
        "options": [
            {"label": "B2B SaaS", "value": "b2b_saas"},
            {"label": "Enterprise Software", "value": "enterprise_software"},
            {"label": "Marketing Technology", "value": "marketing_technology"},
            {"label": "Sales Technology", "value": "sales_technology"},
            {"label": "Data & Analytics", "value": "data_analytics"},
            {"label": "FinTech", "value": "fintech"},
            {"label": "HealthTech", "value": "healthtech"},
            {"label": "E-commerce", "value": "ecommerce"},
            {"label": "Consulting", "value": "consulting"},
            {"label": "Agency", "value": "agency"},
            {"label": "Other", "value": "other"},
            {"label": "Unknown", "value": "unknown"},
        ],
    },
    "company_employee_band": {
        "set": "fit",
        "label": "Employee Band",
        "description": "Standardized company size bucket",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "company",
        "options": [
            {"label": "1-9", "value": "1_9"},
            {"label": "10-49", "value": "10_49"},
            {"label": "50-199", "value": "50_199"},
            {"label": "200-999", "value": "200_999"},
            {"label": "1000-4999", "value": "1000_4999"},
            {"label": "5000+", "value": "5000_plus"},
            {"label": "Unknown", "value": "unknown"},
        ],
    },
    # ── engagement set / contact ──────────────────────────────────────
    "engagement_score": {
        "set": "engagement",
        "label": "Engagement Score",
        "description": "Engagement health score 0-100",
        "type": "number",
        "field_type": "number",
        "object_type": "contact",
    },
    "engagement_status": {
        "set": "engagement",
        "label": "Engagement Status",
        "description": "Current engagement classification",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "contact",
        "options": [
            {"label": "Active", "value": "active"},
            {"label": "At Risk", "value": "at_risk"},
            {"label": "Cold", "value": "cold"},
            {"label": "Dormant", "value": "dormant"},
            {"label": "Opted Out", "value": "opted_out"},
        ],
    },
    "email_opens": {
        "set": "engagement",
        "label": "Email Opens",
        "description": "Simulated email open count",
        "type": "number",
        "field_type": "number",
        "object_type": "contact",
    },
    "email_clicks": {
        "set": "engagement",
        "label": "Email Clicks",
        "description": "Simulated email click count",
        "type": "number",
        "field_type": "number",
        "object_type": "contact",
    },
    "sends_since_engagement": {
        "set": "engagement",
        "label": "Sends Since Engagement",
        "description": "Emails sent since last open or click",
        "type": "number",
        "field_type": "number",
        "object_type": "contact",
    },
    "last_open_date": {
        "set": "engagement",
        "label": "Last Open Date",
        "description": "Date of last simulated email open",
        "type": "date",
        "field_type": "date",
        "object_type": "contact",
    },
    "last_click_date": {
        "set": "engagement",
        "label": "Last Click Date",
        "description": "Date of last simulated email click",
        "type": "date",
        "field_type": "date",
        "object_type": "contact",
    },
    # ── engagement set / deal ─────────────────────────────────────────
    "deal_health_score": {
        "set": "engagement",
        "label": "Deal Health Score",
        "description": "Overall engagement health 0-100",
        "type": "number",
        "field_type": "number",
        "object_type": "deal",
    },
    "deal_engagement_status": {
        "set": "engagement",
        "label": "Deal Engagement Status",
        "description": "Current deal engagement classification",
        "type": "enumeration",
        "field_type": "select",
        "object_type": "deal",
        "options": [
            {"label": "Warm", "value": "warm"},
            {"label": "At Risk", "value": "at_risk"},
            {"label": "Dormant", "value": "dormant"},
        ],
    },
    "deal_last_activity": {
        "set": "engagement",
        "label": "Deal Last Activity",
        "description": "Date of last meaningful engagement on deal",
        "type": "date",
        "field_type": "date",
        "object_type": "deal",
    },
}


def get_fields_by_set(set_name: str) -> dict[str, dict]:
    """Return all fields belonging to a given set."""
    return {name: field for name, field in FIELDS.items()
            if field["set"] == set_name}


def get_fields_by_object_type(object_type: str) -> dict[str, dict]:
    """Return all fields for a given HubSpot object type."""
    return {name: field for name, field in FIELDS.items()
            if field["object_type"] == object_type}
