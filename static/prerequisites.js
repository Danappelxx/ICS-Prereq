function Query(object) {
    "use strict";
    let self = this;

    self.type = object["type"];

    self.isGroup = self.type == "group";
    self.isOr = self.type == "or";
    self.isPrereq = self.type == "course";
    self.isRecommended = self.type == "recommended";
    self.isCoreq = self.type == "coreq";
    self.isNot = self.type == "not";

    // further properties are initialized through constructQuery()

    self.matches = function(coursesTaken) {
        if (self.isGroup) {
            let matchesAll = true;
            self.queries.forEach((query) => {
                if (!query.matches(coursesTaken))
                    matchesAll = false;
            });
            return matchesAll;
        } else if (self.isOr) {
            return self.left.matches(coursesTaken) || self.right.matches(coursesTaken);
        } else if (self.isPrereq) {
            // TODO: maybe a looser comparison
            return coursesTaken.includes(self.name.toLowerCase());
        } else if (self.isRecommended) {
            return true;
        } else if (self.isCoreq) {
            return true;
        } else if (self.isNot) {
            return !self.course.matches(coursesTaken);
        }
    }
}

function constructQuery(object) {
    "use strict";
    let root = new Query(object);
    if (root.isGroup) {
        root.queries = object["queries"].map(constructQuery);
    } else if (root.isOr) {
        root.left = constructQuery(object["queries"][0]);
        root.right = constructQuery(object["queries"][1]);
    } else if (root.isPrereq) {
        root.name = object["name"];
    } else if (root.isRecommended) {
        root.course = constructQuery(object["course"]);
    } else if (root.isCoreq) {
        root.course = constructQuery(object["course"]);
    } else if (root.isNot) {
        root.course = constructQuery(object["course"]);
    }
    return root;
}

function Course(object) {
    "use strict";
    let self = this;

    self.name = object["name"];
    self.title = object["title"];
    self.queryObject = object["prereq_query"];
    self.query = constructQuery(self.queryObject);

    self.tableRow = function() {
        return [self.name, self.title, `<pre>${queryToString(self.queryObject)}</pre>`];
    }
}

function queryToString(query, indent="") {
    switch (query["type"]) {
        case "group":
            let inner = query["queries"].map((q) => queryToString(q, indent + "  ")).join(`\n${indent}AND\n`);
            return `${indent}(\n${inner}\n${indent})`;
        case "or":
            return indent + queryToString(query["queries"][0]) + " OR " + queryToString(query["queries"][1]);
        case "course":
            return indent + "|" + query["name"] + "|";
        case "recommended":
            return indent + "|RECOMMENDED: " + query["course"]["name"] + "|";
        case "coreq":
            return indent + "|COREQ: " + query["course"]["name"] + "|";
        case "not":
            return indent + "|NOT: " + query["course"]["name"] + "|";
    }
}

function fetchCourses() {
    return $.getJSON("/api/prerequisites")
        .then((data) => data.map((q) => new Course(q)));
}

function makeTable() {
    "use strict";
    return $('#prereq-table').DataTable({
        paging: false,
        scrollY: "450px",
        columnDefs: [
            { width: "10%", targets: 0 },
            { width: "17%", targets: 1 }
        ]
    });
}

function loadTable() {
    fetchCourses().then(function (allCourses) {

        let table = makeTable();

        function displayTable(courses) {
            var data = courses.map((c) => c.tableRow());
            table.clear();
            table.rows.add(data);
            table.draw();
        }

        displayTable(allCourses);

        $("#matches-btn").on("click", function() {
            let coursesTaken = $("#matches-input").val().split(",")
                .map((s) => s.toLowerCase())
                .map((s) => s.trim())
                .map((s) => s.replace(/ics/, "i&c sci"));
            if (coursesTaken == "")
                displayTable(allCourses);
            else {
                let matching = allCourses
                    .filter((course) => !coursesTaken.includes(course.name.toLowerCase()))
                    .filter((course) => course.query.matches(coursesTaken));
                displayTable(matching);
            }
        });
    })
}

$(document).ready(loadTable);
