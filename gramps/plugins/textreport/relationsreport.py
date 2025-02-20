# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2023   Alois Poettker
#

"""Reports/Text Reports/Detailed Ancestral/Descendants Report"""

#------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------
EMPTY_ENTRY = "_____________"
HENRY = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import copy, json
from functools import partial

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.config import config

from gramps.gen.display.name import displayer as global_name_display

from gramps.gen.lib import Person  # EventType, FamilyRelType

from gramps.gen.plug.menu import StringOption
from gramps.gen.plug.report import ( Report, Bibliography )
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions

from gramps.plugins.lib.libnarrate import Narrator

# from gramps.plugins.libAP.libstatistic import GenStat
from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libtextreport import TextReport

#------------------------------------------------------------------------
#
#
#
#------------------------------------------------------------------------
class RelationsReport (Report):

    def __init__(self, database, options, user):
        """
        Create the relations object that produces the report.

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance
        """
        self.database = database
        self.options = options
        self.user = user

        self.default_dataset()
        self.read_dataset(self.options)

        Report.__init__(self, database, options, user)
        bibliography = Bibliography(Bibliography.MODE_DATE|Bibliography.MODE_PAGE)
        self.bibliography = bibliography

        self.RelRep = TextReport(bibliography, database, options)

        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()

        self.RelRep._name_display = copy.deepcopy (global_name_display)
        self.RelRep.set_locale = self.set_locale
        self.RelRep._locale = self.set_locale(get_value('trans'))   # Language switch key (= 'default')
        self.RelRep._get_date = self._get_date
        self.RelRep._get_type = self._get_type

        self.RelRep.narrator = Narrator(self.database, options.include['person']['narrative'],
                                           options.include['person']['callnames'], options.base['full_dates'],
                                           options.base['empty_date'], options.base['empty_place'],
                                           nlocale=self.RelRep._locale,
                                           get_endnote_numbers=self.RelRep.endnotes)
        # Allgemein
        self.RelRep._ = self._
        self.local_init(self.options)

    def local_init(self, options):
        """"""
        self.unpid_set = set ()
        for nid in options.base['unpid_list']:
            person = self.database.get_person_from_gramps_id(nid)
            if person: self.unpid_set.add(person.gramps_id)
        for nid in options.base['undesendant_list']:
            if 'F' in nid:
                family = self.database.get_family_from_gramps_id(nid)
                if family:
                    for childRef in family.get_child_ref_list():
                        if childRef.ref:
                            person = self.database.get_person_from_handle(childRef.ref)
                            if person: self.unpid_set.add(person.gramps_id)
            if 'I' in nid:
                person = self.database.get_person_from_gramps_id(nid)
                if person: self.unpid_set.add(person.gramps_id)

        config.set('preferences.name-format', 2)   # 2: First Name, Last name
        config.set('preferences.date-format', 5)   # 5:
        config.set('preferences.place-auto', False)   # Place Title

        self.RelRep._locale._dd.format = 5

        return True

    def default_dataset(self):
        """"""
        self.base = {}
        self._base = {
            'report': '',   # All, Anchestors, Descendants
            'result': '',   # All, Report, Lifeline, References, EndOfLine
            'result_path': '',

            "pid": '',
            "unpid_list": [],
            "undesendant_list": [],

            "max_generation": 0,
            'par_language': False,   # get_value('parlanguage')
            'full_dates': True,   # get_value('fulldates')
            "empty_place": "",   # get_value('repplace')
            "empty_date": "",   # get_value('repdate')
        }
        self.include = {}
        self._include = {
            'common': {
              'private': False,   # get_value('private')
              'ident': True,   # get_value('incident')
              'fulldate': True,   # get_value('fulldates')
              'addresses': False,   # get_value('incaddresses')
              'attributes': False,   # get_value('incattrs')
              'notes': True,   # get_value('incnotes')
              'sources': True,   # get_value('incsources')
              'srcnotes': True,   # get_value('incsrcnotes')
            },
            'person': {
                "enable": True,
                'altnames': False,
                'callnames':  True,   # get_value('usecall')
                'notes': True,   # get_value('incnotes')
                'passport': False,   # get_value('incphotos')
                'passport_generation': 8,
                'lifeline': False,   # get_value('inclifeline')
                'path':  False,   # get_value('incpaths')
                'lineage': True,   # get_value('computeage')
                'computeage': True,   # get_value('computeage')
                'narrative': True,    # get_value('verbose')
                'attributes': False,   # get_value('incattrs')
                'notes': True,   # get_value('incnotes')
                'images': False,
            },
            'mate': {   # get_value('incmates')
                'enable': False,
                'images': True,
            },
            'family': {
                'enable': False,
                'notes': True,   # get_value('incnotes')
                'childsign': True,   # get_value('inc_ssign')
                'childref': True,   # get_value('desref')
                'attributes': False,   # get_value('incattrs')
                'notes': True,   # get_value('incnotes')
                'images': False,
            },
            'children': {
                'enable': False,   # get_value('listc')
                'marriage': False,
                'childs': False,
                'images': True,
            }
        }

    def read_dataset(self, options):
        """"""
        if 'data_set' in options.options_dict:
            file_name = options.options_dict['data_set'] + '.js'
            with open(file_name, 'r') as file_handle:
                dataset = json.load(file_handle)

        {setattr(self, key, value) for (key, value) in dataset.items()}

        options.base = merge_dicts(self._base, self.base)
        if not self.base['result_path']:
            print('No resultpath ...', flush=True)
            exit(1)

        options.include = merge_dicts(self._include, self.include)
        options.include['common']['attributes'] = self.include['person']['attributes'] or self.include['family']['attributes']
        options.include['common']['notes'] = self.include['person']['notes'] or self.include['family']['notes']

        return None

    # Ancestors ----------------------------------------------------------------------------- #
    # Filter for Kekule numbering
    def apply_kekule_filter(self, index_neu, handle_neu, index_alt=0):

        if (not handle_neu) or \
           (index_neu > 2**self.RelRep.max_generation):
            return

        self.RelRep.handle_map[index_neu] = handle_neu
        self.RelRep.index_map[handle_neu] = index_neu
        self.RelRep.path_map[index_neu] = [handle_neu, []]
        if index_alt > 0:
            path = self.RelRep.path_map[index_alt][1].copy()
            path.insert(0, self.RelRep.path_map[index_alt][0])
            self.RelRep.path_map[index_neu][1] = path

        person = self.database.get_person_from_handle(handle_neu)
        # Check for 'Stop' tags
        for tag_handle in person.tag_list:
            tag = self.database.get_tag_from_handle(tag_handle)
            if 'Stop' in tag.get_name(): return

        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self.database.get_family_from_handle(family_handle)
            self.apply_kekule_filter(index_neu *2, family.get_father_handle(), index_neu)
            self.apply_kekule_filter((index_neu *2) +1, family.get_mother_handle(), index_neu)

    def write_ancestors(self):
        """"""
        name_generation = {
            1: 'Eltern', 2: 'Großeltern', 3: 'Urgroßeltern', 4: 'Alteltern', 5: 'Altgroßeltern', 6: 'Alturgroßeltern',
            7: 'Obereltern', 8: 'Obergroßeltern', 9: 'Oberurgroßeltern', 10: 'Stammeltern', 11: 'Stammgroßeltern', 12: 'Stammurgroßeltern',
            13: 'Ahneneltern', 14: 'Ahnengroßeltern', 15: 'Ahnenurgroßeltern', 16: 'Urahneneltern', 17: 'Urahnengroßeltern', 18: 'Urahnenurgroßeltern',
        }

        print('Initial ...')
        self.RelRep.mode['part'] = 'P'   # P-erson
        self.apply_kekule_filter(1, self.RelRep.center_person.get_handle())
        self.RelRep.doc_handle = open(self.RelRep.doc_file, 'w')

        self.RelRep.min_generation = 1   # Control reg. Citations
        self.RelRep.act_generation = 1
        self.RelRep.stoptag = False
        print ('Generation %s ...' % self.RelRep.min_generation)

        for key in sorted(self.RelRep.handle_map):
            if key == 1: continue   # Generation 0: Proband (not used)

            if key >= 2**self.RelRep.act_generation:
                if self.RelRep.act_generation > 1:
                    # close old Generation file
                    self.RelRep.apply_divider('-','\n')
                    self.RelRep.doc_handle.write('\\endinput\n\n')
                    self.RelRep.doc_handle.close()

                    # open next Generation file
                    self.RelRep.doc_file = '%s_Gen%s.tex' % \
                        (self.RelRep.doc_file.split('_Gen')[0], self.RelRep.act_generation)

                    self.RelRep.doc_handle = open(self.RelRep.doc_file, 'w')
                    print ('Generation %d ...' % self.RelRep.act_generation)

                pre_act_generation = 'unmittelbaren' if self.RelRep.act_generation < 4 else 'alternativen'
                roman_act_generation = ReportUtils.roman(self.RelRep.act_generation).upper()
                name_act_generation = name_generation[self.RelRep.act_generation]
                self.RelRep.doc_handle.write(u'\%sesetGenerationNG{section}[%s]{%s}{%s}\n' % \
                                             ('r', pre_act_generation, roman_act_generation, name_act_generation))
                """
                self.RelRep.doc_handle.write(u'\%sitlesectionlined\n' % 't')
                self.RelRep.doc_handle.write('\section[Generation %s --- ???]{Generation %s}\n\n' % \
                    (roman_act_generation, roman_act_generation))
                self.RelRep.doc_handle.write(u'\%sitlesubsectiondotted\n\n' % 't')
                self.RelRep.apply_divider('-','\n')
                """
                self.RelRep.act_generation += 1
                # if self.childref:
                #     self.prev_gen_handles = self.gen_handles.copy()
                #     self.gen_handles.clear()

            person_handle = self.RelRep.handle_map[key]
            person = self.database.get_person_from_handle(person_handle)
            # self.gen_handles[person_handle] = key

            if self.include['person']['enable']:
                duplicate_person = self.RelRep.write_person(person_handle)
                if not duplicate_person:   # Is this a duplicate IND record?
                    continue

            for family_handle in person.get_family_handle_list():
                family = self.database.get_family_from_handle(family_handle)
                father_handle = family.get_father_handle()
                mother_handle = family.get_mother_handle()

                if ((father_handle and father_handle not in iter(self.RelRep.handle_map.values())) or
                    (mother_handle and mother_handle not in iter(self.RelRep.handle_map.values()))):
                    if self.include['mate']['enable']:
                        self.RelRep.write_mate(person, family)

                if (mother_handle is None or
                    (mother_handle not in iter(self.RelRep.handle_map.values())) or
                    (person.get_gender() == Person.FEMALE)):
                    # The second test above also covers the 1. person's
                    # mates, which is not an ancestor and as such is not
                    # included in the self.map dictionary
                    if self.include['family']['enable']:
                        self.RelRep.write_family_info(family)
                    if self.include['children']['enable']:
                        self.RelRep.write_children(family)

                    # Mehrere Ehen
                    if father_handle:
                        father = self.database.get_person_from_handle(father_handle)
                        if father.gramps_id not in self.RelRep.relatives_map:
                            self.RelRep.relatives_map[father.gramps_id] = father_handle
                    if mother_handle:
                        mother = self.database.get_person_from_handle(mother_handle)
                        if mother.gramps_id not in self.RelRep.relatives_map:
                            self.RelRep.relatives_map[mother.gramps_id] = mother_handle

        self.RelRep.apply_divider('-','\n')
        self.RelRep.doc_handle.write('\\endinput\n\n')
        self.RelRep.doc_handle.close()

    # Descendants ---------------------------------------------------------------------------- #
    # Filter for Henry numbering
    def apply_henry_filter(self, index_neu, handle_neu, index_alt, pid, cur_gen=0):
        """"""
        # max_gen +1 wg. genealogischer Nummer
        if (not handle_neu) or (cur_gen > (self.RelRep.max_generation +1)):   # +1: get children of last generation
            return

        # nur erwünschte ID's!
        person = self.database.get_person_from_handle(handle_neu)
        if person.gramps_id in self.unpid_set:
            return

        self.RelRep.index_map[handle_neu] = pid
        self.RelRep.handle_map[index_neu] = handle_neu
        self.RelRep.path_map[index_neu] = [handle_neu, []]
        if index_alt > 0:
            path = self.RelRep.path_map[index_alt][1].copy()
            path.insert(0, self.RelRep.path_map[index_alt][0])
            self.RelRep.path_map[index_neu][1] = path

        if len(self.RelRep.gen_keys) < cur_gen +1:
            self.RelRep.gen_keys.append([index_neu])
        else:
            self.RelRep.gen_keys[cur_gen].append(index_neu)

        index_neu = 0
        person = self.database.get_person_from_handle(handle_neu)
        self.RelRep.line_map.append([pid, handle_neu, person.gender])
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                index = max(self.RelRep.handle_map)
                self.apply_henry_filter(index +1, child_ref.ref, index_neu,
                                  pid + HENRY[index_neu], cur_gen +1)
                index_neu += 1

    # Filter for d'Aboville numbering
    def apply_daboville_filter(self, person_handle, index, pid, cur_gen=1):

        if (not person_handle) or (cur_gen > self.RelRep.max_generation):
            return

        self.RelRep.dnumber[person_handle] = pid
        self.RelRep.handle_map[index] = person_handle

        if len(self.RelRep.gen_keys) < cur_gen:
            self.RelRep.gen_keys.append([index])
        else:
            self.RelRep.gen_keys[cur_gen-1].append(index)

        person = self.database.get_person_from_handle(person_handle)
        index = 1
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                ix = max(self.RelRep.handle_map)
                self.apply_daboville_filter(child_ref.ref, ix+1,
                                  pid+"."+str(index), cur_gen+1)
                index += 1

    # Filter for Record-style (Modified Register) numbering
    def apply_mod_reg_filter_aux(self, person_handle, index, cur_gen=1):
        """"""
        if (not person_handle) or (cur_gen > self.RelRep.max_generation):
            return

        self.RelRep.handle_map[index] = person_handle

        if len(self.RelRep.gen_keys) < cur_gen:
            self.RelRep.gen_keys.append([index])
        else:
            self.RelRep.gen_keys[cur_gen -1].append(index)

        person = self.database.get_person_from_handle(person_handle)

        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                ix = max(self.RelRep.handle_map)
                self.apply_mod_reg_filter_aux(child_ref.ref, ix +1, cur_gen +1)


    def apply_mod_reg_filter(self, person_handle):
        """"""
        self.apply_mod_reg_filter_aux(person_handle, 1, 1)
        mod_reg_number = 1
        for generation in range(len(self.RelRep.gen_keys)):
            for key in self.RelRep.gen_keys[generation]:
                person_handle = self.RelRep.handle_map[key]
                if person_handle not in self.RelRep.dnumber:
                    self.RelRep.dnumber[person_handle] = mod_reg_number
                    mod_reg_number += 1

    def write_descendants(self):
        """
        This function is called by the report system and writes the report.
        """
        name_generation = {
            1: 'Kinder', 2: 'Enkel', 3: 'Urenkel',
            4: 'Ur\textsup{{\sfseries x}~2}enkel', 5: 'Ur\textsup{{\sfseries x}~3}enkel', 6: 'Ur\textsup{{\sfseries x}~4}enkel',
        }

        print('Initial ...')
        self.RelRep.mode['part'] = 'P'   # P-erson
        self.RelRep.doc_handle = open(self.RelRep.doc_file, 'w')
        numbering = "Henry"
        if numbering == "Henry":
            self.apply_henry_filter(1, self.RelRep.center_person.get_handle(), 0, "1")
        elif numbering == "d'Aboville":
            self.apply_daboville_filter(1, self.RelRep.center_person.get_handle(), 0, "1")
        elif numbering == "Record (Modified Register)":
            self.apply_mod_reg_filter(1, self.RelRep.center_person.get_handle(), 0)
        else:
            raise AttributeError("no such numbering: '%s'" % numbering)

        print ('Proband ...')
        print ('Generation %s ...' % self.RelRep.min_generation)
        self.RelRep.doc_handle.write('\\chapter{Nachkommenliste}\n')

        self.RelRep.numbers_printed = list()
        for self.RelRep.act_generation in range(0, len(self.RelRep.gen_keys)):
            if self.RelRep.act_generation > self.RelRep.max_generation:
                return

            if self.RelRep.act_generation > 0:
                # close old Generation file
                self.RelRep.apply_divider('-','\n')
                self.RelRep.doc_handle.write('\\endinput\n\n')
                self.RelRep.doc_handle.close()

                # open next Generation file
                self.RelRep.doc_file = '%s_Gen%s.tex' % \
                    (self.RelRep.doc_file.split('_Gen')[0], self.RelRep.act_generation +1)

                self.RelRep.doc_handle = open(self.RelRep.doc_file, 'w')
                print ('Generation %d ...' % self.RelRep.act_generation)

                roman_act_generation = ReportUtils.roman(self.RelRep.act_generation).upper()
                name_act_generation = name_generation[self.RelRep.act_generation]
                self.RelRep.doc_handle.write(u'\%sesetGenerationNG{section}{%s}{%s}\n' % \
                                            ('r', roman_act_generation, name_act_generation))
                self.RelRep.apply_divider('-','\n')
            """
            if self.options.base['family']['childref']:
                self.prev_gen_handles = self.gen_handles.copy()
                self.gen_handles.clear()
            """
            for key in self.RelRep.gen_keys[self.RelRep.act_generation]:
                person_handle = self.RelRep.handle_map[key]
                # self.gen_handles[person_handle] = key

                self.RelRep.write_person(person_handle)
                self.RelRep.write_family(person_handle)

        self.RelRep.apply_divider('-','\n')
        self.RelRep.doc_handle.write('\\endinput\n\n')
        self.RelRep.doc_handle.close()

    #  ======================================================================================= #
    def write_report(self):
        # Leere PIDs
        """
        for nr in range(16400):
            pid = 'I' + str('%05i' % nr)
            person = self.database.get_person_from_gramps_id(pid)
            if not person:
                print(pid)
            else:
                last_name = person.get_primary_name().get_surname()
                if last_name == 'Dummy': print('%s - Dummy' % pid)
        for nr in range(5000):
            fid = 'F' + str('%04i' % nr)
            family = self.database.get_family_from_gramps_id(fid)
            if not family:
                print(fid)
        print('Fertig')
        return
        """
        if self.base['report'] == 'Ancestors':
            if self.base['result'] == 'Report' or self.base['result'] == 'All':
                self.write_ancestors()

                print ('References ...')   # Referencend persons file for Anchestors
                self.RelRep.act_generation = 1
                self.RelRep.write_refperson('A')

                print ('Citations ...')
                self.RelRep.write_endnotes(self.bibliography, self.database, self.doc)

            if self.base['result'] == 'Index' or self.base['result'] == 'All':
                print ('Index ...')
                self.apply_kekule_filter(1, self.RelRep.center_person.get_handle())
                self.RelRep.write_index('A')   # Index file for Anchestors

            if self.base['result'] == 'Lifeline' or self.base['result'] == 'All':
                print ('Lifeline ...')
                self.apply_kekule_filter(1, self.RelRep.center_person.get_handle())
                self.RelRep.write_lifeline('A')   # Lifeline file for Anchestors

            if self.base['result'] == 'EndOfLine' or self.base['result'] == 'All':
                from gramps.plugins.moduleAP.endofline import EndOfLineReport

                print ('EndOfLine ...')
                endofline = EndOfLineReport(self.database, self.options, self.user)
                endofline.write_endofline('A')

        if self.base['report'] == 'Descendants':
            if self.base['result'] == 'Report' or self.base['result'] == 'All':
                self.write_descendants()

                print ('References ...')
                self.RelRep.act_generation = 1
                self.RelRep.write_refperson('D')   # Referencend persons file for Anchestors

                print ('Citations ...')
                self.RelRep.write_endnotes(self.bibliography, self.database, self.doc)

            if self.base['result'] == 'Index' or self.base['result'] == 'All':
                print ('Index ...')
                self.RelRep.write_index('D')   # Index file for Anchestors

            if self.base['result'] == 'Lifeline' or self.base['result'] == 'All':
                print ('Lifeline ...')
                self.RelRep.write_lifeline('D')   # Lifeline file for Anchestors

#------------------------------------------------------------------------
#
# DetAncestorOptions
#
#------------------------------------------------------------------------
class RelationsReportOptions(MenuReportOptions):
    """
    Defines options and provides handling interface.
    """
    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):
        """
        Add options to the menu for the detailed descendant report.
        """
        category = _("Report Options")
        add_option = partial(menu.add_option, category)

        data_set = StringOption('', '')
        add_option('data_set', data_set)

        stdoptions.add_name_format_option(menu, category)
        stdoptions.add_localization_option(menu, category)
