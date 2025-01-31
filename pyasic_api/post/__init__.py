import asyncio
from typing import Union, List

from fastapi import HTTPException, APIRouter
from pydantic import BaseModel

from pyasic import MinerNetwork, MinerData

router = APIRouter(tags=["POST"])

def create_hosts(ip_constructor) -> list:
    hosts = []
    if isinstance(ip_constructor, list):
        for item in ip_constructor:
            hosts += _create_network(item)
    elif isinstance(ip_constructor, str):
        constructor = ip_constructor.replace(" ", "")
        constructor_list = constructor.split(",")
        for item in constructor_list:
            hosts += _create_network(item)
    return hosts


def _create_network(constructor) -> list:
    if "-" in constructor:
        hosts = MinerNetwork(constructor).hosts()
    else:
        hosts = [constructor]
    return hosts


class DataSelector(BaseModel):
    targets: Union[List[str], str] = "192.168.1.1-192.168.1.255"
    data_selectors: Union[List[str], None] = None


@router.post("/get_data/", summary="Get data from selected miners")
async def get_data(data_selector: DataSelector):
    """Get data from all miners as defined by the selector.

    - ### targets:
        - A set of target IPs to query against.  This uses
        [`pyasic.MinerNetwork`](https://pyasic.readthedocs.io/en/latest/network/miner_network/)
        to scan for miners and uses the same constructor format.  Targets can be a string
        formatted as {ip_1}-{ip_2} which will select all IP addresses in that range, or a string
        with a single ip address, or a list of any combination of these.
    - ### data_selectors:
        - A list of data points to select from the data.  If this is not passed,
        all data will be returned.  Selectable items are all items contained by
        [`pyasic.MinerData`](https://pyasic.readthedocs.io/en/latest/data/miner_data/).
    """
    if data_selector.data_selectors == ["string"]:
        data_selectors = None
    try:
        hosts = create_hosts(data_selector.targets)
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad constructor string")

    miners = await MinerNetwork(hosts).scan_network_for_miners()
    data = await asyncio.gather(*[miner.get_data() for miner in miners])

    ret_data = {}
    for item in data:
        miner_data = {}
        if data_selector.data_selectors:
            for dp in data_selector.data_selectors:
                try:
                    miner_data[dp] = item[dp]
                except KeyError:
                    raise HTTPException(status_code=400, detail=f"Bad data point: {dp}")
            ret_data[item['ip']] = miner_data
        else:
            ret_data[item['ip']] = item.asdict()
    return ret_data
