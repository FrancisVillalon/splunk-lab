"""ALWAYS IGNORE"""

IGNORE_ALWAYS = {}


"""ENDPOINTS"""
"""
<sub_category>: {
    <endpoint>: (<endpoint_path>, <additional path params>, <set()>)
}
"""
ENDPOINTS = {
    "apps": {
        "apps_local": ("/services/apps/local", set()),
    },
    "inputs_outputs_indexes": {
        "indexes": ("/servicesNS/-/-/data/indexes", set()),
    },
    "auth_access_control": {
        "roles": ("/servicesNS/-/-/authorization/roles", set()),
        "users": ("/servicesNS/-/-/authentication/users", set()),
    },
    "kvstore": {
        "collections": ("/servicesNS/-/-/storage/collections/config", set()),
        "status": ("/services/kvstore/status", set()),
        "collections_conf": ("/servicesNS/-/-/configs/conf-collections", set()),
    },
    "search_time_objects": {
        "alert_actions": ("/servicesNS/-/-/admin/alert_actions", set()),
    },
    "props_field_processing": {
        "transforms": ("/servicesNS/-/-/data/transforms/extractions", set()),
        "lookup_defs": ("/servicesNS/-/-/data/transforms/lookups", set()),
        "lookup_files": ("/servicesNS/-/-/data/lookup-table-files", set()),
    },
    "server": {"info": ("/services/server/info", set())},
}
