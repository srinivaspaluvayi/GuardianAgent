"""Allowlists for policy conditions (external domains, etc.)."""

EXTERNAL_DOMAINS_ALLOWLIST: set = {
    "api.company.com",
    "hooks.slack.com",
}

INTERNAL_DOMAINS: set = {
    "internal.company.local",
    "intranet.company.com",
}
