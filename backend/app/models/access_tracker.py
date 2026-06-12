from datetime import datetime

from pydantic import BaseModel


class AccessTrackerSummary(BaseModel):
    """Summary row for the Access Tracker table view.

    TODO: adjust field names once real ClearPass Access Tracker record shapes
    are confirmed (see client.py / builder.py TODOs).
    """

    id: str
    timestamp: datetime
    service_name: str
    username: str | None = None
    endpoint_mac: str | None = None
    result: str  # e.g. "ACCEPT", "REJECT", "DROP"
