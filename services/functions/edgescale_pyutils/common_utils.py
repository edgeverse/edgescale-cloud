# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import calendar
import json
import string
from datetime import datetime
import random


def result_wrapper(obj):
    return json.loads(json.dumps(obj))


def rand_generator(size=32, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def _form_warning(msg):
    return {
        'status': 'fail',
        'message': msg
    }


class hashabledict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))


def get_all_timezone():
    alltimezone = {
        "(UTC-12:00)": [
            "Etc/GMT+12"
        ],
        "(UTC-11:00)": [
            "Etc/GMT+11",
            "Pacific/Midway",
            "Pacific/Niue",
            "Pacific/Pago_Pago",
            "Pacific/Samoa",
            "US/Samoa"
        ],
        "(UTC-10:00)": [
            "Etc/GMT+10",
            "HST",
            "Pacific/Honolulu",
            "Pacific/Johnston",
            "Pacific/Rarotonga",
            "Pacific/Tahiti",
            "US/Hawaii"
        ],
        "(UTC-09:30)": [
            "Pacific/Marquesas"
        ],
        "(UTC-09:00)": [
            "America/Adak",
            "America/Atka",
            "Etc/GMT+9",
            "Pacific/Gambier",
            "US/Aleutian"
        ],
        "(UTC-08:00)": [
            "America/Anchorage",
            "America/Juneau",
            "America/Metlakatla",
            "America/Nome",
            "America/Santa_Isabel",
            "America/Sitka",
            "America/Yakutat",
            "Etc/GMT+8",
            "Pacific/Pitcairn",
            "US/Alaska"
        ],
        "(UTC-07:00)": [
            "America/Chihuahua",
            "America/Creston",
            "America/Dawson",
            "America/Dawson_Creek",
            "America/Ensenada",
            "America/Hermosillo",
            "America/Los_Angeles",
            "America/Mazatlan",
            "America/Phoenix",
            "America/Tijuana",
            "America/Vancouver",
            "America/Whitehorse",
            "Canada/Pacific",
            "Canada/Yukon",
            "Etc/GMT+7",
            "MST",
            "Mexico/BajaNorte",
            "Mexico/BajaSur",
            "PST8PDT",
            "US/Arizona",
            "US/Pacific",
            "US/Pacific-New"
        ],
        "(UTC-06:00)": [
            "America/Bahia_Banderas",
            "America/Belize",
            "America/Boise",
            "America/Cambridge_Bay",
            "America/Cancun",
            "America/Costa_Rica",
            "America/Denver",
            "America/Edmonton",
            "America/El_Salvador",
            "America/Guatemala",
            "America/Inuvik",
            "America/Managua",
            "America/Merida",
            "America/Mexico_City",
            "America/Monterrey",
            "America/Ojinaga",
            "America/Regina",
            "America/Shiprock",
            "America/Swift_Current",
            "America/Tegucigalpa",
            "America/Yellowknife",
            "Canada/East-Saskatchewan",
            "Canada/Mountain",
            "Canada/Saskatchewan",
            "Etc/GMT+6",
            "MST7MDT",
            "Mexico/General",
            "Navajo",
            "Pacific/Galapagos",
            "US/Mountain"
        ],
        "(UTC-05:00)": [
            "America/Atikokan",
            "America/Bogota",
            "America/Cayman",
            "America/Chicago",
            "America/Coral_Harbour",
            "America/Guayaquil",
            "America/Indiana/Knox",
            "America/Indiana/Tell_City",
            "America/Jamaica",
            "America/Knox_IN",
            "America/Lima",
            "America/Matamoros",
            "America/Menominee",
            "America/North_Dakota/Beulah",
            "America/North_Dakota/Center",
            "America/North_Dakota/New_Salem",
            "America/Panama",
            "America/Rainy_River",
            "America/Rankin_Inlet",
            "America/Resolute",
            "America/Winnipeg",
            "CST6CDT",
            "Canada/Central",
            "Chile/EasterIsland",
            "EST",
            "Etc/GMT+5",
            "Jamaica",
            "Pacific/Easter",
            "US/Central",
            "US/Indiana-Starke"
        ],
        "(UTC-04:30)": [
            "America/Caracas"
        ],
        "(UTC-04:00)": [
            "America/Anguilla",
            "America/Antigua",
            "America/Aruba",
            "America/Asuncion",
            "America/Barbados",
            "America/Blanc-Sablon",
            "America/Boa_Vista",
            "America/Campo_Grande",
            "America/Cuiaba",
            "America/Curacao",
            "America/Detroit",
            "America/Dominica",
            "America/Eirunepe",
            "America/Fort_Wayne",
            "America/Grand_Turk",
            "America/Grenada",
            "America/Guadeloupe",
            "America/Guyana",
            "America/Havana",
            "America/Indiana/Indianapolis",
            "America/Indiana/Marengo",
            "America/Indiana/Petersburg",
            "America/Indiana/Vevay",
            "America/Indiana/Vincennes",
            "America/Indiana/Winamac",
            "America/Indianapolis",
            "America/Iqaluit",
            "America/Kentucky/Louisville",
            "America/Kentucky/Monticello",
            "America/Kralendijk",
            "America/La_Paz",
            "America/Louisville",
            "America/Lower_Princes",
            "America/Manaus",
            "America/Marigot",
            "America/Martinique",
            "America/Montreal",
            "America/Montserrat",
            "America/Nassau",
            "America/New_York",
            "America/Nipigon",
            "America/Pangnirtung",
            "America/Port-au-Prince",
            "America/Port_of_Spain",
            "America/Porto_Acre",
            "America/Porto_Velho",
            "America/Puerto_Rico",
            "America/Rio_Branco",
            "America/Santo_Domingo",
            "America/St_Barthelemy",
            "America/St_Kitts",
            "America/St_Lucia",
            "America/St_Thomas",
            "America/St_Vincent",
            "America/Thunder_Bay",
            "America/Toronto",
            "America/Tortola",
            "America/Virgin",
            "Brazil/Acre",
            "Brazil/West",
            "Canada/Eastern",
            "Cuba",
            "EST5EDT",
            "Etc/GMT+4",
            "US/East-Indiana",
            "US/Eastern",
            "US/Michigan",
            "posixrules"
        ],
        "(UTC-03:00)": [
            "America/Araguaina",
            "America/Argentina/Buenos_Aires",
            "America/Argentina/Catamarca",
            "America/Argentina/ComodRivadavia",
            "America/Argentina/Cordoba",
            "America/Argentina/Jujuy",
            "America/Argentina/La_Rioja",
            "America/Argentina/Mendoza",
            "America/Argentina/Rio_Gallegos",
            "America/Argentina/Salta",
            "America/Argentina/San_Juan",
            "America/Argentina/San_Luis",
            "America/Argentina/Tucuman",
            "America/Argentina/Ushuaia",
            "America/Bahia",
            "America/Belem",
            "America/Buenos_Aires",
            "America/Catamarca",
            "America/Cayenne",
            "America/Cordoba",
            "America/Fortaleza",
            "America/Glace_Bay",
            "America/Goose_Bay",
            "America/Halifax",
            "America/Jujuy",
            "America/Maceio",
            "America/Mendoza",
            "America/Moncton",
            "America/Montevideo",
            "America/Paramaribo",
            "America/Recife",
            "America/Rosario",
            "America/Santarem",
            "America/Santiago",
            "America/Sao_Paulo",
            "America/Thule",
            "Antarctica/Palmer",
            "Antarctica/Rothera",
            "Atlantic/Bermuda",
            "Atlantic/Stanley",
            "Brazil/East",
            "Canada/Atlantic",
            "Chile/Continental",
            "Etc/GMT+3"
        ],
        "(UTC-02:30)": [
            "America/St_Johns",
            "Canada/Newfoundland"
        ],
        "(UTC-02:00)": [
            "America/Godthab",
            "America/Miquelon",
            "America/Noronha",
            "Atlantic/South_Georgia",
            "Brazil/DeNoronha",
            "Etc/GMT+2"
        ],
        "(UTC-01:00)": [
            "Atlantic/Cape_Verde",
            "Etc/GMT+1"
        ],
        "(UTC+00:00)": [
            "Africa/Abidjan",
            "Africa/Accra",
            "Africa/Bamako",
            "Africa/Banjul",
            "Africa/Bissau",
            "Africa/Casablanca",
            "Africa/Conakry",
            "Africa/Dakar",
            "Africa/El_Aaiun",
            "Africa/Freetown",
            "Africa/Lome",
            "Africa/Monrovia",
            "Africa/Nouakchott",
            "Africa/Ouagadougou",
            "Africa/Sao_Tome",
            "Africa/Timbuktu",
            "America/Danmarkshavn",
            "America/Scoresbysund",
            "Atlantic/Azores",
            "Atlantic/Reykjavik",
            "Atlantic/St_Helena",
            "Etc/GMT",
            "Etc/GMT+0",
            "Etc/GMT-0",
            "Etc/GMT0",
            "Etc/Greenwich",
            "Etc/UCT",
            "Etc/UTC",
            "Etc/Universal",
            "Etc/Zulu",
            "GMT",
            "GMT+0",
            "GMT-0",
            "GMT0",
            "Greenwich",
            "Iceland",
            "UCT",
            "UTC",
            "Universal",
            "Zulu"
        ],
        "(UTC+01:00)": [
            "Africa/Algiers",
            "Africa/Bangui",
            "Africa/Brazzaville",
            "Africa/Douala",
            "Africa/Kinshasa",
            "Africa/Lagos",
            "Africa/Libreville",
            "Africa/Luanda",
            "Africa/Malabo",
            "Africa/Ndjamena",
            "Africa/Niamey",
            "Africa/Porto-Novo",
            "Africa/Tripoli",
            "Africa/Tunis",
            "Atlantic/Canary",
            "Atlantic/Faeroe",
            "Atlantic/Faroe",
            "Atlantic/Madeira",
            "Eire",
            "Etc/GMT-1",
            "Europe/Belfast",
            "Europe/Dublin",
            "Europe/Guernsey",
            "Europe/Isle_of_Man",
            "Europe/Jersey",
            "Europe/Lisbon",
            "Europe/London",
            "GB",
            "GB-Eire",
            "Libya",
            "Portugal",
            "WET"
        ],
        "(UTC+02:00)": [
            "Africa/Blantyre",
            "Africa/Bujumbura",
            "Africa/Cairo",
            "Africa/Ceuta",
            "Africa/Gaborone",
            "Africa/Harare",
            "Africa/Johannesburg",
            "Africa/Kigali",
            "Africa/Lubumbashi",
            "Africa/Lusaka",
            "Africa/Maputo",
            "Africa/Maseru",
            "Africa/Mbabane",
            "Africa/Windhoek",
            "Arctic/Longyearbyen",
            "Asia/Amman",
            "Asia/Damascus",
            "Asia/Gaza",
            "Asia/Hebron",
            "Atlantic/Jan_Mayen",
            "CET",
            "Egypt",
            "Etc/GMT-2",
            "Europe/Amsterdam",
            "Europe/Andorra",
            "Europe/Belgrade",
            "Europe/Berlin",
            "Europe/Bratislava",
            "Europe/Brussels",
            "Europe/Budapest",
            "Europe/Busingen",
            "Europe/Copenhagen",
            "Europe/Gibraltar",
            "Europe/Ljubljana",
            "Europe/Luxembourg",
            "Europe/Madrid",
            "Europe/Malta",
            "Europe/Monaco",
            "Europe/Oslo",
            "Europe/Paris",
            "Europe/Podgorica",
            "Europe/Prague",
            "Europe/Rome",
            "Europe/San_Marino",
            "Europe/Sarajevo",
            "Europe/Skopje",
            "Europe/Stockholm",
            "Europe/Tirane",
            "Europe/Vaduz",
            "Europe/Vatican",
            "Europe/Vienna",
            "Europe/Warsaw",
            "Europe/Zagreb",
            "Europe/Zurich",
            "MET",
            "Poland"
        ],
        "(UTC+03:00)": [
            "Africa/Addis_Ababa",
            "Africa/Asmara",
            "Africa/Asmera",
            "Africa/Dar_es_Salaam",
            "Africa/Djibouti",
            "Africa/Juba",
            "Africa/Kampala",
            "Africa/Khartoum",
            "Africa/Mogadishu",
            "Africa/Nairobi",
            "Antarctica/Syowa",
            "Asia/Aden",
            "Asia/Baghdad",
            "Asia/Bahrain",
            "Asia/Beirut",
            "Asia/Istanbul",
            "Asia/Jerusalem",
            "Asia/Kuwait",
            "Asia/Nicosia",
            "Asia/Qatar",
            "Asia/Riyadh",
            "Asia/Tel_Aviv",
            "EET",
            "Etc/GMT-3",
            "Europe/Athens",
            "Europe/Bucharest",
            "Europe/Chisinau",
            "Europe/Helsinki",
            "Europe/Istanbul",
            "Europe/Kaliningrad",
            "Europe/Kiev",
            "Europe/Mariehamn",
            "Europe/Minsk",
            "Europe/Nicosia",
            "Europe/Riga",
            "Europe/Simferopol",
            "Europe/Sofia",
            "Europe/Tallinn",
            "Europe/Tiraspol",
            "Europe/Uzhgorod",
            "Europe/Vilnius",
            "Europe/Zaporozhye",
            "Indian/Antananarivo",
            "Indian/Comoro",
            "Indian/Mayotte",
            "Israel",
            "Turkey"
        ],
        "(UTC+03:07)": [
            "Asia/Riyadh87",
            "Asia/Riyadh88",
            "Asia/Riyadh89",
            "Mideast/Riyadh87",
            "Mideast/Riyadh88",
            "Mideast/Riyadh89"
        ],
        "(UTC+04:00)": [
            "Asia/Dubai",
            "Asia/Muscat",
            "Asia/Tbilisi",
            "Asia/Yerevan",
            "Etc/GMT-4",
            "Europe/Moscow",
            "Europe/Samara",
            "Europe/Volgograd",
            "Indian/Mahe",
            "Indian/Mauritius",
            "Indian/Reunion",
            "W-SU"
        ],
        "(UTC+04:30)": [
            "Asia/Kabul",
            "Asia/Tehran",
            "Iran"
        ],
        "(UTC+05:00)": [
            "Antarctica/Mawson",
            "Asia/Aqtau",
            "Asia/Aqtobe",
            "Asia/Ashgabat",
            "Asia/Ashkhabad",
            "Asia/Baku",
            "Asia/Dushanbe",
            "Asia/Karachi",
            "Asia/Oral",
            "Asia/Samarkand",
            "Asia/Tashkent",
            "Etc/GMT-5",
            "Indian/Kerguelen",
            "Indian/Maldives"
        ],
        "(UTC+05:30)": [
            "Asia/Calcutta",
            "Asia/Colombo",
            "Asia/Kolkata"
        ],
        "(UTC+05:45)": [
            "Asia/Kathmandu",
            "Asia/Katmandu"
        ],
        "(UTC+06:00)": [
            "Antarctica/Vostok",
            "Asia/Almaty",
            "Asia/Bishkek",
            "Asia/Dacca",
            "Asia/Dhaka",
            "Asia/Qyzylorda",
            "Asia/Thimbu",
            "Asia/Thimphu",
            "Asia/Yekaterinburg",
            "Etc/GMT-6",
            "Indian/Chagos"
        ],
        "(UTC+06:30)": [
            "Asia/Rangoon",
            "Indian/Cocos"
        ],
        "(UTC+07:00)": [
            "Antarctica/Davis",
            "Asia/Bangkok",
            "Asia/Ho_Chi_Minh",
            "Asia/Hovd",
            "Asia/Jakarta",
            "Asia/Novokuznetsk",
            "Asia/Novosibirsk",
            "Asia/Omsk",
            "Asia/Phnom_Penh",
            "Asia/Pontianak",
            "Asia/Saigon",
            "Asia/Vientiane",
            "Etc/GMT-7",
            "Indian/Christmas"
        ],
        "(UTC+08:00)": [
            "Antarctica/Casey",
            "Asia/Brunei",
            "Asia/Choibalsan",
            "Asia/Chongqing",
            "Asia/Chungking",
            "Asia/Harbin",
            "Asia/Hong_Kong",
            "Asia/Kashgar",
            "Asia/Krasnoyarsk",
            "Asia/Kuala_Lumpur",
            "Asia/Kuching",
            "Asia/Macao",
            "Asia/Macau",
            "Asia/Makassar",
            "Asia/Manila",
            "Asia/Shanghai",
            "Asia/Singapore",
            "Asia/Taipei",
            "Asia/Ujung_Pandang",
            "Asia/Ulaanbaatar",
            "Asia/Ulan_Bator",
            "Asia/Urumqi",
            "Australia/Perth",
            "Australia/West",
            "Etc/GMT-8",
            "Hongkong",
            "PRC",
            "ROC",
            "Singapore"
        ],
        "(UTC+08:45)": [
            "Australia/Eucla"
        ],
        "(UTC+09:00)": [
            "Asia/Dili",
            "Asia/Irkutsk",
            "Asia/Jayapura",
            "Asia/Pyongyang",
            "Asia/Seoul",
            "Asia/Tokyo",
            "Etc/GMT-9",
            "Japan",
            "Pacific/Palau",
            "ROK"
        ],
        "(UTC+09:30)": [
            "Australia/Darwin",
            "Australia/North"
        ],
        "(UTC+10:00)": [
            "Antarctica/DumontDUrville",
            "Asia/Khandyga",
            "Asia/Yakutsk",
            "Australia/Brisbane",
            "Australia/Lindeman",
            "Australia/Queensland",
            "Etc/GMT-10",
            "Pacific/Chuuk",
            "Pacific/Guam",
            "Pacific/Port_Moresby",
            "Pacific/Saipan",
            "Pacific/Truk",
            "Pacific/Yap"
        ],
        "(UTC+10:30)": [
            "Australia/Adelaide",
            "Australia/Broken_Hill",
            "Australia/South",
            "Australia/Yancowinna"
        ],
        "(UTC+11:00)": [
            "Antarctica/Macquarie",
            "Asia/Sakhalin",
            "Asia/Ust-Nera",
            "Asia/Vladivostok",
            "Australia/ACT",
            "Australia/Canberra",
            "Australia/Currie",
            "Australia/Hobart",
            "Australia/LHI",
            "Australia/Lord_Howe",
            "Australia/Melbourne",
            "Australia/NSW",
            "Australia/Sydney",
            "Australia/Tasmania",
            "Australia/Victoria",
            "Etc/GMT-11",
            "Pacific/Efate",
            "Pacific/Guadalcanal",
            "Pacific/Kosrae",
            "Pacific/Noumea",
            "Pacific/Pohnpei",
            "Pacific/Ponape"
        ],
        "(UTC+11:30)": [
            "Pacific/Norfolk"
        ],
        "(UTC+12:00)": [
            "Asia/Anadyr",
            "Asia/Kamchatka",
            "Asia/Magadan",
            "Etc/GMT-12",
            "Kwajalein",
            "Pacific/Fiji",
            "Pacific/Funafuti",
            "Pacific/Kwajalein",
            "Pacific/Majuro",
            "Pacific/Nauru",
            "Pacific/Tarawa",
            "Pacific/Wake",
            "Pacific/Wallis"
        ],
        "(UTC+13:00)": [
            "Antarctica/McMurdo",
            "Antarctica/South_Pole",
            "Etc/GMT-13",
            "NZ",
            "Pacific/Auckland",
            "Pacific/Enderbury",
            "Pacific/Fakaofo",
            "Pacific/Tongatapu"
        ],
        "(UTC+13:45)": [
            "NZ-CHAT",
            "Pacific/Chatham"
        ],
        "(UTC+14:00)": [
            "Etc/GMT-14",
            "Pacific/Apia",
            "Pacific/Kiritimati"
        ],
    }

    return alltimezone


def generate_oemid():
    oem_id = random.randint(1, 16777215)
    oem_id = bin(oem_id)[2:]
    oem_id = "0" * (24-len(oem_id)) + oem_id
    return oem_id + "00000000"


def bin_to_hex(oem_id):
    return hex(int(oem_id, 2))


def bool_helper(value):
    if value == 'true' or value is True:
        return True
    else:
        return False


def get_current_utc_timestamp():
    return calendar.timegm(datetime.utcnow().utctimetuple())


def get_utc_timestamp_from_time(time):
    return calendar.timegm(time.utctimetuple())


def strftime(time):
    return datetime.strftime(time, '%Y-%m-%d %H:%M:%S')


def format_time(dt):
    if dt:
        return datetime.strftime(dt, '%Y-%m-%d %H:%M:%S')
    else:
        return None
