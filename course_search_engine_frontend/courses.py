'''
Course search engine: search

Xinyue 'Yolanda' Pan
'''

from math import radians, cos, sin, asin, sqrt, ceil
import sqlite3
import os


# Use this filename for the database
DATA_DIR = os.path.dirname(__file__)
DATABASE_FILENAME = os.path.join(DATA_DIR, 'course_information.sqlite3')

FIELD_MAPPING_TABLE = {
    "dept": "courses.dept",
    "day": "meeting_patterns.day",
    "time_start": "meeting_patterns.time_start",
    "time_end": "meeting_patterns.time_end",
    "building_code": "sections.building_code",
    "walking_time": "walking_time", # need furthur calculation
    "enrollment": "sections.enrollment",
    "title": 'courses.title',
    "section_num": 'sections.section_num',
    "course_num": 'courses.course_num'
    }

def compute_projection(args_from_ui):
    """
    computes the attributes that go in the projection
    """
    columns = ['dept', 'course_num', 'title']
    fields = [FIELD_MAPPING_TABLE[x] for x in columns]

    if any(key in args_from_ui for key in ["building_code", "walking_time"]):
        extra_columns = ['section_num', 'day', 'time_start', 'time_end', 'enrollment', 'building_code', 'walking_time']
        lst = [FIELD_MAPPING_TABLE[x] for x in extra_columns[:-2]]
        fields.extend(lst)
        fields.append('sections.building_code')
        fields.append("compute_time_between(gps.lon, gps.lat, target.lon, target.lat) AS walking_time")
        columns.extend(extra_columns)
    
    elif any(key in args_from_ui for key in ["day", "time_start", "time_end", "enrollment"]):
        extra_columns = ['section_num', 'day', 'time_start', 'time_end', 'enrollment']
        lst = [FIELD_MAPPING_TABLE[x] for x in extra_columns]
        fields.extend(lst)
        columns.extend(extra_columns)

    return ', '.join(fields), columns

def compute_join(args_from_ui):
    """
    write the FROM, ON, JOIN queries

    (to compute relations and join conditions)
    """
    query = " courses"
    params = []

    if len(args_from_ui) == 1 and 'dept' in args_from_ui:
        return query, params
    
    query += " LEFT JOIN sections ON courses.course_id = sections.course_id"
    if any(key in args_from_ui for key in ["day", "time_start", "time_end", "enrollment", "building_code", "walking_time"]):
        query += " JOIN meeting_patterns ON sections.meeting_pattern_id = meeting_patterns.meeting_pattern_id"
    if 'terms' in args_from_ui:
        query += " JOIN catalog_index ON courses.course_id = catalog_index.course_id"
    if any(key in args_from_ui for key in ["building_code", "walking_time"]):
        query += " JOIN gps ON sections.building_code = gps.building_code"
        query += " JOIN gps AS target ON target.building_code = ?"
        params.append(args_from_ui['building_code'])
    return query, params

def compute_conditions(args_from_ui):
    """
    write the WHERE queries
    return clause, arguments
    """
    condition = []
    params = []
    group_by_clause = ''
    base_conditions = {
        'terms': ' IN ({})',
        'dept': ' = ?',
        'day': ' IN ({})',
        'enrollment': ' BETWEEN ? AND ?',
        'time_start': ' >= ?',
        'time_end': ' <= ?',
        'walking_time': ' <= ?'
    }

    for key, value in args_from_ui.items():
        if value and key in base_conditions:
            if key in ('terms', 'day'):
                placeholder = ', '.join(['?' for _ in value])
                if key == 'terms':
                    condition.append(f' catalog_index.word IN ({placeholder})')
                    group_by_clause = f' GROUP BY courses.course_id, sections.section_id'
                    if len(value) > 1:
                        group_by_clause += f' HAVING COUNT(DISTINCT catalog_index.word) >= {len(value)}'
                else:
                    condition.append(f'{FIELD_MAPPING_TABLE[key]} {base_conditions[key].format(placeholder)}')
                params.extend(value)
            else:
                condition.append(f'{FIELD_MAPPING_TABLE[key]} {base_conditions[key]}')
                if isinstance(value, (list, tuple)):
                    params.extend(value) 
                else:
                    params.append(value)
    query = ''
    if condition:
        query = ' WHERE ' + ' AND '.join(condition)
    if group_by_clause:
        query += group_by_clause

    return query, params

def build_query(args_from_ui):

    """
    input: takes output (strings) from projection and condition functions,
    assembles it, executes a sql query using this string

    ouput: returns all courses that meet a specific (dept, day, etc.) criteria

    but this function calls the following functions:

        compute_projection(args_from_ui)
        compute_join(args_from_ui)
        compute_conditions(args_from_ui)

    """
    (proj_str, _) = compute_projection(args_from_ui)
    (join_str, join_args) = compute_join(args_from_ui)
    (where_str, where_args) = compute_conditions(args_from_ui)

    query_format = """SELECT {}\nFROM {}\n{}"""
    query = query_format.format(proj_str, join_str, where_str)

    return (query, join_args + where_args)
 

def find_courses(args_from_ui):
    '''
    Takes a dictionary containing search criteria and returns courses
    that match the criteria.  The dictionary will contain some of the
    following fields:

      - dept a string
      - day is list of strings
           -> ["'MWF'", "'TR'", etc.]
      - time_start is an integer in the range 0-2359
      - time_end is an integer an integer in the range 0-2359
      - enrollment is a pair of integers
      - walking_time is an integer
      - building_code ia string
      - terms is a list of strings string: ["quantum", "plato"]

    Returns a pair: an ordered list of attribute names and a list the
     containing query results.  Returns ([], []) when the dictionary
     is empty.
    '''

    assert_valid_input(args_from_ui)

    if not args_from_ui:
        return ([], [])
    else:
        (query, args) = build_query(args_from_ui)

    _, columns = compute_projection(args_from_ui)

    conn = sqlite3.connect(DATABASE_FILENAME)
    conn.create_function("compute_time_between", 4, compute_time_between)
    cur = conn.cursor()

    results = cur.execute(query, args).fetchall()
    conn.close()

    # replace with a list of the attribute names in order and a list
    # of query results.

    return (columns, results)


########### auxiliary functions #################
########### do not change this code #############

def assert_valid_input(args_from_ui):
    '''
    Verify that the input conforms to the standards set in the
    assignment.
    '''

    assert isinstance(args_from_ui, dict)

    acceptable_keys = set(['time_start', 'time_end', 'enrollment', 'dept',
                           'terms', 'day', 'building_code', 'walking_time'])
    assert set(args_from_ui.keys()).issubset(acceptable_keys)

    # get both buiding_code and walking_time or neither
    has_building = ("building_code" in args_from_ui and
                    "walking_time" in args_from_ui)
    does_not_have_building = ("building_code" not in args_from_ui and
                              "walking_time" not in args_from_ui)

    assert has_building or does_not_have_building

    assert isinstance(args_from_ui.get("building_code", ""), str)
    assert isinstance(args_from_ui.get("walking_time", 0), int)

    # day is a list of strings, if it exists
    assert isinstance(args_from_ui.get("day", []), (list, tuple))
    assert all([isinstance(s, str) for s in args_from_ui.get("day", [])])

    assert isinstance(args_from_ui.get("dept", ""), str)

    # terms is a non-empty list of strings, if it exists
    terms = args_from_ui.get("terms", [""])
    assert terms
    assert isinstance(terms, (list, tuple))
    assert all([isinstance(s, str) for s in terms])

    assert isinstance(args_from_ui.get("time_start", 0), int)
    assert args_from_ui.get("time_start", 0) >= 0

    assert isinstance(args_from_ui.get("time_end", 0), int)
    assert args_from_ui.get("time_end", 0) < 2400

    # enrollment is a pair of integers, if it exists
    enrollment_val = args_from_ui.get("enrollment", [0, 0])
    assert isinstance(enrollment_val, (list, tuple))
    assert len(enrollment_val) == 2
    assert all([isinstance(i, int) for i in enrollment_val])
    assert enrollment_val[0] <= enrollment_val[1]


def compute_time_between(lon1, lat1, lon2, lat2):
    '''
    Converts the output of the haversine formula to walking time in minutes
    '''
    meters = haversine(lon1, lat1, lon2, lat2)

    # adjusted downwards to account for manhattan distance
    walk_speed_m_per_sec = 1.1
    mins = meters / (walk_speed_m_per_sec * 60)

    return int(ceil(mins))


def haversine(lon1, lat1, lon2, lat2):
    '''
    Calculate the circle distance between two points
    on the earth (specified in decimal degrees)
    '''
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))

    # 6367 km is the radius of the Earth
    km = 6367 * c
    m = km * 1000
    return m


def get_header(cursor):
    '''
    Given a cursor object, returns the appropriate header (column names)
    '''
    header = []

    for i in cursor.description:
        s = i[0]
        if "." in s:
            s = s[s.find(".")+1:]
        header.append(s)

    return header
