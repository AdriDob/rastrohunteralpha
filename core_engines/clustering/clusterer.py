

class Clusterer:
    def cluster_endpoints(
        self, endpoints: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        grouped = {}
        for endpoint in endpoints:
            key = endpoint.get("path", "").split("/")[1:3]
            key = "/".join(key)
            grouped.setdefault(key, []).append(endpoint)
        return [
            {"group": group, "count": len(items), "members": items}
            for group, items in grouped.items()
        ]
