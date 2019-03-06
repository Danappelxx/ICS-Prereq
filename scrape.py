from bs4 import BeautifulSoup
import requests
import urllib.parse

class Query(object):
    def as_json(self) -> dict:
        raise NotImplementedError()

class Group(Query):
    def __init__(self, queries: [Query]):
        self.queries = queries

    def __repr__(self):
        return "[ {} ]".format(" AND ".join([repr(s) for s in self.queries]))

    def as_json(self) -> dict:
        return {
            "type": "group",
            "queries": [q.as_json() for q in self.queries]
        }

class Or(Query):
    def __init__(self, left: Query, right: Query):
        self.left = left
        self.right = right

    def __repr__(self):
        return "{} OR {}".format(self.left, self.right)

    def as_json(self) -> dict:
        return {
            "type": "or",
            "queries": [self.left.as_json(), self.right.as_json()]
        }

class Prereq(Query):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return "|{}|".format(self.name)

    def as_json(self) -> dict:
        return {
            "type": "course",
            "name": self.name
        }

class Recommended(Query):
    def __init__(self, course: Prereq):
        self.course = course

    def __repr__(self):
        return "|RECOMMENDED: {}|".format(self.course.name)

    def as_json(self) -> dict:
        return {
            "type": "recommended",
            "course": self.course.as_json()
        }

class Coreq(Query):
    def __init__(self, course: Prereq):
        self.course = course

    def __repr__(self):
        return "|COREQ: {}|".format(self.course.name)

    def as_json(self) -> dict:
        return {
            "type": "coreq",
            "course": self.course.as_json()
        }

class Not(Query):
    def __init__(self, course: Prereq):
        self.course = course

    def __repr__(self):
        return "|NOT: {}|".format(self.course.name)

    def as_json(self) -> dict:
        return {
            "type": "not",
            "course": self.course.as_json()
        }

def normalize(s: str) -> str:
    return " ".join(s.split())

def minify(q: Query) -> Query:
    if type(q) == Group:
        if len(q.queries) == 1:
            return minify(q.queries[0])
    return q

def print_tokens(tokens: [str or [str]], indent=""):
    for token in tokens:
        if type(token) == list:
            print_tokens(token, indent=indent + "  ")
        else:
            print(indent + token)

def tokenize(strings: [str]) -> [str or [str]]:
    index = 0
    tokens = []
    while index in range(len(strings)):
        string = strings[index]

        if string == "(":
            end = index + strings[index:].index(")")
            substrings = strings[index+1:end]
            index = end

            tokens.append(tokenize(substrings))
        elif string == ")":
            assert string != ")"
            continue
        elif "grade = c" in string.lower() or "min " in string:
            pass
        elif "NO REPEATS ALLOWED" in string:
            tokens.pop()
        elif "LOWER DIVISION WRITING" in string:
            tokens.pop()
        else:
            tokens.append(normalize(string))

        index += 1
    return tokens

def parse_prereqs(tokens: [str or [str]]) -> Group:
    index = 0
    query = []
    while index in range(len(tokens)):
        token = tokens[index]

        if type(token) == list:
            query.append(parse_prereqs(token))
        else:
            if token == "AND":
                pass
            elif "recommended" in token:
                last = query.pop()
                assert type(last) == Prereq
                query.append(Recommended(last))
            elif "coreq" in token:
                last = query.pop()
                assert type(last) in (Prereq, Group, Or)
                if type(last) == Prereq:
                    query.append(Coreq(last))
                elif type(last) == Group:
                    assert type(last.queries[-1]) == Prereq
                    last.queries[-1] = Coreq(last.queries[-1])
                    query.append(last)
                elif type(last) == Or:
                    assert type(last.right) == Prereq
                    last.right = Coreq(last.right)
                    query.append(last)
            elif "NO" in token:
                next = tokens[index + 1]
                index += 1
                if type(next) == list:
                    q = parse_prereqs(next)
                else:
                    q = Prereq(next)
                query.append(Not(q))
            elif token == "OR":
                last = query.pop()
                next = tokens[index + 1]
                index += 1
                q = None
                if type(next) == list:
                    q = parse_prereqs(next)
                else:
                    q = Prereq(next)
                query.append(Or(last, q))
            else:
                query.append(Prereq(token))

        index += 1

    return Group(query)

class Course(object):
    def __init__(self, name: str, title: str, prereq_query: Query):
        self.name = name
        self.title = title
        self.prereq_query = prereq_query

    def as_json(self):
        return {
            "name": self.name,
            "title": self.title,
            "prereq_query": self.prereq_query.as_json()
        }

def get_school_courses(school) -> [Course]:
    # "http://catalogue.uci.edu/ribbit/index.cgi?page=getcourse.rjs&code=STATS%207"

    url = "https://www.reg.uci.edu/cob/prrqcgi?dept={}&term=201903&action=view_all#1B".format(urllib.parse.quote(school))
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find_all("table")[5]
    rows = table.find_all("tr")[1:]

    courses = []
    for row in rows:
        course_name_td = row.findChild(attrs="course")
        if course_name_td:
            course_name = normalize(list(course_name_td.stripped_strings)[0])

        course_title_td = row.findChild(attrs="title")
        if course_title_td:
            try:
                course_title = next(course_title_td.stripped_strings)
            except StopIteration:
                print("Course without a title [name: {}]".format(course_name))
                continue

        prereqs_td = row.findChild(attrs="prereq")
        if prereqs_td:
            prereqs = list(prereqs_td.stripped_strings)

        tokens = tokenize(prereqs)
        query = minify(parse_prereqs(tokens))

        # print("{}\t\t{}\t\t{}".format(course_name, course_title, query))
        courses.append(Course(course_name, course_title, query))

    return courses
