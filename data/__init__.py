from dotenv import load_dotenv

# Load .env (project root) so FRED_API_KEY and friends are available before
# any submodule reads os.environ.
load_dotenv()

from .inputs import ModelInputs, get_inputs  # noqa: E402

__all__ = ["ModelInputs", "get_inputs"]
