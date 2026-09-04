"""Read the workflow configuration."""

import json
import os

CONFIG_ENV_VAR = "AFTDB_CONFIG"
DEFAULT_CONFIG_PATH = "config.json"


def load_config(config_path=None):
    """Read the JSON config file that holds the workflow data paths

    Parameters
    ----------
    config_path : str, optional
        Path to the config file. Defaults to the value of the ``AFTDB_CONFIG``
        environment variable, else ``config.json`` in the current working
        directory. Both the Snakefile and the README expect ``config.json`` at
        the root of a working copy, and snakemake runs scripts from there, so
        the default resolves the same file the workflow itself reads.

    Returns
    -------
    dict
        Parsed config, with data paths under the "paths" key.
    """
    if config_path is None:
        config_path = os.environ.get(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)

    with open(config_path, "r") as config_fh:
        return json.load(config_fh)
