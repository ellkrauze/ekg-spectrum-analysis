import logging
import os

from matplotlib.figure import Figure

from ekg.config import load_config

logger = logging.getLogger(__name__)


def save_fig(fig: Figure, name: str):
    cfg = load_config()
    figures_path = cfg["paths"]["figures"]
    fname = os.path.join(figures_path, name)
    os.makedirs(figures_path, exist_ok=True)
    fig.savefig(fname=fname, dpi="figure", bbox_inches="tight")
    logger.info("Saved figure to %s", fname)
