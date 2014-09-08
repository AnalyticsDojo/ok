"""
Utility functions used by API and other services
"""
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import zipfile as zf
from flask import jsonify, request, Response, json

from google.appengine.api import memcache

def coerce_to_json(data, fields):
    if hasattr(data, 'to_json'):
        return data.to_json(fields)
    elif isinstance(data, list):
        return [mdl.to_json(fields) if hasattr(data, 'to_json')
                else coerce_to_json(mdl, fields) for mdl in data]
    elif isinstance(data, dict):
        return {k: (mdl.to_json(fields.get(k, {})) if hasattr(data, 'to_json')
                else coerce_to_json(mdl, fields.get(k, {}))) for k, mdl in data.iteritems()}
    else:
        return data

#TODO(martinis) somehow having data be an empty list doesn't make it
# return an empty list, but an empty object.
def create_api_response(status, message, data=None):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    if isinstance(data, dict) and 'results' in data:
        data['results'] = (
            coerce_to_json(data['results'], request.fields.get('fields', {})))

    if request.args.get('format', 'default') == 'raw':
        response = Response(json.dumps(data))
    else:
        response = jsonify(**{
            'status': status,
            'message': message,
            'data': data
        })
    response.status_code = status
    return response

def create_zip(obj):
    zipfile_str = StringIO()
    with zf.ZipFile(zipfile_str, 'w') as zipfile:
        for filename, contents in obj.items():
            zipfile.writestr(filename, contents)
    zip_string = zipfile_str.getvalue()
    return zip_string

def paginate(entries, page, num_per_page):
    """
    Added stuff from
    https://p.ota.to/blog/2013/4/pagination-with-cursors-
        in-the-app-engine-datastore/

    Support pagination for an NDB query.
    Arguments:
      |entries| - a query which returns the items to paginate over.
      |cursor|  - a cursor of where in the pagination the user is.
      |num_per_page| - the number of results to display per page.

    The return value will be different from a regular query:
    There will be 3 things returned:
    - results: a list of results
    - forward_curs: a urlsafe hash for the cursor. Use this to get
    the next page. To retrieve the cursor object, do Cursor(urlsafe=s)
    - more: a boolean for whether or not there is more content.

    For more documentation, look at:
    https://developers.google.com/appengine/docs/python/ndb/queryclass#Query_fetch_page
    """
    if num_per_page is None:
        return {
            'results': entries.fetch(),
            'page': 0,
            'more': False
        }

    this_page_cursor_key = "cursor_page_%s" % page
    next_page_cursor_key = "cursor_page_%s" % (page + 1)
    cursor = None
    if page > 0:
        cursor = memcache.get(this_page_cursor_key) # pylint: disable=no-member
        if not cursor:
            page = 0 # Reset to the front, since memcached failed

    if cursor is not None:
        results, forward_cursor, more = entries.fetch_page(
            int(num_per_page), start_cursor=cursor)
    else:
        results, forward_cursor, more = entries.fetch_page(int(num_per_page))

    memcache.set(next_page_cursor_key, forward_cursor) # pylint: disable=no-member

    return {
        'results': results,
        'page': page,
        'more': more
    }

def _apply_filter(query, model, arg, value):
    field = getattr(model, arg, None)
    if not field:
        # Silently swallow for now
        # TODO(martinis) cause an error
        return query

    # Only equals for now
    return query.filter(field == value)

def filter_query(query, args, model):
    """
    Applies the filters in |args| to |query|.
    |args| is a dictionary of key to value, to be used to filter the query.
    |allowed| is an optional list of the allowed filters.

    Returns a modified query with the appropriate filters.
    """
    for arg, value in args.iteritems():
        query = _apply_filter(query, model, arg, value)

    return query
