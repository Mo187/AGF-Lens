import os
import threading
import base64
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from functools import lru_cache

#local imports
from apps import cache

# # Bitdefender API credentials
# API_key = os.getenv('API_KEY')
# BASE_url = os.getenv('BASE_URL')


# @lru_cache(maxsize=1)
# def get_auth_header():
#     auth_string = f'{API_key}:'
#     auth_bytes = auth_string.encode('ascii')
#     auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
#     return {'Authorization': f'Basic {auth_base64}', 'Content-Type': 'application/json'}



# def get_company_details(company_id=None):
#     payload = {
#         "jsonrpc": "2.0",
#         "method": "getCompanyDetails",
#         "params": {},
#         "id": "1"
#     }
#     if company_id is not None:
#         payload['params']['companyId'] = company_id
    
#     try:
#         response = requests.post(BASE_url + 'companies', json=payload, headers=get_auth_header())
#         response.raise_for_status()
#         return response.json().get('result')
#     except requests.exceptions.RequestException as e:

#         return None


# def get_endpoints_list(parent_id=None, is_managed=None, per_page=100, filters=None, options=None):
#     all_endpoints = []
#     page = 1
    
#     while True:
#         params = {
#             "parentId": parent_id,
#             "isManaged": is_managed,
#             "page": page,
#             "perPage": per_page
#         }
        
#         if filters is not None:
#             params["filters"] = filters
#         if options is not None:
#             params["options"] = options
        
#         payload = {
#             "jsonrpc": "2.0",
#             "method": "getEndpointsList",
#             "params": params,
#             "id": "1"
#         }

#         try:
#             response = requests.post(BASE_url + 'network', json=payload, headers=get_auth_header())
#             response.raise_for_status()
#             result = response.json().get('result')
#             if not result or 'items' not in result or not result['items']:
#                 break
#             all_endpoints.extend(result['items'])
#             if len(result['items']) < per_page:
#                 break
#             page += 1
#         except requests.exceptions.RequestException as e:
#             return None

#     return all_endpoints


# def create_report(name, report_type, target_ids, scheduled_info=None, options=None, emails_list=None):
#     payload = {
#         "jsonrpc": "2.0",
#         "method": "createReport",
#         "params": {
#             "name": name,
#             "type": report_type,
#             "targetIds": target_ids,
#             "scheduledInfo": scheduled_info,
#             "options": options,
#             "emailsList": emails_list
#         },
#         "id": "1"
#     }
#     try:
#         response = requests.post(BASE_url + 'reports', json=payload, headers=get_auth_header())
#         response.raise_for_status()
#         return response.json().get('result')
#     except requests.exceptions.RequestException as e:
#         return None
    
    
# def get_network_inventory_items(parent_id=None, page=1, per_page=100, filters=None, options=None):
#     params = {
#         "parentId": parent_id,
#         "page": page,
#         "perPage": per_page,
#     }

#     if filters is not None:
#         params["filters"] = filters
#     if options is not None:
#         params["options"] = options

#     payload = {
#         "jsonrpc": "2.0",
#         "method": "getNetworkInventoryItems",
#         "params": params,
#         "id": "1"
#     }

#     try:
#         response = requests.post(BASE_url + 'network', json=payload, headers=get_auth_header())
#         response.raise_for_status()
#         return response.json().get('result')
#     except requests.exceptions.RequestException as e:
#         return None


## Freshdesk Functions ##########################################################################################################################################

fresh_url = os.getenv('fresh_url')
fresh_key = os.getenv('fresh_key')
fresh_passw = os.getenv('fresh_passw')


def process_ticket(ticket, requesters, agent_id_to_name):
    ticket_info = {
        'id': ticket.get('id'),
        'subject': ticket.get('subject', 'No Subject'),
        'requester': requesters.get(ticket.get('requester_id'), 'Unknown'),
        'priority': get_priority_name(ticket.get('priority')),
        'created_at': format_datetime(ticket.get('created_at')),
        'status': get_status_name(ticket.get('status')),
        'agent': agent_id_to_name.get(ticket.get('responder_id'), 'Unassigned')
    }
    return ticket_info

def get_priority_name(priority_code):
    priority_mapping = {
        1: 'Low',
        2: 'Medium',
        3: 'High',
        4: 'Urgent'
    }
    return priority_mapping.get(priority_code, 'Unknown')

def get_status_name(status_code):
    status_mapping = {
        2: 'Open',
        3: 'Pending',
        4: 'Resolved',
        5: 'Closed'
    }
    return status_mapping.get(status_code, 'Unknown')

def format_datetime(dt_str):
    if not dt_str:
        return ''
    dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%SZ')
    return dt.strftime('%Y-%m-%d %H:%M:%S')

@cache.cached(timeout=2000, key_prefix='cached_agent_data')
def get_agent_data(session):
    agents_response = session.get(f"{fresh_url}agents", auth=(fresh_key, fresh_passw))
    agents_response.raise_for_status()
    return agents_response.json()

def get_requesters(requester_ids, session):
    requesters = {}
    missing_requester_ids = []

    # Check cache first
    for requester_id in requester_ids:
        cached_name = cache.get(f'requester_{requester_id}')
        if cached_name:
            requesters[requester_id] = cached_name
        else:
            missing_requester_ids.append(requester_id)
    
    cache_lock = threading.Lock()

    def fetch_requester(requester_id):
        contact_response = session.get(
            f"{fresh_url}contacts/{requester_id}",
            auth=(fresh_key, fresh_passw)
        )
        if contact_response.status_code == 200:
            contact_data = contact_response.json()
            name = contact_data.get('name', 'Unknown')
        else:
            name = 'Unknown'

        # Acquire the lock before updating shared data
        with cache_lock:
            requesters[requester_id] = name
            cache.set(f'requester_{requester_id}', name, timeout=86400)

    threads = []
    for requester_id in missing_requester_ids:
        thread = threading.Thread(target=fetch_requester, args=(requester_id,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return requesters

@cache.cached(timeout=300, key_prefix='average_resolution_time')
def get_average_resolution_time(session):
    # Define time range
    days_back = 30  # Adjust as needed
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    # Fetch resolved tickets within the time range
    tickets_url = f"{fresh_url}tickets"
    params = {
        'per_page': 100,
        'order_by': 'created_at',
        'order_type': 'desc',
        'include': 'stats',
    }
    headers = {'Content-Type': 'application/json'}

    total_resolution_time = timedelta()
    resolved_ticket_count = 0
    page = 1
    while True:
        params['page'] = page
        response = session.get(
            tickets_url,
            params=params,
            headers=headers,
            auth=(fresh_key, fresh_passw)
        )
        response.raise_for_status()
        tickets = response.json()
        if not tickets:
            break
        for ticket in tickets:
            status = ticket.get('status')
            created_at_str = ticket.get('created_at')
            resolved_at_str = ticket.get('stats', {}).get('resolved_at')
            if status in [4, 5] and created_at_str and resolved_at_str:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ')
                resolved_at = datetime.strptime(resolved_at_str, '%Y-%m-%dT%H:%M:%SZ')
                if start_date <= resolved_at <= end_date:
                    resolution_time = resolved_at - created_at
                    total_resolution_time += resolution_time
                    resolved_ticket_count += 1
        if len(tickets) < 100 or page >= 30:
            break
        page += 1

    if resolved_ticket_count == 0:
        avg_resolution_time_hours = 0
    else:
        average_resolution_time = total_resolution_time / resolved_ticket_count
        avg_resolution_time_hours = average_resolution_time.total_seconds() / 3600

    return avg_resolution_time_hours

@cache.cached(timeout=300, key_prefix='ticket_status_distribution')
def get_ticket_status_distribution(session):
    # Define time range
    days_back = 30  # Adjust as needed
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    # Fetch tickets created within the time range
    tickets_url = f"{fresh_url}tickets"
    params = {
        'per_page': 100,
        'order_by': 'created_at',
        'order_type': 'desc',
    }
    headers = {'Content-Type': 'application/json'}

    status_counts = defaultdict(int)
    page = 1
    while True:
        params['page'] = page
        response = session.get(
            tickets_url,
            params=params,
            headers=headers,
            auth=(fresh_key, fresh_passw)
        )
        response.raise_for_status()
        tickets = response.json()
        if not tickets:
            break
        for ticket in tickets:
            created_at_str = ticket.get('created_at')
            if created_at_str:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ')
                if start_date <= created_at <= end_date:
                    status = get_status_name(ticket.get('status'))
                    status_counts[status] += 1
        if len(tickets) < 100 or page >= 30:
            break
        page += 1

    statuses = list(status_counts.keys())
    counts = [status_counts[status] for status in statuses]

    return statuses, counts

@cache.memoize(timeout=300)
def get_ticket_volume_over_time(session):
    # Define time range
    days_back = 30  # Adjust as needed
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    # Initialize variables
    tickets_url = f"{fresh_url}tickets"
    params = {
        'per_page': 100,
        'order_by': 'created_at',
        'order_type': 'asc',
    }
    headers = {'Content-Type': 'application/json'}

    # Fetch tickets
    all_tickets = []
    page = 1
    while True:
        params['page'] = page
        response = session.get(
            tickets_url,
            params=params,
            headers=headers,
            auth=(fresh_key, fresh_passw)
        )
        response.raise_for_status()
        tickets = response.json()
        if not tickets:
            break
        all_tickets.extend(tickets)
        if len(tickets) < 100 or page >= 30:
            break
        page += 1

    # Group tickets by date
    ticket_volume = defaultdict(int)
    for ticket in all_tickets:
        created_at_str = ticket.get('created_at')
        if created_at_str:
            created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ')
            if start_date <= created_at <= end_date:
                date_key = created_at.strftime('%Y-%m-%d')  # Group by day
                ticket_volume[date_key] += 1

    # Ensure all dates in range are present
    date_list = [start_date + timedelta(days=x) for x in range(days_back + 1)]
    sorted_dates = [date.strftime('%Y-%m-%d') for date in date_list]
    ticket_counts = [ticket_volume.get(date, 0) for date in sorted_dates]

    return sorted_dates, ticket_counts