var allRows;

function last12Months(rows){
  // offset today by 12 d3-defined months in the past
  var latestDate = d3.max(rows, function(d){ return d.date; })
  var startDate = d3.time.month.offset(latestDate, -12);
  console.log("startDate", startDate);
  return rows.filter(function(r){
    return startDate < r.date;
  });
}

function notEqual(a, b){
  if( a instanceof Date || b instanceof Date ){
    return a.getTime() != b.getTime();
  } else {
    return a != b;
  }
}

function unique(a, b){
  if( a instanceof Array ){
    var s = d3.set(a)
    s.add(b)
    return s.values();
  } else {
    return d3.set([a, b]).values();
  }
}

function allegationReducer(complaint, allegation){
  var newObj = {};
  for (key in complaint){
    if( complaint.hasOwnProperty(key) ){
      var complaintVal = complaint[key];
      var allegationVal = allegation[key];
      if( notEqual(complaintVal, allegationVal) ){
          newObj[key] = unique(complaintVal, allegationVal);
      } else {
        newObj[key] = complaint[key];
      }
    }
  }
  return newObj;
}

function allegationsToComplaints(rows){
  var complaintGrouper = d3.nest()
    .key(function (d){ return d.id; })
    .rollup(function(allegations){
      var complaint = allegations.reduce(allegationReducer);
      complaint['allegations'] = allegations;
      return complaint;
    });
  return complaintGrouper.map(rows, d3.map).values();
}

function uniqueOfficerComplaints(rows){
  var newSet = [];
  var grouper = d3.nest()
    .key(function (d){ return d.officerIdentifier; })
    .key(function (d){ return d.id; });
  var officerComplaintMap = grouper.map(rows, d3.map);
  officerComplaintMap.forEach(function(offId, complaints){
    newSet.push({ 
      officerId: offId,
      complaintCount: complaints.keys().length,
      values: complaints
    });
  });
  return newSet;
}


var raceKey = {
  "Unknown": "Unknown",
  "Black": "Black",
  "": "Unknown",
  "Hispanic": "Hispanic",
  "White": "White",
  "Bi-racial": "Other",
  "White ": "White",
  "black": "Black",
  "B": "Black",
  "Asian": "Asian",
  "Other": "Other",
};

function race(k){
  return function(d){ return raceKey[d[k]]; };
}

function uniqueResidentProxy(d){
   return [ d.residentAge, "year old", d.residentRace, d.residentSex ].join(" ");
}

function uniqueComplaintAboutOfficerByResidentProxy(d){
   return [ 
     d.residentAge, 
     "year old", 
     d.residentRace, 
     d.residentSex,
     "filed",
     d.id,
     "about",
     d.officerIdentifier
       ].join(" ");
}

function raceMatrix(config, data){

  var complaints = d3.nest()
    .key(uniqueComplaintAboutOfficerByResidentProxy)
    .rollup(function (group){
      var obj = {};
      [ 'residentAge', 'residentSex', 'officerAge',
        'officerSex', 'officerYearsOfService',
        ].map(function(k){
          obj[k] = group[0][k];
        });
      [ 'residentRace', 'officerRace',
        ].map(function(k){
          obj[k] = raceKey[group[0][k]];
        });
      obj.allegations = group;
      return obj;
    }).entries(data);

  var totalComplaintCount = complaints.length;
  var counts = d3.nest()
    .key(function(d){
      return d.values.residentRace;
    }).key(function(d){
      return d.values.officerRace;
    }).rollup(function(group){
      return {
        count: group.length,
        percent: ( group.length / totalComplaintCount ),
        complaints: group,
      };
    }).map(complaints, d3.map);

  // get resident race totals
  counts.keys().forEach(function(resRace){
      var total = 0;
      var subgroups = counts.get(resRace);
      subgroups.values().map(function(offRace){ total += offRace.count; });
      subgroups.count = total;
      subgroups.percent = ( total / totalComplaintCount );
    });

  var officerRaceTotals = d3.nest()
    .key(function(d){ return d.values.officerRace; })
    .rollup(function(group){
      return {
        count: group.length,
        percent: ( group.length / totalComplaintCount ),
      };
    }).map(complaints, d3.map);

  counts.officerRaceTotals = officerRaceTotals;
  return counts;
}

function addOtherCategory(dataMap){
  var threshold = .01;
  var small_list = [];
  var total = dataMap.values().map(function (g){
    return g.count;
  }).reduce(function (a,b) {
    return a + b;
  }); 
  var otherTotal = 0;

  dataMap.forEach(function(key, group) {
    if(group.count / total < threshold){
      small_list.push(key);
      otherTotal = otherTotal + group.count;
    }
  });
    
  dataMap.set("Other", {
    count: otherTotal,
    type: "Other",
    groups: small_list,
  });
  
  small_list.forEach(function(key){
    dataMap.remove(key);
  });
}

function officerComplaintsCount(config, data){
  data = uniqueOfficerComplaints(data);
  var counts = d3.nest()
    .key( function (d){
      return d.complaintCount;
    }).rollup( function (values){
      return values.length;
    }).entries(data);
  return counts.map(function(e){
    var obj = {};
    var n = e.key;
    obj['label'] = "Officers with " + ( n > 1 ? n+" complaints" : n+" complaint" );
    obj['count'] = n;
    obj[config.y] = e.values;
    return obj;
  });


}

var experienceBuckets = d3.scale.quantize()
  .domain([2.5, 5.5, 10.5])
  .range([
      '0-2 years',
      '3-5 years',
      '6-10 years',
      '10+ years',
      ]);

var currentYear = 2015;
var defaultNullValue = "NULL";

function translate(x, y){
  return "translate(" + x + "," + y + ")";
}

function mergeMaps(a, b){
  b.forEach(function(k, v){
    a.set(k, v);
  });
}

function nullify(value){
  if (value === defaultNullValue){
    return null;
  } else {
    return value
  }
}

var dateTimeFormat = d3.time.format("%Y-%m-%d %H:%M:%S");
var dateTimeKey = "occuredDate";

function parseDate(dateTimeString){
  return dateTimeString ? dateTimeFormat.parse(dateTimeString) : null;
}

function parseData(rows){
  // parses dates and nulls from the raw csv
  rows.forEach(function(r){
    var dateString = nullify(r[dateTimeKey]);
    r.date = parseDate(dateString);
  });
  rows = rows.filter(function(d){
    return d.date;
  });
  return rows;
}

function drawChart(rows, config){
  // structure data for the particular chart
  if( config.dataFunc ){
    var data = config.dataFunc(config, rows);
  } else {
    var data = structureData(rows, config);
  }

  // get the correct function for drawing this chart
  drawingFunction = drawFuncs[config.chartType];

  // if we have no chart block in the database, just make the brick
  if(config.noTemplate){
    var brick = d3.select('[role=main]')
      .append('div').attr("class", "brick");
    brick.append("h4").attr("class", "brick-title")
      .text(config.title);
    config.parent = brick.append("div").attr("class", config.parent)[0][0];
  }

  // run the function to draw the chart
  drawingFunction(config, data);
}

function addMissingYears(dataMap){
  // add missing years to the map, so we know they are empty
  var year0 = d3.min(dataMap.keys());
  var allYears = d3.range(year0, currentYear);
  allYears.forEach(function(yr){
    if( !dataMap.has(yr) ){
      dataMap.set(
        yr, {
          year: yr,
          count: 0,
          incidents: [],
      });
    }
  });
}

function structureData(parsed_rows, config){
  // restructures csv data into data than can be used to draw a chart

  // filter rows if necessary
  if( config.filter ){
    parsed_rows = config.filter(parsed_rows);
  }

  // create a grouping machine that groups by key function
  var data_grouper = d3.nest()
    .key(config.keyFunc)
    .rollup(function(leaves){
      var datum = {};
      datum[config.y] = config.yFunc(leaves);
      datum[config.x] = config.xFunc(leaves);
      datum['incidents'] = leaves;
      return datum;
    });

  // use the parsed data and the grouping machine to create a
  // simple key value store (aka "map") with years as keys
  var data = data_grouper.map(parsed_rows, d3.map);
  console.log("mapped & filtered data", data);

  if( config.dataMapAdjust ){
    config.dataMapAdjust(data);
  }

  if( config.dontFlatten ){
    return data;
  }

  // return data structured for a chart
  var structured_data = data.values();
  if( config.sortWith ){
    var mapped = structured_data.map(function(d, i){
      return { index: i, value: config.sortWith(d) };
    });
    mapped.sort(function(a,b){
      return +(a.value > b.value) || +(a.value === b.value) - 1;
    });
    structured_data = mapped.map(function(n){
      return structured_data[n.index];
    });
  }
  console.log("structured_data", structured_data);
  return structured_data;
}

drawFuncs = {
  'lineChart': lineChart,
  'map': mapChart,
  'percent': basicPercent,
  'flagHistogram': flagHistogram,
  'matrix': matrixChart,
}
