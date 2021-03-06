# -*- coding: utf-8 -*-
from flask import Blueprint, request
from comport.decorators import extractor_auth_required
from comport.department.models import Extractor
from comport.data.models import UseOfForceIncident, CitizenComplaint, OfficerInvolvedShooting
from comport.utils import parse_date, parse_int, send_slack_message

from .cleaners import Cleaners

import json
from datetime import datetime


blueprint = Blueprint("data", __name__, url_prefix='/data',
                      static_folder="../static")


@blueprint.route("/heartbeat", methods=['POST'])
@extractor_auth_required()
def heartbeat():
    username = request.authorization.username
    extractor = Extractor.query.filter_by(username=username).first()

    extractor.last_contact = datetime.now()
    extractor.save()

    heartbeat_response = json.dumps({"received": request.json})
    slack_body_lines = []
    extractor_department = extractor.first_department()
    if extractor_department:
        slack_body_lines.append('For: {}'.format(extractor_department.name))
    else:
        slack_body_lines.append('Username: {}'.format(username))

    slack_date_line = 'No extraction start date in reply.'

    if extractor.next_month and extractor.next_year:
        heartbeat_response = json.dumps({"received": request.json, "nextMonth": extractor.next_month, "nextYear": extractor.next_year})
        slack_date_line = 'Replied with extraction start date: {}/{}'.format(extractor.next_month, extractor.next_year)

    slack_body_lines.append(slack_date_line)
    send_slack_message('Comport Pinged by Extractor!', slack_body_lines)

    return heartbeat_response


@blueprint.route("/UOF", methods=['POST'])
@extractor_auth_required()
def use_of_force():
    username = request.authorization.username
    extractor = Extractor.query.filter_by(username=username).first()
    department_id = extractor.first_department().id
    j = request.json
    added_rows = 0
    updated_rows = 0
    cleaner = Cleaners()

    for incident in j['data']:

        # capitalize the location
        incident["division"] = cleaner.capitalize(incident["division"])
        incident["precinct"] = cleaner.capitalize(incident["precinct"])
        incident["shift"] = cleaner.capitalize(incident["shift"])
        incident["beat"] = cleaner.capitalize(incident["beat"])
        # clean force type, race, gender
        incident["officerForceType"] = cleaner.officer_force_type(incident["officerForceType"])
        incident["residentRace"] = cleaner.race(incident["residentRace"])
        incident["residentSex"] = cleaner.sex(incident["residentSex"])
        incident["officerRace"] = cleaner.race(incident["officerRace"])
        incident["officerSex"] = cleaner.sex(incident["officerSex"])
        # make sure values that might've been sent as integers are strings
        incident["residentAge"] = cleaner.number_to_string(incident["residentAge"])
        incident["officerAge"] = cleaner.number_to_string(incident["officerAge"])
        incident["officerYearsOfService"] = cleaner.number_to_string(incident["officerYearsOfService"])

        found_incident = UseOfForceIncident.query.filter_by(
            opaque_id=incident["opaqueId"],
            department_id=department_id,
            officer_identifier=incident["officerIdentifier"],
            officer_force_type=incident["officerForceType"]
        ).first()

        occured_date = parse_date(incident["occuredDate"])

        if not found_incident:
            found_incident = UseOfForceIncident.create(
                department_id=department_id,
                opaque_id=incident["opaqueId"],
                occured_date=occured_date,
                division=incident["division"],
                precinct=incident["precinct"],
                shift=incident["shift"],
                beat=incident["beat"],
                disposition=incident["disposition"],
                census_tract=None,
                officer_force_type=incident["officerForceType"],
                use_of_force_reason=incident["useOfForceReason"],
                service_type=incident["serviceType"],
                arrest_made=incident["arrestMade"],
                arrest_charges=incident["arrestCharges"],
                resident_weapon_used=incident["residentWeaponUsed"],
                resident_injured=incident["residentInjured"],
                resident_hospitalized=incident["residentHospitalized"],
                officer_injured=incident["officerInjured"],
                officer_hospitalized=incident["officerHospitalized"],
                resident_race=incident["residentRace"],
                resident_sex=incident["residentSex"],
                resident_age=incident["residentAge"],
                resident_condition=incident["residentCondition"],
                officer_identifier=incident["officerIdentifier"],
                officer_race=incident["officerRace"],
                officer_sex=incident["officerSex"],
                officer_age=incident["officerAge"],
                officer_years_of_service=incident["officerYearsOfService"],
                officer_condition=incident["officerCondition"]
            )
            added_rows += 1
            continue

        found_incident.department_id = department_id
        found_incident.opaque_id = incident["opaqueId"]
        found_incident.occured_date = occured_date
        found_incident.division = incident["division"]
        found_incident.precinct = incident["precinct"]
        found_incident.shift = incident["shift"]
        found_incident.beat = incident["beat"]
        found_incident.disposition = incident["disposition"]
        found_incident.census_tract = None
        found_incident.officer_force_type = incident["officerForceType"]
        found_incident.use_of_force_reason = incident["useOfForceReason"]
        found_incident.service_type = incident["serviceType"]
        found_incident.arrest_made = incident["arrestMade"]
        found_incident.arrest_charges = incident["arrestCharges"]
        found_incident.resident_weapon_used = incident["residentWeaponUsed"]
        found_incident.resident_injured = incident["residentInjured"]
        found_incident.resident_hospitalized = incident["residentHospitalized"]
        found_incident.officer_injured = incident["officerInjured"]
        found_incident.officer_hospitalized = incident["officerHospitalized"]
        found_incident.resident_race = incident["residentRace"]
        found_incident.resident_sex = incident["residentSex"]
        found_incident.resident_age = incident["residentAge"]
        found_incident.resident_condition = incident["residentCondition"]
        found_incident.officer_identifier = incident["officerIdentifier"]
        found_incident.officer_race = incident["officerRace"]
        found_incident.officer_sex = incident["officerSex"]
        found_incident.officer_age = incident["officerAge"]
        found_incident.officer_years_of_service = incident["officerYearsOfService"]
        found_incident.officer_condition = incident["officerCondition"]
        found_incident.save()
        updated_rows += 1

    extractor.next_month = None
    extractor.next_year = None
    extractor.save()
    return json.dumps({"added": added_rows, "updated": updated_rows})


@blueprint.route("/OIS", methods=['POST'])
@extractor_auth_required()
def officer_involved_shooting():
    username = request.authorization.username
    extractor = Extractor.query.filter_by(username=username).first()
    department_id = extractor.first_department().id
    request_json = request.json
    added_rows = 0
    updated_rows = 0
    cleaner = Cleaners()

    for incident in request_json['data']:

        # capitalize the location
        incident["division"] = cleaner.capitalize(incident["division"])
        incident["precinct"] = cleaner.capitalize(incident["precinct"])
        incident["shift"] = cleaner.capitalize(incident["shift"])
        incident["beat"] = cleaner.capitalize(incident["beat"])
        # clean weapon, race, gender
        incident["residentWeaponUsed"] = cleaner.resident_weapon_used(incident["residentWeaponUsed"])
        incident["residentSex"] = cleaner.sex(incident["residentSex"])
        incident["residentRace"] = cleaner.race(incident["residentRace"])
        incident["officerSex"] = cleaner.sex(incident["officerSex"])
        incident["officerRace"] = cleaner.race(incident["officerRace"])
        # make sure values that might've been sent as integers are strings
        incident["residentAge"] = cleaner.number_to_string(incident["residentAge"])
        incident["officerAge"] = cleaner.number_to_string(incident["officerAge"])
        # and values that might've been sent as strings are integers
        incident["officerYearsOfService"] = cleaner.string_to_integer(incident["officerYearsOfService"])

        found_incident = OfficerInvolvedShooting.query.filter_by(
            opaque_id=incident["opaqueId"],
            department_id=department_id,
            officer_identifier=incident["officerIdentifier"]
        ).first()

        occured_date = parse_date(incident["occuredDate"])

        if not found_incident:
            found_incident = OfficerInvolvedShooting.create(
                department_id=department_id,
                opaque_id=incident["opaqueId"],
                service_type=incident["serviceType"],
                occured_date=occured_date,
                division=incident["division"],
                precinct=incident["precinct"],
                shift=incident["shift"],
                beat=incident["beat"],
                disposition=incident["disposition"],
                resident_race=incident["residentRace"],
                resident_sex=incident["residentSex"],
                resident_age=incident["residentAge"],
                resident_weapon_used=incident["residentWeaponUsed"],
                resident_condition=incident["residentCondition"],
                officer_identifier=incident["officerIdentifier"],
                officer_weapon_used=incident["officerForceType"],
                officer_race=incident["officerRace"],
                officer_sex=incident["officerSex"],
                officer_age=incident["officerAge"],
                officer_years_of_service=parse_int(incident["officerYearsOfService"]),
                officer_condition=incident["officerCondition"],
                census_tract=None
            )
            added_rows += 1
            continue

        found_incident.department_id = department_id
        found_incident.opaque_id = incident["opaqueId"]
        found_incident.service_type = incident["serviceType"]
        found_incident.occured_date = occured_date
        found_incident.division = incident["division"]
        found_incident.precinct = incident["precinct"]
        found_incident.shift = incident["shift"]
        found_incident.beat = incident["beat"]
        found_incident.disposition = incident["disposition"]
        found_incident.resident_race = incident["residentRace"]
        found_incident.resident_sex = incident["residentSex"]
        found_incident.resident_age = incident["residentAge"]
        found_incident.resident_weapon_used = incident["residentWeaponUsed"]
        found_incident.resident_condition = incident["residentCondition"]
        found_incident.officer_identifier = incident["officerIdentifier"]
        found_incident.officer_weapon_used = incident["officerForceType"]
        found_incident.officer_race = incident["officerRace"]
        found_incident.officer_sex = incident["officerSex"]
        found_incident.officer_age = incident["officerAge"]
        found_incident.officer_years_of_service = parse_int(incident["officerYearsOfService"])
        found_incident.officer_condition = incident["officerCondition"]
        found_incident.census_tract = None
        found_incident.save()
        updated_rows += 1

    extractor.next_month = None
    extractor.next_year = None
    extractor.save()
    return json.dumps({"added": added_rows, "updated": updated_rows})


@blueprint.route("/complaints", methods=['POST'])
@extractor_auth_required()
def complaints():
    username = request.authorization.username
    extractor = Extractor.query.filter_by(username=username).first()
    department_id = extractor.first_department().id
    j = request.json
    added_rows = 0
    updated_rows = 0
    cleaner = Cleaners()

    for incident in j['data']:
        # make sure values that might've been sent as integers are strings
        incident["residentAge"] = cleaner.number_to_string(incident["residentAge"])
        incident["officerAge"] = cleaner.number_to_string(incident["officerAge"])
        incident["officerYearsOfService"] = cleaner.number_to_string(incident["officerYearsOfService"])
        # capitalize all the fields in the incident
        incident = cleaner.capitalize_incident(incident)
        # clean sex & race
        incident["residentSex"] = cleaner.sex(incident["residentSex"])
        incident["residentRace"] = cleaner.race(incident["residentRace"])
        incident["officerSex"] = cleaner.sex(incident["officerSex"])
        incident["officerRace"] = cleaner.race(incident["officerRace"])

        found_incident = CitizenComplaint.query.filter_by(
            opaque_id=incident["opaqueId"],
            allegation_type=incident["allegationType"],
            allegation=incident["allegation"],
            officer_identifier=incident["officerIdentifier"],
            department_id=department_id,
            resident_race=incident["residentRace"],
            resident_sex=incident["residentSex"],
            resident_age=incident["residentAge"]
        ).first()

        occured_date = parse_date(incident["occuredDate"])

        if not found_incident:

            multiple_complaintant_check = CitizenComplaint.query.filter_by(
                opaque_id=incident["opaqueId"],
                allegation_type=incident["allegationType"],
                allegation=incident["allegation"],
                officer_identifier=incident["officerIdentifier"],
                department_id=department_id
            ).first()

            if multiple_complaintant_check:
                continue

            found_incident = CitizenComplaint.create(
                department_id=department_id,
                opaque_id=incident["opaqueId"],
                service_type=incident["serviceType"],
                source=incident["source"],
                occured_date=occured_date,
                division=incident["division"],
                precinct=incident["precinct"],
                shift=incident["shift"],
                beat=incident["beat"],
                allegation_type=incident["allegationType"],
                allegation=incident["allegation"],
                disposition=incident["disposition"],
                resident_race=incident["residentRace"],
                resident_sex=incident["residentSex"],
                resident_age=incident["residentAge"],
                officer_identifier=incident["officerIdentifier"],
                officer_race=incident["officerRace"],
                officer_sex=incident["officerSex"],
                officer_age=incident["officerAge"],
                officer_years_of_service=incident["officerYearsOfService"],
                census_tract=None
            )

            added_rows += 1
            continue

        found_incident.department_id = department_id
        found_incident.opaque_id = incident["opaqueId"]
        found_incident.service_type = incident["serviceType"]
        found_incident.source = incident["source"]
        found_incident.occured_date = occured_date
        found_incident.division = incident["division"]
        found_incident.precinct = incident["precinct"]
        found_incident.shift = incident["shift"]
        found_incident.beat = incident["beat"]
        found_incident.allegation_type = incident["allegationType"]
        found_incident.allegation = incident["allegation"]
        found_incident.disposition = incident["disposition"]
        found_incident.resident_race = incident["residentRace"]
        found_incident.resident_sex = incident["residentSex"]
        found_incident.resident_age = incident["residentAge"]
        found_incident.officer_identifier = incident["officerIdentifier"]
        found_incident.officer_race = incident["officerRace"]
        found_incident.officer_sex = incident["officerSex"]
        found_incident.officer_age = incident["officerAge"]
        found_incident.officer_years_of_service = incident["officerYearsOfService"]
        found_incident.census_tract = None
        found_incident.save()
        updated_rows += 1

    extractor.next_month = None
    extractor.next_year = None
    extractor.save()
    return json.dumps({"added": added_rows, "updated": updated_rows})
