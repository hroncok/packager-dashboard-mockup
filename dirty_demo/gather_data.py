# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import asyncio
import getpass
import warnings

import httpx

FEDORAS = [30, 31, 32]
EPELS = [6, 7, 8]
RAWHIDE = FEDORAS[-1]
USER = getpass.getuser()


async def pagure_owner_alias():
    url = "https://src.fedoraproject.org/extras/pagure_owner_alias.json"
    r = await httpx.get(url)
    r.raise_for_status()

    return r.json()["rpms"]


async def my_packages(user=USER):
    packages = await pagure_owner_alias()
    return [p for p in packages if user in packages[p]]


async def _healthcheck(version, *, testing=False):
    if testing:
        version = f"{version}-testing"
    url = (
        f"https://pagure.io/fedora-health-check/raw/master/f/data/report-{version}.json"
    )
    r = await httpx.get(url)
    if r.is_error:
        warnings.warn(f"Healtcheck {version} returned error {r.status_code}")
        return {}
    closure = r.json()["closure"]
    return {p["package"]: p for p in closure}


async def healthcheck():
    tasks = {}
    for f in FEDORAS:
        if f == RAWHIDE:
            tasks[(f, False)] = asyncio.create_task(_healthcheck("rawhide"))
        else:
            tasks[(f, False)] = asyncio.create_task(_healthcheck(f))
            tasks[(f, True)] = asyncio.create_task(_healthcheck(f, testing=True))
    return {k: await t for k, t in tasks.items()}


async def main():
    healthcheck_task = asyncio.create_task(healthcheck())
    my_pkgs_task = asyncio.create_task(my_packages())

    for pkg in await my_pkgs_task:
        for fedora in FEDORAS:
            for testing in False, True:
                try:
                    print((await healthcheck_task)[fedora, testing][pkg])
                except KeyError:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
