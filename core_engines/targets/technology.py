"""Technology fingerprinting for target discovery and enrichment.

Detects CMS, frameworks, CDN, and infrastructure technologies from
program metadata, scope keywords, and URL conventions. Passive analysis
only — no active scanning.
"""

import logging
import re
from typing import Dict, List, Optional, Set

LOG = logging.getLogger("rastro.targets.technology")

CMS_INDICATORS: Dict[str, List[str]] = {
    "wordpress": [
        r"wordpress", r"wp-", r"wp_content", r"wp-includes",
        r"wp-admin", r"wp-login", r"xmlrpc\.php",
        r"wp-json", r"wp-api", r"rest\.wordpress",
    ],
    "drupal": [
        r"drupal", r"drupal-", r"\.drupal", r"sites/default",
    ],
    "joomla": [
        r"joomla", r"com_content", r"com_users", r"components/com_",
    ],
    "magento": [
        r"magento", r"skin/frontend", r"vendor/magento",
    ],
    "shopify": [
        r"shopify", r"myshopify\.com", r"cdn\.shopify",
    ],
    "wix": [
        r"wix", r"wixstatic", r"wix\.com",
    ],
    "squarespace": [
        r"squarespace", r"static\d+\.squarespace",
    ],
}

FRAMEWORK_INDICATORS: Dict[str, List[str]] = {
    "laravel":       [r"laravel", r"\.env", r"artisan"],
    "symfony":       [r"symfony", r"app\.php", r"_sf2_"],
    "django":        [r"django", r"csrfmiddlewaretoken", r"wsgi\.py"],
    "rails":         [r"ruby on rails", r"rails", r"\.ruby", r"gemfile"],
    "express":       [r"express", r"node\.js", r"node_modules"],
    "nextjs":        [r"next\.js", r"nextjs", r"_next/static"],
    "nuxt":          [r"nuxt\.js", r"nuxtjs", r"_nuxt/"],
    "gatsby":        [r"gatsby", r"gatsby-"],
    "spring":        [r"spring", r"spring boot", r"java/"],
    "flask":         [r"flask", r"jinja", r"werkzeug"],
    "fastapi":       [r"fastapi", r"uvicorn"],
    "aspnet":        [r"asp\.net", r"\.aspx", r"\.ashx", r"web\.config"],
}

INFRA_INDICATORS: Dict[str, List[str]] = {
    "nginx":         [r"nginx", r"nginx/"],
    "apache":        [r"apache", r"apache/", r"\.htaccess"],
    "cloudflare":    [r"cloudflare", r"__cfduid", r"cf-ray"],
    "cloudfront":    [r"cloudfront", r"cloudfront\.net"],
    "fastly":        [r"fastly", r"fastly\.net"],
    "akamai":        [r"akamai", r"akamaihd"],
    "google_cloud":  [r"google cloud", r"gcp", r"appspot\.com"],
    "aws":           [r"aws", r"amazonaws", r"s3\.amazonaws", r"cloudfront"],
    "azure":         [r"azure", r"azureedge", r"windows\.net"],
    "kubernetes":    [r"kubernetes", r"k8s", r"eks\.", r"aks\.", r"gke\."],
    "docker":        [r"docker", r"container", r"dockerfile"],
}

WORDPRESS_PLUGINS: Dict[str, List[str]] = {
    "woocommerce":   [r"woocommerce", r"wc-", r"wc_api", r"product/"],
    "elementor":     [r"elementor", r"elementor-"],
    "yoast":         [r"yoast", r"wordpress-seo"],
    "acf":           [r"advanced custom fields", r"acf-"],
    "jetpack":       [r"jetpack", r"jetpack-"],
    "wpforms":       [r"wpforms", r"wpforms-"],
    "contact_form_7": [r"contact-form-7", r"wpcf7"],
    "wordfence":     [r"wordfence", r"wfwaf"],
    "wprocket":      [r"wp rocket", r"wprocket", r"wp-rocket"],
}


def _match_indicators(text: str, indicators: Dict[str, List[str]]) -> Set[str]:
    matched: Set[str] = set()
    lower = text.lower()
    for name, patterns in indicators.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                matched.add(name)
                break
    return matched


def fingerprint_program(program: Dict) -> List[str]:
    """Passively detect technologies from program metadata.

    Examines the program name, scope keywords, domain, and any
    provided URL hints. Returns a sorted list of detected technology tags.
    """
    tags: Set[str] = set()
    text_parts: List[str] = []

    name = program.get("name") or program.get("title") or ""
    domain = program.get("domain") or program.get("program_url") or ""
    scopes = program.get("scopes") or program.get("scope") or []
    scope_text = " ".join(scopes) if isinstance(scopes, list) else str(scopes)
    program_url = program.get("program_url") or program.get("url") or ""

    text_parts.extend([name, domain, scope_text, program_url])
    combined = " ".join(text_parts)

    tags.update(_match_indicators(combined, CMS_INDICATORS))
    tags.update(_match_indicators(combined, FRAMEWORK_INDICATORS))
    tags.update(_match_indicators(combined, INFRA_INDICATORS))

    wordpress_plugins = _match_indicators(combined, WORDPRESS_PLUGINS)
    if "wordpress" in tags or wordpress_plugins:
        tags.add("wordpress")
    tags.update(wordpress_plugins)

    return sorted(tags)


def classify_cms(technologies: List[str]) -> Optional[str]:
    """Return the primary CMS name from detected technology tags."""
    cms_map = {
        "wordpress", "drupal", "joomla", "magento",
        "shopify", "wix", "squarespace",
    }
    for t in technologies:
        if t in cms_map:
            return t
    return None


def is_wordpress_ecosystem(technologies: List[str]) -> bool:
    """Check if technology set indicates WordPress ecosystem."""
    wp_keywords = {"wordpress", "woocommerce", "elementor", "yoast",
                   "acf", "jetpack", "wpforms", "wordfence", "wprocket"}
    return bool(wp_keywords & set(technologies))


def score_technology_relevance(technologies: List[str]) -> float:
    """Score a program based on its tech stack relevance (0-100).

    WordPress ecosystem: +40 base
    Each WP plugin: +10
    Modern frameworks (Next.js, Django, FastAPI, etc.): +25
    Cloud infra (AWS, GCP, Azure, K8s): +20
    Well-known CMS (Drupal, Joomla, Magento): +20
    """
    score = 0.0
    tag_set = set(technologies)

    if is_wordpress_ecosystem(technologies):
        score += 40.0

    wp_plugin_bonus = len(tag_set & {
        "woocommerce", "elementor", "yoast", "acf", "jetpack",
        "wpforms", "wordfence", "wprocket",
    }) * 10.0
    score += min(wp_plugin_bonus, 40.0)

    modern_frameworks = {"nextjs", "nuxt", "django", "fastapi",
                         "spring", "laravel", "rails"}
    if tag_set & modern_frameworks:
        score += 25.0

    cloud_platforms = {"aws", "google_cloud", "azure", "cloudflare",
                       "cloudfront", "kubernetes"}
    if tag_set & cloud_platforms:
        score += 20.0

    other_cms = {"drupal", "joomla", "magento", "shopify"}
    if tag_set & other_cms:
        score += 20.0

    return min(score, 100.0)
