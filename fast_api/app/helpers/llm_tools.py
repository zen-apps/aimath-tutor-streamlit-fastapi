import json


def build_json_sierializable(response):
    """Build json sierializable."""
    build_json_sierializable = {}
    for key, value in response.items():
        try:
            json.dumps(value)
            build_json_sierializable[key] = value
        except:
            build_json_sierializable[key] = str(value)
    return build_json_sierializable
