"""
PA1: Course Search Engine Part 1
Yolanda Pan
"""
# DO NOT REMOVE THESE LINES OF CODE
# pylint: disable-msg=invalid-name, redefined-outer-name, unused-argument, unused-variable

import queue
import json
import sys
import csv
import re
import bs4
import util

INDEX_IGNORE = set(['a', 'also', 'an', 'and', 'are', 'as', 'at', 'be',
                    'but', 'by', 'course', 'for', 'from', 'how', 'i',
                    'ii', 'iii', 'in', 'include', 'is', 'not', 'of',
                    'on', 'or', 's', 'sequence', 'so', 'social', 'students',
                    'such', 'that', 'the', 'their', 'this', 'through', 'to',
                    'topics', 'units', 'we', 'were', 'which', 'will', 'with',
                    'yet'])


### YOUR FUNCTIONS HERE
def process_page(url):
    '''
    Fetches and parses a webpage from the given URL.

    Args:
        url (str): The URL of the webpage to fetch and parse.

    Returns:
        BeautifulSoup: Parsed HTML as a BeautifulSoup object, or None if the request fails.
    '''
    request = util.get_request(url)
    if request is None:
        return []
    html = util.read_request(request)
    if not html:
        return []
    soup = bs4.BeautifulSoup(html, 'html.parser')
    return soup

def extract_links(soup, current_url, limiting_domain):
    '''
    Extracts and returns a set of valid, absolute URLs from the given HTML content (soup).
    
    Args:
        soup (BeautifulSoup): Parsed HTML content.
        current_url (str): The URL of the page that the soup was scraped from.
        limiting_domain (str): The domain to limit the URLs to (for domain filtering).
        
    Returns:
        set: A set containing valid absolute URLs.
    '''
    links = set()
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            absolute_url = util.convert_if_relative_url(current_url, href)
            if absolute_url and util.is_url_ok_to_follow(absolute_url, limiting_domain):
                links.add(absolute_url)
    return links

def extract_course_codes(title_text):
    """
    Extracts all course codes from a title text, including sequences of any length.
    
    This function handles cases like:
    - Single courses: "CMSC 12100"
    - Two-course sequences: "ANTH 20701-20702"
    - Multi-course sequences: "CMSC 12100-12200-12300-12400"
    
    Args:
        title_text (str): The course title text containing course codes
        
    Returns:
        list: A list of all course codes found in the text
    """

    pattern = r'([A-Z]+)\s+((?:\d{5}(?:-\d{5})*))'
    matches = re.finditer(pattern, title_text)
    course_codes = []

    for match in matches:
        dept = match.group(1)
        print(dept)
        all_num = match.group(2)
        num_list = all_num.split('-')
        for num in num_list:
            course_codes.append(f"{dept} {num}")
    return course_codes

def get_valid_words(text):
    """
    Extracts valid words from text, handling all text processing rules.
    1. Converting to lowercase
    2. Finding valid words (starts with a-z and contains only a-z, 0-9, and/or _)
    3. Removing stop words
    
    Args:
        text (str): The input text to process
        
    Returns:
        set: A set of valid words that aren't in INDEX_IGNORE
    """
    text = text.lower()
    words = set(re.findall(r'[a-z][a-z0-9_]*', text))
    return words - INDEX_IGNORE

def extract_course_info(url, course_map):
    '''
    Helper function that takes a url of a webpage and the 
    text in  that webpage, process it, map its unique id from course map,
    and return dictionary of that course.

    Input:
        url: page to scrape
        course_map: the dictionary that maps course code to unique identifiers.

    Output:
        dictionary of course information
    '''
    word_to_courses = {}
    soup = process_page(url)
    if not soup:
        return {}
    # 'courseblock main' and 'courseblock subsequence' has the same html structure
    for block in soup.find_all('div', class_=['courseblock main', 'courseblock subsequence']):
       #  process courseb title
        title_tag = block.find('p', class_='courseblocktitle')
        title_text = title_tag.get_text(strip = True)
        # extract course code from title
        course_codes = extract_course_codes(title_text)
        # map each course code to unique identifier
        identifiers = set()
        for code in course_codes:
            if code in course_map:
                identifiers.add(course_map[code])
        # process course description
        descrip_tag = block.find('p', class_ = 'courseblockdesc')
        # combine text and create list
        all_text = title_text + " " + descrip_tag.get_text(strip = True)
        word_list = get_valid_words(all_text)
        # map each word to unique identifier of each course
        for word in word_list:
            if word not in word_to_courses:
                word_to_courses[word] = set()
            word_to_courses[word].update(identifiers)
    return word_to_courses

def go(num_pages_to_crawl, course_map_filename, index_filename):
    '''
    Crawl the college catalog and generates a CSV file with an index.

    Inputs:
        num_pages_to_crawl: the number of pages to process during the crawl
        course_map_filename: the name of a JSON file that contains the mapping
          course codes to course identifiers
        index_filename: the name for the CSV of the index.

    Outputs:
        CSV file of the index index.
    '''

    starting_url = ("http://www.classes.cs.uchicago.edu/archive/2015/winter"
                    "/12200-1/new.collegecatalog.uchicago.edu/index.html")
    limiting_domain = "classes.cs.uchicago.edu"

    # YOUR CODE HERE
    url_queue = queue.Queue()
    visited_urls = set()
    visited_urls.add(starting_url)
    word_course_pair = set()
    i = 1
    # load json formatted course_map into a dictionary
    with open(course_map_filename, 'r') as f:
        course_map = json.load(f)
    # Organize and manage links in a hierarchical structure
    link_hierarchy = {
        1: set(),
        2: set()
        }
    lv1_soup = process_page(starting_url)
    lv1_links = extract_links(lv1_soup, starting_url, limiting_domain)
    link_hierarchy[1].update(lv1_links)
    for url in lv1_links:
        if url not in visited_urls:
            visited_urls.add(url)
            i += 1
            lv2_soup = process_page(url)
            lv2_links = extract_links(lv2_soup, url, limiting_domain)
            for lv2_link in lv2_links:
                url_queue.put(lv2_link)
            link_hierarchy[2].update(lv2_links) # for tracking
    # write csv and track word in the mean time to avoid repetitive loops
    with open(index_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter='|')
        # check each url and scrape if not empty and not reaching the limit
        while not url_queue.empty() and i <= num_pages_to_crawl:
            link = url_queue.get()
            if link in visited_urls:
                continue
            visited_urls.add(link)
            i += 1
            # process page(of the url) into a dictionary of {word: string, courseid:set}
            page = extract_course_info(link, course_map)
            # for every word and courseid, create a unique pair of each and write into csv file
            for word, course_ids in page.items():
                for course_id in course_ids:
                    if (word, course_id) not in word_course_pair:
                        word_course_pair.add((word, course_id))
                        writer.writerow([course_id, word])
        return

if __name__ == "__main__":
    usage = "python3 crawl.py <number of pages to crawl>"
    args_len = len(sys.argv)
    course_map_filename = "course_map.json"
    index_filename = "catalog_index.csv"
    if args_len == 1:
        num_pages_to_crawl = 1000
    elif args_len == 2:
        try:
            num_pages_to_crawl = int(sys.argv[1])
        except ValueError:
            print(usage)
            sys.exit(0)
    else:
        print(usage)
        sys.exit(0)

    go(num_pages_to_crawl, course_map_filename, index_filename)
