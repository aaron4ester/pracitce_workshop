"""Run only the transaction-history feature, without the rest of the backend.

    uvicorn app.transactions.standalone:app --reload

Handy while app/main.py is still being assembled by the rest of the team.
"""

from .integration import create_app

app = create_app()
