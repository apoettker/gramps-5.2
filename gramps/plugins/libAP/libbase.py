# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020  Alois Poettker
#
#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import codecs, csv, re, roman, json, os
from collections import defaultdict
# from defaultlist import defaultlist
from io import TextIOWrapper

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.constfunc import win
from gramps.gen.lib import (Date,
                            SrcAttribute, Attribute,
                            Event, EventRef, EventType, EventRoleType,
                            Place, PlaceName,
                            Note, NoteType)

from gramps.gen.display.name import displayer as _nd
from gramps.gen.display.place import displayer as _pd
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.location import get_location_list
from gramps.gen.utils.file import media_path_full

from gramps.plugins.libAP.libnameobject import ordName

#------------------------------------------------------------------------
#
#
#
#------------------------------------------------------------------------
ConnectorWords = ['u.', 'und']
SeparatorWords = ['&', '|', '/']
ChurchNames = ['Dom ', 'Herz ', 'Mariä ', 'Propstei ', 'St. ']

# Substitution system
AKA_NAMETYPE = 'Auch bekannt als'
BAPT_NAMETYPE = 'Taufname'
CALL_NAMETYPE = 'Rufname'
SUBST_NAMETYPE = 'Transkription'

CALLNAME_YEAR_LOW = 1800
CALLNAME_YEAR_HIGH = 1900
FRANCE_YEAR_LOW = 1809
FRANCE_YEAR_HIGH = 1815
WEDDINGNAME_YEAR_LOW = 1794
WEDDINGNAME_YEAR_HIGH = 1945
CIVIL_REGISTRY_YEAR = 1875
BIRTH_PICTURE_YEAR = 1890   # First picture's available

MONTHS_NUM2TXT = {
    0: 'Null',
    1: 'Jan.', 2: 'Feb.', 3: 'Mrz.', 4: 'Apr.', 5: 'Mai', 6: 'Jun.', \
    7: 'Jul.', 8: 'Aug.', 9: 'Sept.', 10: 'Okt.', 11: 'Nov.', 12: 'Dez.'
}

# General methods
def apply_filehead(report, database, pid, basepath, report_type, filetype, fileext, ext=''):
    """"""
    text = ''
    if report == 'A': text = 'Vorfahren'
    elif report == 'P': text = 'Probanden'
    elif report == 'D': text = 'Nachfahren'

    person = database.get_person_from_gramps_id(pid)
    ord_name = ordName(person)
    givenname = '_%s' % ord_name.givenname \
        if not 'NN' in ord_name.givenname else ''

    path_name = basepath + '%s_%s_%s%s%s' % \
        (pid, filetype, ord_name.lastname, givenname, ext)
    if fileext: path_name += '.%s' % fileext

    report_text = '%s der %s von %s %s [%s]' % \
        (report_type, text, ord_name.givenname, ord_name.lastname, pid)
    if fileext != 'js': report_text += '\n\n'

    return path_name, report_text

def determine_birthdate(database, person, options=False):
    """Determines a person's birth date"""
    if not person: return 0, []

    birth = None
    for event_ref in person.get_event_ref_list():
        event = database.get_event_from_handle(event_ref.ref)
        if event and event_ref.role.value == EventRoleType.PRIMARY and \
           (event.type.value == EventType.BIRTH or
            event.type.value == EventType.BAPTISM or
            event.type.value == EventType.CHRISTEN):
            birth = event
            break
    if not birth:
        return 0, []
    if options and options['endnote']:   # correct!
        options['endnote'](birth, False)

    bdate, bcit = 0, []
    if keys_true(options, 'year_only'):
        bdate = birth.get_date_object().get_year()
    else:
        date = birth.get_date_object()
        bdate = '%s.%s.%s' % \
                    (str(date.dateval[0]).zfill(2), str(date.dateval[1]).zfill(2), str(date.dateval[2]).zfill(4))
    if bdate == '': bdate = 0

    for cit_handle in event.citation_list:
        citation = database.get_citation_from_handle(cit_handle)
        bcit.append(citation.gramps_id)

    return bdate, bcit

def find_birthdate(database, person, options=False):
    # Determines a person's birth date

    birth_date = {'event': None, 'date': 0, 'year': 0, 'qual': 0, 'cit': []}
    if not person:
        return birth_date

    event = None
    for event_ref in person.get_event_ref_list():
        event = database.get_event_from_handle(event_ref.ref)
        if event and event_ref.role.value == EventRoleType.PRIMARY and \
           (event.type.value == EventType.BIRTH or
            event.type.value == EventType.CHRISTEN):
            birth_date['event'] = event
            break
    if not birth_date['event']:
        return birth_date

    if options and keys_true(options, 'endnote'):
        options['endnote'](event, False)

    birth_date['year'] = event.get_date_object().get_year()
    if keys_true(options, 'year_only'):
        birth_date['date'] = birth_date['year']
    else:
        date = event.get_date_object()
        birth_date['date'] = '%s. %s %s' % \
                    (str(date.dateval[0]), MONTHS_NUM2TXT[date.dateval[1]], str(date.dateval[2]).zfill(4))

    for cit_handle in event.citation_list:
        citation = database.get_citation_from_handle(cit_handle)
        birth_date['cit'].append(citation.gramps_id)

    return birth_date

def determine_deathdate(database, person, options=False):
    """Determines a person's death date"""
    if not person: return 0, []

    death = None
    for event_ref in person.get_event_ref_list():
        event = database.get_event_from_handle(event_ref.ref)
        if event and event_ref.role.value == EventRoleType.PRIMARY and \
           (event.type.value == EventType.DEATH or
            event.type.value == EventType.BURIAL):
            death = event
            break
    if not death:
        return 0, []

    if options and keys_true(options, 'endnote'):
        options['endnote'](death, False)
    ddate, dcit = 0, []
    if keys_true(options, 'year_only'):
        ddate = death.get_date_object().get_year()
        for cit_handle in event.citation_list:
            citation = database.get_citation_from_handle(cit_handle)
            dcit.append(citation.gramps_id)
    else:
        if probably_alive(person, database): ddate = 'T'
    if ddate == '': ddate = 0

    return ddate, dcit

def find_deathdate(database, person, options=False):
    # Determines a person's death date

    death_date = {'event': None, 'date': 0, 'year': 0, 'qual': 0, 'cit': [], 'cause': ''}
    if not person:
        return death_date

    event = None
    for event_ref in person.get_event_ref_list():
        event = database.get_event_from_handle(event_ref.ref)
        if event and event_ref.role.value == EventRoleType.PRIMARY and \
           (event.type.value == EventType.DEATH or
            event.type.value == EventType.BURIAL):
            death_date['event'] = event
            break
    if not death_date['event']:
        return death_date

    if options and keys_true(options, 'endnote'):
        options['endnote'](event, False)

    death_date['year'] = event.get_date_object().get_year()
    if keys_true(options, 'year_only'):
        death_date['date'] = death_date['year']
    else:
        date = event.get_date_object()
        death_date['date'] = '%s. %s %s' % \
                    (str(date.dateval[0]), MONTHS_NUM2TXT[date.dateval[1]], str(date.dateval[2]).zfill(4))
        if probably_alive(person, database): death_date['date'] = 'T'

    for cit_handle in event.citation_list:
        citation = database.get_citation_from_handle(cit_handle)
        death_date['cit'].append(citation.gramps_id)

    return death_date

def find_specific_event(database, objekt, eventtypelist, eventtypestring='', \
                        descriptionlist=[], roletypelist=[EventRoleType.PRIMARY],
                        mode='S'):   # mode: Single, Multiple
    """Determines a object's specific date"""
    if not objekt: return None, None
    separator = ['-',',','|','&','/']

    event, event_ref = None, None
    for evt_ref in objekt.get_event_ref_list():
        evt = database.get_event_from_handle(evt_ref.ref)
        if evt and evt.type.value in eventtypelist and \
           evt_ref.role.value in roletypelist:
            if evt.type.value == EventType.CUSTOM:
                if evt.type.string != eventtypestring: continue

            if descriptionlist:
                description = evt.description
                for sep in separator:
                    description = description.replace(sep, ' ')
                description_list = description.split()
                if not any(item in descriptionlist for item in description_list): continue

            if mode == 'S':   # Single
                event, event_ref = evt, evt_ref
                break
            if mode == 'M':   # Multiple
                if not event: event = []
                event.append(evt)

    return event, event_ref

def find_reference_object(database, objekt, event_ref,
                          roletypelist=[EventRoleType.PRIMARY],
                          mode='Person'):
    """"""
    # if mode == 'Person': ord_name = ordName(objekt) # Debug!

    # event_role = event_ref.get_role().value
    # event_string = event_ref.get_role().string
    event = database.get_event_from_handle(event_ref.ref)
    # event_value = event.get_type().value
    # event_type = event.get_type().string

    objekt_ref_list = []
    for backlink_handle in database.find_backlink_handles(
        event.handle, include_classes=["Person", "Family"]
    ):
        event_ref_list = None
        # Referenztype Bestimmung
        if backlink_handle[0] == mode and mode == 'Person':   # Person related events
            ref_person = database.get_person_from_handle(backlink_handle[1])
            ref_name = ordName(ref_person) # Debug!
            event_ref_list = ref_person.get_event_ref_list()
        if backlink_handle[0] == mode and mode == 'Family':   # Family related events
            ref_family = database.get_family_from_handle(backlink_handle[1])
            event_ref_list = ref_family.get_event_ref_list()
        if event_ref_list:
            for ref_event in event_ref_list:
                ref_evt = database.get_event_from_handle(ref_event.ref)
                if event.gramps_id == ref_evt.gramps_id:   # The right event?
                    # refevt_role = ref_event.get_role().value
                    refevt_string = ref_event.get_role().string

                    if (objekt.gramps_id != ref_person.gramps_id) and \
                        refevt_string in roletypelist:
                        objekt_ref_list.append(ref_person.handle)

    return objekt_ref_list

def get_gen_str(index_map, relation, handle):
    # index_map: Proband, Ancestor = int, Descendant = str!
    if not handle:
        return ''

    gen_str = ''
    if (relation == 'A'):   # P:roband, A:ncestor
        gen_no = index_map[handle]
        gen_str = '{0:,}'.format(gen_no).replace(',',' ')
    if (relation == 'D'):   # D:escendant
        if index_map[handle].isnumeric():
            gen_no = int(index_map[handle])
            gen_str = '{0:,}'.format(gen_no).replace(',',' ')
        else:
            gen_str = index_map[handle]

    return gen_str

def get_name_from_gramps_id(database, gramps_id):
    """"""
    def compile_name(handle):
        """"""
        person = database.get_person_from_handle(handle)
        firstnames = person.get_primary_name().get_first_name()
        surname = ''
        prefix = ' '.join(person.get_primary_name().get_prefixes())
        if prefix: surname += '%s ' % prefix
        surname += person.get_primary_name().get_primary_surname().surname
        suffix = person.get_primary_name().get_suffix()
        if suffix: surname += ' %s' % suffix

        return person, firstnames, surname

    if gramps_id.startswith('I'):
        person = database.get_person_from_gramps_id(gramps_id)
        if person:
            ord_name = ordName(person)
            return ord_name.lastname, ord_name.shortname

    if gramps_id.startswith('F') or gramps_id.startswith('P') :   # F:amily, P:roperty
        father_firstnames, father_surname, father = '', '', None
        mother_firstnames, mother_surname, mother = '', '', None
        family = database.get_family_from_gramps_id(gramps_id)
        if family:
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            if father_handle:
                father, father_firstnames, father_surname = compile_name(father_handle)
            if mother_handle:
                mother, mother_firstnames, mother_surname = compile_name(mother_handle)

            return [father, father_firstnames, father_surname, mother, mother_firstnames, mother_surname]

    return None

def get_event_place(database, event, long=False):
    """ get the place of the event """
    if not event:
        return '', ''

    place_type, place_text = '', ''
    place_handle = event.get_place_handle()
    if place_handle:
        place = database.get_place_from_handle(place_handle)
        if place:
            place_type = place.place_type.string
            place_text = _pd.display(database, place)

        if long:
            places = get_location_list(database, place, event.get_date_object())
            placenames = [item[0] for item in places]
            if 'Deutschland' in placenames:
                place_type = places[0][1].string
                place_text = placenames[0]

                if len(places) > 1:
                    if place_type in ['Kapelle', 'Kirche', 'Kloster', 'Krankenhaus']:   # Selbst definiert: Kirche, Krankenhaus
                        place_text = '%s, %s' % (placenames[0], placenames[1])

    return place_type, place_text

def create_srcattribute(attr_type, attr_cust='', attr_text=''):
    """ Create an attribute based on Text """
    if not attr_text: return None

    sattr = SrcAttribute()
    if attr_cust: sattr.set_type((attr_type, attr_cust))
    else: sattr.set_type(attr_type)
    sattr.set_value(attr_text)

    return sattr

def create_attribute(attr_type, attr_cust='', attr_text=''):
    """ Creates an attribute base on (Custom-)Type and Text. """
    if not attr_text: return None

    attr = Attribute()
    attr.set_type((attr_type, attr_cust))
    attr.set_value(attr_text)

    return attr

def get_or_create_place(database, namelist, name):
    """
    Finds or creates a Place based on the place name.
    """
    if not name:
        return 'fail', ''

    if name in namelist and namelist[name]:
        state = 'old'
        place = database.get_place_from_handle(namelist[name])
    else:   # create a new Place
        state = 'new'
        place = Place()
        place.set_name(PlaceName(value=name))
        place.set_title(name)

    return state, place

def create_event_and_ref(etype, date=None, place=None, desc=None,
                         citation=None, note=None, attr=None):
    """
    Finds or creates an Event based on the Type, Date, Place, Description,
    Citation, Note and Attribute.
    """
    event = Event()
    event.set_type(EventType(etype))
    event.set_description(desc)

    if date: event.set_date_object(date)
    if place: event.set_place_handle(place.get_handle())

    event_ref = EventRef()

    return event, event_ref

def create_note(note_text, note_type, note_cust=''):
    """ Create an note based on Type and Text. """
    if not note_text:
        return None

    if isinstance(note_text, list):
        note_text = '\n'.join(note_text)

    note = Note()
    note.set(note_text)
    note_type = NoteType()
    note_type.set((note_type, note_cust))

    return note


# ============================================================================ #
class FamilyBase(object):
    """"""
    def __init__(self, database):
        """"""
        self.database = database

    def apply_head(self, family):
        """"""
        family_prefix, father_shortname = [], ''
        father_handle = family.get_father_handle()
        if father_handle:
            father = self.database.get_person_from_handle(father_handle)
            father_name = ordName(father)
            father_shortname = father_name.shortname
            if not family_prefix and father_name.groupname:
                father_lastname = '%s %s' % (father_name.prefix, father_name.lastname) \
                    if father_name.prefix else father_name.lastname
                family_prefix = [father_name.groupname, father_lastname]

        mother_shortname = ''
        mother_handle = family.get_mother_handle()
        if mother_handle:
            mother = self.database.get_person_from_handle(mother_handle)
            mother_name = ordName(mother)
            mother_shortname = mother_name.shortname
            if not family_prefix and mother_name.groupname:
                mother_lastname = '%s %s' % (mother_name.prefix, mother_name.lastname) \
                    if mother_name.prefix else mother_name.lastname
                family_prefix = [mother_name.groupname, mother_lastname]

        return family_prefix, father_shortname, mother_shortname

# ============================================================================ #
class AnalyzeFile(object):
    """"""
    def __init__(self, analyse=None):
        self.enable = False
        self.init(analyse)

    def init(self, analyse):
        if analyse:
            self.enable = keys_true(analyse, 'enable')
            self.file = analyse['file']
            if self.file[-4:] != ".txt": self.file += ".txt"
            self.handle = None
            self.list = []

    def start(self, analyse=None):
        self.init(analyse)
        if self.enable:
            self.handle = open(self.file, 'w')
            self.list = []
            self.handle.write('Start\n\n')

    def stop(self):
        if self.enable:
            for analyze in self.list:
                self.handle.write('%s\n' % analyze)
            self.handle.write('\nStop\n')
            self.handle.close()

    def append(self, string):
        if self.enable:
            self.list.append(string)

# ---------------------------------------------------------------------------- #
# Text to Date system
MONTHES = {
    'jan': 1, 'jan. ': 1,   # de
    'feb': 2, 'febr. ': 2,   # de
    'mrz': 3, 'märz ': 3,   # de
    'apr': 4, 'april ': 4,   # de
    'mai': 5,   # de
    'jun': 6, 'juni ': 6,   # de
    'jul': 7, 'juli ': 7,   # de
    'aug': 8, 'aug. ': 8,   # de
    'sep': 9, 'sept. ': 9,   # de
    'okt': 10, 'okt. ': 10,   # de
    'nov': 11, 'nov. ': 11,   # de
    'dez': 12, 'dez. ': 12   # de
}
MONTHESdot = {
    'jan.': 1,   # de
    'febr.': 2,   # de
    'märz': 3,   # de
    'april': 4,   # de
    'mai': 5,   # de
    'juni': 6,   # de
    'juli': 7,   # de
    'aug.': 8,   # de
    'sept.': 9,   # de
    'okt.': 10,   # de
    'nov.': 11,   # de
    'dez.': 12   # de
}

date_pat0 = re.compile(r'(?P<year>\d{4}) (.|-|=) (?P<month>\d{1,2}) (.|-|=) (?P<day>\d{1,2})',
                         re.VERBOSE)
date_pat1 = re.compile(r'(?P<day>\d{1,2}) (.|-|=) (?P<month>\d{1,2}) (.|-|=) (?P<year>\d{2,4})',
                         re.VERBOSE)
date_pat2 = re.compile(r'(?P<month>\d{1,2}) (.|-|=) (?P<year>\d{4})',
                         re.VERBOSE)
date_pat3 = re.compile(r'(?P<year>\d{3,4})', re.VERBOSE)
date_pat4 = re.compile(r'(v|vor|n|nach|ca|circa|etwa|in|um|±) (\.|\s)* (?P<year>\d{3,4})',
                            re.VERBOSE)
date_pat5 = re.compile(r'(oo|OO) (-|=) (oo|OO) (-|=) (?P<year>\d{2,4})',
                         re.VERBOSE)
date_pat6 = re.compile(r'(?P<month>(%s)) (\.|\s)* (?P<year>\d{3,4})' % \
                         '|'.join(list(MONTHES.keys())),
                         re.VERBOSE | re.IGNORECASE)
# ---------------------------------------------------------------------------- #
def create_date_from_text(date_text, diag_msg=None):
    """
    Finds or creates a Date based on Text, an Offset and a Message.
    """
    # Pro-Gen has a text field for the date.
    # It can be anything (it should be dd-mm-yyyy), but we have seen:
    # yyyy
    # mm-yyyy
    # before yyyy
    # dd=mm-yyyy  (typo I guess)
    # 00-00-yyyy
    # oo-oo-yyyy
    # dd-mm-00 (does this mean we do not know about the year?)

    # Function tries to parse the text and create a proper Gramps Date()
    # object. If all else fails create a MOD_TEXTONLY Date() object.

    dte_txt = date_text == _("Unknown")
    if not (dte_txt or date_text) or date_text == '??':
        return None, 0, 0, 0

    date = Date()
    year, month, day = 0, 0, 0

    # yyyy-mm-dd
    dte_mtch = date_pat0.match(date_text)
    if dte_mtch:
        day = int(dte_mtch.group('day'))
        month = int(dte_mtch.group('month'))
        if month > 12: month %= 12
        year = int(dte_mtch.group('year'))
        if day and month and year:
            date.set_yr_mon_day(year, month, day)
        else:
            date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                     (day, month, year, 0))
        return date, year, month, day

    # dd-mm-yyyy
    dte_mtch = date_pat1.match(date_text)
    if dte_mtch:
        day = int(dte_mtch.group('day'))
        month = int(dte_mtch.group('month'))
        if month > 12: month %= 12
        year = int(dte_mtch.group('year'))
        if day and month and year:
            date.set_yr_mon_day(year, month, day)
        else:
            date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                     (day, month, year, 0))
        return date, year, month, day

    # mm-yyyy
    dte_mtch = date_pat2.match(date_text)
    if dte_mtch:
        month = int(dte_mtch.group('month'))
        year = int(dte_mtch.group('year'))
        date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                 (0, month, year, 0))
        return date, year, month, day

    # yyy or yyyy
    dte_mtch = date_pat3.match(date_text)
    if dte_mtch:
        year = int(dte_mtch.group('year'))
        date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                 (0, 0, year, 0))
        return date, year, month, day

    # before|after|... yyyy
    dte_mtch = date_pat4.match(date_text)
    if dte_mtch:
        year = int(dte_mtch.group('year'))
        if dte_mtch.group(1) == 'v' or dte_mtch.group(1) == 'vor' or \
           dte_mtch.group(1) == 'before' or \
           dte_mtch.group(1) == 'voor' or dte_mtch.group(1) == 'vóór':
            date.set(Date.QUAL_NONE, Date.MOD_BEFORE, Date.CAL_GREGORIAN,
                     (0, 0, year, 0))
        elif dte_mtch.group(1) == 'n' or dte_mtch.group(1) == 'nach' or \
             dte_mtch.group(1) == 'after' or \
             dte_mtch.group(1) == 'na':
            date.set(Date.QUAL_NONE, Date.MOD_AFTER, Date.CAL_GREGORIAN,
                     (0, 0, year, 0))
        else:
            date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                     (0, 0, year, 0))
        return date, year, month, day

    # oo-oo-yyyy
    dte_mtch = date_pat5.match(date_text)
    if dte_mtch:
        year = int(dte_mtch.group('year'))
        date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                 (0, 0, year, 0))
        return date, year, month, day

    # mmm yyyy (textual month)
    dte_mtch = date_pat6.match(date_text)
    if dte_mtch:
        year = int(dte_mtch.group('year'))
        month = MONTHES.get(dte_mtch.group('month'), 0)
        date.set(Date.QUAL_NONE, Date.MOD_ABOUT, Date.CAL_GREGORIAN,
                 (0, month, year, 0))
        return date, year, month, day

    # Hmmm. Just use the plain text.
    date.set_as_text(date_text)

    return date, year, month, day

def get_imagepath(database, person):
    """"""
    path = ''
    for mediaref in person.get_media_list():
        media = database.get_media_from_handle(mediaref.ref)
        pth = media_path_full(database, media.get_path())
        if 'GTSTZ' in media.get_path(): continue
        if 'Shadow' in media.get_path(): continue
        if os.path.isfile(pth):
            path = pth.replace('\\', '/') if win() else pth
            break # first image only

    return path

def get_lineage(database, path, gen_no=0, report='A', prefix='', suffix=''):
    """"""
    index = len(path)

    cnt_actual = 0
    cnt_threshold = 3 if report == 'A' else 2

    line = ''
    for handle in path:
        cnt_actual += 1
        idx = roman.toRoman(index -1).upper() if index > 1 else 0
        person = database.get_person_from_handle(handle)
        ord_name = ordName(person)   # extract the right names
        line += '\\Gen{%s}: %s' % (idx, ord_name.shortname)
        line += ' \\Idt{%s}' % person.gramps_id
        if index > 1:
            line += '\n $\\rightarrow$ '
            if cnt_actual == cnt_threshold:
                line += ' \\\\ '
                cnt_actual = 0

        index -= 1

    lineage = '\n\\Lineage'
    if prefix: lineage += prefix
    if gen_no > 0: lineage += '(%s)' % gen_no
    lineage += '{%s}' % line
    if suffix: lineage += suffix
    lineage += '\n'

    return lineage

def apply_lifeline(database, person, options):
    """Write the period of life as time bar"""

    # Extract Birth/ Death dates
    birth = find_birthdate(database, person, {'year_only': True})
    death = find_deathdate(database, person, {'year_only': True})
    if options['mode'] != 1 and \
       (birth['date'] == 0 and death['date'] == '0'):
        return ''

    if options['mode'] == 0: # LifeLine in DAR / DDR
        line = '\n\\LifeLine'
        if options['rindent']: line += '>40|'
        elif birth['date'] > BIRTH_PICTURE_YEAR: line += '>|'
        if birth['date'] > 0 or death['date'] != '0':
            line += '{%s}{%s}' % (birth['date'], death['date'])

    if options['mode'] == 1: # A-LifeLine in LifeLine
        rom = ReportUtils.roman(options['act_generation'] -1).upper() \
            if options['act_generation'] > 1 else '0'
        line = '%s.' % rom \
            if options['new_generation'] else ' '*(len(rom) +1)

    if options['mode'] == 2: # D-LifeLine in LifeLine
        line = '%s.' % options['index_map'][person.handle] # self.apply_gen_index(person.handle)

    if options['mode'] > 0: # LifeLine in LifeLine | Y/M-Line
        gen_no = options['index_map'][person.handle]
        ord_name = ordName(person, groupas=options['groupname'])
        line += ' & \\textsf(%s). & \\enInd%s & ' % (gen_no, ord_name.linename)
        """
        if birth['date'] > 0 or death['date'] != '0':
            birth['date'], death['date'] = birth['date'], death['date']
            if self.report == 'A':
                if birth['date'] == 0: birth['date'] = '??~~'
                if death['date'] == '0': death['date'] = '??~~'
            line += '(%s \\& -- \\& %s)' % (birth['date'], death['date'])
        else:
            line += '& &'
        line += ' &'
        """
        if birth['date'] > 0 or death['date'] != '0':
            line += '\\LifeLine'
            if options['new_generation']:
                line += '[L0%sab]' % options['act_generation']
            line += '{%s}{%s}' % (birth['date'], death['date'])
        line += ' \\\\'

    line += '\n'

    return line

# ---------------------------------------------------------------------------- #
# List methods
class ListBase(object):
    """"""
    def __init__(self, handle=None):
        """"""
        self.doc_handle = handle

    def apply(self, data_list, indent='', sieve='', compress=None, sort=None, blank=None):
        """"""
        text = ''
        data_list = list(filter(None, data_list))   # Eliminates empty
        if sieve: data_list = [data for data in data_list if not sieve in data] # Eliminates filter
        if compress: data_list = list(set(data_list)) # Eliminates doubles
        if sort: data_list.sort() # Sorts list
        for data in data_list:
            if data:
                text += indent + data.strip() # Eliminates blanks
            text+= blank if blank else '\n'

        return text.rstrip()

    def push(self, text_list, indent=''):
        """"""
        for text_line in text_list:
            if text_line: self.doc_handle.write(indent + text_line)

    def write(self, data_list, indent='', compress=None, sort=None, blank=None):
        """"""
        line = self.apply(data_list, indent, '', compress, sort, blank)
        if line:
            self.doc_handle.write(line)
            self.doc_handle.write('\n')

# ---------------------------------------------------------------------------- #
# JSON data dicts methods
class JSONdata(object):

    def __init__ (self, source=''):
        """"""
        self.datadict = source if source else defaultdict(list)

    def read_datadict(self, file_name):
        """"""
        file_name += '.js' if 'js' not  in file_name else ''
        with open(file_name, 'r') as file_handle:
            self.datadict = json.load(file_handle)

        {setattr(self, key, value) for (key, value) in self.datadict.items()}

        return self.datadict

    def write_datadict(self, file_name):
        """"""
        file_name = file_name.split('.js')[0] + '.js'
        with open(file_name, 'w') as file_handle:
            file_handle.write(json.dumps(self.datadict, indent=2))

    def asdict(self):
        return self.datadict


# ============================================================================ #
# Python data dicts methods
def replace_all(text, dic):
    """"""
    if not text: return

    for i, j in dic.items():
        text = text.replace(i, j)

    return text

def get_by_value(nested_dict, value):
    """"""
    for k, v in nested_dict.items():
        if k == value:
            return v
        elif isinstance(v, dict):
            return get_by_value(v, value)
        elif isinstance(v, list):
            for i in v:
                if isinstance(i, dict):
                    return get_by_value(i, value)

def keys_exists(element, *keys):
    # Check if *keys (nested) exists in 'element' (dict).
    if not (isinstance(element, dict) or isinstance(element, list) or isinstance(element, tuple)):
        raise AttributeError('keys_exists() expects dict / list / tuple as first argument.')
    if len(keys) == 0:
        raise AttributeError('keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False

    return True

def keys_true(element, *keys):
    # Check if *keys (nested) exists and are True in 'element' (dict).
    key_list = []
    for key in keys:
        key_list.extend(list(key)) if isinstance(key, tuple) else key_list.append(key)

    _element = element
    for key in key_list:
        try:
            _element = _element[key]
        except KeyError:
            return False

    if _element:
        if isinstance(_element, (bool, int, str, list)): return True
        elif element[key]: return True
    else: return False

def keys_false(element, *keys):
    # Check if *keys (nested) exists and are False in 'element' (dict).
    key_list = []
    for key in keys:
        key_list.extend(list(key)) if isinstance(key, tuple) else key_list.append(key)

    _element = element
    for key in key_list:
        try:
            _element = _element[key]
        except KeyError:
            return True

    if _element:
        if isinstance(_element, (bool, int, str, list)): return False
        elif element[key]: return False
    else: return True

def open_file(filename, extension):
    """Function synonym to import data in 'extension' format."""
    try:
        if filename[-3:] != extension:
            filename += "." + extension
        with open(filename, 'rb') as filehandle:
            line = filehandle.read(3)
            if line == codecs.BOM_UTF8:
                filehandle.seek(0)
                filehandle = TextIOWrapper(filehandle, encoding='utf_8_sig',
                                           errors='replace', newline='')
            else:   # just open with OS encoding
                filehandle.seek(0)
                filehandle = TextIOWrapper(filehandle,
                                           errors='replace', newline='')
            msg = _("Reading: file %(filename)s.") % \
                {'filename': filename}
            print(msg)

            data = {}
            if extension == 'csv':
                data = [[r.strip().replace('"', '') for r in row] \
                            for row in csv.reader(filehandle)]

            return data

    except EnvironmentError as err:
        msg = _("\n%s could not be opened\n") % filename, str(err)
        print(msg)

        return None

def merge_dicts(a_dict, b_dict):
    """"""
    result_dict = a_dict
    for key, value in b_dict.items():
        if isinstance(value, dict):
            for k, v in  value.items():
                if isinstance(v, dict):
                    for K, V in value.items():
                        if isinstance(V, dict):
                            for k, v in value.items():
                                result_dict[key][K][k] = v
                        else:
                            result_dict[key][k] = v

                else:
                    result_dict[key][k] = v
        else:
            result_dict[key] = value
    return result_dict

def replace_all(text, dic, end=False):
    """"""
    if not text: return

    for i, j in dic.items():
        if end and text.endswith(i):
            text = text.rsplit(i, 1)[0].strip()
        else:
            text = text.replace(i, j)

    return text

def add_to_list(item_object):
    """"""
    item_list = []
    if item_object:
        if isinstance(item_object, str):   # String ?
            item_list = item_object.split(', ') if ', ' in item_object else [item_object]   # String with commas?
        else: item_list = item_object  # Flat list!
    return item_list

"""
elif any(isinstance(item, list) for item in item_object):   # Nested lists?
    item_list = [item for sublist in item_object for item in sublist]
"""