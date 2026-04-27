#
# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#

"""Reports/Text Reports/Elements"""

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import collections, math, os, operator, re

from collections import defaultdict

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
# from datetime import datetime

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
# from gramps.gen.config import config
# from gramps.gen.errors import ReportError
from gramps.gen.lib import NameType, FamilyRelType, Person, EventType, EventRef, \
     EventRoleType, NoteType, MediaRef, Citation, PlaceType

import gramps.plugins.lib.libgedcom as libgedcom

from gramps.gen.utils.alive import probably_alive
# from gramps.gen.utils.db import find_children, find_parents, find_witnessed_people
# from gramps.gen.utils.file import media_path_full
#from gramps.gen.utils.string import conf_strings
from gramps.gen.utils.location import get_location_list, get_main_location

from gramps.gen.display.name import displayer as global_name_display

# from gramps.gen.plug.report import endnotes
# from gramps.gen.plug.report import Report #, Bibliography
# from gramps.gen.plug.report import Citation as sortCitation
from gramps.gen.plug.report import utils as ReportUtils

from gramps.plugins.lib.libnarrate import Narrator

from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libobjects import *
from gramps.plugins.libAP.libnameobject import ordName, NameList

#------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------
BIRTH_PICTURE = 1890   # First picture's available
PREFIXES = ['i', 'o', 'c', 'b', 'm', 'd', 'e', 'r'] # In, Out, Church, Born, Marriage, Death, Embedded, Reference

ALTERNATE = ['CUST','AKA','BRTHN','MARN','ADPT','UNKWN','CHRN','CALL']
DEPENDENT = ['None', 'Zwilling', 'Pate', 'Vertretung', 'Zeuge', 'Helfer', 'Geistlicher']
ADJACENT = ['auf', 'der', 'van', 'von', 'zu']

class TextReport (object):
    """
    ReportElements is a class which provides elements for text reports.
    """

    def __init__ (self, bibliography, database, options):
        """
        Initialize the textreport elements class.
        """
        self.bibliography = bibliography
        self.database = database
        self.base = options.base
        self.include = options.include

        self.handle_map = options.handle_map
        self.index_map = options.index_map
        self.line_map = options.line_map
        self.path_map = options.path_map
        self.gen_keys = options.gen_keys

        self.list_base = ListBase()
        self.family_base = FamilyBase(database)

        self.report = 'A' if options.base['report'] == 'Ancestors' else 'D'
        self.pid = self.base['pid']
        self.max_generation = self.base['max_generation']
        self.doc_handle = None
        self.doc_file = '%s%s_Gen1.tex' % (self.base['result_path'], self.pid)

        self.owner_country = 'DE'   # database.get_researcher().get_country()
        self.center_person = database.get_person_from_gramps_id(self.pid)
        """
        self._name_display = copy.deepcopy (global_name_display)
        name_format = options.menu.get_option_by_name("name_format")
        name_value = name_format.get_value() if name_format else 0
        if name_value != 0:   # name_value
            self._name_display.set_default_format(2)   # 2: First Name, Last name
        """
        self.shortname, self.familyname = '', ''

        self._local_init_ ()
        self.numbers_printed = []

        return

    def _local_init_(self):
        """"""
        self.mode = {'part': 'P',   # P-erson, R-eference
                     'object': ''   # P-erson, F-amily, C-hild, s-ub-C-hild
                    }
        self.line_indent = ''
        self.min_generation, self.act_generation = 0, 0

        # Event-Citation liste
        self.event_citlist = []

        # Items: Anzahl, Identifier, Name(n), Index, Zitat(e), Notiz(en)
        # 0: Custom, 1: Also know as, 2: Birth name, 3: Married name, 4: Adopted name, 5: Unknown
        self.altname = NameList(ALTERNATE)
        self.dependent = NameList(DEPENDENT)

        # Schattenbilder
        self.passport = None
        self.shadow_pics = None
        self.shadow_female = self.database.get_person_from_gramps_id('I99997')
        self.shadow_male = self.database.get_person_from_gramps_id('I99998')
        if self.shadow_male and self.shadow_female:
            self.shadow_pics = (self.shadow_female.media_list[0], \
                                self.shadow_male.media_list[0])

        self.kid_report = False
        self.kid_counter = 0
        self.regular_map = {}
        self.embedded_map = defaultdict(list)

        # Nebenregister (Referezierte Personen, Mehrere Heiraten)
        self.relatives_map = {}   # Relative Map (= Father & Mother)
        self.ref = {'part': 0,
                    'tag': '',
                    'format': '',
                    'famind': [],   # Family Index
                    'evtlist': [],   # Event-List
                    'idmap': {}   # Gramps-Id dictionary
                   }

    # General methods
    def apply_divider(self, zeichen, ende='', zahl=75):

        divider=zeichen*zahl
        self.doc_handle.write('%% %s %%%s' % (divider, ende))

    def apply_language(self, person, lang):
        """"""
        self._locale = self.set_locale(lang)
        self.narrator._translate_text = self._locale.translation.gettext
        self.narrator._get_date = self._locale.get_date
        self.narrator._locale = self._locale
        self.narrator.set_subject(person)

    narr_dict = {
        '-': '--',
        'amvor': 'vor',
        'am etwa': 'etwa',
        'am vor': 'vor',
        'amnach': 'nach',
        'am nach': 'nach',
        'von mehr als etwa': 'von etwa',
        'von um': 'von',
        'am geschätzt': 'geschätzt am',

        'N.N. N.N..': '\\NN',
        'N.N. N.N.': '\\NN',
        'N.N.': '\\NN',
        'Unknown#': '\\NN',
        '..': '.',
        '(: ': '(',
        '.#.': '.#',
        '----': '--',

        'Jahre': 'Jahren',
        'Monate': 'Monaten',
        'Tage': 'Tagen'
    }
    def replace_narrative_text(self, text, month=True):
        """"""
        # Fehler im Gramps Textgenerierungsystem
        text = replace_all(text, self.narr_dict)
        if month: text = replace_all(text, MONTHS_DICT)

        return text

    def split_text_citation(self, narrator_text):
        """"""
        nar_text, cit_text = '', ''
        if '<super>' in narrator_text:
            nar_list = narrator_text.split('<super>')
            nar_text = '%s.' %  nar_list[0]
            cit_text = nar_list[1].replace('</super>', '')
            cit_text = cit_text.replace('.', '')
        else:
            nar_text = narrator_text

        return nar_text.strip(), cit_text.strip()

    def check_elements_count(self, handle):
        """"""
        elements = 2

        person = self.database.get_person_from_handle(handle)
        if not self.include['common']['private'] and person.private: return 0

        if len(person.get_event_ref_list()) > 0:
            spec_events = self.find_specific_eventrole(person, ['Pate',  'Zeuge'])
            if len(spec_events) == 1: elements -= 1
            if len(spec_events) > 1: elements -= 2

        if len(person.get_alternate_names()) > 0:
            spec_names = self.find_specific_nametype(person, [ALTERNATE.index('CALL'), ALTERNATE.index('MARN')])
            if len(spec_names) > 0: elements -= 1
        """
        if len(person.get_attribute_list()) > 0:
            elements -= 1

        if len(person.get_note_list()) > 0:
            elements -= 1

        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self.database.get_family_from_handle(family_handle)
            if not self.include['common']['private'] and family.private:
                return elements

            events = family.get_event_ref_list()
            if events: elements += 32
            attributes = family.get_attribute_list()
            if attributes: elements += 64
            notes = family.get_note_list()
            if notes: elements += 128
        """
        if elements < 0: elements = 0

        return elements

    def apply_list(self, data_list, indent='', sieve='', compress=None, sort=None, blank=None):
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

    def push_list(self, text_list, indent=''):
        """"""
        for text_line in text_list:
            if text_line: self.doc_handle.write(indent + text_line)

    def write_list(self, data_list, indent='', compress=None, sort=None, blank=None):
        """"""
        line = self.apply_list(data_list, indent, '', compress, sort, blank)
        if line:
            self.doc_handle.write(line)
            self.doc_handle.write('\n')

    # Index methods
    def apply_ident(self, ident, bold=False):
        """Write the ident to the sub- resp. superposition"""

        line = ' \\Idt'
        if bold: line += '[B]'
        line += '{%s}' % ident

        return line

    def apply_gen_index(self, handle):
        # index_map: DAR = int, DDR = str!
        if not handle: return ''

        if (self.report == 'A'):
            gen_no = self.index_map[handle]
            gen_str = '{0:,}'.format(gen_no).replace(',',' ')
        else:   # (self.report == 'P', 'D')
            if self.index_map[handle].isnumeric():
                gen_no = int(self.index_map[handle])
                gen_str = '{0:,}'.format(gen_no).replace(',',' ')
            else:
                gen_str = self.index_map[handle]

        return gen_str

    def apply_ind_index(self, prefix, gennr, firstattr, firstnames, \
                        lastattr, lastprefix, groupname, lastname, identnr, pageattr='', \
                        ref=False, dubref=False):
        """Applies a individual index to repository"""

        line = '\\'
        if prefix: line += '%s' % prefix
        line += 'Ind'

        if gennr: line += '[%s]' % gennr

        if firstattr: line += '[\\%s]' % firstattr
        firstnames = firstnames.replace('N.N.', '\\NN')
        line += '{%s}' % firstnames

        if lastattr: line += '[\\%s]' % lastattr
        lastname = lastname.replace('N.N.', '\\NN')
        if lastprefix:
            prefix = '%s ' % lastprefix
            lastname = lastname.replace(prefix, '')
            line += '+%s+' % lastprefix
        line += '{%s!%s}' % (groupname, lastname) \
            if groupname else '{%s}' % lastname

        if identnr: line += '[%s]' % identnr
        if not ref:
            if pageattr: line += '[%s]' % pageattr
        else:
            if dubref:
                if pageattr: line += '[see%s{%s}]' % (pageattr, ref)
            else:
                line += '[see{%s}]' % ref

        return line

    def apply_nind_index(self, prefix, givenname, firstnames, lastprefix, lastname, identnr):
        """Applies a normal embedded individual index to repository"""

        line = '\\'
        if prefix: line += '%s' % prefix
        line += 'Ind'

        firstnames = firstnames.replace('N.N.', '\\NN')
        if givenname in firstnames:
            tmp_list = firstnames.split(givenname)
        if tmp_list[0]: line += '[%s]' % tmp_list[0].strip()
        line += '{%s}' % givenname
        if len(tmp_list) > 1 and tmp_list[1]:
            line += '[%s]' % tmp_list[1].strip()
        if lastprefix: line += '+%s+' % lastprefix
        lastname = lastname.replace('N.N.', '\\NN')
        line += '{%s}' % lastname
        if identnr: line += '[%s]' % identnr

        return line

    def apply_ind_list(self, index_list, indent=''):
        """"""
        line = '%s' % indent
        for i, txt in enumerate(index_list):
            if ((i > 0) and (i % 2 == 0)) or \
               ((len(line) + len(txt)) >100):
                line += '\n%s%s ' % (indent, txt)
            else:
                line += '%s ' % txt

        return line.rstrip()

    def apply_fam_index(self, prefix, ident, sortprefix, spouse1, spouse2, pageattr=''):
        """Write a family index to repository"""

        if spouse1 == '\\NN' and spouse2 == '\\NN':
            return ''

        line = '\\'
        if prefix: line += '%s' % prefix
        line += 'Fam'

        sortname = spouse1
        if sortprefix:
            prefix = '%s ' % sortprefix
            sortname = spouse1.replace(prefix, '')
        first = sortname.split(' ', 1)[0]
        if (' ' in sortname):
            last = sortname.split(' ', 1)[1]
            line += '{%s, %s}' % (last, first)
        else:
            line += '{%s}' % (first)
        if spouse1 == '': spouse1 = '\\NN'
        spouse1 = spouse1.replace('N.N.', '\\NN')
        if spouse2 == '': spouse2 = '\\NN'
        spouse2 = spouse2.replace('N.N.', '\\NN')
        line += '{%s}{%s}' % (spouse1, spouse2)

        if ident:  line += '[%s]' % ident
        if pageattr:
            line += '[%s]' % pageattr
        line += '\n'

        return line.rstrip()

    def apply_loc_index(self, prefix, plctype, country, place, locality):
        """Write a location index to repository"""

        if not place:
            return None, None

        if country == 'Belgien': cntry = 'BE'
        elif country == 'Niederlande': cntry = 'NL'
        else: cntry = ''

        loc, loc_list = '', []
        if locality: loc += '{%s!%s}' % (place, locality)
        else: loc += '{%s}' % place

        ind_loc, emb_loc = '\\', '\\'
        if prefix:
            ind_loc += prefix
            emb_loc += prefix
        ind_loc += 'Loc'
        emb_loc += 'LocChr' if plctype == 'Kirche' else 'Loc'
        if cntry: emb_loc += '>\\Loc%s<' % cntry
        if self.ref['part'] and ('!' in loc):
            ind_loc += '!r!'
            emb_loc += '!r!'
        if plctype in ['Friedhof']:
            loc = '{%s!%s}' % (place.split()[1], place.split()[0])

        if locality:
            if plctype not in ['Krankenhaus', 'Kirche', 'Gebäude'] and \
               locality not in ['Harrenstätte', 'Spahn']:   # selbst definiert
                ref_loc = '\\rLoc{%s}[see{%s--%s}]' % (locality, place, locality)
                loc_list.append(ref_loc.strip())

        ind_loc += loc
        emb_loc += loc
        loc_list.append(ind_loc.strip())

        return loc_list, emb_loc

    def apply_dse_index(self, prefix, disease):
        """Write a disease index to repository"""

        if not disease: return None

        line = '\\Dse{%s}' % disease

        diseases = []
        diseases.append(line.strip())

        return diseases

    # Name methods
    def find_specific_nametype(self, objekt, nametype_list):
        """"""
        name_list = []

        for name in objekt.get_alternate_names():
            type_value = name.type.value
            type_string = name.type.string
            if type_value == 0:
                if type_string == 'Adaption': type_value = 4
                if type_string == 'Taufname': type_value = 6
                if type_string == 'Rufname': type_value = 7
            if type_value not in nametype_list:
                name_list.append(name)

        return name_list

    def compile_name_primary(self, person):
        """
        List the primary name for the given person
        """
        prim_name = person.get_primary_name()
        __ = self.add_citations(prim_name, False)

    def find_name_alternate(self, person):
        """
        List the alternative names for the given person
        """
        altname = NameList(ALTERNATE)

        ord_name = ordName(person)
        for alt_name in person.get_alternate_names():
            if not self.include['common']['private'] and alt_name.private: continue
            if not alt_name.surname_list: continue

            altname.counter += 1
            alt_type = alt_name.get_type().value
            alt_string = alt_name.get_type().string
            if alt_type == -1: alt_type = 5
            if alt_type > 5: alt_type = 5
            if alt_string == 'Adaption': alt_type = 4
            if alt_string == 'Taufname': alt_type = 6
            if alt_string == 'Rufname': alt_type = 7
            if alt_string == 'Name bei der Hochzeit': alt_type = 1   # = AKA

            altname.reg[alt_type][1] = ALTERNATE[alt_type]
            if alt_type == 0:   # 0: Custom Name
                altname.reg[alt_type][1] = alt_string

            idx, nte = '', ''
            txt = alt_name.get_regular_name()
            txt = txt.replace('N.N.', '\\NN')
            # 0:Custom, # 1:Also Known As, 2:Birth Name, 3:Married Name, 5: Unknown
            if alt_type in [0, 1, 2, 3, 5, 6, 7]:
                # __, f_name, sur_prefix, sur_name = self.apply_name(alt_name)
                first_names = alt_name.get_first_name()
                sur_prefix = alt_name.surname_list[0].prefix
                sur_name = alt_name.get_name().split(',', 1)[0]
                group_name = alt_name.group_as

                ref_name = ord_name.firstnames \
                    if sur_name == ord_name.surname \
                    else ord_name.shortname

                prefix = self.ref['format'] if self.ref['format'] else ''
                if alt_type in [0, 1, 2, 5, 6, 7]:   # Apply Index
                    idx = self.apply_ind_index(prefix,  '', '', \
                        first_names, '', sur_prefix, group_name, sur_name, person.gramps_id, '', ref_name, \
                        False) # reference
                if alt_type == 3:   # Apply Index
                    idx = self.apply_ind_index(prefix, '', '', \
                        first_names, '', sur_prefix, group_name, sur_name, person.gramps_id, 'It', ord_name.shortname, \
                        True) # double reference
            else:
                pass

            cit = self.add_citations(alt_name, False)

            if self.include['common']['notes']:
                # Type 23: Report Text (used for Notes etc.)
                nte = apply_note(self.database, alt_name.get_note_list(), 23, \
                    private=self.include['common']['private'])

            altname.reg[alt_type][0] += 1
            if txt: altname.reg[alt_type][2].append(txt)
            if idx: altname.reg[alt_type][3].append(idx)
            if cit: altname.reg[alt_type][4].append(cit)
            if nte: altname.reg[alt_type][5].append(nte)

        return altname

    def apply_name_alternate(self, altname, alttype, indent=''):
        """"""
        name_text, cit_text, index_text = '', '', ''
        if altname.reg[alttype][0] > 0:
            con = '+\\DoT+' if alttype in [1, 3] else ' \\& '   # Connector
            ind = '' if alttype in [0, 1, 2, 5, 6, 7] else '  '   # Indention

            # 1: AKA, 5: Unknown Name
            if alttype in [1, 5] or \
               alttype in [2, 6, 7] and self.ref['part'] == 3:
                if self.mode['part'] in ['P', 'R']:   # P-erson, R-eference
                    name_text += '\\indNameType'
                elif self.mode['part'] == 'K':   # Mode: K-id
                    name_text += '\\kidNameType'
                elif self.mode['part'] == 'sC':   # s-ub-C-ild
                    name_text += '\\colNameType'

                if self.ref['part']: name_text += '!R!'   # Mode: Reference
                if self.ref['part'] and alttype == 2:   # 2: Birth Name
                    name_text += '|%s|' % altname.reg[alttype][1][:4]
                else:
                    name_text += '|%s|' % altname.reg[alttype][1]
                name_text += self.apply_name_list(altname.reg[alttype][2], con)   # Text
                pass
            elif alttype in [2, 6, 7]:   # 2: Birth, 6: Christen, 7: Call Name
                if self.mode['part'] == 'P':   # P-erson
                    name_text += '\\textsb{'
                if self.mode['part'] == 'sC':   # s-ub-C-ild
                    name_text += '\\colNameType!S!|%s|' % altname.reg[alttype][1]
                name_text += self.apply_name_list(altname.reg[alttype][2])   # Text
                if self.mode['part'] == 'P':   # P-erson
                    name_text += '}'
            elif alttype == 3:   # 3: Married Name
                if self.mode['part'] == 'K':   # Mode: K-id
                    name_text += '\\kidNameType|%s|' % altname.reg[alttype][1]
                elif self.mode['part'] == 'sC':   # s-ub-C-ild
                    name_text += '\\colNameType!S!|%s|' % altname.reg[alttype][1]
                else:
                    name_text += '  \\Evt{gen%s}' % altname.reg[alttype][1]
                name_text += self.apply_name_list(altname.reg[alttype][2], con)   # Text
            else:
                name_text += '  \\Evt{gen%s}' % altname.reg[alttype][1]
                name_text += self.apply_name_list(altname.reg[alttype][2], con)   # Text

            if altname.reg[alttype][4]:   # Citations
                cit_text += '%s' % self.apply_citation_text(altname.reg[alttype][4], True)

            if altname.reg[alttype][3]:   # Indexes
                idx_text = self.apply_ind_list(altname.reg[alttype][3], ind)
                if idx_text: index_text += '%s%s%s' % (self.line_indent, indent, idx_text)

            if altname.reg[alttype][5]:   # Notes
                for nte_text in altname.reg[alttype][5]:
                    index_text += '\n%s%s%s%s' % (self.line_indent, indent, ind, nte_text)

            if not altname.debug:
                altname.reg[alttype][0] = 0
                altname.reg[alttype][2], altname.reg[alttype][3] = [], []

        return name_text, cit_text, index_text

    def apply_name_list(self, name_list, con_word=''):
        """"""
        name_text = '{'
        for i, nme_txt in enumerate(name_list):
            name_text += nme_txt
            if (con_word != '') and (i < len(name_list) -1):
                if i == 0 and 'DoT' in con_word: name_text += '}'
                name_text += con_word
                if 'DoT' in  con_word: name_text += '['
        name_text += '}' if ('DoT' not in con_word) or len(name_list) == 1 else ']'

        return name_text

    # Media methods
    def apply_passport(self, person):
        """Writes a portrait picture"""

        if self.act_generation -1 > self.include['person']['passport_generation']:
            return None

        ord_name = ordName(person)   # Extract the right names

        passport, passport_text = None, ''
        media_list = person.get_media_list()
        if len(media_list) > 0:
            passport = media_list[0]
        elif not self.ref['part'] and \
             self.shadow_pics and \
             self.birth > BIRTH_PICTURE:
            passport = self.shadow_pics[person.gender]

        if passport and not passport.private:
            media = self.database.get_media_from_handle(passport.ref)
            if not ord_name.shortname:
                ord_name.shortname = media.desc

            # Compose alt string for insert_passport
            name_year = re.sub('[ ]', '|', ord_name.shortname)
            year = media.get_date_object().get_year()
            if year != 0:
                name_year += '|' + str(year)

            gender = 'U'
            if person.gender == 0: gender = 'F'
            elif person.gender == 1: gender = 'M'

            citation_text = self.add_citations(passport, False)

            outfile = os.path.splitext(media.path)[0]
            if name_year:
                pictname = re.sub('\\|', ' ', name_year)
            else:
                pictname = latexescape(os.path.split(outfile)[1])

            passport_text = '%s\\passPicture{%s}{%s}' % (self.line_indent, pictname, gender)
            if citation_text: passport_text += '!\\Cit{%s}!' % citation_text
            passport_text += '%s\n  {%s}\n' % (self.line_indent, outfile)

        return passport_text

    def apply_media (self, media_ref, citation=True, notes=True):
        """"""
        media_ref_handle = media_ref.get_reference_handle()
        media_object = self.database.get_media_from_handle(media_ref_handle)
        mime_type = media_object.get_mime_type()
        year = media_object.get_date_object().get_year()
        month = media_object.get_date_object().get_month()

        outfile = ''
        if mime_type and mime_type.startswith("image"):
            # infile = media_path_full(database, media_object.get_path())   # Absolute path
            outfile = media_object.get_path()   # Relative path

        citation_text = ''
        if citation:
            citation_text = self.add_citations(media_ref, False)
            if not citation_text:
                citation_text = self.add_citations(media_object, False)
            citation_list = media_object.get_citation_list()

        note_text = ''
        if notes:
            note_list = media_ref.get_note_list()
            if not note_list:
                note_list = media_object.get_note_list()
            media_note = apply_note(self.database, note_list, 17, \
                private=self.include['common']['private'])   # Type 17: Media
            if media_note:
                media_note = media_note.replace(u' - ', u' -- ')
                note_list = media_note.splitlines()
                note_text = '%%\n%%  [(%s' % note_list[0]
                for nte in note_list[1:]:
                    note_text += '\\\\\n%%  %s' % nte

        return outfile, month, year, citation_text, note_text

    def apply_nme_media(self, filename):
        """ Greps object name out of filename """

        obj_type, obj_name = '', ''
        if filename:
            # print('>%s<' % file_name)
            if filename[1] == ':': filename = filename[4:]
            obj_type = filename.split('/')[0]
            # obj_name = file_name.split('/')[3] if 'xxx' in file_name else file_name.split('/')[2]
            obj_name = filename.rsplit('/')[-1]
            obj_name = obj_name.split(' ')[1]

            if obj_name == 'EP': obj_name = 'Ehepaar'
            elif obj_name == 'TB': obj_name = 'Totenbrief'
            elif obj_name == 'TA': obj_name = 'Todesanzeige'
            elif obj_name == 'TZ': obj_name = 'Totenzettel'
            elif obj_name == 'DS': obj_name = 'Danksagung'

        return obj_type, obj_name

    def apply_evt_media(self, event):
        """ Applies personal related media"""

        media_list = event.get_media_list()
        if len(media_list) == 0:
            return ''

        pic1 = media_list[1]  if len(media_list) == 2 else None
        for pic_nr, pic in enumerate(media_list):

            # Administer Citation
            media_text = ''
            if self.include['common']['sources']:
                media_text = '\n%\\cit'
                if pic1: media_text += 'two'
                media_text += 'Picture'
                cit_text = self.add_citations(pic, False)
                media_text += '{%s}' % cit_text if cit_text else '{}'
                if pic1:
                    cit_text = self.add_citations(pic1, False)
                    media_text += '{%s}' % cit_text if cit_text else '{}'
                media_text += '\n'

            pic0_file, pic0_month, pic0_year, __, __ = self.apply_media(pic, False, False)
            if pic1:
                pic1_file, pic1_month, pic1_year, __, __ = self.apply_media(pic1, False, False)

            obj_type, obj_name = self.apply_nme_media(pic0_file)
            self_name = '???'
            if obj_type == 'IND': self_name = self.shortname
            if obj_type == 'FAM': self_name = self.familyname

            event_type = event.get_type()
            # Type 13: Death, 19: Burial, 22: Christening, 23: Confirmation
            if event_type in (13, 19, 22, 23):
                media_text += '%\\two' if pic1 else '%\\one'
                media_text += 'sub'
            else:
                media_text += '%\\std'

            media_text += 'Picture\n%' + '  {%s}\n' % pic0_file
            if pic1:
                media_text += '%' + '  {%s}\n' % pic1_file
            media_text += '%  {}{66 mm}'
            media_text += '{%s}[%s]' % (obj_name, self_name)
            month = MONTHS_SHORT[pic0_month -1] + ' ' if pic0_month > 0 else ''
            media_text += '{%s%s}\n\n' %  (month, pic0_year)

            if pic1 and pic_nr == 0:   # Stop if exact two pictures shown
                break

        return media_text

    def apply_media_list(self, medialist, destination, citation=True):
        if not medialist: return ''

        media_text = ''
        for media_ref in medialist:
            media_file, media_month, media_year, citation_text, note_text = \
                self.apply_media(media_ref, citation)

            if media_file:
                if media_text: media_text += '\n'
                if self.include['common']['sources'] and citation:
                    media_text += '%\\citPicture{'
                    if citation_text: media_text += citation_text
                    media_text += '}\n'

                self_name = ''
                obj_type, obj_name = self.apply_nme_media(media_file)
                if obj_type == 'IND': self_name = self.shortname
                elif obj_type == 'FAM': self_name = self.familyname
                elif obj_type == 'SOU':
                    if destination == 'I': self_name = self.shortname
                    elif destination == 'F': self_name = self.familyname

                media_text += '%\\stdPicture\n'
                media_text += '%' + '  {%s}\n' % media_file
                media_text += '%  {}{80 mm}'
                media_text += '{%s}' % obj_name
                if self_name: media_text += '[%s]' % self_name
                month = MONTHS_SHORT[media_month -1] + ' ' if media_month > 0 else ''
                media_text += '{%s%s}' %  (month, media_year)
                if media_text: media_text = media_text.replace(u'etwa', u'(etwa)')

                if self.include['common']['notes']:
                    media_text += note_text
                media_text += '\n'

        return media_text

    # Place methods
    def apply_embedded_place(self, prefix, text, objekt, eventtype, eventrole=EventRoleType.PRIMARY):
        """"""
        if not text:
            return None, None, None

        text, pcitation = self.split_text_citation(text)
        ptext = self.replace_narrative_text(text)
        plocation_list = ''

        # pevent = self.apply_defined_event(objekt, event_type, event_role)
        pevent, __ = find_specific_event(self.database, objekt, [eventtype], \
                                    roletypelist=[eventrole])
        if pevent:
            self.add_citations(pevent, False)   # Eintrag in die Citationsliste
            ptype, __, pcountry, pplace, plocality, __ = self.apply_event_place(pevent)
            ploc_list, ploc = self.apply_loc_index(prefix, ptype, pcountry, pplace, plocality)

            if ploc_list and len(ploc_list) > 1:
                plocation_list = ploc_list[1]
            if ploc:
                if plocality:
                    if pplace in ptext and plocality in ptext:
                        ptmp = plocality + ', ' + pplace
                        # ptext = ptext.replace(' in ', ' im ')
                        ptext = ptext.replace(ptmp, ploc)
                    if pplace in ptext and not plocality in ptext:
                        ptext = ptext.replace(pplace, ploc)
                    if not pplace in ptext and plocality in ptext:
                        ptext = ptext.replace(plocality, ploc)
                else:
                    if pplace in ptext:
                        ptext = ptext.replace(pplace, ploc)

        return ptext, pcitation, plocation_list

    # Lineage (anchestor, descendand) methods
    def apply_path(self, gen_no, person):
        if self.report == 'P':
            return None

        path = []
        if self.report == 'A':
            for handle in self.path_map[gen_no][1]:
                person = self.database.get_person_from_handle(handle)
                if person: path.append(person.get_handle())

        if self.report == 'D':
            for gen in range(0, self.act_generation):    # person changes in the loop
                desc_family_handle = person.get_main_parents_family_handle()
                if desc_family_handle:
                    person = None
                    family = self.database.get_family_from_handle(desc_family_handle)
                    mother_handle = family.get_mother_handle()
                    father_handle = family.get_father_handle()
                    if mother_handle and mother_handle in self.index_map:
                        person = self.database.get_person_from_handle(mother_handle)
                    elif father_handle and father_handle in self.index_map:
                        person = self.database.get_person_from_handle(father_handle)
                    if person: path.append(person.get_handle())
                    else: break

        lineage = get_lineage(self.database, path, gen_no, self.report) if path else None

        return lineage

    def apply_pathNG(self, gen_no, person):
        """"""
        # Erfordert Neuberechnung bei jedem TeX-Lauf!
        if self.report == 'D' and self.act_generation > 0:
            return '\\LineageNG{}\n'

    # Notes methods
    def write_note(self, notelist, notetype, embedded=True):
        """ Writes the notes"""
        note_text = ''
        if self.include['common']['notes']:
            note_text = apply_note(self.database, notelist, notetype, \
                private=self.include['common']['private'], embedded=embedded)
            if note_text: self.doc_handle.write(note_text)

        return note_text

    # Event methods
    def get_event_abbr(self, event_type):
        """Converts event type to genealogic GEDCOM abbreviation"""

        # Person
        if 'Personenstand' in event_type: abbr = 'PERS'
        elif 'Zwilling' in event_type: abbr = 'TWIN'
        elif 'Adoption' in event_type: abbr = 'ADOP'
        # Religious
        elif 'Taufe' in event_type: abbr = 'CHR'
        elif 'Kleinkindtaufe' in event_type: abbr = 'CHR'
        elif 'Firmung' in event_type: abbr = 'CONF'
        elif 'Pate' in event_type: abbr = 'GODX'
        elif 'TaufpateVon' in event_type: abbr = 'GODFo'
        elif 'TaufpatinVon' in event_type:
            abbr = 'GODMo'
        elif 'Geistlicher' in event_type: abbr = 'CLER'
        elif 'Clerky' in event_type: abbr = 'CLER'
        elif 'Helfer' in event_type: abbr = 'HELP'
        elif 'Beerdigung' in event_type: abbr = 'burial'
        # Family
        elif 'Familienstand' in event_type: abbr = 'FAMS'
        elif 'SohnVon' in event_type: abbr = 'CHLDMo'
        elif 'TochterVon' in event_type: abbr = 'CHLDFo'
        elif event_type == 'Hochzeit': abbr = 'MARR'
        elif event_type == 'HochzeitMit': abbr = 'MARRw'
        elif event_type == 'Trauung': abbr = 'WITT'
        elif event_type == 'TrauungMit': abbr = 'WITTw'
        # Pruefungen der event_type Länge nach
        elif event_type == 'IndTrauzeuge': abbr = 'WITM' # Trauzeuge
        elif event_type == 'IndTrauzeugin': abbr = 'WITF' # Trauzeugin
        elif 'IndTrauzeugen' in event_type: abbr = 'WITX' # Trauzeugen
        elif 'IndTrauzeugeVon' in event_type:
            abbr = 'WITMo' # Personal witness ref.
        elif 'IndTrauzeuginVon' in event_type: abbr = 'WITFo' # Personal witness ref.
        elif 'FamTrauzeugen' in event_type: abbr = 'WITX' # Witness family
        elif 'FamTrauzeugenVon' in event_type: abbr = 'WITXo' # Family witness ref.
        elif 'HelferBei' in event_type: abbr = 'HELP' # Wedding helper ref.
        elif 'Zeuge' in event_type: abbr = 'WITx'
        # Travel
        elif 'AuswanderungMit' in event_type: abbr = 'EMMIw'
        elif 'Rückwanderung' in event_type: abbr = 'REMI'
        # Misc
        elif 'BerufMit' in event_type: abbr = 'OCCUw'
        elif 'BesitzMit' in event_type: abbr = 'PROPw'
        elif 'Ehrenamt' in event_type: abbr = 'HONR'
        elif 'Nennung' in event_type: abbr = 'MENT'
        elif 'NennungMit' in event_type: abbr = 'MENTw'
        elif 'Passion' in event_type: abbr = 'PASS'
        elif 'Wohnort' in event_type: abbr = 'RESI'
        elif 'Unknown' in event_type: abbr = 'UNKWN'
        elif 'Cause Of Death' in event_type: abbr = 'CAUS'
        else:
            abbr = '%s' % event_type

        return abbr

    def get_event_type(self, event_ref):
        "Checks referenced event types"

        event = self.database.get_event_from_handle(event_ref)
        event_type = event.get_type()
        # Check for personal GEDCOM event types
        evt_abbr = libgedcom.PERSONALCONSTANTEVENTS.get(int(event_type), '').strip()
        evt_abbr = evt_abbr.replace(u'_', u'')
        if not evt_abbr:
            # Check for familiar GEDCOM event types
            evt_abbr = libgedcom.FAMILYCONSTANTEVENTS.get(int(event_type), '').strip()
            evt_abbr = evt_abbr.replace(u'_', u'')
        if not evt_abbr:
            # Additional (non GEDCOM) declared event types
            event_type = self._get_type(event.get_type())
            evt_abbr = self.get_event_abbr(event_type)

        return event, evt_abbr

    def get_event_religion(self, description):
        "Gets event religion"

        if description == '':
            return '', ''

        if description == 'Evangelisch-Uniert':
            return 'ev.--uni.', 'e.u.'
        elif description == 'Evangelisch-Lutherisch':
            return 'ev.--luth.', 'e.l.'
        elif description == 'Römisch-Katholisch':
            return 'röm.--kath.', 'r.k.'
        else:
            return '????', '??'

    def apply_event_place(self, event):
        """"""
        if not event:
            return '', '', '', '', '', ''

        umlaut = {   # FIXME: Only German Umlauts
            ord(u'Ä'): u'Ae', ord(u'ä'): u'ae',
            ord(u'Ö'): u'Oe', ord(u'ö'): u'oe',
            ord(u'Ü'): u'Ue', ord(u'ü'): u'ue',
            ord(u'ß'): u'ss',
         }

        place_handle = None
        place_type, label, country, place, locality, house = '', '', '', '', '', ''
        if event:
            place_handle = event.get_place_handle()
            if place_handle:
                # lang = config.get('preferences.place-lang')
                location = self.database.get_place_from_handle(place_handle)
                if (self.include['common']['private'] and location.private):
                    return '', '', '', '', ''

                places = get_location_list(self.database, location, event.get_date_object())
                placenames = [item[0] for item in places]
                country = ''.join(item[0] for item in places if item[1].value == 1)

                # PlaceType 0: Custom, 4: City, 6: Locality
                placetypeno = int(places[0][1])
                place_type = places[0][1].string
                label, place = placenames[0], placenames[0]

                if len(places) > 1:
                    if placetypeno == PlaceType.LOCALITY:
                        place, locality = placenames[1], placenames[0]
                    if placetypeno == PlaceType.BUILDING or \
                       place_type in ['Krankenhaus'] or \
                       place_type in ['Kirche']:   # Selbst definiert: Krankenhaus, Kirche
                        place, locality = placenames[1], placenames[0]
                        house = '%s!%s' % (placenames[1], placenames[0])

        if label: label = label.replace(u'-', u'--')
        if place: place = place.replace(u'-', u'--')
        if locality: locality = locality.replace(u'-', u'--')

        return place_type, label, country, place, locality, house

    def find_specific_eventrole(self, objekt, roletype_list):
        """"""
        event_list = []

        for evt_ref in objekt.get_event_ref_list():
            event = self.database.get_event_from_handle(evt_ref.ref)
            if event and evt_ref.role.string not in roletype_list:
                event_list.append(event)

        return event_list

    def apply_defined_event(self, entity, event_type, event_role):
        """"""
        event = []
        for evt_ref in entity.get_event_ref_list():
            evt = self.database.get_event_from_handle(evt_ref.ref)
            evt_type = evt.type.value
            evt_role = evt_ref.role
            if evt and evt.type.value == event_type \
               and evt_ref.role.value == event_role:
                event.append(evt)
                self.add_citations(evt, False)   # Eintrag in die Citationsliste
        return event

    def apply_dependend_event(self, ref_type):
        """"""
        evt_text = ''

        if self.dependent.reg[ref_type][0] > 0:
            evt_text = '%s  \\Evt[R]' % self.line_indent
            evt_text += '{gen%s}' % self.get_event_abbr(self.dependent.reg[ref_type][1])
            evt_text += '%s<0>\n' % self.apply_name_list(self.dependent.reg[ref_type][2], ' & ')
            ind_txt = self.apply_ind_list(self.dependent.reg[ref_type][3], '  ')
            if ind_txt: evt_text += '%s\n' % ind_txt

            if not self.dependent.debug:
                self.dependent.reg[ref_type][0] = 0
                self.dependent.reg[ref_type][2], self.dependent.reg[ref_type][3] = [], []

        return evt_text

    def apply_referenced_event(self, event_ref, event_abbr=None):
        """"""
        if not event_ref:
            return 0, '', '', '', ''

        prefix = 'r'
        if event_abbr in ['burial', 'genMENT', 'genMENTw', 'OCCU', 'OCCUw', 'RESI', 'RESIw']: prefix = 'e'
        if event_abbr in ['MARR', 'MARRw', 'WITT', 'WITTw', \
                          'WITMo', 'WITFo', 'WITX', 'WITXo']: prefix = 'em'

        evt_dte, evt_id, evt_text, cit_text, nte_text = '', '', '', '', ''
        evt_id, evt_dte, __, __, evt_srel, evt_txt, __, cit_text = \
            self.apply_event(event_ref, prefix)
        if evt_txt:
            evt_text += '%s(' % self.line_indent
            if event_abbr in ['CHR', 'GODFo', 'GODMo']: evt_text += '\\bapt'
            if event_abbr in ['CHLDF', 'CHLDM', 'CHLDFo', 'CHLDMo', 'MARR', 'MARRw',\
                              'WITT', 'WITTw', 'WITMo', 'WITFo', 'WITX', 'WITXo']:
                evt_text += '\\marr'
            if event_abbr in ['burial']: evt_text += '\\buri'
            if evt_srel: evt_text += '[%s]' % evt_srel
            if len(evt_text) > 1: evt_text += ' '
            evt_text += '%s)' % evt_txt

        if cit_text:
            cit_text = self.apply_citation_text(cit_text.split(','))

        if self.include['common']['notes']:
            evt = self.database.get_event_from_handle(event_ref)
            if evt:
                nte_list = evt.get_note_list()
                nte_text = apply_note(self.database, nte_list, 11, \
                    private=self.include['common']['private'])  # 11: Eventref

        return evt_dte, evt_id, evt_text, cit_text, nte_text

    def apply_event(self, event_ref, prefix='e'):
        """"""
        event, evt_abbr = self.get_event_type(event_ref)
        if self.ref['part'] and evt_abbr in ['MARR', 'WITT']:   # Debug
            a = 1

        if not self.include['common']['private'] and event.private:
            return 0, None, None, None, None, None, None, None

        evt_id = event.gramps_id   # fuer Referenz-Personen
        evt_lrel, evt_srel, evt_text, label_text, desc_text = '', '', '', '', ''
        if self.base['full_dates']:
            date = self._get_date(event.get_date_object())
            a = 1
        else:
            date = event.get_date_object().get_year()
        date = replace_all(date, MONTHS_DICT)

        evt_date = event.get_date_object().get_year() *10000 + \
            event.get_date_object().get_month() *100 + \
            event.get_date_object().get_day()
        if evt_date == 0: evt_date = 99999999
        if evt_abbr in ['MARR', 'WITT', 'WITTw']:
            evt_date += 1

        if 'RELI' in evt_abbr or 'CAUS' in evt_abbr: date = ''
        if date:
            evt_text += self._('%(date)s') % {'date' : date}
            evt_text = evt_text.replace('geschätzt', '$\\approx$')

        if evt_abbr == 'BIRT': prefix = 'eb'
        elif evt_abbr in ['CHR', 'HONR']: prefix = 'e'
        elif evt_abbr in ['FAMS', 'MENT', 'OCCUw', 'RESIw']: prefix = 'e'
        elif evt_abbr == 'DEAT': prefix = 'ed'
        elif evt_abbr in ['MARR', 'WITT', 'WITTw']: prefix = 'em'
        plc_type, label, country, place, locality, house = self.apply_event_place(event)
        loc_list, emb_loc = self.apply_loc_index(prefix, plc_type, country, place, locality)
        if emb_loc: label_text = emb_loc   # Keine Referencen verwenden!

        desc = event.get_description()   # Beschreibung
        if desc:
            desc_text = desc.replace(u'-', u'--')
            if 'DEAT' in evt_abbr: desc_text = '\\eDse{%s}' % desc
            elif 'CAUS' in evt_abbr: desc_text = '\\eDse{%s}' % desc
            elif 'PERS' in evt_abbr: desc_text = '\\ePst{%s}' % desc
            elif 'PROP' in evt_abbr: desc_text = '\\ePst{%s}' % desc
            elif 'EDUC' in evt_abbr: desc_text = '\\eOcc{%s}' % desc
            elif 'OCCU' in evt_abbr:
                if '|' in desc:   # Mehrsprachige Berufsbeschreibung
                    dsc = desc.split('|')
                    desc_text = '\\eOccT>NL<[%s]{%s}' % (dsc[0].strip(), dsc[1].strip())
                else:
                    desc_text = '\\eOcc{%s}' % desc
            else:
                pass

        desc_flag = False
        if plc_type in ['Stadt', 'Dorf', 'Lokalität', 'Gebäude']:
            if 'CHR' in evt_abbr: desc_flag = True   #  and ('St.' in desc or 'Kirche' in desc)
            elif 'FCOM' in evt_abbr: desc_flag = True
            # elif ('MARR' in evt_abbr) and ('Civil' not in desc): desc_flag = True
            else:
                pass

            if desc_flag:  # Old style
                evt_text += ', ' if evt_text else ''
                evt_text += '\\%sLocChr{%s!%s}' % (prefix, label, desc)
            else:
                if label_text:
                    evt_text += ', ' if evt_text else ''
                    evt_text += label_text
                if desc_text:
                    evt_text += '. ' if evt_text else ''
                    evt_text += desc_text

        elif plc_type == 'Kirche':
            evt_text += ', ' if evt_text else ''

            if desc:
                if desc not in ['Pfarrer', 'Küster']:
                    evt_lrel, evt_srel = self.get_event_religion(desc)   # Religion (Lang-, Kurzform)
                else:
                    evt_text += '%s ' % desc

            ref_ptr = '!r!' if self.ref['part'] and ('!' in house) else ''
            evt_text += '\\%sLocChr%s{%s}' % (prefix, ref_ptr, house)

            pass
        else:   # plc_type in ['Unbekannt']
            if label_text:
                evt_text += ', ' if evt_text else ''
                evt_text += label_text
            if desc_text:
                if desc_text == 'Civil':
                    evt_srel, evt_lrel = 'Civ.', 'Civil'
                else:
                    evt_text += '. ' if evt_text else ''
                    evt_text += desc_text
            pass

        cit, cit_text = True, ''
        if 'RELI' in evt_abbr:   # Geteilte Religionsereignisse haben viele! Referenzen
            cit = len(event.get_citation_list()) < 2
        if cit: cit_text = self.add_citations(event, False)

        attr_text = ''
        if self.include['common']['attributes']:
            attr_list = event.get_attribute_list()
            # attr_lst.extend(event_ref.get_attribute_list())  # FIXME
            if attr_list:
                attr_dict = self.apply_attribut(attr_list, ['e']) # e-mbedded
                for attr in attr_dict:
                    if 'text' in attr: evt_text += attr_dict['text']
                    if 'TeX' in attr:
                        attr_text += attr_dict['TeX']

        return evt_id, evt_date, evt_abbr, evt_lrel, evt_srel, evt_text, attr_text, cit_text

    def apply_total_event(self, event_ref, event_role=None):
        """"""
        event_text, note_text, media_text = '', '', ''
        evt_id, event_dte, event_abbr, evt_lrel, evt_srel, evt_text, attr_text, cit_text = \
            self.apply_event(event_ref.ref)

        if self.ref['part']:
            if (self.ref['tag'] == 'Kirchenamt') and \
               (event_abbr in  ['CHR', 'MARR', 'WITMv', 'WITFv', 'WITX', 'WITXv', 'burial']) and \
               (evt_id not in self.ref['evtlist']):
                return 0, '', '', '', ''

        if evt_text:
            event_text += '  \\Evt'
            if evt_lrel or evt_srel:   # Religion
                event_text += ('+%s+' % evt_lrel) \
                    if not self.ref['part'] else ('+%s+' % evt_srel)

                # ersetze 'Hochzeit' durch 'Trauung'
                if 'MARR' in event_abbr:
                    event_abbr = 'WITT'
            if event_abbr in ['RELI', 'CAUS']:
                event_text += '[R]'   # Einrueckoption für LaTeX
            event_text += '{gen%s}' % event_abbr
            if event_role: event_text += '(%s)' % event_role

            # Ereignis ID mitprotokollieren für Referenz-Abschnitt
            if evt_id and event_abbr in ['BAPT', 'CHR', 'MARR', 'WITT', 'burial']:
                event_text += '|%s|' % evt_id
                self.ref['evtlist'].append(evt_id)

            event_text += '{%s' % evt_text

            alt_nme, alt_cit, alt_ind = '', '', ''
            alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 2)   # 2: Geburtsname
            if alt_nme:
                if self.ref['part']: event_text += ','
                event_text += ' als %s' % alt_nme
            if alt_cit:
                cit_text = ', %s' % alt_cit if cit_text else alt_cit
                self.event_citlist.extend(alt_cit.split(',')) # Collect Eventcitations / Person

            if event_abbr in ['CHR']:
                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 6)   # 6: Taufname
                if alt_nme:
                    if self.ref['part']: event_text += ','
                    event_text += ' als %s' % alt_nme
                if alt_cit:
                    cit_text = ', %s' % alt_cit if cit_text else alt_cit
                    self.event_citlist.extend(alt_cit.split(',')) # Collect Eventcitations / Person

            event_text += '}'   # Abschluß der Event-Zeile

            if cit_text:
                # [self.event_citlist.append(cit) for cit in cit_text.split(',')]   # Collect Eventcitations
                self.event_citlist.extend(cit_text.split(','))
                event_text += self.apply_citation_text(cit_text.split(','))

            event_text += '\n'
            indent = '    ' if self.ref['part'] == 2 else '  '
            if alt_ind: event_text += '%s%s\n' % (indent, alt_ind)

            alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 5)   # 5: Unbekannter Name
            if alt_cit:
                self.event_citlist.extend(alt_cit.split(',')) # Collect Eventcitations / Person
                # self.event_citlist.append(alt_cit)   # Collect Eventcitations
                alt_cit = self.apply_citation_text(alt_cit.split(','))
            if alt_nme: event_text += '%s%s\n' % (alt_nme, alt_cit)
            if alt_ind: event_text += '%s\n' % alt_ind

            if evt_lrel or 'RELI' in event_abbr:   # Taufe
                for value in [2,3,4,6]:   # Pate, Vertretung, Zeuge, Geistlicher
                    event_text += self.apply_dependend_event(value)
            if 'MARR' in event_abbr:   # Hochzeit, Trauung
                for value in [4,5,6]:   # Zeuge, Helfer, Geistlicher
                    event_text += self.apply_dependend_event(value)

            if event_role:
                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 3)   # 3: Married name
                if alt_cit:
                    self.event_citlist.extend(alt_cit.split(',')) # Collect Eventcitations / Person
                    # self.event_citlist.append(alt_cit)   # Collect Eventcitations
                    alt_cit = self.apply_citation_text(alt_cit.split(','))
                if alt_nme: event_text += '%s%s\n' % (alt_nme, alt_cit)
                if alt_ind:
                    if self.ref['famind']:
                        alt_ind = alt_ind.replace('\\Ind', '% \\Ind')
                        alt_ind = alt_ind.replace('\\oInd', '% \\oInd')
                    event_text += '%s\n' % alt_ind

            if attr_text: event_text += '  %% %s\n' % attr_text

            event = self.database.get_event_from_handle(event_ref.ref)
            if event:
                note_text = apply_note(self.database, event.get_note_list(), 10, \
                                            private=self.include['common']['private'])   # 10: Events
                media_text = self.apply_evt_media(event)

        event_text = event_text.replace('&', '\\&')

        return event_dte, event_abbr, event_text, note_text, media_text

    def sort_event_list(self, event_list, event_type, position):
        """Sort event_list (list of lists) by event_type, depending of position"""

        found = False
        for nr, evt_type in enumerate(event_list):
            if evt_type[2] == event_type:
                found = True
                break
        if found:
            # Shortcut's
            if position == 'B' and nr == 0:
                return event_list
            if position == 'E' and nr == len(event_list):
                return event_list

            # Event list reorganizing
            event_list.remove(evt_type)
            if position == 'B':   # 'Begin'
                event_list = [evt_type] + event_list
            if position == 'E':   # 'End'
                event_list.append(evt_type)

        return event_list


    # Reference methods
    def compile_references(self, person):
        """
        List the references for the given person
        """
        for ref in person.get_person_ref_list():
            if not self.include['common']['private'] and ref.private:
                continue

            ref_person = self.database.get_person_from_handle(ref.ref)
            if not self.include['common']['private'] and ref_person.private:
                continue

            ref_type = 0
            if ref.rel == 'Zwilling':  ref_type =1
            elif ref.rel == 'Taufpate': ref_type = 2
            elif ref.rel == 'Vertretung': ref_type = 3
            elif ref.rel == 'Zeuge': ref_type = 4

            if ref_type > 0:
                ref_nindex = '\\eoInd%s' % ordName(ref_person)   # Extract the right names

                self.dependent.reg[ref_type][0] += 1
                if ref_nindex: self.dependent.reg[ref_type][2].append(ref_nindex)

                # Referenzierte Personen
                if ref_person.gramps_id == 'Ixxxxx':
                    a = 1
                if not self.ref['part'] and \
                   (ref_person.gramps_id not in self.ref['idmap']) and \
                   (ref_person.gramps_id not in self.regular_map) and \
                   (ref_person.gramps_id not in self.relatives_map):
                    self.ref['idmap'][ref_person.gramps_id] = [ref_person.get_handle(), 'o', self.act_generation -1]   # 'o': out

    # Attribute methods
    def apply_attribut(self, attribute_list, attribute_type=['n']):
        "Type: n-ormal, e-mbedded, C-ite, L-ink, T-itel, Te-X"
        if not attribute_list:
            return []

        attr_dict = {}
        for attr in attribute_list:
            if not self.include['common']['private'] and attr.private:
                continue

            attr_type = self._get_type(attr.get_type())
            attr_type = self.replace_narrative_text(attr_type)
            """
            if 'C' in attribute_type and not 'cite' in attr_type.lower():
                continue
            if 'L' in attribute_type and not 'link' in attr_type.lower():
                continue
            if 'T' not in attribute_type and 'titel' in attr_type.lower():
                continue
            if 'T' in attribute_type and not 'titel' in attr_type.lower():
                continue
            if 'zusammengefasst' in attr_type.lower():
                continue
            """
            if 'TeX' in attr_type: attribute_type = 'X'   # Te-X

            attr_text = '. ' if 'e' in attribute_type else ''   #  Embedded Attribute
            attr_text += self._("%(type)s: %(value)s") % \
                {'type' : self._(attr_type), 'value' : attr.get_value()}

            if 'C' in attribute_type and attr_type == 'Cite':   # C-ite
                attr_dict['cite'] = attr_text.split(':')[1].strip()
                continue
            elif 'L' in attribute_type and attr_type == 'Link':   # L-ink
                attr_dict['link'] = attr.get_value()
                continue
            elif 'T' in attribute_type:   # Ortsangaben in T-itel
                if any(x in attr_text for x in ADJACENT):
                    *first, last = attr_text.split()
                    attr_text = ' '.join(first) + ' \\eLoc{%s}' % last
                attr_dict['Titel'] = attr_text
            elif 'X' in attribute_type:   # Te-X
                attr_dict['TeX'] = attr_text
            """
            elif attr_type != 'Cite':
                attr_dict['text'].append(attr_text)
            """
            if "get_citation_list" in dir(attr):
                cit_text = self.add_citations(attr, False)
                if cit_text:
                    cit_list = add_to_list(cit_text)
                    attr_dict['cit'] = self.apply_citation_text(cit_list)

            if "get_note_list" in dir(attr):
                note_text = apply_note(self.database, attr.get_note_list(), 5, \
                    private=self.include['common']['private'])  # Type 5: Attribute
                if note_text:
                    attr_dict['note'] += '\n%s' % note_text

        return attr_dict

    def apply_attribute_dict(self, attribute_dict, spacer=''):
        """ Compose a 'Attribute list' to a 'Attribute string' """
        if not attribute_dict:
            return None

        attribute_text = ''
        for attribute in attribute_dict:
            if attribute == 'cit':
                attribute_text += '%s' % attribute_dict['cit']
            if attribute == 'cite':
                attribute_text += '\\FootciteC%s' % spacer
                if '-' in attribute_dict['cite']:
                    cite_list = attribute_dict['cite'].rsplit('-', 1)   # Only last dash
                    if len(cite_list) == 2:
                        source, page = cite_list[0].strip(), cite_list[1].split('S.')[1].strip()
                        attribute_text += '{%s}[%s]' % (source, page)   # [siehe]
                    else:
                        print('apply_attribute_dict::Error: Cite failed!')
                else:
                    attribute_text += '{%s}' % attribute_dict['cite'].strip()   # [siehe]
            if attribute == 'note':
                attribute_text += '\n%s' % attribute_dict['note']
            if attribute == 'text':
                attribute_text += '\\textit{%s}' % attribute_dict['text']

        return attribute_text

    # Personal methods
    def analyse_person(self, person, global_variable=True):
        """Determines the birth and death date"""
        self.main_person = person

        # Extract the right names
        ord_name = ordName(person, groupas=self.include['person']['groupnames'])
        ord_name.surname = ord_name.surname.replace('N.N.', '\\NN')
        if global_variable: self.shortname = ord_name.shortname

        # Extract the right tags
        for tag_handle in person.tag_list:
            tag = self.database.get_tag_from_handle(tag_handle)
            tag_name = tag.get_name()

            self.stoptag = 'Stop' in tag_name
            self.ref['tag'] = tag_name if tag_name == 'Kirchenamt' else ''

        date_options = {'endnote': self.add_citations, 'year_only': global_variable}
        # Extract Birth Date
        birth = find_birthdate(self.database, person, date_options)
        if global_variable: self.birth = birth['date']

        # Extract Death Date
        death = find_deathdate(self.database, person, date_options)
        if global_variable: self.death = death['date']

        cause, __ = find_specific_event(self.database, person, [EventType.CAUSE_DEATH])
        if cause: death['cause'] = cause.description
        if global_variable: self.cause = death['cause']

        return ord_name.surname, birth, death

    def apply_person_lifetime(self, person, con='', div=','):
        """"""
        def apply_event_str(event, loc):
            evt_cit = []
            if event['cit']: evt_cit += add_to_list(event['cit'])
            place_type, evt_place = get_event_place(self.database, event['event'])
            if evt_place:
                if place_type in ['Kapelle', 'Kirche', 'Kloster', 'Krankenhaus'] and ',' in evt_place:
                    place = evt_place.split(', ')
                    evt_place = '\\%sLoc!e!{%s!%s}' % (loc, place[1], place[0])
                else: evt_place = '\\%sLoc{%s}' % (loc, evt_place)
            if event['event']:
                __, label, country, place, locality, __ = self.apply_event_place(event['event'])
                cit_item = self.add_citations(event['event'], False)
                if cit_item: evt_cit += add_to_list(cit_item)
                if label:
                    loc_list, loc = self.apply_loc_index(loc, '', country, place, locality)
                    if loc_list and len(loc_list) > 1: loc_list.append(loc_list[1])

            return event['date'], evt_place, evt_cit

        date_options = {'endnote': self.add_citations, 'year_only': False}
        birth = find_birthdate(self.database, person, date_options)
        birth_date, birth_place, birth_cit = apply_event_str(birth, 'eb')
        death = find_deathdate(self.database, person, date_options)
        death_date, death_place, death_cit = apply_event_str(death, 'ed')

        lifeline_str = ''
        if birth_date or birth_place or death_date or death_place:
            if birth_date or birth_place:
                lifeline_str += '\\born '
                if birth_date: lifeline_str += '%s' % birth_date
                if con: lifeline_str += '%s ' % con
                if birth_place: lifeline_str += birth_place
            if death_date or death_place:
                lifeline_str = '%s%s ' % (lifeline_str.strip(), div)
                lifeline_str += '\\death '
                if death_date: lifeline_str += '%s' % death_date
                if con: lifeline_str += '%s ' % con
                if death_place: lifeline_str += death_place

        return lifeline_str, birth_cit, death_cit

    def apply_person_narr(self, person, ext=False):
        """"""
        if not person: return '', '', ''

        person_dict = {
            'birth': '', 'christen': '', 'death': '', 'burial': '',
            'cit_list': [], 'loc_list': [], 'ind_list': [], 'dis_list': []
        }

        born_cit, born_loc = '', ''
        born_text = self.narrator.get_born_string()
        if born_text:
            person_dict['birth'], born_cit, born_loc = \
                self.apply_embedded_place('eb', born_text, person, EventType.BIRTH)
            if born_cit: person_dict['cit_list'] += add_to_list(born_cit)
            if born_loc: person_dict['loc_list'].append(born_loc)
        if ext:
            chris_text = self.narrator.get_christened_string()
            if chris_text:
                person_dict['christen'], chris_cit, chris_loc = \
                    self.apply_embedded_place('e', chris_text, person, EventType.CHRISTEN)
                person_dict['christen'] = ' und ' + person_dict['christen'].split(' ', 2)[2]
                if chris_cit: person_dict['cit_list'] += add_to_list(chris_cit)
                if chris_loc: person_dict['loc_list'].append(chris_loc)

                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 6)   # 6: Taufname
                if alt_nme:
                    person_dict['christen'] = person_dict['christen'].replace \
                        ('getauft', 'als %s getauft' % alt_nme)
                if alt_cit: person_dict['cit_list'] += add_to_list(alt_cit)
                if alt_ind: person_dict['ind_list'].append(alt_ind)

                __, christen_ref = find_specific_event(self.database, person, [EventType.CHRISTEN])
                chrisref_list = find_reference_object(self.database, person, christen_ref, \
                                                roletypelist=[u'Pate', u'Taufpate', u'Taufzeuge'])
                if chrisref_list:
                    ref_line = self.apply_witnessed_referenced_person(chrisref_list, '\\symGODx')
                    person_dict['christen'] = person_dict['christen'][:-1] + ref_line

        if not probably_alive(person, self.database):
            died_cit, died_loc = '', ''
            died_text = self.narrator.get_died_string(self.include['person']['computeage'])
            if died_text:
                person_dict['death'], died_cit, died_loc = \
                    self.apply_embedded_place('ed', died_text, person, EventType.DEATH)
                if died_cit: person_dict['cit_list'] += add_to_list(died_cit)
                if died_loc: person_dict['loc_list'].append(died_loc)

                disease, __ = find_specific_event(self.database, person, [EventType.DEATH])
                if disease and disease.description:
                    person_dict['death'] = person_dict['death'][:-1] + ' an \\eDse' + '{' + disease.description + '}.'
                    ddesc = self.apply_dse_index('o', disease.description)
                    person_dict['dis_list'].append(ddesc)
                disease, __ = find_specific_event(self.database, person, [EventType.CAUSE_DEATH])
                if disease and disease.description:
                    person_dict['death'] = person_dict['death'][:-1] + ' an \\eDse' + '{' + disease.description + '}.'
                    ddesc = self.apply_dse_index('o', disease.description)
                    person_dict['dis_list'].append(ddesc)

            if ext:
                buri_text = self.narrator.get_buried_string ()
                if buri_text:
                    person_dict['burial'], buri_cit, buri_loc = \
                        self.apply_embedded_place('e', buri_text, person, EventType.BURIAL)
                    person_dict['burial'] = ' und ' + person_dict['burial'].split(' ', 1)[1]
                    if buri_cit: person_dict['cit_list'] += add_to_list(buri_cit)
                    if buri_loc: person_dict['loc_list'].append(buri_loc)

        return person_dict

    def apply_person_parallel (self, person):
        """"""
        text_parr = []
        self.apply_language (person, self.base['par_language'])

        person_dict = self.apply_person_narr (person)
        if person_dict['birth']: text_parr += ['  %s' % person_dict['birth']]
        texts, __, __ = self.apply_parents (person, prefix='p')
        if texts: text_parr += ['  %s' % texts]
        __, texts, __, __, __, __ = self.apply_marriage_narr(person)
        if texts: text_parr += '  %s' % texts
        if person_dict['death']: text_parr += ['  %s' % person_dict['death']]

        self.apply_language(person, 'de')
        return text_parr

    def write_person_narr(self, person):
        """Writes the persons informations """
        text_list, citation_list, index_list, location_list, disease_list = [], [], [], [], []

        # Element: Narrative Text Head
        text_list += ['\n\\parHead'] if self.base['par_language'] else ['\n\\textHead']
        if self.passport: text_list += ['>|']
        if self.base['par_language']: text_list += '{'
        text_list += '\n'

        # Element: Narrative Text
        self.narrator.set_subject(person)
        person_dict = self.apply_person_narr (person)
        if person_dict['birth']: text_list.append('  %s\n' % person_dict['birth'])
        if person_dict['cit_list']: citation_list += add_to_list(person_dict['cit_list'])
        # location_list.extend(person_dict['loc_list'])
        # index_list.extend(person_dict['ind_list'])
        # disease_list.extend(person_dict['dis_list'])

        if self.report != 'A' or \
           self.act_generation < self.max_generation or \
           not self.stoptag:
            texts, __, citations = self.apply_parents(person)
            if texts: text_list.append('  %s\n' % texts)
            if citations: citation_list += add_to_list(citations)

        if person.gramps_id == 'I00145':
            a = 1

        if self.include['mate']['enable']:
            __, texts, citations, indexes, __, __ = self.apply_marriage_narr(person)
            if texts: text_list.append('  %s\n' % ''.join(texts))
            if citations: citation_list += add_to_list(citations)
            if indexes: index_list.extend(indexes)
            # if locations: location_list.extend(locations)

        if person_dict['death']:
            text_list.append('  %s\n' % person_dict['death'])

        if self.base['par_language']:
            text_parr = self.apply_person_parallel(person)
            text_list.append('}{%\n%s\n' % text_parr)

        # add. Locations
        text_line = self.apply_list(location_list, '  ', 'C', 'S', ' ')   # Compress, Sort
        if text_line: text_list.append('%s\n' % text_line)

        # Element: Narrative Text Tail
        if self.base['par_language']:
            text_list.append('\\parTail\n')
        else:
            text_list.append('\\textTail\n')

        if self.include['common']['notes']:
            note_text = apply_note(self.database, person.get_note_list(), 4, \
                    private=self.include['common']['private'])   # Type 4: Person
            if note_text: text_list.append(note_text)

        return text_list, index_list, citation_list

    def apply_person_info(self, person):
        """"""
        if len([self.include['person']['altnames'], self.include['person']['events'], self.include['person']['attributes'], \
                self.include['common']['addresses']]) == 0:
            return False

        event_list, attr_dict, media_text = [], {}, ''

        self.narrator.set_subject(person)
        # ord_name = ordName(person)

        # List the references for the given person
        self.compile_references(person)

        if self.include['common']['addresses']:   # List the adresses for the given person
            adress_text = '' # self.write_address(person)
            if adress_text:
                self.doc_handle.write('%s\n' % adress_text)

        if self.include['person']['events']:
            # List the events for the given person
            for event_ref in person.get_event_ref_list():   # for all events
            # for event_ref in person.get_primary_event_ref_list():   # only pri. events

                desc_role = None
                event_write = False
                event_role = event_ref.get_role().value
                event_string = event_ref.get_role().string
                event = self.database.get_event_from_handle(event_ref.ref)
                event_value = event.get_type().value
                event_type = event.get_type().string

                # Debug (löscht die 'Referenced'-Tabelle!)

                # Event Role: 1: Primär
                # Event Type: 12: Birth, 14: Adult Christ., 15: Baptism, 19: Burial, 22: Christen.
                if event_role == 1 and event_value not in [12, 14, 15, 19, 22]:
                    pass   # Fast track for events
                else: # Look for every event if referenced
                    for backlink_handle in self.database.find_backlink_handles (event_ref.ref):

                        # Referenztype Bestimmung
                        ref_typename = event_type if self.ref['part'] else event_string
                        if event_string in [u'Pate', u'Taufpate', u'Taufzeuge']: # Witness at christening
                            if person.gender == 0: ref_typename = u'TaufpatinVon'   # 0: Female
                            if person.gender == 1: ref_typename = u'TaufpateVon'   # 1: Male
                        elif event_string == u'Zeuge':   # Witness at wedding
                            if person.gender == 0: ref_typename = u'IndTrauzeuginVon'   # 0: Female
                            if person.gender == 1: ref_typename = u'IndTrauzeugeVon'   # 1: Male

                        event_txt = ''
                        if backlink_handle[0] == u'Person':   # Personal related events
                            ref_person = self.database.get_person_from_handle(backlink_handle[1])

                            for ref_event in ref_person.get_event_ref_list():
                                ref_evt = self.database.get_event_from_handle(ref_event.ref)
                                if self.ref['part'] and \
                                    (self.ref['tag'] == 'Kirchenamt') and \
                                    (ref_evt not in self.ref['evtlist']):
                                    continue

                                if ref_evt.are_equal (event):   # The right event?
                                    refevt_role = ref_event.get_role().value
                                    refevt_string = ref_event.get_role().string

                                    # Debug (löscht die 'Referenced'-Tabelle!)
                                    # self.dependent.debug = True

                                    if self.ref['part'] and \
                                       (person.gramps_id != ref_person.gramps_id) and \
                                       refevt_role == 1:   # 1: Primaer
                                        # Keine geteilten Religionsereignisse!
                                        if ref_typename == 'Religion':
                                            continue
                                        event_date, event_txt, event_abbr = self.apply_event_referenced_person \
                                            (ref_typename, ref_person, event_ref.ref)
                                        if event_txt:
                                            event_item = [event_date, event_txt, event_abbr]
                                            event_list.append(event_item)
                                            event_write = True
                                        pass
                                    else:
                                        if event_string in [u'Pate', u'Taufpate', u'Taufzeuge']:
                                            if refevt_role == 1:
                                                event_date, event_txt, event_abbr = self.apply_event_referenced_person \
                                                    (ref_typename, ref_person, event_ref.ref)
                                                if event_txt:
                                                    event_item = [event_date, event_txt, event_abbr]
                                                    event_list.append(event_item)
                                                    event_write = True

                                                # Referenzierte Personen notieren
                                                if not self.ref['part'] and \
                                                   (person.gramps_id not in self.ref['idmap']) and \
                                                   (ref_person.gramps_id not in self.regular_map) and \
                                                   (person.gramps_id not in self.relatives_map):
                                                    self.ref['idmap'][person.gramps_id] = [person.get_handle(), '', self.act_generation]
                                        else:
                                            prefix, ref_type = 'o', 0
                                            if refevt_string == 'Zeuge': ref_type = 4
                                            elif refevt_string == 'Helfer': ref_type = 5
                                            elif refevt_string == 'Geistlicher': prefix, ref_type = 'c', 6

                                            if ref_type > 0:
                                                ref_nindex = '\\eoInd%s' % ordName(ref_person, groupas=self.include['person']['groupnames'])   # Extract the right names

                                                self.dependent.reg[ref_type][0] += 1   # Counter
                                                if ref_nindex: self.dependent.reg[ref_type][2].append(ref_nindex)

                                                # Referenzierte Personen notieren
                                                if ref_person.gramps_id == 'Ixxxxx':
                                                    a = 1
                                                if not self.ref['part'] and \
                                                   (ref_person.gramps_id not in self.ref['idmap']) and \
                                                   (ref_person.gramps_id not in self.regular_map) and \
                                                   (ref_person.gramps_id not in self.relatives_map):
                                                    self.ref['idmap'][ref_person.gramps_id] = \
                                                        [ref_person.get_handle(), 'o', self.act_generation -1]

                        if backlink_handle[0] == u'Family':   # Family related events
                            ref_family = self.database.get_family_from_handle(backlink_handle[1])

                            event_date, event_txt, event_abbr = self.apply_referenced_family_event \
                                (ref_typename, ref_family, event_ref.ref)
                            if event_txt:
                                event_item = [event_date, event_txt, event_abbr]
                                event_list.append(event_item)
                                event_write = True

                    # Additional role description
                    if event_role == 5: desc_role = 'BR'   # Braut
                    if event_role == 6: desc_role = 'GR'   # Brauetigam

                # The main call for person events
                if not event_write:
                    event_date, event_abbr, event_txt, note_txt, media_txt = \
                        self.apply_total_event(event_ref, desc_role)

                    if event_txt:
                        if note_txt: event_txt += note_txt
                        event_item = [event_date, event_txt, event_abbr]
                        event_list.append(event_item)
                    if media_txt:
                        if self.include['person']['images']:
                            media_text += media_txt
                else:   # STOP!
                    pass

        # Compact Events
        def event_compact(event_list, key1_str, key1_nr, key2_str, key2_nr):
            """"""
            evt_abbr = key1_str
            if 'röm.--kath' in event_list[key2_nr][1]: evt_abbr += 'rk'
            elif 'evangel.' in event_list[key2_nr][1]: evt_abbr += 'ev'
            evt_abbr += key2_str

            evt_ref = event_list[key2_nr][1].split('|')
            evt_refstr = '|%s|' % evt_ref[1] if evt_ref[1] else ''

            evt_birthstr = event_list[key1_nr][1].split('}{')
            evt_birthstr = evt_birthstr[1].split('}}')
            evt_christenstr = event_list[key2_nr][1].split('|{')

            evt_str = '  \\Evt{gen%s}%s{%s} / %s' % (evt_abbr, evt_refstr, evt_birthstr[0], evt_christenstr[1])
            event_list[key1_nr][1] = evt_str
            event_list[key1_nr][2] = evt_abbr

            del event_list[key2_nr]

        evt_birth, evt_christen, evt_death, evt_burial = -1, -1, -1, -1
        for evt_nr, evt in enumerate(event_list):
            if evt[2] == 'BIRT': evt_birth = evt_nr
            if evt[2] == 'CHR' and ' als ' not in evt[1]: evt_christen = evt_nr
        if not self.ref['part'] and \
           (evt_birth > -1 and evt_christen > -1):   # only in normal mode!
            event_compact(event_list, 'BIRT', evt_birth, 'CHR', evt_christen)

        for evt_nr, evt in enumerate(event_list):
            if evt[2] == 'DEAT': evt_death = evt_nr
            if evt[2] == 'burial': evt_burial = evt_nr
        if not self.ref['part'] and \
           (evt_death > -1 and evt_burial > -1):   # only in normal mode!
            event_compact(event_list, 'DEAT', evt_death, 'burial', evt_burial)

        # Rest: Alternate Names
        if self.include['person']['altnames']:
            for nr, __ in enumerate(self.altname.reg):
                if nr in [1, 2, 4, 5, 6, 7]: continue   # 1: AKA, 2: BIRTH, 5: Unkown (hier bei refpart == 2)
                event_date, event_txt = 99999999, ''

                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, nr)
                if alt_cit: alt_cit = self.apply_citation_text(alt_cit.split(','))
                if alt_nme: event_txt += '%s%s\n' % (alt_nme, alt_cit)
                if alt_ind:
                    indent = '  ' if not self.ref['famind'] else ''
                    if self.ref['famind']:
                        alt_ind = alt_ind.replace('\\Ind', '% \\Ind')
                        alt_ind = alt_ind.replace('\\oInd', '% \\oInd')
                    event_txt += '%s%s\n' % (indent, alt_ind)
                if event_txt:
                    event_item = [event_date, event_txt, '']
                    event_list.append(event_item)

        if self.include['person']['attributes']:   # List the atrributes for the given person
            attr_dict = self.apply_attribut(person.get_attribute_list())

        if self.include['person']['images']:
            media_list = person.get_media_list()
            if len(media_list) > 0:
                media_list.pop(0)   # First picture = passport
            media_txt = self.apply_media_list(media_list, 'I', True)
            if media_txt: media_text += media_txt

        return event_list, attr_dict, media_text

    def write_person_info(self, person, event_list, citation_list, attribute_dict, media_text):
        """"""
        event_text =''
        for event_txt in event_list:
            event_text += '%s%s' % (self.line_indent, event_txt[1])

        citation_txt = self.add_citations(person, False)
        citation_lst = add_to_list(citation_txt)
        if citation_lst:
            citation_list.extend(citation_lst)
            citation_list = self.compress_object_list(citation_list)

        # Doppelte Citate aus der Hauptliste ausfiltern und den eigentlichen
        altname_citlist = self.altname.apply_citation()
        citation_list = self.substract_citation_list(citation_list, altname_citlist)
        event_citlist = self.compress_object_list(self.event_citlist)
        citation_list = self.substract_citation_list(citation_list, event_citlist)

        citation_text = self.apply_citation_text(citation_list)

        text_list = []
        attribute_text = self.apply_attribute_dict(attribute_dict)
        if attribute_text: text_list.append(attribute_text)

        if self.include['person']['events'] and \
           (event_text or citation_text):
            ord_name = ordName(person, groupas=self.include['person']['groupnames'])
            if not self.ref['part']:
                shortname = ord_name.shortname.replace('N.N.', '\\NN')
                text_list.append('\n\\indHead{%s}' % shortname)
                if citation_text: text_list.append(citation_text)
                text_list += '\n'

            if event_text:
                htext = 'listHead' if not self.ref['part'] else 'refList'
                ttext = 'list' if not self.ref['part'] else 'ref'
                text_list.append('\n%s\\%s\n' % (self.line_indent, htext))
                text_list.append(event_text)
                text_list.append('%s\\%sTail\n' % (self.line_indent, ttext))

        self.push_list(text_list)
        text_list.clear()

        if media_text:
            self.doc_handle.write(media_text)
            self.doc_handle.write('\n')

        if not self.ref['part']: self.doc_handle.write('\n')

    def write_person(self, handle):
        """Output birth, death, parentage, marriage and notes information """

        self.mode['part'] = 'P'   # P-erson,
        person = self.database.get_person_from_handle(handle)
        if not self.include['common']['private'] and person.private:
            return None
        if not person.gramps_id in self.regular_map:
            self.regular_map[person.gramps_id] = handle

        if person.gramps_id == 'I13769':
            a = 1

        ord_name = ordName(person, groupas=self.include['person']['groupnames'])   # Extract the right names
        if not ord_name.valid: return False

        # Element: Primary / Alternate Names
        # self.compile_name_primary(person)
        self.dependent.clear(DEPENDENT)
        self.altname = self.find_name_alternate(person)
        self.analyse_person(person)

        # index_map: DAR = int, DDR = str!
        if (self.report == 'A'):
            gen_no = self.index_map[handle]
        else:   # (self.report == 'D')
            if self.index_map[handle].isnumeric():
                gen_no = int(self.index_map[handle])
            else:
                gen_no = int(self.index_map[handle], 16) -16
        gen_str = '{0:,}'.format(int(gen_no)).replace(',',' ')
        gen_str =  '{%s}' % gen_str
        gen_str += '[%s]' % ord_name.nametype   # gut zum Kontrollieren des Namentypes!

        if gen_no in self.numbers_printed:
            return False
        else:
            self.numbers_printed.append(gen_no)

        text_list = []
        # Element: Spacer
        if gen_no > 2**(self.act_generation -1):
            self.apply_divider('=','\n')
            if person.gender == 0: text_list.append('\\vspace{+2 ex}\n')   # 0: Female
            if person.gender == 1: text_list.append('\\vspace{+2.5 ex}\n')   # 1: Male

        # Element: Individual number + name
        text_list.append('\\narrLabel%s\n' % gen_str)
        text_list.append('\\narrHead')
        text_list.append(ord_name.linename)

        # Element: Attribut: Cite
        if self.include['person']['attributes']:
            ref_attrdict = self.apply_attribut(person.get_attribute_list(), ['C'])  # C-ite
            ref_attrtext = self.apply_attribute_dict(ref_attrdict)
            if ref_attrtext: text_list.append(ref_attrtext)

        text_list.append('\n')

        # Element: Apply Narrative Data
        text_narr, index_narr, citation_narr = [], '', []
        if self.include['person']['narrative']:
            text_narr, index_narr, citation_narr = self.write_person_narr(person)
            text_list.append('%s\n' % ''.join(index_narr))

        # Element: Alternate Names
        if self.include['person']['altnames']:
            alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 1)   # 1: Also known as (AKA)
            if alt_cit: alt_cit = self.apply_citation_text(alt_cit.split(','))
            if alt_nme: text_list.append('%s%s%s\n' % (' '*2, alt_nme, alt_cit))
            if alt_ind: text_list.append('  %s\n' % alt_ind)

        # Element: Attribut: Titel
        if self.include['person']['attributes']:
            attribute_dict = self.apply_attribut(person.get_attribute_list(), ['T'])  # T-itel
            attribute_text = self.apply_attribute_dict(attribute_dict)
            if attribute_text: text_list.append(attribute_text)

        # Element: Passport picture
        if self.include['person']['passport']:
            passport_text = self.apply_passport(person)
            if passport_text: text_list.append(passport_text)

        # Element: Life line
        if self.include['person']['lifeline'] and not self.ref['part']:
            options = {'mode':0, 'new_generation': False, 'act_generation': self.act_generation,
                       'rindent': True, 'groupname': self.include['person']['groupnames'], 'index_map': self.index_map}
            life_line = apply_lifeline(self.database, person, options)
            if life_line: text_list.append(life_line)

        # Element: Lineage path
        if self.include['person']['path'] and not self.ref['part']:
            path = self.apply_path(gen_no, person)
            text_list.append(path)

        # Element: Write Data
        text_list.extend(text_narr)
        self.push_list(text_list)

        event_list, attribute_dict, media_text = [], {}, ''
        if self.include['person']['events']:
            event_list, attribute_dict, media_text = self.apply_person_info(person)

        self.write_person_info(person, event_list, citation_narr, attribute_dict, media_text)

        self.altname.clear(ALTERNATE)
        self.dependent.clear(DEPENDENT)

        # Clear Event Citation Liste
        del self.event_citlist[:]

        return True


    # Referenced Personal methods
    def apply_witnessed_referenced_person(self, reflist, refsym):
        """"""
        if not reflist: return '.'

        ref_line = ' (%s ' % refsym
        for r, ref in enumerate(reflist):
            ref_person = self.database.get_person_from_handle(ref)
            ref_name = ordName(ref_person, groupas=self.include['person']['groupnames'])
            if r == len(reflist) -1: ref_line += ' \\& '
            elif len(ref_line) > 12: ref_line += ', '
            ref_line += '\\eoInd' + ref_name.linename
        ref_line += ').'
        return ref_line

    def apply_embedded_referenced_person(self, person, ref_person, prefix=''):
        """"""
        # referenced persons (e.g. out of child list)
        if not self.ref['part'] and self.kid_report and \
           (person.gramps_id not in self.ref['idmap']) and \
           (ref_person.gramps_id not in self.regular_map) and \
           (person.gramps_id not in self.relatives_map):
            # add to reference map
            self.ref['idmap'][person.gramps_id] = [person.get_handle(), prefix, self.act_generation -1]   # '': normal

            exist = None
            for key in self.embedded_map:
                exist = person.gramps_id in self.embedded_map[key]

            if not ref_person:
                kid_id = 'K%s' % str(self.kid_counter).zfill(4)
            else:
                kid_id = ref_person.gramps_id

            if exist:
                emblist = self.embedded_map[person.gramps_id]
                emblist.append(kid_id)
                self.embedded_map[person.gramps_id] = emblist
                pass
            else:
                self.embedded_map[person.gramps_id].append(kid_id)

        return True

    def apply_event_referenced_person(self, ref_type, person, event_ref, family_handle=None):
        """"""
        pers_name = ordName(person, groupas=self.include['person']['groupnames'])   # Extract the right names
        pers_nindex = 'nInd'
        pers_findex = ''

        if family_handle:
            family = self.database.get_family_from_handle(family_handle)

            if self.ref['famind']:   #  besteht vorheriger Familien-Index?
                if person.gender == 0:
                    pers_nindex = 'fInd'
                    ref_handle = family.get_father_handle()
                elif person.gender == 1:
                    pers_nindex = 'mInd'
                    ref_handle = family.get_mother_handle()
            else:
                if person.gender == 0:
                    pers_nindex = 'fIndFam'
                    ref_handle = family.get_father_handle()
                elif person.gender == 1:
                    pers_nindex = 'mIndFam'
                    ref_handle = family.get_mother_handle()
            ref_person = self.database.get_person_from_handle(ref_handle)
            ref_name = ordName(ref_person, groupas=self.include['person']['groupnames'])   # Extract the right names
            if self.ref['format'] == 'o': pers_nindex += '!o!'
            if not self.ref['famind']:
                pers_findex = '(%s)' % ref_name.marriagename if ref_name.marriagename else ''
                if family.gramps_id: pers_findex += '[%s]' % family.gramps_id

        ref_type += 'Mit'
        evt_abbr = self.get_event_abbr(ref_type)
        ref_date, ref_id, ref_evttext, ref_cittext, ref_ntetext = \
            self.apply_referenced_event(event_ref, evt_abbr)

        if self.ref['part']:
            if (self.ref['tag'] == 'Kirchenamt') and \
               (ref_id not in self.ref['evtlist']):
                return 0, '', ''

        if evt_abbr == 'MARRw': evt_abbr = 'WITTw'
        evt_text = '  \\Evt{gen%s}' % evt_abbr
        evt_text += '{'
        if pers_nindex: evt_text += '\\e%s%s' % (pers_nindex, pers_name)
        if pers_findex: evt_text += pers_findex
        if ref_evttext: # ref_evttext kann None sein, erzeugt Leerzeichen
            evt_text += ' '
            if self.ref['part']: evt_text += '\\\\'
            evt_text += '\n%s%s' % (' '*4, ref_evttext)
        evt_text += '}'

        if ref_cittext: evt_text += '%s' % ref_cittext
        if self.ref['part'] and ref_id in self.ref['evtlist']:
            evt_text += '\\refPtr{%s}' % ref_id
        evt_text += '\n'
        if ref_ntetext: evt_text += '  %s\n' % ref_ntetext

        return ref_date, evt_text, evt_abbr

    def apply_refperson(self, refid):
        """Output birth, death, parentage, marriage and notes information """

        self.ref['format'] = refid[3]
        person = self.database.get_person_from_handle(refid[1])
        if not self.include['common']['private'] and person.private: return None

        ord_name = ordName(person, groupas=self.include['person']['groupnames'])   # Extract the right names
        if not ord_name.valid: return False

        # Element: Primary / Alternate Names
        self.dependent.clear(DEPENDENT)
        self.altname = self.find_name_alternate(person)
        self.analyse_person(person)

        self.ref['part'] = 2   # Referenced Persons List generation Part 2
        # Element: Verheiratet
        self.ref['famind'].clear()
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            mate_handle = ReportUtils.find_spouse(person, family)
            if not mate_handle: continue

            mate = self.database.get_person_from_handle(mate_handle)
            __, __, famind = self.apply_marriage_index(family, person, mate, prefix=self.ref['format'])
            famind = '%s\\%s\n' % (self.line_indent, famind)
            self.ref['famind'].append(famind)

        event_list, citation_list, attribute_dict = [], [], {}
        # Element: Sohn / Tochter von
        if self.main_person.gender == 0: typename = 'TochterVon'
        elif self.main_person.gender == 1: typename = 'SohnVon'
        else: typename = 'UnbekanntVon'
        parent_handle = person.get_main_parents_family_handle()
        if parent_handle:
            parents = self.database.get_family_from_handle(parent_handle)
            marriage, marriage_ref = find_specific_event(self.database, parents, \
                                        [EventType.MARRIAGE], roletypelist=[EventRoleType.FAMILY])
            marriage_ref = marriage_ref.ref if marriage_ref else None
            event_date, event_txt, event_abbr = self.apply_referenced_family_event \
                (typename, parents, marriage_ref)
            if event_txt:
                event_item = [event_date, event_txt, event_abbr]
                event_list.append(event_item)

        # Element: Passport picture
        passport_text = self.apply_passport(person)

        #  Element: Ereignisse: Person
        event_lst, attribute_dct, media_text = self.apply_person_info(person)
        if event_lst: event_list.extend(event_lst)
        if attribute_dct: attribute_dict.update(attribute_dct)

        #  Element: Ereignisse: Familie
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            event_lst, citation_lst, attribute_dct, __ = self.apply_family_info(family)
            if event_lst: event_list.extend(event_lst)
            if citation_lst: citation_list.extend(citation_lst)
            if attribute_dct: attribute_dict.update(attribute_dct)

        # Sorting by date, event type
        event_list.sort () # (key=lambda x:x[0])
        event_list = self.sort_event_list(event_list, 'CHRIS', 'B')
        event_list = self.sort_event_list(event_list, 'BIRT', 'B')
        event_list = self.sort_event_list(event_list, 'CHLDFo', 'B')
        event_list = self.sort_event_list(event_list, 'CHLDMo', 'B')
        event_list = self.sort_event_list(event_list, 'DEAT', 'E')
        event_list = self.sort_event_list(event_list, 'burial', 'E')

        self.ref['part'] = 3   # Referenced Persons List generation Part 3
        text_list = []
        # Element: Individual number + name
        text_list.append('%s\\refLabel{%s}' % (self.line_indent, refid[4]))   # Level, Generation
        if refid[3]: text_list.append('[%s]' % refid[3])   # Format
        text_list.append('{%s}\n' % ord_name.nametype)   # NameType

        text_list.append('%s\\refHead%s' % (self.line_indent, ord_name.linename))
        # Element: Attribut: Cite
        ref_idlist = ''
        if person.gramps_id in self.embedded_map:
            emblist = self.embedded_map[person.gramps_id]
            for i, kid_id in enumerate(emblist):
                ref_idlist += '{%s}' % kid_id if i == 0 else '[%s]' % kid_id

        ref_cittext = ''
        citation_text = self.add_citations(person, False)   # Eintrag in die Citationsliste
        if citation_text:
            citation_list = add_to_list(citation_text)
            ref_cittext = self.apply_citation_text(citation_list)

        spacer = 'x' if citation_text else ''
        ref_attrdict = self.apply_attribut(person.get_attribute_list(), ['C'])  # C-ite
        ref_attrtext = self.apply_attribute_dict(ref_attrdict, spacer)

        if  ref_idlist or ref_cittext or ref_attrtext:
            text_line = '!'
            if ref_attrtext: text_line += ref_attrtext
            if ref_cittext: text_line += ref_cittext
            if ref_idlist: text_line += '\\Ref%s' % ref_idlist
            text_line += '!'
            text_list.append(text_line)
        text_list.append('\n')

        # Element: Family Index
        if self.ref['famind']:
            text_list.extend(self.ref['famind'])

        # Element: Passport picture
        if passport_text: text_list.append(passport_text)

        #  2: Birth -, 5: Unknown -, 1: AKA, 0: Custom name
        for alt_type in [6, 7, 2, 4, 5, 1, 0]:
            alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, alt_type, '  ')
            if alt_cit: alt_cit = self.apply_citation_text(alt_cit.split(','))
            if alt_nme: text_list.append('%s%s%s\n' % (self.line_indent, alt_nme, alt_cit))
            if alt_ind: text_list.append('%s\n' % alt_ind)

        # Element: Attribut: Titel
        attribute_dict = self.apply_attribut(person.get_attribute_list(), ['T'])  # T-itel
        attribute_text = self.apply_attribute_dict(attribute_dict)
        if attribute_text: text_list.append('%s%s' % (self.line_indent, [attribute_text]))

        self.push_list(text_list)

        self.write_person_info(person, event_list, citation_list, attribute_dict, media_text)

        self.altname.clear(ALTERNATE)
        self.dependent.clear(DEPENDENT)

        # Clear Event Citation Liste
        del self.event_citlist[:]

        return True

    def write_refperson(self, report):
        """Write data sets reg. Referencend Persons"""

        # Referencend Persons
        self.mode['part'] = 'R'   # R-eference
        self.ref['part'] = 1   # Activate Referenced Persons List generation

        ref_list = []
        for key in sorted (self.ref['idmap']):
            if key in self.regular_map: continue
            # if key in self.regular_map: self.ref['idmap'][key][1] = ''   #  normalize (out) entries
            if self.ref['idmap'][key][1] == 'n': self.ref['idmap'][key][1] = ''   # sort normal entries out
            if (self.ref['idmap'][key][0] not in self.handle_map.values()) and \
               (self.ref['idmap'][key][0] not in self.relatives_map.values()):
                person = self.database.get_person_from_handle(self.ref['idmap'][key][0])

                ord_name = ordName(person, groupas=self.include['person']['groupnames'])   # Extract the right names
                ord_name.surname = ord_name.surname.replace('\\NN', 'NN')
                for adj in ADJACENT:
                    if adj in ord_name.surname:
                        ord_name.surname = ord_name.surname.replace(adj + ' ', '')
                sort_name = '%s_%s' % (ord_name.surname, ord_name.givenname)

                ref_data = [key, self.ref['idmap'][key][0], sort_name, \
                            self.ref['idmap'][key][1], self.ref['idmap'][key][2]]
                if ref_data: ref_list.append(ref_data)

        # Sorting by names
        ref_list.sort (key=lambda x:x[2])

        path_name, report_text = \
            apply_filehead(report, self.database, self.pid, self.base['result_path'], \
                           'Referenzierte Personen', 'Ref', 'tex')
        ref_file = open(path_name, mode='w', buffering=1)
        ref_file.writelines('%% %s' % report_text)

        self.doc_handle = ref_file

        # Writing into a file
        for key in ref_list:
            self.ref['part'], self.ref['famid'], self.ref['tag'] = 1, '', ''
            # Elements: Amount
            elements = self.check_elements_count(key[1])
            key.append(elements)

            self.line_indent = '  ' if elements else''
            if elements: ref_file.write('\\ifnumgreater{\\value{_srcRef_}}{%s}{\n' % elements)
            result = self.apply_refperson(key)
            if elements: ref_file.write('}{}')
            ref_file.write('\n')
            if result: self.apply_divider('-','\n')

        # Closing
        ref_file.write('\\endinput\n\n')
        ref_file.close()

        self.ref['part'] = 0   # Deactivate Referenced Persons List generation
        self.line_indent = ''   # Deactivate Line Indention

        return True


    # Family methods
    def get_family_type(self, family_type):
        """"""
        symbol = ''
        if family_type.value == family_type.CIVIL_UNION:
            symbol = '\\ftCU'   # gesetzliche Partnerschaft
        elif family_type.value == family_type.MARRIED:
            symbol = '\\ftM'   # Verheiratet
        elif family_type.value == family_type.UNMARRIED:
            symbol = '\\ftD'   # Geschieden (Divorced)
        elif family_type.value == family_type.UNKNOWN:
            symbol = '\\ftU'   # Unbekannt
        elif family_type.value == family_type.CUSTOM:
            symbol = '\\ftC'   # Benutzerdefiniert

        return symbol

    def apply_family_and(self, family_type, family_id=None):
        """ Creates the 'Marriage' symbol """
        fam_and = '\\And'
        if self.ref['part']: fam_and += '[R]'
        fam_and += '{%s}' % self.get_family_type(family_type)
        if family_id: fam_and += '[%s]' % family_id

        return fam_and

    def apply_family(self, family_handle, ref_person=None, prefix='', con=''):
        """"""
        if not family_handle:
            return ['', '', ''], ['', '', ''], '', ''

        family = self.database.get_family_from_handle(family_handle)
        father_handle = family.get_father_handle()
        father = self.database.get_person_from_handle(father_handle) \
            if father_handle else None
        mother_handle = family.get_mother_handle()
        mother = self.database.get_person_from_handle(mother_handle) \
            if mother_handle else None
        father_index, mother_index, family_index = \
            self.apply_marriage_index(family, father, mother, embedded='\\e', prefix='')

        father_shortname = ''
        if father_handle:
            father_name = ordName(father, groupas=self.include['person']['groupnames'])   # Extract the right names
            if father_name.valid:
                father_shortname = father_name.shortname
                self.apply_embedded_referenced_person(father, ref_person, prefix)
            else:
                father_handle = None

        mother_shortname = ''
        if mother_handle:
            mother_name = ordName(mother, groupas=self.include['person']['groupnames'])   # Extract the right names
            if mother_name.valid:
                mother_shortname = mother_name.shortname
                self.apply_embedded_referenced_person(mother, ref_person, prefix)
            else:
                mother_handle = None

        family_shortname = '%s %s %s' % (father_index, con, family_index) \
            if father_handle and mother_handle else ''

        return [father, father_shortname, father_index], \
               [mother, mother_shortname, mother_index], \
               [family, family_shortname, family_index]

    def apply_referenced_family_event(self, ref_type, family, event_ref):
        """"""
        father_handle = family.get_father_handle()
        father = self.database.get_person_from_handle(father_handle) \
            if father_handle else None
        mother_handle = family.get_mother_handle()
        mother = self.database.get_person_from_handle(mother_handle) \
            if mother_handle else None
        prefix = 'o' if self.ref['format'] == 'o' and \
               father and father.gramps_id not in self.regular_map else ''
        father_index, __, family_index = \
            self.apply_marriage_index(family, father, mother, embedded='\\e', prefix=prefix)

        ref_type += 'Mit'
        evt_abbr = self.get_event_abbr(ref_type)
        ref_dte, ref_id, ref_evttext, ref_cittext, ref_ntetext = \
            self.apply_referenced_event(event_ref, evt_abbr)

        if self.ref['part']:
            if (self.ref['tag'] == 'Kirchenamt') and \
               (ref_id not in self.ref['evtlist']):
                return 0, '', ''

        evt_text = '  \\Evt{gen%s}' % evt_abbr
        evt_text += '{%s \\& %s' % (father_index, family_index)
        if ref_evttext: # ref_evttext kann None sein, erzeugt Leerzeichen
            if self.ref['part']: evt_text += '\\\\'
            evt_text += '\n%s%s' % (' '*4, ref_evttext)
        evt_text += '}'
        if ref_cittext: evt_text += '%s' % ref_cittext
        if self.ref['part'] and ref_id in self.ref['evtlist']:
            evt_text += '\\refPtr{%s}' % ref_id
        evt_text += '\n'
        if ref_ntetext: evt_text += '  %s\n' % ref_ntetext

        return ref_dte, evt_text, evt_abbr

    def write_family_head(self, family, citation_list):
        """ Writes the families informations """

        mother_handle = family.get_mother_handle()
        father_handle = family.get_father_handle()
        if not (mother_handle and father_handle):
            return None

        family_prefix, father_shortname, mother_shortname = self.family_base.apply_head(family)

        if mother_shortname and father_shortname:
            self.apply_divider('.', '\n')
            marr_text = '\\marHead{%s}' % mother_shortname
            if family_prefix:
                marr_text += '[%s!%s]' % (family_prefix[0], family_prefix[1])
            marr_text += '{%s}' % father_shortname
            marr_text += '[%s]' % family.gramps_id
            if citation_list:
                citation_text = self.apply_citation_text(citation_list)
                marr_text += citation_text
            self.doc_handle.write('%s\n' % marr_text)

            # fam_index = self.apply_fam_index('', family.gramps_id, father_prefix, father_shortname, mother_shortname, 'textbf')
            # self.doc_handle.write('%s\n' % fam_index)

            self.write_note(family.get_note_list(), 9, False)   # Type 9: Family
            self.doc_handle.write('\n')

    def apply_family_info(self, family):
        """ Writes the families informations """

        event_list, citation_list, attribute_dict, media_text = [], [], {}, ''

        mother_handle = family.get_mother_handle()
        father_handle = family.get_father_handle()
        if not (mother_handle and father_handle):
            return event_list, citation_list, attribute_dict, media_text

        if self.include['family']['events']:
            # List the events for the given family
            for event_ref in family.get_event_ref_list():
                event_write = False

                event = self.database.get_event_from_handle(event_ref.ref)
                event_string = event_ref.get_role().string   #  Debug!
                event_value = event_ref.get_role().value

                # Look for every event if referenced
                if not self.ref['part']:
                    for backlink_handle in self.database.find_backlink_handles (event_ref.ref):

                        ref_typename = u'Unkown'
                        if backlink_handle[0] == u'Person' and \
                           backlink_handle[1] != father_handle and \
                           backlink_handle[1] != mother_handle:
                            ref_person = self.database.get_person_from_handle(backlink_handle[1])

                            for ref_event in ref_person.get_event_ref_list():
                                refevt = self.database.get_event_from_handle(ref_event.ref)
                                if self.ref['part'] and \
                                    (self.ref['tag'] == 'Kirchenamt') and \
                                    (ref_evt not in self.ref['evtlist']):
                                    continue

                                if refevt.are_equal(event):   # The right event?
                                    refevt_string = ref_event.get_role ().string

                                    prefix, ref_type = 'o', 0
                                    if refevt_string == 'Zeuge':  ref_type = 4
                                    elif refevt_string == 'Helfer': ref_type = 5
                                    elif refevt_string == 'Geistlicher': prefix, ref_type = 'c', 6

                                    if ref_type > 0:
                                        ref_nindex = '\\enInd%s' % ordName(ref_person)   # Extract the right names

                                        self.dependent.reg[ref_type][0] += 1
                                        if ref_nindex: self.dependent.reg[ref_type][2].append(ref_nindex)

                                        # if self.dependent.reg[ref_type][0] > 1:   ???
                                        if refevt_string == 'Zeuge':
                                            if self.dependent.reg[ref_type][0] == 1:
                                                if ref_person.gender == 0:
                                                    self.dependent.reg[ref_type][1] = u'IndTrauzeuginVon'   # 0: Female
                                                if ref_person.gender == 1:
                                                    self.dependent.reg[ref_type][1] = u'IndTrauzeugeVon'   # 1: Male
                                            else:
                                                self.dependent.reg[ref_type][1] = u'IndTrauzeugen'

                                        # Referenzierte Personen
                                        if ref_person.gramps_id == 'Ixxxxx':
                                            a = 1
                                        if not self.ref['part'] and \
                                           (ref_person.gramps_id not in self.ref['idmap']) and \
                                           (ref_person.gramps_id not in self.regular_map) and \
                                           (ref_person.gramps_id not in self.relatives_map):
                                            self.ref['idmap'][ref_person.gramps_id] = [ref_person.get_handle(), 'o', self.act_generation -1]

                                    else:
                                        pass   # STOP!

                    if backlink_handle[0] == u'Family':
                        ref_family = self.database.get_family_from_handle(backlink_handle[1])

                        if family.handle != ref_family.handle:
                            for ref_event in ref_family.get_event_ref_list():
                                refevt = self.database.get_event_from_handle(ref_event.ref)
                                refevt_role = ref_event.get_role().value
                                # refevt_type = ref_event.get_role().string
                                if refevt.are_equal (event):   # The right event?
                                    if event_value == 8 and refevt_role == 7:   # 7: Witness, 8: Family Trauzeuge bei einer Heirat)
                                        ref_typename = u'FamTrauzeugen'
                                        event_date, event_txt, event_abbr = self.apply_referenced_family_event \
                                            (ref_typename, ref_family, None)
                                    elif event_value == 7 and refevt_role == 8:   # 8: Family (Trauzeuge von den Brautleuten)
                                        ref_typename = u'FamTrauzeugenVon'
                                        event_date, event_txt, event_abbr = self.apply_referenced_family_event \
                                            (ref_typename, ref_family, event_ref.ref)
                                    else:
                                        ref_typename = u'Unkown:' + str(event_value) +'-'+ str(refevt_role)
                                        event_date, event_txt, event_abbr = self.apply_referenced_family_event \
                                            (ref_typename, ref_family, None)
                                        pass
                                    if event_txt:
                                        event_item = [event_date, event_txt, event_abbr]
                                        event_list.append(event_item)

                # The main call for family events
                if not event_write:
                    event_date, event_abbr, event_txt, note_txt, media_txt = self.apply_total_event(event_ref)
                    if self.ref['part']:
                        if event_abbr in ['MARB']: continue

                        ref_typename = event.get_type ().string
                        if self.main_person.gender == 0: mate_handle = father_handle
                        elif self.main_person.gender == 1: mate_handle = mother_handle
                        else: break
                        ref_person = self.database.get_person_from_handle(mate_handle)

                        event_date, event_txt, event_abbr = self.apply_event_referenced_person \
                            (ref_typename, ref_person, event_ref.ref, family.handle)
                    if event_txt:
                        if note_txt: event_txt += note_txt
                        event_item = [event_date, event_txt, event_abbr]
                        event_list.append(event_item)
                    if media_txt:
                        if self.include['family']['images']:
                            media_text += media_txt

        if self.include['family']['attributes']:
            # List the attributes for the given family
            attribute_dict = self.apply_attribut(family.get_attribute_list(), ['C', 'L', 'X'])

        if self.include['family']['images']:
            media_list = family.get_media_list()
            media_txt = self.apply_media_list(media_list, 'F', True)
            if media_txt: media_text += media_txt

        citation_text = self.add_citations(family, False)   # Eintrag in die Citationsliste
        citation_list = add_to_list(citation_text)
        citation_list = self.compress_object_list(citation_list)

        return event_list, citation_list, attribute_dict, media_text

    def write_family_info(self, family):
        """"""
        # Clear Event Citation Liste
        del self.event_citlist[:]

        event_list, citation_list, attr_text, media_text = self.apply_family_info(family)

        # Doppelte Citate ausfiltern
        event_citlist = self.compress_object_list(self.event_citlist)
        citation_list = self.substract_citation_list(citation_list, event_citlist)

        # Ehe auffuehren
        if self.include['family']['enable']:
            self.write_family_head(family, citation_list)

        # Clear Event Citation Liste
        del self.event_citlist[:]

        event_text =''
        for event_txt in event_list:
            event_text += event_txt[1]

        if attr_text:
            text = '\\textit{%s}\n\n' % attr_text
            self.doc_handle.write(text)

        if event_text:
            self.doc_handle.write('\\listHead\n')
            self.doc_handle.write(event_text)
            self.doc_handle.write('\\listTail\n\n')

        if media_text:
            self.doc_handle.write(media_text)

        return True

    def write_family(self, person_handle):
        """"""
        person = self.database.get_person_from_handle(person_handle)
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            mother_handle = family.get_mother_handle()
            father_handle = family.get_father_handle()
            if not (mother_handle or father_handle):
                continue

            if self.include['mate']['enable']:
                self.write_mate(person, family)

            self.write_family_info(family)

            if self.include['children']['enable']:
                self.write_children(family)


    # Relatives methods
    def apply_parents(self, person, ref_person=None, prefix='', con=' und'):
        """ Apply the parants """
        family_handle = person.get_main_parents_family_handle()
        if not family_handle:
            return '', '', []
        family = self.database.get_family_from_handle(family_handle)

        def life_span(person, prefix=''):
            """"""
            life_lne = ''
            date_options = {'endnote': self.add_citations, 'year_only': True}
            byear, bcit = determine_birthdate(self.database, person, date_options)
            dyear, dcit = determine_deathdate(self.database, person, date_options)
            if (bcit or dcit) and prefix == 'o':
                life_lne += ' {\\small('
                if byear != 0: life_lne += '%s' % byear
                life_lne += '--'
                if byear != 0: life_lne += '%s' % dyear
                life_lne += ')}'
            return life_lne

        par_text, par_line, par_cit = '', '', []
        par_father, par_mother, par_family = \
            self.apply_family(family_handle, ref_person, prefix, con=con)   # p: Parents
        narr_text = self.narrator.get_child_string(par_father[1], par_mother[1])
        if narr_text:
            narr_text, narr_cit = self.split_text_citation(narr_text)
            if narr_cit: par_cit += add_to_list(narr_cit)
            narr_text = narr_text.split('von')[0] + 'von '

            if par_father[0]:
                narr_text += par_father[2] + life_span(par_father[0], prefix)
            if par_father[0] and par_mother[0]: narr_text += ' und '
            if par_mother[0]:
                narr_text += par_family[2] + life_span(par_mother[0], prefix)
            narr_text += '.'

            if (par_father[0] and par_mother[0]) and prefix == 'o':
                fam_conn = self.apply_family_and(family.type, family.gramps_id)
                narr_text = narr_text.replace('und', fam_conn)

                wedd_sym, wedd_line, wedd_cit = self.apply_wedding(family)
                if wedd_line:
                    narr_text = narr_text[:-1] + ', %s %s.' % (wedd_sym, wedd_line)
                if wedd_cit: par_cit = add_to_list(wedd_cit)

            par_text = self.replace_narrative_text(narr_text)
            par_line = par_text[:-1].split('von ')[1]

        return par_text, par_line, par_cit

    def apply_marriage(self, family, global_variable=True):
        """Apply a family's marriage date """
        """
        marr_date = 0

        self.add_citations(marr_event, False)
        marr_date = marr_event.get_date_object().get_year() \
                    if global_variable else \
                    self._get_date(marr_event.get_date_object())
        if marr_date == '': marr_date = 0

        return marr_date
        """
        marr_event, __ = find_specific_event (self.database, family, \
                            [EventType.MARRIAGE], roletypelist=[EventRoleType.FAMILY])
        if marr_event:
            evt_id, evt_dte, __, __, evt_srel, evt_txt, __, cit_text = \
                self.apply_event(marr_event.handle, 'r')
            if evt_txt:
                marr_sym = '\\marr'
                if evt_srel: marr_sym += '[%s]' % evt_srel
                return marr_sym, evt_txt, cit_text
        return '', '', ''

    def apply_wedding(self, family):
        """Apply a family's weddings date """
        wedd_event, __ = find_specific_event (self.database, family, \
                        [EventType.CUSTOM], eventtypestring='Trauung', roletypelist=[EventRoleType.FAMILY])
        if wedd_event:
            evt_id, evt_dte, __, __, evt_srel, evt_txt, __, cit_txt = \
                self.apply_event(wedd_event.handle, 'r')
            if evt_txt:
                wedd_sym = '\\marr'
                if evt_srel: wedd_sym += '[%s]' % evt_srel
                return wedd_sym, evt_txt, cit_txt
        return '', '', ''

    def apply_marriage_index(self, family, person, mate, embedded='\\', prefix=''):
        """"""
        person_index, mate_index, family_index = embedded + 'mInd', embedded + 'fInd', embedded + 'fIndFam'
        person_name = ordName(person, groupas=self.include['person']['groupnames'])
        mate_name = ordName(mate, groupas=self.include['person']['groupnames'])

        if mate:   # Mate maybe None!
            if family.type.string in ['Verheiratet', 'Geschieden']:
                if mate.gender == 1:
                    person_index, mate_index, family_index = embedded + 'fInd', embedded + 'mInd', embedded + 'mIndFam'

                if prefix: family_index += '!%s!' % prefix
                family_index += mate_name.linename
                if mate_name.marriagename:
                    family_index += '(%s!%s)' % (person_name.groupname, mate_name.marriagename) \
                        if person_name.groupname else '(%s)' % mate_name.marriagename
                if family.gramps_id: family_index += '[%s]' % family.gramps_id
            else:
                family_index += 'fInd' if mate.gender == 0 else 'mInd'
                if prefix: family_index += '!%s!' % prefix
                family_index += mate_name.linename

            if prefix: mate_index += '!%s!' % prefix
            mate_index += mate_name.linename
        else: mate_index, family_index = '', ''

        if person:   # Person maybe None!
            if prefix: person_index += '!%s!' % prefix
            person_index += person_name.linename
        else: person_index == ''

        return person_index, mate_index, family_index

    marr_dict = {'Civil': 'zivil',
                 'Römisch-Katholisch': 'röm.--kath.',
                 'Evangelisch': 'evang.'
                }
    def apply_marriage_narr(self, person, prefix=''):
        """
        Output marriage sentence.
        """
        is_first = True
        spouse_dict = {}
        mar_list, cit_list, idx_list, loc_list, dse_list, mda_list = [], [], [], [], [], []

        # person_name = ordName(person)   # Extract the right names
        # pers_prefix, pers_shortname, pers_fullname, __, __ = self.apply_referenced_person(prefix, person)
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            spouse_handle = ReportUtils.find_spouse(person, family)
            if not spouse_handle: continue

            spouse = self.database.get_person_from_handle(spouse_handle)
            __, spouse_idx, family_idx = self.apply_marriage_index(family, person, spouse, embedded='', prefix=prefix)
            spouse_name = ordName(spouse)   # Extract the right names
            spouse_dict[spouse.gramps_id] = {'family': family_handle, 'spouse': spouse_handle}

            if not self.ref['part'] and \
               (spouse.gramps_id not in self.ref['idmap']):
                self.ref['idmap'][spouse.gramps_id] = [spouse.get_handle(), '', self.act_generation -1]

            if spouse and spouse_name.valid:
                self.apply_embedded_referenced_person(spouse, person)
                spse_lastname, birth, death = self.analyse_person(spouse, False)
                if birth['cit']: cit_list += add_to_list(birth['cit'])
                if death['cit']: cit_list += add_to_list(death['cit'])
                spse_lifetime, __, __ = self.apply_person_lifetime(spouse, ' in')
                idx_list.append('\\%s' % family_idx)   # Spouse Index for

                if self.kid_report:   # embedded family
                    if death['cause']:
                        dse_list.extend(self.apply_dse_index('', death['cause']))

                    spse_media = spouse.get_media_list()
                    if spse_media:
                        passport_text = self.apply_passport(spouse)
                        mda_list.append(passport_text)

            narr_text = self.narrator.get_married_string(family, is_first, self._name_display)
            if narr_text:
                mar_text, mar_cit, __ = self.apply_embedded_place('em', narr_text, family, \
                                                EventType.MARRIAGE, EventRoleType.FAMILY)
                if mar_cit: cit_list += add_to_list(mar_cit)

                # Satzkorrekturen
                if family.type.string != 'Geschieden':
                    mar_text = mar_text.replace('hatte', 'hat')
                mar_tmplist = mar_text.split(spouse_name.lastname)

                mar_text = '\n' if mar_list else ''   # Linefeed for second spouse!
                if spouse.gramps_id == 'I00145':
                    s = 1

                spse_idx = family_idx if self.kid_report else spouse_idx
                if family.type.string in ['Verheiratet', 'Geschieden']:
                    mar_text += 'Er' if spouse.gender == 0 else 'Sie'
                    if is_first: mar_text += ' heiratete \\e%s' % spse_idx
                    else: mar_text += ' heiratete auch \\e%s' % spse_idx
                else:
                    mar_text += mar_tmplist[0].split('mit')[0]
                    mar_text += 'mit \\e%s' % spse_idx

                if self.kid_report and spse_lifetime:   # embedded family
                    mar_text += ' (%s)#' % spse_lifetime   # Setzt Marker '#'

                # Attribut: standesamtliche / kirchliche Hochzeit
                marr_event, marr_ref = find_specific_event(self.database, family, [EventType.MARRIAGE], \
                                            descriptionlist=['Civil'], roletypelist=[EventRoleType.FAMILY])
                if marr_event:
                    cit_item = self.add_citations(marr_event, False)   # Eintrag in die Citationsliste
                    if cit_item: cit_list += add_to_list(cit_item)
                    if marr_event.description:
                        mar_text += ' %s' % replace_all(marr_event.description, self.marr_dict)
                    if len(mar_tmplist) > 1:
                        mar_text += mar_tmplist[1].replace(', ' + spouse_name.firstnames, '')

                    if self.kid_report:   # embedded family
                        marrref_list = find_reference_object(self.database, family, marr_ref, \
                                                             roletypelist=[u'Zeuge', u'Trauzeuge'])
                        marrref_line = self.apply_witnessed_referenced_person(marrref_list, '\\symWITx')
                        if marrref_line: mar_text = mar_text[:-1] + marrref_line

                # Attribut: kirchliche Hochzeit
                wedd_event, wedd_ref = find_specific_event(self.database, family, [EventType.CUSTOM], \
                                            eventtypestring='Trauung', roletypelist=[EventRoleType.FAMILY])
                if wedd_event:
                    cit_item = self.add_citations(wedd_event, False)   # Eintrag in die Citationsliste
                    if cit_item: cit_list += add_to_list(cit_item)
                    wedd_desc = replace_all(wedd_event.description, self.marr_dict)
                    wedd_date = self._get_date(wedd_event.get_date_object())
                    wedd_date = replace_all(wedd_date, MONTHS_DICT)
                    wtype, __, wcountry, wplace, wlocality, __ = self.apply_event_place(wedd_event)
                    weddloc_list, weddloc = self.apply_loc_index('em', wtype, wcountry, wplace, wlocality)
                    if mar_text[:-1] == '.': mar_text = mar_text[:-1] + ','
                    mar_text += ' %s am %s in %s.' % (wedd_desc, wedd_date, weddloc)

                    if self.kid_report:   # embedded family
                        weddref_list = find_reference_object(self.database, family, wedd_ref, \
                                                             roletypelist=[u'Zeuge', u'Trauzeuge'])
                        weddref_line = self.apply_witnessed_referenced_person(weddref_list, '\\symWITx')
                        if weddref_line: mar_text = mar_text[:-1] + weddref_line
                """
                marr_event2 = []
                if len(marr_event) > 1:
                   marr_event2.append(marr_event[1])
                tmp_event = self.apply_defined_event(family, EventType.CUSTOM, EventRoleType.FAMILY)
                if tmp_event and tmp_event[0].type.string == 'Trauung':
                    marr_event2.extend(tmp_event)

                add_text = ''
                if marr_event2:
                    for marr_evt in marr_event2:
                        add_desc = replace_all(marr_evt.description, self.marr_dict)
                        add_date = self._get_date(marr_evt.get_date_object())

                        mtype, __, mcountry, mplace, mlocality, __ = self.apply_event_place(marr_evt)
                        addloc_list, addloc = self.apply_loc_index('em', mtype, mcountry, mplace, mlocality)
                        # if addloc_list and len(addloc_list) > 1: loc_list.extend(addloc_list)

                        add_text += ', %s am %s in %s' % (add_desc, add_date, addloc)
                        cit_text = self.add_citations(marr_evt, False)
                        if cit_text: cit_list.append(cit_text)   # Eintrag in die Citationsliste

                    add_text += '.'
                    mar_text = mar_text[:-1] + add_text
                """
                mar_text = self.replace_narrative_text(mar_text, False)
                mar_list.append(mar_text)
                is_first = False

        return spouse_dict, mar_list, cit_list, idx_list, loc_list, mda_list

    def write_mate(self, person, family):
        """
        Write information about the person's spouse/mate.
        """
        # Clear Event Citation Liste
        del self.event_citlist[:]

        mate_handle = family.get_mother_handle() \
            if person.get_gender() == Person.MALE else \
            family.get_father_handle()

        if mate_handle:
            mate = self.database.get_person_from_handle(mate_handle)
            self.regular_map[mate.gramps_id] = mate_handle
            self.analyse_person(mate)

            text_narr, index_narr, citation_narr = self.write_person_narr(mate)

            # Element: Alternate Names
            self.dependent.clear(DEPENDENT)
            self.altname = self.find_name_alternate(mate)

            self.apply_divider('-','\n')

            text_list = []
            # Element: Spacer
            text_list.append('\\vspace{+2 ex}\n')

            # Element: Individual name
            mate_name = ordName(mate, groupas=self.include['person']['groupnames'])   # Extract the right names
            text_list.append('\\narrLabel{}[%s]\n' % mate_name.nametype)
            text_list.append('\\narrHead')
            if family.get_child_ref_list():
                text_list.append('[%s:]' % (self._("Spouse")))
            else:
                text_list.append('[\\Mate{%s}[%s]:]' % (self._("Spouse"), family.gramps_id))

            text_list.append('%s\n' % mate_name.linename)

            # Element: Family Index
            text_list.append('%s\n' % ''.join(index_narr))

            # Element: Passport picture
            passport = False
            if self.include['person']['passport']:
                passport_text = self.apply_passport(mate)
                if passport_text:
                    passport = True
                    text_list.append(passport_text)

            # Element: Line line
            if self.include['person']['lifeline']:
                options = {'mode': 0, 'new_generation': False, 'act_generation': self.act_generation,
                           'rindent': passport, 'groupname': self.include['person']['groupnames'], 'index_map': self.index_map}
                life_line = apply_lifeline(self.database, person, options)
                if life_line: text_list.append(life_line)

            # Element: Write Data
            self.push_list(text_list)
            self.push_list(text_narr)

            event_list, attr_text, media_text = self.apply_person_info(mate)
            self.write_person_info(mate, event_list, citation_narr, attr_text, media_text)

            self.dependent.clear(DEPENDENT)
            self.altname.clear(ALTERNATE)

            # Clear Event Citation Liste
            del self.event_citlist[:]


    def get_child_label(self, child, name, counter):
        """"""
        text_line = ''
        prefix = ''
        if self.include['family']['childsign']:
            for family_handle in child.get_family_handle_list():
                family = self.database.get_family_from_handle(family_handle)
                if family.get_child_ref_list():
                    prefix = "+"
                    break

        gen_str = ''
        if child.handle in self.index_map:
            # index_map: DAR = int, DDR = str!
            if (self.report == 'A'):
                gen_no = self.index_map[child.handle]
            else:   # (self.report == 'D')
                if self.index_map[child.handle].isnumeric():
                    gen_no = int(self.index_map[child.handle])
                else:
                    gen_no = int(self.index_map[child.handle], 16) -16
            gen_str = '{0:,}'.format(int(gen_no)).replace(',',' ')
        if gen_str: text_line += '[%s]' % gen_str

        text_line += '{'
        if prefix: text_line += '%s ' % prefix
        text_line += '%s.}'% ReportUtils.roman(counter +1).lower()
        # if not 'G' in name.nametype:
        text_line += '[%s]' % name.nametype

        return text_line, gen_str

    def get_child_type(self, child_type):
        """"""
        symbol = ''
        if child_type.value == child_type.CIVIL_UNION:
            symbol = '\\ftCU'   # gesetzliche Partnerschaft
        elif child_type.value == child_type.MARRIED:
            symbol = '\\ftM'   # Verheiratet
        elif child_type.value == child_type.UNMARRIED:
            symbol = '\\ftD'   # Geschieden (Divorced)
        elif child_type.value == child_type.UNKNOWN:
            symbol = '\\ftU'   # Unbekannt
        elif child_type.value == child_type.CUSTOM:
            symbol = '\\ftC'   # Benutzerdefiniert

        return symbol

    def get_subchild(self, family_handle):
        """"""
        if not family_handle:
            return None

        def get_spouse(family, spouse, child):
            """"""
            spse_list = ['\n%s\\begin{subColumn}' % (' '*2)]

            cit_list, loc_list = [], []
            spse_lifetime, spse_birthcit, spse_deathcit = self.apply_person_lifetime(spouse, con=',', div=';')
            spse_lifelist = spse_lifetime.split('}; ')   # Saubere Trennung!
            spse_lifelist[0] += '}'
            spse_born = spse_lifelist[0].split(' ', 1)
            spse_born1 = spse_born[1] if len(spse_born) > 1 else ''
            spse_list.append('\n%s\\colItem{%s}{%s}.' % ((' '*4), spse_born[0], spse_born1))
            if spse_birthcit: spse_list.append(self.apply_citation_text(spse_birthcit))

            __, par_line, par_cit = self.apply_parents(spouse, child, prefix='o', con='\\&')
            if par_line:
                if par_cit: cit_list += add_to_list(par_cit)
                par_sym = '\\symwBbMbW' if spouse.gender else '\\symwGbMbW'
                spse_list.append('\n%s\\colItem{%s}{%s}.' % ((' '*4), par_sym, par_line))

            marr_sym, marr_line, marr_cit = self.apply_marriage(family)
            if marr_line:
                if marr_cit: cit_list += add_to_list(marr_cit)
                spse_list.append('\n%s\\colItem{\\marrCIV}{%s}.' % ((' '*4), marr_line))
            wedd_sym, wedd_line, wedd_cit = self.apply_wedding(family)
            if wedd_sym == '\\marr[r.k.]': wedd_sym = '\\marrRK'
            elif wedd_sym == '\\marr[ev.]': wedd_sym = '\\marrEV'
            if wedd_line:
                if wedd_cit: cit_list += add_to_list(wedd_cit)
                spse_list.append('\n%s\\colItem{%s}{%s}.' % ((' '*4), wedd_sym, wedd_line))

            if len(spse_lifelist) > 1:
                spse_death = spse_lifelist[1].split(' ', 1)
                spse_death1 = spse_death[1] if len(spse_death) > 1 else ''
                spse_list.append('\n%s\\colItem{%s}{%s}.' % ((' '*4), spse_death[0], spse_death1))
                if spse_deathcit: spse_list.append(self.apply_citation_text(spse_deathcit))

            spse_list.append('\n%s\\end{subColumn}' % (' '*2))

            if spse_list:
                return [spse_list, cit_list, loc_list]
            else:
                return None

        self.mode['part'] = 'sC'   # P-erson
        list_left, list_right = [], []
        txt_list, cit_list = [], []

        family = self.database.get_family_from_handle(family_handle)
        counter, number = 0, len(family.get_child_ref_list())
        for counter, child_ref in enumerate(family.get_child_ref_list()):
            child = self.database.get_person_from_handle(child_ref.ref)
            if not self.include['common']['private'] and child.private: continue
            self.regular_map[child.gramps_id] = child.handle

            # Data preparing ...
            name = ordName(child, groupas=self.include['person']['groupnames'])   # Extract the right names
            cit_list += add_to_list(self.add_citations(name.Basename, False))
            child_lifetime, child_birthcit, child_deathcit = self.apply_person_lifetime(child, con=',', div='\\n')

            alt_name_str, alt_ind_str = '', ''
            alt_name = self.find_name_alternate(child)
            # 1: AKA, 2: Birthname, 3: Married-, 6: Christen-, 7: Call-
            for alt_type in [6, 7, 2, 1, 3]:
                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(alt_name, alt_type, '  ')
                if alt_cit: cit_list += add_to_list(alt_cit)
                if alt_nme: alt_name_str += alt_nme
                if alt_ind: alt_ind_str += '%s ' % alt_ind

            # Text compiling ...
            cit_str, kid_str = '', ''
            label_str, __ = self.get_child_label(child, name, counter)
            cit_str = self.apply_citation_text(cit_list)
            kid_str += '  \\col#Label%s\n' % label_str
            kid_str += '  \\col#Head%s' % name.linename
            if cit_str: kid_str += '!%s!' % cit_str
            if alt_name_str:
                kid_str += '\n%s%s' % (' '*2, alt_name_str)
                if alt_ind_str:
                    kid_str += '\n%s%s' % (' '*4, alt_ind_str.strip())
            if child_lifetime:
                kid_str += '\n%s\\col#Text{%s}' % (' '*2, child_lifetime)
                kid_str += '!%s!' % self.apply_citation_text(child_birthcit + child_deathcit)

            spse_txt = ''
            for ref_family_handle in child.get_family_handle_list():
                ref_family = self.database.get_family_from_handle(ref_family_handle)
                spouse_handle = ReportUtils.find_spouse(child, ref_family)
                if not spouse_handle: continue

                spouse = self.database.get_person_from_handle(spouse_handle)
                __, spouse_idx, ref_family_idx = self.apply_marriage_index(ref_family, child, spouse, prefix='')
                spouse_name = ordName(spouse)   # Extract the right names
                if spouse and spouse_name.valid:
                    self.apply_embedded_referenced_person(spouse, child)
                    spse_lastname, spse_birth, spse_death = self.analyse_person(spouse, False)
                    if spse_birth['cit']: cit_list += add_to_list(spse_birth['cit'])
                    if spse_death['cit']: cit_list += add_to_list(spse_death['cit'])
                    spse_txt += '\n%s\\col#Text{\\marr[%s] \\e%s}' % (' '*2, ref_family.gramps_id, ref_family_idx)
                    spse_list = get_spouse(ref_family, spouse, child)
                    if spse_list:
                        if spse_list[1]: spse_txt += '!%s!' % self.apply_citation_text(spse_list[1])
                        spse_txt += ''.join(spse_list[0])
                        a = 1

            if counter % 2:   # Debug & View!
                kid_str = kid_str.replace('#', 'R')
                spse_txt = spse_txt.replace('#', 'R')
                list_right.append(kid_str + spse_txt)
                list_right.append('  \n\n')
            else:
                kid_str = kid_str.replace('#', 'L')
                spse_txt = spse_txt.replace('#', 'L')
                list_left.append(kid_str + spse_txt)
                list_left.append('  \n\n')
            """
            if counter > 0 and counter < number and counter % 2:
                text_list.append(' \\\\\n\n')
            else: text_list.append(' &\n\n')
            """

        self.mode['part'] = 'K'   # K-id
        if list_left or list_right:
            txt_list = ['\\begin{kidColumn}!n0![.075][.475][.075][.475]\n']
            txt_list.extend(list_left)
            txt_list.append('&\n')
            txt_list.extend(list_right)
            txt_list.append('\\end{kidColumn}\n')
            return txt_list

        return None

    def write_children(self, family):
        """
        List the children for the given family.
        """
        if not family.get_child_ref_list():
            return None

        #  Element: Family Head
        text_line = '\\%s{' % 'famHead'   # \f is FormFeed (strange Results)
        __, father_shortname, mother_shortname = self.family_base.apply_head(family)
        if mother_shortname:
            mother_shortname = mother_shortname.replace('N.N. N.N.', '\\NN')
            text_line += mother_shortname.replace('N.N.', '\\NN')
        text_line += '}'
        if mother_shortname and father_shortname:
            fam_conn = self.apply_family_and(family.type)
            if not 'M' in fam_conn: text_line += '[%s]' % fam_conn
        text_line += '{'
        if father_shortname:
            father_shortname = father_shortname.replace('N.N. N.N.', '\\NN')
            text_line += father_shortname.replace('N.N.', '\\NN')
        text_line += '}'
        if not self.include['children']['marriage']:
            text_line += '[%s]' % family.gramps_id
        text_line += '\n\n'
        self.doc_handle.write(text_line)

        #  Element: All Children
        child_counter = 0
        for child_counter, child_ref in enumerate(family.get_child_ref_list()):
            child_handle = child_ref.ref
            child = self.database.get_person_from_handle(child_handle)
            self.regular_map[child.gramps_id] = child_handle
            child_name = ordName(child, groupas=self.include['person']['groupnames'])   # Extract the right names

            if not self.include['common']['private'] and child.private: continue

            self.narrator.set_subject(child)
            text_list, index_list, citation_list, location_list, disease_list = [], [], [], [], []
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
            # Element: Label
            text_line = '\\kidLabel'
            label_str, gen_str = self.get_child_label(child, child_name, child_counter)
            text_line += label_str
            self.doc_handle.write('%s\n' % text_line)

            citation_list += add_to_list(self.add_citations(child, False))
            citation_list += add_to_list(self.add_citations(child_name.Basename, False))

            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
            child_dict = self.apply_person_narr(child, ext=True)
            citation_list += add_to_list(child_dict['cit_list'])
            if not gen_str: location_list.extend(child_dict['loc_list'])

            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
            # Element: Alternate Names
            if self.include['person']['altnames']:
                self.kid_report = True   # Aktiviert Flag für embedded
                self.dependent.clear(DEPENDENT)
                self.altname = self.find_name_alternate(child)

                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 1)   # 1: Also known as (AKA)
                if alt_nme: text_list += add_to_list('%s\n' % alt_nme)
                if alt_cit: citation_list += add_to_list(alt_cit)
                if alt_ind: text_list+= add_to_list('%s\n' % alt_ind)

                alt_nme, alt_cit, alt_ind = self.apply_name_alternate(self.altname, 3)   # 3: Married name
                if alt_nme: text_list+= add_to_list('%s\n' % alt_nme)
                if alt_cit: citation_list += add_to_list(alt_cit)
                if alt_ind: text_list+= add_to_list('%s\n' % alt_ind)

                self.altname.clear(ALTERNATE)
                self.kid_report = False

            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
            # Element: Marriage
            # A: Ancestor, D: Descendant, !=: xor
            child_marriage = False
            child_marriage |= (self.report == 'A')
            child_marriage |= (self.report == 'D') and (self.act_generation == self.max_generation)

            media = []
            marr_text, marr_nr = [], -1
            childs_text = []
            if child_marriage and not gen_str: # and (child_handle in self.index_map)
                self.mode['part'] = 'K'   # K-id
                self.kid_report = True   # Aktiviert Flag für embedded family

                spouses, texts, citations, __, __, media = \
                    self.apply_marriage_narr(child)
                if texts:
                    marr_text.append('  %s\n' % ''.join(texts))
                    marr_nr += 1

                if citations: citation_list += add_to_list(citations)
                # if locations: location_list.extend(locations)

                for sid in spouses:
                    spouse_handle = spouses[sid]['spouse']
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    self.regular_map[spouse.gramps_id] = spouse_handle
                    self.narrator.set_subject(spouse)

                    if child.gramps_id == 'I00021':
                        a = 1
                    par_text, __, par_cit = self.apply_parents(spouse, child, prefix='o')
                    if par_text:
                        if par_cit: citation_list += add_to_list(par_cit)

                        if not par_text.endswith('NN'): par_text = par_text[:-1]
                        if spouse.gender == 0: par_tmplist = par_text.split(' die ')
                        if spouse.gender == 1: par_tmplist = par_text.split(' der ')
                        if '#' in marr_text[marr_nr]:
                            marr_tmplist = marr_text[marr_nr].split('#')
                            marr_text[marr_nr] = marr_tmplist[0][:-1] + ', ' + par_tmplist[1].lstrip() + ')' + marr_tmplist[1]
                        else:   # Outdated? 2026-02-09
                            # tmp_list = marr_text[marr_nr].split('.')
                            # marr_text[marr_nr] = tmp_list[0][:-1] + ' ( ' + par_text + ')' + tmp_list[1]
                            pass
                    marr_text[marr_nr] = self.replace_narrative_text(marr_text[marr_nr])
                    marr_text[marr_nr] = marr_text[marr_nr].replace('#', '')   # Entfernt letzte Marker

                    subchild_list = self.get_subchild(spouses[sid]['family'])
                    if subchild_list:
                        childs_text.extend(subchild_list)
                        pass

                self.kid_report = False   # Dektiviert Flag für embedded family
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

            text_line = '\\kidHead'
            text_line += child_name.linename

            citation_text = self.apply_citation_text(citation_list)
            if citation_text:text_line += '!%s!' % citation_text
            self.doc_handle.write('%s\n' % text_line)

            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
            # A: Ancestor, D: Descendant
            child_media = False
            child_media |= (self.report == 'A')
            child_media |= (self.report == 'D') and (self.act_generation == self.max_generation)

            kid_media = ''
            if child_media:
                media_list = child.get_media_list()
                if media_list:
                    kid_media += '>|'
                    passport_text = self.apply_passport(child)
                    if passport_text: media.append(passport_text)
            if media:
                for mda in media: self.doc_handle.write(mda)

            if child_dict['birth'] or marr_text or child_dict['death']:
                text_list.append('\\kidText')
                if kid_media: text_list.append(kid_media)
                text_list.append('{\n')

                text_line = ''
                if child_dict['birth']: text_line = '  %s' % child_dict['birth']
                if child_dict['christen']: text_line = text_line[:-1] + child_dict['christen']
                text_list.append('%s\n' % text_line)

                if marr_text: text_list.extend(marr_text)

                text_line = ''
                if child_dict['death']: text_line = '  %s' % child_dict['death']
                if child_dict['burial']: text_line = text_line[:-1] + child_dict['burial']
                text_list.append('%s\n' % text_line)

                if self.base['par_language']:
                    self.narrator.set_subject(child)
                    self.apply_language(child, self.base['par_language'])
                    text_parr = self.apply_person_parallel(child)
                    self.apply_language(child, 'de')
                    text_list.append('[%\n')
                    if text_parr: text_list.append('  %s' % text_parr)
                    text_list.append(']')

                if location_list:
                    location_line = self.apply_list(location_list, '  ', '', 'C', 'S', ' ')
                    text_list.append('%s\n' % location_line)
                text_list.append('}\n')

                if childs_text: text_list.extend(childs_text)

                self.push_list(text_list)

            self.write_list(index_list)
            # self.write_list(disease_list) # Disease tag inside text
            self.doc_handle.write('\n')

        return True

    # Gramps Object methods
    def compress_object_list(self, gramps_list):
        """ Compile a 'Gramps list' """

        grmps_list = []
        for grmp in gramps_list:
            grmp_lst = add_to_list(grmp.strip())
            if grmp_lst: grmps_list.extend(grmp_lst)

        grmps_list = list(set(grmps_list))   # Eliminates doubles
        grmps_list = sorted(grmps_list)

        return grmps_list

    # Citation methods
    def substract_citation_list(self, citation_list, event_list):
        """ Substract from a 'Citation list' """
        if not citation_list: return []

        if event_list:
            cit_list = self.compress_object_list(citation_list)
            event_list = self.compress_object_list(event_list)
            return [x for x in cit_list if x not in event_list]

        return citation_list

    def apply_citation_text(self, citation_list, embedded=None):
        """ Compose 'Citation list' to a 'Citation string' """
        if not self.include['common']['sources']: return None

        cit_list = self.compress_object_list(citation_list)

        cit_div2, cit_div3, cit_div4, cit_rest, cit_text = 0, 16, 26, '', ''
        if cit_list:
            if not embedded:
                cit_text += '\\Cit'
                cit_div2 = math.ceil(len(cit_list) / 2)
                if cit_div2 < 2 : cit_div2 = 2
                # max. 8 citation in row
                if len(cit_list) > 17: cit_div2 = 8

                for i, cit in enumerate(cit_list):
                    if i == 0: cit_text += '{%s}' % cit
                    elif i == cit_div2: cit_text += '+[%s]' % cit
                    elif i == cit_div3: cit_text += '-[%s]' % cit
                    elif i == cit_div4: cit_rest += '[%s]' % cit
                    else: cit_text += '[%s]' % cit
                if len(cit_list) > 17: cit_text += '-'
                if len(cit_list) > 2: cit_text += '+'
                if cit_rest: cit_text += '%% %s' % cit_rest
            else:
                for cit in cit_list:
                    cit_text += ', %s' % cit if cit_text else cit

        return cit_text


    def add_citations(self, objekt, embedded=True):
        """ Collect (list of) citation to 'cit_text' """
        if not objekt or not self.include['common']['sources']: return ''

        # 2016-10-31: From gramps/gen/plug/report/endnotes.py
        # text = endnotes.cite_source(self.bibliography, self.database, person)
        cit_text, cite_text = '', ''
        cit_list = objekt.get_citation_list()
        for ref in cit_list:
            if cit_text: cit_text += ', '
            citation = self.database.get_citation_from_handle(ref)
            if not citation: continue
            if not self.include['common']['private'] and citation.private: continue

            if citation.attribute_list:
                cit_dict = self.apply_attribut(citation.attribute_list, ['C', 'L'])  # C-ite, L-ink
                if 'link' in cit_dict:
                    citation = self.database.get_citation_from_gramps_id(cit_dict['link'])
                    if not citation: continue
                    if not self.include['common']['private'] and citation.private: continue

                cite_text = self.apply_attribute_dict(cit_dict)

            if citation.gramps_id in self.cit_substitution_dict:
                citation = self.database.get_citation_from_gramps_id(self.cit_substitution_dict[citation.gramps_id])
            """
            for subst_list in self.cit_substitution_dict.values():
                for subst_dict in subst_list:
                    if citation.handle in subst_dict['cit_list']:
                        backup = citation
                        citation = self.database.get_citation_from_gramps_id(subst_dict['cit_subst'])
                        print('Substitution:: %s %s -> %s %s' % (backup.gramps_id, backup.page, citation.gramps_id, citation.page))
            """

            if citation:
                (cit_index, ref_key) = self.bibliography.add_reference(citation)
            else:
                print('endnotes::Error: Citation failed, Ref: >%s<' % ref)
                continue
            if citation.gramps_id: cit_text += citation.gramps_id

        if cit_text and embedded:  # for narrate texts!
            cit_text = '<super>' + cit_text + '</super>'

        return cit_text
