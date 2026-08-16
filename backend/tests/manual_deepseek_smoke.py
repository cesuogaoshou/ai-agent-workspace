import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.api.agent import create_run
from backend.app.schemas.agent import CreateRunRequest


if __name__ == "__main__":
    response = create_run(CreateRunRequest(task="Use the calculator to compute 12 * 7 + 3."))
    print(response.model_dump_json(indent=2))
