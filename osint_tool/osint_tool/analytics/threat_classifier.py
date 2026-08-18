# analytics/threat_classifier.py

def classify_threat(finding):
    """
    Simple rule-based threat classification.
    Returns: 'low', 'medium', 'high'
    """
    # Example: IPs known for abuse (could integrate with AbuseIPDB)
    value = finding.value.lower()
    if finding.type == "ip":
        # Placeholder: check against local blacklist
        if value.startswith("192.168.") or value.startswith("10."):
            return "low"
        else:
            return "medium"
    if finding.type == "email":
        # Check if domain is suspicious
        suspicious_domains = ["example.com", "spam.net"]
        if any(dom in value for dom in suspicious_domains):
            return "high"
        else:
            return "low"
    return "low"