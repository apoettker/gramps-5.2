# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2019  Alois Poettker
#

"Substitute objects in Gramps"

#-------------------------------------------------------------------------
#
# standard python modules
#
#-------------------------------------------------------------------------
import codecs, csv, logging
from io import TextIOWrapper

LOG = logging.getLogger('.SubstituteObjects')

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

from gramps.plugins.importer.importcsv import rd

class SubstitutionParser:
    """
    Class to compute substitution elements in Gramps objects
    """
    def __init__(self):
        """"""
        column2label = {
            "element": ("element", _("element"), _("Element")),
            "original": ("original", _("original"), _("Original")),
            "substitute": ("substitute", _("substitute"), _("Substitute")),
            "action": ("action", _("action"), _("Action")),
            "description": ("description", _("description"), _("Description")),
            # ----------------------------------
            "person": ("person", _("person"), _("Person")),
            "name": ("name", _("name"), _("Name")),
            # Elements
            "firstname": ("firstname", _("firstname"), _("Firstname"),
                          "first name", _("first name"), _("First name"),
                          "given", _("given"), _("Given"),
                          "given name", _("given name"), _("Given name")),
            "suffix": ("suffix", _("suffix"), _("Suffix")),
            "groupname": ("groupname", _("groupname"), _("Groupname"),
                          "group name", _("group name"), _("Group name")),
            "nickname": ("nickname", _("nickname"), _("Nickname")),
            "translation": ("translation", _("translation"), _("Translation")),
            "prefix": ("prefix", _("prefix"), _("Prefix")),
            # ----------------------------------
            "event": ("event", _("event"), _("Event")),
            "christen": ("christen", _("christen"), _("Christen"),
                         "christening", _("christening"), _("Christening"),),
            "baptism": ("baptism", _("baptism"), _("baptism")),
            "marriage": ("marriage", _("marriage"), _("Marriage")),
            "burial": ("burial", _("burial"), _("Burial")),
            # Elements
            "place": ("place", _("place"), _("Place")),
            # ----------------------------------
        }
        lab2col_dict = []
        for key in list(column2label.keys()):
            for val in column2label[key]:
                lab2col_dict.append((val.lower(), key))
        self.label2column = dict(lab2col_dict)

        self.exist = False
        # Accepted substituable elements
        self.person_dict = {}
        self.person_elements = ['firstname', 'akaname', 'suffix', 'translation', 'nickname', 'groupname', \
                                'prefix', 'lastname']

        # Accepted substituable elements
        self.event_dict = {}
        self.event_elements = ['place']

        # Accepted substituable elements
        self.ancestor_dict = {}
        self.ancestor_type = ['lastname']

    def import_data(self, filename):
        """Function synonym called by Gramps to import data in CSV format."""

        try:
            if filename[-4:] != ".csv": filename += ".csv"
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
                msg = _("Reading: substitution file %(filename)s.") % \
                    {'filename' : filename}
                print(msg)
                self.exist = True

                self._parse(filehandle)

        except EnvironmentError as err:
            msg = _("%s could not be opened\n") % filename, str(err)
            print(msg)

            return None

    def _cleanup_column_name(self, column):
        """Handle column aliases for CSV spreadsheet import and SQL."""
        return self.label2column.get(column, column)

    def _read_csv(self, filehandle):
        'Read the data from the file and return it as a list.'
        try:
            data = [[r.strip().replace('"', '') for r in row] \
                    for row in csv.reader(filehandle)]

        except csv.Error as err:
            if user:
                self.user.notify_error \
                    (_('format error: line %(line)d: %(zero)s') % \
                    {'line' : reader.line_num, 'zero' : err })
            return None

        return data

    def _parse(self, filehandle):
        """
        Parse each line of the input data file and act accordingly.
        """
        data = self._read_csv(filehandle)

        header = None
        for line_number, row in enumerate(data, 1):
            row_0 = [r.strip() for r in row[0].split(';') if r != '']
            if ''.join(row_0) == '':   # no blanks are allowed inside a table
                header = None   # clear headers, ready for next 'table'CALL
                continue
            if row_0[0][0] == '#':   # comment lines starts with '#'
                continue

            if header is None:
                header = [self._cleanup_column_name(r.lower()) for r in row]
                col = {}
                for count, key in enumerate(header):
                    col[key] = count
                continue

            # different kinds of data: persons, events
            if ('person' in header):
                # ('element' in header) and
                #('original' in header) and
                #('substitute' in header)):
                self._parse_person(line_number, row, col)
            elif ('event' in header):
                self._parse_event(line_number, row, col)
            elif ('ancestor' in header):
                self._parse_ancestor(line_number, row, col)
            else:
                LOG.warning('ignoring line %d' % line_number)

        return None

    def _parse_person(self, line_number, row, col):
        "Parse the content of a Person line."
        person_type = rd(line_number, row, col, 'person')
        if person_type in self.person_elements:
            original = rd(line_number, row, col, 'original')
            substitut = rd(line_number, row, col, 'substitute')
            substitute = substitut if substitut != '~' else ''
            gndr = rd(line_number, row, col, 'gender')
            if gndr == 'F': gender = 0
            elif gndr == 'M': gender = 1
            else: gender = 2
            action = rd(line_number, row, col, 'action')
            if not person_type in self.person_dict:
                self.person_dict[person_type] = {}
            person_dict = self.person_dict[person_type]
            if not original in person_dict:
                person_dict[original] = [action, substitute, gender]
            # print(person_type, original, action, substitute)   # Debug!

    def _parse_event(self, line_number, row, col):
        "Parse the content of a Event line."
        event_type = rd(line_number, row, col, 'event')
        element = rd(line_number, row, col, 'element')
        if element in self.event_elements:
            original = rd(line_number, row, col, 'original')
            substitute = rd(line_number, row, col, 'substitute')
            description = rd(line_number, row, col, 'description')
            if original and substitute:
                if not event_type in self.event_dict:
                    self.event_dict[event_type] = {}
                event_dict = self.event_dict[event_type]
                if not element in event_dict:
                    event_dict[element] = {}
                element_dict = event_dict[element]
                element_dict[original] = [substitute, description]
                # print(event_type, element, original, substitute)   # Debug!

    def _parse_ancestor(self, line_number, row, col):
        "Parse the content of a Ancestor line."
        element_type = rd(line_number, row, col, 'ancestor')
        if element_type in self.ancestor_type:
            generation = rd(line_number, row, col, 'generation')
            if not generation: generation = -1
            predessor = rd(line_number, row, col, 'predessor')
            successor = rd(line_number, row, col, 'successor')
            if predessor and successor:
                if not element_type in self.ancestor_dict:
                    self.ancestor_dict[element_type] = {}
                ancestor_dict = self.ancestor_dict[element_type]
                if not predessor in ancestor_dict:
                    ancestor_dict[(int(generation), predessor)] = successor
                    # print(element_type, predessor, generation, successor)   # Debug!

    def compare_person(self, element, original, source='', generation=0, gender=2):   # 2: Unknown
        'Compare element: original and/or substitute'
        if not self.exist:
            return False, '', '', ''

        if element in self.person_dict:
            element_dict = self.person_dict[element]

            if element in ['firstname', 'lastname', 'akaname']:
                if original == '':
                    return 'replace', '', 'N.N.', ''
                if 'N.N.' in original:
                    return False, '', '', ''
                if 'N. N.' in original:
                    return 'replace', 'N. N.', 'N.N.', ''

            if element in ['firstname', 'akaname']:
                action, subst, add = None, '', ''
                for orig in original.split(' '):
                    if '-' in orig:
                        action = 'replace'
                        tmp = orig.split('-')
                        subst = tmp[0].capitalize() + '-' + tmp[1].capitalize()
                        break
                    if '?' in orig:
                        action = 'replace'
                        break
                    if orig.isupper():
                        action = 'replace'
                    if orig in element_dict:
                        if element_dict[orig][2] < 2:   # 'F', 'M'
                            if element_dict[orig][2] == gender:
                                action = element_dict[orig][0]
                                subst += '%s ' % element_dict[orig][1]
                        else:
                            action = element_dict[orig][0]
                            if len(orig) == 1:   #  Letter!
                                add = element_dict[orig][1]
                            elif 'shift' in action:   # L: Lastname, P: Prefix
                                subst = '%s' % element_dict[orig][1]
                                if 'P' in  action:   # Prefix
                                    return action, original.rstrip(), subst, orig
                            else:
                                subst += '%s ' % element_dict[orig][1].capitalize()
                    else:
                        subst += '%s ' % orig.capitalize()
                return action, original.rstrip(), subst.rstrip(), add.strip()

            if element in ['lastname']:
                action, subst, add = None, '', ''
                if original.isupper():
                    action = 'replace'
                if original in element_dict:
                    action = element_dict[original][0]
                    subst += element_dict[original][1]

                return action, original.rstrip(), subst.rstrip(), add.strip()

            if element in ['suffix', 'prefix']:
                action, substitute = None, ''
                if original in element_dict:
                    action = element_dict[original][0]
                    substitute = element_dict[original][1]
                return action, original.rstrip(), substitute.rstrip(), ''

            if element in ['nickname', 'translation']:
                action, subst = None, ''
                for orig in original.split(' '):
                    # Rules for short adjectives (eg. 'd.' = 'der')
                    if '.' in orig: orig = orig.split('.')[0] + '.'
                    if orig in element_dict:
                        action = element_dict[orig][0]
                        if element_dict[orig]:
                            subst = element_dict[orig][1]
                        break
                return action, orig.rstrip(), subst.rstrip(), ''

            if element == 'groupname':
                action, group, subst = None, '', ''
                for orig in original.split(' '):
                    if orig in element_dict:
                        action = element_dict[orig][0]
                        if '(' in orig:
                            subst = original.split(orig)[0]
                        group = element_dict[orig][1]
                        break
                return action, orig.rstrip(), group.rstrip(), subst.rstrip()

        return None, '', '', ''

    def compare_event(self, event, element, original):
        'Compare element: original vs. substitute'
        if not self.exist:
            return False, '', ''

        event_type = event.get_type().string.lower()
        if event_type == _('Baptism').lower() or \
           event_type == _('Christening').lower():
            event_type = 'christen'
        elif event_type == _('Marriage').lower():
            event_type = 'marriage'
        elif event_type == _('Burial').lower():
            event_type = 'burial'

        if event_type in self.event_dict:
            event_dict = self.event_dict[event_type]

            if element in event_dict:
                element_dict = event_dict[element]

                if element == 'place':
                    org_name = original.get_name().value
                    if org_name in element_dict:
                        subst_name = element_dict[org_name][0]
                        subst_desc = element_dict[org_name][1] \
                            if len(element_dict[org_name]) > 1 else ''

                        return True, subst_name, subst_desc

        return False, '', ''

    def compare_ancestor(self, element, generation, predessor, successor):
        'Compare element: original vs. substitute'
        if not self.exist:
            return False

        if element in self.ancestor_dict:
            element_dict = self.ancestor_dict[element]

            if (generation, predessor) in element_dict:
                if ',' in element_dict[(generation, predessor)]:
                    for succ in element_dict[(generation, predessor)].split(','):
                        if successor == succ.strip():
                            return True
                elif successor == element_dict[(generation, predessor)]:
                    return True

        return False
