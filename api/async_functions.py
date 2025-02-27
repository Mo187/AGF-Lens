import aiohttp
import asyncio
import base64
import os
from functools import lru_cache
from functools import wraps

# Bitdefender API credentials
API_key = os.getenv('API_KEY')
BASE_url = os.getenv('BASE_URL')

# Helper to get auth header

@lru_cache(maxsize=1)
def get_auth_header():
    auth_string = f'{API_key}:'
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    return {'Authorization': f'Basic {auth_base64}', 'Content-Type': 'application/json'}

# Wrapper to make async functions usable in synchronous code
def async_to_sync(async_func):
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

# Async version of get_company_details
async def _get_company_details_async(company_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "getCompanyDetails",
        "params": {},
        "id": "1"
    }
    if company_id is not None:
        payload['params']['companyId'] = company_id
    
    # Create the session directly in the function
    async with aiohttp.ClientSession(headers=get_auth_header()) as session:
        try:
            async with session.post(BASE_url + 'companies', json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result')
                return None
        except Exception as e:
            print(f"Error in get_company_details: {str(e)}")
            return None

# Synchronous wrapper
@async_to_sync
async def get_company_details(company_id=None):
    return await _get_company_details_async(company_id)

# Async version of get_endpoints_list
async def _get_endpoints_list_async(parent_id=None, is_managed=None, per_page=100, filters=None, options=None):
    all_endpoints = []
    page = 1
    
    while True:
        params = {
            "parentId": parent_id,
            "isManaged": is_managed,
            "page": page,
            "perPage": per_page
        }
        
        if filters is not None:
            params["filters"] = filters
        if options is not None:
            params["options"] = options
        
        payload = {
            "jsonrpc": "2.0",
            "method": "getEndpointsList",
            "params": params,
            "id": "1"
        }

        # Create the session directly in the function
        async with aiohttp.ClientSession(headers=get_auth_header()) as session:
            try:
                async with session.post(BASE_url + 'network', json=payload, timeout=15) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    result = data.get('result')
                    
                    if not result or 'items' not in result or not result['items']:
                        break
                        
                    all_endpoints.extend(result['items'])
                    
                    if len(result['items']) < per_page:
                        break
                        
                    page += 1
            except Exception as e:
                print(f"Error in get_endpoints_list: {str(e)}")
                return None

    return all_endpoints

# Synchronous wrapper
@async_to_sync
async def get_endpoints_list(parent_id=None, is_managed=None, per_page=100, filters=None, options=None):
    return await _get_endpoints_list_async(parent_id, is_managed, per_page, filters, options)

# Add the async version of get_network_inventory_items since it's used in routes.txt
async def _get_network_inventory_items_async(parent_id=None, page=1, per_page=100, filters=None, options=None):
    params = {
        "parentId": parent_id,
        "page": page,
        "perPage": per_page,
    }

    if filters is not None:
        params["filters"] = filters
    if options is not None:
        params["options"] = options

    payload = {
        "jsonrpc": "2.0",
        "method": "getNetworkInventoryItems",
        "params": params,
        "id": "1"
    }

    async with aiohttp.ClientSession(headers=get_auth_header()) as session:
        try:
            async with session.post(BASE_url + 'network', json=payload, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result')
                return None
        except Exception as e:
            print(f"Error in get_network_inventory_items: {str(e)}")
            return None

# Synchronous wrapper
@async_to_sync
async def get_network_inventory_items(parent_id=None, page=1, per_page=100, filters=None, options=None):
    return await _get_network_inventory_items_async(parent_id, page, per_page, filters, options)