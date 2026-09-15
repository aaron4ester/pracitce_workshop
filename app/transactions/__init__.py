"""Transaction history feature (owner: Ayan).

Mount it on the main app with one line:

    from .transactions import setup_transactions
    setup_transactions(app)

To require a signed-in user on every history route:

    setup_transactions(app, dependencies=[Depends(get_current_user)])

Layout (MVC, one file per layer):
    router.py      Controller: HTTP in, JSON out
    service.py     Business rules: paging, month windows, CSV, validation
    repository.py  All SQL lives here
    models.py      The Transaction entity (one table row)
    schemas.py     JSON shapes the frontend sees
    database.py    Connection + table creation
"""

from .integration import create_app, setup_transactions
from .router import router

__all__ = ["router", "setup_transactions", "create_app"]
