from pathlib import Path
from typing import Any

import ipaddress
import json
import makejinja
import re
import shutil
import subprocess


# Return the filename of a path without the j2 extension
def basename(value: str) -> str:
    return Path(value).stem


# Return the nth host in a CIDR range
def nthhost(value: str, query: int) -> str:
    try:
        network = ipaddress.ip_network(value, strict=False)
        if 0 <= query < network.num_addresses:
            return str(network[query])
    except ValueError:
        pass
    return False


# Return the age public or private key from age.key
def age_key(key_type: str, file_path: str = 'age.key') -> str:
    try:
        with open(file_path, 'r') as file:
            file_content = file.read().strip()
        if key_type == 'public':
            key_match = re.search(r"# public key: (age1[\w]+)", file_content)
            if not key_match:
                raise ValueError("Could not find public key in the age key file.")
            return key_match.group(1)
        elif key_type == 'private':
            key_match = re.search(r"(AGE-SECRET-KEY-[\w]+)", file_content)
            if not key_match:
                raise ValueError("Could not find private key in the age key file.")
            return key_match.group(1)
        else:
            raise ValueError("Invalid key type. Use 'public' or 'private'.")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while processing {file_path}: {e}")


# Return the GitHub deploy key from github-deploy.key
def github_deploy_key(file_path: str = 'github-deploy.key') -> str:
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while reading {file_path}: {e}")


# Return a list of files in the talos patches directory
def talos_patches(value: str) -> list[str]:
    path = Path(f'template/config/talos/patches/{value}')
    if not path.is_dir():
        return []
    return [str(f) for f in sorted(path.glob('*.yaml.j2')) if f.is_file()]


CONFIG_FILE = 'cluster.toml'
SCHEMA_FILE = 'template/resources/config.schema.cue'


def _cue_export_candidates() -> list[list[str]]:
    candidates: list[list[str]] = []

    # Prefer the binary path resolved by mise so Python venv shims cannot shadow it.
    if shutil.which('mise'):
        resolved = subprocess.run(
            ['mise', 'which', 'cue'],
            capture_output=True,
            text=True,
        )
        cue_path = resolved.stdout.strip()
        if resolved.returncode == 0 and cue_path:
            candidates.append([cue_path, 'export', CONFIG_FILE, SCHEMA_FILE, '--out', 'json'])
        candidates.append(['mise', 'exec', '--', 'cue', 'export', CONFIG_FILE, SCHEMA_FILE, '--out', 'json'])

    candidates.append(['cue', 'export', CONFIG_FILE, SCHEMA_FILE, '--out', 'json'])
    return candidates


# Run `cue export` to validate and apply schema defaults to the user's config.
def cue_export() -> dict[str, Any]:
    failures: list[str] = []
    for command in _cue_export_candidates():
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            failures.append(f"{' '.join(command)}\n{result.stderr.strip()}")
            continue

        stdout = result.stdout.strip()
        if not stdout:
            failures.append(f"{' '.join(command)}\nno JSON output on stdout\n{result.stderr.strip()}")
            continue

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            failures.append(f"{' '.join(command)}\ninvalid JSON output: {e}\n{result.stdout[:300]}")

    details = '\n\n'.join(failures) if failures else 'no commands attempted'
    raise RuntimeError(f"cue export failed:\n{details}")


class Plugin(makejinja.plugin.Plugin):
    def __init__(self, data: dict[str, Any]):
        self._data = data


    def data(self) -> makejinja.plugin.Data:
        data = cue_export()
        # network.default_gateway is the one default CUE cannot express
        # (no CIDR arithmetic in CUE's stdlib).
        network = data['network']
        network.setdefault('default_gateway', nthhost(network['node_cidr'], 1))
        return data


    def filters(self) -> makejinja.plugin.Filters:
        return [
            basename,
            nthhost
        ]


    def functions(self) -> makejinja.plugin.Functions:
        return [
            age_key,
            github_deploy_key,
            talos_patches
        ]
